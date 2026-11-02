"""Stage 1: collect recent items from RSS/Atom feeds and the Hacker News API.

Feed content is untrusted data. It is parsed, never executed, size-capped, and XML that declares
entities is refused (blocks 'billion laughs' style attacks).
"""
import datetime as dt
import json
import urllib.request
import zlib
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

from .common import UTC, canonical_url, clean_text, log

UA = "ai-newsletter/0.1 (personal AI news digest; polite feed reader)"
MAX_BYTES = 3_000_000
ATOM = "{http://www.w3.org/2005/Atom}"
CONTENT = "{http://purl.org/rss/1.0/modules/content/}"
DC = "{http://purl.org/dc/elements/1.1/}"
TEXT_LIMIT = 1500


def fetch(url, timeout=20):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "application/rss+xml, application/atom+xml, application/xml, application/json, */*",
    })
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = r.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError("response too large")
    return gunzip_if_needed(data)


def gunzip_if_needed(data):
    """Some servers send gzip even when not asked. Decompress safely, capping the output size."""
    if data[:2] == b"\x1f\x8b":
        d = zlib.decompressobj(16 + zlib.MAX_WBITS)
        data = d.decompress(data, MAX_BYTES + 1)
        if len(data) > MAX_BYTES or d.unconsumed_tail:
            raise ValueError("decompressed response too large")
    return data


def parse_date(s):
    if not s:
        return None
    s = s.strip()
    try:
        d = parsedate_to_datetime(s)
    except (TypeError, ValueError):
        d = None
    if d is None:
        try:
            d = dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
        except ValueError:
            return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=UTC)
    return d.astimezone(UTC)


def parse_feed(data, source):
    """Return a list of item dicts from RSS 2.0 or Atom bytes."""
    if b"<!ENTITY" in data:
        raise ValueError("feed declares XML entities; refused")
    root = ET.fromstring(data)
    out = []

    def add(title, link, text, published):
        title, link = clean_text(title), (link or "").strip()
        if not title or not link:
            return
        if not link.lower().startswith(("http://", "https://")):
            return  # never accept javascript:, file:, data: etc. (XSS on the site, local-file probing in link checks)
        out.append({
            "source_id": source["id"], "source": source["name"], "authority": source.get("authority", 2),
            "title": title, "url": link, "text": clean_text(text, TEXT_LIMIT),
            "published": published.isoformat() if published else None, "points": 0,
        })

    entries = list(root.iter(ATOM + "entry"))
    if entries:
        for e in entries:
            href = ""
            for l in e.findall(ATOM + "link"):
                if l.get("rel", "alternate") == "alternate":
                    href = l.get("href", "")
                    break
            text = e.findtext(ATOM + "summary") or e.findtext(ATOM + "content") or ""
            pub = parse_date(e.findtext(ATOM + "published") or e.findtext(ATOM + "updated"))
            add(e.findtext(ATOM + "title"), href, text, pub)
    else:
        for it in root.iter("item"):
            text = it.findtext("description") or it.findtext(CONTENT + "encoded") or ""
            pub = parse_date(it.findtext("pubDate") or it.findtext(DC + "date"))
            add(it.findtext("title"), it.findtext("link"), text, pub)
    return out


def parse_hn(data, source):
    out = []
    for h in json.loads(data).get("hits", []):
        title = clean_text(h.get("title"))
        url = h.get("url") or f"https://news.ycombinator.com/item?id={h.get('objectID')}"
        if not title or not url.lower().startswith(("http://", "https://")):
            continue
        pub = dt.datetime.fromtimestamp(h.get("created_at_i", 0), UTC)
        out.append({
            "source_id": source["id"], "source": source["name"], "authority": source.get("authority", 2),
            "title": title, "url": url, "text": title, "published": pub.isoformat(),
            "points": int(h.get("points") or 0),
        })
    return out


def collect(sources, lookback_hours, max_per_source, now=None, fetcher=fetch):
    """Return (items, errors). A failing source is recorded and skipped, never fatal."""
    now = now or dt.datetime.now(UTC)
    cutoff = now - dt.timedelta(hours=lookback_hours)
    items, errors = [], []
    for src in sources:
        try:
            url = src["url"].replace("{since}", str(int(cutoff.timestamp())))
            data = fetcher(url)
            parsed = parse_hn(data, src) if src["type"] == "hn" else parse_feed(data, src)
            fresh = []
            for it in parsed:
                d = dt.datetime.fromisoformat(it["published"]) if it["published"] else None
                if d and d >= cutoff:
                    it["canonical"] = canonical_url(it["url"])
                    it["filter"] = bool(src.get("filter"))
                    fresh.append(it)
            fresh.sort(key=lambda x: x["published"], reverse=True)
            items.extend(fresh[:max_per_source])
            log(f"collect: {src['id']:<16} {len(fresh):>3} fresh of {len(parsed):>3}")
        except Exception as exc:  # noqa: BLE001 - any single-source failure must not stop the run
            errors.append({"source": src["id"], "error": f"{type(exc).__name__}: {exc}"[:200]})
            log(f"collect: {src['id']:<16} FAILED {type(exc).__name__}")
    return items, errors
