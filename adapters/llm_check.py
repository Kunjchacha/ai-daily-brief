"""Diagnose the AI provider: python -m adapters.llm_check

Runs a tiny request against each candidate Gemini model and prints status, latency and Google's own error text,
so a flaky or misconfigured free tier can be understood from evidence. It never prints a key (only whether one is
set). Safe to run in GitHub Actions (see .github/workflows/llm-check.yml) or locally with a .env.
"""
import os
import sys
import time

from adapters import llm
from pipeline.common import load_env, settings

PROMPT = 'Reply with exactly this JSON and nothing else: {"ok": true}'


def main():
    load_env()
    cfg = settings()["llm"]
    key = os.environ.get("GEMINI_API_KEY")
    print(f"provider: {cfg['provider']} | fallback: {cfg.get('fallback_provider') or 'none'}")
    print(f"GEMINI_API_KEY set: {bool(key)} | GROQ_API_KEY set: {bool(os.environ.get('GROQ_API_KEY'))}")
    if not key:
        print("No Gemini key in this environment; nothing to test.")
        return 1
    llm.start_budget(240)

    print("\n-- Models this key can call (generateContent):")
    try:
        names = llm.gemini_models(key)
        flash = llm.rank_flash(names)
        print(f"{len(names)} models; flash candidates (best first): {', '.join(flash[:6]) or 'none'}")
    except llm.LLMError as exc:
        names, flash = [], []
        print(f"could not list models: {exc}")

    candidates = []
    for n in [cfg["gemini_model"], *cfg.get("gemini_fallback_models", []), *flash[:3]]:
        if n not in candidates:
            candidates.append(n)

    print("\n-- Tiny test request per model (30s limit, no retries):")
    worked = []
    for name in candidates:
        started = time.time()
        try:
            llm._post(f"{llm.GEMINI_BASE}/models/{name}:generateContent",
                      {"contents": [{"parts": [{"text": PROMPT}]}],
                       "generationConfig": {"temperature": 0, "responseMimeType": "application/json"}},
                      {"x-goog-api-key": key}, timeout=30, retries=0)
            print(f"  OK    {name:<34} {time.time() - started:5.1f}s")
            worked.append(name)
        except llm.LLMError as exc:
            print(f"  FAIL  {name:<34} {time.time() - started:5.1f}s  {exc}")
    print("\nGemini result:", f"{len(worked)} model(s) answered: {', '.join(worked)}" if worked else
          "no model answered. Read the reasons above (404 = name retired, 403 = key/permission, 429 = quota, "
          "503 or timeout = Google is overloaded or throttling this network).")

    print("\n== Groq ==")
    gkey = os.environ.get("GROQ_API_KEY")
    print(f"GROQ_API_KEY set: {bool(gkey)}")
    if not gkey:
        print("No Groq key in this environment; skipping.")
        return 0
    llm.start_budget(240)
    try:
        gnames = llm.groq_models(gkey)
        granked = llm.rank_groq(gnames)
        print(f"{len(gnames)} models; best candidates: {', '.join(granked[:6]) or 'none'}")
    except llm.LLMError as exc:
        granked = []
        print(f"could not list models: {exc}")
    gcands = []
    for n in [cfg["groq_model"], *cfg.get("groq_fallback_models", []), *granked[:3]]:
        if n not in gcands:
            gcands.append(n)
    print("\n-- Tiny test request per Groq model (30s limit, no retries):")
    gworked = []
    for name in gcands:
        started = time.time()
        try:
            llm._post(f"{llm.GROQ_BASE}/chat/completions",
                      {"model": name, "temperature": 0, "response_format": {"type": "json_object"},
                       "messages": [{"role": "user", "content": PROMPT}]},
                      {"Authorization": f"Bearer {gkey}"}, timeout=30, retries=0)
            print(f"  OK    {name:<40} {time.time() - started:5.1f}s")
            gworked.append(name)
        except llm.LLMError as exc:
            print(f"  FAIL  {name:<40} {time.time() - started:5.1f}s  {exc}")
    print("\nGroq result:", f"{len(gworked)} model(s) answered: {', '.join(gworked)}" if gworked else
          "no model answered. Read the reasons above (403 = blocked or bad key, 404 = model retired, 429 = rate limit).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
