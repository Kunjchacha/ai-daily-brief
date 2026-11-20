# Review notes: 2026-11-21-evening

- Status: **ready_for_review** (nothing is posted until you approve it)
- Review agent score: **37%, skip today** (the weakest item sets the score; advice only)
  - 92% grade B: METR report shows exponential AI capability growth but weaker judgement performance (all checks passed)
  - 92% grade B: PostgreSQL 19 adds read‑your‑writes consistency via WAIT FOR LSN (all checks passed)
  - 57% grade B: Nvidia to cease H200 chip sales in China (1 claim(s) unsupported by the article)
  - 57% grade B: Widespread tech outages reported this week (1 claim(s) unsupported by the article)
  - 37% grade B: Anthropic founders each receive $280 million from IPO (evidence quote not found in the full article; 1 claim(s) unsupported by the article)
- Writing mode: llm
- Items kept: 5 | dropped: 4

## What each item rests on
Check that each is a CONFIRMED FACT (something that has happened or been officially announced), not a rumour or opinion.

1. **METR report shows exponential AI capability growth but weaker judgement performance**: announced; MIT Technology Review, 1 hours old
   Source says: "A new report from the AI evaluation nonprofit METR finds that some AI capabilities are continuing to improve along an exponential trajectory"
2. **PostgreSQL 19 adds read‑your‑writes consistency via WAIT FOR LSN**: announced; Simon Willison, 22 hours old
   Source says: "PostgreSQL 19 adds "read-your-writes" consistency with the new WAIT FOR LSN command"
3. **Nvidia to cease H200 chip sales in China**: announced; TechCrunch, 4 hours old
   Source says: "the chipmaker said it will stop selling its H200 chips in China"
4. **Widespread tech outages reported this week**: reported; The Verge, 5 hours old
   Source says: "There was a dayslong Outlook outage"
5. **Anthropic founders each receive $280 million from IPO**: reported; TechCrunch, 18 hours old
   Source says: "Anthropic's seven founders each pocketed $280 million, while the company nabbed nearly $105 billion"

## Dropped by the verification gate
- ChatPRD creator ends free trials amid token fraud surge: second pass: The source mentions token fraud exploiting free trials, but it does not state that Claire Vo has ended or discontinued t
- Anthropic researcher claims Claude helped prove Riemann hypothesis: not a confirmed fact (writer classed it as 'rumour')
- NVIDIA and Microsoft Expand Accelerated Computing From Azure to Windows PCs: no AI fact check for this story (the AI could not handle it): not shown as a confirmed fact
- Into the Omniverse: How Developers Turn Ideas Into Simulations With Frontier AI Agents: no AI fact check for this story (the AI could not handle it): not shown as a confirmed fact

## Notes
- story 8: no usable AI output, used extractive text
- story 9: no usable AI output, used extractive text

## Your approval step (nothing goes out without it)
1. Open each source link and read it. Accuracy and judgement are your job, not the script's.
2. Open `drafts/2026-11-21-evening-issue.md`, edit anything you want, set `Include: no` on anything that is not a confirmed fact,
   replace any `[ADD YOUR LINE]`, then change `Status: DRAFT` to `Status: APPROVED` and save.
3. Run Actions > **Approve issue** with this date. It produces the final post (sources included) from YOUR text.
4. Post the final text on LinkedIn (or queue it in Buffer), then run Actions > **Publish approved issue**.
