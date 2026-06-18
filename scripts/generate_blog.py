#!/usr/bin/env python3
"""Weekly AI & NLP research blog generator.

Fetches real signals (Hacker News AI stories + recent arXiv cs.CL papers),
asks Google Gemini to synthesize a weekly digest, and writes a dated
markdown post + updates blog/index.json manifest.

Env: GEMINI_API_KEY (GitHub repo secret).
Run in CI weekly; also runnable locally with the key exported.
"""
import json
import os
import re
import urllib.request
from datetime import datetime, timezone

# ----- Config -----
GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={{key}}"
HF_AUTHOR_FOCUS = ("AI, NLP, LLMs, vision-language models, agentic AI, "
                   "document intelligence, RAG, and information extraction")

def http_get_json(url, timeout=15):
    req = urllib.request.Request(url, headers={"User-Agent": "pritamdeka-blog-bot/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))

def fetch_hn_ai_stories(limit=8):
    """Top recent Hacker News stories with AI/ML in the title."""
    try:
        ids = http_get_json("https://hacker-news.firebaseio.com/v0/topstories.json")[:30]
        stories = []
        for sid in ids:
            s = http_get_json(f"https://hacker-news.firebaseio.com/v0/item/{sid}.json")
            title = (s.get("title") or "").lower()
            if any(k in title for k in ("ai", "llm", "gpt", "model", "language model",
                                        "transformer", "rag", "agent", "nlp", "diffusion",
                                        "open source", "anthropic", "gemini", "claude")):
                stories.append({"title": s.get("title"), "url": s.get("url", ""),
                                "score": s.get("score", 0)})
            if len(stories) >= limit:
                break
        return stories
    except Exception as e:
        print(f"HN fetch failed: {e}")
        return []

def fetch_arxiv_cl_papers(limit=8):
    """Recent arXiv cs.CL (Computation & Language) papers."""
    try:
        url = ("http://export.arxiv.org/api/query?search_query=cat:cs.CL"
               f"&start=0&max_results={limit}&sortBy=submittedDate&sortOrder=descending")
        req = urllib.request.Request(url, headers={"User-Agent": "pritamdeka-blog-bot/1.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            xml = r.read().decode("utf-8")
        entries = []
        for m in re.finditer(r"<entry>(.*?)</entry>", xml, re.S):
            block = m.group(1)
            title = re.search(r"<title>(.*?)</title>", block, re.S)
            link = re.search(r'<id>(.*?)</id>', block)
            summary = re.search(r"<summary>(.*?)</summary>", block, re.S)
            if title:
                entries.append({
                    "title": re.sub(r"\s+", " ", title.group(1)).strip(),
                    "url": link.group(1).strip() if link else "",
                    "summary": re.sub(r"\s+", " ", summary.group(1)).strip()[:300] if summary else ""
                })
        return entries
    except Exception as e:
        print(f"arXiv fetch failed: {e}")
        return []

def call_gemini(prompt):
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY not set")
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 2048},
    }
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        GEMINI_URL.format(key=key),
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.loads(r.read().decode("utf-8"))
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        raise RuntimeError(f"Unexpected Gemini response: {json.dumps(data)[:400]}")

def build_prompt(hn, arxiv):
    hn_list = "\n".join(f"- {s['title']} ({s['url']})" for s in hn) or "(none)"
    arxiv_list = "\n".join(f"- {p['title']} ({p['url']})" for p in arxiv) or "(none)"
    return f"""You are a concise, technically accurate AI research blogger writing for
Dr. Pritam Deka's personal site (an AI engineer & NLP researcher).
Write a weekly digest in Markdown of the most notable developments in
{HF_AUTHOR_FOCUS}.

Use ONLY the signals below as your factual basis. Do not invent stories,
links, or numbers. If a signal is thin, keep the post short rather than
padding.

## This week's Hacker News AI stories
{hn_list}

## This week's arXiv cs.CL papers
{arxiv_list}

Output format (Markdown only, no preamble):
# <Week of YYYY-MM-DD>

A 2-3 sentence intro.

## Top stories
- **<title>** — one sentence + link

## Notable papers
- **<title>** — one sentence on the contribution + arXiv link

## Takeaway
One short paragraph on what matters for applied AI / NLP engineers this week.
"""

def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:60]

def main():
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d")
    week = now.strftime("%Y-W%U")

    hn = fetch_hn_ai_stories()
    arxiv = fetch_arxiv_cl_papers()
    if not hn and not arxiv:
        print("No signals fetched — skipping this week.")
        return

    prompt = build_prompt(hn, arxiv)
    post_md = call_gemini(prompt)

    # Extract title from the markdown (first # line)
    title_match = re.search(r"^#\s+(.+)$", post_md, re.M)
    title = title_match.group(1).strip() if title_match else f"Weekly AI Digest — {date_str}"
    slug = slugify(title) or f"digest-{date_str}"

    os.makedirs("blog", exist_ok=True)
    post_path = f"blog/{date_str}-{slug}.md"
    with open(post_path, "w", encoding="utf-8") as f:
        f.write(post_md)

    # Update manifest
    manifest_path = "blog/index.json"
    try:
        with open(manifest_path, encoding="utf-8") as f:
            manifest = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        manifest = []

    manifest.insert(0, {
        "date": date_str,
        "week": week,
        "title": title,
        "file": post_path,
        "excerpt": re.sub(r"[#*\[\]()>]", "", post_md).strip()[:180] + "...",
    })
    manifest = manifest[:52]  # keep last year

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"Blog post generated: {post_path}")

if __name__ == "__main__":
    main()
