#!/usr/bin/env python3
"""Generate the weekly AI/NLP digest from public HN and arXiv signals.

Synthesis order: Gemini, Groq-hosted open models, then a deterministic
source-based fallback. The workflow remains useful if either API is unavailable.
"""
import json
import os
import re
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent?key={{key}}"
)
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_GROQ_MODELS = (
    "llama-3.3-70b-versatile",
    "openai/gpt-oss-20b",
    "llama-3.1-8b-instant",
)
AUTHOR_FOCUS = (
    "AI, NLP, LLMs, vision-language models, agentic AI, document intelligence, "
    "RAG, and information extraction"
)


def http_request(url, timeout=20, data=None, headers=None, attempts=3):
    request_headers = {
        "User-Agent": "pritamdeka-blog-bot/1.1 (+https://pritamdeka.com/blog)",
        **(headers or {}),
    }
    last_error = None
    for attempt in range(attempts):
        try:
            request = urllib.request.Request(url, data=data, headers=request_headers)
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read()
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as error:
            last_error = error
            if attempt + 1 < attempts:
                time.sleep(2 ** attempt)
    raise last_error


def http_get_json(url, timeout=20, attempts=3):
    return json.loads(
        http_request(url, timeout=timeout, attempts=attempts).decode("utf-8")
    )


def fetch_hn_ai_stories(limit=8):
    """Return recent high-ranking HN stories with AI-related titles."""
    try:
        ids = http_get_json(
            "https://hacker-news.firebaseio.com/v0/topstories.json",
            timeout=15,
            attempts=2,
        )[:40]
        stories = []
        keywords = (
            "ai", "llm", "gpt", "model", "language model", "transformer",
            "rag", "agent", "nlp", "diffusion", "open source", "anthropic",
            "gemini", "claude",
        )
        for story_id in ids:
            story = http_get_json(
                f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json",
                timeout=8,
                attempts=1,
            )
            title = (story.get("title") or "").lower()
            if any(keyword in title for keyword in keywords):
                stories.append({
                    "title": story.get("title", ""),
                    "url": story.get("url", ""),
                    "score": story.get("score", 0),
                })
            if len(stories) >= limit:
                break
        return stories
    except Exception as error:
        print(f"HN fetch failed: {type(error).__name__}: {error}")
        return []


def fetch_arxiv_cl_papers(limit=8):
    """Return recent arXiv cs.CL papers."""
    try:
        url = (
            "https://export.arxiv.org/api/query?search_query=cat:cs.CL"
            f"&start=0&max_results={limit}&sortBy=submittedDate&sortOrder=descending"
        )
        xml = http_request(url).decode("utf-8")
        entries = []
        for match in re.finditer(r"<entry>(.*?)</entry>", xml, re.S):
            block = match.group(1)
            title = re.search(r"<title>(.*?)</title>", block, re.S)
            link = re.search(r"<id>(.*?)</id>", block)
            summary = re.search(r"<summary>(.*?)</summary>", block, re.S)
            if title:
                entries.append({
                    "title": re.sub(r"\s+", " ", title.group(1)).strip(),
                    "url": link.group(1).strip() if link else "",
                    "summary": (
                        re.sub(r"\s+", " ", summary.group(1)).strip()[:300]
                        if summary else ""
                    ),
                })
        return entries
    except Exception as error:
        print(f"arXiv fetch failed: {type(error).__name__}: {error}")
        return []


def call_gemini(prompt):
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY not set")
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 2048},
    }
    raw = http_request(
        GEMINI_URL.format(key=key),
        timeout=60,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        attempts=2,
    )
    data = json.loads(raw.decode("utf-8"))
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        raise RuntimeError(f"Unexpected Gemini response: {json.dumps(data)[:400]}")


def groq_models():
    configured = os.environ.get("GROQ_MODELS", "")
    models = tuple(model.strip() for model in configured.split(",") if model.strip())
    return models or DEFAULT_GROQ_MODELS


def call_groq(prompt):
    """Try configured Groq models in order and return text plus the model used."""
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        raise RuntimeError("GROQ_API_KEY not set")

    failures = []
    for model in groq_models():
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Return only the requested Markdown. Be concise, factual, "
                        "and use only the source signals in the user prompt."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.7,
            "max_completion_tokens": 2048,
        }
        try:
            raw = http_request(
                GROQ_URL,
                timeout=60,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                },
                attempts=1,
            )
            data = json.loads(raw.decode("utf-8"))
            content = data["choices"][0]["message"]["content"].strip()
            if not content:
                raise RuntimeError("empty response")
            return content, model
        except Exception as error:
            failure = f"{model}: {type(error).__name__}: {error}"
            failures.append(failure)
            print(f"Groq model unavailable ({failure})")

    raise RuntimeError("All Groq models failed: " + " | ".join(failures))


def build_prompt(date_str, hn, arxiv):
    hn_list = "\n".join(
        f"- {story['title']} ({story['url']})" for story in hn
    ) or "(none)"
    arxiv_list = "\n".join(
        f"- {paper['title']} ({paper['url']})" for paper in arxiv
    ) or "(none)"
    return f"""You are a concise, technically accurate AI research blogger writing for
Dr. Pritam Deka's personal site.
Write a weekly Markdown digest about {AUTHOR_FOCUS}.

Use only the signals below as your factual basis. Do not invent stories,
links, or numbers. If the signals are thin, keep the post short.

## Hacker News signals
{hn_list}

## Recent arXiv cs.CL papers
{arxiv_list}

Output Markdown only. Use this exact heading:
# Week of {date_str}

A two-sentence introduction.

## Top stories
- **<title>** — one sentence plus its source link

## Notable papers
- **<title>** — one sentence on the contribution plus its arXiv link

## Takeaway
One short paragraph for applied AI and NLP engineers.
"""


def markdown_link(title, url):
    clean_title = re.sub(r"\s+", " ", title or "").strip()
    return f"[{clean_title}]({url})" if url else clean_title


def build_fallback_post(date_str, hn, arxiv):
    """Build a source-led digest without requiring a generative API."""
    lines = [
        f"# Week of {date_str}",
        "",
        "This automated digest highlights recent public signals across applied AI "
        "and NLP. The notes are intentionally concise and link to primary sources.",
        "",
        "## Top stories",
    ]
    if hn:
        for story in hn[:5]:
            lines.append(
                f"- **{markdown_link(story.get('title'), story.get('url'))}** — "
                f"Trending on Hacker News with a score of "
                f"{story.get('score', 0)} at collection time."
            )
    else:
        lines.append("- No matching Hacker News stories were available during this run.")

    lines.extend(["", "## Notable papers"])
    if arxiv:
        for paper in arxiv[:5]:
            summary = re.sub(r"\s+", " ", paper.get("summary", "")).strip()
            if len(summary) > 180:
                summary = summary[:177].rsplit(" ", 1)[0] + "…"
            lines.append(
                f"- **{markdown_link(paper.get('title'), paper.get('url'))}** — "
                f"{summary or 'A recent contribution in computation and language.'}"
            )
    else:
        lines.append("- No recent cs.CL papers were available during this run.")

    lines.extend([
        "",
        "## Takeaway",
        "This week’s signals reinforce the pace of change across language-model "
        "research and applied AI. Follow the linked sources for full details.",
        "",
        "_Generated from public Hacker News and arXiv signals; AI synthesis was "
        "unavailable for this run._",
        "",
    ])
    return "\n".join(lines)


def slugify(value):
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")[:60]


def main():
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d")
    week = now.strftime("%Y-W%U")

    hn = fetch_hn_ai_stories()
    arxiv = fetch_arxiv_cl_papers()
    print(f"Signals fetched: {len(hn)} Hacker News stories, {len(arxiv)} arXiv papers")
    if not hn and not arxiv:
        print("No signals fetched — skipping without changing the blog.")
        return

    prompt = build_prompt(date_str, hn, arxiv)
    provider = "deterministic"
    model = None
    try:
        post_md = call_gemini(prompt)
        provider = "gemini"
        model = GEMINI_MODEL
        print("Gemini synthesis completed.")
    except Exception as gemini_error:
        print(
            f"Gemini synthesis unavailable "
            f"({type(gemini_error).__name__}: {gemini_error})."
        )
        try:
            post_md, model = call_groq(prompt)
            provider = "groq"
            print(f"Groq synthesis completed with {model}.")
        except Exception as groq_error:
            print(
                f"Groq synthesis unavailable "
                f"({type(groq_error).__name__}: {groq_error})."
            )
            print("Using deterministic source-based fallback.")
            post_md = build_fallback_post(date_str, hn, arxiv)

    title_match = re.search(r"^#\s+(.+)$", post_md, re.M)
    title = (
        title_match.group(1).strip()
        if title_match else f"Weekly AI Digest — {date_str}"
    )
    slug = slugify(title) or f"digest-{date_str}"

    os.makedirs("blog", exist_ok=True)
    post_path = f"blog/{date_str}-{slug}.md"
    with open(post_path, "w", encoding="utf-8") as output:
        output.write(post_md)

    manifest_path = "blog/index.json"
    try:
        with open(manifest_path, encoding="utf-8") as source:
            manifest = json.load(source)
        if not isinstance(manifest, list):
            manifest = []
    except (FileNotFoundError, json.JSONDecodeError):
        manifest = []

    entry = {
        "date": date_str,
        "week": week,
        "title": title,
        "file": post_path,
        "excerpt": re.sub(r"[#*\[\]()>]", "", post_md).strip()[:180] + "...",
        "synthesis_provider": provider,
    }
    if model:
        entry["synthesis_model"] = model
    manifest = [item for item in manifest if item.get("date") != date_str]
    manifest.insert(0, entry)

    with open(manifest_path, "w", encoding="utf-8") as output:
        json.dump(manifest[:52], output, indent=2, ensure_ascii=False)

    print(f"Blog post generated: {post_path}")


if __name__ == "__main__":
    main()
