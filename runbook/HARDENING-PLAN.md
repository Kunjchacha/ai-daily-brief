# Hardening plan: prove the daily LinkedIn brief works (3 Nov 2026)

Goal: every day, by about 15:00 IST there is a draft, a score you can trust, and either a queued post or a clear alert, with no duplicates and nothing posted without your yes. All times are IST.

Rule for this plan: a step is only "done" when its check passed, not when the code was written.

| # | Risk found | Fix | Proof (pass means) | Status |
|---|---|---|---|---|
| 1 | The tests used the fixed date 2026-11-03. Once that day had an approved issue, the tests failed, and the workflow runs the tests BEFORE building a draft, so a failing test would have blocked the daily draft | The run-cap tests now redirect the approval-folder check to a temporary folder | `python3 -m unittest discover -s tests` passes on a repo that holds an approved issue for that date | Done: 84 pass |
| 2 | The review agent never audited the "Why it matters" line, and let two over-reaching lines through | The claim audit now includes that line; hedge words are checked in it too (the hedge check was never wired in before) | Tests: why line reaches the checker; hedged why line caps at 70 | Done |
| 3 | A headline used as "evidence" proved nothing but scored 92 | A headline-style quote earns half the quote points and caps the story at 89 | Replay of the real Nvidia item: 92 became 82 | Done |
| 4 | An old event (signed "at the end of September") in a 5-hour-old story scored 92 | A month name earlier than the story's own date caps the story at 85 | Test: September in a November story scores below 90; a later month ("in December") does not | Done |
| 5 | The 14:00 IST cron has never fired on its own | A backup cron at 15:00 IST was added (the draft job skips a day that already has a draft) | A scheduled-event run appears in Actions on 4 Nov. A one-off check task runs at 15:30 IST on 4 Nov and tells you | Waiting for 4 Nov |
| 6 | The Buffer queue task had never run | Run it once now against 3 Nov, which is already queued | Result: it stops at Step 0, queues nothing, Buffer still shows exactly 1 post | FAILED to prove: see results |

## What still cannot be proven today
- Only a real day shows whether GitHub fires the cron. That is why step 5 has a dated check.
- The 90% auto-queue path has never been exercised, because no issue has scored 90 or above yet. Until it has, treat every issue as "needs your yes" (the 14-day trial recommended earlier).

## Results log
- 3 Nov 15:50 IST: 90 tests pass; the replay of the real Nvidia item went from 92 to 82.
- 3 Nov 15:53 IST: the 15:00 IST Buffer task started at 15:10 IST but has made no progress since 15:10 IST (three tool calls, then nothing). It is almost certainly waiting on permission prompts, because its tools were never pre-approved. Tomorrow's run would stall the same way. Fix: open the task's page, click Run now once and approve (or always allow) its prompts.
- 4 Nov 15:30 IST: one-off task `ai-daily-brief-cron-check-4-nov` reports whether the cron fired. It also needs one Run now to pre-approve its tools.
