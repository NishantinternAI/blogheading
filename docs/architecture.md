# Blogheading — Automated Financial Blog Pipeline

> Automated pipeline that generates SEO-optimised blogs, Instagram captions,
> push notifications, and images from Indian financial news every 15 minutes.
> Runs 24/7 on Docker.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architecture](#2-architecture)
3. [File Structure](#3-file-structure)
4. [RSS Sources](#4-rss-sources)
5. [Three-Stack Priority System](#5-three-stack-priority-system)
6. [Posting Pattern](#6-posting-pattern)
7. [IPO Pipeline](#7-ipo-pipeline)
8. [Image Generation](#8-image-generation)
9. [Article Selection Logic](#9-article-selection-logic)
10. [AI Filter Bypass](#10-ai-filter-bypass)
11. [Blog Generator — SEO Engine](#11-blog-generator--seo-engine)
12. [Post-Processors — Guaranteed Fixes](#12-post-processors--guaranteed-fixes)
13. [Streamlit Dashboard — app.py](#13-streamlit-dashboard--apppy)
14. [Configuration Flags](#14-configuration-flags)
15. [Output Format](#15-output-format)
16. [Deployment](#16-deployment)
17. [Testing](#17-testing)

---

## 1. Project Overview

```
Every 15 minutes:
  Fetch financial news from 6 sources
  Filter → Deduplicate → Classify → Save to 3 stacks
  Pop one article (based on POSTING_PATTERN)
  Generate SEO-optimised blog + push notification + Instagram caption (AI)
  Post-process blog HTML (guaranteed SEO fixes regardless of AI output)
  Generate 3 images (IPO template OR AI/smart template)
  Save to output.json / testing_webp_output.json
```

**Tech Stack:**

| Layer | Technology |
|---|---|
| Language | Python 3.11 |
| Scheduler | APScheduler (cron every 15 min) |
| Containerisation | Docker + docker-compose |
| AI (blog/captions) | OpenAI GPT |
| AI (images) | OpenAI gpt-image-1 |
| Image processing | Pillow (PIL) |
| Web scraping | BeautifulSoup4, requests |
| RSS parsing | feedparser |
| Server | Ubuntu 24, Nginx reverse proxy |

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                       scheduler.py                          │
│                  APScheduler every 5 min                    │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                   pipeline.py                         │
│                     run_pipeline()                          │
│                                                             │
│  Step 1 → Load 3 stacks from disk                           │
│  Step 2 → Fetch 6 sources if stacks empty                   │
│           (IPO bypass AI filter)                            │
│  Step 3 → decide_pop_type() via POSTING_PATTERN             │
│  Step 4 → _pop_article_from_stack()                         │
│           IPO = oldest-first, others = random               │
│  Step 5 → Duplicate check vs output.json                    │
│  Step 6 → generate_blog() + notify() + instagram() [AI]     │
│           + post-processors run automatically               │
│  Step 7 → Generate images                                   │
│           IPO article → ipo_compositor.py (always)          │
│           non-IPO + AI=True → gpt-image-1                   │
│           non-IPO + AI=False → compositor.py template       │
│  Step 8 → Save to output.json                               │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. File Structure

```
Blogheading/
│
├── scheduler.py                         ← APScheduler entry point
├── pipeline.py                   ← Main pipeline (run_pipeline)
├── app.py                               ← Streamlit dashboard
│
├── sources/
│   ├── ipo.py                           ← NSE IPO + Chittorgarh scraper
│   │                                       + InvestorGain + Moneycontrol fallback
│   ├── zerodha.py                       ← Zerodha Pulse RSS
│   ├── cnbc.py                          ← CNBC TV18 RSS
│   ├── paisa.py                         ← 5Paisa RSS
│   ├── livemint.py                      ← Livemint RSS
│   └── fetch_nse_corporate.py           ← NSE corporate actions
│
├── content_engine/
│   ├── image_module/
│   │   ├── compositor.py                ← Normal image generator
│   │   ├── ipo_compositor.py            ← IPO Alert image generator
│   │   ├── text_extractor.py            ← AI text extraction
│   │   ├── tempalte_selector.py         ← Smart template selection
│   │   └── ai_image_generator.py        ← OpenAI gpt-image-1
│   └── templates/
│       ├── ipo_alert.png                ← IPO Alert template (1080×1350)
│       └── ipo_inner.png                ← IPO Inner template (1920×490)
│
├── generators/
│   ├── blog_generator.py                ← AI blog writer + SEO post-processors
│   ├── notify_generator.py              ← AI notification writer
│   └── generate_instagram_caption.py    ← AI Instagram caption
│
├── utils/
│   ├── combined_filter.py               ← Country + category AI filter
│   └── timer.py                         ← @timed decorator + Timer context
│
├── storage/
│   └── save_output.py                   ← Saves article to output.json
│
├── output/
│   ├── output.json                      ← Published articles store
│   ├── testing_webp_output.json         ← Test output (USE_AI_IMAGES=True)
│   ├── stack_priority.json              ← IPO articles queue
│   ├── stack_news.json                  ← News articles queue
│   ├── stack_corporate.json             ← Corporate actions queue
│   ├── pattern_index.json               ← Posting pattern position
│   └── stack_timestamp.json             ← Last stack build time
│
└── output_images/
    ├── jpg_images/                      ← All JPG outputs
    └── webp_images/                     ← All WebP outputs
```

---

## 4. RSS Sources

| Source | Stack | Articles/Fetch | Notes |
|---|---|---|---|
| NSE IPO (+ Chittorgarh) | priority | up to 6 | IPO filings only |
| NSE Corporate | corporate | up to 6 | Ex-dates, dividends |
| Zerodha Pulse | news | up to 6 | Also used as fallback |
| CNBC TV18 | news | up to 6 | |
| 5Paisa | news | up to 6 | |
| Livemint | news | up to 6 | |

**Zerodha fallback:** if all 6 sources return no fresh articles after dedup,
one random Zerodha article is picked and published immediately (skips stacks).

---

## 5. Three-Stack Priority System

Articles are classified into 3 stacks by `source` field only:

```python
PRIORITY_SOURCES  = ["nse_ipo", "google_trends", "market_summary"]
CORPORATE_SOURCES = ["nse_corporate"]
NEWS_SOURCES      = ["zerodha", "cnbc", "5paisa", "livemint"]
```

| Stack File | Sources | Image Method |
|---|---|---|
| `stack_priority.json` | `nse_ipo`, `market_summary` | See notes |
| `stack_news.json` | zerodha, cnbc, 5paisa, livemint | AI or template |
| `stack_corporate.json` | `nse_corporate` | AI or template |

**Priority Stack Image Methods:**
- `nse_ipo` articles: `ipo_compositor.py` always (template-based)
- `market_summary` articles: AI or template (per `USE_AI_IMAGES` flag, same as news/corporate)

**Market Summary Articles**

`market_summary` articles route to the priority stack and follow the `POSTING_PATTERN`. Unlike IPO articles, they use the standard image generation path (AI-generated or smart template) rather than the IPO compositor. The blog generator uses a dedicated `generate_market_summary_blog()` prompt function (in `generators/blog_generator.py`) rather than the generic `generate_blog()`. Data comes from `sources/market_summary.py`, built from NSE's public end-of-day archive CSVs, providing Nifty 50 and Bank Nifty pivot support/resistance levels, top gainers/losers, and market-wide statistics (PCR ratio).

---

## 6. Posting Pattern

Controls which stack is used each pipeline run:

```python
POSTING_PATTERN = ["priority", "news", "priority", "corporate"]
```

Current position is tracked in `output/pattern_index.json`.

**Example with all stacks full:**

```
Run 1 → priority  (IPO article)
Run 2 → news
Run 3 → priority  (IPO article)
Run 4 → corporate
Run 5 → priority  (loops back)
```

If a stack is empty, that position is skipped and the next non-empty stack
is used. Pattern index still advances.

---

## 7. IPO Pipeline

### 7.1 Flow

```
NSE RSS XML feed
      ↓
Filter entries containing "for its ipo"
Skip: CP-NI, NCD, rights issue, buyback, open offer
      ↓
Detect doc type: PROSP / RHP / DRHP
      ↓
_scrape_ipo_details() — waterfall:
  1. Chittorgarh  (primary — best structured data)
  2. InvestorGain (fallback 1)
  3. Moneycontrol (fallback 2)
  4. Stale cache  (in-memory, if all sources fail)
      ↓
_validate_ipo_article()
  ERROR: open_date has 2+ month names → block
  WARNING: price_band missing → allow
      ↓
Add to priority stack with _stack_index
```
**NOTE**-
"If we don't know the price AND we don't know the open date — don't make a blog for this company."

### 7.2 Data Source Waterfall

```python
scrapers = [
    ("Chittorgarh",  _scrape_chittorgarh),   # primary
    ("InvestorGain", _scrape_investorgain),   # fallback 1
    ("Moneycontrol", _scrape_moneycontrol),   # fallback 2
]
# Stale cache used if all 3 fail
```

### 7.3 Cache

- **Key:** `_normalize_company_key()` — strips "Limited", "Ltd", "IPO", "India"
- **TTL:** 6 hours
- **Stale cache:** returned if all sources 


- **What Is a Cache?**

Cache = temporary memory that saves data
so you don't have to fetch it again.

Without cache:
  Every time IPO article runs → scrape Chittorgarh
  = 1 HTTP request per article per pipeline run
  = 96 requests per day to Chittorgarh's website
  = Chittorgarh blocks your IP (too many requests)
  = All IPO data stops working ❌

With cache:
  First time → scrape Chittorgarh → save in memory
  Next 5 runs → read from memory (no HTTP request)
  = Chittorgarh sees maybe 10-15 requests per day
  = No blocking, no rate limiting 

**The Problem It Solves**
NSE RSS feed might say:    "Hexagon Nutrition Limited"
Chittorgarh might say:     "Hexagon Nutrition"
InvestorGain might say:    "Hexagon Nutrition India"
Your cache key might be:   "Hexagon Nutrition IPO"

Without normalization:
  All 4 = different cache keys
  = 4 separate scraping calls
  = same company scraped 4 times
  = wasted API calls + slower pipeline ❌

With normalization:
  All 4 → strip "Limited", "Ltd", "IPO", "India"
  All 4 → become "hexagon nutrition" (lowercase)
  = same cache key
  = scraped once, cached, reused 4 times ✅

**What TTL Means**
TTL = Time To Live
= how long cached data is considered "fresh"
= after 6 hours, cache expires and data is re-fetched

Think of it like milk in the fridge:
  Fresh milk (within 6 hours) = use it directly ✅
  Old milk (past 6 hours)     = throw it out, buy new ❌

**Why 6 Hours Specifically**
IPO data changes like this:

  Day 1 (DRHP filed):
    open_date   = "To be announced"
    price_band  = "To be announced"
    lot_size    = "To be announced"

  Day 3 (RHP filed):
    open_date   = "29 May 2026"      ← NEW
    price_band  = "₹70 per share"    ← NEW
    lot_size    = "2,000 shares"     ← NEW

  Day 5 (IPO opens):
    gmp         = "₹12 premium"      ← NEW
    subscribed  = "2.3x"             ← NEW

If TTL = 1 hour:
  Too many Chittorgarh requests
  Risk of IP blocking
  Pipeline slows down

If TTL = 24 hours:
  IPO data changes during the day
  Your blog shows outdated data (wrong price/dates)
  Investors get wrong information ❌

If TTL = 6 hours:
  Refreshes data ~4 times per day
  Catches most important updates
  Not too many requests
  = Right balance ✅
### 7.4 Date Parser

Handles two Chittorgarh formats:

```
Format A: "5 to 9 Jun, 2026"
  → open_date = "5 Jun, 2026"   close_date = "9 Jun, 2026"

Format B: "29 May to 2 Jun, 2026"   (cross-month)
  → open_date = "29 May, 2026"  close_date = "2 Jun, 2026"
```

**Validation:** `open_date` must contain exactly 1 month name + a 4-digit year.
If 2 month names found → date parser bug → article blocked.

### 7.5 `_stack_index`

Added **only to IPO articles** when building the stack:

```python
ipo_counter = 0
for article in fresh:
    if article.get("source") == "nse_ipo":
        article["_stack_index"] = ipo_counter   # 0, 1, 2...
        ipo_counter += 1
```

### 7.6 IPO Fields Scraped

`open_date` · `close_date` · `listing_date` · `price_band` · `lot_size` ·
`issue_size` · `face_value` · `exchange` · `issue_type` · `sale_type` ·
`gmp` · `market_cap` · `business` · `financials` · `data_source`

### 7.7 TEST_MODE

```python
TEST_MODE    = False             # set False before push to server
TEST_COMPANY = "Aureate Tradde"
```

Available test companies: Aureate Tradde, Liotech Industries, Merritronix,
Hexagon Nutrition, SMR Jewels, Harikanta Overseas, Rajnandini Fashion India,
Yaashvi Jewellers, Vegorama Punjabi Angithi.

---

## 8. Image Generation

### 8.1 Decision Logic (STEP 7)

```
Article popped
      ↓
Is it IPO? (priority + source = nse_ipo)
      ↓
   YES → ipo_compositor.py ALWAYS     ← USE_AI_IMAGES ignored for IPO
   NO  → check USE_AI_IMAGES flag
           True  → gpt-image-1 (OpenAI)
           False → compositor.py (smart template)
```

### 8.2 IPO Images — `ipo_compositor.py`

| Image | Template | Size | Text Written |
|---|---|---|---|
| Blog outer | `ipo_alert.png` (1080×1350) | 640×480 | Company name + 6 zone values |
| Blog inner | `ipo_inner.png` (1920×490) | 1920×490 (direct) | None |
| Instagram | `ipo_alert.png` (1080×1350) | 1080×1080 (center crop) | Company name + 6 zone values |

**Zone positions (% of image):**

| Field | x% | y% | Format |
|---|---|---|---|
| Date | 45.3% | 44.1% | `"29-2"` / `"Jun '26"` (2 lines) |
| Price | 79.7% | 44.1% | `"₹42 to ₹45"` / `"Per share"` (2 lines) |
| Lot | 45.3% | 60.4% | `"333 Shares"` (1 line) |
| Size | 79.7% | 60.4% | `"₹139Cr"` (1 line) |
| Allotment | 45.3% | 78.1% | `"9 JUN '26"` (uppercase) |
| Listing | 79.7% | 78.1% | `"JUN 12 '26"` (uppercase) |

### 8.3 Non-IPO AI Images

```
2 API calls per article:
  Call 1: size=1536×1024 → blog_outer (640×480) + blog_inner (1920×490)
  Call 2: size=1024×1024 → instagram (1080×1080)
Total: 6 files, 2 API calls
```

### 8.4 Non-IPO Template Images

- `extract_image_text()` → AI extracts `{headline, subtext, tag}` (1 API call)
- `select_template_pair_smart()` → AI picks best template (1 API call)[According to description]

---

## 9. Article Selection Logic

| Stack | Has IPO articles? | Method |
|---|---|---|
| priority | YES | Sorted by `published` + `_stack_index` → oldest first |
| priority | NO | `random.choice()` |
| news | — | `random.choice()` |
| corporate | — | `random.choice()` |

---

## 10. AI Filter Bypass

IPO articles (`source=nse_ipo`) and market summary articles
(`source=market_summary`) both skip the AI country/category filter:

```python
ipo_articles             = [a for a in all_data if a.get("source") == "nse_ipo"]
market_summary_articles  = [a for a in all_data if a.get("source") == "market_summary"]
other_articles           = [a for a in all_data if a.get("source") not in ("nse_ipo", "market_summary")]
filtered_other           = filter_by_country_and_category(other_articles, ...)
filtered_data            = ipo_articles + market_summary_articles + filtered_other
```

**Why bypass is needed:** IPO `Blog_Content` is structured form data, not prose.
The AI filter misclassifies it as non-finance and removes all IPO articles,
leaving the priority stack permanently empty. `market_summary`'s `Blog_Content`
is the same kind of structured field-by-field brief (pivot levels, gainers/
losers table data) rather than narrative prose, so it carries the identical
misclassification risk and gets the same bypass.

---

## 11. Blog Generator — SEO Engine

`generators/blog_generator.py` — major SEO improvements added.

### 11.1 Article Type Detection

The AI detects article type FIRST before generating any content:

| Type | Signals | H2 Structure |
|---|---|---|
| A — IPO | ipo, lot size, allotment, price band | 4 fixed H2s |
| B — Gold/Silver | gold, silver, bullion, mcx | 3 dynamic H2s |
| C — Stock | company + shares/stock/results/dividend | 3 dynamic H2s |
| D — RBI | rbi, repo rate, monetary policy | 3 dynamic H2s |
| E — Market | sensex, nifty, market, rally | 3 dynamic H2s |
| F — General | none of above | 3 dynamic H2s |

### 11.2 H2 Structure Rules

**Every H2 must contain the PRIMARY KEYWORD.**
Generic H2s are banned: `News Context`, `Portfolio Focus`, `Risks and Cautions`.

**IPO articles — 4 fixed H2s (consistent across all IPO pages):**
```
H2-1: [Company] IPO – Key Details and Dates   + DATA TABLE
H2-2: [Company] IPO GMP and Market Sentiment
H2-3: Should You Apply For [Company] IPO?
H2-4: Risks of Investing in [Company] IPO
```

**All other articles — 3 dynamic H2s (text changes per article):**
```
H2-1: [Topic + specific event] – Key Details
H2-2: [Topic + specific event] – Impact on Your Money
H2-3: Key Risks of [specific action from this news]
```

### 11.3 Dynamic H3 Rule

H3 tags must be **specific to the actual article** — never generic.

**Only one H3 is consistent across all articles:**
```
"What SIP, Lumpsum and Traders Should Do Now"
```

All other H3s must contain the actual company name, number, or event:
```
✅ "Why Gold Fell 1% – US-Iran Tensions Explained"
✅ "How Rs 33,000 Cr FPI Exit Affects Your Holdings"
✅ "Which IT Stocks Gain From RBI Rate Cut?"
❌ "What This Means For Your Portfolio"
❌ "Sectors To Watch – Priority Order"
```

### 11.4 Data Table Rule

**ONLY IPO articles (TYPE A) get a data table.**
All other types (Gold, Stock, RBI, Market) — NO table.

**Why:**
- IPO data (price, dates, lot size) is fixed after SEBI approval → table stays accurate
- Gold/stock prices change every minute → table goes stale
- IPO table is eligible for Google Featured Snippet (position 0)

**IPO table format:**
```html
<table>
  <thead><tr><th>Detail</th><th>Information</th></tr></thead>
  <tbody>
    <tr><td>IPO Open Date</td>      <td>29 May 2026</td></tr>
    <tr><td>IPO Close Date</td>     <td>2 Jun 2026</td></tr>
    <tr><td>Price / Price Band</td> <td>₹70 per share</td></tr>
    <tr><td>Lot Size</td>           <td>2,000 Shares</td></tr>
    <tr><td>Minimum Investment</td> <td>₹1,40,000</td></tr>
    <tr><td>Issue Size</td>         <td>₹27 Crore</td></tr>
    <tr><td>Listing Exchange</td>   <td>BSE SME</td></tr>
    <tr><td>Listing Date</td>       <td>5 Jun 2026</td></tr>
  </tbody>
</table>
```

### 11.5 Internal Links Rule

**Corrected 2026-07-24** — this is not implemented in the LLM prompt or in
`blog_generator.py`'s post-processing at all (that approach — `fix_duplicate_links()`
/ `fix_links_before_faq()` — no longer exists in the code; review.md #15
tracked this as an open half-reverted feature and is now resolved as
"implemented, just via a different mechanism").

Internal ("related") links are instead added at **publish time** in
`publishing/webflow_poster.py`, sourced from `keywords/related_links.py`:
up to `MAX_RELATED_LINKS` (3) links to other blogs sharing the same
primary keyword (or a fuzzy-matched one), ranked by secondary-keyword
overlap then search volume, injected as an `<h2>Related Reads</h2>`
block immediately **before the Conclusion** heading (not before FAQ —
FAQ is handled separately, see §13.5). The link graph lives in
`output/keyword_graph.json`, keyed by primary keyword, and is updated
after each successful publish via `add_blog_to_graph()`.

### 11.6 Title Rules

Every `Blog_Title` and `Meta_Title` must have all 3:
1. ONE NUMBER (₹ amount, %, crore, points, date)
2. ONE "YOU" word (You, Your, Are You, Should You)
3. ONE QUESTION (ends with ?)

**Banned words in titles:**
`Ex-Date` → Buy Before [date] | `PAT` → Profit | `YoY` → vs Last Year |
`Basis Points` → Interest Rate | `Volatile` → Up and Down |
`Correction` → Market Fall | `Geopolitical` → War / Conflict

### 11.7 TLDR Keyword Rule

Each TLDR bullet must contain the PRIMARY KEYWORD:

```
✅ "Gold price fell 1% today on MCX to ₹74,000 per 10g"
✅ "Gold price fall reduces portfolio hedge value"
❌ "What happened – prices moved today"
❌ "Direct impact on investor portfolio"
```

### 11.8 Anti-Duplication Rules

Before output, the AI verifies:
- Internal links count = 1
- Swastika paragraph count = 1
- SIP/Lumpsum section count = 1
- Sector priority list count = 1
- Risk section count = 1
- No repeated H2 topics

### 11.9 Other Formatting Rules

- Word count: 900-1200 (increased from 600-800)
- FAQ questions: `<h4>` tags only — never `<h3>`
- FAQ h2 must contain main keyword
- En dash (`–`) only — never em dash (`—`)
- English only — no foreign language characters
- No h2 above TLDR bullet list
- Swastika paragraph: exactly once, inside second H2 only

---

## 12. Post-Processors — Guaranteed Fixes

Post-processors run in Python **after** the AI generates the blog.
They fix issues regardless of whether the AI follows prompt rules.

All processors are in `generators/blog_generator.py` and called via `fix_all_fields()`.

| Function | What It Fixes |
|---|---|
| `fix_em_dash()` | Replaces `—` with `–` everywhere |
| `fix_tldr_h2()` | Removes `<h2>TLDR</h2>` tag |
| `fix_faq_tags()` | Converts `<h3>` → `<h4>` inside FAQ section only |
| `fix_faq_h2_keyword()` | Adds keyword to bare FAQ h2 |
| `fix_placeholder_h3()` | Removes/replaces generic placeholder h3 text |
| `fix_duplicate_swastika()` | Keeps only the first Swastika paragraph |
| `fix_table_na()` | Replaces N/A cells with "To be announced" |
| `fix_remove_non_ipo_table()` | Removes table from non-IPO articles |
| `fix_extra_ipo_h2()` | Removes rogue h2 sections from IPO articles |
| `fix_garbage_characters()` | Removes non-English characters (e.g. Chinese) |

### Post-Processor Call Order

```python
def fix_all_fields(data, source=""):
    # Applied to Blog_Content:
    value = fix_tldr_h2(value)
    value = fix_faq_tags(value)
    value = fix_faq_h2_keyword(value, blog_title)
    value = fix_placeholder_h3(value)
    value = fix_duplicate_links(value)
    value = fix_links_before_faq(value)
    value = fix_duplicate_swastika(value)
    value = fix_table_na(value)
    value = fix_remove_non_ipo_table(value, source)
    value = fix_extra_ipo_h2(value, source)
    # Applied to all string fields:
    value = fix_em_dash(value)
    value = fix_garbage_characters(value)
```

---

## 13. Streamlit Dashboard — app.py

### 13.1 Blog Content Assembly

The dashboard assembles final blog HTML from multiple JSON fields:

```
output.json fields → assembled blog HTML

blog.Blog_Title     → <h1>title</h1>
blog.TLDR           → <h2>Key Takeaways</h2><ul>...</ul>
blog.Blog_Content   → cleaned HTML (h1/TLDR/FAQ/Conclusion stripped)
blog.FAQ_Schema     → <h2>FAQ</h2>
                      <h4>question?</h4><p>answer</p>  (h4 not h3)
blog.Conclusion     → <h2>Conclusion</h2><p>...</p>
```

### 13.2 Key Functions

| Function | Purpose |
|---|---|
| `clean_blog_html(html)` | Strips h1/TLDR/FAQ/Conclusion from Blog_Content (re-added cleanly) |
| `parse_date(item)` | Handles RFC2822, ISO, NSE date formats for correct sorting |

### 13.3 clean_blog_html() — What Gets Stripped

```python
REMOVE_PREFIXES = (
    "tldr",                      # strips any h2 TLDR inside Blog_Content
    "key takeaways",             # strips any Key Takeaways h2
    "frequently asked questions",
    "faq",
    "conclusion",
    "cta",
)
```

Also strips:
- First `<h1>` (re-added from `Blog_Title`)
- First `<ul>` (TLDR list — re-added from `TLDR` JSON field)
- All `<h4>` FAQ questions and their `<p>` answers (re-added from `FAQ_Schema`)
- CTA links to swastika.co.in

**Allowed tags (kept in Blog_Content):**
`h1-h4, p, ul, ol, li, strong, em, br, a, span, table, thead, tbody, tr, th, td`

Note: `table` tags are kept so IPO data tables display correctly.

### 13.4 TLDR H2 — Bare Heading

```python
blog_combined += "<h2>Key Takeaways</h2>\n<ul>\n"
```

No per-article keyword is added to this heading — this was a keyword-rich
`<h2>Key Takeaways – {keyword}</h2>` at one point, backed by an
`extract_faq_keyword()` helper, but that call was dropped and the
now-dead helper removed (2026-07-24; owner decision, see
`docs/review.md` #5/#16). Heading is plain `<h2>Key Takeaways</h2>`.

### 13.5 FAQ H2 and H4

```python
blog_combined += "<h2>FAQ</h2>\n"
blog_combined += f"<h4>{q}</h4>\n<p>{a}</p>\n\n"
```

Same as above — no keyword suffix on the FAQ heading. Questions render
as `<h4>` (not `<h3>`).

### 13.6 Notification Handling

Handles both string and dict formats:

```python
notify = item.get("notify", {})
notify_text = (notify if isinstance(notify, str)
               else notify.get("blog_notify", "") if isinstance(notify, dict)
               else "")
```

### 13.7 Instagram Handling

Handles both string and dict formats:

```python
insta = item.get("instagram_notify", {})
caption  = insta if isinstance(insta, str) else insta.get("instagram_caption", "")
hashtags = "" if isinstance(insta, str) else insta.get("hashtags", "")
```

---

## 14. Configuration Flags

### `pipeline.py`

```python
USE_AI_IMAGES = False   # True → OpenAI gpt-image-1 for non-IPO
                        # False → compositor.py smart templates

POSTING_PATTERN = ["priority", "news", "priority", "corporate"]

PRIORITY_SOURCES  = ["nse_ipo"]
CORPORATE_SOURCES = ["nse_corporate"]
NEWS_SOURCES      = ["zerodha", "cnbc", "5paisa", "livemint"]
```

### `sources/ipo.py`

```python
TEST_MODE       = True              # False = real NSE feed
TEST_COMPANY    = "Aureate Tradde"
CACHE_TTL_HOURS = 6
```

### `app.py`

```python
USE_AI_IMAGES = False   # Must match pipeline.py
# True  → reads testing_webp_output.json
# False → reads output.json
```

---

## 15. Output Format

Each published article in `output/output.json`:

```json
{
  "Blog_Title":       "Aureate Tradde IPO Opens 29 May, 2026 — Apply or Avoid?",
  "Blog_Content":     "Company: Aureate Tradde\nOpen Date: 29 May...",
  "source":           "nse_ipo",
  "source_type":      "priority",
  "data_source":      "Chittorgarh",
  "_stack_index":     0,
  "open_date":        "29 May, 2026",
  "close_date":       "2 Jun, 2026",
  "listing_date":     "Jun 5, 2026",
  "price_band":       "₹70 per share",
  "lot_size":         "2,000 Shares",
  "issue_size":       "₹27Cr",
  "blog": {
    "Meta_Title":      "Aureate Tradde IPO at ₹70 – Should You Apply?",
    "Meta_Description":"...",
    "TLDR":            ["point1", "point2", "point3", "point4"],
    "Blog_Title":      "Aureate Tradde IPO at ₹70 – Should You Apply?",
    "Blog_Content":    "<h1>...</h1><h2>...</h2>...",
    "Investor_Impact": {"primary_sector":"...", "action":"Wait", ...},
    "Action_Points":   ["action1", "action2", "action3"],
    "FAQ_Schema":      {"@context":"https://schema.org", "@type":"FAQPage", ...},
    "Conclusion":      "...",
    "CTA":             "https://trade.swastika.co.in/"
  },
  "notify":           {"blog_notify": "Push notification text"},
  "instagram_notify": {"instagram_caption": "...", "hashtags": "#Nifty ..."},
  "blog_image":       {"jpg": "output_images/jpg_images/blog_Aureate.jpg", "webp": "..."},
  "blog_image_inner": {"jpg": "output_images/jpg_images/blog_inner_Aureate.jpg", "webp": "..."},
  "instagram_image":  {"jpg": "output_images/jpg_images/insta_Aureate.jpg", "webp": "..."},
  "Run_Timestamp":    "2026-05-29 11:04:54"
}
```

---

## 16. Deployment

### Docker Commands

```bash
# Build and start both containers
docker compose up --build -d

# Start/stop individual containers
docker start blogheading-scheduler-1
docker start blogheading-streamlit-1
docker stop blogheading-scheduler-1

# Live logs
docker logs -f blogheading-scheduler-1
docker logs --tail 100 blogheading-scheduler-1

# Status
docker ps
```

### Deploy New Code

```bash
# Local machine
git add .
git commit -m "your message"
git push origin main

# Server
cd ~/Content\ Engine/Blogheading
docker compose down
git pull origin main
docker compose up --build -d
docker logs -f blogheading-scheduler-1
```

### `docker-compose.yml`

```yaml
version: "3.8"
services:
  scheduler:
    build: .
    container_name: blogheading-scheduler-1
    restart: always
    volumes:
      - ./output:/app/output
      - ./output_images:/app/output_images
    env_file: .env
    command: python scheduler.py

  streamlit:
    build: .
    container_name: blogheading-streamlit-1
    restart: always
    ports:
      - "8501:8501"
    volumes:
      - ./output:/app/output
      - ./output_images:/app/output_images
    env_file: .env
    command: streamlit run app.py --server.port 8501 --server.address 0.0.0.0
```

---

## 17. Testing

### Test Full Pipeline (IPO article)

```bash
# 1. Clear stacks + reset pattern
python -c "
import json
for f in ['stack_priority','stack_news','stack_corporate']:
    json.dump([], open(f'output/{f}.json','w'))
json.dump({'current_index':0,'last_type':'news'}, open('output/pattern_index.json','w'))
print('Reset done')
"

# 2. Run pipeline
python -c "
from pipeline import run_pipeline
results = run_pipeline()
if results:
    r = results[0]
    print('source_type :', r.get('source_type'))
    print('data_source :', r.get('data_source'))
    print('blog_image  :', r.get('blog_image',{}).get('jpg',''))
"
```

### Test IPO Scraper Only

```bash
python sources/ipo.py
```

### Test IPO Compositor Only

```bash
python content_engine/image_module/ipo_compositor.py
```

### Test Post-Processors Only

```bash
python -c "
from generators.blog_generator import fix_all_fields
sample = {
    'Blog_Title': 'Test IPO at Rs 70 – Should You Apply?',
    'Blog_Content': '<h2>TLDR</h2><ul><li>test</li></ul><h2>FAQ</h2><h3>Q1?</h3><p>A1</p>'
}
result = fix_all_fields(sample, source='nse_ipo')
print(result['Blog_Content'][:300])
"
```

### Check Stack State

```bash
python -c "
import json
for f in ['priority','news','corporate']:
    try:
        data = json.load(open(f'output/stack_{f}.json'))
        print(f'{f}: {len(data)} articles')
    except: print(f'{f}: empty')
"
```

### Verify Post-Processors Running

Add temporarily to `fix_faq_tags()`:
```python
def fix_faq_tags(html):
    print("[POST-PROCESSOR] fix_faq_tags running")
    ...
```
Then check: `docker logs -f blogheading-scheduler-1`

---







## Quick Reference

### Files to update before production push

```
sources/ipo.py              TEST_MODE = False
pipeline.py      USE_AI_IMAGES = True/False (your choice)
app.py                  USE_AI_IMAGES = True/False (must match above)
```

### Template files required on server

```
content_engine/templates/ipo_alert.png   (1080×1350)
content_engine/templates/ipo_inner.png   (1920×490)
```

### Key logs to watch

```
[STACK BUILD] Priority:1 | News:16 | Corporate:2
[POP] IPO → oldest-first (published + _stack_index)
[IMAGE] IPO article → ipo_compositor.py (always template)
[DONE] [PRIORITY] Saved → output/output.json
```

### SEO Score Checklist (per blog)

| Check | Tool |
|---|---|
| H2 has keyword | View page source |
| FAQ schema valid | search.google.com/test/rich-results |
| Page speed | pagespeed.web.dev |
| On-page SEO score | ahrefs.com/seo-checker |
| Index status | search.google.com/search-console |

---

## Changelog

### May–June 2026

**blog_generator.py**
- Added article type detection (TYPE A–F) before H2 generation
- Added dynamic H2 structure — each type gets keyword-rich H2s
- Added dynamic H3 rule — specific to actual news, not generic
- IPO-only data table rule — other article types get no table
- Added mandatory internal links section (3 links, before FAQ) — superseded
  2026-07-24: internal links are now added at publish time via
  `keywords/related_links.py` + `publishing/webflow_poster.py`, injected
  before Conclusion rather than before FAQ. See §11.5.
- Word count increased from 600-800 to 900-1200 words
- Title rules: number + you + question mark mandatory
- Banned 15+ jargon words from titles (PAT, YoY, Volatile, etc.)
- TLDR bullets must contain primary keyword
- Anti-duplication rules: Swastika once, SIP once, links once
- Added 12 post-processors (see Section 12)
- En dash (`–`) enforced — em dash (`—`) banned everywhere
- English-only rule — removes foreign language characters

**app.py**
- Added `extract_faq_keyword()` function
- TLDR section: `<h2>TLDR</h2>` → `<h2>Key Takeaways – [keyword]</h2>`
- FAQ section: `<h3>` → `<h4>` for all FAQ questions
- FAQ h2: added keyword — `FAQ – [keyword] For Investors`
- `clean_blog_html()`: added `"tldr"` to REMOVE_PREFIXES
- `clean_blog_html()`: added table tags to `allowed_tags` (IPO tables kept)
- `notify_text`: handles both string and dict formats
- `instagram_notify`: handles both string and dict formats

> **2026-07-24 update:** the keyword-in-h2 calls above were dropped at
> some point (headings went back to bare `<h2>Key Takeaways</h2>` /
> `<h2>FAQ</h2>`) and `extract_faq_keyword()` sat unused. Owner decision
> was to keep bare headings and remove the now-dead function — see
> §13.4/§13.5 above and `docs/review.md` #5/#16.

---

*Last updated: 2026-07-24*