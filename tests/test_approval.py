"""Facts-only gate and the human approval step. Offline."""
import datetime as dt
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import approve, publish, verify  # noqa: E402
from pipeline.common import settings  # noqa: E402

FACTS = settings()["facts_only"]
SRC_TEXT = "Lab releases Model X. The lab released Model X on Monday. It scores 78 percent on a benchmark."


def it(**kw):
    base = {"headline": "Lab releases Model X", "summary": "The lab released Model X on Monday.",
            "why_it_matters": "It gives developers a new option.", "mode": "llm", "kind": "announced",
            "evidence_quote": "The lab released Model X on Monday", "source_text": SRC_TEXT,
            "url": "https://example.com/a", "source": "Test Lab", "score": 1.0,
            "published": "2026-11-03T03:00:00+00:00"}
    base.update(kw)
    return base


class FactsGateTests(unittest.TestCase):
    def test_confirmed_fact_passes(self):
        self.assertEqual(verify.check_facts(it(), FACTS), [])

    def test_rumour_and_opinion_are_rejected(self):
        for kind in ("rumour", "opinion", ""):
            self.assertTrue(verify.check_facts(it(kind=kind), FACTS), kind)

    def test_quote_must_be_in_source(self):
        self.assertTrue(verify.check_facts(it(evidence_quote="Lab will ship Model Y next week for sure"), FACTS))
        self.assertTrue(verify.check_facts(it(evidence_quote=""), FACTS))

    def test_hedged_wording_is_rejected(self):
        self.assertTrue(verify.check_facts(it(summary="The lab reportedly released Model X."), FACTS))
        self.assertTrue(verify.check_facts(it(headline="Lab could release Model X"), FACTS))

    def test_disabled_gate_does_nothing(self):
        self.assertEqual(verify.check_facts(it(kind="rumour"), {"enabled": False}), [])


class ApprovalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "drafts").mkdir()
        (self.tmp / "issues").mkdir()
        items = [it(headline=f"Lab {n} releases Model {n}", url=f"https://example.com/{n}") for n in "ABCD"]
        self.issue = {"date": "2026-11-03", "status": "ready_for_review", "mode": "llm", "brand": "AI Daily Brief",
                      "items": items, "report": [], "errors": [], "notes": [], "created": "2026-11-03T06:00:00+00:00"}
        (self.tmp / "issues" / "2026-11-03.json").write_text(json.dumps(self.issue), encoding="utf-8")
        self.md = self.tmp / "drafts" / "2026-11-03-issue.md"
        self.md.write_text(approve.render_issue_md(self.issue, "AI Daily Brief"), encoding="utf-8")
        p1 = mock.patch.object(approve, "DRAFTS", self.tmp / "drafts")
        p2 = mock.patch.object(approve, "ISSUES", self.tmp / "issues")
        p1.start(); p2.start()
        self.addCleanup(p1.stop); self.addCleanup(p2.stop)
        self.s = settings()

    def _status(self):
        return json.loads((self.tmp / "issues" / "2026-11-03.json").read_text())["status"]

    def _edit(self, old, new, count=-1):
        self.md.write_text(self.md.read_text().replace(old, new, count), encoding="utf-8")

    def test_round_trip_parses_every_item(self):
        parsed = approve.parse_issue_md(self.md.read_text())
        self.assertEqual(parsed["status"], "DRAFT")
        self.assertEqual(len(parsed["items"]), 4)
        self.assertEqual(parsed["items"][0]["Include"], "yes")

    def test_draft_is_refused(self):
        self.assertEqual(approve.approve("2026-11-03", self.s), 1)
        self.assertEqual(self._status(), "ready_for_review")
        self.assertFalse((self.tmp / "drafts" / "2026-11-03-linkedin-final.txt").exists())

    def test_approved_builds_final_text(self):
        self._edit("Status: DRAFT", "Status: APPROVED", 1)
        self.assertEqual(approve.approve("2026-11-03", self.s), 0)
        self.assertEqual(self._status(), "approved")
        self.assertTrue((self.tmp / "drafts" / "2026-11-03-linkedin-final.txt").exists())
        self.assertTrue(approve.is_approved("2026-11-03"))

    def test_include_no_removes_item_and_too_few_is_refused(self):
        self._edit("Status: DRAFT", "Status: APPROVED", 1)
        self._edit("\nInclude: yes", "\nInclude: no", 1)
        self.assertEqual(approve.approve("2026-11-03", self.s), 0)  # 3 left = minimum
        final = (self.tmp / "drafts" / "2026-11-03-linkedin-final.txt").read_text()
        self.assertNotIn("Lab A releases", final)
        self._edit("\nInclude: yes", "\nInclude: no", 1)
        self.assertEqual(approve.approve("2026-11-03", self.s), 1)  # only 2 left

    def test_placeholder_blocks_approval(self):
        self._edit("Status: DRAFT", "Status: APPROVED", 1)
        self._edit("Why it matters: It gives developers a new option.", "Why it matters: [ADD YOUR LINE]", 1)
        self.assertEqual(approve.approve("2026-11-03", self.s), 1)
        self.assertEqual(self._status(), "ready_for_review")

    def test_rumour_kind_is_excluded_even_if_approved(self):
        self._edit("Status: DRAFT", "Status: APPROVED", 1)
        self._edit("Kind: announced", "Kind: rumour", 1)
        self.assertEqual(approve.approve("2026-11-03", self.s), 0)
        final = (self.tmp / "drafts" / "2026-11-03-linkedin-final.txt").read_text()
        self.assertNotIn("Lab A releases", final)

    def test_publish_refuses_unapproved(self):
        with mock.patch.object(publish, "ISSUES", self.tmp / "issues"), mock.patch.object(publish, "SITE", self.tmp / "site"):
            self.assertEqual(publish.publish("2026-11-03"), 1)
            self.assertFalse((self.tmp / "site").exists())


if __name__ == "__main__":
    unittest.main()
