#!/usr/bin/env python3
"""Generate an Atom feed (feed.xml) from the news items in index.html.

Parses the .news-item blocks inside #news and writes a valid Atom 1.0 feed.
Run locally or in CI after editing news. No third-party deps — stdlib only.
"""
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

def to_iso_date(date_str):
    """Convert 'March 2026' -> '2026-03-01T00:00:00Z' (first of month)."""
    m = re.match(r'(\w+)\s+(\d{4})', date_str)
    if not m:
        return datetime.now(timezone.utc).isoformat()
    month, year = MONTHS.get(m.group(1), 1), int(m.group(2))
    return f"{year:04d}-{month:02d}-01T00:00:00Z"

def esc(s):
    return html.escape(s, quote=True)

def main():
    idx = Path('index.html')
    if not idx.exists():
        print("index.html not found")
        return
    html_text = idx.read_text(encoding='utf-8')
    news = parse_news(html_text)
    if not news:
        print("No news items found")
        return

    updated = max(to_iso_date(d) for d, _, _ in news)
    entries = []
    for i, (date_str, heading, body) in enumerate(news):
        iso = to_iso_date(date_str)
        eid = f"urn:pritamdeka:news:{i}:{iso[:7]}"
        entries.append(f"""  <entry>
    <id>{eid}</id>
    <title>{esc(heading)}</title>
    <link href="{SITE}/#news"/>
    <updated>{iso}</updated>
    <published>{iso}</published>
    <summary>{esc(body)}</summary>
    <author><name>{AUTHOR}</name></author>
  </entry>""")

    feed = f"""<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>{AUTHOR} — News</title>
  <link href="{SITE}/" rel="alternate" type="text/html"/>
  <link href="{SITE}/feed.xml" rel="self" type="application/atom+xml"/>
  <id>{FEED_ID}</id>
  <updated>{updated}</updated>
  <author><name>{AUTHOR}</name></author>
{chr(10).join(entries)}
</feed>
"""
    Path('feed.xml').write_text(feed, encoding='utf-8')
    print(f"feed.xml generated with {len(news)} entries")

if __name__ == '__main__':
    main()
