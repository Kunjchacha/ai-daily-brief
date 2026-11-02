"""LLM adapter. Swap providers through config/settings.json ("llm.provider") with no code changes.

Providers: "gemini" (Google AI Studio free tier), "groq" (free tier), "none" (no AI: extractive fallback).
Keys come from environment variables only (GEMINI_API_KEY, GROQ_API_KEY). Never write keys to files.
Free-tier model names and limits change; check the provider's current free model and update settings.json.
"""
import json
import os
import time
import urllib.error
import urllib.request


class LLMError(Exception):
    pass


def _post(url, body, headers, timeout=90, retries=2):
    data = json.dumps(body).encode("utf-8")
    last = None
    for attempt in range(retries + 1):
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json", **headers})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}"
            if e.code not in (429, 500, 502, 503, 504):
                break
        except Exception as e:  # noqa: BLE001
            last = type(e).__name__
        time.sleep(2 ** attempt * 2)
    raise LLMError(f"request failed ({last})")


def gemini(prompt, model):
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise LLMError("GEMINI_API_KEY not set")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    body = {"contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"}}
    res = _post(url, body, {"x-goog-api-key": key})
    try:
        return res["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError):
        raise LLMError("unexpected Gemini response shape")


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


def get_provider(cfg):
    """Return a callable prompt -> text, or None when no AI should be used."""
    name = (cfg.get("provider") or "none").lower()
    if name == "none":
        return None
    if name == "gemini":
        return lambda p: gemini(p, cfg["gemini_model"])
    if name == "groq":
        return lambda p: groq(p, cfg["groq_model"])
    raise LLMError(f"unknown provider: {name}")
