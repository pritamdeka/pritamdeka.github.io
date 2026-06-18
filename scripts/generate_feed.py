#!/usr/bin/env python3
"""Generate an Atom feed (feed.xml) from news items + weekly blog posts.

Parses the .news-item blocks in index.html AND reads blog/index.json,
merges them by date, and writes a valid Atom 1.0 feed.
Run locally or in CI. No third-party deps — stdlib only.
"""
import json
import re
import html
from datetime import datetime, timezone
from pathlib import Path

SITE = "https://pritamdeka.github.io"
AUTHOR = "Dr. Pritam Deka"
FEED_ID = f"urn:uuid:pritamdeka-{SITE}"

MONTHS = {
    'January': 1, 'February': 2, 'March': 3, 'April': 4, 'May': 5, 'June': 6,
    'July': 7, 'August': 8, 'September': 9, 'October': 10, 'November': 11, 'December': 12
}

def parse_news(html_text):
    """Extract (date_str, heading, body) tuples from .news-item blocks."""
    items = []
    for m in re.finditer(r'<div class="news-item">\s*<span class="news-date">(.*?)</span>\s*<div class="news-content">\s*<h4>(.*?)</h4>\s*<p>(.*?)</p>\s*</div>\s*</div>', html_text, re.S):
        date_str, heading, body = m.group(1), m.group(2), m.group(3)
        heading = re.sub(r'<[^>]+>', '', heading).strip()
        body = re.sub(r'<[^>]+>', '', body).strip()
        items.append((date_str.strip(), heading, body))
    return items

def parse_blog():
    """Read blog/index.json and return (date, title, excerpt, file) tuples."""
    p = Path('blog/index.json')
    if not p.exists():
        return []
    try:
        manifest = json.loads(p.read_text(encoding='utf-8'))
    except (json.JSONDecodeError, OSError):
        return []
    return [(b.get('date', ''), b.get('title', ''), b.get('excerpt', ''), b.get('file', ''))
            for b in manifest if b.get('date')]

def to_iso_date(date_str):
    """Convert 'March 2026' or '2026-06-18' -> ISO 8601 UTC."""
    m = re.match(r'(\w+)\s+(\d{4})', date_str)
    if m:
        month, year = MONTHS.get(m.group(1), 1), int(m.group(2))
        return f"{year:04d}-{month:02d}-01T00:00:00Z"
    m = re.match(r'(\d{4})-(\d{2})-(\d{2})', date_str)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}T09:00:00Z"
    return datetime.now(timezone.utc).isoformat()

def esc(s):
    return html.escape(s, quote=True)

def main():
    idx = Path('index.html')
    if not idx.exists():
        print("index.html not found")
        return
    html_text = idx.read_text(encoding='utf-8')
    news = parse_news(html_text)
    blog = parse_blog()

    entries = []

    # News items (personal updates)
    for i, (date_str, heading, body) in enumerate(news):
        iso = to_iso_date(date_str)
        eid = f"urn:pritamdeka:news:{i}:{iso[:7]}"
        entries.append({
            'iso': iso,
            'xml': f"""  <entry>
    <id>{eid}</id>
    <title>{esc(heading)}</title>
    <link href="{SITE}/#news"/>
    <updated>{iso}</updated>
    <published>{iso}</published>
    <summary>{esc(body)}</summary>
    <author><name>{AUTHOR}</name></author>
  </entry>"""
        })

    # Blog posts (weekly AI digest)
    for b in blog:
        date_str, title, excerpt, file = b
        iso = to_iso_date(date_str)
        eid = f"urn:pritamdeka:blog:{iso[:10]}"
        link = f"{SITE}/{file}" if file else f"{SITE}/blog.html"
        entries.append({
            'iso': iso,
            'xml': f"""  <entry>
    <id>{eid}</id>
    <title>{esc(title)}</title>
    <link href="{link}"/>
    <updated>{iso}</updated>
    <published>{iso}</published>
    <summary>{esc(excerpt)}</summary>
    <author><name>{AUTHOR} (AI digest)</name></author>
  </entry>"""
        })

    if not entries:
        print("No news or blog items found")
        return

    # Sort by date descending (newest first)
    entries.sort(key=lambda e: e['iso'], reverse=True)
    updated = entries[0]['iso']

    feed = f"""<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>{AUTHOR} — News &amp; Weekly AI Digest</title>
  <link href="{SITE}/" rel="alternate" type="text/html"/>
  <link href="{SITE}/feed.xml" rel="self" type="application/atom+xml"/>
  <id>{FEED_ID}</id>
  <updated>{updated}</updated>
  <author><name>{AUTHOR}</name></author>
{chr(10).join(e['xml'] for e in entries)}
</feed>
"""
    Path('feed.xml').write_text(feed, encoding='utf-8')
    print(f"feed.xml generated with {len(news)} news + {len(blog)} blog = {len(entries)} entries")

if __name__ == '__main__':
    main()
