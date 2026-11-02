"""Promote an approved draft to the public website (archive page, index and RSS feed).

Usage: python3 -m pipeline.publish --date 2026-11-03
Run this only after you have posted (or approved) the issue. It never posts to LinkedIn itself.
"""
import argparse
import json
import sys

from .common import ROOT, log, settings
from .render import feed_xml, index_page, issue_page

SITE = ROOT / "site"
ISSUES = ROOT / "data" / "issues"


def published_issues():
    out = []
    for f in sorted(ISSUES.glob("*.json"), reverse=True):
        try:
            i = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if i.get("status") == "published":
            out.append(i)
    return out


def publish(day):
    s = settings()
    f = ISSUES / f"{day}.json"
    if not f.exists():
        log(f"no issue file for {day}")
        return 1
    issue = json.loads(f.read_text(encoding="utf-8"))
    if issue["status"] not in ("ready_for_review", "published"):
        log(f"issue {day} has status {issue['status']}; nothing to publish")
        return 1
    if any(it.get("needs_human_line") for it in issue["items"]):
        log("some items still need a human 'why it matters' line; publishing them without that line")
    issue["status"] = "published"
    f.write_text(json.dumps(issue, indent=1, ensure_ascii=False), encoding="utf-8")
    (SITE / "issues").mkdir(parents=True, exist_ok=True)
    (SITE / "issues" / f"{day}.html").write_text(
        issue_page(issue, s["brand"], s["tagline"], s["site"].get("contact", "")), encoding="utf-8")
    pub = published_issues()
    (SITE / "index.html").write_text(index_page(pub, s["brand"], s["tagline"]), encoding="utf-8")
    (SITE / "feed.xml").write_text(feed_xml(pub, s["brand"], s["tagline"], s["site"].get("base_url", "")), encoding="utf-8")
    log(f"published {day}: {len(issue['items'])} stories; archive now has {len(pub)} issues")
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--date", required=True)
    return publish(p.parse_args(argv).date)


if __name__ == "__main__":
    sys.exit(main())
