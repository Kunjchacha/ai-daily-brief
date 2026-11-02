# Operations runbook: AI Daily Brief

This file is the handover. Everything needed to run, move or stop the newsletter without Claude is here.

## 1. What runs, and where
| Piece | What it is | Cost | Can be swapped for |
|---|---|---|---|
| Code, drafts, archive | This repo on GitHub (public) | £0 | Any Git host, or just a folder |
| Daily scheduler | GitHub Actions cron (`.github/workflows/daily.yml`) | £0 (public repos) | Any cron (see section 6) |
| Website and RSS | GitHub Pages from the `site/` folder | £0 | Any static host |
| News sources | Public RSS/Atom feeds and the Hacker News API | £0 | Edit `config/sources.json` |
| AI writer | Free-tier Gemini or Groq via `adapters/llm.py` | £0 | Change `llm.provider` in `config/settings.json`, or `none` |
| LinkedIn posting | You, or Buffer's free plan | £0 | n/a |

Free tiers change. Re-check the AI provider's current free model and limits every few months and update the model name in `config/settings.json`.

## 2. One-time setup (you do these; accounts and keys are yours)
1. Create a free GitHub account (use a personal email, not a work one) and a **public** repository, then push this folder to it.
2. Get a free API key: Google AI Studio (Gemini) or Groq. Keep it private.
3. GitHub: Settings > Secrets and variables > Actions > New repository secret > name `GEMINI_API_KEY` (or `GROQ_API_KEY`).
4. GitHub: Settings > Pages > Build and deployment > Source: **GitHub Actions**.
5. Edit `config/settings.json`: set `site.base_url` to your Pages address (for example `https://YOURNAME.github.io/REPO`) and `site.contact` to a public address for corrections.
6. Actions tab > "Daily draft" > Run workflow once to test.

## 3. Daily routine (about 3 minutes)
1. Open today's `drafts/YYYY-MM-DD-review.md` (also shown in the Actions run summary).
2. Skim each source link. **Accuracy is your job; the script only reduces the risk.**
3. Open `drafts/YYYY-MM-DD-linkedin.txt`, fix wording, replace any `[ADD YOUR LINE]`, and post it (or queue it in Buffer).
4. Paste `drafts/YYYY-MM-DD-comment.txt` as the first comment (links in the comment, not the post, tend to reach further on LinkedIn).
5. Actions > "Publish approved issue" > Run workflow with the date, to add it to the public archive.

Quiet news days: the status is `quiet_day` and no post is drafted. Skip posting, or write one yourself.

## 4. Controls and safety
- **Pause everything:** set `"paused": true` in `config/settings.json`, or add a file named `KILL_SWITCH` to the repo root. Resume by undoing it.
- **Stop using AI:** set `"provider": "none"`. Drafts then use the extractive fallback (the source's own first sentences) and need your "why it matters" lines.
- **Spend and rate guard:** `llm.max_llm_calls_per_day` caps AI calls per day (default 6; a normal day uses 2).
- **Verification gate:** items with numbers, names or quotes not found in the source text, hype phrases, over-long text or dead links are dropped automatically. It lowers the chance of invented facts; it cannot guarantee none.
- **Secrets:** never put keys in files, chats or issues. If a key leaks, revoke it at the provider and create a new one.
- **Subscriber data (phase 2) never goes in this repo.** The repo is public.

## 5. When something goes wrong
| Symptom | Likely cause | Fix |
|---|---|---|
| Daily run failed (GitHub emails you) | Tests failed, bad config, or a code error | Open the failed run's log; run `python3 -m unittest discover -s tests` locally |
| `AI writing failed ... used the extractive fallback` | Key missing, quota hit, or model renamed | Check the secret, the provider's free limits and the model name in settings |
| One source shows `FAILED` in the review notes | Feed moved or temporarily down | Ignore for a day, or fix or remove it in `config/sources.json` |
| Fewer than 3 stories (`quiet_day`) | Slow news or too many filters | Widen `lookback_hours_max`, add sources, or loosen `deny_title_patterns` |
| Odd or off-topic picks | Ranking has no editorial taste | Add `deny_title_patterns`, raise or lower source `authority`, rely on your review |
| RSS links start with `/` | `site.base_url` not set | Set it in `config/settings.json` |

## 6. Moving, or running without GitHub
It is plain Python (standard library only, 3.9+) plus static files. To run anywhere: copy the folder, set `GEMINI_API_KEY` in a `.env`, and schedule `python3 -m pipeline.run` with cron. To host the site elsewhere, upload the `site/` folder to any static host. Nothing is tied to GitHub except the free scheduler and Pages.

## 7. Phase 2: at 100+ subscribers (not built yet)
- **Collecting subscribers before then:** a link in your LinkedIn profile to a simple sign-up (a free email service form or a WhatsApp Channel link).
- **Email:** use a free-tier email service with double opt-in and one-click unsubscribe; keep a private, exported copy of the list. Re-check free limits first, because they change.
- **WhatsApp:** a WhatsApp Channel is free but broadcast-only and manual.
- **Privacy and PII (Agilisys policy):** subscriber email addresses are personal data. Run this as your own venture, separate from Agilisys and Blenheim Chalcot systems, accounts, devices and data, and check your employment terms on outside business activity. Add a privacy notice, an unsubscribe route and a postal contact address before collecting anyone's email. UK GDPR/PECR, India's DPDP Act and CAN-SPAM may all apply depending on where readers are.
- **Copyright:** summaries and links only; no republished articles.
