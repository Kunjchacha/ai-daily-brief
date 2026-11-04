"""ops/ensure_draft.py: starts the draft job only when it is missing and not already running. Offline."""
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "ops"))

import ensure_draft as ed  # noqa: E402


class EnsureTests(unittest.TestCase):
    def run_ensure(self, exists=(False, True), running=False, dispatch_status=204):
        calls = []
        seq = iter(exists)

        def fake_call(path, token=None, body=None):
            calls.append((path, body))
            return dispatch_status, None

        with mock.patch.object(ed, "draft_exists", side_effect=lambda d: next(seq)), \
             mock.patch.object(ed, "run_in_progress", return_value=running), \
             mock.patch.object(ed, "call", side_effect=fake_call), mock.patch.object(ed.time, "sleep"):
            return ed.ensure("2026-11-04", "tok", wait_seconds=60), calls

    def test_existing_draft_starts_nothing(self):
        result, calls = self.run_ensure(exists=(True,))
        self.assertIn("already", result)
        self.assertEqual(calls, [])

    def test_missing_draft_starts_one_run_without_force(self):
        result, calls = self.run_ensure()
        self.assertEqual(len(calls), 1)
        path, body = calls[0]
        self.assertTrue(path.endswith("/dispatches"))
        self.assertEqual(body, {"ref": "main"})  # no 'force' input: it can never rebuild an existing issue
        self.assertIn("now on GitHub", result)

    def test_run_already_in_progress_is_not_started_again(self):
        result, calls = self.run_ensure(running=True)
        self.assertEqual(calls, [])
        self.assertIn("in progress", result)

    def test_rejected_token_is_reported_loudly(self):
        result, _ = self.run_ensure(exists=(False,), dispatch_status=401)
        self.assertIn("TOKEN REJECTED", result)

    def test_other_failure_is_reported(self):
        result, _ = self.run_ensure(exists=(False,), dispatch_status=500)
        self.assertIn("FAILED", result)


if __name__ == "__main__":
    unittest.main()
