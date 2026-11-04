# Mac job that starts the daily draft (does not depend on GitHub's scheduler)

Why: GitHub's own scheduler fired once, 7 hours late, and did nothing at 14:00 or 15:00 IST on 4 Nov. This job asks GitHub to start "Daily draft" at 14:05, 14:35, 15:05 and 16:05 IST if today's draft is missing. If the Mac was asleep, launchd runs the missed slot when it wakes. It only ever starts a DRAFT.

## One-time setup (you; 2 minutes)
1. GitHub > your profile picture > Settings > Developer settings > Personal access tokens > Fine-grained tokens > Generate new token.
   - Name: ai-daily-brief-draft. Expiry: 90 days. Repository access: Only select repositories > Kunjchacha/ai-daily-brief.
   - Permissions > Repository permissions > Actions: Read and write. Nothing else.
2. Copy the token (do not paste it into any chat), then in Terminal run:
   `mkdir -p ~/.config/ai-daily-brief && pbpaste > ~/.config/ai-daily-brief/token && chmod 600 ~/.config/ai-daily-brief/token`
3. Test it (this also starts today's draft if it is missing): `/usr/bin/python3 ~/.local/share/ai-daily-brief/ensure_draft.py`
   Expect a Mac notification and a line in `~/Library/Logs/ai-daily-brief.log`.

## Installed job
The script runs from `~/.local/share/ai-daily-brief/ensure_draft.py`, a copy of `ops/ensure_draft.py`. macOS stops background jobs reading the Desktop folder, so it cannot run from the repo. After changing `ops/ensure_draft.py`, copy it again.
`~/Library/LaunchAgents/com.kunj.ai-daily-brief.plist` (a copy of `ops/com.kunj.ai-daily-brief.plist`).
- Check: `launchctl print gui/$(id -u)/com.kunj.ai-daily-brief | head`
- Stop: `launchctl bootout gui/$(id -u)/com.kunj.ai-daily-brief`

## When the token expires (about every 90 days)
You get a Mac notification "TOKEN REJECTED". Make a new token and repeat step 2.
