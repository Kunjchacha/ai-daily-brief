"""Make sure today's AI Daily Brief draft exists, without relying on GitHub's own scheduler (which has been late or silent).

Run by macOS launchd at 14:05, 14:35, 15:05 and 16:05 IST (see ops/INSTALL.md). Each run:
  1. Has today's draft (drafts/DATE-issue.md) reached GitHub? If yes, nothing to do.
  2. Is a "Daily draft" run already queued or running? If yes, wait for it.
  3. Otherwise ask GitHub to start "Daily draft" (the same as pressing Run workflow, with force off, so it never
     rebuilds or overwrites an existing or approved issue).
It only starts a DRAFT. It never approves, posts or schedules anything. The token (Actions: read and write on this one
repository) is read from ~/.config/ai-daily-brief/token and is never printed or logged.
"""
import datetime as dt
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

REPO = "Kunjchacha/ai-daily-brief"
API = f"https://api.github.com/repos/{REPO}"
TOKEN_FILE = os.path.expanduser("~/.config/ai-daily-brief/token")
LOG = os.path.expanduser("~/Library/Logs/ai-daily-brief.log")
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))


def log(msg):
    line = f"{dt.datetime.now(IST):%Y-%m-%d %H:%M:%S} IST  {msg}"
    print(line)
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def notify(msg):
    """A Mac notification, so a problem is never silent."""
    try:
        subprocess.run(["osascript", "-e", f'display notification "{msg}" with title "AI Daily Brief"'], timeout=10)
    except Exception:  # noqa: BLE001 - a notification failing must not stop the job
        pass


def call(path, token=None, body=None):
    """Return (status, parsed JSON or None). Network errors raise."""
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "ai-daily-brief-ensure-draft"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(API + path, data=data, headers=headers, method="POST" if body is not None else "GET")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read()
            return r.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        return e.code, None


def draft_exists(day):
    """Today's draft is there when GitHub has today's evening issue (two-a-day) or the original one-a-day issue."""
    return any(call(f"/contents/drafts/{name}-issue.md?ref=main")[0] == 200 for name in (f"{day}-evening", day))


def run_in_progress():
    status, data = call("/actions/workflows/daily.yml/runs?per_page=5")
    return status == 200 and any(r["status"] in ("queued", "in_progress", "waiting") for r in data["workflow_runs"])


def ensure(day, token, wait_seconds=300):
    """Returns a short result string; never raises for an expected situation."""
    if draft_exists(day):
        return "draft already on GitHub"
    if run_in_progress():
        result = "a Daily draft run is already in progress"
    else:
        status, _ = call("/actions/workflows/daily.yml/dispatches", token, {"ref": "main"})
        if status == 401 or status == 403:
            return "TOKEN REJECTED: create a new token (expired or missing the Actions permission)"
        if status != 204:
            return f"FAILED to start the run (GitHub answered {status})"
        result = "started the Daily draft run"
    deadline = time.time() + wait_seconds
    while time.time() < deadline:
        time.sleep(20)
        if draft_exists(day):
            return result + "; the draft is now on GitHub"
    return result + "; no draft yet after waiting (check Actions)"


def main():
    day = dt.datetime.now(IST).strftime("%Y-%m-%d")
    if draft_exists(day):
        log(f"{day}: draft already on GitHub, nothing to do")
        return 0
    try:
        token = open(TOKEN_FILE, encoding="utf-8").read().strip()
    except OSError:
        token = ""
    if not token:
        log(f"{day}: no draft yet and no token at {TOKEN_FILE}: cannot start it")
        notify("No draft yet and no GitHub token set up. See ops/INSTALL.md")
        return 1
    try:
        result = ensure(day, token)
    except Exception as exc:  # noqa: BLE001 - report any failure loudly
        result = f"ERROR {type(exc).__name__}: {str(exc)[:100]}"
    log(f"{day}: {result}")
    if "TOKEN" in result or "FAILED" in result or "ERROR" in result or "no draft yet" in result:
        notify(result[:120])
        return 1
    notify("Today's draft: " + result[:100])
    return 0


if __name__ == "__main__":
    sys.exit(main())
