# Content plan: up to four posts a day (4 Nov 2026)

## Why
Confirmed-fact AI news alone gives about 3 solid stories a day. Two news posts a day left the 5 Nov morning issue with 2 stories. So the other slots use other kinds of post, held to the same rule: **every fact comes from a data source, a paper's own abstract, or a bank the owner has reviewed, never from an AI's memory.**

## The four slots (IST) and what goes in them
| Slot | Time | Preferred format | If it cannot be built |
|---|---|---|---|
| Morning | 08:00 | News brief (3+ confirmed stories) | Explainer |
| Midday | 12:30 | Open-source spotlight (GitHub repo) or model spotlight (Hugging Face), alternating by weekday | The other spotlight, then an explainer |
| Afternoon | 17:00 | Research in plain English (Mon, Wed, Fri) or an explainer (other days) | The other one, then a question |
| Evening | 20:00 | News brief | Question |

The 14:00 IST run builds this evening's issue and tomorrow's morning, midday and afternoon issues. Keys: `2026-11-05-morning`, `-midday`, `-afternoon`, `-evening`.

## Where each format's facts come from
- **News:** the existing pipeline (facts gate, review agent).
- **Open-source spotlight:** GitHub's own data (stars, licence, language, creation date, the owner's description). No AI. Skips repos with no licence, forks, spam words, non-English descriptions and anything featured before.
- **Model spotlight:** Hugging Face's own trending list (downloads, likes, licence, task). No AI. Needs a real licence.
- **Research in plain English:** the most up-voted paper on Hugging Face Daily Papers. One AI call turns the abstract into two plain sentences; the post is kept only if its quoted result sentence is a word-for-word match in the abstract and it adds no new numbers. If not, the post uses the abstract's own sentences. Always labelled as the authors' claims.
- **Explainer:** `config/explainers.json`, 13 entries written for this project, each with a source link. You review the wording once; they rotate.
- **Question:** `config/questions.json`, 10 engagement prompts. They state no facts and ask readers not to share customer or company data (Agilisys policy).

## Re-think: what could go wrong
1. **Volume erodes trust.** Every format is fact-grounded and every post is approved by you. The evening question is the easiest slot to skip. Start with 3 and add the 4th if it works.
2. **Approval load.** Four posts a day means four short files. Each is one item with the same Approve step.
3. **Quiet days.** Fallbacks guarantee every slot is filled, but a fallback explainer is evergreen, not news. Only 13 explainers exist, so after about 2 weeks they repeat unless more are added.
4. **AI quota.** Two news runs use about 6 AI calls, the paper 1 more, against a cap of 10 a day.
5. **Star counts can be gamed.** Spotlight posts say stars show popularity, not quality, and you read each one before it goes out.
6. **Buffer effort.** Each approved post still has to be queued in Buffer. Setting Buffer's posting schedule to the four slots would let one click add each post to the next slot (your decision; a Buffer setting).

## Changing it
Slot times and the weekday plan are in `pipeline/pack.py` (`SLOT_TIMES`, `plan`). Add explainers and questions by editing the two JSON files in `config/`.
