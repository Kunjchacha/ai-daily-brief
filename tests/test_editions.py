"""Two issues a day: file keys, headings, no repeated stories between editions, and the one-a-day guard. Offline."""
import datetime as dt
import email.utils
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import approve as approve_mod, common, run as runmod  # noqa: E402

SRC = {"id": "t", "name": "Test Lab", "authority": 5}
WORDS = [("quantum", "robotics"), ("satellite", "vision"), ("protein", "folding"), ("battery", "chemistry"), ("warehouse", "drones"),
         ("legal", "contracts"), ("music", "generation"), ("climate", "forecasting"), ("hospital", "triage"), ("chip", "packaging"),
         ("tutoring", "classrooms"), ("farming", "sensors"), ("translation", "dialects"), ("wildfire", "detection"),
         ("cybersecurity", "patching"), ("logistics", "routing")]


def feed(url):
    """Two stories per source (the issue keeps at most two per source), 8 sources: 16 distinct stories."""
    n = int(url.rsplit("s", 1)[1])
    pub = email.utils.format_datetime(dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=3))
    body = "The lab announced a new AI system and described how developers can use the model in production tools today. " * 3
    items = "".join(f"<item><title>{a.capitalize()} {b} gets an artificial intelligence upgrade</title><link>https://e.com/{k}</link>"
                    f"<description>{body} Details on {a} and {b} follow.</description><pubDate>{pub}</pubDate></item>"
                    for k, (a, b) in ((2 * n, WORDS[2 * n]), (2 * n + 1, WORDS[2 * n + 1])))
    return f"<?xml version='1.0'?><rss version='2.0'><channel>{items}</channel></rss>".encode()


class KeyTests(unittest.TestCase):
    def test_keys_and_labels(self):
        self.assertEqual(common.issue_key("2026-11-05"), "2026-11-05")
        self.assertEqual(common.issue_key("2026-11-05", "evening"), "2026-11-05-evening")
        self.assertEqual(common.edition_label({"edition": "morning"}), " (Morning edition)")
        self.assertEqual(common.edition_label({"date": "2026-11-04"}), "")  # original one-a-day issues keep their heading
        self.assertEqual(common.key_of({"date": "2026-11-04"}), "2026-11-04")
        self.assertEqual(common.key_of({"date": "2026-11-05", "key": "2026-11-05-evening"}), "2026-11-05-evening")


class TwoEditionRunTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        for d in ("drafts", "data/issues", "data/logs"):
            (self.tmp / d).mkdir(parents=True)
        (self.tmp / "data" / "usage.json").write_text("{}")

    def build(self, date, edition):
        t = self.tmp
        with mock.patch.object(runmod, "DRAFTS", t / "drafts"), mock.patch.object(approve_mod, "DRAFTS", t / "drafts"), \
             mock.patch.object(runmod, "ISSUES", t / "data" / "issues"), mock.patch.object(runmod, "LOGS", t / "data" / "logs"), \
             mock.patch.object(runmod, "USAGE", t / "data" / "usage.json"), \
             mock.patch("pipeline.rank.ROOT", t), \
             mock.patch.object(runmod, "load_json", side_effect=lambda rel: {"sources": [dict(SRC, id=f"s{n}", name=f"Lab {n}", type="rss", url=f"http://s{n}") for n in range(8)]}
                               if "sources" in rel else json.load(open(Path(runmod.ROOT) / rel))):
            return runmod.run(date, no_ai=True, offline=True, edition=edition, fetcher=feed,
                              link_checker=lambda u: (True, "ok"))

    def issue(self, key):
        return json.loads((self.tmp / "data" / "issues" / f"{key}.json").read_text())

    def test_evening_and_morning_are_separate_issues_with_different_stories(self):
        today = dt.date(2026, 11, 5)
        self.assertEqual(self.build(today, "evening"), 0)
        self.assertEqual(self.build(today + dt.timedelta(days=1), "morning"), 0)
        eve, mor = self.issue("2026-11-05-evening"), self.issue("2026-11-06-morning")
        self.assertEqual((eve["edition"], eve["key"], mor["edition"], mor["key"]), ("evening", "2026-11-05-evening", "morning", "2026-11-06-morning"))
        self.assertTrue(eve["items"] and mor["items"], "both editions need stories")
        self.assertFalse({i["url"] for i in eve["items"]} & {i["url"] for i in mor["items"]}, "a story must not appear in both")
        self.assertTrue((self.tmp / "drafts" / "2026-11-05-evening-issue.md").exists())
        self.assertIn("(Evening edition)", (self.tmp / "drafts" / "2026-11-05-evening-linkedin.txt").read_text())
        self.assertIn("(Morning edition)", (self.tmp / "drafts" / "2026-11-06-morning-linkedin.txt").read_text())

    def test_rebuilding_one_edition_does_not_count_itself_as_history(self):
        d = dt.date(2026, 11, 5)
        self.build(d, "evening")
        first = {i["url"] for i in self.issue("2026-11-05-evening")["items"]}
        (self.tmp / "drafts" / "2026-11-05-evening-review.md").unlink()
        self.build(d, "evening")
        self.assertEqual(first, {i["url"] for i in self.issue("2026-11-05-evening")["items"]})

    def test_an_existing_one_a_day_issue_blocks_an_edition_on_the_same_day(self):
        d = dt.date(2026, 11, 4)
        (self.tmp / "drafts" / "2026-11-04-review.md").write_text("x")
        self.assertEqual(self.build(d, "evening"), 0)
        self.assertFalse((self.tmp / "data" / "issues" / "2026-11-04-evening.json").exists())

    def test_an_approved_edition_is_never_overwritten(self):
        d = dt.date(2026, 11, 5)
        (self.tmp / "drafts" / "2026-11-05-evening-issue.md").write_text("# x\nStatus: APPROVED\n")
        self.build(d, "evening")
        self.assertFalse((self.tmp / "data" / "issues" / "2026-11-05-evening.json").exists())
        self.assertIn("APPROVED", (self.tmp / "drafts" / "2026-11-05-evening-issue.md").read_text())


if __name__ == "__main__":
    unittest.main()


class DroppedStoryTests(unittest.TestCase):
    def test_a_story_the_owner_dropped_does_not_come_back(self):
        from pipeline import rank
        t = Path(tempfile.mkdtemp())
        (t / "data" / "issues").mkdir(parents=True)
        (t / "data" / "issues" / "2026-11-04.json").write_text(json.dumps({
            "date": "2026-11-04", "items": [],
            "excluded": [{"headline": "Trump signs order rebranding AI", "url": "https://x.com/a?utm_source=z"}]}))
        with mock.patch.object(rank, "ROOT", t):
            urls, heads = rank.load_history(28, "2026-11-05-morning")
        self.assertIn("https://x.com/a", urls)
        self.assertTrue(any("trump" in h for h in heads))
