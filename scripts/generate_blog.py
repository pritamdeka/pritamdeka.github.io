#!/usr/bin/env python3
"""Generate a substantive weekly AI/NLP research briefing.

Pipeline:
1. Collect and rank current Hacker News and arXiv signals.
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
            text = clean_text(re.sub(r"<[^>]+>", " ", story.get("text") or ""))
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
            abstract = xml_text(entry, "summary", namespace)
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


def source_dossier(hn, arxiv):
    sections = ["NEWS / ENGINEERING SIGNALS"]
    for index, story in enumerate(hn, 1):
        sections.append(
            f"[N{index}] {story['title']}\n"
            f"Primary URL: {story['url']}\n"
            f"HN discussion: {story['hn_url']}\n"
            f"Published: {story['published']} | Domain: {story['domain']} | "
            f"HN points: {story['score']} | Comments: {story['comments']}\n"
            f"Available context: {story['context'] or 'Title and engagement metadata only.'}"
        )
    sections.append("\nRESEARCH SIGNALS")
    for index, paper in enumerate(arxiv, 1):
        sections.append(
            f"[P{index}] {paper['title']}\n"
            f"URL: {paper['url']}\n"
            f"Published: {paper['published']} | Categories: "
            f"{', '.join(paper['categories'])}\n"
            f"Authors: {', '.join(paper['authors'])}\n"
            f"Abstract: {paper['abstract']}"
        )
    return "\n\n".join(sections)


def allowed_urls(hn, arxiv):
    urls = set()
    for story in hn:
        urls.update((story["url"], story["hn_url"]))
    for paper in arxiv:
        urls.add(paper["url"])
    return {url.rstrip("/") for url in urls if url}


def build_prompt(date_str, hn, arxiv):
    dossier = source_dossier(hn, arxiv)
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

Required Markdown structure:
# Week of {date_str}: <specific analytical title>

An opening thesis of 90-140 words stating the week's central pattern.

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
phrases, breathless claims, and summaries that merely repeat source titles.

SOURCE DOSSIER
{dossier}
"""


def extract_urls(markdown):
    return {url.rstrip("/") for url in re.findall(r"https?://[^)\s>]+", markdown)}


def validate_draft(markdown, date_str, source_urls):
    issues = []
    words = re.findall(r"\b[\w'-]+\b", markdown)
    if not markdown.startswith(f"# Week of {date_str}:"):
        issues.append(f"heading must start exactly '# Week of {date_str}:'")
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
    lowered = markdown.lower()
    used_generic = [phrase for phrase in GENERIC_PHRASES if phrase in lowered]
    if used_generic:
        issues.append("contains generic phrases: " + ", ".join(used_generic))
    if len(re.findall(r"\b(however|because|therefore|trade-off|limitation|risk)\b", lowered)) < 3:
        issues.append("insufficient analytical or caveat language")
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


def generate_validated_draft(prompt, date_str, urls):
    attempts = []
    try:
        draft = call_gemini(prompt)
        issues = validate_draft(draft, date_str, urls)
        attempts.append(("gemini", GEMINI_MODEL, issues))
        if not issues:
            return draft, "gemini", GEMINI_MODEL
        print("Gemini draft rejected: " + "; ".join(issues))
        revised = call_gemini(revision_prompt(prompt, draft, issues))
        revised_issues = validate_draft(revised, date_str, urls)
        attempts.append(("gemini-revision", GEMINI_MODEL, revised_issues))
        if not revised_issues:
            return revised, "gemini", GEMINI_MODEL
        print("Gemini revision rejected: " + "; ".join(revised_issues))
    except Exception as error:
        print(f"Gemini unavailable ({type(error).__name__}: {error})")

    try:
        draft, model = call_groq(prompt)
        issues = validate_draft(draft, date_str, urls)
        attempts.append(("groq", model, issues))
        if not issues:
            return draft, "groq", model
        print(f"Groq draft rejected ({model}): " + "; ".join(issues))
        revised, revision_model = call_groq(revision_prompt(prompt, draft, issues))
        revised_issues = validate_draft(revised, date_str, urls)
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
    return f"[{clean_text(title)}]({url})" if url else clean_text(title)


def build_fallback_post(date_str, hn, arxiv):
    """Build a readable source-led briefing when both AI providers fail."""
    strongest_news = hn[:3]
    strongest_papers = arxiv[:5]
    theme_terms = []
    combined = " ".join(item["title"].lower() for item in strongest_news + strongest_papers)
    for phrase in TOPIC_WEIGHTS:
        if phrase in combined:
            theme_terms.append(phrase)
    theme = ", ".join(theme_terms[:3]) or "applied AI systems"

    lines = [
        f"# Week of {date_str}: Signals across {theme}",
        "",
        "This week's strongest public signals point less to a single breakthrough "
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
            f"- **{markdown_link(story['title'], story['url'])}** attracted "
            f"{story['score']} points and {story['comments']} comments on "
            f"[Hacker News]({story['hn_url']}). Engagement is not evidence of technical "
            "quality, but it is a useful indicator of where practitioners are finding "
            "friction, opportunity, or disagreement."
        )
    lines.extend([
        "",
        "Taken together, these discussions are worth reading for the implementation "
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
            f"Relevant categories: {', '.join(paper['categories'][:3])}."
        )
    lines.extend([
        "",
        "## Practical implications",
        "",
        "- Reproduce the most relevant claim on a small internal dataset before changing architecture.",
        "- Separate retrieval, generation, and verification metrics so aggregate scores do not hide failure modes.",
        "- Record latency, token use, and human-review burden alongside task quality.",
        "- Test the system on distribution shifts and incomplete documents, not only clean benchmark inputs.",
        "- Treat community excitement as a discovery signal, then verify claims against primary evidence.",
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


def main():
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d")
    week = now.strftime("%G-W%V")

    hn = fetch_hn_ai_stories()
    arxiv = fetch_arxiv_papers()
    print(f"Ranked signals: {len(hn)} HN stories, {len(arxiv)} arXiv papers")
    if not hn and not arxiv:
        raise RuntimeError("No source signals were available; refusing to publish an empty post")

    prompt = build_prompt(date_str, hn, arxiv)
    urls = allowed_urls(hn, arxiv)
    provider = "deterministic"
    model = None
    try:
        post_md, provider, model = generate_validated_draft(prompt, date_str, urls)
        print(f"Editorial draft passed with {provider}/{model}.")
    except Exception as error:
        print(f"AI editorial pipeline unavailable ({error})")
        post_md = build_fallback_post(date_str, hn, arxiv)

    title_match = re.search(r"^#\s+(.+)$", post_md, re.M)
    title = title_match.group(1).strip() if title_match else f"AI briefing - {date_str}"
    slug = slugify(title) or f"briefing-{date_str}"

    blog_dir = Path("blog")
    blog_dir.mkdir(exist_ok=True)
    post_path = blog_dir / f"{date_str}-{slug}.md"
    post_path.write_text(post_md, encoding="utf-8")

    manifest_path = blog_dir / "index.json"
    manifest = load_manifest(manifest_path)
    entry = {
        "date": date_str,
        "week": week,
        "title": title,
        "file": post_path.as_posix(),
        "excerpt": clean_text(re.sub(r"[#*\[\]()>]", "", post_md))[:220] + "...",
        "synthesis_provider": provider,
        "source_count": len(hn) + len(arxiv),
        "word_count": len(re.findall(r"\b[\w'-]+\b", post_md)),
    }
    if model:
        entry["synthesis_model"] = model
    manifest = [item for item in manifest if item.get("date") != date_str]
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
