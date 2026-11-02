"""Daily run: collect > rank > write > verify > render a DRAFT for human review.

Usage (from the project folder):
    python3 -m pipeline.run                 # today's issue (IST date)
    python3 -m pipeline.run --no-ai         # skip the AI writer, use the extractive fallback
    python3 -m pipeline.run --offline       # skip link checks
    python3 -m pipeline.run --date 2026-11-03 --force

Safe by design: it only ever writes drafts. Posting happens after a human approves. If anything breaks the
run exits non-zero (so the scheduler alerts you) and never leaves a half-written issue behind.
"""
import argparse
import datetime as dt
import json
import sys
import traceback

from adapters.llm import LLMError, get_provider

from .collect import collect
from .common import ROOT, UTC, load_env, load_json, log, settings, today_ist
from .rank import rank
from .render import first_comment, linkedin_post, review_notes
from .verify import verify
from .write import write

DRAFTS = ROOT / "drafts"
ISSUES = ROOT / "data" / "issues"
LOGS = ROOT / "data" / "logs"
USAGE = ROOT / "data" / "usage.json"


def _usage_get(day):
    try:
        return json.loads(USAGE.read_text(encoding="utf-8")).get(day, 0)
    except (OSError, ValueError):
        return 0


def _usage_add(day, n):
    try:
        data = json.loads(USAGE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    data[day] = data.get(day, 0) + n
    USAGE.write_text(json.dumps(dict(sorted(data.items())[-60:]), indent=1), encoding="utf-8")


def run(date, force=False, no_ai=False, offline=False, fetcher=None, link_checker=None, provider=None):
    s = settings()
    if s.get("paused") or (ROOT / "KILL_SWITCH").exists():
        log("paused (settings.paused or KILL_SWITCH file): nothing to do")
        return 0
    DRAFTS.mkdir(exist_ok=True)
    ISSUES.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    day = str(date)
    if (DRAFTS / f"{day}-review.md").exists() and not force:
        log(f"draft for {day} already exists (use --force to rebuild)")
        return 0

    now = dt.datetime.now(UTC)
    kwargs = {} if fetcher is None else {"fetcher": fetcher}
    try:
        sources = load_json("config/sources.json")["sources"]
        def gather(hours):
            got, errs = collect(sources, hours, s["max_per_source"], now=now, **kwargs)
            ranked = rank(got, now, hours, s["history_days"], s["candidates_to_write"], date,
                          min_text=s.get("min_text_chars", 0), deny=s.get("deny_title_patterns", []),
                          per_source=s.get("max_per_source_in_issue", 0))
            log(f"rank: {len(ranked)} candidate stories from {len(got)} items ({hours}h window)")
            return got, errs, ranked

        run_notes = []
        items, errors, clusters = gather(s["lookback_hours"])
        wide = s.get("lookback_hours_max", 0)
        if len(clusters) < s["candidates_to_write"] and wide > s["lookback_hours"]:
            items, errors, clusters = gather(wide)
            run_notes.append(f"quiet news period: widened the window to {wide} hours")

        llm_cfg = s["llm"]
        checker = provider  # an injected provider (tests) is used for both roles
        cap = llm_cfg["max_llm_calls_per_day"]
        # The cap guards free-tier limits against runaway loops. A manual --force run is a deliberate rebuild
        # by the owner, so it is exempt (its calls are still counted).
        if provider is None and not no_ai and (force or _usage_get(day) < cap):
            try:
                provider = get_provider(llm_cfg)
                checker = get_provider(llm_cfg, role="checker") or provider  # a different AI gives a genuine second opinion
            except LLMError as exc:
                log(f"AI provider unavailable: {exc}")
                run_notes.append(f"AI provider unavailable ({exc}); used the extractive fallback")
        elif not no_ai and provider is None:
            log("daily AI call cap reached; using extractive fallback")
            run_notes.append(f"AI skipped: today's AI call cap ({cap}, llm.max_llm_calls_per_day) was already used up; "
                             "used the extractive fallback. A manual 'force' run ignores the cap.")
        calls = 0
        if provider and clusters:
            calls += 1
        written, mode, notes = write(clusters, None if no_ai else provider, s["brand"], llm_cfg.get("fall_back_to_extractive", True))
        notes = run_notes + notes
        vcfg = dict(s["verify"], check_links=s["verify"]["check_links"] and not offline)
        second = bool(provider) and mode == "llm" and llm_cfg.get("second_pass_check", True) and not no_ai
        if second:
            calls += 1
        vkw = {} if link_checker is None else {"link_checker": link_checker}
        kept, report = verify(written, vcfg, provider=checker, second_pass=second, **vkw)
        if calls:
            _usage_add(day, calls)

        kept.sort(key=lambda i: -i["score"])
        kept = kept[: s["items_in_issue"]]
        status = "ready_for_review" if len(kept) >= s["min_items"] else "quiet_day"
        public = [{k: v for k, v in it.items() if k != "source_text"} for it in kept]  # never store source text
        issue = {"date": day, "status": status, "mode": mode, "brand": s["brand"], "items": public,
                 "report": report, "errors": errors, "notes": notes,
                 "created": now.isoformat()}
        (ISSUES / f"{day}.json").write_text(json.dumps(issue, indent=1, ensure_ascii=False), encoding="utf-8")
        (DRAFTS / f"{day}-review.md").write_text(review_notes(issue), encoding="utf-8")
        if status == "ready_for_review":
            li = s["linkedin"]
            (DRAFTS / f"{day}-linkedin.txt").write_text(linkedin_post(issue, s["brand"], li["hashtags"], li["max_chars"]), encoding="utf-8")
            (DRAFTS / f"{day}-comment.txt").write_text(first_comment(issue), encoding="utf-8")
        log(f"done: status={status}, items={len(public)}, mode={mode}")
        (LOGS / f"{day}.json").write_text(json.dumps({"date": day, "status": status, "items": len(public), "mode": mode,
                                                      "source_errors": len(errors), "llm_calls": calls}, indent=1), encoding="utf-8")
        return 0
    except Exception:  # noqa: BLE001 - report loudly, leave no half-written issue
        traceback.print_exc()
        (LOGS / f"{day}.json").write_text(json.dumps({"date": day, "status": "failed"}), encoding="utf-8")
        return 1


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--date", help="issue date YYYY-MM-DD (default: today in IST)")
    p.add_argument("--force", action="store_true")
    p.add_argument("--no-ai", action="store_true")
    p.add_argument("--offline", action="store_true", help="skip link checks")
    a = p.parse_args(argv)
    load_env()
    date = dt.date.fromisoformat(a.date) if a.date else today_ist()
    return run(date, force=a.force, no_ai=a.no_ai, offline=a.offline)


if __name__ == "__main__":
    sys.exit(main())
