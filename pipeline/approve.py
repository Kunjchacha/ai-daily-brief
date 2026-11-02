"""The human approval step. Nothing is posted or published until a person approves the issue.

Each draft comes with `drafts/YYYY-MM-DD-issue.md`: one readable file with every item, the exact sentence from the source it
rests on, its kind (announced / reported) and its age. The owner edits it, drops anything that is not a confirmed fact
(`Include: no`), and changes `Status: DRAFT` to `Status: APPROVED`. Only then does this command (run through
Actions > Approve issue) produce the final post text. The pipeline itself can never approve an issue.

Usage: python3 -m pipeline.approve --date 2026-11-03
"""
import argparse
import datetime as dt
import json
import re
import sys

from .common import ROOT, UTC, log, long_date, settings
from .render import PLACEHOLDER, age_text, first_comment, linkedin_post

DRAFTS = ROOT / "drafts"
ISSUES = ROOT / "data" / "issues"
STATUS_RE = re.compile(r"^Status:\s*([A-Za-z]+)", re.M)
HEADER_RE = re.compile(r"^## \d+\.\s*", re.M)
FIELD_RE = re.compile(r"^(Summary|Why it matters|Source|Evidence from the source|Kind|Age|Include):\s*(.*)$")
NOT_FACT_KINDS = ("rumour", "rumor", "opinion", "unconfirmed", "prediction")


def render_issue_md(issue, brand):
    """The one file the owner reads, edits and approves."""
    day = dt.date.fromisoformat(issue["date"])
    ref = dt.datetime.fromisoformat(issue["created"])
    out = [f"# {brand}: {long_date(day)}", "Status: DRAFT", "",
           "HOW TO APPROVE",
           "1. Read every item. Edit any wording below (keep the 'Field:' labels as they are).",
           "2. Not a confirmed fact (a rumour, prediction, plan or opinion)? Change 'Include: yes' to 'Include: no'.",
           f"3. Replace any {PLACEHOLDER} with your own line, and check each source link.",
           "4. When you are happy, change 'Status: DRAFT' above to 'Status: APPROVED' and save.",
           "5. Run Actions > Approve issue. Only then is the final post text produced.", ""]
    for n, it in enumerate(issue["items"], 1):
        quote = it.get("evidence_quote") or "(none: written without AI, so check the source yourself)"
        out += [f"## {n}. {it['headline']}",
                f"Summary: {it['summary']}",
                f"Why it matters: {it['why_it_matters'] or PLACEHOLDER}",
                f"Source: {it['source']} | {it['url']}",
                f"Evidence from the source: {quote}",
                f"Kind: {it.get('kind') or 'unchecked'}",
                f"Age: {age_text(it.get('published'), ref)}",
                "Include: yes", ""]
    return "\n".join(out)


def parse_issue_md(text):
    """Return {"status": "DRAFT"|"APPROVED"|..., "items": [{"headline":..., "Summary":..., ...}]}."""
    m = STATUS_RE.search(text)
    parts = HEADER_RE.split(text)[1:]
    items = []
    for block in parts:
        first, _, rest = block.partition("\n")
        item = {"headline": first.strip()}
        for line in rest.splitlines():
            f = FIELD_RE.match(line.strip())
            if f:
                item[f.group(1)] = f.group(2).strip()
        items.append(item)
    return {"status": m.group(1).upper() if m else "", "items": items}


def is_approved(day):
    f = DRAFTS / f"{day}-issue.md"
    return f.exists() and parse_issue_md(f.read_text(encoding="utf-8"))["status"] == "APPROVED"


def approve(day, s=None):
    s = s or settings()
    ipath, mpath = ISSUES / f"{day}.json", DRAFTS / f"{day}-issue.md"
    if not ipath.exists() or not mpath.exists():
        log(f"No draft found for {day}: expected {ipath.name} and {mpath.name}")
        return 1
    issue = json.loads(ipath.read_text(encoding="utf-8"))
    parsed = parse_issue_md(mpath.read_text(encoding="utf-8"))
    if parsed["status"] != "APPROVED":
        log(f"NOT APPROVED: Status is '{parsed['status'] or 'missing'}'. Edit drafts/{mpath.name}, change the Status line to "
            "'Status: APPROVED', save, then run this again.")
        return 1

    originals = {it["url"]: it for it in issue["items"]}
    facts = s.get("facts_only", {})
    hedges = facts.get("hedge_patterns", []) if facts.get("enabled") else []
    kept, excluded, problems, warnings = [], [], [], []
    for p in parsed["items"]:
        head = p["headline"]
        if (p.get("Include") or "yes").lower() not in ("yes", "y", "true"):
            excluded.append(f"{head} (Include: {p.get('Include')})")
            continue
        kind = (p.get("Kind") or "").lower()
        if kind in NOT_FACT_KINDS:
            excluded.append(f"{head} (Kind: {kind}, so not a confirmed fact)")
            continue
        summary, why = p.get("Summary", ""), p.get("Why it matters", "")
        if not summary or PLACEHOLDER in f"{head} {summary} {why}" or not why:
            problems.append(f"'{head}' still needs its summary or your 'Why it matters' line")
        source, _, url = p.get("Source", "").rpartition(" | ")
        if not url.startswith(("http://", "https://")):
            problems.append(f"'{head}' has no valid http(s) source link")
        for pattern in hedges:
            hit = re.search(pattern, f"{head} {summary}", re.I)
            if hit:
                warnings.append(f"'{head}' contains hedged wording ('{hit.group(0)}'): is this really a confirmed fact?")
                break
        item = dict(originals.get(url, {}))
        item.update(headline=head, summary=summary, why_it_matters=why, source=source or item.get("source", ""),
                    url=url, kind=kind or item.get("kind", ""), needs_human_line=False, approved_text=True)
        kept.append(item)
    if len(kept) < s["min_items"]:
        problems.append(f"only {len(kept)} item(s) left; an issue needs at least {s['min_items']}")
    if problems:
        for pr in problems:
            log("CANNOT APPROVE: " + pr)
        return 1

    issue["items"] = kept
    issue["status"] = "approved"
    issue["approved_at"] = dt.datetime.now(UTC).isoformat()
    ipath.write_text(json.dumps(issue, indent=1, ensure_ascii=False), encoding="utf-8")
    li = s["linkedin"]
    final = linkedin_post(issue, s["brand"], li["hashtags"], li["max_chars"])
    (DRAFTS / f"{day}-linkedin-final.txt").write_text(final, encoding="utf-8")
    (DRAFTS / f"{day}-comment-final.txt").write_text(first_comment(issue), encoding="utf-8")
    log(f"APPROVED {day}: {len(kept)} item(s) kept, {len(excluded)} excluded")
    for e in excluded:
        log("  excluded: " + e)
    for w in warnings:
        log("  WARNING: " + w)
    print("\n===== FINAL LINKEDIN POST =====\n" + final + "\n\n===== FIRST COMMENT =====\n" + first_comment(issue))
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--date", required=True, help="issue date YYYY-MM-DD")
    return approve(p.parse_args(argv).date)


if __name__ == "__main__":
    sys.exit(main())
