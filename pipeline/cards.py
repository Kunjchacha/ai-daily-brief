"""Image card for a post (1080x1350, the 4:5 portrait size LinkedIn shows well on phones), drawn from the approved issue.

Usage: python3 -m pipeline.cards --key 2026-11-05-midday [--out cards]
Needs Google Chrome (it renders the card headless). Cards are not committed to git (see .gitignore): make one when you queue the post.
The card only repeats what the post says: the hook (or the headlines), the format and the brand. It adds no facts.
"""
import argparse
import html
import json
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

from .common import ROOT, long_date
from .render import FORMAT_NAMES

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


def run_chrome(args, timeout=90):
    """Run headless Chrome with a throw-away profile (a shared profile can hang a second run), retrying once."""
    import shutil
    import tempfile
    for attempt in (1, 2):
        prof = tempfile.mkdtemp(prefix="chrome-")
        try:
            subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--user-data-dir={prof}",
                            "--no-first-run", "--no-default-browser-check", *args], check=True, timeout=timeout, capture_output=True)
            return
        except subprocess.TimeoutExpired:
            if attempt == 2:
                raise
        finally:
            shutil.rmtree(prof, ignore_errors=True)
CSS = """
*{box-sizing:border-box;margin:0}body{width:1080px;height:1350px;background:#0B1B2B;color:#F8FAFC;
font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;padding:96px 90px;display:flex;flex-direction:column;justify-content:space-between}
.kicker{color:#FBBF24;font-size:34px;letter-spacing:.14em;text-transform:uppercase;font-weight:700}
.title{font-weight:800;line-height:1.14}
.list{font-size:46px;line-height:1.25;font-weight:600}.list li{margin:0 0 30px 0;list-style:none}
.list b{color:#FBBF24;margin-right:18px}
.pts{margin-top:46px;padding:0}.pts li{list-style:none;color:#CBD5E1;font-size:40px;line-height:1.32;margin:0 0 26px 0;padding-left:46px;position:relative}.pts li:before{content:'';position:absolute;left:0;top:18px;width:18px;height:18px;border-radius:50%;background:#FBBF24}
.foot{display:flex;justify-content:space-between;align-items:flex-end;color:#94A3B8;font-size:30px}
.brand{color:#F8FAFC;font-size:36px;font-weight:700}.bar{width:120px;height:10px;background:#FBBF24;margin:0 0 28px}
"""


def card_parts(issue, brand):
    """(kicker, headline text or list, small line under it, footer note)."""
    fmt = issue.get("format") or "news"
    when = long_date(__import__("datetime").date.fromisoformat(issue["date"]))
    if fmt == "news":
        n = len(issue["items"])
        return "News brief", [i["headline"] for i in issue["items"]], [], when
    it = issue["items"][0]
    host = urlparse(it["url"]).netloc.replace("www.", "") if it.get("url") else ""
    pts = [x for x in it.get("points", []) if len(x) <= 140 and not x.startswith("The authors report")][:3]
    return FORMAT_NAMES[fmt], it.get("hook") or it["headline"], pts, host or when


def card_html(issue, brand):
    kicker, main, sub, note = card_parts(issue, brand)
    if isinstance(main, list):
        body = "<ol class='list'>" + "".join(f"<li><b>{i}</b>{html.escape(h)}</li>" for i, h in enumerate(main[:4], 1)) + "</ol>"
    else:
        size = 80 if len(main) < 60 else 66 if len(main) < 110 else 54
        body = f"<div class='title' style='font-size:{size}px'>{html.escape(main)}</div>"
    if sub:
        body += "<ul class='pts'>" + "".join(f"<li>{html.escape(x)}</li>" for x in sub) + "</ul>"
    return (f"<!doctype html><meta charset='utf-8'><style>{CSS}</style><div><div class='bar'></div>"
            f"<div class='kicker'>{html.escape(kicker)}</div><div style='height:44px'></div>{body}</div>"
            f"<div class='foot'><span class='brand'>{html.escape(brand)}</span><span>{html.escape(note)}</span></div>")


def render(key, out="cards"):
    issue = json.loads((ROOT / "data" / "issues" / f"{key}.json").read_text(encoding="utf-8"))
    out_dir = Path(out) if Path(out).is_absolute() else ROOT / out
    out_dir.mkdir(exist_ok=True)
    page, png = out_dir / f"{key}.html", out_dir / f"{key}.png"
    page.write_text(card_html(issue, issue.get("brand", "AI Daily Brief")), encoding="utf-8")
    run_chrome([f"--screenshot={png}", "--window-size=1080,1350", f"file://{page}"], 60)
    return png


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--key", required=True)
    p.add_argument("--out", default="cards")
    print(render(p.parse_args(argv).key, p.parse_args(argv).out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
