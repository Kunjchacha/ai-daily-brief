"""Offline tests for the LLM adapter: no network, no real key."""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from adapters import llm  # noqa: E402

REPLY = {"candidates": [{"content": {"parts": [{"text": '{"items": []}'}]}}]}


class PickFlashTests(unittest.TestCase):
    def test_prefers_newest_stable_non_lite_text_model(self):
        names = ["gemini-2.0-flash", "gemini-2.5-flash-lite", "gemini-2.5-flash", "gemini-3-flash-preview",
                 "gemini-2.5-flash-image", "gemini-2.5-pro", "text-embedding-004"]
        self.assertEqual(llm.pick_flash(names), "gemini-2.5-flash")

    def test_uses_preview_only_when_nothing_stable(self):
        self.assertEqual(llm.pick_flash(["gemini-3-flash-preview", "gemini-pro"]), "gemini-3-flash-preview")

    def test_none_when_no_flash_model(self):
        self.assertIsNone(llm.pick_flash(["gemini-2.5-pro", "embedding-001"]))


@mock.patch.dict(os.environ, {"GEMINI_API_KEY": "fake-key-for-tests"})
class GeminiFallbackTests(unittest.TestCase):
    def setUp(self):
        llm._GEMINI_CHOSEN.clear()
        self._tmp = tempfile.TemporaryDirectory()
        patcher = mock.patch.object(llm, "STATE_PATH", Path(self._tmp.name) / "llm_state.json")
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self._tmp.cleanup)

    def test_last_working_model_is_remembered_and_tried_first(self):
        calls = []

        def post(url, body, headers, **kw):
            calls.append(url.split("/models/")[1].split(":")[0])
            return REPLY
        with mock.patch.object(llm, "_post", side_effect=post):
            llm.gemini("hi", "configured", [])
            self.assertEqual(llm._load_state()["gemini_model"], "configured")
            llm._GEMINI_CHOSEN.clear()  # simulate a brand-new run
            llm.STATE_PATH.write_text('{"gemini_model": "remembered"}', encoding="utf-8")
            calls.clear()
            llm.gemini("hi", "configured", [])
        self.assertEqual(calls[0], "remembered")

    def test_retired_model_falls_back_to_listed_alternative(self):
        def post(url, body, headers, **kw):
            if "/models/old-model:" in url or "/models/fallback-gone:" in url:
                raise llm.LLMError("request failed (HTTP 404)")
            return REPLY
        with mock.patch.object(llm, "_post", side_effect=post), \
             mock.patch.object(llm, "gemini_models", return_value=["gemini-9-flash", "gemini-9-pro"]):
            out = llm.gemini("hi", "old-model", ["fallback-gone"])
        self.assertEqual(out, '{"items": []}')
        self.assertEqual(llm._GEMINI_CHOSEN["m"], "gemini-9-flash")

    def test_configured_fallback_is_used_without_discovery(self):
        def post(url, body, headers, **kw):
            if "/models/old-model:" in url:
                raise llm.LLMError("request failed (HTTP 404)")
            return REPLY
        with mock.patch.object(llm, "_post", side_effect=post), \
             mock.patch.object(llm, "gemini_models", side_effect=AssertionError("should not discover")):
            llm.gemini("hi", "old-model", ["good-fallback"])
        self.assertEqual(llm._GEMINI_CHOSEN["m"], "good-fallback")

    def test_overloaded_model_503_moves_to_the_next_model(self):
        def post(url, body, headers, **kw):
            if "/models/busy-model:" in url:
                raise llm.LLMError("request failed (HTTP 503)")
            return REPLY
        with mock.patch.object(llm, "_post", side_effect=post), \
             mock.patch.object(llm, "gemini_models", side_effect=AssertionError("should not discover")):
            llm.gemini("hi", "busy-model", ["calm-model"])
        self.assertEqual(llm._GEMINI_CHOSEN["m"], "calm-model")

    def test_everything_overloaded_gives_one_clear_error(self):
        with mock.patch.object(llm, "_post", side_effect=llm.LLMError("request failed (HTTP 503)")), \
             mock.patch.object(llm, "gemini_models", return_value=["gemini-9-flash"]):
            with self.assertRaises(llm.LLMError) as cm:
                llm.gemini("hi", "a", ["b"])
        self.assertIn("no usable Gemini model", str(cm.exception))
        self.assertIn("503", str(cm.exception))

    def test_timeout_moves_to_the_next_model(self):
        def post(url, body, headers, **kw):
            if "/models/slow-model:" in url:
                raise llm.LLMError("request failed (Timeout after 45s)")
            return REPLY
        with mock.patch.object(llm, "_post", side_effect=post):
            llm.gemini("hi", "slow-model", ["fast-model"])
        self.assertEqual(llm._GEMINI_CHOSEN["m"], "fast-model")

    def test_non_404_errors_are_not_masked(self):
        with mock.patch.object(llm, "_post", side_effect=llm.LLMError("request failed (HTTP 403)")):
            with self.assertRaises(llm.LLMError) as cm:
                llm.gemini("hi", "any-model", ["x"])
        self.assertIn("403", str(cm.exception))

    def test_clear_error_when_no_model_is_usable(self):
        with mock.patch.object(llm, "_post", side_effect=llm.LLMError("request failed (HTTP 404)")), \
             mock.patch.object(llm, "gemini_models", return_value=["gemini-2.5-pro"]):
            with self.assertRaises(llm.LLMError) as cm:
                llm.gemini("hi", "old-model", [])
        self.assertIn("no usable Gemini model", str(cm.exception))


class ProviderChainTests(unittest.TestCase):
    CFG = {"provider": "gemini", "fallback_provider": "groq", "gemini_model": "m", "groq_model": "g"}

    def test_fallback_provider_answers_when_primary_fails(self):
        with mock.patch.object(llm, "gemini", side_effect=llm.LLMError("request failed (HTTP 503)")), \
             mock.patch.object(llm, "groq", return_value="from-groq"):
            self.assertEqual(llm.get_provider(self.CFG)("hi"), "from-groq")

    def test_both_failing_reports_both_reasons(self):
        with mock.patch.object(llm, "gemini", side_effect=llm.LLMError("gemini down")), \
             mock.patch.object(llm, "groq", side_effect=llm.LLMError("GROQ_API_KEY not set")):
            with self.assertRaises(llm.LLMError) as cm:
                llm.get_provider(self.CFG)("hi")
        self.assertIn("gemini: gemini down", str(cm.exception))
        self.assertIn("groq: GROQ_API_KEY not set", str(cm.exception))

    def test_no_fallback_configured_uses_primary_only(self):
        cfg = dict(self.CFG, fallback_provider="")
        with mock.patch.object(llm, "gemini", return_value="from-gemini"), \
             mock.patch.object(llm, "groq", side_effect=AssertionError("must not be called")):
            self.assertEqual(llm.get_provider(cfg)("hi"), "from-gemini")


class BudgetAndRedactionTests(unittest.TestCase):
    def tearDown(self):
        llm._BUDGET["deadline"] = None

    def test_exhausted_budget_stops_requests_immediately(self):
        llm.start_budget(-5)
        with mock.patch("urllib.request.urlopen", side_effect=AssertionError("must not call the network")):
            with self.assertRaises(llm.LLMError) as cm:
                llm._post("http://x", {}, {})
        self.assertIn("budget", str(cm.exception))

    def test_keys_are_redacted_from_error_text(self):
        with mock.patch.dict(os.environ, {"GEMINI_API_KEY": "SECRETKEY123456"}):
            self.assertEqual(llm._redact("bad key SECRETKEY123456 here"), "bad key *** here")

    def test_http_error_body_message_is_surfaced(self):
        import io
        import urllib.error
        err = urllib.error.HTTPError("http://x", 503, "Service Unavailable", {},
                                     io.BytesIO(b'{"error": {"code": 503, "message": "The model is overloaded."}}'))
        self.assertEqual(llm._fail_text(err, 0), "HTTP 503: The model is overloaded.")


class ThinkingAndHeaderTests(unittest.TestCase):
    @mock.patch.dict(os.environ, {"GEMINI_API_KEY": "fake-key-for-tests"})
    def test_thinking_is_switched_off_but_retried_without_if_rejected(self):
        bodies = []

        def post(url, body, headers, **kw):
            bodies.append(dict(body["generationConfig"]))
            if "thinkingConfig" in body["generationConfig"]:
                raise llm.LLMError("request failed (HTTP 400: thinking budget is not supported for this model)")
            return REPLY
        with mock.patch.object(llm, "_post", side_effect=post):
            out = llm._gemini_call("hi", "m", "fake-key-for-tests")
        self.assertEqual(out, '{"items": []}')
        self.assertIn("thinkingConfig", bodies[0])
        self.assertNotIn("thinkingConfig", bodies[1])

    def test_400_not_about_thinking_still_raises(self):
        with mock.patch.object(llm, "_post", side_effect=llm.LLMError("request failed (HTTP 400: API key not valid)")):
            with self.assertRaises(llm.LLMError):
                llm._gemini_call("hi", "m", "k")

    def test_requests_identify_themselves_not_python_urllib(self):
        seen = {}

        class Resp:
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def read(self): return b"{}"

        def fake_urlopen(req, timeout=0):
            seen["ua"] = req.get_header("User-agent")
            return Resp()
        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            llm._post("http://x", {}, {})
        self.assertIn("ai-daily-brief", seen["ua"])


class GroqTests(unittest.TestCase):
    def setUp(self):
        llm._GROQ_CHOSEN.clear()
        self._tmp = tempfile.TemporaryDirectory()
        patcher = mock.patch.object(llm, "STATE_PATH", Path(self._tmp.name) / "llm_state.json")
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self._tmp.cleanup)

    def test_rank_groq_prefers_capable_chat_models(self):
        ids = ["whisper-large-v3", "llama-3.1-8b-instant", "llama-3.3-70b-versatile", "openai/gpt-oss-120b",
               "meta-llama/llama-guard-4-12b", "playai-tts", "some-405b-giant"]
        ranked = llm.rank_groq(ids)
        self.assertEqual(ranked[0], "openai/gpt-oss-120b")
        self.assertEqual(ranked[1], "llama-3.3-70b-versatile")
        self.assertNotIn("whisper-large-v3", ranked)
        self.assertNotIn("meta-llama/llama-guard-4-12b", ranked)
        self.assertNotIn("playai-tts", ranked)

    @mock.patch.dict(os.environ, {"GROQ_API_KEY": "fake-groq-key-for-tests"})
    def test_retired_groq_model_falls_back_to_a_listed_one_and_is_remembered(self):
        reply = {"choices": [{"message": {"content": '{"items": []}'}}]}

        def post(url, body, headers, **kw):
            if body["model"] == "retired-model":
                raise llm.LLMError("request failed (HTTP 404: model decommissioned)")
            return reply
        with mock.patch.object(llm, "_post", side_effect=post), \
             mock.patch.object(llm, "groq_models", return_value=["llama-3.3-70b-versatile", "whisper-large-v3"]):
            out = llm.groq("hi", "retired-model", [])
        self.assertEqual(out, '{"items": []}')
        self.assertEqual(llm._load_state()["groq_model"], "llama-3.3-70b-versatile")

    def test_missing_groq_key_gives_clear_error(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(llm.LLMError) as cm:
                llm.groq("hi", "m", [])
        self.assertIn("GROQ_API_KEY not set", str(cm.exception))

    def test_each_provider_gets_its_own_time_budget(self):
        seen = {}

        def slow_gemini(prompt, model, fallbacks=()):
            llm.start_budget(-5)  # simulate Gemini using up all of its time
            raise llm.LLMError("request failed (Timeout: AI time budget used up)")

        def fast_groq(prompt, model, fallbacks=()):
            seen["remaining"] = llm._remaining()
            return "from-groq"
        cfg = {"provider": "gemini", "fallback_provider": "groq", "gemini_model": "g", "groq_model": "q",
               "time_budget_seconds": 150}
        with mock.patch.object(llm, "gemini", side_effect=slow_gemini), mock.patch.object(llm, "groq", side_effect=fast_groq):
            self.assertEqual(llm.get_provider(cfg)("hi"), "from-groq")
        self.assertGreater(seen["remaining"], 100)
        llm._BUDGET["deadline"] = None


class CheckerRoleTests(unittest.TestCase):
    CFG = {"provider": "groq", "fallback_provider": "gemini", "checker_provider": "gemini",
           "checker_fallback_provider": "groq", "gemini_model": "g", "groq_model": "q"}

    def test_writer_uses_groq_first_and_checker_uses_gemini_first(self):
        order = []
        with mock.patch.object(llm, "gemini", side_effect=lambda *a, **k: order.append("gemini") or "g"), \
             mock.patch.object(llm, "groq", side_effect=lambda *a, **k: order.append("groq") or "q"):
            llm.get_provider(self.CFG)("hi")
            llm.get_provider(self.CFG, role="checker")("hi")
        self.assertEqual(order, ["groq", "gemini"])

    def test_checker_falls_back_to_the_other_provider(self):
        with mock.patch.object(llm, "gemini", side_effect=llm.LLMError("request failed (HTTP 503)")), \
             mock.patch.object(llm, "groq", return_value="from-groq"):
            self.assertEqual(llm.get_provider(self.CFG, role="checker")("hi"), "from-groq")

    def test_checker_defaults_to_writer_settings_when_not_configured(self):
        cfg = {"provider": "groq", "fallback_provider": "gemini", "gemini_model": "g", "groq_model": "q"}
        with mock.patch.object(llm, "groq", return_value="from-groq"), \
             mock.patch.object(llm, "gemini", side_effect=AssertionError("should not be called")):
            self.assertEqual(llm.get_provider(cfg, role="checker")("hi"), "from-groq")

    def test_provider_none_means_no_checker_either(self):
        self.assertIsNone(llm.get_provider({"provider": "none"}, role="checker"))


class KeyHandlingTests(unittest.TestCase):
    def test_missing_key_gives_clear_error(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(llm.LLMError) as cm:
                llm.gemini("hi", "m", [])
        self.assertIn("GEMINI_API_KEY not set", str(cm.exception))

    def test_provider_none_returns_no_callable(self):
        self.assertIsNone(llm.get_provider({"provider": "none"}))


if __name__ == "__main__":
    unittest.main()
