# Blogheading — Full Codebase Documentation

**Scope:** every module in the repository, what it does, what's live vs. dead, and where behavior diverges from what other docs in this repo claim. This document is the ground-truth map of the code as it actually exists, verified by direct reading + cross-repo grep, not by trusting docstrings or the older `Blogheading docs·md`.

Companion docs, and how this one relates to them:
- `Blogheading docs·md` — the original architecture writeup (SEO rules, stack system, IPO pipeline). Broadly accurate, but was written before some prompt/feature reverts (see §9 and §12). Read alongside this doc for the SEO prompt-engineering rationale, which isn't repeated here.
- `REVIEW.md` — a line-referenced bug/dead-code audit. This doc incorporates its dead-code findings directly (marked **dead** below) rather than repeating the bug list; go to `REVIEW.md` for exact fix recommendations.
- `SEO_TOOLS_INTEGRATION.md` — a *planned, not-yet-built* Google Keyword Planner + Semrush integration. Not implemented in code today.
- `CLAUDE.md` — short orientation notes for AI coding agents working in this repo.

---

## 1. What this system does

A 24/7 pipeline that watches Indian financial news + NSE IPO filings, turns fresh items into AI-generated SEO blogs (with push notification + Instagram caption + 3 composited images), and publishes them to Webflow as CMS drafts. Two containers run continuously: a **scheduler** (pipeline + auto-publish) and a **Streamlit dashboard** (manual review).

**Tech stack:** Python 3.10 (Dockerfile) / doc claims 3.11 elsewhere — unify before trusting either; APScheduler; OpenAI (`gpt-image-1` for images, a reasoning-capable text model via the Responses API for copy); Webflow CMS API v2; BeautifulSoup4/trafilatura/newspaper3k/curl_cffi/Selenium for scraping; Pillow for image compositing; Google Ads API (Keyword Planner) for search volume.

---

## 2. Entry points — which process actually runs what

| File | Used in production? | What it does |
|---|---|---|
| `scheduler.py` | **Yes** — `docker-compose.yml` runs `python3 scheduler.py` in the `blogheading-scheduler-1` container | `BlockingScheduler` cron job every 8 minutes: `run_pipeline()` → if a new article resulted, hands it to `mcp_agent.run_agent(entry=results[0])`, which auto-publishes to Webflow. Runs once immediately on start, then on the cron schedule. |
| `app.py` | **Yes** — its own container, `blogheading-streamlit-1` | Streamlit dashboard. Reads `output/output.json` (or `output/testing_webp_output.json` when `USE_AI_IMAGES=True`) independently of the scheduler; assembles final blog HTML from separate JSON fields (title/TLDR/content/FAQ/conclusion) — see `Blogheading docs·md` §13 for the exact assembly rules. Not involved in publishing. |
| `run.py` | **No** — not referenced by `docker-compose.yml` or the `Dockerfile` CMD | An alternate, unused scheduler: runs the pipeline every 5 minutes via `BackgroundScheduler` and launches Streamlit as a subprocess in the same process. Legacy/alternative harness — don't assume it's what's deployed. |

**Two different cron intervals are documented inconsistently across the repo**: `scheduler.py` (live) runs every 8 minutes; `run.py` (dead) every 5 minutes; `Blogheading docs·md` says "every 15 minutes". Trust `scheduler.py`'s `*/8` as current production behavior.

---

## 3. Pipeline core — `pipeline.py`

5,648 lines total; **only one ~915-line block (currently starting at `def run_pipeline` around line 1746) is live**. Everything before and after it is one or two entire prior versions of the same pipeline, left as commented-out history. When editing, confirm you're in the active block.

The stack system, posting pattern, IPO scraping waterfall (implemented in `RSS/ipo.py`, called from here), and image-generation decision tree are documented in depth in `Blogheading docs·md` §2–§10 — not repeated here. Key facts that doc doesn't make explicit:

- **AI country/category filtering** (`utils/combined_filter.py::filter_by_country_and_category`) is applied to all non-IPO articles; IPO articles bypass it entirely (their content is structured data, not prose, and the AI filter misclassifies it as non-finance).
- **Freshness filtering** (`utils/date_filter.py::filter_fresh_articles`) restricts articles to same-day IST publish windows (12:00 AM–6:00 PM), with `nse_ipo`/`nse_corporate` sources exempted (`BYPASS_SOURCES`).
- **Timing instrumentation** (`utils/timer.py`) wraps fetch/generation steps via `@timed` and `Timer(...)` context managers, logging to `pipeline_timing.log`.
- Corporate-action articles (`source=nse_corporate`) are routed through the **generic** `AI_GEN/blog_generator.py::generate_blog()`, not a dedicated corporate-blog generator — see §5.4 for why the dedicated one exists but is dead.
- `USE_AI_IMAGES` (module-level bool) must be manually kept in sync with the identical flag in `app.py` — flipping one without the other desyncs which output file/image path the dashboard reads vs. what the pipeline writes.

---

## 4. RSS / news source fetchers — `RSS/`

Twelve files. Each returns a list of article dicts; **field names are not consistent across files** — see §4.13.

### 4.1 `RSS/ipo.py` — NSE IPO scraper (most complex file in the repo)

~2600 lines; only the block from line ~1690 onward is live (2+ full prior implementations sit above it, commented out).

**`fetch_nse_ipo() -> list`** — two-stage discovery + per-company enrichment waterfall:

1. **Discovery** — `_fetch_nse_current_companies()`:
   - NSE JSON API (`_build_nse_session()` visits the homepage + IPO page first to collect anti-bot cookies, then hits `all-upcoming-issues?category=ipo` and `category=sme`), filtered to `status` ∈ `{active, open, live, ongoing}`.
   - Selenium fallback (`_scrape_nse_page_selenium()`, headless Chrome via `webdriver_manager`) — scrapes the rendered IPO table directly, because the JSON API frequently omits SME IPOs. Deduped against API results by lowercased company name. Selenium/webdriver_manager import is wrapped in `try/except ImportError` so the module still works if those packages aren't installed (returns `[]` for that step instead of crashing).

2. **Per-company enrichment** — `_scrape_ipo_details(company_name)`:
   - Cache check first: `_normalize_company_key()` strips `" limited"/" ltd"/" ipo"/" india"` and lowercases, so "Hexagon Nutrition Limited" / "HEXAGON NUTRITION LTD" / "Hexagon Nutrition IPO" all hit the same in-memory cache entry (`_ipo_data_cache`, 6-hour TTL).
   - On a cache miss, waterfall: **Chittorgarh** (`_scrape_chittorgarh`, richest structured data — 20+ fields from table rows plus regex-scraped GMP/business description/financials/market cap) → **InvestorGain** (`_scrape_investorgain`) → **Moneycontrol** (`_scrape_moneycontrol`, regex-only since the site isn't table-structured) → stale cache entry (tagged `data_source: "cache_stale"`) if all three fail → `{}`.
   - `_build_ipo_map()` (Chittorgarh's list-of-all-IPOs page → company-name→URL DataFrame) is cached **once per process with no TTL** — a long-lived container never re-discovers IPOs filed after the process started. This is the TTL gap `REVIEW.md` flags.
   - `_parse_ipo_date()` handles both `"5 to 9 Jun, 2026"` (same-month) and `"29 May to 2 Jun, 2026"` (cross-month) date-range formats from Chittorgarh.
   - `_validate_ipo_article()` is a quality gate only — it can log errors (e.g. `open_date` containing 2+ month names, indicating a parser bug) but **the live `fetch_nse_ipo()` appends the article regardless of validation result** ("adding anyway"), so active IPOs are never silently dropped by this check even when it fails.

**Output fields** (note: this source does *not* follow the `Blog_Links`/`Blog_PublishDate` convention used by the news scrapers): `Blog_Title, Blog_Content, source="nse_ipo", company, doc_type, data_source, ipo_date, open_date, close_date, listing_date, price_band, lot_size, issue_size, face_value, exchange, issue_type, sale_type, gmp, market_cap, ipo_url, status, published`.

### 4.2 `RSS/fetch_nse_corporate.py` — NSE corporate actions

Fetches `Corporate_action.xml` from NSE archives and parses each entry's title (`"{Company} - Ex-Date: {date}"`) and pipe-delimited summary (`SERIES/PURPOSE/FACE_VALUE/RECORD_DATE/...`) into structured fields. Classifies action type (`_classify`: dividend/bonus/split/rights/buyback/agm/egm/general) and extracts a formatted amount per type (`_extract_amount`: `"₹X per share"` for dividends, `"N:M"` ratio for bonus, split-ratio for splits, etc.). Builds a human-readable `title_hint` per action type for the image compositor. **`Blog_Title` is deliberately left as `""`** — the docstring says a downstream `generate_corporate_blog()` should fill it in, but that function is dead code (§5.4); in the live pipeline, corporate items are generated via the same `generate_blog()` used for news.

No caching. Catches `requests.RequestException`/non-200 and returns `[]` rather than raising; per-entry parse failures are logged and skipped without aborting the batch.

### 4.3 News scrapers — common pattern

`zerodha.py`, `cnbc.py`, `paisa.py` (5paisa), `livemint.py`, `Business_Standard.py`, `economic_times.py`, `ndtv_profit.py` all follow the same shape: fetch one or more RSS feeds → for each entry, try a chain of scraping strategies gated by a `MIN_WORDS` (usually 150) threshold → clean the extracted text with source-specific regex boilerplate stripping → fall back to the RSS summary if nothing scrapes well.

Output fields (the common convention): `Blog_Title, Blog_Links, Blog_PublishDate, Blog_Content, source, source_name, _source_type="news", _content_words, _content_quality`.

Per-file notes:

- **`zerodha.py`** — Zerodha Pulse is an *aggregator* feed; `Blog_Links` points to the original publisher (economictimes, thehindu, livemint, business-standard, ndtvprofit, etc.), so this file re-scrapes the true source. NDTV Profit URLs get their own 4-tier bypass chain (`curl_cffi` → AMP page with Googlebot UA → cookie-session fetch → Google cache) — implemented independently here, duplicated with different logic in `ndtv_profit.py` (see cross-file note below). Used as the **pipeline's fallback source**: if all 6 configured sources return nothing fresh after dedup, one random Zerodha article is published immediately, bypassing the stack system (per `Blogheading docs·md` §4) — but note the P1 bug in `REVIEW.md` #3: the dedup list computed for this fallback is not actually what gets selected.
- **`cnbc.py`** — explicitly documented in-code as **blocked by CNBC's IP allowlist WAF from server/cloud IPs**; scraping is attempted anyway and expected to fall back to the RSS summary in production, working correctly only when run locally. Contains several oddly specific hardcoded strip patterns (e.g. a Hormuz-strait-article subheading regex) — evidence of iterative live-patching against real feed content rather than general rules.
- **`paisa.py`** (5paisa) — cleanup patterns include a literal leaked-PowerShell-prompt regex (`^ps d:\\.*`), suggesting a dev-environment artifact once leaked into scraped content and was patched around rather than fixed at the source.
- **`livemint.py`** — the most elaborate content cleaner in the set: `find_bio_start()` heuristically detects and truncates trailing author-bio blocks (looking for phrases like "is a journalist and editor", "based in New Delhi", email/handle patterns) rather than relying on a fixed footer length, since bio length varies per author.
- **`Business_Standard.py`** — the only file that does **not** scrape full articles at all; content is the RSS summary only, HTML-unescaped by hand (no BeautifulSoup). Fetches all entries per feed (no `top_n` per-feed), merges 4 feeds, dedups by normalized title, then slices to `top_n` on the combined set.
- **`economic_times.py`** — the only news scraper that actively **drops** entries with empty/<30-word content rather than keeping them tagged `quality: "empty"` like its siblings.
- **`ndtv_profit.py`** — imports `utils.mcp_tools.fetch_and_clean` (a shared scraper cascade also used by `AI_GEN/blog_generator.py`) as its fallback tier, via a `sys.path.insert` hack at module top so the import resolves regardless of working directory. **NDTV Profit scraping is thus implemented twice in the repo** — independently in `zerodha.py` (self-contained 4-tier chain) and here (curl_cffi-first + shared-utility fallback) — with no code sharing.

An identical `assess_quality()` (word-count → rich/thin/bare/empty bucket) function is copy-pasted verbatim across `zerodha.py`, `cnbc.py`, `paisa.py`, `livemint.py`, `economic_times.py` — a candidate for extraction into a shared utility, currently duplicated 5 times.

### 4.4 `RSS/google_trends.py`

Fetches Google Trends India RSS (`ht:` namespace) via raw regex over XML rather than `feedparser`. Each trend can carry up to 3 related news-item URLs; `_resolve_title()` falls back from a possibly-unusable trend title (numeric, too short, or regional-script) to the best available English-language related headline. `_scrape_all_news_urls()` tries the related URLs in order and **stops early** once cumulative scraped content reaches 400 chars, to minimize outbound requests. `Blog_Content` is a composite of trend metadata + related headlines + (if scraped) article snippets — explicitly framed as an LLM prompt scaffold, not raw article text.

### 4.5 `RSS/google_news_business.py`

Parses a Google News "topic" RSS feed's `<description>` HTML (a list of related-publisher headlines with source `<font>` tags) — performs **zero** article scraping. `Blog_Content` is synthesized entirely from headline aggregation across publishers, again explicitly as an LLM prompt scaffold.

### 4.6 `RSS/test.py` — not a test file

Despite the name, this is a **Finnhub REST API** fetcher (`fetch_finnhub_news`, `fetch_finnhub_company_news`), unrelated to RSS or to the repo's actual test scripts. Reads `FINNHUB_API_KEY` from `.env` at import time. Hardcodes `+0530` (IST) when formatting API timestamps regardless of server timezone. Not documented as wired into `pipeline.py`'s live source list — verify before assuming it's used.

### 4.7 Field-name drift summary

| Convention | Files |
|---|---|
| `Blog_Title/Blog_Links/Blog_PublishDate/Blog_Content` + `source`/`source_name`/`_source_type`/`_content_words`/`_content_quality` | zerodha, cnbc, paisa, livemint, business_standard, economic_times, ndtv_profit, test.py (Finnhub) |
| `Blog_Title/Blog_Content` but `published` (no `Blog_Links`), uses `ipo_url` | ipo.py |
| `Blog_Links`/`Blog_Title` (empty) but no `Blog_PublishDate`/`Blog_Content` (uses `pub_date`/`title`) | fetch_nse_corporate.py |
| `Blog_Links/Blog_PublishDate/Blog_Content/Blog_Title` but no `source`/`_content_*` fields | google_trends.py, google_news_business.py |

Downstream code (`app.py`, `pipeline.py`) handles this defensively field-by-field rather than through a shared schema.

---

## 5. AI content generation — `AI_GEN/`

### 5.1 `blog_generator.py` — the core generator (1,234 lines, all live — no dead code in this file)

**`generate_blog(item) -> dict`** — the main news/corporate blog generator:
1. Fetches real article text via `fetch_via_websearch(item["Blog_Links"])` (an OpenAI `web_search`-tool call, not the raw RSS content passed in).
2. Extracts keywords (`priAndsec_keywords.extract_keywords`) and looks up Google Ads search volume (`keyword_researcher.get_keyword_volumes`).
3. **Kill switch:** if the primary keyword has zero volume and no secondary keyword has volume > 0, the function returns `{}` — the article is silently dropped, no blog is produced.
4. Builds a long prompt (article-type detection, H2/H3 rules, title rules, banned-word substitutions — see `Blogheading docs·md` §11 for the SEO rule content) plus a keyword-substitution block and two rules not documented elsewhere: an "Expert Opinion Callout" format for named-analyst quotes (never invent a quote), and a rule to never attribute market stats to the reporting outlet.
5. Calls the model, JSON-parses the result; on `JSONDecodeError` attempts `repair_json()` (writes `repaired_blog_response.json` on success, `failed_blog_response.json` + returns `{}` on failure — no retry of the LLM call itself).
6. Runs `fix_all_fields(data)` (post-processors, below).

**`generate_ipo_blog(item) -> dict`** — separate IPO-specific prompt/pipeline; does not consult keyword volume or `priAndsec_keywords` at all; builds directly from `item['Blog_Title']`/`item['Blog_Content']`. Its JSON-repair fallback is different (escapes raw newlines and re-parses) — no `repair_json` fallback here.

**Post-processors** (all called via `fix_all_fields(data, source="")`, in this exact order against `Blog_Content`):

| # | Function | Fix |
|---|---|---|
| — | `fix_meta_length` | Truncates `Meta_Title` (60 chars) / `Meta_Description` (155 chars) |
| — | `fix_faq_schema_answers` | Strips HTML tags from FAQ schema answer text |
| — | `fix_tldr_list` | Strips stray HTML from each TLDR bullet |
| 1 | `fix_strip_tldr_from_content` | Removes a duplicate TLDR/"Key Takeaways" block accidentally embedded in `Blog_Content` |
| 2 | `fix_nested_p_tags` | Collapses `<p><p>x</p></p>` |
| 3 | `fix_html_tags` | General cleanup — dedupes tags, strips stray "Conclusion – Paragraph N:" labels, removes empty/orphan headings |
| 4 | `fix_tldr_h2` | Removes a bare `<h2>TLDR</h2>` heading |
| 5 | `fix_faq_tags` | `<h3>`→`<h4>` inside FAQ only |
| 6 | `fix_faq_h2_keyword` | Adds keyword to a bare FAQ `<h2>` |
| 7 | `fix_placeholder_h3` | Replaces known LLM placeholder H3s with content-derived headings |
| 8 | `fix_duplicate_swastika` | Keeps only the first Swastika-mentioning paragraph |
| 9 | `fix_swastika_heading` | Deletes any heading mentioning "swastika" (must only appear in `<p>`) |
| 10 | `fix_swastika_paragraph_start` | Prevents a paragraph opening with the literal word "Swastika" |
| 11 | `fix_table_na` | Replaces empty/N-A table cells with "To be announced" |
| — | *(disabled)* `fix_remove_non_ipo_table` | Commented out — currently never runs |
| 12 | `fix_faq_before_conclusion` | Moves FAQ block before Conclusion if order is wrong |
| 13 | `fix_ensure_conclusion` | Guarantees a real, non-empty Conclusion section exists (4-case fallback, including inserting a placeholder if nothing conclusion-like is found) |
| 14 | `fix_conclusion_labels` | Strips inline "Conclusion:"/"Takeaway:"/"Bottom line:" prefixes |

Applied to **all** string fields: `fix_em_dash` (em→en dash). Applied additionally to `Blog_Title`/`Meta_Title`/`Meta_Description`/`Conclusion` (**not** `Blog_Content`, contradicting `REVIEW.md` finding #6 and the older docs' claim that it runs on "all string fields"): `fix_garbage_characters` (strips non-ASCII except a small whitelist: ₹, en/em dash, °, curly quotes, ellipsis).

**Model call mechanics** (in `add_cached.py`, shared by everything in `AI_GEN/`): `cached_model_call(prompt)` is `@lru_cache(maxsize=200)`-decorated (near-zero real hit rate since prompts embed full article bodies — flagged in `REVIEW.md`), uses OpenAI's Responses API in JSON-object mode with `reasoning={"effort":"high"}`, no `temperature` param. Every call is logged to `logs/prompts/{date}.txt` with token counts and a hardcoded $3/$15-per-million cost estimate (wrong if the model changes — also flagged in `REVIEW.md`). No retry/backoff around the network call itself in `blog_generator.py`.

### 5.2 `notify_generator.py`

`generate_notification(item) -> {"blog_notify": str}` — single push-notification sentence, max 130 chars, one sentence, no hashtags/newlines, includes a one-shot worked example embedded in the prompt. No error handling around `json.loads` — a malformed model response raises uncaught.

### 5.3 `generate_instagram_caption.py`

`generate_instagram_caption(item) -> {"instagram_caption": str, "hashtags": str}` — informal single-paragraph caption + fixed 5-hashtag string, structured as hook → money-relevance → simplify → takeaway → closing line → Swastika-app CTA tied to the specific news topic. Contains **two full dead prompt variants** left commented out inside the live file (a stricter "STRICT DOMAIN RULES" version above the function, and a punchier alternate version inside it) — only one prompt (lines ~94–157) is actually sent.

### 5.4 Dead/orphaned files in `AI_GEN/`

- **`generate_corporate_blog.py`** — a fully built, well-documented 612-line module whose own docstring claims `pipeline.py` imports it for `nse_corporate` items. **This is false in the current code** — confirmed by repo-wide grep, nothing imports it. Corporate items are actually generated through the generic `generate_blog()`. Its own internal import (`from add_cached import cached_model_call, fix_all_fields`) is itself stale, since `fix_all_fields` lives in `blog_generator.py`, not `add_cached.py` — further evidence this predates the current pipeline shape.
- **`AI_GEN/prompts/news_prompt.py`, `corporate_prompt.py`, `priority_prompt.py`** — an alternate, more rigid prompt design (numbered "MUST INCLUDE" checklists) from an earlier iteration. Confirmed via grep: none of their exports are imported anywhere in the repo. Fully dead.
- **`filter_by_category_model.py`** and **`get_system_timestamp.py`** — both **live**, but only via the dead `mergeall.py` predecessor (§7), not the current `pipeline.py` pipeline.

---

## 6. Image generation — `content_engine/image_module/`

Two production template categories exist under `content_engine/templates/`: `finance/` and `general/` (the hardcoded fallback), each with exactly 17 `outer` (640×480) + 17 `inner` (1920×490) template PNGs and its own `image_descriptions.json` (used for AI template selection, §6.3). There is no `ipo/` subfolder — IPO template paths are supplied externally by the caller, not resolved by this module.

**`storage.py` is completely empty (0 bytes)** — despite the name, no persistence logic lives here; saving is implemented inline in each generator (`_save_both_formats` in `compositor.py`/`ipo_compositor.py`, `save_image_formats` in `ai_image_generator.py`).

### 6.1 `compositor.py` — non-IPO template compositing

Live code is lines 207–531 (2,298-line file — the rest is 5+ historical rewrites, commented out).

- `FONTS` dict references `ExtraBold.ttf`/`Regular.ttf` (PascalCase); the actual files on disk are lowercase (`extrabold.ttf`, `regular.ttf`) — matches only for the Google Sans bold file. Works on Windows (case-insensitive FS); on a case-sensitive Linux container, `get_font()` silently falls back to hardcoded `/usr/share/fonts/...` DejaVu/Liberation paths, which may not exist, ultimately falling to PIL's bitmap default font — with no error raised anywhere in that chain.
- `compose_image(template_path, texts, jpg_path, webp_path, image_type)`:
  - `"blog_inner"` → template used as-is at native size (expected 1920×490), **no text overlay**.
  - `"instagram"` → center-crop-to-fill to exactly 1080×1080, then text composited.
  - default/`"blog_outer"` → template used as-is (expected 640×480), then text composited.
  - Text zones (`_compose_with_text`): gradient overlay over the bottom 55%(blog)/60%(instagram) of the image; a blue "tag" badge; auto-shrinking headline font (42px→24px floor for blog, 64px→24px for instagram) that word-wraps by measured pixel width; a 2-line subtext block. All x-positions are fixed pixel offsets (30px left margin); only heights/y-positions are percentage-of-image-size based.
  - `texts` dict consumed here (`headline`, `subtext`, `tag`) is produced by `text_extractor.py` (§6.4).

### 6.2 `ipo_compositor.py` — IPO alert template compositing

Live code is lines 420–851 (851-line file; lines 1–419 are a commented-out earlier, non-auto-sizing version). Same font-casing mismatch as `compositor.py`.

- Percentage-based zone coordinates for company name + 6 data fields (`date/price/lot/size/allotment/listing`), separate coordinate sets for `blog` vs `instagram` image types — full zone table already documented in `Blogheading docs·md` §8.2, not repeated here.
- `_fit_company_name()` auto-shrinks the company-name font (24px→14px for blog, 43px→20px for instagram, 1px steps) and tries 1-line then 2-line layouts before falling back to character-truncation with `"..."`, so long company names never overflow into the "IPO ALERT" heading or funnel icon above/below.
- `_prepare_ipo_data()` transforms raw scraped fields into short display strings: combined date range, lot size with "Shares" suffix stripped, regex-extracted `₹XXXCr` issue size, weekday names stripped from listing/allotment dates. Missing fields default to `"TBA"`.
- `compose_ipo_image()` — same three-image-type shape as `compose_image` (blog 640×480 + text, blog_inner 1920×490 no text, instagram 1080×1080 + text), but writes structured IPO fields at fixed zones rather than a headline/subtext/tag block.

### 6.3 `tempalte_selector.py` (filename typo is real, confirmed on disk)

- `select_template()` / `select_template_pair()` — deterministic MD5-hash-of-title fallback selection (no AI call).
- `select_template_pair_smart(category, blog_title, blog_content)` — **AI-based** selection: loads `templates/<category>/image_descriptions.json`, sends the model a numbered list of `outer/templateN.png: <description>` and asks it to pick the best-matching template number via strict JSON (`{"template_number": N}`). The model sees only text descriptions, never the actual template images. Falls back to the MD5 method on any missing-file/parse/API error.

### 6.4 `text_extractor.py`

`extract_image_text(blog_title, blog_content, category) -> {"headline": str, "subtext": str, "tag": str}` — one AI call, using only the first 300 characters of `blog_content` plus the title. `headline` max 6 words, `subtext` max 10 words, `tag` one all-caps word.

### 6.5 `validator.py`

`validate_template()`/`validate_all_templates()` — diagnostic-only; checks actual template file dimensions against `EXPECTED_SIZES` (`outer`: 640×480, `inner`: 1920×490, `instagram`: 1080×1080) and reports mismatches. **Never called from the live compositing path** — it's a manual/CI-style pre-flight check invoked only via its own `__main__` block, not integrated into `compose_image`/`compose_ipo_image`.

### 6.6 `ai_image_generator.py` — AI image path (used when `USE_AI_IMAGES=True`, non-IPO only)

`generate_ai_image()` makes **exactly 2 `gpt-image-1` API calls total** per article:
1. `size="1536x1024"` (landscape) → one image reused to derive both `blog_outer` (resized 640×480) and `blog_inner` (resized 1920×490) via `save_image_formats()`.
2. `size="1024x1024"` (square) → resized to `instagram` (1080×1080).

`build_image_prompt()` detects sentiment/topic keywords (bullish/bearish/dividend/IPO/RBI/gold/oil/IT/rupee) to vary emotion/scene/color-mood in the prompt text, and explicitly instructs "NO text overlay, NO watermarks, NO logos" — since text is composited separately by `compositor.py` for the template path, but for the AI-image path there is **no text overlay step at all** (the AI images ship with no headline/subtext).

---

## 7. Publishing — `mcp_agent.py` + `webflow_poster.py` + `related_links.py`

This is the live, production publishing path, called from `scheduler.py` after every pipeline run.

### 7.1 `mcp_agent.py::run_agent(entry)`

An OpenAI tool-calling loop with exactly **one live tool**: `post_single_blog(image_dir?)`. The blog payload is deliberately *not* passed as a tool argument — it's kept in a module-level global (`_PENDING_ENTRY`) to avoid the model carrying large JSON payloads (which the code notes previously caused truncation/control-character errors). System prompt instructs the model to call the tool exactly once and confirm title/item_id/slug. Loop: call model → if no tool calls, return final text; else execute each tool call, feed the result back, loop again — unbounded turn count.

A module-level `_ALREADY_POSTED` flag guards against the model calling `post_single_blog` twice in one run (observed in logs to create duplicate Webflow items) — but this guard is **in-memory and per-run only**; it does not persist across restarts and does not check Webflow itself for an existing item. A second tool, `post_blogs_from_file`, is wired into the dispatcher but **not included in the `TOOLS` list**, so it's unreachable — dead branch.

### 7.2 `webflow_poster.py::post_entry_as_draft(entry, image_dir)`

Live code starts at line 754 of 1,594 (everything above is a commented-out earlier version).

**API calls** (all synchronous `requests`, `BASE = "https://api.webflow.com/v2"` hardcoded): asset pre-sign → direct multipart POST to S3 (bucket from the pre-sign response) → create CMS item (`isDraft: False` set at creation time) → publish item. Only **WebP** images are uploaded (`entry["blog_image"]["webp"]`, `["blog_image_inner"]["webp"]`) — the `IMAGE_JPG_DIR` env var exists but is unused in this flow.

**No duplicate-detection against Webflow itself** — no check for an existing item/slug before creating a new one. The only guard anywhere in the pipeline is `mcp_agent.py`'s in-memory `_ALREADY_POSTED` (§7.1), and a narrower dedup inside the source-reference injection step (§7.2 HTML pipeline, item 10) that only prevents that one block from being inserted twice, not a real Webflow duplicate check.

**Content quality gate** (not a duplicate gate): `_validate_content()` checks for empty H2 sections, missing/placeholder Conclusion, or content < 300 chars — if it fails, the created item is left as a draft (`isDraft: True` in the *result*) instead of being published, but the CMS item is created either way.

**HTML transformation pipeline** applied to `Blog_Content` before posting, in order: strip `<h1>` → Title-Case headings → remove empty sections → prepend TLDR block → inject related-links block (via `related_links.py`, §7.3, wrapped in try/except) → strip any LLM-generated FAQ → inject a clean FAQ block built from `FAQ_Schema` before the Conclusion heading → clean stray labels inside Conclusion → append a hardcoded CTA link after Conclusion → inject a source-attribution block (skipped if already present) → style blockquotes/tables with inline CSS.

**Hardcoded values in this file** (not env vars): `ALL_BLOG_CATEGORY_ID`, author identity (`Nidhi Thakur` / her email — used as the CMS item's author field for every single post), the CTA URL/UTM params.

**Post-publish side effects**, each independently try/excepted so a failure doesn't break the reported success: `save_webflow_url()` writes the live URL back into `output.json` (matched by `Blog_Links`, atomic write via temp-file + `os.replace` — unlike `storage/save_output.py`, this one *is* atomic); `add_blog_to_graph()` registers the new blog into `keyword_graph.json` (§7.3).

### 7.3 `related_links.py` — confirmed live, not dead

`keyword_graph.json` is keyed by **normalized primary keyword** → a list of `{url, title, volume, secondary_kws}` entries sharing that keyword (O(1) group lookup, not URL-keyed as an earlier commented-out design was).

`_find_group_key()` (shared by `get_related_links()`, `add_blog_to_graph()`, and imported directly into `build_keyword_graph.py` "so both files can never drift out of sync"): exact match first, then a **containment-based fuzzy fallback** — the shorter string must be a substring of the longer one, be ≥10 chars, and be ≥55% of the longer string's length. The module's own comments explain plain `difflib`-style ratio matching was tried and rejected because it scored two *different* companies' similar-length keywords as more related than the same company's shorter/longer wording variants.

Relatedness ranking within a matched group: secondary-keyword set-overlap count if any candidate has overlap > 0, else fall back to sorting by search volume.

---

## 8. Shared utilities — `utils/`, `storage/`

| File | Status | Purpose |
|---|---|---|
| `utils/combined_filter.py` | **Live** | AI country+category filter, used in `pipeline.py` |
| `utils/timer.py` | **Live** | `@timed` decorator / `Timer` context manager, logs to `pipeline_timing.log` |
| `utils/date_filter.py` | **Live** | Same-day IST freshness filter with IPO/corporate exemption |
| `utils/mcp_tools.py` | **Live** (despite the generic name, this is the article-scraper module) | `fetch_and_clean()` scraper cascade (curl_cffi→trafilatura→newspaper3k→requests+BS4) used by `blog_generator.py` and `RSS/ndtv_profit.py`; also exposes an MCP server wrapper for standalone use |
| `utils/fuzzy_dedup.py` | Dead | `thefuzz`-based title dedup — not imported anywhere |
| `utils/regex_dedup.py` | Dead | Fingerprint-based title dedup — not imported anywhere |
| `utils/stack_manager.py` | Dead | `pipeline.py` has its own duplicate `save_stack`/`load_stack`/`pop_from_stack` functions rather than importing this |
| `utils/normalize_country.py` | Dead in live pipeline | Only used by the dead `mergeall.py` predecessor |
| `utils/parser.py` | Dead in live pipeline | Only referenced (and even there, commented out) in `mergeall.py` |
| `storage/save_output.py` | **Live** | `save_output()` — appends to `output.json`, dedups on lowercased `Blog_Title`. **Not atomic** (plain `open(..., "w")` — a crash mid-write can truncate/corrupt the file, per `REVIEW.md`) |

`Filter_news/finance_filter.py` — **confirmed dead**: only referenced by `mergeall.py`, and even there the call is commented out.

---

## 9. Maintenance / one-off scripts (root level)

None of these are wired into the live pipeline; they're run manually against `output/output.json` or `output/blogs_missing_keywords.json`.

**Keyword & SEO pipeline (unwired — see `SEO_TOOLS_INTEGRATION.md` for the intended design):**
- `keyword_researcher.py::get_keyword_volumes()` — live Google Ads Keyword Planner query (India geo), used by `blog_generator.py` and `enrich_missing_keywords.py`.
- `priAndsec_keywords.py::extract_keywords()` — LLM keyword extraction, used by `blog_generator.py`.
- `keyword_optimizer.py::optimize_keywords()` — Pass-2 LLM rewrite to weave keywords into title/headings/FAQ without touching facts. Docstring says it should be called from `pipeline.py`; **not currently imported there** — verify before assuming it runs.
- `build_keyword_graph.py` — CLI, rebuilds `keyword_graph.json` from `blogs_missing_keywords.json`, sharing matching logic with `related_links.py`. Idempotent (dedups by URL).
- `enrich_missing_keywords.py` — CLI (`--dry-run`), backfills volume data onto plain-string keywords. Takes a timestamped backup before writing, checkpoints every 10 blogs, rate-limits API calls.
- `add_keywords_to_blogs.py` — legacy batch keyword-tagging script with a hardcoded `START_DATE` cutoff and hardcoded `D:\Blogheading\...` paths; overwrites its output file with no backup.

**Webflow/data repair (one-time, explicitly documented as such in their own docstrings):**
- `backfill_webflow_urls.py` — matches already-published Webflow items back to local records by title (exact, then fuzzy ≥0.90 confidence flagged for manual review); atomic write, no backup (relies on git).
- `filter_blogs_with_url.py` — destructively drops any blog record without a confirmed `webflow_url`; **mandatory backup before writing** unless `--dry-run`.
- `migrate_output.py` — converts old flat image-path fields to the new outer/inner/webp schema; writes to a *separate* output file, non-destructive to the source.
- `fix_output.py` — strips literal `\n` artifacts from all string fields in `output.json`, **overwrites in place with no backup and no atomic write** — the riskiest script in the repo from a data-safety standpoint.
- `regenerate_images.py` — regenerates all three images for every blog in `output.json` via the template compositor path; also overwrites in place with no backup.
- `verify_images.py` — read-only: prints actual dimensions of the first blog's three images.
- `generate_image_descriptions.py` — one-time GPT-4o-vision script that generates `image_descriptions.json` per template category (skips already-described images, so safe to re-run incrementally).

**Legacy/superseded:**
- `mergeall.py` — the pipeline's predecessor to `pipeline.py`. **Confirmed dead** by repo-wide grep — nothing imports it; only runnable standalone.
- `filter_blogs_country.py`, `get_refresh_token.py` (Google OAuth token helper), `test_connection.py` (Google Ads client sanity check), `dynamic_input_country.py` (CLI arg parser, unclear current caller).

**Ad-hoc "test" scripts (root level `test_*.py`) — not a test suite, no assertions, no runner config:**
- `test_debug.py` — dumps the last 100 blogs from `output.json`.
- `test_debug2.py` — a **hardcoded one-time repair** of a specific already-published Webflow item (fixes nested `<li><li>` and republishes it live). Contains **a Webflow bearer token committed in plaintext in the source** — this is a live secret in git history; see the security note in §11.
- `test_ipo_blog.py` — exercises the full IPO scrape→validate→generate path for one hardcoded test company, dumps result to a local JSON file.
- `test_keywords.py` — manual Google Ads API connectivity/shape check.
- `test_title.py` — smoke-tests `generate_blog()` title/meta quality on one hardcoded synthetic item.

---

## 10. Configuration

| File/var | Required for | Notes |
|---|---|---|
| `config.py` (gitignored) | Everything that calls `client`/`MODEL` | Must exist locally/on server before running anything; wraps `OPENAI_API_KEY` + model name |
| `.env` (gitignored) | `OPENAI_API_KEY`, `FINNHUB_API_KEY`, others | |
| `google-ads.yaml` (gitignored) | Google Ads Keyword Planner calls | Obtained via `get_refresh_token.py`'s OAuth flow |
| `USE_AI_IMAGES` | `pipeline.py` + `app.py` (two separate hardcoded copies) | Must be manually kept in sync; switches AI-generated vs. template images and which output JSON file is read |
| `RSS/ipo.py::TEST_MODE` | IPO scraper | Must be `False` before deploying — `True` uses a fixed test company instead of the live feed |
| `docker-compose.yml` env vars | scheduler container | `WEBFLOW_API_TOKEN`, `SITE_ID`, `COLLECTION_ID`, `IMAGE_JPG_DIR` |

---

## 11. Known issues worth flagging (not exhaustive — see `REVIEW.md` for the full audit)

- **Secrets committed to git in plaintext**: `docker-compose.yml` has a live `WEBFLOW_API_TOKEN` hardcoded (not read from `.env` there, despite `.env` being gitignored elsewhere); `test_debug2.py` has a second bearer token literal in source. Both should be rotated and moved to environment variables / secrets management.
- Font-file casing mismatches (`compositor.py`, `ipo_compositor.py` reference PascalCase filenames; disk has lowercase) are silently masked on Windows and will silently degrade font rendering on Linux production containers.
- `storage/save_output.py`'s non-atomic write can corrupt `output.json` (the pipeline's only persistent store + dedup index) on a mid-write crash.
- Several "documented" features (mandatory internal links, keyword-rich H2s) are half-reverted — the code and `Blogheading docs·md` actively disagree, and per `REVIEW.md` this needs an owner decision, not a silent "fix."

---

## 12. Where to look next

- Adding a new RSS source → follow the common-pattern shape in §4.3, register it in `pipeline.py`'s source list and `PRIORITY_SOURCES`/`CORPORATE_SOURCES`/`NEWS_SOURCES` (per `Blogheading docs·md` §5).
- Changing SEO/prompt rules → `AI_GEN/blog_generator.py`'s `generate_blog()`/`generate_ipo_blog()` prompts, plus whichever post-processor in §5.1's table enforces the rule mechanically.
- Changing what gets posted to Webflow / how → `webflow_poster.py::post_entry_as_draft()`, §7.2's HTML pipeline list.
- Changing image look → `content_engine/image_module/compositor.py` (non-IPO) or `ipo_compositor.py` (IPO), §6.1–6.2.
