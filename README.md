# AI Daily Brief

A zero-cost, self-owned daily AI news brief. It collects fresh stories from public feeds, ranks them, drafts short summaries,
runs an automated fact-support check, and hands you a ready-to-review LinkedIn post. A human approves every issue.

- **Phase 1 (now):** LinkedIn posts + a free public archive and RSS feed.
- **Phase 2 (100+ subscribers):** email or a WhatsApp Channel, whichever readers prefer. See `runbook/OPERATIONS.md`.

## Try it locally (no account, no key)
```bash
python3 -m pipeline.run --no-ai        # builds today's draft in drafts/ using real feeds
python3 -m unittest discover -s tests  # 23 offline tests
```
With a free API key in `.env` (copy `.env.example`), drop `--no-ai` and the AI writes the summaries and a second pass checks them.

## Pipeline
`collect` (feeds) > `rank` (de-dupe, score, variety cap) > `write` (AI or extractive) > `verify` (numbers, names, quotes, links, hype) > `render` (drafts) > **you approve** > `publish` (archive).

## Layout
- `config/` sources and settings (JSON, so nothing needs installing)
- `pipeline/` the stages; `adapters/llm.py` swappable AI provider
- `drafts/` daily review notes, LinkedIn post, first comment
- `data/` issue records and logs (public news only; never subscriber data)
- `site/` the public archive; `runbook/OPERATIONS.md` is the handover
- `.github/workflows/` free daily scheduler and publish workflow

## Honest limits
- Free AI tiers can change or throttle; the project falls back to a plain extractive draft rather than failing.
- The verification gate reduces invented facts but cannot remove them; read the sources before posting.
- Ranking has no editorial taste; your review is the quality control.
