"""Week-one formats: the deck bank, the chart engine (with canned data), and the slide types. Offline."""
import datetime as dt
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import carousel, charts, formats, pack, render  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
NOW = dt.datetime(2026, 11, 5, 8, 0, tzinfo=dt.timezone.utc)
VALID = {"kicker", "title", "body", "items", "ordered", "tick", "code", "head", "rows", "flow", "options", "compare", "left", "right", "svg"}


class DeckBankTests(unittest.TestCase):
    def setUp(self):
        self.bank = json.load(open(ROOT / "config" / "decks.json", encoding="utf-8"))

    def test_ids_are_unique_and_every_kind_has_decks(self):
        ids = [d["id"] for d in self.bank]
        self.assertEqual(len(ids), len(set(ids)))
        for kind in formats.DECK_KINDS:
            self.assertTrue([d for d in self.bank if d["kind"] == kind], kind)

    def test_every_deck_is_complete_short_and_safe(self):
        for d in self.bank:
            self.assertTrue(d["hook"] and d["ask"].endswith("?") and d["points"] and d["slides"], d["id"])
            self.assertLessEqual(len(d["hook"]), 120, d["id"])
            self.assertTrue(1 <= len(d["slides"]) <= 8, d["id"])
            if d["url"]:
                self.assertTrue(d["url"].startswith("https://"), d["id"])
            for s in d["slides"]:
                self.assertTrue(set(s) <= VALID, (d["id"], set(s) - VALID))
                self.assertTrue(s["title"], d["id"])
                for key in ("items", "flow", "options"):
                    for line in s.get(key, []):
                        self.assertLess(len(line), 190, (d["id"], line[:40]))

    def test_a_quiz_caption_never_gives_the_answer(self):
        for d in [d for d in self.bank if d["kind"] == "quiz"]:
            text = " ".join(d["points"] + [d["hook"]]).lower()
            self.assertNotIn("answer:", text)
            self.assertTrue(any(w in " ".join(d["points"]).lower() for w in ("answer", "fix", "next slide")), "tell readers where to look")

    def test_every_deck_renders_as_slides_and_a_short_caption(self):
        for d in self.bank:
            it = formats.deck(set(), d["kind"], [d])
            issue = {"date": "2026-11-05", "edition": "morning", "key": "2026-11-05-morning", "format": d["kind"], "items": [it]}
            slides = carousel.slides_for(issue)
            self.assertGreaterEqual(len(slides), 3)
            html = carousel.deck_html(slides, "AI Daily Brief")
            self.assertEqual(html.count("class='slide'"), len(slides))
            post = render.linkedin_post(issue, "AI Daily Brief", ["#AI"], 2800)
            self.assertIn("Swipe", post)
            self.assertLess(len(post), 800, d["id"])

    def test_decks_rotate_within_a_kind(self):
        a = formats.deck(set(), "quiz")
        b = formats.deck({a["bank_id"]}, "quiz")
        self.assertNotEqual(a["bank_id"], b["bank_id"])


def hf(models):
    return lambda url: json.dumps(models).encode()


class ChartTests(unittest.TestCase):
    MODELS = [{"id": f"org/model-{i}", "downloads": 1000 * (9 - i), "pipeline_tag": "text-generation" if i % 2 else "image-to-text",
               "tags": ["license:mit" if i % 3 else "license:other"]} for i in range(8)]

    def test_bar_chart_draws_every_row_and_escapes_text(self):
        svg = charts.bar_svg(["a<b", "c"], [5, 1], " models")
        self.assertIn("a&lt;b", svg)
        self.assertIn("5 models", svg)
        self.assertIn("1 model<", svg)

    def test_models_chart_headline_is_built_only_from_the_data(self):
        c = charts.models_downloads(NOW, hf(self.MODELS))
        self.assertIn("org/model-0", c["hook"])
        self.assertIn("9,000", c["hook"])
        self.assertTrue(c["slides"][0]["svg"].startswith("<svg"))
        self.assertIn("Does not show", c["slides"][1]["right"]["head"])
        self.assertIn("fetched 05 Nov 2026", c["source_note"])

    def test_chart_returns_none_when_the_data_is_thin(self):
        self.assertIsNone(charts.models_downloads(NOW, hf(self.MODELS[:3])))

    def test_licence_chart_does_not_call_other_a_licence_name(self):
        many = [{"id": f"o/m{i}", "tags": ["license:other"]} for i in range(40)]
        c = charts.licences(NOW, hf(many))
        self.assertIn("custom or 'other' licence", c["hook"])

    def test_arxiv_weekly_computes_the_change_from_the_counts(self):
        counts = iter([100, 110, 120, 130, 140, 150, 160, 200])
        fetch = lambda url: f"<feed><opensearch:totalResults xmlns:opensearch='x'>{next(counts)}</opensearch:totalResults></feed>".encode()
        c = charts.arxiv_weekly(NOW, fetch)
        self.assertIn("200", c["hook"])
        self.assertIn("up 25%", c["hook"])

    def test_chart_format_falls_through_when_a_source_fails(self):
        calls = []

        def fetch(url):
            calls.append(url)
            if "huggingface.co/api/models" in url and "limit=8" in url:
                raise OSError("down")
            return json.dumps(self.MODELS * 6).encode()

        it = formats.chart(NOW, fetch)
        self.assertIsNotNone(it)
        self.assertEqual(it["kind"], "data")
        self.assertTrue(it["slides"][0]["svg"])


class PlanTests(unittest.TestCase):
    def test_flagship_by_weekday_uses_the_week_one_formats(self):
        seen = {pack.plan(dt.date(2026, 11, 2) + dt.timedelta(days=d))["morning"][0] for d in range(7)}
        self.assertEqual(seen, {"workflow", "chart", "myth", "infographic", "paper", "comparison", "quiz"})


if __name__ == "__main__":
    unittest.main()
