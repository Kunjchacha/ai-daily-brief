"""Stage 5: render the LinkedIn draft, its first comment, the reviewer notes, the web page and the RSS feed."""
import datetime as dt
import email.utils
import html

from .common import IST, long_date

PLACEHOLDER = "[ADD YOUR LINE]"


def _date(issue):
    return dt.date.fromisoformat(issue["date"])


def linkedin_post(issue, brand, hashtags, max_chars):
    items = list(issue["items"])
    while True:
        lines = [f"{brand}: {long_date(_date(issue))}", "", f"{len(items)} AI developments worth your time today:", ""]
        for n, it in enumerate(items, 1):
            lines.append(f"{n}. {it['headline']}")
            lines.append(it["summary"])
            why = it["why_it_matters"] or PLACEHOLDER
            lines.append(f"Why it matters: {why}")
            lines.append("")
        lines += ["Sources are in the first comment.",
                  "Which of these matters most to you? Reply and I'll feature the best take.", "",
                  "AI-assisted, human-reviewed.", "", " ".join(hashtags)]
        text = "\n".join(lines)
        if len(text) <= max_chars or len(items) <= 1:
            return text
        items.pop()


def first_comment(issue):
    lines = ["Sources:"]
    for n, it in enumerate(issue["items"], 1):
        extra = f" (also covered by {', '.join(it['also'])})" if it.get("also") else ""
        lines.append(f"{n}. {it['source']}: {it['url']}{extra}")
    return "\n".join(lines)


def review_notes(issue):
    L = [f"# Review notes: {issue['date']}", "", f"- Status: **{issue['status']}**",
         f"- Writing mode: {issue['mode']}",
         f"- Items kept: {len(issue['items'])} | dropped: {sum(1 for r in issue['report'] if r['status'] == 'dropped')}", ""]
    need = [it for it in issue["items"] if it.get("needs_human_line")]
    if need:
        L += ["## Needs your line", "Replace `[ADD YOUR LINE]` in the post for:"] + [f"- {it['headline']}" for it in need] + [""]
    dropped = [r for r in issue["report"] if r["status"] == "dropped"]
    if dropped:
        L += ["## Dropped by the verification gate"] + [f"- {r['headline']}: {'; '.join(r['problems'])}" for r in dropped] + [""]
    warn = [r for r in issue["report"] if r["warnings"] and r["status"] == "kept"]
    if warn:
        L += ["## Warnings"] + [f"- {r['headline']}: {'; '.join(r['warnings'])}" for r in warn] + [""]
    if issue.get("notes"):
        L += ["## Notes"] + [f"- {n}" for n in issue["notes"]] + [""]
    if issue.get("errors"):
        L += ["## Source errors"] + [f"- {e['source']}: {e['error']}" for e in issue["errors"]] + [""]
    L += ["## Before you post", "1. Open each source link and skim it (accuracy is your job, not the script's).",
          "2. Fix wording you don't like, fill any placeholder, then post to LinkedIn (or queue it in Buffer).",
          "3. Put the contents of the comment file in the first comment.", ""]
    return "\n".join(L)


CSS = ("body{font-family:Inter,Helvetica,Arial,sans-serif;max-width:720px;margin:2rem auto;padding:0 1rem;color:#0F172A;"
       "line-height:1.55}h1{font-size:1.6rem}h2{font-size:1.15rem;margin-bottom:.2rem}a{color:#15803D}"
       ".meta{color:#64748B;font-size:.9rem}.why{background:#DCFCE7;padding:.5rem .8rem;border-radius:6px}"
       "footer{margin-top:2.5rem;color:#64748B;font-size:.9rem}")


def _page(title, body):
    return (f'<!doctype html><html lang="en-GB"><head><meta charset="utf-8"><meta name="viewport" '
            f'content="width=device-width,initial-scale=1"><title>{html.escape(title)}</title><style>{CSS}</style></head>'
            f"<body>{body}</body></html>")


def issue_page(issue, brand, tagline, contact=""):
    d = long_date(_date(issue))
    parts = [f"<h1>{html.escape(brand)}</h1><p class='meta'>{html.escape(d)}</p>"]
    for it in issue["items"]:
        why = f"<p class='why'>Why it matters: {html.escape(it['why_it_matters'])}</p>" if it["why_it_matters"] else ""
        parts.append(f"<h2>{html.escape(it['headline'])}</h2><p>{html.escape(it['summary'])}</p>{why}"
                     f"<p class='meta'>Source: <a href='{html.escape(it['url'], quote=True)}' rel='noopener'>"
                     f"{html.escape(it['source'])}</a></p>")
    fix = f" Spotted a mistake? {html.escape(contact)}" if contact else ""
    parts.append(f"<footer>AI-assisted, human-reviewed. We summarise and link; the original authors own their work.{fix}"
                 f"</footer>")
    return _page(f"{brand}: {d}", "".join(parts))


def index_page(issues, brand, tagline):
    rows = "".join(f"<li><a href='issues/{i['date']}.html'>{html.escape(long_date(_date(i)))}</a> "
                   f"<span class='meta'>{len(i['items'])} stories</span></li>" for i in issues)
    return _page(brand, f"<h1>{html.escape(brand)}</h1><p>{html.escape(tagline)}</p><ul>{rows}</ul>")


def feed_xml(issues, brand, tagline, base_url):
    base = base_url.rstrip("/")
    items = []
    for i in issues[:30]:
        when = dt.datetime.combine(_date(i), dt.time(7, 30), IST)
        desc = " | ".join(it["headline"] for it in i["items"])
        items.append(f"<item><title>{html.escape(brand)}: {html.escape(long_date(_date(i)))}</title>"
                     f"<link>{base}/issues/{i['date']}.html</link><guid>{base}/issues/{i['date']}.html</guid>"
                     f"<pubDate>{email.utils.format_datetime(when)}</pubDate>"
                     f"<description>{html.escape(desc)}</description></item>")
    return ('<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel>'
            f"<title>{html.escape(brand)}</title><link>{base}/</link><description>{html.escape(tagline)}</description>"
            + "".join(items) + "</channel></rss>")
