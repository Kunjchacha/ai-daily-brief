"""Stage 5: render the LinkedIn draft, the reviewer notes, the web page and the RSS feed."""
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
            lines.append(f"Source: {it['url']}")
            lines.append("")
        lines += ["AI-assisted, human-reviewed.", "", " ".join(hashtags)]
        text = "\n".join(lines)
        if len(text) <= max_chars or len(items) <= 1:
            return text
        items.pop()


def age_text(published, ref):
    """'7 hours old' / '3 days old', so stale stories are obvious."""
    try:
        hours = (ref - dt.datetime.fromisoformat(published)).total_seconds() / 3600
    except (TypeError, ValueError):
        return "age unknown"
    return f"{hours / 24:.0f} days old" if hours >= 48 else f"{max(hours, 0):.0f} hours old"


def agent_lines(issue):
    """The review agent's advice: the issue score, its verdict and a per-item scorecard (empty when the agent did not run)."""
    a = issue.get("agent")
    if not a:
        return ["- Review agent: did not run (offline or disabled): check every source yourself"]
    out = [f"- Review agent score: **{a['score']}%, {a['verdict']}** (the weakest item sets the score; advice only)"]
    for r in a["items"]:
        why = "; ".join(r["reasons"]) or "all checks passed"
        out.append(f"  - {r['score']}% grade {r['grade']}: {r['headline']} ({why})")
    return out


def review_notes(issue):
    L = [f"# Review notes: {issue['date']}", "", f"- Status: **{issue['status']}** (nothing is posted until you approve it)",
         *agent_lines(issue),
         f"- Writing mode: {issue['mode']}",
         f"- Items kept: {len(issue['items'])} | dropped: {sum(1 for r in issue['report'] if r['status'] == 'dropped')}", "",
         "## What each item rests on",
         "Check that each is a CONFIRMED FACT (something that has happened or been officially announced), not a rumour or opinion.", ""]
    ref = dt.datetime.fromisoformat(issue["created"]) if issue.get("created") else dt.datetime.now(dt.timezone.utc)
    for n, it in enumerate(issue["items"], 1):
        quote = it.get("evidence_quote") or "no exact quote (written without AI: check the source yourself)"
        L.append(f"{n}. **{it['headline']}**: {it.get('kind') or 'unchecked'}; {it['source']}, {age_text(it.get('published'), ref)}")
        L.append(f"   Source says: \"{quote}\"")
    L.append("")
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
    day = issue["date"]
    L += ["## Your approval step (nothing goes out without it)",
          "1. Open each source link and read it. Accuracy and judgement are your job, not the script's.",
          f"2. Open `drafts/{day}-issue.md`, edit anything you want, set `Include: no` on anything that is not a confirmed fact,",
          "   replace any `[ADD YOUR LINE]`, then change `Status: DRAFT` to `Status: APPROVED` and save.",
          "3. Run Actions > **Approve issue** with this date. It produces the final post (sources included) from YOUR text.",
          "4. Post the final text on LinkedIn (or queue it in Buffer), then run Actions > **Publish approved issue**.", ""]
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


def preview_page(issue, brand, tagline, linkedin_text, contact=""):
    """One self-contained page showing how the LinkedIn post will read and how the website page will look.
    It is a draft preview only: nothing in it is published."""
    site = html.escape(issue_page(issue, brand, tagline, contact), quote=True)
    style = ("<style>.banner{background:#FEF3C7;border:1px solid #F59E0B;padding:.6rem .9rem;border-radius:8px}"
             ".card{border:1px solid #CBD5E1;border-radius:10px;padding:1rem;background:#fff}"
             ".card pre{white-space:pre-wrap;font:inherit;margin:.5rem 0 0}.who{color:#475569}"
             "iframe{width:100%;height:760px;border:1px solid #CBD5E1;border-radius:10px;background:#fff}</style>")
    body = (f"{style}<p class='banner'><b>PREVIEW ONLY.</b> Nothing here is posted or published. Status: "
            f"{html.escape(issue['status'])}.</p><h1>1. LinkedIn post</h1>"
            f"<div class='card'><div class='who'>Your profile &middot; just now &middot; {len(linkedin_text)} characters</div>"
            f"<pre>{html.escape(linkedin_text)}</pre></div>"
            f"<h1>2. Website archive page</h1><iframe srcdoc=\"{site}\" title='Website page preview'></iframe>")
    return _page(f"Preview: {brand} {issue['date']}", body)


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
