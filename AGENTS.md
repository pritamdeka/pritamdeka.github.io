# AGENTS.md

Static personal academic website deployed via GitHub Pages (user site
`pritamdeka.github.io`). No build step, no package manager, no framework.

## Deploy

- Push to `main` → live on GitHub Pages. There is no preview/staging branch.
- No `npm`/`pip`/test/lint/typecheck/format commands exist. Verify HTML/JS
  edits by opening the files locally in a browser.

## Architecture

- Five static pages share one stylesheet and one script:
  `index.html`, `education.html`, `papers.html`, `activities.html`, `blog.html`
  → `style-dynamic.css` + `dynamic.js`.
- All content (news, experience, skills, research interests, the search
  index, the journey map, the vis-network research graph) is hardcoded
  either in the HTML or as JS arrays in `dynamic.js`. There is no data
  layer — edit the markup/JS directly. The exception is the blog (see below).
- `cv/Pritam_Deka_CV.pdf` is linked from the sidebar; `favicon.svg` is an
  SVG monogram referenced from all pages.

## Service worker

- `sw.js` (root) caches the site shell for offline/instant repeat loads.
- Registered from `dynamic.js` only on HTTPS (so it's live on GitHub Pages
  but inert for `file://` local testing). Bump `CACHE` const in `sw.js`
  when changing cached assets; the activate handler purges old versions.
- Network-first for HTML/JSON (fresh content), cache-first for static
  assets; cross-origin (CDN fonts, third-party APIs) is never cached.

## External services wired in `dynamic.js`

- `citations.json` + `citations-history.json` fetched at runtime to
  populate the publication/citation counters and the growth sparkline;
  on failure falls back to hardcoded `10+` / `174`.
- HuggingFace stats via `https://huggingface.co/api/models?author=pritamdeka`
  (5s timeout; shows `—` on failure, not a fake number).
- View counter via `https://api.countapi.xyz` (frequently down; 4.5s
  timeout then shows `—` gracefully — no longer silently inflates a
  localStorage number).
- Contact form posts to Formspree endpoint `https://formspree.io/f/mzdjpyve`.
- Google Scholar author ID `b0jYTAUAAAAJ` is hardcoded here and in the
  fetch script.
- CDN deps: Font Awesome 6.4.2, vis-network (UMD standalone), marked.js
  (blog page only), Google Fonts (Sora + Inter).

## `citations.json` & `citations-history.json` are auto-generated

- Owned by `scripts/fetch_citations.py` + the daily CI workflow
  `.github/workflows/update-citations.yml`.
- Workflow runs on cron `0 3 * * *` and via `workflow_dispatch`; uses
  Python 3.11, installs `requests`, calls SerpAPI's
  `google_scholar_author` engine with the `SERPAPI_KEY` repo secret.
- The script writes both `citations.json` (current totals) AND appends a
  dated snapshot to `citations-history.json` (kept to last 180 days),
  which feeds the citation-growth sparkline in the sidebar.
- Without `SERPAPI_KEY` the script writes fallback values (`174`
  citations / `10` papers) — so a missing secret silently produces
  stale-looking numbers, not an error.
- The same workflow also runs `scripts/generate_feed.py` to regenerate
  `feed.xml` (Atom) from the news items in `index.html`.
- CI auto-commits with message `📊 Auto-update citation count [skip ci]`
  (the `[skip ci]` is intentional). Any manual edit to `citations.json`
  or `citations-history.json` will be overwritten on the next successful run.

## Weekly AI blog (auto-generated)

- `scripts/generate_blog.py` + `.github/workflows/weekly-blog.yml`
  (cron `0 9 * * 1` = 09:00 UTC every Monday, plus `workflow_dispatch`).
- Fetches real signals: top Hacker News AI stories + recent arXiv cs.CL
  papers, then asks Google Gemini (`gemini-2.5-flash`) to synthesize a
  weekly digest. Needs `GEMINI_API_KEY` repo secret.
- Writes a dated markdown file to `blog/` and updates `blog/index.json`
  manifest (kept to last 52 weeks). `blog.html` fetches the manifest and
  renders posts client-side with marked.js.
- Without `GEMINI_API_KEY` the script prints an error and exits — no
  post is written, no commit happens.
- Auto-commits with `📝 Weekly AI digest [skip ci]`.

## RSS/Atom feed

- `feed.xml` (Atom 1.0) is regenerated from `index.html` news items by
  `scripts/generate_feed.py` (stdlib only, no deps). Run in the daily
  citations workflow so it stays in sync. Add news items to `index.html`
  and the next CI run updates the feed.

## Editing notes

- The Python scripts only run in CI; they are not part of local dev and
  have no effect on the rendered site beyond producing their data files.
  `generate_feed.py` CAN be run locally (stdlib only) to preview feed.xml.
- When updating bio/news/experience, keep the existing emoji-icon
  conventions in headings (`<i class="fas ...">`) and the `fade-in`
  section classes — the CSS depends on them.
- Motion uses shared `--ease` / `--dur` / `--dur-slow` CSS tokens —
  prefer these over hardcoded timings in new transitions.
- Commit messages in this repo commonly use a leading emoji
  (e.g. `📊`, `📝`, `Updates`); match the casual style when committing
  content changes.
