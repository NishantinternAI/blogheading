# Code Review — Blogheading Pipeline

**Reviewer:** Jay Shrivastava (Principal AI Engineer review)
**Branch:** `test_ipo_news`
**Date:** 2026-06-02
**Scope:** Full codebase vs `Blogheading docs·md` (README), re-verified against the
current tree after merging `origin/main` (`05672c1`, `4b9987c`).

> Items below are re-verified against the **current** code, with exact
> `file:line`. New findings beyond the earlier pass are marked **[NEW]**.

---

## P0 — Breaks / misbehaves in production

### 1. `pillow` missing from `requirements.txt`
`requirements.txt` has no `pillow`. Five modules do `from PIL import Image`:
`content_engine/image_module/{compositor,ipo_compositor,ai_image_generator,validator}.py`
and `verify_images.py`. A clean Docker build (`pip install -r requirements.txt`)
will not have Pillow → **all image generation fails** the moment the first
article is processed.
**Fix:** add `pillow` to `requirements.txt`.

### 2. Import-time network calls in 5 of 6 RSS fetchers  **[NEW — earlier pass caught only 1]**
Module-level statements that execute on `import`:
- `sources/zerodha.py:37` → `print(len(fetch_zerodha()))`
- `sources/cnbc.py:22` → `print(len(fetch_cnbc()))`
- `sources/paisa.py:23` → `print(len(fetch_5paisa()))`
- `sources/livemint.py:34` → `print(len(fetch_livemint()))`
- `sources/fetch_nse_corporate.py:41-42` → `result = fetch_nse_corporate()` + print

`pipeline.py` imports all of these at the top, so **every scheduler
start fires 5 unnecessary HTTP requests** (plus the startup log noise:
`25 / 200 / 10 / 35 / NSE COUNT`). `sources/ipo.py` is the only one that correctly
guards its test code with `if __name__ == "__main__":`.
**Fix:** wrap each stray call in `if __name__ == "__main__":`.

---

## P1 — Logic bugs

### 3. Zerodha fallback ignores its own dedup result  (`pipeline.py:1592-1602`)  **[NEW — the merge "fix" is incomplete]**
Commit `05672c1` ("fix duplicate handling in zerodha fallback") added a
`fresh_zerodha` dedup list and an abort-if-empty check — but the line that
actually picks the article was left untouched:
```python
fresh_zerodha = [a for a in zerodha_data if normalize_title(...) not in used_titles]
if not fresh_zerodha: return []
...
final_item = random.choice(zerodha_data)   # ← still the UN-deduped list
```
So the dedup work is dead: selection still draws from `zerodha_data`.
**Real impact:** it will **not** double-publish — `save_output()` dedups on
`Blog_Title` (`.strip().lower()`) and returns `False`. The harm is (a) **wasted
AI generation + image spend** on an article that gets discarded at save, and
(b) `run_pipeline` returns `[final_item]` reporting success for a run that saved
nothing — misleading logs/metrics.
**Fix:** `final_item = random.choice(fresh_zerodha)`.

### 4. ~~Font filename case mismatch — silent fallback on Linux/Docker~~ **[FIXED 2026-07-24]**
~~`content_engine/image_module/compositor.py:214,216` and
`ipo_compositor.py:428,430` reference:~~
```python
'extrabold': '.../fonts/ExtraBold.ttf',
'regular':   '.../fonts/Regular.ttf',
```
~~The committed files are **lowercase**: `content_engine/fonts/extrabold.ttf`,
`regular.ttf` (only `GoogleSans_17pt-Bold.ttf` matches its reference exactly).
On Windows (case-insensitive FS) this works, so it passed local testing. On the
**Linux production container (case-sensitive)** `os.path.exists()` is `False` →
code silently falls back to DejaVu/Liberation or `ImageFont.load_default()`.
Result: company names / overlays render in the **wrong font** on the server with
no error. Classic "works on my machine."~~
Since the phase-b refactor, both compositors share one `FONTS` dict in
`content_engine/image_module/base_compositor.py:32-36`. Fixed there by
pointing `'extrabold'`/`'regular'` at the actual lowercase filenames
(`extrabold.ttf`/`regular.ttf`).

### 5. `extract_faq_keyword()` result computed then discarded  (`app.py:490,503`)  **[NEW]**
```python
tldr_keyword = extract_faq_keyword(ai_title)   # line 490 — never used
blog_combined += f"<h2>Key Takeaways</h2>\n"    # bare, no keyword
...
faq_keyword = extract_faq_keyword(ai_title)     # line 503 — never used
blog_combined += f"<h2>FAQ</h2>\n"              # bare, no keyword
```
The emitted HTML is bare `<h2>Key Takeaways</h2>` / `<h2>FAQ</h2>`. This
**contradicts README §13.4/§13.5 and the Changelog**, which claim
`<h2>Key Takeaways – {keyword}</h2>` and `<h2>FAQ – {keyword} For Investors</h2>`.
Also note `extract_faq_keyword`'s `STOP` set (`app.py:52`) ends with a literal
`...` (Python `Ellipsis`) — placeholder code that was never finished.
**This is a half-reverted feature — see "Decisions for the owner" below.**

### 6. `fix_garbage_characters` is never applied to `Blog_Content`  (`generators/blog_generator.py:210-228`)  **[NEW]**
In `fix_all_fields`, the garbage/foreign-char filter runs only for
`Blog_Title, Meta_Title, Meta_Description, Conclusion`. For `Blog_Content` only
the HTML-specific fixers run — `fix_garbage_characters` is **not** called.
README §11.9/§12 claim "English only — removes foreign language characters" and
list it applied to "all string fields." So Chinese/foreign characters in the
**blog body** survive. (`fix_garbage_characters` keeps all `<128` chars, so HTML
tags are safe to filter.)
**Fix:** also run `fix_garbage_characters` over `Blog_Content`.

### 7. Exceptions swallowed without traceback  (`pipeline.py:1852-1853`)
```python
except Exception as e:
    print(f"[ERROR] {e}")
```
The whole STEP 6–8 block (blog gen, images, save) is wrapped in this. Only the
message prints — no stack trace, no file/line. Production failures are very hard
to diagnose.
**Fix:** `traceback.print_exc()` (or `logging.exception`).

---

## P2 — Robustness & architecture

### 8. `output.json` write is not atomic  (`storage/save_output.py:39-40`)  **[NEW]**
```python
with open(filepath, "w", encoding="utf-8") as f:
    json.dump(existing, f, ...)
```
`output.json` is both the **published store** and the **dedup index**. Opening
in `"w"` truncates first; a crash / container kill mid-`json.dump` leaves a
truncated/corrupt file. On the next run `load_used_titles()` / the dashboard
silently get `[]` (the bare `except` swallows `JSONDecodeError`) → **all history
lost + dedup resets**. Write to a temp file then `os.replace()` (atomic on
same filesystem). Also relative path `output/{filename}` — works only because
Docker `WORKDIR=/app`; use `BASE_DIR`.

### 9. Chittorgarh IPO URL map never expires  (`sources/ipo.py:108-164`)  **[NEW]**
`_build_ipo_map()` caches `_ipo_df_cache` as a module global with **no TTL**.
The per-company data cache `_ipo_data_cache` has a 6h TTL, but the *map of which
IPOs exist* is built once on the first fetch and reused for the entire container
lifetime (days/weeks). On a 24/7 scheduler, **IPOs filed after process start are
never found by the primary source** (Chittorgarh `_find_ipo_url` returns "" →
falls to InvestorGain/Moneycontrol or gets skipped). README §7.3 calls it
"Cached per session," but a long-lived container = one infinite session.
**Fix:** give `_ipo_df_cache` the same 6h TTL as the data cache.

### 10. `requests.get` without timeout  (`sources/fetch_nse_corporate.py:13`)
No `timeout=`. NSE is frequently slow/blocking; a hung socket blocks the single
scheduler thread indefinitely (`ThreadPoolExecutor(1)`), stalling the whole
pipeline. **Fix:** add `timeout=15`.

### 11. Country/category filter fails open  (`utils/combined_filter.py:101-102`)  **[NEW — review for intent]**
```python
if not filtered:
    print("[FILTER] No match → returning all data")
    return data, "fallback"
```
When the AI legitimately matches **nothing** (`source="none"`), the code returns
**all** unfiltered articles — identical to the parse-failure path. So a run with
genuinely no India/finance matches floods the news stack with everything. May be
intentional (avoid empty pipeline), but it silently defeats the filter. At least
distinguish `"none"` (legitimately empty) from a parse error.

### 12. `USE_AI_IMAGES` duplicated, manual sync  (`pipeline.py:996`, `app.py:224`)
Two hardcoded copies that "must match." If one is flipped without the other, the
dashboard reads the wrong JSON file and shows stale/empty data. Should be one
env var read by both.

### 13. Dead code — large
- `pipeline.py`: active code is **941–1856** (~915 lines). Lines **1–940**
  and **1858–5415** are two full commented-out prior versions (~4,500 lines).
- `generators/blog_generator.py`: active **1–803**; **805–2142** commented (~1,340).
- `content_engine/image_module/ipo_compositor.py`: active from **420**; ~400
  commented above.
- `scheduler.py`: ~140 commented lines.
- Dead files (only referenced by each other, not the live pipeline):
  `mergeall.py`, `utils/stack_manager.py`, `generators/filter_by_category_model.py`,
  `Filter_news/finance_filter.py`.

---

## P3 — Documentation vs code (code is the source of truth unless noted)

| # | README location | README says | Code actually does | Direction |
|---|---|---|---|---|
| 14 | §1 Overview | "every 15 minutes" | `scheduler.py:14` cron `*/5` = **5 min** | Fix README |
| 15 | §11.5 + §12 + Changelog | Mandatory **internal links** (3, before FAQ); `fix_duplicate_links`/`fix_links_before_faq` active | Both post-processors are **commented out** (`blog_generator.py:116-151,222-223`); prompt now says "**NO internal links anywhere**" (line 728) | **Owner decision** (see below) |
| 16 | §13.4/§13.5 + Changelog | keyword-rich `<h2>Key Takeaways – …>` / `<h2>FAQ – … For Investors>` | `app.py` emits bare h2 (finding #5) | **Owner decision** |
| 17 | §7.7/§14 | `TEST_MODE = True`, `TEST_COMPANY = "Aureate Tradde"` | `sources/ipo.py:677-678` `TEST_MODE = False`, `"Q-Line Biotech Limited"` | Fix README (code correct for prod) |
| 18 | §16 Deployment | `version: 3.8`, `env_file: .env` compose | `Dockerfile` is `python:3.10`; README §1 says Python 3.11; no compose file in repo | Fix README / add compose |
| 19 | §16 Deployment | no mention of `config.py` | `config.py` is **required** (`add_cached.py:2` `from config import client, MODEL`), gitignored — must exist on server before first run | Document it |

---

## Decisions for the owner (do NOT silently "fix")

These are **half-reverted product/SEO features**, not bugs. Git history shows the
prompt was deliberately changed. Resolving them by editing code to match the
stale README would *introduce* a regression. Choose per item:

- **Internal links (#15):** restore the feature (uncomment processors + re-add
  prompt rule) **OR** keep current "no links" behaviour and correct README §11.5/§12.
- **Keyword-in-H2 (#16):** restore (wire `tldr_keyword`/`faq_keyword` into the h2
  strings + finish the `STOP` set) **OR** remove the dead variables and correct
  README §13.4/§13.5.

---

## Minor / nice-to-have
- `add_cached.py:36` hardcodes `$3/$15` per-M token pricing regardless of `MODEL`
  — cost log is wrong if the model changes.
- `add_cached.py:19` `@lru_cache(maxsize=200)` keys on the full prompt (article
  body included) → near-zero hit rate; just holds 200 large strings in memory.
- Field name drift: `cnbc/paisa/livemint` emit `Blog_Links` (plural);
  `zerodha/nse_corporate` emit `Blog_Link` (singular). Handled defensively in
  `app.py` but fragile.
- `sources/ipo.py:391` `_scrape_moneycontrol` → `name_clean.split()[0]` raises
  `IndexError` if the normalized name is empty (e.g. "India Ltd"); currently
  masked by the waterfall `try/except`.
- No `.dockerignore` — `COPY . .` ships `.git/`, `output/`, `__pycache__/`.

---

## Suggested fix order
1. `requirements.txt` += `pillow` (P0 #1)
2. Guard all 5 RSS import-time calls (P0 #2)
3. `random.choice(fresh_zerodha)` (P1 #3)
4. Font filename casing in both compositors (P1 #4)
5. `fix_garbage_characters` on `Blog_Content` (P1 #6)
6. `traceback.print_exc()` (P1 #7)
7. `timeout=15` on NSE corporate fetch (P2 #10)
8. Atomic `save_output` write (P2 #8)
9. TTL on Chittorgarh map (P2 #9)
10. (Owner) dead-code deletion, `USE_AI_IMAGES` env var, doc fixes, #15/#16 decisions

---

## Published blog SEO QA — gold price today (2026-07-23)

**URL:** `https://www.swastika.co.in/blog/gold-price-today-across-india-city-wise-24k-and-22k-rates`
**Reviewer:** Jay Shrivastava, via third-party SEO grader
**Scope:** SEO only — readability (63.3, target 50.0) and tone of voice (consistent,
92%) both graded fine and are **out of scope** for follow-up. Only the SEO
section (**5.8 / 10, "Mediocre"**) needs action.

### Target keywords not yet used
None of these appear in the post at all — each should land at least once:
`gokaldas exports stock`, `retail expansion`, `retail investor`, `margin expansion`,
`retail growth`, `revenue streams`, `ril stock`, `growth phase`, `ai stock assistant`,
`omnichannel growth`.

> Note: several of these (`gokaldas exports stock`, `ril stock`, `retail expansion`,
> `omnichannel growth`) read as keywords carried over from a different content
> template (retail/stock-analysis) rather than this gold-price piece — worth
> checking whether the SEO tool's keyword set was correctly scoped to this URL
> before force-fitting all ten into a gold-price article.

### Recommended (secondary) keywords to enrich with
`supply chains`, `social media`, `physical stores`, `ai powered`, `retail store`,
`product or service`, `artificial intelligence`, `products and services`,
`customer base`, `growth opportunities`, `market share`, `wide range`,
`growth rates`, `competitive advantage`, `revenue growth`, `marketing strategies`,
`customer engagement`, `retail businesses`, `customer preferences`,
`brick and mortar store`.

### Alt attribute issues
Grader flags missing/insufficient image alt text — add more images with
descriptive alt attributes.

### Link issues
1. "Open your trading and demat account here" — currently links to the
   homepage; should point to a more specific/relevant page (e.g. account
   opening page) instead.
2. "Swastika's Sarthi AI stock assistant" — **link is broken**, needs fixing.

### Title issues
Grader wants at least one target keyword in the title, and no target keyword
repeated more than once. Current title — "Gold Price Today Across India:
City-Wise 24K & 22K Rates" — contains none of the listed target keywords
(consistent with the keyword-scoping question raised above).

### Action items (SEO only — readability/tone need no changes)
- [ ] Fix the broken "Sarthi AI stock assistant" link.
- [ ] Repoint the "Open your trading and demat account here" link away from
  the homepage to a more relevant page.
- [ ] Add alt text to images (and consider adding more images).
- [ ] Confirm with the SEO tool/owner whether the target-keyword list was
  correctly scoped to this article before weaving them in — several look
  mismatched to a gold-price piece.
- [ ] If confirmed correct, work the target keywords in naturally (title +
  body) and sprinkle in recommended keywords, without breaking the
  currently-good readability/tone scores.
