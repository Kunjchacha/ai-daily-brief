"""Review agent: article reading and the weighted approval score. Offline."""
import datetime as dt
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import review  # noqa: E402
from pipeline.common import UTC  # noqa: E402

REF = dt.datetime(2026, 11, 2, 14, 0, tzinfo=UTC)
SOURCES = [{"name": "OpenAI", "authority": 5}, {"name": "Some Blog", "authority": 2}, {"name": "The Outlet", "authority": 3}]
ARTICLE = ("OpenAI will honor a shared robots.txt signal to help website operators communicate their AI training preferences "
           "to participating providers. " * 4)
QUOTE = "OpenAI will honor a shared robots.txt signal to help website operators communicate"


def item(**kw):
    base = {"id": 1, "headline": "OpenAI to honour robots.txt", "summary": "OpenAI will respect a shared signal.",
            "source": "OpenAI", "url": "https://openai.com/a", "evidence_quote": QUOTE,
            "published": "2026-11-02T06:00:00+00:00"}
    base.update(kw)
    return base


def audit(*verdicts, primary=True):
    return {"primary": primary, "claims": [{"claim": "c", "verdict": v} for v in verdicts]}


class ScoreTests(unittest.TestCase):
    def test_clean_primary_story_scores_100(self):
        r = review.score_item(item(), ARTICLE, audit("supported", "supported"), SOURCES, REF)
        self.assertEqual((r["score"], r["grade"]), (100, "A"))

    def test_unsupported_claim_caps_at_60(self):
        r = review.score_item(item(), ARTICLE, audit("supported", "unsupported"), SOURCES, REF)
        self.assertLessEqual(r["score"], 60)

    def test_unreadable_article_cannot_reach_90(self):
        r = review.score_item(item(), None, audit("supported"), SOURCES, REF)
        self.assertLess(r["score"], 90)
        self.assertTrue(any("could not read" in x for x in r["reasons"]))

    def test_second_hand_blog_cannot_reach_90(self):
        r = review.score_item(item(source="Some Blog"), ARTICLE, audit("supported", primary=False), SOURCES, REF)
        self.assertEqual(r["grade"], "C")
        self.assertLessEqual(r["score"], 80)

    def test_partly_supported_or_missing_audit_stays_below_90(self):
        self.assertLess(review.score_item(item(), ARTICLE, audit("supported", "partly"), SOURCES, REF)["score"], 90)
        self.assertLess(review.score_item(item(), ARTICLE, None, SOURCES, REF)["score"], 90)

    def test_quote_missing_from_article_loses_points(self):
        r = review.score_item(item(evidence_quote="OpenAI will ship a robot next Tuesday for sure"), ARTICLE,
                              audit("supported"), SOURCES, REF)
        self.assertEqual(r["checks"]["quote"], 0)

    def test_old_story_loses_freshness(self):
        r = review.score_item(item(published="2026-10-20T06:00:00+00:00"), ARTICLE, audit("supported"), SOURCES, REF)
        self.assertEqual(r["checks"]["fresh"], 0)

    def test_bands(self):
        self.assertEqual([review.band(s) for s in (95, 90, 89, 70, 69, 0)],
                         ["recommend approve", "recommend approve", "review carefully", "review carefully",
                          "skip today", "skip today"])


class ReviewTests(unittest.TestCase):
    html_page = "<html><body><nav>menu</nav><script>x=1</script><p>" + ARTICLE + "</p></body></html>"

    def test_article_text_strips_scripts_and_nav(self):
        t = review.article_text(self.html_page)
        self.assertIn("robots.txt", t)
        self.assertNotIn("x=1", t)
        self.assertNotIn("menu", t)

    def test_blocked_page_is_reported_not_raised(self):
        def blocked(url):
            raise OSError("HTTP 403")
        text, note = review.fetch_article("https://x.com/a", blocked)
        self.assertIsNone(text)
        self.assertIn("could not read", note)
        self.assertIsNone(review.fetch_article("javascript:alert(1)")[0])

    def test_blocked_page_falls_back_to_the_feed_text(self):
        def blocked(url):
            raise OSError("HTTP 403")
        reply = json.dumps({"items": [{"id": 1, "primary": True, "claims": [{"claim": "c", "verdict": "supported"}]}]})
        out = review.review([item(source_text=ARTICLE[:200])], lambda p: reply, REF, SOURCES, fetcher=blocked)
        self.assertEqual(out["items"][0]["score"], 100)
        self.assertIn("feed text", out["items"][0]["article_note"])

    def test_issue_score_is_the_weakest_item(self):
        pages = {"https://openai.com/a": self.html_page, "https://x.com/b": "<p>short</p>"}
        reply = json.dumps({"items": [{"id": 1, "primary": True, "claims": [{"claim": "c", "verdict": "supported"}]}]})
        items = [item(), item(id=2, url="https://x.com/b")]
        out = review.review(items, lambda prompt: reply, REF, SOURCES, fetcher=lambda u: pages[u])
        self.assertEqual(out["items"][0]["score"], 100)
        self.assertEqual(out["score"], out["items"][1]["score"])
        self.assertEqual(out["verdict"], "skip today" if out["score"] < 70 else review.band(out["score"]))

    def test_audit_failure_lowers_score_without_crashing(self):
        def broken(prompt):
            raise RuntimeError("quota")
        out = review.review([item()], broken, REF, SOURCES, fetcher=lambda u: self.html_page)
        self.assertLess(out["score"], 90)

    def test_empty_issue_scores_zero(self):
        self.assertEqual(review.review([], None, REF, SOURCES)["score"], 0)


if __name__ == "__main__":
    unittest.main()
