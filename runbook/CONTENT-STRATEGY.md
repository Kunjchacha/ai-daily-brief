# Content strategy for the LinkedIn posts (4 Nov 2026)

Supersedes the four-slots-a-day idea in CONTENT-PLAN.md. All sources below are vendor and creator blogs, not LinkedIn's own documentation: the figures are indicative, and several repeat one underlying dataset. The advice is to test it on your own analytics.

## What the research says
| Question | Finding | Sources |
|---|---|---|
| Which format? | Carousels (PDF documents) get the most saves and dwell time; plain text posts get the most comments; images beat text-only; polls reach people but engage less. | [AuthoredUp](https://authoredup.com/blog/best-performing-content-on-linkedin), [Linkhub (57,809 posts)](https://linkhub.gg/en/blog/format-post-linkedin-engagement) |
| Generic AI posts? | A 2025 study of 99 influential profiles found likely-AI posts averaged 45% less engagement. Posts that start from a real source plus one first-person detail read as human. | [SocialNexis](https://socialnexis.com/guides/ai-post-performance-by-format) |
| What kind of content? | Practical, saveable content (checklists, step-by-step, frameworks) and myth-busting do well. A 40/30/20/10 mix is suggested: educational / opinion on news / personal experience / resources. | [ThoughtMint](https://thoughtmint.ai/blog/linkedin-personal-branding/) |
| How often? | One post a day, or 3 to 5 a week, is the safest default. One dataset of 1.8 million posts reports a median reach drop of over 40% per post when an account posts twice in a day. Gaps of 12 to 24 hours are advised. | [AuthoredUp](https://authoredup.com/blog/how-often-to-post-on-linkedin), [Ordinal](https://www.tryordinal.com/blog/how-often-to-post-on-linkedin) |
| What do AI news accounts add? | Summary-only feeds are a commodity. The ones with a following add a "so what" or "what to do next". | [Dupple](https://dupple.com/learn/best-ai-newsletters-2026) |
| Engagement bait? | "Comment YES" style prompts are reported as penalised; a specific, genuine question is fine. | [LinkedInPreview](https://linkedinpreview.com/blog/linkedin-engagement-bait-2026) |
| Links? | Sources disagree on whether an outbound link cuts reach, and by how much. | [Oktopost](https://www.oktopost.com/blog/outbound-links-on-linkedin/) |
| Carousel specs? | 1080x1350 PDF, about 8 to 10 slides, a hook on slide 1, one clear last slide; test on a phone. | [Decktopus](https://www.decktopus.com/blog/linkedin-carousel-best-practices) |
| Can Buffer schedule a PDF? | Buffer says LinkedIn document posts can be scheduled; whether the free plan includes it is not confirmed. | [Buffer](https://buffer.com/resources/linkedin-carousels/) |

## What was wrong with the earlier posts
They were templated (same shape every time), encyclopaedic (definitions from Wikipedia), and had no point of view, no usefulness you could save and no personal detail. That is the profile of a generic AI post.

## What changes
1. **Two posts a day, not four.** Morning (08:00 IST) is the day's flagship; evening (20:00 IST) is news. That is 12 hours apart. The midday and afternoon slots stay in the code but are switched off (`pack.active_slots` in `config/settings.json`). Run two posts a day against one a day for two weeks and compare impressions per post in Buffer before adding more.
2. **The flagship is a carousel**, chosen by weekday: Mon practical card, Tue news, Wed myth-buster, Thu practical card, Fri research in plain English, Sat open-source spotlight, Sun myth-buster. If a format cannot be built, it falls back to a practical card, then a myth-buster, then an explainer.
3. **Practical cards ("AI at work")**: a task, three steps, a copy-and-paste prompt, what to check, the mistake to avoid. 10 so far in `config/workflows.json`. They state no facts about any product, and each carries the reminder not to paste customer or company data.
4. **Myth vs reality**: 5 so far in `config/myths.json`, each tied to a source page.
5. **A "Take:" line on every post.** One sentence of your own experience or opinion. This is the biggest lever against a generic feel, and only you can write it. It is optional, but posts without one should be expected to do worse.
6. **News keeps its facts-only gate**; the evening digest is unchanged (you rejected a reader-question line there).

## What I cannot do for you
I cannot invent personal experience, and I should not. The cards give you the material; your sentence on the `Take:` line gives it a voice.

## Open decisions
- Whether to attach each card's PDF in Buffer (needs a test on the free plan) or post text plus a single image.
- Whether to keep the closing questions (they are specific, not "comment YES").
- Whether to add a short "so what" to every news story (the research says it sets news posts apart).
