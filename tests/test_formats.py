"""Post formats (spotlight, research, explainer, question), the pack plan, and approval of one-item issues. Offline."""
import datetime as dt
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import approve as approve_mod, formats, pack, render  # noqa: E402

NOW = dt.datetime(2026, 11, 5, 8, 0, tzinfo=dt.timezone.utc)


def repo(name, stars=500, lic="MIT", desc="An open-source toolkit for building local AI agents that run on your laptop.", **kw):
    r = {"full_name": name, "html_url": f"https://github.com/{name}", "stargazers_count": stars, "language": "Python",
         "license": {"spdx_id": lic} if lic else None, "description": desc, "created_at": "2026-11-01T00:00:00Z",
         "fork": False, "archived": False}
    r.update(kw)
    return r


def fetch_repos(*repos):
    return lambda url: json.dumps({"items": list(repos)}).encode()


class RepoTests(unittest.TestCase):
    def test_picks_the_biggest_clean_repo_and_states_its_facts(self):
        it = formats.repo_spotlight(NOW, set(), fetch_repos(repo("a/small", 200), repo("a/big", 900)))
        self.assertEqual(it["headline"], "a/big")
        self.assertIn("900 stars", it["details"])
        self.assertIn("MIT licence", it["details"])

    def test_skips_no_licence_forks_spam_non_english_and_repeats(self):
        bad = [repo("a/nolic", 9000, lic=None), repo("a/fork", 8000, fork=True), repo("a/crypto-bot", 7000),
               repo("a/short", 6000, desc="tiny"), repo("a/cn", 5000, desc="一个用于构建本地人工智能代理的开源工具包，可以在笔记本电脑上运行"),
               repo("a/seen", 4000)]
        ok = repo("a/ok", 300)
        it = formats.repo_spotlight(NOW, {"https://github.com/a/seen"}, fetch_repos(*bad, ok))
        self.assertEqual(it["headline"], "a/ok")

    def test_returns_none_when_nothing_suitable(self):
        self.assertIsNone(formats.repo_spotlight(NOW, set(), fetch_repos(repo("a/nolic", 900, lic=None))))


class ModelTests(unittest.TestCase):
    def test_needs_a_real_licence_and_uses_the_right_article(self):
        data = [{"id": "x/other", "downloads": 90000, "likes": 5, "pipeline_tag": "text-generation", "tags": ["license:other"]},
                {"id": "x/good", "downloads": 90000, "likes": 5, "pipeline_tag": "automatic-speech-recognition",
                 "tags": ["license:apache-2.0"], "createdAt": "2026-11-01T00:00:00Z"}]
        it = formats.model_spotlight(NOW, set(), lambda u: json.dumps(data).encode())
        self.assertEqual(it["headline"], "x/good")
        self.assertTrue(it["summary"].startswith("An automatic speech recognition model"))


ABSTRACT = ("We study routing between language models. " * 3 + "We show that a small router improves accuracy by 12% on "
            "three benchmarks while cutting cost. " + "The code is released. " * 4)


def papers(upvotes=40):
    return lambda u: json.dumps([{"paper": {"id": "2611.00001", "title": "Routing  models", "summary": ABSTRACT, "upvotes": upvotes,
                                            "authors": [{}, {}], "publishedAt": "2026-11-04T00:00:00Z"}}]).encode()


class PaperTests(unittest.TestCase):
    def test_ai_summary_must_quote_the_abstract_and_add_no_new_numbers(self):
        good = json.dumps({"plain": "The authors built a router between models. They report better accuracy at lower cost.",
                           "result_quote": "We show that a small router improves accuracy by 12% on three benchmarks while cutting cost."})
        it = formats.paper_of_the_day(NOW, set(), lambda p: good, papers())
        self.assertEqual(it["mode"], "llm")
        bad_quote = json.dumps({"plain": "The authors built a router between models and report gains.", "result_quote": "It is magic."})
        self.assertEqual(formats.paper_of_the_day(NOW, set(), lambda p: bad_quote, papers())["mode"], "extractive")
        new_number = json.dumps({"plain": "The authors report a 99% improvement across many tests and more.",
                                 "result_quote": "We show that a small router improves accuracy by 12% on three benchmarks while cutting cost."})
        self.assertEqual(formats.paper_of_the_day(NOW, set(), lambda p: new_number, papers())["mode"], "extractive")

    def test_works_without_an_ai_and_skips_unpopular_or_used_papers(self):
        it = formats.paper_of_the_day(NOW, set(), None, papers())
        self.assertEqual(it["mode"], "extractive")
        self.assertIn("improves accuracy", it["evidence_quote"])
        self.assertIsNone(formats.paper_of_the_day(NOW, set(), None, papers(upvotes=1)))
        self.assertIsNone(formats.paper_of_the_day(NOW, {"https://arxiv.org/abs/2611.00001"}, None, papers()))


class BankTests(unittest.TestCase):
    def test_banks_rotate_and_every_explainer_has_a_https_source(self):
        bank = [{"id": "a", "title": "A", "body": "b", "source": "S", "url": "https://x.org"}, {"id": "b", "title": "B", "body": "b",
                                                                                              "source": "S", "url": "https://y.org"}]
        self.assertEqual(formats.explainer(set(), bank)["bank_id"], "a")
        self.assertEqual(formats.explainer({"a"}, bank)["bank_id"], "b")
        real = json.load(open(Path(__file__).resolve().parent.parent / "config" / "explainers.json"))
        self.assertTrue(all(e["url"].startswith("https://") and len(e["body"]) < 600 for e in real))

    def test_question_has_no_source_and_no_facts(self):
        q = formats.question(set(), [{"id": "q", "question": "Which tool?", "context": "Answer briefly."}])
        self.assertEqual(q["url"], "")
        self.assertEqual(q["kind"], "question")


class PlanTests(unittest.TestCase):
    def test_every_day_has_four_slots_and_a_fallback_that_cannot_run_dry(self):
        for d in range(7):
            p = pack.plan(dt.date(2026, 11, 2) + dt.timedelta(days=d))
            self.assertEqual(set(p), set(pack.SLOTS))
            for fmts in p.values():
                self.assertIn(fmts[-1], ("explainer", "question"), "the last choice must be a bank that never runs out")


class SingleFormatApprovalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        for d in ("drafts", "data/issues"):
            (self.tmp / d).mkdir(parents=True)

    def make(self, fmt, item, slot="midday"):
        from pipeline import run as runmod
        s = {"brand": "AI Daily Brief", "tagline": "t", "linkedin": {"hashtags": ["#AI"], "max_chars": 2800},
             "site": {}, "min_items": 3, "facts_only": {}}
        with mock.patch.object(runmod, "ISSUES", self.tmp / "data" / "issues"), mock.patch.object(runmod, "DRAFTS", self.tmp / "drafts"):
            pack.write_single(dt.date(2026, 11, 5), slot, fmt, item, s, NOW)
        return s

    def approve(self, s):
        with mock.patch.object(approve_mod, "DRAFTS", self.tmp / "drafts"), mock.patch.object(approve_mod, "ISSUES", self.tmp / "data" / "issues"):
            return approve_mod.approve("2026-11-05-midday", s)

    def test_one_item_issue_approves_with_a_single_item_and_no_why_line(self):
        it = formats.repo_spotlight(NOW, set(), fetch_repos(repo("a/big", 900)))
        s = self.make("repo", it)
        f = self.tmp / "drafts" / "2026-11-05-midday-issue.md"
        self.assertEqual(self.approve(s), 1, "still a DRAFT: must refuse")
        f.write_text(f.read_text().replace("Status: DRAFT", "Status: APPROVED"))
        self.assertEqual(self.approve(s), 0)
        final = (self.tmp / "drafts" / "2026-11-05-midday-linkedin-final.txt").read_text()
        self.assertIn("Open-source spotlight", final)
        self.assertIn("https://github.com/a/big", final)
        self.assertNotIn("Why it matters", final)

    def test_question_approves_without_a_source_link(self):
        s = self.make("question", formats.question(set(), [{"id": "q", "question": "Which tool?", "context": "Answer briefly."}]))
        f = self.tmp / "drafts" / "2026-11-05-midday-issue.md"
        f.write_text(f.read_text().replace("Status: DRAFT", "Status: APPROVED"))
        self.assertEqual(self.approve(s), 0)

    def test_excluding_the_only_item_is_refused(self):
        s = self.make("explainer", formats.explainer(set(), [{"id": "a", "title": "A", "body": "text", "source": "S", "url": "https://x.org"}]))
        f = self.tmp / "drafts" / "2026-11-05-midday-issue.md"
        f.write_text(f.read_text().replace("Status: DRAFT", "Status: APPROVED").replace("Include: yes", "Include: no"))
        self.assertEqual(self.approve(s), 1)


if __name__ == "__main__":
    unittest.main()
