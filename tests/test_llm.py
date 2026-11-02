"""Offline tests for the LLM adapter: no network, no real key."""
import os
import sys
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
