"""Charts drawn from live, free data, as SVG (no plotting library needed) and wrapped as carousel slides.

Every number comes straight from the source API. The headline sentence is a template filled with those numbers, never written by an
AI, and each chart ends with what it shows, what it does not show, the source and the date it was fetched.
"""
import datetime as dt
import html
import re
import urllib.request

from .collect import UA
from .formats import SPAM_RE, TOPICS, _ascii_ratio, _clean, get_json, LICENCE_NAMES

W = 900
INK, MUTED, GRID, BAR = "#E2E8F0", "#94A3B8", "#2B4A66", "#FBBF24"
PALETTE = ["#FBBF24", "#38BDF8", "#34D399", "#F472B6", "#A78BFA", "#FB923C", "#94A3B8"]
FONT = "font-family=\"Helvetica Neue,Helvetica,Arial,sans-serif\""


def _esc(s):
    return html.escape(str(s), quote=True)


def _short(s, n=34):
    return s if len(s) <= n else s[: n - 1] + "…"


def bar_svg(labels, values, unit=""):
    """Horizontal bars, one row per label, the label above its bar and the value at the bar's end."""
    top = max(values) or 1
    row, pad = 92, 10
    h = pad * 2 + row * len(values)
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {h}" width="{W}" height="{h}" {FONT}>']
    for i, (lab, val) in enumerate(zip(labels, values)):
        y = pad + i * row
        bw = max(6, int((W - 190) * val / top))
        out.append(f'<text x="0" y="{y + 28}" font-size="28" fill="{INK}">{_esc(_short(lab))}</text>')
        out.append(f'<rect x="0" y="{y + 40}" width="{bw}" height="30" rx="6" fill="{BAR}"/>')
        out.append(f'<text x="{bw + 14}" y="{y + 65}" font-size="28" font-weight="700" fill="{INK}">{val:,}{_esc(unit.replace(" models", " model") if val == 1 else unit)}</text>')
    return "".join(out) + "</svg>"


def donut_svg(labels, values):
    """A donut with a legend listing each share."""
    total = sum(values) or 1
    import math
    cx, cy, r, sw = 210, 210, 150, 62
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} 440" width="{W}" height="440" {FONT}>']
    circ, offset = 2 * math.pi * r, 0.0
    for i, v in enumerate(values):
        frac = v / total
        out.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{PALETTE[i % len(PALETTE)]}" stroke-width="{sw}" '
                   f'stroke-dasharray="{frac * circ:.2f} {circ:.2f}" stroke-dashoffset="{-offset:.2f}" transform="rotate(-90 {cx} {cy})"/>')
        offset += frac * circ
    for i, (lab, v) in enumerate(zip(labels, values)):
        y = 60 + i * 58
        out.append(f'<rect x="470" y="{y - 24}" width="30" height="30" rx="6" fill="{PALETTE[i % len(PALETTE)]}"/>')
        out.append(f'<text x="516" y="{y}" font-size="30" fill="{INK}">{_esc(_short(lab, 22))}  <tspan font-weight="700">{round(100 * v / total)}%</tspan></text>')
    return "".join(out) + "</svg>"


def line_svg(xlabels, values):
    """A simple line with a dot and a value on every point, starting the axis at zero."""
    top = max(values) or 1
    left, right, ttop, bottom = 20, W - 20, 70, 380
    n = len(values)
    pts = [(left + (right - left - 20) * i / max(n - 1, 1) + 10, bottom - (bottom - ttop) * v / top) for i, v in enumerate(values)]
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} 450" width="{W}" height="450" {FONT}>',
           f'<line x1="{left}" y1="{bottom}" x2="{right}" y2="{bottom}" stroke="{GRID}" stroke-width="3"/>',
           f'<polyline fill="none" stroke="{BAR}" stroke-width="6" points="{" ".join(f"{x:.0f},{y:.0f}" for x, y in pts)}"/>']
    for (x, y), v, lab in zip(pts, values, xlabels):
        out.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="9" fill="{BAR}"/>')
        out.append(f'<text x="{x:.0f}" y="{y - 20:.0f}" font-size="24" fill="{INK}" text-anchor="middle">{v:,}</text>')
        out.append(f'<text x="{x:.0f}" y="{bottom + 40}" font-size="22" fill="{MUTED}" text-anchor="middle">{_esc(lab)}</text>')
    return "".join(out) + "</svg>"


def _frame(title, svg, shows, not_shows, source_note, hook):
    """Cover, the chart, how to read it, and the source slide."""
    return {"hook": hook, "slides": [
        {"kicker": "Chart", "title": title, "svg": svg},
        {"kicker": "How to read it", "title": "What it shows, and what it does not", "compare": True,
         "left": {"head": "Shows", "items": shows}, "right": {"head": "Does not show", "items": not_shows}}],
        "source_note": source_note}


def _stamp(now):
    return now.astimezone(dt.timezone(dt.timedelta(hours=5, minutes=30))).strftime("%d %b %Y, %H:%M IST")


# ---- the five charts: each returns {"hook","slides","source_note","url","source","points"} or None -------------------------------
def models_downloads(now, fetcher=None):
    data = get_json("https://huggingface.co/api/models?sort=trendingScore&direction=-1&limit=8", fetcher)
    rows = [(m["id"], m.get("downloads", 0)) for m in data if m.get("downloads")]
    if len(rows) < 5:
        return None
    top = max(rows, key=lambda r: r[1])
    out = _frame("Downloads of the 8 models trending on Hugging Face", bar_svg([r[0] for r in rows], [r[1] for r in rows]),
                 ["The 8 models on Hugging Face's own trending list right now", "Each model's download count, as Hugging Face reports it"],
                 ["Quality: a download is not a review", "Whether people kept using the model after downloading it"],
                 f"Source: Hugging Face API, fetched {_stamp(now)}. Numbers change daily.",
                 f"{top[0]} has the most downloads, {top[1]:,}, of the 8 models trending on Hugging Face right now.")
    out.update(url="https://huggingface.co/models?sort=trending", source="Hugging Face",
               points=["Trending is not the same as best. The chart compares the 8 models on today's trending list."])
    return out


def repos_stars(now, fetcher=None):
    since = (now - dt.timedelta(days=14)).strftime("%Y-%m-%d")
    best = {}
    for topic in TOPICS[:4]:
        try:
            d = get_json(f"https://api.github.com/search/repositories?q=topic:{topic}+created:%3E{since}+stars:%3E150&sort=stars&order=desc&per_page=15",
                         fetcher, "GITHUB_TOKEN")
        except Exception:  # noqa: BLE001
            continue
        for r in d.get("items", []):
            if (not r.get("fork") and _ascii_ratio(r.get("description") or "") >= 0.9 and not SPAM_RE.search(f'{r["full_name"]} {r.get("description") or ""}')):
                best[r["html_url"]] = r
    rows = sorted(best.values(), key=lambda r: -r["stargazers_count"])[:8]
    if len(rows) < 5:
        return None
    out = _frame("Stars on the newest AI repositories", bar_svg([r["full_name"] for r in rows], [r["stargazers_count"] for r in rows]),
                 ["Repositories created in the last 14 days under AI-related GitHub topics", "Their current star counts"],
                 ["Quality or safety: stars show interest, not code review", "Repositories without these topics, or older ones"],
                 f"Source: GitHub search API, fetched {_stamp(now)}. Stars can be inflated.",
                 f"{rows[0]['full_name']} leads the newest AI repositories on GitHub with {rows[0]['stargazers_count']:,} stars in under two weeks.")
    out.update(url="https://github.com/topics/llm", source="GitHub", points=["Popularity is not safety: read the licence and the code before you rely on a repository."])
    return out


def licences(now, fetcher=None):
    data = get_json("https://huggingface.co/api/models?sort=trendingScore&direction=-1&limit=40", fetcher)
    tags = []
    for m in data:
        lic = next((t.split(":", 1)[1] for t in m.get("tags", []) if t.startswith("license:")), None)
        tags.append("Custom or other" if (lic or "").lower() in ("other", "unknown") else
                    LICENCE_NAMES.get((lic or "").lower(), lic) if lic else "Not stated")
    if len(tags) < 20:
        return None
    from collections import Counter
    c = Counter(tags).most_common()
    top = c[:5]
    rest = sum(v for _, v in c[5:])
    labels = [k for k, _ in top] + (["Others"] if rest else [])
    vals = [v for _, v in top] + ([rest] if rest else [])
    pct = round(100 * top[0][1] / len(tags))
    out = _frame("Licences of the 40 models trending on Hugging Face", donut_svg(labels, vals),
                 ["The licence tag on each of the 40 models on the trending list", "'Not stated' where the model has no licence tag"],
                 ["What a licence allows: always read the licence itself", "Models outside the trending list"],
                 f"Source: Hugging Face API, fetched {_stamp(now)}.",
                 {"Not stated": f"{pct}% of the 40 models trending on Hugging Face right now state no licence.",
                  "Custom or other": f"{pct}% of the 40 models trending on Hugging Face right now use a custom or 'other' licence, not a standard one."}
                 .get(top[0][0], f"{pct}% of the 40 models trending on Hugging Face right now use the {top[0][0]} licence."))
    out.update(url="https://huggingface.co/models?sort=trending", source="Hugging Face",
               points=["A licence decides what you may do with a model. Check it before you build on one."])
    return out


def tasks(now, fetcher=None):
    data = get_json("https://huggingface.co/api/models?sort=trendingScore&direction=-1&limit=50", fetcher)
    from collections import Counter
    c = Counter(m["pipeline_tag"].replace("-", " ") for m in data if m.get("pipeline_tag")).most_common(7)
    if len(c) < 4:
        return None
    out = _frame("What the 50 trending models do", bar_svg([k for k, _ in c], [v for _, v in c], " models"),
                 ["The task each of the 50 trending models is tagged with on Hugging Face"],
                 ["How good the models are at the task", "Models without a task tag"],
                 f"Source: Hugging Face API, fetched {_stamp(now)}.",
                 f"'{c[0][0]}' is the most common task among the 50 models trending on Hugging Face right now: {c[0][1]} of 50.")
    out.update(url="https://huggingface.co/models?sort=trending", source="Hugging Face",
               points=["One look at what builders are working on this week, by task."])
    return out


def arxiv_weekly(now, fetcher=None):
    import time
    end = (now.date() - dt.timedelta(days=now.weekday() + 1))  # the most recent Sunday: only complete weeks
    counts, labels = [], []
    for w in range(8, 0, -1):
        last = end - dt.timedelta(weeks=w - 1)
        first = last - dt.timedelta(days=6)
        url = ("https://export.arxiv.org/api/query?search_query=cat:cs.AI+AND+submittedDate:%5B"
               f"{first:%Y%m%d}0000+TO+{last:%Y%m%d}2359%5D&max_results=1")
        raw = (fetcher(url) if fetcher else _arxiv_get(url)).decode("utf-8", "replace")
        m = re.search(r"<opensearch:totalResults[^>]*>(\d+)<", raw)
        if not m:
            return None
        counts.append(int(m.group(1)))
        labels.append(f"{last:%d %b}")
        if not fetcher:
            time.sleep(3.2)  # arXiv asks API users to wait between calls
    chg = round(100 * (counts[-1] - counts[-2]) / counts[-2]) if counts[-2] else 0
    word = "up" if chg > 0 else "down" if chg < 0 else "level"
    out = _frame("AI papers submitted to arXiv each week", line_svg(labels, counts),
                 ["Papers submitted in each of the last 8 complete weeks (to the Sunday shown) that list cs.AI as a category"],
                 ["Paper quality or importance", "Papers in other categories, and cross-listed papers are counted once under this query"],
                 f"Source: arXiv API, fetched {_stamp(now)}.",
                 f"{counts[-1]:,} papers listing cs.AI were submitted to arXiv in the week to {labels[-1]}, "
                 + (f"{word} {abs(chg)}% on the week before." if chg else "level with the week before."))
    out.update(url="https://arxiv.org/list/cs.AI/recent", source="arXiv", points=["Counting papers shows volume, not progress."])
    return out


def _arxiv_get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=30) as r:
        return r.read()


KINDS = {"models": models_downloads, "repos": repos_stars, "licences": licences, "tasks": tasks, "arxiv": arxiv_weekly}
