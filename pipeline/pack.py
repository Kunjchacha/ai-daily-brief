"""The daily pack: up to four posts a day, each in a slot, each approved by a person before it is queued.

Slots (IST): morning 08:00, midday 12:30, afternoon 17:00, evening 20:00. Each slot has a preferred format and fallbacks, so a
quiet news day still gives a full day of posts (news that is too thin falls back to an explainer or a question).

Run at 14:00 IST it builds this evening's issue and tomorrow's morning, midday and afternoon issues:
    python3 -m pipeline.pack                # today (IST)
    python3 -m pipeline.pack --force        # rebuild slots that already have a draft (never an APPROVED one)
Only drafts are written. Nothing is approved, queued or posted here.
"""
import argparse
import datetime as dt
import json
import sys

from adapters.llm import LLMError, get_provider

from . import formats, run as runmod
from .approve import is_approved, render_issue_md
from .common import UTC, issue_key, load_env, log, settings, today_ist
from .render import linkedin_post, preview_page, review_notes

SLOTS = ("morning", "midday", "afternoon", "evening")
SLOT_TIMES = {"morning": "08:00", "midday": "12:30", "afternoon": "17:00", "evening": "20:00"}


def plan(date):
    """Preferred formats per slot, in order of preference, for this weekday (Mon = 0)."""
    wd = date.weekday()
    return {"morning": ["news", "explainer"],
            "midday": (["repo", "model"] if wd in (0, 2, 4, 6) else ["model", "repo"]) + ["explainer"],
            "afternoon": (["paper", "explainer"] if wd in (0, 2, 4) else ["explainer", "paper"]) + ["question"],
            "evening": ["news", "question"]}


def history():
    """URLs (including ones the owner dropped) and bank ids already used in recent issues."""
    urls, ids = set(), set()
    for f in sorted(runmod.ISSUES.glob("*.json"))[-60:]:
        try:
            issue = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for it in list(issue.get("items", [])) + list(issue.get("excluded", [])):
            if it.get("url"):
                urls.add(it["url"])
            if it.get("bank_id"):
                ids.add(it["bank_id"])
    return urls, ids


def write_single(date, slot, fmt, item, s, now):
    """Write the draft files for a one-item issue, in the same layout as the news pipeline."""
    key = issue_key(date, slot)
    issue = {"date": str(date), "edition": slot, "key": key, "format": fmt, "status": "ready_for_review", "mode": item["mode"],
             "brand": s["brand"], "items": [item], "report": [], "errors": [], "notes": [f"slot {slot}, {SLOT_TIMES[slot]} IST"],
             "agent": None, "created": now.isoformat()}
    (runmod.ISSUES / f"{key}.json").write_text(json.dumps(issue, indent=1, ensure_ascii=False), encoding="utf-8")
    post = linkedin_post(issue, s["brand"], s["linkedin"]["hashtags"], s["linkedin"]["max_chars"])
    (runmod.DRAFTS / f"{key}-review.md").write_text(review_notes(issue), encoding="utf-8")
    (runmod.DRAFTS / f"{key}-linkedin.txt").write_text(post, encoding="utf-8")
    (runmod.DRAFTS / f"{key}-issue.md").write_text(render_issue_md(issue, s["brand"]), encoding="utf-8")
    (runmod.DRAFTS / f"{key}-preview.html").write_text(
        preview_page(issue, s["brand"], s["tagline"], post, s["site"].get("contact", "")), encoding="utf-8")


def get_checker(s, force):
    llm = s["llm"]
    try:
        if force or runmod._usage_get(str(today_ist())) < llm["max_llm_calls_per_day"]:
            return get_provider(llm)
    except LLMError as exc:
        log(f"pack: AI provider unavailable ({exc})")
    return None


def build_slot(date, slot, s, now, force=False, fetcher=None, provider=None):
    key = issue_key(date, slot)
    if (runmod.DRAFTS / f"{date}-review.md").exists():
        return "skipped: a one-a-day issue already exists for this date"
    if is_approved(key):
        return "kept: already APPROVED by a person"
    if (runmod.DRAFTS / f"{key}-issue.md").exists() and not force:
        return "exists"
    urls, ids = history()
    for fmt in plan(date)[slot]:
        if fmt == "news":
            runmod.run(date, force=force, edition=slot)
            if (runmod.DRAFTS / f"{key}-issue.md").exists():
                return "news"
            log(f"pack: not enough confirmed news for {key}; trying the next format")
            continue
        item = None
        if fmt == "repo":
            item = formats.repo_spotlight(now, urls, fetcher)
        elif fmt == "model":
            item = formats.model_spotlight(now, urls, fetcher)
        elif fmt == "paper":
            prov = provider if provider is not None else get_checker(s, force)
            item = formats.paper_of_the_day(now, urls, prov, fetcher)
            if prov is not None and item and item["mode"] == "llm" and provider is None:
                runmod._usage_add(str(today_ist()), 1)
        elif fmt == "explainer":
            item = formats.explainer(ids)
        elif fmt == "question":
            item = formats.question(ids)
        if item:
            write_single(date, slot, fmt, item, s, now)
            return fmt
        log(f"pack: nothing suitable for {key} as {fmt}; trying the next format")
    return "nothing built"


def build_pack(today, force=False, fetcher=None, provider=None):
    s = settings()
    if s.get("paused"):
        log("paused: nothing to do")
        return 0
    runmod.DRAFTS.mkdir(exist_ok=True)
    runmod.ISSUES.mkdir(parents=True, exist_ok=True)
    now = dt.datetime.now(UTC)
    tomorrow = today + dt.timedelta(days=1)
    targets = [(today, "evening")] + [(tomorrow, slot) for slot in ("morning", "midday", "afternoon")]
    failed = 0
    for date, slot in targets:
        try:
            result = build_slot(date, slot, s, now, force, fetcher, provider)
        except Exception as exc:  # noqa: BLE001 - one slot failing must not stop the others
            log(f"pack: {issue_key(date, slot)} failed: {type(exc).__name__}: {str(exc)[:120]}")
            failed += 1
            continue
        log(f"pack: {issue_key(date, slot)} ({SLOT_TIMES[slot]} IST): {result}")
    return 1 if failed == len(targets) else 0


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--date", help="today's date YYYY-MM-DD (default: today in IST)")
    p.add_argument("--force", action="store_true")
    a = p.parse_args(argv)
    load_env()
    return build_pack(dt.date.fromisoformat(a.date) if a.date else today_ist(), force=a.force)


if __name__ == "__main__":
    sys.exit(main())
