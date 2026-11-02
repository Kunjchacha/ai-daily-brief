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
from pathlib import Path

GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"
STATE_PATH = Path(__file__).resolve().parent.parent / "data" / "llm_state.json"  # remembers the last model that worked
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


def _load_state():
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _remember(state_key, name):
    """Persist the model that just worked so the next run tries it first (models retire and overload often)."""
    state = _load_state()
    if state.get(state_key) == name:
        return
    state[state_key] = name
    try:
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        STATE_PATH.write_text(json.dumps(state, indent=1), encoding="utf-8")
    except OSError:
        pass


# Some providers (Groq sits behind Cloudflare) reject Python's default user agent with a 403, so identify ourselves.
USER_AGENT = "ai-daily-brief/0.1 (+https://github.com/Kunjchacha/ai-daily-brief)"


def _post(url, body, headers, timeout=100, retries=1):
    data = json.dumps(body).encode("utf-8")
    last = None
    for attempt in range(retries + 1):
        if _remaining() <= 1:
            raise LLMError("request failed (Timeout: AI time budget used up)")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json",
                                                              "User-Agent": USER_AGENT, **headers})
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
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **headers})
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


def _run_models(label, chosen, state_key, order, call, discover):
    """Try models in order (last working one first). 'Unavailable' errors move on to the next model; when the
    list runs out, ask the provider which models exist now and try the best few. Real errors raise at once."""
    tried, last = [], "none"

    def attempt(name):
        nonlocal last
        tried.append(name)
        try:
            out = call(name)
            chosen["m"] = name
            _remember(state_key, name)
            return out
        except LLMError as exc:
            if not any(code in str(exc) for code in TRY_NEXT):
                raise
            last = f"{name}: {exc}"
            print(f"[llm] {label} model '{name}' unavailable ({exc}); trying the next one", flush=True)
            return None

    remembered = chosen.get("m") or _load_state().get(state_key)
    for name in ([remembered] if remembered else []) + list(order):
        if name not in tried:
            out = attempt(name)
            if out is not None:
                return out
    try:
        discovered = discover(tried)[:3]
    except LLMError as exc:
        raise LLMError(f"no usable {label} model (tried {', '.join(tried)}; model list failed: {exc})")
    for name in discovered:
        out = attempt(name)
        if out is not None:
            print(f"[llm] used discovered {label} model '{name}'. Update settings.json.", flush=True)
            return out
    raise LLMError(f"no usable {label} model (tried {', '.join(tried)}; last error {last})")


def _gemini_call(prompt, model, key):
    """One request. Hidden 'thinking' is switched off (summarising doesn't need it and it adds a lot of delay);
    if a model rejects that setting with HTTP 400, the same request is sent once without it."""
    body = {"contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json",
                                 "thinkingConfig": {"thinkingBudget": 0}}}
    url = f"{GEMINI_BASE}/models/{model}:generateContent"
    try:
        res = _post(url, body, {"x-goog-api-key": key})
    except LLMError as exc:
        if "HTTP 400" in str(exc) and "think" in str(exc).lower():
            body["generationConfig"].pop("thinkingConfig")
            res = _post(url, body, {"x-goog-api-key": key})
        else:
            raise
    try:
        return res["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError):
        raise LLMError("unexpected Gemini response shape")


def gemini(prompt, model, fallbacks=()):
    """Call Gemini with model fallback and discovery (see _run_models)."""
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise LLMError("GEMINI_API_KEY not set")
    return _run_models("Gemini", _GEMINI_CHOSEN, "gemini_model", [model, *fallbacks],
                       lambda n: _gemini_call(prompt, n, key),
                       lambda tried: rank_flash([n for n in gemini_models(key) if n not in tried]))


GROQ_BASE = "https://api.groq.com/openai/v1"
_GROQ_CHOSEN = {}


def rank_groq(ids):
    """Chat-capable Groq models, best first: capable mid-to-large sizes before tiny or giant ones."""
    skip = ("whisper", "guard", "tts", "playai", "embed", "orpheus", "safeguard", "moderation", "vision")
    cands = [i for i in ids if not any(s in i.lower() for s in skip)]

    def size(i):
        m = re.search(r"(\d+)b", i.lower())
        return int(m.group(1)) if m else 0
    return sorted(cands, key=lambda i: (20 <= size(i) <= 130, size(i)), reverse=True)


def groq_models(key):
    """Ask Groq which models this key can use right now."""
    res = _get(f"{GROQ_BASE}/models", {"Authorization": f"Bearer {key}"})
    return [m["id"] for m in res.get("data", []) if m.get("active", True)]


def _groq_call(prompt, model, key):
    body = {"model": model, "temperature": 0.2, "response_format": {"type": "json_object"},
            "messages": [{"role": "user", "content": prompt}]}
    res = _post(f"{GROQ_BASE}/chat/completions", body, {"Authorization": f"Bearer {key}"})
    try:
        return res["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        raise LLMError("unexpected Groq response shape")


def groq(prompt, model, fallbacks=()):
    """Call Groq with model fallback and discovery (see _run_models)."""
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        raise LLMError("GROQ_API_KEY not set")
    return _run_models("Groq", _GROQ_CHOSEN, "groq_model", [model, *fallbacks],
                       lambda n: _groq_call(prompt, n, key),
                       lambda tried: rank_groq([i for i in groq_models(key) if i not in tried]))


def _single(name, cfg):
    if name == "gemini":
        return lambda p: gemini(p, cfg["gemini_model"], cfg.get("gemini_fallback_models", []))
    if name == "groq":
        return lambda p: groq(p, cfg["groq_model"], cfg.get("groq_fallback_models", []))
    raise LLMError(f"unknown provider: {name}")


def get_provider(cfg, role="writer"):
    """Return a callable prompt -> text, or None when no AI should be used.

    role="writer" uses "provider" then "fallback_provider". role="checker" (the independent fact-check) uses
    "checker_provider" then "checker_fallback_provider", defaulting to the writer's settings if those are absent.
    The first is tried first; if it fails, the fallback is tried next. Using a different provider to check than
    to write gives a genuine second opinion.
    """
    if role == "checker":
        primary = (cfg.get("checker_provider") or cfg.get("provider") or "none").lower()
        fb = (cfg.get("checker_fallback_provider") or cfg.get("fallback_provider") or "").lower()
    else:
        primary = (cfg.get("provider") or "none").lower()
        fb = (cfg.get("fallback_provider") or "").lower()
    if primary == "none":
        return None
    names = [primary]
    if fb and fb not in ("none", primary):
        names.append(fb)
    chain = [(n, _single(n, cfg)) for n in names]

    def call(prompt):
        errors = []
        for name, fn in chain:
            start_budget(cfg.get("time_budget_seconds", 150))  # each provider gets its own time, so a slow one can't starve the next
            try:
                return fn(prompt)
            except LLMError as exc:
                errors.append(f"{name}: {exc}")
        raise LLMError("; ".join(errors))
    return call
