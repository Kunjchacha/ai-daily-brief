# 100 ways to teach AI on LinkedIn: a plan (5 Nov 2026)

Status: PLAN ONLY. Nothing here is built yet except what is marked as built. All times are IST. Cost target: £0.

## 1. What the research gave us
Sources are vendor and creator blogs unless stated, so treat figures as indicative.

- **Documents (PDF carousels) are the most saveable format;** step-by-step, comparison and 'mistake' hooks are the commonly cited carousel types, usually 8 to 12 slides ([Buffer](https://buffer.com/resources/linkedin-carousel-examples/), [Plann That](https://www.plannthat.com/linkedin-carousel-post-ideas/)).
- **Video:** LinkedIn autoplays muted, so the first seconds and burned-in captions must carry the meaning; under 30 seconds completes best by vendor claims ([Opus](https://www.opus.pro/blog/linkedin-video-caption-subtitle-best-practices), [Ligosocial](https://ligosocial.com/en/blog/linkedin-video-post-best-practices)). Upload natively.
- **Explainer styles that are cheap to make:** whiteboard, kinetic typography (animated text and numbers) and cut-out styles ([WordStream](https://jump.wordstream.com/types-of-explainer-videos), [Wyzowl](https://www.wyzowl.com/explainer-video-style/)).
- **Free data:** Epoch AI's models dataset is a daily-updated CSV under Creative Commons Attribution ([Epoch AI](https://epoch.ai/benchmarks/use-this-data)). Our World in Data's own charts are CC BY, but third-party data on it keeps the original licence ([OWID](https://ourworldindata.org/faq)). The Stanford AI Index's reuse terms are unverified, so we will not use its charts until checked. The Hugging Face, GitHub and arXiv APIs already work in this project.
- **Not found:** no reliable source tested quizzes, scorecards or analogy animations for saves. Those are hypotheses to test on our own analytics.

## 2. What we can make with what is on this Mac, at £0
| Tool | Available | Use |
|---|---|---|
| Chrome (headless) | yes | Posters, slides, PDF carousels, PNG charts from SVG/HTML |
| Python 3 standard library | yes | Fetch data, draw SVG charts, build slides |
| Swift (from the Instagram project: animate, frame, encode, mux) | yes | Turn frames into an MP4 |
| macOS `say` | yes | Optional voice-over |
| ffmpeg, Node, matplotlib, ImageMagick | **no** | Not needed; avoid adding them |

Animations are therefore: HTML/CSS/SVG scenes, captured frame by frame in Chrome, encoded to MP4 with the existing Swift tools, captions burned into the frame.

## 3. Fact-safety rule for every idea
- **Auto:** the numbers come from a live free data source; a script draws them. No AI judgement of facts.
- **Bank:** written and reviewed once in this project, each with a source link; no claims about any product; you approve each.
- **Manual:** needs a person to check a source first (policy, vendor, survey). Not built until you supply or confirm the source.
- Animations of how a model works are labelled **'simplified illustration'**.
- Every post that touches data sharing carries 'do not paste customer or company data' (Agilisys policy).

## 4. Topic coverage
| Code | Topic | Ideas |
|---|---|---|
| T1 | How AI works | 11 |
| T2 | Prompting | 7 |
| T3 | AI at work | 7 |
| T4 | Data & spreadsheets | 4 |
| T5 | Safety & security | 4 |
| T6 | Ethics & bias | 4 |
| T7 | Law, policy & governance | 5 |
| T8 | Industry & news | 4 |
| T9 | Open source & models | 8 |
| T10 | Research & benchmarks | 11 |
| T11 | Hardware, data centres & energy | 5 |
| T12 | Agents & automation | 4 |
| T13 | Careers & skills | 4 |
| T14 | AI in sectors | 4 |
| T15 | History | 5 |
| T16 | Tools & comparisons | 4 |
| T17 | Creative AI (image, audio, video) | 4 |
| T18 | Trust & evaluation | 5 |

No topic has fewer than 4 ideas, and none has more than 11. Sector, careers and ethics ideas are mostly 'Manual' because they need a checked source first.

## 5. The 100 ideas
Legend. Build: S small (hours), M medium (a day), L large (several days, first one builds the reusable engine). Run: Auto = a script makes it from live data; Bank = reviewed once, reused; Manual = needs a human check first.

### A. Infographics and cheat sheets
| # | Idea | Format | Topic | Fact basis | Build | Run |
|---|---|---|---|---|---|---|
| 1 | Anatomy of a prompt: a labelled diagram | Infographic | T2 | Own writing | S | Bank |
| 2 | How an LLM answers: tokens in, next-word choices, answer out | Infographic | T1 | Own writing + Wikipedia LLM | S | Bank |
| 3 | AI terms on one page: 12-term poster | Infographic | T1 | Explainer bank | S | Bank |
| 4 | Which AI tool for which job: a decision flowchart | Flowchart | T16 | Own writing, no product claims | S | Bank |
| 5 | Hallucination spotter: a checklist poster | Infographic | T18 | Wikipedia: hallucination | S | Bank |
| 6 | Before you paste: a traffic-light sheet for public, internal and customer data | Infographic | T7 | Own policy rules, no PII | S | Bank |
| 7 | Model sizes made visual: parameters as a scale of everyday objects | Infographic | T1 | Epoch AI data (CC BY) [verify] | M | Auto |
| 8 | Local vs cloud AI: a side-by-side sheet | Comparison | T9 | Own writing | S | Bank |
| 9 | The AI stack: chips, cloud, models, apps as layers | Infographic | T11 | Own writing | S | Bank |
| 10 | Prompt patterns cheat sheet: role, format, examples, limits | Infographic | T2 | Own writing | S | Bank |

### B. Charts from free live data
| # | Idea | Format | Topic | Fact basis | Build | Run |
|---|---|---|---|---|---|---|
| 11 | Trending models this week: a downloads bar chart | Chart | T9 | Hugging Face API | M | Auto |
| 12 | Fastest-growing AI repos this fortnight: a stars chart | Chart | T9 | GitHub API | M | Auto |
| 13 | AI papers per week on arXiv: a line chart | Chart | T10 | arXiv API | M | Auto |
| 14 | Licences of trending models: a donut chart | Chart | T9 | Hugging Face API | M | Auto |
| 15 | Which tasks are trending: text vs image vs audio share | Chart | T17 | Hugging Face API | M | Auto |
| 16 | Languages of new AI repos: a ranked bar chart | Chart | T12 | GitHub API | M | Auto |
| 17 | Notable AI models per year | Chart | T10 | Epoch AI CSV (CC BY) [verify] | M | Auto |
| 18 | Training compute over time on a log scale | Chart | T1 | Epoch AI CSV (CC BY) [verify] | M | Auto |
| 19 | AI data centres and chips snapshot | Chart | T11 | Epoch AI open databases [verify] | M | Auto |
| 20 | Who releases models, and how often | Chart | T8 | Epoch AI CSV [verify] | M | Auto |

### C. Short animations (30 to 45 seconds)
| # | Idea | Format | Topic | Fact basis | Build | Run |
|---|---|---|---|---|---|---|
| 21 | Tokens: a sentence splitting into pieces | Animation | T1 | Google ML glossary | L | Bank |
| 22 | Next-word prediction: probability bars shifting | Animation | T1 | Own illustration, labelled as simplified | L | Bank |
| 23 | Context window as a sliding frame | Animation | T1 | Wikipedia LLM | L | Bank |
| 24 | Temperature: one prompt, calmer to wilder answers | Animation | T2 | Own illustration, labelled as simplified | L | Bank |
| 25 | Attention: words lighting up their links | Animation | T1 | Wikipedia: Transformer | L | Bank |
| 26 | RAG in 30 seconds: question, lookup, answer | Animation | T12 | Wikipedia: RAG | L | Bank |
| 27 | Prompt injection: an instruction hidden in a page | Animation | T5 | OWASP LLM Top 10 | L | Bank |
| 28 | The agent loop: plan, act, observe, repeat | Animation | T12 | Wikipedia: Intelligent agent | L | Bank |
| 29 | Embeddings: meaning as points on a map | Animation | T1 | Wikipedia: Word embedding | L | Bank |
| 30 | Bias in a hiring screen: how a skewed sample skews the output (simplified illustration) | Animation | T6 | Worked example, numbers shown | L | Bank |

### D. Quizzes and interaction
| # | Idea | Format | Topic | Fact basis | Build | Run |
|---|---|---|---|---|---|---|
| 31 | Spot the hallucination: three statements, one invented | Quiz | T18 | Answer with a source | S | Bank |
| 32 | Which prompt is better? A versus B with the reason | Quiz | T2 | Own writing | S | Bank |
| 33 | Guess the token count of a paragraph | Quiz | T1 | Computed by script | S | Auto |
| 34 | Real or made-up AI headline? | Quiz | T18 | Real ones from our own history | S | Auto |
| 35 | Match the term to the picture | Quiz | T1 | Explainer bank | M | Bank |
| 36 | Match the AI task to the right kind of tool | Quiz | T16 | Own writing | S | Bank |
| 37 | Fix this prompt: before and after | Quiz | T2 | Own writing | S | Bank |
| 38 | A short poll: which AI task do you trust least? | Poll | T6 | Opinion, no facts | S | Bank |
| 39 | Name that model type from a one-line description | Quiz | T9 | Explainer bank | S | Bank |
| 40 | Spot the bias: a small table with a skew | Quiz | T6 | Worked example, numbers shown | M | Bank |

### E. Timelines and history
| # | Idea | Format | Topic | Fact basis | Build | Run |
|---|---|---|---|---|---|---|
| 41 | AI in 12 milestones | Timeline | T15 | Wikipedia: history of AI | M | Bank |
| 42 | From the Turing test to today | Timeline | T15 | Wikipedia | M | Bank |
| 43 | A year of AI models: releases over the last 12 months | Timeline | T8 | Epoch AI [verify] | M | Auto |
| 44 | The AI winters explained | Timeline | T15 | Wikipedia: AI winter | M | Bank |
| 45 | The paper that started it: Attention Is All You Need in 5 slides | Carousel | T10 | The paper (arXiv) | M | Bank |
| 46 | Games and AI: chess, Go and what came next | Timeline | T15 | Wikipedia | M | Bank |
| 47 | How image generation evolved | Timeline | T17 | Wikipedia | M | Bank |
| 48 | How we got to chatbots: rules, statistics, neural networks | Timeline | T15 | Wikipedia | M | Bank |
| 49 | UK AI policy: a timeline | Timeline | T7 | gov.uk pages | M | Manual |
| 50 | EU AI Act: the key dates | Timeline | T7 | EU official pages | M | Manual |

### F. Myths, comparisons and scorecards
| # | Idea | Format | Topic | Fact basis | Build | Run |
|---|---|---|---|---|---|---|
| 51 | Myth vs reality series | Carousel | T18 | Linked source per myth | M | Bank |
| 52 | Small model vs big model: side by side | Comparison | T9 | Wikipedia: distillation | S | Bank |
| 53 | Open weights vs open source | Comparison | T9 | Wikipedia | S | Bank |
| 54 | Chatbot vs agent: a comparison table | Comparison | T12 | Wikipedia | S | Bank |
| 55 | Search engine or AI assistant: when to use which | Comparison | T16 | Own writing | S | Bank |
| 56 | Free vs paid AI tools: what you actually get | Comparison | T16 | Vendor pages, changes often | M | Manual |
| 57 | AI safety, AI security and AI ethics: a Venn diagram | Infographic | T5 | Own writing | S | Bank |
| 58 | AI in education: what teachers can safely try | Infographic | T14 | Education department guidance [verify] | M | Manual |
| 59 | Prompting, fine-tuning or RAG: a decision tree | Flowchart | T4 | Wikipedia | S | Bank |
| 60 | Model card scorecard: what to check before you use a model | Scorecard | T9 | Hugging Face model cards | S | Bank |

### G. Practical workflow cards (10 built)
| # | Idea | Format | Topic | Fact basis | Build | Run |
|---|---|---|---|---|---|---|
| 61 | Meeting notes into clear actions | Workflow card | T3 | Own writing | S | Bank |
| 62 | Draft a reply in your own tone | Workflow card | T3 | Own writing | S | Bank |
| 63 | Summarise a long document with page references | Workflow card | T3 | Own writing | S | Bank |
| 64 | Get an Excel formula you can test | Workflow card | T4 | Own writing | S | Bank |
| 65 | Clean a messy list into a table | Workflow card | T4 | Own writing | S | Bank |
| 66 | Prepare better questions for a meeting | Workflow card | T3 | Own writing | S | Bank |
| 67 | Explain a hard idea at three levels | Workflow card | T2 | Own writing | S | Bank |
| 68 | Tighten your writing, keep your voice | Workflow card | T3 | Own writing | S | Bank |
| 69 | Compare options with a table you can defend | Workflow card | T3 | Own writing | S | Bank |
| 70 | Break a vague task into a plan with risks | Workflow card | T3 | Own writing | S | Bank |

### H. Research in pictures
| # | Idea | Format | Topic | Fact basis | Build | Run |
|---|---|---|---|---|---|---|
| 71 | Paper of the day in plain English | Research | T10 | Hugging Face Daily Papers + abstract | S | Auto |
| 72 | A paper in 5 slides: problem, method, result, caveat, so what | Carousel | T10 | The abstract | M | Auto |
| 73 | The numbers in the abstract, as moving big type | Animation | T10 | The abstract | L | Auto |
| 74 | What the authors did not claim: the limits | Carousel | T10 | The paper's own limitations | M | Manual |
| 75 | Jargon decoder for one paper: five terms | Infographic | T10 | The abstract + glossary | M | Auto |
| 76 | Has the code been released? Papers with a GitHub link | Chart | T10 | Hugging Face Daily Papers API | M | Auto |
| 77 | Most-discussed papers this week: a ranked chart | Chart | T10 | Hugging Face Daily Papers API | M | Auto |
| 78 | Benchmarks explained: what a score does and does not measure | Infographic | T10 | Benchmark papers | M | Bank |
| 79 | Paper versus press headline | Comparison | T18 | Paper + article, manual check | M | Manual |
| 80 | Career paths into AI work: analyst, product, data, security | Infographic | T13 | Own writing + cited surveys | M | Manual |

### I. Industry, work, careers and sectors
| # | Idea | Format | Topic | Fact basis | Build | Run |
|---|---|---|---|---|---|---|
| 81 | Three stories and what to do about them | Carousel | T8 | Confirmed news only | M | Auto |
| 82 | The weekly scoreboard: five numbers from the week | Chart | T8 | Our own APIs | M | Auto |
| 83 | An AI skills map for analysts, managers and developers | Infographic | T13 | Own writing + cited surveys | M | Manual |
| 84 | Before and after: how long a task took with and without AI | Chart | T13 | The owner's own timings only | M | Manual |
| 85 | AI in the public sector: five documented use cases | Carousel | T14 | gov.uk case studies | M | Manual |
| 86 | AI in healthcare: what regulators say | Carousel | T14 | Regulator pages | M | Manual |
| 87 | Spreadsheet jobs worth automating: five examples | Carousel | T4 | Own writing | S | Bank |
| 88 | Questions to ask a vendor selling you AI | Checklist | T7 | Own writing | S | Bank |
| 89 | An AI project risk register template | Template | T7 | Own writing | S | Bank |
| 90 | Tasks, not jobs: what AI changes first | Carousel | T13 | Cited surveys only | M | Manual |

### J. Safety, law, infrastructure and creative AI
| # | Idea | Format | Topic | Fact basis | Build | Run |
|---|---|---|---|---|---|---|
| 91 | Prompt injection as a comic strip | Comic | T5 | OWASP | M | Bank |
| 92 | Deepfakes: five signs and three checks | Infographic | T5 | Reputable guidance pages | M | Manual |
| 93 | Bias in a model: one worked example with numbers | Chart | T6 | Worked example, numbers shown | M | Bank |
| 94 | Energy per AI query: what is known and what is not | Infographic | T11 | Published estimates, ranges shown | M | Manual |
| 95 | Data centres by the numbers | Chart | T11 | Epoch AI database [verify] | M | Auto |
| 96 | GPU, CPU and TPU: what each is good at | Comparison | T11 | Wikipedia | S | Bank |
| 97 | How a diffusion model paints: an animation | Animation | T17 | Wikipedia: diffusion models | L | Bank |
| 98 | Voice cloning: what to know and what to check | Infographic | T17 | Reputable guidance | M | Manual |
| 99 | Public sector AI: one question an officer should ask before buying | Series | T14 | gov.uk guidance [verify] | M | Manual |
| 100 | Ask me anything about AI: reader questions answered next week | Series | T2 | Reader questions, answered with sources | M | Manual |

Counts by run type: Auto 23, Bank 60, Manual 17. By build size: L 12, M 49, S 39.

## 6. How it fits the week (two posts a day)
| Day | 08:00 flagship | 20:00 |
|---|---|---|
| Mon | Workflow card (G) | News |
| Tue | Chart of the week (B) | News |
| Wed | Myth vs reality or comparison (F) | News |
| Thu | 30-second animation (C) | News |
| Fri | Research in pictures (H) | News |
| Sat | Timeline or infographic (E, A) | Quiz (D) |
| Sun | Safety, law or creative (J) | Quiz (D) |

At this pace the flagship slot uses about one idea a day, so 100 ideas is more than three months of material, before repeating.

## 7. Build order
1. **Week 1, small and no new tools:** infographic and comparison cards through the existing carousel engine (A, F, D), plus a chart engine that draws SVG from the Hugging Face and GitHub APIs (B). Targets about 25 ideas.
2. **Week 2, data series:** arXiv and Hugging Face Daily Papers charts (B, H); verify the Epoch AI CSV and licence before using it.
3. **Weeks 3 to 4, animation engine:** one reusable HTML scene template, frame capture, MP4 encoding with the Swift tools, captions burned in. Prove it on 'Tokens' first (C).
4. **Later:** Manual items only when you supply or confirm the source.

## 8. Risks and honest limits
- The engagement claims behind these formats are from vendor blogs, so we test: two weeks of one format at a time, compare impressions and saves per post in Buffer.
- Auto charts can be dull or misleading if the data is thin; each chart states its source, date and what it does not show.
- Animation is the biggest build. Do it only after the carousels and charts prove the approach.
- Two posts a day is the research-backed cap; ideas rotate, they do not add volume.
- A personal 'Take:' line from you still matters more than any format.

## 9. Decisions for you
1. Is the topic spread right (section 4)? Anything to add or drop, for example more UK or India policy?
2. Start with week 1 (infographics, comparisons and quizzes through carousels, plus the chart engine)?
3. Are animations worth the build cost now, or after two weeks of data?
4. Should 'Manual' items wait until you can provide sources?

## 10. Week one: built (5 Nov 2026)
Built and tested, in the reviewed bank `config/decks.json` (25 decks) and the live chart engine `pipeline/charts.py` (5 charts):
- **Infographics (7):** anatomy of a prompt, AI terms on one page, before-you-paste traffic lights, the AI stack, prompt patterns, three kinds of machine learning, tasks not jobs.
- **Flowcharts (3):** how a model writes an answer, which tool for which job, prompting vs fine-tuning vs RAG.
- **Comparisons (7):** local vs cloud, small vs big models, open weights vs open source, chatbot vs agent, search vs assistant, CPU/GPU/TPU, safety vs security vs ethics.
- **Checklists (3):** hallucination spotter, model card checklist, questions for an AI vendor.
- **Quizzes (5):** spot the false statement, which prompt is better, safe or risky to paste, fix this prompt, name that term.
- **Live charts (5):** downloads of trending models, newest AI repos by stars, licences of trending models, what trending models do, AI papers per week on arXiv. The kind rotates weekly; every number comes straight from the API.

Weekday flagship now: Mon workflow card, Tue chart, Wed myth vs reality, Thu infographic, Fri research, Sat comparison, Sun quiz. If a format cannot be built, it falls back through workflow card, myth, infographic, comparison, quiz, explainer.

Still to do: week two data series (Epoch AI, after checking its licence), animation engine, and the Manual items.
