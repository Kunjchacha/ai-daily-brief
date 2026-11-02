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
