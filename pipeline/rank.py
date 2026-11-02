"""Stage 2: filter to AI topics, merge duplicate stories, score, and pick the best candidates."""
import datetime as dt
import json
import re

from .common import ROOT, UTC, jaccard, tokens

AI_RE = re.compile(
    r"\b(ai|a\.i\.|llms?|gpt\S*|chatgpt|claude|anthropic|openai|gemini|deepmind|mistral|llama|copilot|"
    r"agents?|agentic|machine learning|deep learning|neural|transformers?|diffusion|generative|"
    r"foundation models?|language models?|robotics?|nvidia|inference|fine-?tun\w*|rag|prompts?|"
    r"reasoning models?|benchmarks?|open-?source models?)\b", re.I)
SAME_STORY = 0.55
REPEAT_HEADLINE = 0.6


def load_history(days, today):
    """URLs and headline token sets from recent issues, so we don't repeat ourselves."""
    urls, heads = set(), []
    folder = ROOT / "data" / "issues"
    for f in sorted(folder.glob("*.json"))[-days:]:
        try:
            issue = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if issue.get("date") == str(today):
            continue
        for it in issue.get("items", []):
            urls.add(it.get("canonical") or it.get("url", ""))
            heads.append(tokens(it.get("headline", "")))
    return urls, heads


def is_ai_related(item):
    return bool(AI_RE.search(item["title"] + " " + item["text"][:400]))


def cluster(items):
    """Greedy clustering: same canonical URL or very similar titles count as one story."""
    clusters = []
    for it in sorted(items, key=lambda x: -x["authority"]):
        tk = tokens(it["title"])
        home = None
        for c in clusters:
            if it["canonical"] == c["lead"]["canonical"] or jaccard(tk, c["tokens"]) >= SAME_STORY:
                home = c
                break
        if home:
            home["also"].append(it["source"])
            home["points"] += it.get("points", 0)
        else:
            clusters.append({"lead": it, "tokens": tk, "also": [], "points": it.get("points", 0)})
    return clusters


def score(c, now, lookback_hours, seen_urls, seen_heads):
    lead = c["lead"]
    if lead["canonical"] in seen_urls:
        return -100.0
    age_h = max(0.0, (now - dt.datetime.fromisoformat(lead["published"])).total_seconds() / 3600)
    recency = 3.0 * max(0.0, 1 - age_h / lookback_hours)
    coverage = min(len(set(c["also"])), 3) * 1.5
    hn = min(c["points"] / 100.0, 3.0)
    s = lead["authority"] * 2.0 + recency + coverage + hn
    if any(jaccard(c["tokens"], h) >= REPEAT_HEADLINE for h in seen_heads):
        s -= 5.0
    return round(s, 2)


def has_substance(lead, min_text):
    """A story needs real text to summarise honestly; a bare title is not enough."""
    return lead["text"].strip().lower() != lead["title"].strip().lower() and len(lead["text"]) >= min_text


def diversify(ranked, per_source):
    """Keep at most `per_source` stories from any one publisher so one source can't dominate an issue."""
    counts, out = {}, []
    for c in ranked:
        name = c["lead"]["source"]
        if per_source and counts.get(name, 0) >= per_source:
            continue
        counts[name] = counts.get(name, 0) + 1
        out.append(c)
    return out


def rank(items, now, lookback_hours, history_days, top_n, today, min_text=0, deny=(), per_source=0):
    deny_re = [re.compile(p, re.I) for p in deny]
    wanted = [i for i in items if ((not i["filter"]) or is_ai_related(i)) and not any(r.search(i["title"]) for r in deny_re)]
    seen_urls, seen_heads = load_history(history_days, today)
    out = [c for c in cluster(wanted) if has_substance(c["lead"], min_text)]
    for c in out:
        c["score"] = score(c, now, lookback_hours, seen_urls, seen_heads)
        c["also"] = sorted(set(c["also"]))
    out = [c for c in out if c["score"] > 0]
    out.sort(key=lambda c: -c["score"])
    return diversify(out, per_source)[:top_n]
