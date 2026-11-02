"""LLM adapter. Swap providers through config/settings.json ("llm.provider") with no code changes.

Providers: "gemini" (Google AI Studio free tier), "groq" (free tier), "none" (no AI: extractive fallback).
Keys come from environment variables only (GEMINI_API_KEY, GROQ_API_KEY). Never write keys to files.
Free-tier model names and limits change; check the provider's current free model and update settings.json.
"""
import json
import os
import re
import socket
import time
import urllib.error
import urllib.request

GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"
_GEMINI_CHOSEN = {}  # remembers the model that worked during this run
_BUDGET = {"deadline": None}  # hard cap on total AI time per call, so a flaky provider can't stall the run


class LLMError(Exception):
    pass


def start_budget(seconds):
    _BUDGET["deadline"] = time.time() + seconds


def _remaining():
    d = _BUDGET["deadline"]
    return 1e9 if d is None else d - time.time()


def _redact(text):
    for name in ("GEMINI_API_KEY", "GROQ_API_KEY"):
        secret = os.environ.get(name)
        if secret and len(secret) > 6:
            text = text.replace(secret, "***")
    return text


def _err_text(e):
    """A short, key-redacted reason from an HTTP error body (e.g. 'The model is overloaded')."""
    try:
        raw = e.read(400).decode("utf-8", "replace")
        m = re.search(r'"message"\s*:\s*"([^"]{1,140})', raw)
        return _redact((m.group(1) if m else raw[:140]).replace("\n", " ")).strip()
    except Exception:  # noqa: BLE001
        return ""


def _fail_text(e, started):
    """Describe a failed request in a short, consistent way."""
    if isinstance(e, urllib.error.HTTPError):
        detail = _err_text(e)
        return f"HTTP {e.code}" + (f": {detail}" if detail else "")
    reason = getattr(e, "reason", e)
    if isinstance(e, (TimeoutError, socket.timeout)) or isinstance(reason, (TimeoutError, socket.timeout)):
        return f"Timeout after {time.time() - started:.0f}s"
    return _redact(f"{type(e).__name__}: {reason}")[:100]


def _post(url, body, headers, timeout=45, retries=1):
    data = json.dumps(body).encode("utf-8")
    last = None
    for attempt in range(retries + 1):
        if _remaining() <= 1:
            raise LLMError("request failed (Timeout: AI time budget used up)")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json", **headers})
        started = time.time()
        try:
            with urllib.request.urlopen(req, timeout=max(2, min(timeout, _remaining()))) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            last = _fail_text(e, started)
            if e.code not in (429, 500, 502, 503, 504):
                break
        except Exception as e:  # noqa: BLE001
            last = _fail_text(e, started)
        if attempt < retries:
            time.sleep(2 ** attempt * 2)
    raise LLMError(f"request failed ({last})")


def _get(url, headers, timeout=30):
    req = urllib.request.Request(url, headers=headers)
    started = time.time()
    try:
        with urllib.request.urlopen(req, timeout=max(2, min(timeout, _remaining()))) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:  # noqa: BLE001
        raise LLMError(f"request failed ({_fail_text(e, started)})")


def rank_flash(names):
    """Usable 'flash' text models, best first: stable before preview, newer before older, non-lite before lite."""
    skip = ("image", "tts", "live", "audio", "embedding", "robotics", "computer", "exp", "vision")
    cands = [n for n in names if "flash" in n and not any(s in n for s in skip)]

    def version(n):
        m = re.search(r"gemini-(\d+(?:\.\d+)?)", n)
        return float(m.group(1)) if m else 0.0
    return sorted(cands, key=lambda n: ("preview" not in n, version(n), "lite" not in n), reverse=True)


def pick_flash(names):
    """The single best flash model (None if there is none)."""
    ranked = rank_flash(names)
    return ranked[0] if ranked else None


# Errors that mean "this model is unavailable right now": move on to the next model. Anything else
# (400/401/403: bad key, no permission) is a real problem and is raised straight away.
TRY_NEXT = ("HTTP 404", "HTTP 429", "HTTP 500", "HTTP 502", "HTTP 503", "HTTP 504", "Timeout")


def gemini_models(key):
    """Ask the API which models this key may call with generateContent."""
    res = _get(f"{GEMINI_BASE}/models?pageSize=200", {"x-goog-api-key": key})
    return [m["name"].split("/", 1)[1] for m in res.get("models", [])
            if "generateContent" in m.get("supportedGenerationMethods", [])]


def _gemini_call(prompt, model, key):
    body = {"contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"}}
    res = _post(f"{GEMINI_BASE}/models/{model}:generateContent", body, {"x-goog-api-key": key})
    try:
        return res["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError):
        raise LLMError("unexpected Gemini response shape")


def gemini(prompt, model, fallbacks=()):
    """Call Gemini. If a model name is retired (HTTP 404), try fallbacks, then discover a current one."""
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise LLMError("GEMINI_API_KEY not set")
    tried, last = [], "none"

    def attempt(name):
        nonlocal last
        tried.append(name)
        try:
            out = _gemini_call(prompt, name, key)
            _GEMINI_CHOSEN["m"] = name
            return out
        except LLMError as exc:
            if not any(code in str(exc) for code in TRY_NEXT):
                raise
            last = f"{name}: {exc}"
            print(f"[llm] Gemini model '{name}' unavailable ({exc}); trying the next one", flush=True)
            return None

    for name in ([_GEMINI_CHOSEN["m"]] if "m" in _GEMINI_CHOSEN else []) + [model, *fallbacks]:
        if name not in tried:
            out = attempt(name)
            if out is not None:
                return out
    try:
        discovered = rank_flash([n for n in gemini_models(key) if n not in tried])[:3]
    except LLMError as exc:
        raise LLMError(f"no usable Gemini model (tried {', '.join(tried)}; model list failed: {exc})")
    for name in discovered:
        out = attempt(name)
        if out is not None:
            print(f"[llm] used discovered model '{name}'. Update llm.gemini_model in settings.json.", flush=True)
            return out
    raise LLMError(f"no usable Gemini model (tried {', '.join(tried)}; last error {last})")


def groq(prompt, model):
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        raise LLMError("GROQ_API_KEY not set")
    body = {"model": model, "temperature": 0.2, "response_format": {"type": "json_object"},
            "messages": [{"role": "user", "content": prompt}]}
    res = _post("https://api.groq.com/openai/v1/chat/completions", body, {"Authorization": f"Bearer {key}"})
    try:
        return res["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        raise LLMError("unexpected Groq response shape")


def _single(name, cfg):
    if name == "gemini":
        return lambda p: gemini(p, cfg["gemini_model"], cfg.get("gemini_fallback_models", []))
    if name == "groq":
        return lambda p: groq(p, cfg["groq_model"])
    raise LLMError(f"unknown provider: {name}")


def get_provider(cfg):
    """Return a callable prompt -> text, or None when no AI should be used.

    "provider" is tried first; if it fails and "fallback_provider" is set (and its key exists), that is tried next.
    """
    primary = (cfg.get("provider") or "none").lower()
    if primary == "none":
        return None
    names = [primary]
    fb = (cfg.get("fallback_provider") or "").lower()
    if fb and fb not in ("none", primary):
        names.append(fb)
    chain = [(n, _single(n, cfg)) for n in names]

    def call(prompt):
        start_budget(cfg.get("time_budget_seconds", 100))
        errors = []
        for name, fn in chain:
            try:
                return fn(prompt)
            except LLMError as exc:
                errors.append(f"{name}: {exc}")
        raise LLMError("; ".join(errors))
    return call
