"""Shared helpers: paths, config, text cleaning, dates. Standard library only (works on Python 3.9+)."""
import datetime as dt
import html
import json
import re
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parent.parent
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
UTC = dt.timezone.utc

TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+")
STOP = set("""a an the and or of to in on for with from by at as is are was were be been it its this that these those
how why what when who new says say said will can could would should about into over after before more most than
you your we our they their their's his her not no yes up down out off just now""".split())
DROP_PARAMS = {"ref", "fbclid", "gclid", "source", "mc_cid", "mc_eid"}


def load_env():
    """Read KEY=VALUE lines from a local .env (git-ignored) into the environment, without overriding real variables."""
    import os
    f = ROOT / ".env"
    if not f.exists():
        return
    for line in f.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            if v.strip():
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def load_json(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def settings():
    return load_json("config/settings.json")


def clean_text(s, limit=None):
    """Strip HTML, decode entities, collapse whitespace, optionally trim to a word boundary."""
    s = html.unescape(TAG_RE.sub(" ", s or ""))
    s = WS_RE.sub(" ", s).strip()
    if limit and len(s) > limit:
        s = s[:limit].rsplit(" ", 1)[0].rstrip(",;:") + "..."
    return s


def canonical_url(u):
    """Normalise a URL so the same story from two feeds compares equal."""
    p = urlsplit((u or "").strip())
    q = [(k, v) for k, v in parse_qsl(p.query) if not k.lower().startswith("utm_") and k.lower() not in DROP_PARAMS]
    host = p.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return urlunsplit((p.scheme.lower(), host, p.path.rstrip("/") or "/", urlencode(q), ""))


def tokens(title):
    return {t for t in re.findall(r"[a-z0-9]+", (title or "").lower()) if t not in STOP and len(t) > 1}


def jaccard(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def today_ist():
    return dt.datetime.now(IST).date()


def long_date(d):
    return f"{d.strftime('%A')} {d.day} {d.strftime('%B %Y')}"


def log(msg):
    print(f"[{dt.datetime.now(UTC).strftime('%H:%M:%S')}Z] {msg}", flush=True)
