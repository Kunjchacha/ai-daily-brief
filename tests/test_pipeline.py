"""Offline tests: no network, no API keys. Run from the project folder:
    python3 -m unittest discover -s tests -v
"""
import datetime as dt
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import collect, rank, render, verify, write  # noqa: E402
from pipeline.common import UTC, canonical_url  # noqa: E402

NOW = dt.datetime(2026, 11, 3, 6, 0, tzinfo=UTC)
SRC = {"id": "t", "name": "Test Lab", "authority": 5}

RSS = b"""<?xml version="1.0"?><rss version="2.0"><channel>
<item><title>Lab releases Model X</title><link>https://example.com/a?utm_source=x</link>
<description>&lt;p&gt;The lab released Model X on Monday. It scores 78 percent on a benchmark.&lt;/p&gt;</description>
<pubDate>Tue, 03 Nov 2026 03:00:00 GMT</pubDate></item>
<item><title>Old story</title><link>https://example.com/old</link><description>x</description>
<pubDate>Mon, 01 Jan 2024 03:00:00 GMT</pubDate></item></channel></rss>"""

ATOM = b"""<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Atom story</title>
<link rel="alternate" href="https://example.com/atom"/><summary>Atom summary text.</summary>
<published>2026-11-03T02:00:00Z</published></entry></feed>"""

EVIL = b"""<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "aaaa">]><rss><channel><item><title>&a;</title></item></channel></rss>"""


def item(**kw):
    base = {"id": 1, "headline": "Lab releases Model X", "summary": "The lab released Model X on Monday.",
            "why_it_matters": "It sets a new reference point for others.", "mode": "llm", "url": "https://example.com/a",
            "source_text": "Lab releases Model X. The lab released Model X on Monday. It scores 78 percent on a benchmark."}
    base.update(kw)
    return base


class CollectTests(unittest.TestCase):
    def test_parse_rss_strips_html_and_tracking(self):
        items = collect.parse_feed(RSS, SRC)
        self.assertEqual(len(items), 2)
        self.assertIn("Model X", items[0]["text"])
        self.assertNotIn("<p>", items[0]["text"])
        self.assertEqual(canonical_url(items[0]["url"]), "https://example.com/a")

    def test_gzip_responses_are_decompressed_and_capped(self):
        import gzip
        self.assertEqual(collect.gunzip_if_needed(gzip.compress(RSS)), RSS)
        self.assertEqual(collect.gunzip_if_needed(RSS), RSS)
        bomb = gzip.compress(b"a" * (collect.MAX_BYTES + 10))
        with self.assertRaises(ValueError):
            collect.gunzip_if_needed(bomb)

    def test_parse_atom(self):
        items = collect.parse_feed(ATOM, SRC)
        self.assertEqual(items[0]["url"], "https://example.com/atom")

    def test_non_http_links_are_dropped(self):
        feed = (b'<?xml version="1.0"?><rss version="2.0"><channel>'
                b'<item><title>Bad</title><link>javascript:alert(1)</link><description>x</description></item>'
                b'<item><title>Local</title><link>file:///etc/passwd</link><description>x</description></item>'
                b'<item><title>Good</title><link>https://example.com/ok</link><description>x</description></item>'
                b'</channel></rss>')
        self.assertEqual([i["title"] for i in collect.parse_feed(feed, SRC)], ["Good"])

    def test_entity_declarations_are_refused(self):
        with self.assertRaises(ValueError):
            collect.parse_feed(EVIL, SRC)

    def test_collect_filters_old_and_survives_failures(self):
        def fetcher(url):
            if "bad" in url:
                raise OSError("boom")
            return RSS
        srcs = [dict(SRC, id="a", type="rss", url="http://a"), dict(SRC, id="b", type="rss", url="http://bad")]
        items, errors = collect.collect(srcs, 36, 15, now=NOW, fetcher=fetcher)
        self.assertEqual([i["title"] for i in items], ["Lab releases Model X"])
        self.assertEqual(errors[0]["source"], "b")


class RankTests(unittest.TestCase):
    def mk(self, title, url, auth, src):
        return {"title": title, "url": url, "canonical": canonical_url(url), "text": title, "authority": auth,
                "source": src, "published": NOW.isoformat(), "points": 0, "filter": False}

    def test_one_source_cannot_dominate(self):
        items = []
        titles = ["Robotics arm learns to fold laundry", "Chip maker unveils faster inference accelerator",
                  "Court rules on training data copyright", "Benchmark shows reasoning gains in small models"]
        for n, t in enumerate(titles):
            x = self.mk(t, f"https://l.com/{n}", 5, "Lab")
            x["text"] = "Body text that is long enough to count as substance. " * 4
            items.append(x)
        out = rank.rank(items, NOW, 36, 14, 9, dt.date(2026, 11, 3), min_text=120, per_source=2)
        self.assertEqual(len(out), 2)

    def test_same_story_from_two_sources_merges_and_scores_higher(self):
        body = "Body text that is long enough to count as substance. " * 4
        a = self.mk("Lab releases Model X for developers", "https://a.com/1", 5, "Lab")
        b = self.mk("Lab releases Model X for developers today", "https://b.com/2", 3, "News")
        c = self.mk("Completely different robotics story here", "https://c.com/3", 5, "Other")
        for x in (a, b, c):
            x["text"] = body
        out = rank.rank([a, b, c], NOW, 36, 14, 5, dt.date(2026, 11, 3))
        self.assertEqual(len(out), 2)
        merged = [x for x in out if x["also"]][0]
        self.assertEqual(merged["also"], ["News"])

    def test_deny_patterns_and_thin_stories_are_dropped(self):
        podcast = self.mk("Weekly AI podcast episode 12", "https://p.com/1", 5, "Pod")
        podcast["text"] = "x" * 300
        thin = self.mk("A bare link with no text", "https://t.com/1", 5, "Thin")
        good = self.mk("Lab ships a new reasoning model", "https://g.com/1", 5, "Lab")
        good["text"] = "The lab shipped a new reasoning model with longer context. " * 4
        out = rank.rank([podcast, thin, good], NOW, 36, 14, 5, dt.date(2026, 11, 3), min_text=120,
                        deny=[r"\bpodcast\b"])
        self.assertEqual([c["lead"]["title"] for c in out], ["Lab ships a new reasoning model"])

    def test_non_ai_items_are_filtered_when_flagged(self):
        x = self.mk("Local council approves new car park", "https://x.com/1", 3, "Gen")
        x["filter"] = True
        self.assertEqual(rank.rank([x], NOW, 36, 14, 5, dt.date(2026, 11, 3)), [])


class WriteTests(unittest.TestCase):
    def test_parse_fenced_json(self):
        raw = '```json\n{"items":[{"id":1,"headline":"H","summary":"S","why_it_matters":"W"}]}\n```'
        self.assertEqual(write.parse_results(raw)[1]["headline"], "H")

    def test_extractive_does_not_repeat_the_headline(self):
        c = {"lead": {"title": "Big news today", "text": "Big news today. The detail sentence follows. Another one."}}
        self.assertEqual(write.extractive(c)["summary"], "The detail sentence follows. Another one.")

    def test_extractive_fallback_needs_human_line(self):
        c = {"lead": {"title": "T", "text": "First sentence. Second sentence. Third sentence."}}
        out = write.extractive(c)
        self.assertEqual(out["summary"], "First sentence. Second sentence.")
        self.assertTrue(out["needs_human_line"])


class VerifyTests(unittest.TestCase):
    cfg = {"max_unsupported_names": 1, "check_links": False}

    def run_verify(self, it):
        kept, report = verify.verify([it], self.cfg, link_checker=lambda u: (True, "200"))
        return kept, report

    def test_faithful_item_passes(self):
        kept, _ = self.run_verify(item())
        self.assertEqual(len(kept), 1)

    def test_false_number_is_rejected(self):
        kept, rep = self.run_verify(item(summary="The lab released Model X and it scores 92 percent."))
        self.assertEqual(kept, [])
        self.assertIn("number not in source: 92", rep[0]["problems"])

    def test_invented_names_are_rejected(self):
        kept, rep = self.run_verify(item(summary="The lab released Model X after a deal with Contoso and Fabrikam."))
        self.assertEqual(kept, [])
        self.assertTrue(any(p.startswith("names not in source") for p in rep[0]["problems"]))

    def test_invented_quote_is_rejected(self):
        kept, _ = self.run_verify(item(summary='The lead said "this changes everything for everyone" at launch.'))
        self.assertEqual(kept, [])

    def test_hype_is_rejected(self):
        kept, _ = self.run_verify(item(headline="Revolutionary Model X arrives"))
        self.assertEqual(kept, [])

    def test_dead_link_is_rejected(self):
        kept, rep = verify.verify([item()], {"max_unsupported_names": 1, "check_links": True},
                                  link_checker=lambda u: (False, "HTTP 404"))
        self.assertEqual(kept, [])
        self.assertIn("link failed: HTTP 404", rep[0]["problems"])

    def test_second_pass_can_drop_unsupported(self):
        provider = lambda p: json.dumps({"items": [{"id": 1, "supported": False, "reason": "claim not in source"}]})  # noqa: E731
        kept, rep = verify.verify([item()], self.cfg, provider=provider, second_pass=True,
                                  link_checker=lambda u: (True, "200"))
        self.assertEqual(kept, [])
        self.assertEqual(rep[0]["status"], "dropped")

    def test_second_pass_failure_is_a_warning_not_a_crash(self):
        def provider(p):
            raise RuntimeError("quota")
        kept, rep = verify.verify([item()], self.cfg, provider=provider, second_pass=True,
                                  link_checker=lambda u: (True, "200"))
        self.assertEqual(len(kept), 1)
        self.assertTrue(rep[0]["warnings"])


class RenderTests(unittest.TestCase):
    def issue(self, n=6):
        its = [dict(item(id=i, headline=f"Headline {i}", summary="S " * 100), also=[], source="Lab", url="https://e.com/%d" % i,
                    needs_human_line=False) for i in range(1, n + 1)]
        return {"date": "2026-11-03", "status": "ready_for_review", "mode": "llm", "items": its, "report": [], "errors": [], "notes": []}

    def test_linkedin_post_respects_limit_and_has_disclosure(self):
        text = render.linkedin_post(self.issue(), "AI Daily Brief", ["#AI"], 1500)
        self.assertLessEqual(len(text), 1500)
        self.assertIn("AI-assisted, human-reviewed", text)

    def test_placeholder_shown_when_line_missing(self):
        iss = self.issue(1)
        iss["items"][0]["why_it_matters"] = ""
        self.assertIn(render.PLACEHOLDER, render.linkedin_post(iss, "B", ["#AI"], 3000))

    def test_page_escapes_html(self):
        iss = self.issue(1)
        iss["items"][0]["headline"] = "<script>alert(1)</script>"
        self.assertNotIn("<script>", render.issue_page(iss, "B", "t"))


if __name__ == "__main__":
    unittest.main()
