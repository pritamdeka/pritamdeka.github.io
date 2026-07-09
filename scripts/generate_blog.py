#!/usr/bin/env python3
"""Generate a substantive weekly AI/NLP research briefing.

Pipeline:
1. Collect and rank Hugging Face Daily Papers, official lab news, open-source
   releases, arXiv research, and a small community-signal sample.
2. Give the model source dossiers rather than bare titles.
3. Validate drafts for depth, structure, dates, and source integrity.
4. Try Gemini, then Groq open models, then a deterministic briefing.
"""
import json
import math
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path

GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent?key={{key}}"
)
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_GROQ_MODELS = (
    "llama-3.3-70b-versatile",
    "openai/gpt-oss-20b",
    "llama-3.1-8b-instant",
)
ARXIV_CATEGORIES = ("cs.CL", "cs.AI", "cs.LG", "cs.CV")
OFFICIAL_FEEDS = (
    ("OpenAI", "https://openai.com/news/rss.xml"),
    ("Google DeepMind", "https://deepmind.google/blog/rss.xml"),
    ("Hugging Face", "https://huggingface.co/blog/feed.xml"),
)
RELEASE_REPOS = (
    ("Transformers", "huggingface/transformers"),
    ("vLLM", "vllm-project/vllm"),
    ("llama.cpp", "ggml-org/llama.cpp"),
)
MIN_DRAFT_WORDS = 700
MAX_DRAFT_WORDS = 1800

TOPIC_WEIGHTS = {
    "agent": 5, "agentic": 6, "rag": 5, "retrieval": 4,
    "language model": 4, "llm": 5, "vision-language": 6, "multimodal": 5,
    "document": 5, "information extraction": 6, "reasoning": 4,
    "evaluation": 4, "benchmark": 3, "alignment": 3, "inference": 3,
    "fine-tuning": 3, "open source": 3, "open-source": 3,
    "fact-check": 6, "verification": 5, "hallucination": 4,
}
GENERIC_PHRASES = (
    "rapidly evolving landscape",
    "game-changer",
    "revolutionize the industry",
    "exciting times ahead",
    "only time will tell",
    "paradigm shift",
)


def http_request(url, timeout=20, data=None, headers=None, attempts=3):
    request_headers = {
        "User-Agent": "pritamdeka-blog-bot/2.0 (+https://pritamdeka.com/blog)",
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


def clean_text(value):
    return re.sub(r"\s+", " ", value or "").strip()


def strip_html(value):
    """Convert source/model HTML fragments into plain Markdown-safe text."""
    text = str(value or "")
    text = re.sub(r"(?is)<(script|style|svg|picture|iframe|video|audio)\b.*?</\1>", " ", text)
    text = re.sub(r"(?is)<img\b[^>]*>", " ", text)
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</p\s*>", "\n", text)
    text = re.sub(r"(?i)</h[1-6]\s*>", "\n", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&lt;", "<", text)
    text = re.sub(r"&gt;", ">", text)
    text = re.sub(r"&quot;", '"', text)
    text = re.sub(r"&#39;|&apos;", "'", text)
    return clean_text(text)


def plain_text(value):
    """Normalize arbitrary source text for inclusion in prompts/posts."""
    return strip_html(value)


def canonical_url(url):
    value = clean_text(url).rstrip("/")
    if value.startswith("https://hf.co/papers/"):
        value = value.replace("https://hf.co/papers/", "https://huggingface.co/papers/", 1)
    return value


def topic_score(text):
    lowered = clean_text(text).lower()
    return sum(weight for phrase, weight in TOPIC_WEIGHTS.items() if phrase in lowered)


def similar_title(left, right):
    normalize = lambda value: re.sub(r"[^a-z0-9 ]", "", value.lower())
    return SequenceMatcher(None, normalize(left), normalize(right)).ratio() >= 0.84


def deduplicate(items):
    selected = []
    for item in sorted(items, key=lambda entry: entry["rank"], reverse=True):
        if not any(similar_title(item["title"], existing["title"]) for existing in selected):
            selected.append(item)
    return selected


def fetch_hn_ai_stories(limit=7):
    """Collect AI stories from multiple HN lists and rank by relevance/engagement."""
    try:
        story_ids = []
        for endpoint in ("beststories", "topstories", "newstories"):
            ids = http_get_json(
                f"https://hacker-news.firebaseio.com/v0/{endpoint}.json",
                timeout=15,
                attempts=2,
            )[:45]
            story_ids.extend(ids)
        story_ids = list(dict.fromkeys(story_ids))[:75]

        now = datetime.now(timezone.utc).timestamp()
        stories = []
        def fetch_story(story_id):
            return story_id, http_get_json(
                f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json",
                timeout=8,
                attempts=1,
            )

        fetched = []
        with ThreadPoolExecutor(max_workers=16) as executor:
            futures = [executor.submit(fetch_story, story_id) for story_id in story_ids]
            for future in as_completed(futures):
                try:
                    fetched.append(future.result())
                except Exception:
                    continue

        for story_id, story in fetched:
            if not isinstance(story, dict):
                continue
            title = clean_text(story.get("title"))
            text = plain_text(story.get("text") or "")
            relevance = topic_score(f"{title} {text}")
            if not title or relevance < 3:
                continue
            published_timestamp = story.get("time") or now
            age_days = max(0, (now - published_timestamp) / 86400)
            score = int(story.get("score", 0))
            comments = int(story.get("descendants", 0))
            rank = (
                relevance * 8
                + math.log1p(score) * 4
                + math.log1p(comments) * 2
                - min(age_days, 14) * 1.5
            )
            url = story.get("url") or f"https://news.ycombinator.com/item?id={story_id}"
            stories.append({
                "title": title,
                "url": url,
                "hn_url": f"https://news.ycombinator.com/item?id={story_id}",
                "domain": urllib.parse.urlparse(url).netloc.replace("www.", ""),
                "score": score,
                "comments": comments,
                "published": datetime.fromtimestamp(
                    published_timestamp, timezone.utc
                ).strftime("%Y-%m-%d"),
                "context": text[:500],
                "rank": round(rank, 2),
            })
        return deduplicate(stories)[:limit]
    except Exception as error:
        print(f"HN fetch failed: {type(error).__name__}: {error}")
        return []


def fetch_hf_daily_papers(limit=12):
    """Fetch community-ranked papers with code/project metadata from HF Papers."""
    try:
        rows = http_get_json(
            f"https://huggingface.co/api/daily_papers?limit={max(limit * 2, 20)}",
            timeout=25,
            attempts=3,
        )
        papers = []
        for row in rows if isinstance(rows, list) else []:
            paper = row.get("paper", row)
            paper_id = clean_text(paper.get("id"))
            title = clean_text(paper.get("title") or row.get("title"))
            summary = plain_text(paper.get("summary") or row.get("summary"))
            if not paper_id or not title:
                continue
            authors = [
                clean_text(author.get("name"))
                for author in paper.get("authors", [])
                if clean_text(author.get("name"))
            ]
            upvotes = int(paper.get("upvotes") or row.get("upvotes") or 0)
            github_stars = int(paper.get("githubStars") or 0)
            project_url = paper.get("projectPage") or ""
            code_url = paper.get("githubRepo") or ""
            relevance = topic_score(f"{title} {summary}")
            asset_bonus = 8 if code_url else 0
            project_bonus = 5 if project_url else 0
            rank = (
                45
                + relevance * 7
                + math.log1p(upvotes) * 7
                + math.log1p(github_stars) * 3
                + asset_bonus
                + project_bonus
            )
            papers.append({
                "title": title,
                "url": f"https://huggingface.co/papers/{paper_id}",
                "arxiv_url": f"https://arxiv.org/abs/{paper_id}",
                "abstract": summary[:1200],
                "authors": authors[:5],
                "published": clean_text(
                    paper.get("publishedAt") or row.get("publishedAt")
                )[:10],
                "categories": paper.get("ai_keywords", [])[:6],
                "upvotes": upvotes,
                "code_url": code_url,
                "project_url": project_url,
                "thumbnail": row.get("thumbnail") or paper.get("thumbnail") or "",
                "source": "Hugging Face Daily Papers",
                "rank": round(rank, 2),
            })
        return deduplicate(papers)[:limit]
    except Exception as error:
        print(f"Hugging Face Papers fetch failed: {type(error).__name__}: {error}")
        return []


def parse_feed_items(xml, source_name, limit=6):
    root = ET.fromstring(xml)
    items = []
    candidates = list(root.findall(".//item"))
    if not candidates:
        atom = "{http://www.w3.org/2005/Atom}"
        candidates = list(root.findall(f".//{atom}entry"))
    for entry in candidates[:limit * 2]:
        def first_text(names):
            for name in names:
                node = entry.find(name)
                if node is not None and clean_text(node.text):
                    return clean_text(node.text)
            return ""

        title = first_text(("title", "{http://www.w3.org/2005/Atom}title"))
        summary = first_text((
            "description",
            "{http://www.w3.org/2005/Atom}summary",
            "{http://www.w3.org/2005/Atom}content",
        ))
        link = first_text(("link",))
        if not link:
            atom_link = entry.find("{http://www.w3.org/2005/Atom}link")
            if atom_link is not None:
                link = atom_link.attrib.get("href", "")
        published = first_text((
            "pubDate",
            "{http://www.w3.org/2005/Atom}published",
            "{http://www.w3.org/2005/Atom}updated",
        ))
        if not title or not link:
            continue
        relevance = topic_score(f"{title} {summary}")
        if relevance < 2:
            continue
        items.append({
            "title": title,
            "url": link,
            "summary": plain_text(summary)[:900],
            "published": published[:25],
            "source": source_name,
            "rank": 55 + relevance * 8,
        })
    return deduplicate(items)[:limit]


def fetch_official_news(limit=10):
    """Fetch relevant posts from official AI lab and platform feeds."""
    items = []
    for source_name, url in OFFICIAL_FEEDS:
        try:
            xml = http_request(url, timeout=20, attempts=2).decode("utf-8")
            items.extend(parse_feed_items(xml, source_name, limit=5))
        except Exception as error:
            print(f"{source_name} feed failed: {type(error).__name__}: {error}")
    return deduplicate(items)[:limit]


def fetch_release_notes(limit=7):
    """Fetch official release notes from high-impact open-source AI projects."""
    releases = []
    for project, repo in RELEASE_REPOS:
        try:
            rows = http_get_json(
                f"https://api.github.com/repos/{repo}/releases?per_page=5",
                timeout=20,
                attempts=2,
            )
            for row in rows if isinstance(rows, list) else []:
                if row.get("draft") or row.get("prerelease"):
                    continue
                title = clean_text(row.get("name") or row.get("tag_name"))
                body = plain_text(row.get("body"))
                if not title or not row.get("html_url"):
                    continue
                releases.append({
                    "title": f"{project} {title}",
                    "url": row["html_url"],
                    "summary": body[:900],
                    "published": clean_text(row.get("published_at"))[:10],
                    "source": f"{project} release notes",
                    "rank": 48 + topic_score(f"{title} {body}") * 5,
                })
        except Exception as error:
            print(f"{project} releases failed: {type(error).__name__}: {error}")
    return deduplicate(releases)[:limit]


def xml_text(element, name, namespace):
    node = element.find(f"{{{namespace}}}{name}")
    return clean_text(node.text) if node is not None else ""


def fetch_arxiv_papers(limit=10):
    """Collect recent papers across relevant arXiv categories and rank them."""
    try:
        query = " OR ".join(f"cat:{category}" for category in ARXIV_CATEGORIES)
        params = urllib.parse.urlencode({
            "search_query": query,
            "start": 0,
            "max_results": 35,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        })
        xml = http_request(
            f"https://export.arxiv.org/api/query?{params}",
            timeout=30,
            attempts=3,
        ).decode("utf-8")
        root = ET.fromstring(xml)
        namespace = "http://www.w3.org/2005/Atom"
        papers = []
        for entry in root.findall(f"{{{namespace}}}entry"):
            title = xml_text(entry, "title", namespace)
            abstract = plain_text(xml_text(entry, "summary", namespace))
            url = xml_text(entry, "id", namespace)
            published = xml_text(entry, "published", namespace)[:10]
            authors = [
                xml_text(author, "name", namespace)
                for author in entry.findall(f"{{{namespace}}}author")
            ]
            categories = [
                category.attrib.get("term", "")
                for category in entry.findall(f"{{{namespace}}}category")
            ]
            relevance = topic_score(f"{title} {abstract}")
            rank = relevance * 8 + (5 if "cs.CL" in categories else 0)
            papers.append({
                "title": title,
                "url": url,
                "abstract": abstract[:1000],
                "authors": authors[:4],
                "published": published,
                "categories": categories[:5],
                "rank": round(rank, 2),
            })
        return deduplicate(papers)[:limit]
    except Exception as error:
        print(f"arXiv fetch failed: {type(error).__name__}: {error}")
        return []


def call_gemini(prompt):
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY not set")
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.55, "maxOutputTokens": 4096},
    }
    raw = http_request(
        GEMINI_URL.format(key=key),
        timeout=75,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        attempts=2,
    )
    data = json.loads(raw.decode("utf-8"))
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except (KeyError, IndexError):
        raise RuntimeError(f"Unexpected Gemini response: {json.dumps(data)[:400]}")


def groq_models():
    configured = os.environ.get("GROQ_MODELS", "")
    models = tuple(model.strip() for model in configured.split(",") if model.strip())
    return models or DEFAULT_GROQ_MODELS


def call_groq(prompt):
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
                        "You are a rigorous technology editor. Return only Markdown. "
                        "Prioritize evidence, specificity, trade-offs, and practical value."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.55,
            "max_completion_tokens": 4096,
        }
        try:
            raw = http_request(
                GROQ_URL,
                timeout=75,
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


def groq_title_prompt(markdown, date_str, prior_titles, source_titles):
    current_title = ""
    match = re.search(r"^#\s+(.+)$", markdown, re.M)
    if match:
        current_title = match.group(1).strip()
    source_list = "\n".join(f"- {title}" for title in source_titles[:10])
    prior_list = "\n".join(f"- {title}" for title in prior_titles[:12]) or "- none"
    body_preview = clean_text(re.sub(r"\[[^\]]+\]\([^)]+\)", "", markdown))[:1800]
    return f"""Write one stronger headline for this AI research blog post.

Rules:
- Return only the headline, no markdown, quotes, numbering, or explanation.
- 8-14 words.
- Hook-driven and specific, but not clickbait.
- No date, no "week", no "weekly", no colon-prefixed keyword list.
- It must not be similar to prior titles.

Publication date: {date_str}
Current title: {current_title}

Prior titles to avoid:
{prior_list}

Source titles behind the article:
{source_list}

Article preview:
{body_preview}
"""


def generate_groq_title(markdown, date_str, prior_titles, source_titles):
    """Use a Groq open model for the post title without slowing the whole run."""
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        return None, None

    prompt = groq_title_prompt(markdown, date_str, prior_titles, source_titles)
    for model in groq_models()[:2]:
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": "You write concise, evidence-led technology headlines.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.8,
            "max_completion_tokens": 80,
        }
        try:
            raw = http_request(
                GROQ_URL,
                timeout=20,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                },
                attempts=1,
            )
            data = json.loads(raw.decode("utf-8"))
            title = clean_text(data["choices"][0]["message"]["content"])
            title = title.strip(" #\"'“”‘’")
            title = re.sub(r"^\d+\.\s*", "", title)
            if "\n" in title:
                title = clean_text(title.splitlines()[0])
            issues = validate_headline(title, date_str, prior_titles)
            if not issues:
                return title, model
            print(f"Groq title rejected ({model}): " + "; ".join(issues))
        except Exception as error:
            print(f"Groq title unavailable ({model}: {type(error).__name__}: {error})")
    return None, None


def replace_markdown_title(markdown, title):
    if re.search(r"^#\s+.+$", markdown, re.M):
        return re.sub(r"^#\s+.+$", f"# {title}", markdown, count=1, flags=re.M)
    return f"# {title}\n\n{markdown.lstrip()}"


def article_excerpt(markdown, limit=220):
    body = re.sub(r"^#\s+.+\n+", "", markdown, count=1, flags=re.M)
    body = re.sub(r"^_[^_]+_\s*", "", body.strip(), count=1)
    body = re.sub(r"\[[^\]]+\]\((https?://[^)]+)\)", lambda m: m.group(0).split("](")[0][1:], body)
    body = re.sub(r"[*_`#>\-]+", " ", body)
    text = plain_text(body)
    return text[:limit].rstrip() + ("..." if len(text) > limit else "")


def source_dossier(hf_papers, official_news, releases, arxiv, hn):
    sections = ["FEATURED RESEARCH — HUGGING FACE DAILY PAPERS"]
    for index, paper in enumerate(hf_papers, 1):
        sections.append(
            f"[HF{index}] {paper['title']}\n"
            f"Hugging Face paper page: {paper['url']}\n"
            f"arXiv: {paper['arxiv_url']}\n"
            f"Published: {paper['published']} | HF upvotes: {paper['upvotes']}\n"
            f"Authors: {', '.join(paper['authors'])}\n"
            f"Code: {paper['code_url'] or 'not linked'}\n"
            f"Project page: {paper['project_url'] or 'not linked'}\n"
            f"Abstract: {paper['abstract']}"
        )

    sections.append("\nOFFICIAL LAB / PLATFORM NEWS")
    for index, item in enumerate(official_news, 1):
        sections.append(
            f"[O{index}] {item['title']}\n"
            f"Source: {item['source']} | Published: {item['published']}\n"
            f"URL: {item['url']}\n"
            f"Summary: {item['summary']}"
        )

    sections.append("\nOFFICIAL OPEN-SOURCE RELEASE NOTES")
    for index, item in enumerate(releases, 1):
        sections.append(
            f"[R{index}] {item['title']}\n"
            f"Source: {item['source']} | Published: {item['published']}\n"
            f"URL: {item['url']}\n"
            f"Release context: {item['summary']}"
        )

    sections.append("\nRECENT ARXIV — BREADTH / BACKUP")
    for index, paper in enumerate(arxiv, 1):
        sections.append(
            f"[A{index}] {paper['title']}\n"
            f"URL: {paper['url']}\n"
            f"Published: {paper['published']} | Categories: "
            f"{', '.join(paper['categories'])}\n"
            f"Authors: {', '.join(paper['authors'])}\n"
            f"Abstract: {paper['abstract']}"
        )

    sections.append("\nCOMMUNITY REACTION — USE SPARINGLY, NEVER AS PRIMARY EVIDENCE")
    for index, story in enumerate(hn, 1):
        sections.append(
            f"[C{index}] {story['title']}\n"
            f"Primary URL: {story['url']}\n"
            f"HN discussion: {story['hn_url']}\n"
            f"Published: {story['published']} | Domain: {story['domain']} | "
            f"HN points: {story['score']} | Comments: {story['comments']}\n"
            f"Available context: {story['context'] or 'Title and engagement metadata only.'}"
        )
    return "\n\n".join(sections)


def item_urls(item):
    """Return all source URLs attached to a collected signal."""
    return {
        canonical_url(url)
        for url in (
            item.get("url"),
            item.get("arxiv_url"),
            item.get("code_url"),
            item.get("project_url"),
            item.get("hn_url"),
        )
        if clean_text(url)
    }


def allowed_urls(hf_papers, official_news, releases, arxiv, hn):
    urls = set()
    for paper in hf_papers:
        urls.update(item_urls(paper))
    for item in official_news + releases:
        urls.update(item_urls(item))
    for paper in arxiv:
        urls.update(item_urls(paper))
    for story in hn:
        urls.update(item_urls(story))
    return {canonical_url(url) for url in urls if url}


def build_prompt(date_str, hf_papers, official_news, releases, arxiv, hn):
    dossier = source_dossier(hf_papers, official_news, releases, arxiv, hn)
    return f"""Write a genuinely useful weekly AI research briefing for Dr. Pritam
Deka's website. The audience is AI/NLP researchers and engineers who already
understand LLMs. The publication date is {date_str}.

Editorial goal:
- Synthesize developments; do not produce a link roundup.
- Select the 2-3 strongest themes connecting multiple sources.
- Explain what changed, why it matters technically, and what remains uncertain.
- Distinguish evidence from inference. Do not claim to have read details that are
  absent from the source dossier.
- Discuss practical consequences for evaluation, system design, deployment,
  research methodology, or product decisions.
- Include concrete caveats and avoid hype.
- Use only URLs included in the dossier. Every factual item must link to its source.
- Prioritize Hugging Face Daily Papers with linked code/projects, official lab
  announcements, and official release notes. Use raw arXiv as supporting breadth.
- Hacker News may appear only as community reaction and must never drive the thesis.

Required Markdown structure:
# <8-14 word hook-driven analytical headline>

The headline must make a specific, defensible claim or create informed curiosity.
Do not include a date, "week of", "weekly digest", a colon-separated date prefix,
or a keyword list. Follow it with a 30-50 word standfirst in italics that tells
the reader exactly why this article is worth their time.

Then write an opening thesis of 90-140 words stating the central pattern.

## The signal
Explain the 2-3 connected developments and the evidence behind the thesis.

## Deep dive
Give a technically informed analysis of the most consequential development.
Compare approaches or trade-offs where the sources support it.

## Research radar
Discuss 3-5 papers in connected prose or substantive bullets. For each, state
the problem, the proposed contribution from the abstract, and why it may matter.

## Practical implications
Provide 4-6 specific actions, experiments, design questions, or evaluation
checks that an applied AI team could use next week.

## What to watch
Name 2-4 unresolved questions or signals worth monitoring.

Length: 900-1400 words. Use descriptive link text, not raw URLs. Avoid generic
phrases, breathless claims, keyword-stuffed headlines, and summaries that merely
repeat source titles. At least 70% of cited evidence must come from featured
papers, official news, official release notes, or primary arXiv pages rather than
community discussion.

SOURCE DOSSIER
{dossier}
"""


def extract_urls(markdown):
    return {
        canonical_url(url)
        for url in re.findall(r"https?://[^)\s>]+", markdown)
    }


def contains_html_tags(markdown):
    return bool(re.search(r"</?[a-z][a-z0-9-]*(?:\s+[^>]*)?>", markdown, re.I))


def sanitize_markdown(markdown):
    """Remove raw HTML while preserving ordinary Markdown structure."""
    lines = []
    for line in str(markdown or "").splitlines():
        cleaned = strip_html(line) if contains_html_tags(line) else line.rstrip()
        lines.append(cleaned)
    sanitized = "\n".join(lines).strip() + "\n"
    sanitized = re.sub(r"\n{4,}", "\n\n\n", sanitized)
    return sanitized


def validate_draft(markdown, date_str, source_urls, community_urls=None):
    issues = []
    if contains_html_tags(markdown):
        issues.append("contains raw HTML tags")
    words = re.findall(r"\b[\w'-]+\b", markdown)
    title_match = re.match(r"^#\s+(.+)$", markdown, re.M)
    if not title_match:
        issues.append("missing H1 headline")
        title = ""
    else:
        title = title_match.group(1).strip()
        issues.extend(validate_headline(title, date_str))
    first_lines = [line.strip() for line in markdown.splitlines()[1:] if line.strip()]
    if not first_lines or not (
        first_lines[0].startswith("_") and first_lines[0].endswith("_")
    ):
        issues.append("missing italic standfirst immediately below headline")
    if len(words) < MIN_DRAFT_WORDS:
        issues.append(f"too short ({len(words)} words; minimum {MIN_DRAFT_WORDS})")
    if len(words) > MAX_DRAFT_WORDS:
        issues.append(f"too long ({len(words)} words; maximum {MAX_DRAFT_WORDS})")
    for heading in (
        "## The signal",
        "## Deep dive",
        "## Research radar",
        "## Practical implications",
        "## What to watch",
    ):
        if heading not in markdown:
            issues.append(f"missing section: {heading}")
    used_urls = extract_urls(markdown)
    invented = used_urls - source_urls
    if invented:
        issues.append("contains URLs not present in source dossier")
    expected_links = min(5, len(source_urls))
    if len(used_urls & source_urls) < expected_links:
        issues.append(
            f"insufficient source links ({len(used_urls & source_urls)}; "
            f"expected at least {expected_links})"
        )
    community_urls = community_urls or set()
    cited = used_urls & source_urls
    if cited:
        community_count = len(cited & community_urls)
        if community_count / len(cited) > 0.3:
            issues.append("more than 30% of citations come from community sources")
    lowered = markdown.lower()
    used_generic = [phrase for phrase in GENERIC_PHRASES if phrase in lowered]
    if used_generic:
        issues.append("contains generic phrases: " + ", ".join(used_generic))
    if len(re.findall(r"\b(however|because|therefore|trade-off|limitation|risk)\b", lowered)) < 3:
        issues.append("insufficient analytical or caveat language")
    return issues


def validate_headline(title, date_str, prior_titles=None):
    issues = []
    title = clean_text(title).strip("# ")
    title_words = re.findall(r"\b[\w'-]+\b", title)
    if not 6 <= len(title_words) <= 16:
        issues.append(f"headline must contain 6-16 words ({len(title_words)} found)")
    if re.search(r"\bweek(?:ly)?\b", title.lower()) or date_str in title:
        issues.append("headline must not contain week/weekly wording or the publication date")
    if title.count(",") >= 2:
        issues.append("headline appears keyword-stuffed")
    if ":" in title[:24]:
        issues.append("headline must not use a dated or keyword-list prefix")
    for old_title in prior_titles or ():
        if similar_title(title, old_title):
            issues.append("headline is too similar to a prior post")
            break
    return issues


def revision_prompt(original_prompt, draft, issues):
    return f"""{original_prompt}

The previous draft failed editorial review:
{chr(10).join(f"- {issue}" for issue in issues)}

Rewrite it completely. Preserve only claims supported by the dossier, fix every
listed problem, and return only the revised Markdown.

PREVIOUS DRAFT
{draft}
"""


def generate_validated_draft(prompt, date_str, urls, community_urls=None):
    attempts = []
    try:
        draft = sanitize_markdown(call_gemini(prompt))
        issues = validate_draft(draft, date_str, urls, community_urls)
        attempts.append(("gemini", GEMINI_MODEL, issues))
        if not issues:
            return draft, "gemini", GEMINI_MODEL
        print("Gemini draft rejected: " + "; ".join(issues))
        revised = sanitize_markdown(call_gemini(revision_prompt(prompt, draft, issues)))
        revised_issues = validate_draft(revised, date_str, urls, community_urls)
        attempts.append(("gemini-revision", GEMINI_MODEL, revised_issues))
        if not revised_issues:
            return revised, "gemini", GEMINI_MODEL
        print("Gemini revision rejected: " + "; ".join(revised_issues))
    except Exception as error:
        print(f"Gemini unavailable ({type(error).__name__}: {error})")

    try:
        draft, model = call_groq(prompt)
        draft = sanitize_markdown(draft)
        issues = validate_draft(draft, date_str, urls, community_urls)
        attempts.append(("groq", model, issues))
        if not issues:
            return draft, "groq", model
        print(f"Groq draft rejected ({model}): " + "; ".join(issues))
        revised, revision_model = call_groq(revision_prompt(prompt, draft, issues))
        revised = sanitize_markdown(revised)
        revised_issues = validate_draft(revised, date_str, urls, community_urls)
        attempts.append(("groq-revision", revision_model, revised_issues))
        if not revised_issues:
            return revised, "groq", revision_model
        print(f"Groq revision rejected ({revision_model}): " + "; ".join(revised_issues))
    except Exception as error:
        print(f"Groq unavailable ({type(error).__name__}: {error})")

    summary = " | ".join(
        f"{provider}/{model}: {', '.join(issues) or 'passed'}"
        for provider, model, issues in attempts
    )
    raise RuntimeError(f"No AI draft passed editorial review. {summary}")


def markdown_link(title, url):
    label = plain_text(title)
    return f"[{label}]({url})" if url else label


def compact_topic(title):
    words = [
        word
        for word in re.findall(r"[A-Za-z][A-Za-z0-9-]{2,}", plain_text(title))
        if word.lower() not in {
            "the", "and", "for", "with", "from", "into", "using", "toward",
            "towards", "based", "large", "language", "model", "models",
            "release", "version", "addition", "new", "paper",
        }
    ]
    topic = " ".join(words[:4])
    return topic or "Evidence"


def deterministic_headline(source_titles, date_str, prior_titles=None):
    topics = [compact_topic(title) for title in source_titles if clean_text(title)]
    topics = [topic for index, topic in enumerate(topics) if topic and topic not in topics[:index]]
    primary = topics[0] if topics else "Evidence"
    secondary = topics[1] if len(topics) > 1 else "Evaluation"
    candidates = [
        f"Why {primary} Matters for Reliable AI Systems",
        f"How {primary} Changes the Reliability Question for AI Builders",
        f"What {primary} Reveals About Evaluation Debt in AI Systems",
        f"Why {primary} and {secondary} Are Reshaping Applied AI",
        f"The Practical AI Signal Hidden Inside {primary}",
    ]
    for candidate in candidates:
        if not validate_headline(candidate, date_str, prior_titles):
            return candidate
    safe_topic = re.sub(r"[^A-Za-z0-9 ]+", "", primary).strip() or "Evidence"
    return f"Why {safe_topic} Deserves a Fresh Reliability Check"


def build_fallback_post(date_str, hf_papers, official_news, releases, arxiv, hn, prior_titles=None):
    """Build a readable source-led briefing when both AI providers fail."""
    strongest_news = official_news[:3]
    strongest_releases = releases[:2]
    strongest_papers = (hf_papers + arxiv)[:6]
    theme_terms = []
    combined = " ".join(
        item["title"].lower()
        for item in strongest_news + strongest_releases + strongest_papers
    )
    for phrase in TOPIC_WEIGHTS:
        if phrase in combined:
            theme_terms.append(phrase)
    theme = theme_terms[0] if theme_terms else "AI systems"
    source_titles = [
        item["title"]
        for item in strongest_papers + strongest_news + strongest_releases
        if clean_text(item.get("title"))
    ]
    headline = deterministic_headline(source_titles, date_str, prior_titles)

    lines = [
        f"# {headline}",
        "",
        "_A source-led briefing on the papers, official announcements, and open-source "
        "releases most likely to affect how applied AI teams evaluate and build systems._",
        "",
        "The strongest public signals in this briefing point less to a single breakthrough "
        "than to a shared engineering problem: turning model capability into systems "
        "that can be evaluated, trusted, and operated under real constraints. The "
        "items below are selected for relevance to applied NLP, multimodal systems, "
        "retrieval, and document intelligence. Where only metadata is available, the "
        "briefing avoids conclusions beyond that evidence.",
        "",
        "## The signal",
    ]
    for story in strongest_news:
        lines.append(
            f"- **{markdown_link(story['title'], story['url'])}** — "
            f"{story['summary'][:420].rstrip()}"
        )
    for release in strongest_releases:
        lines.append(
            f"- **{markdown_link(release['title'], release['url'])}** — "
            f"{release['summary'][:320].rstrip()}"
        )
    lines.extend([
        "",
        "Taken together, these primary sources are worth reading for the implementation "
        "questions they expose: which claims survive evaluation, what operational "
        "costs are hidden by demos, and where open tooling changes the build-versus-buy "
        "decision.",
        "",
        "## Deep dive",
        "",
    ])
    if strongest_papers:
        lead = strongest_papers[0]
        lines.append(
            f"The highest-ranked research signal is **{markdown_link(lead['title'], lead['url'])}**. "
            f"Its abstract frames the contribution as follows: {lead['abstract'][:650]} "
            "The practical question is not merely whether the reported method improves "
            "a benchmark, but whether its assumptions, data requirements, and evaluation "
            "setting resemble the environment in which a real system would operate."
        )
    lines.extend(["", "## Research radar"])
    for paper in strongest_papers:
        lines.append(
            f"- **{markdown_link(paper['title'], paper['url'])}** — "
            f"{paper['abstract'][:420].rstrip()} "
            f"Relevant topics: {', '.join(paper.get('categories', [])[:3])}."
        )
    lines.extend([
        "",
        "## Practical implications",
        "",
        "- Reproduce the most relevant claim on a small internal dataset before changing architecture.",
        "- Separate retrieval, generation, and verification metrics so aggregate scores do not hide failure modes.",
        "- Record latency, token use, and human-review burden alongside task quality.",
        "- Test the system on distribution shifts and incomplete documents, not only clean benchmark inputs.",
        "- Treat community excitement as discovery only; verify claims against papers, code, and official releases.",
        "",
        "## What to watch",
        "",
        "- Whether the highlighted methods release code, data, and reproducible evaluation details.",
        "- Whether follow-up work confirms gains outside the original benchmark or domain.",
        "- Whether operational costs alter the apparent advantage over simpler baselines.",
        "",
        "_This fallback edition was assembled directly from public source metadata because "
        "the AI editorial providers were unavailable or their drafts did not pass review._",
        "",
    ])
    return "\n".join(lines)


def slugify(value):
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")[:70]


def load_manifest(path):
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
        return manifest if isinstance(manifest, list) else []
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def published_context(manifest, current_date, blog_dir=Path("blog")):
    """Read prior published posts so a new week does not recycle them."""
    prior_titles = []
    prior_urls = set()
    current_files = set()

    for entry in manifest:
        if not isinstance(entry, dict):
            continue
        title = clean_text(entry.get("title"))
        if title and entry.get("date") != current_date:
            prior_titles.append(title)

        file_name = clean_text(entry.get("file"))
        if file_name and entry.get("date") == current_date:
            current_files.add(file_name)

        for url in entry.get("source_urls") or ():
            if clean_text(url) and entry.get("date") != current_date:
                prior_urls.add(canonical_url(url))

        if entry.get("date") == current_date or not file_name:
            continue
        path = Path(file_name)
        if not path.is_absolute():
            path = Path(file_name)
        try:
            prior_urls.update(extract_urls(path.read_text(encoding="utf-8")))
        except OSError:
            continue

    return {
        "prior_titles": prior_titles,
        "prior_urls": prior_urls,
        "current_files": current_files,
    }


def freshen_items(items, context, limit):
    """Drop signals already cited or too close to older post titles."""
    prior_titles = context["prior_titles"]
    prior_urls = context["prior_urls"]
    fresh = []
    for item in items:
        urls = item_urls(item)
        if urls and urls & prior_urls:
            continue
        if any(similar_title(item["title"], title) for title in prior_titles):
            continue
        fresh.append(item)
    return fresh[:limit]


def unique_slug(base_slug, date_str, manifest):
    """Keep post paths stable for same-day reruns and unique across older posts."""
    used = {
        Path(clean_text(item.get("file"))).stem
        for item in manifest
        if isinstance(item, dict) and item.get("date") != date_str
    }
    slug = base_slug
    suffix = 2
    while f"{date_str}-{slug}" in used:
        trimmed = base_slug[: max(1, 67 - len(str(suffix)))]
        slug = f"{trimmed}-{suffix}"
        suffix += 1
    return slug


def prune_manifest(manifest, current_date):
    """Remove same-day duplicates and older duplicate titles/files."""
    pruned = []
    seen_titles = set()
    seen_files = set()
    for item in manifest:
        if not isinstance(item, dict):
            continue
        if item.get("date") == current_date:
            continue
        title_key = clean_text(item.get("title")).lower()
        file_key = clean_text(item.get("file"))
        if title_key and title_key in seen_titles:
            continue
        if file_key and file_key in seen_files:
            continue
        if title_key:
            seen_titles.add(title_key)
        if file_key:
            seen_files.add(file_key)
        pruned.append(item)
    return pruned


def main():
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d")
    week = now.strftime("%G-W%V")
    blog_dir = Path("blog")
    blog_dir.mkdir(exist_ok=True)
    manifest_path = blog_dir / "index.json"
    manifest = load_manifest(manifest_path)
    context = published_context(manifest, date_str, blog_dir)

    collectors = {
        "hf_papers": lambda: fetch_hf_daily_papers(limit=12),
        "official_news": lambda: fetch_official_news(limit=10),
        "releases": lambda: fetch_release_notes(limit=7),
        "arxiv": lambda: fetch_arxiv_papers(limit=12),
        "hn": lambda: fetch_hn_ai_stories(limit=2),
    }
    collected = {name: [] for name in collectors}
    with ThreadPoolExecutor(max_workers=len(collectors)) as executor:
        futures = {
            executor.submit(collector): name
            for name, collector in collectors.items()
        }
        for future in as_completed(futures):
            name = futures[future]
            try:
                collected[name] = future.result()
            except Exception as error:
                print(f"{name} collector failed: {type(error).__name__}: {error}")

    hf_papers = freshen_items(collected["hf_papers"], context, 12)
    official_news = freshen_items(collected["official_news"], context, 10)
    releases = freshen_items(collected["releases"], context, 7)
    hf_titles = {paper["title"].lower() for paper in hf_papers}
    arxiv = [
        paper for paper in collected["arxiv"]
        if not any(similar_title(paper["title"], title) for title in hf_titles)
    ]
    arxiv = freshen_items(arxiv, context, 8)
    hn = freshen_items(collected["hn"], context, 2)
    print(
        "Ranked signals: "
        f"{len(hf_papers)} HF papers, {len(official_news)} official posts, "
        f"{len(releases)} releases, {len(arxiv)} additional arXiv papers, "
        f"{len(hn)} community signals"
    )
    if not (hf_papers or official_news or releases or arxiv):
        raise RuntimeError("No source signals were available; refusing to publish an empty post")

    prompt = build_prompt(
        date_str, hf_papers, official_news, releases, arxiv, hn
    )
    urls = allowed_urls(hf_papers, official_news, releases, arxiv, hn)
    community_urls = {
        canonical_url(url)
        for story in hn
        for url in (story["url"], story["hn_url"])
        if url
    }
    provider = "deterministic"
    model = None
    try:
        post_md, provider, model = generate_validated_draft(
            prompt, date_str, urls, community_urls
        )
        print(f"Editorial draft passed with {provider}/{model}.")
    except Exception as error:
        print(f"AI editorial pipeline unavailable ({error})")
        post_md = build_fallback_post(
            date_str, hf_papers, official_news, releases, arxiv, hn,
            context["prior_titles"]
        )
    post_md = sanitize_markdown(post_md)

    source_titles = [
        item["title"]
        for item in (hf_papers + official_news + releases + arxiv + hn)
        if clean_text(item.get("title"))
    ]
    title_provider = provider
    title_model = model
    groq_title, groq_title_model = generate_groq_title(
        post_md, date_str, context["prior_titles"], source_titles
    )
    if groq_title:
        post_md = replace_markdown_title(post_md, groq_title)
        title_provider = "groq"
        title_model = groq_title_model
        print(f"Groq headline selected with {groq_title_model}.")

    title_match = re.search(r"^#\s+(.+)$", post_md, re.M)
    title = title_match.group(1).strip() if title_match else f"AI briefing - {date_str}"
    headline_issues = validate_headline(title, date_str, context["prior_titles"])
    if headline_issues:
        raise RuntimeError(
            "Generated headline failed validation: " + "; ".join(headline_issues)
        )
    slug = unique_slug(slugify(title) or f"briefing-{date_str}", date_str, manifest)

    post_path = blog_dir / f"{date_str}-{slug}.md"
    post_path.write_text(post_md, encoding="utf-8")

    entry = {
        "date": date_str,
        "week": week,
        "title": title,
        "file": post_path.as_posix(),
        "excerpt": article_excerpt(post_md),
        "synthesis_provider": provider,
        "title_provider": title_provider,
        "source_count": (
            len(hf_papers) + len(official_news) + len(releases) + len(arxiv)
        ),
        "source_mix": {
            "hf_papers": len(hf_papers),
            "official_news": len(official_news),
            "release_notes": len(releases),
            "arxiv": len(arxiv),
            "community": len(hn),
        },
        "word_count": len(re.findall(r"\b[\w'-]+\b", post_md)),
        "source_urls": sorted(urls),
    }
    if hf_papers and hf_papers[0].get("thumbnail"):
        entry["hero_image"] = hf_papers[0]["thumbnail"]
    if model:
        entry["synthesis_model"] = model
    if title_model:
        entry["title_model"] = title_model
    manifest = prune_manifest(manifest, date_str)
    manifest.insert(0, entry)
    manifest_path.write_text(
        json.dumps(manifest[:52], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(
        f"Published {post_path} ({entry['word_count']} words, "
        f"{entry['source_count']} sources)"
    )


if __name__ == "__main__":
    main()
