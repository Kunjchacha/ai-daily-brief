"""LinkedIn carousel (a PDF 'document' post) for the formats that teach something: workflow cards and myth-vs-reality.

Usage: python3 -m pipeline.carousel --key 2026-11-06-morning [--out cards]
Writes cards/KEY.pdf (upload this as the post's document) and cards/KEY-01.png ... for checking on your phone. 1080x1350 pages,
the 4:5 portrait size that fills a phone screen. Needs Google Chrome. Slides repeat only what the approved issue says.
"""
import argparse
import html
import json
import subprocess
import sys
from pathlib import Path

from .cards import CHROME
from .common import ROOT

CSS = """
@page{size:1080px 1350px;margin:0}
*{box-sizing:border-box;margin:0}html,body{width:1080px}
.slide{width:1080px;height:1350px;background:#0B1B2B;color:#F8FAFC;font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;
padding:90px;display:flex;flex-direction:column;justify-content:space-between;page-break-after:always;overflow:hidden}
.kicker{color:#FBBF24;font-size:32px;letter-spacing:.14em;text-transform:uppercase;font-weight:700}
.bar{width:110px;height:10px;background:#FBBF24;margin:0 0 26px}
.t{font-weight:800;line-height:1.14;margin-top:38px}
.b{color:#CBD5E1;font-size:44px;line-height:1.36;margin-top:34px}
ol,ul{padding:0;margin-top:40px}li{list-style:none;position:relative;padding-left:78px;font-size:44px;line-height:1.3;margin:0 0 34px 0;color:#F1F5F9}
ol{counter-reset:n}ol li:before{counter-increment:n;content:counter(n);position:absolute;left:0;top:-2px;width:54px;height:54px;border-radius:50%;
background:#FBBF24;color:#0B1B2B;font-weight:800;font-size:34px;text-align:center;line-height:54px}
ul li:before{content:'';position:absolute;left:8px;top:16px;width:22px;height:22px;border-radius:50%;background:#FBBF24}
.code{background:#13293D;border:3px solid #2B4A66;border-radius:22px;padding:44px;font-family:Menlo,Consolas,monospace;font-size:35px;line-height:1.45;
color:#E2E8F0;margin-top:40px;white-space:pre-wrap}
.foot{display:flex;justify-content:space-between;align-items:flex-end;color:#94A3B8;font-size:28px}.brand{color:#F8FAFC;font-weight:700;font-size:32px}
.swipe{color:#FBBF24;font-size:34px;font-weight:700}
"""


def _size(text, big=84, mid=68, small=56):
    return big if len(text) < 60 else mid if len(text) < 110 else small


def slides_for(issue):
    """A list of slide dicts: kicker, title, optional body, items (list), code, ordered (bool)."""
    fmt, it = issue["format"], issue["items"][0]
    if fmt == "workflow":
        w = it["bank"]
        return [{"kicker": "AI at work", "title": it["hook"], "cover": True},
                {"kicker": "The problem", "title": "Why this is worth five minutes", "body": w["problem"]},
                {"kicker": "Steps", "title": w["title"], "items": w["steps"], "ordered": True},
                {"kicker": "The prompt", "title": "Copy it, then change the [brackets]", "code": w["prompt"]},
                {"kicker": "Check before you use it", "title": "Never skip this part", "items": w["checks"]},
                {"kicker": "Mistake to avoid", "title": w["mistake"], "body": w["privacy"]},
                {"kicker": "Keep this", "title": "Save it for the next time you need it.", "body": w["title"], "end": True}]
    if fmt == "myth":
        m = it["bank"]
        up = lambda x: x[:1].upper() + x[1:]  # noqa: E731 - after cutting 'Myth: ' the sentence must start with a capital
        s = [{"kicker": "Myth", "title": up(m["myth"].removeprefix("Myth: ")), "cover": True},
             {"kicker": "Reality", "title": up(m["reality"].removeprefix("Reality: "))},
             {"kicker": "So what?", "title": m["so_what"]},
             {"kicker": "Try this", "title": m["do"]},
             {"kicker": "Source", "title": m["source"], "body": m["url"], "end": True}]
        return s
    raise ValueError(f"no carousel for format {fmt}")


def slide_html(s, i, n, brand):
    size = _size(s["title"]) if not s.get("cover") else _size(s["title"], 92, 76, 62)
    body = f"<div class='t' style='font-size:{size}px'>{html.escape(s['title'])}</div>"
    if s.get("body"):
        body += f"<div class='b'>{html.escape(s['body'])}</div>"
    if s.get("items"):
        tag = "ol" if s.get("ordered") else "ul"
        body += f"<{tag}>" + "".join(f"<li>{html.escape(x)}</li>" for x in s["items"]) + f"</{tag}>"
    if s.get("code"):
        body += f"<div class='code'>{html.escape(s['code'])}</div>"
    right = "<span class='swipe'>Swipe &rarr;</span>" if s.get("cover") else f"<span>{i} / {n}</span>"
    return (f"<div class='slide'><div><div class='bar'></div><div class='kicker'>{html.escape(s['kicker'])}</div>{body}</div>"
            f"<div class='foot'><span class='brand'>{html.escape(brand)}</span>{right}</div></div>")


def deck_html(slides, brand, only=None):
    n = len(slides)
    chosen = [(i, s) for i, s in enumerate(slides, 1) if only in (None, i)]
    return ("<!doctype html><meta charset='utf-8'><style>" + CSS + "</style>"
            + "".join(slide_html(s, i, n, brand) for i, s in chosen))


def render(key, out="cards"):
    issue = json.loads((ROOT / "data" / "issues" / f"{key}.json").read_text(encoding="utf-8"))
    slides, brand = slides_for(issue), issue.get("brand", "AI Daily Brief")
    out_dir = Path(out) if Path(out).is_absolute() else ROOT / out
    out_dir.mkdir(exist_ok=True)
    page = out_dir / f"{key}-deck.html"
    page.write_text(deck_html(slides, brand), encoding="utf-8")
    pdf = out_dir / f"{key}.pdf"
    base = [CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars"]
    subprocess.run(base + [f"--print-to-pdf={pdf}", "--no-pdf-header-footer", f"file://{page}"], check=True, timeout=90, capture_output=True)
    pngs = []
    for i in range(1, len(slides) + 1):
        one = out_dir / f"{key}-{i:02d}.html"
        one.write_text(deck_html(slides, brand, only=i), encoding="utf-8")
        png = out_dir / f"{key}-{i:02d}.png"
        subprocess.run(base + [f"--screenshot={png}", "--window-size=1080,1350", f"file://{one}"], check=True, timeout=60,
                       capture_output=True)
        one.unlink()
        pngs.append(png)
    return pdf, pngs


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--key", required=True)
    p.add_argument("--out", default="cards")
    a = p.parse_args(argv)
    pdf, pngs = render(a.key, a.out)
    print(pdf, f"({len(pngs)} slides)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
