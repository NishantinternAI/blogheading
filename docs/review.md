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

### 1. ~~`pillow` missing from `requirements.txt`~~ **[FIXED 2026-07-24]**
~~`requirements.txt` has no `pillow`. Five modules do `from PIL import Image`:
`content_engine/image_module/{compositor,ipo_compositor,ai_image_generator,validator}.py`
and `verify_images.py`. A clean Docker build (`pip install -r requirements.txt`)
will not have Pillow → **all image generation fails** the moment the first
article is processed.~~
Added `pillow` to `requirements.txt`.

### 2. ~~Import-time network calls in 5 of 6 RSS fetchers~~ **[STALE — already fixed, verified 2026-07-24]**
~~Module-level statements that execute on `import`:~~
- ~~`sources/zerodha.py:37` → `print(len(fetch_zerodha()))`~~
- ~~`sources/cnbc.py:22` → `print(len(fetch_cnbc()))`~~
- ~~`sources/paisa.py:23` → `print(len(fetch_5paisa()))`~~
- ~~`sources/livemint.py:34` → `print(len(fetch_livemint()))`~~
- ~~`sources/fetch_nse_corporate.py:41-42` → `result = fetch_nse_corporate()` + print~~

Re-checked against the current tree: all five test-call blocks in
`sources/{zerodha,cnbc,paisa,livemint,fetch_nse_corporate}.py` are now
guarded by `if __name__ == "__main__":`. No code change needed here —
this matches the note already in `CLAUDE.md` ("Known gotchas") that this
finding no longer holds post-2026-07-refactor.

---

## P1 — Logic bugs

### 3. ~~Zerodha fallback ignores its own dedup result~~ **[STALE — already fixed, verified 2026-07-24]**
~~Commit `05672c1` ("fix duplicate handling in zerodha fallback") added a
`fresh_zerodha` dedup list and an abort-if-empty check — but the line that
actually picks the article was left untouched:~~
```python
fresh_zerodha = [a for a in zerodha_data if normalize_title(...) not in used_titles]
if not fresh_zerodha: return []
...
final_item = random.choice(fresh_zerodha)   # already selects from the deduped list
```
Re-checked `core/pipeline.py:1361` against the current tree: selection
already draws from `fresh_zerodha`, not the un-deduped `zerodha_data`. No
code change needed — this was fixed sometime before/during the 2026-07
refactor and the review just hadn't been re-verified against current
line numbers.

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

### 5. ~~`extract_faq_keyword()` result computed then discarded~~ **[RESOLVED 2026-07-24 — owner decision]**
Re-verified against the current tree: the calls that computed
`tldr_keyword`/`faq_keyword` and discarded them no longer exist at all
(not just discarded — removed), so headings were already bare
`<h2>Key Takeaways</h2>` / `<h2>FAQ</h2>` with no dead call sites left
behind. Owner chose to keep bare headings and delete the now-fully-unused
`extract_faq_keyword()` function from `app.py` rather than restore the
keyword-in-h2 feature. `docs/architecture.md` §13.2/§13.4/§13.5 and the
Changelog corrected to match.

### 6. ~~`fix_garbage_characters` is never applied to `Blog_Content`~~ **[FIXED 2026-07-24]**
~~In `fix_all_fields`, the garbage/foreign-char filter runs only for
`Blog_Title, Meta_Title, Meta_Description, Conclusion`. For `Blog_Content` only
the HTML-specific fixers run — `fix_garbage_characters` is **not** called.
README §11.9/§12 claim "English only — removes foreign language characters" and
list it applied to "all string fields." So Chinese/foreign characters in the
**blog body** survive.~~
Added a `fix_garbage_characters(value)` call to the `Blog_Content` branch
of `fix_all_fields` (`generators/blog_generator.py`), right after the
newline normalisation and before the HTML-structure fixers. Verified it
strips non-ASCII/non-allowlisted characters while leaving HTML tags and
allowlisted symbols (`₹`, en/em dash, curly quotes, `°`, `…`) intact.
**Fix:** also run `fix_garbage_characters` over `Blog_Content`.

### 7. ~~Exceptions swallowed without traceback~~ **[FIXED 2026-07-24]**
```python
except Exception as e:
    print(f"[ERROR] {e}")
    traceback.print_exc()
```
The whole STEP 6–8 block (blog gen, images, save) is wrapped in this
(now `core/pipeline.py:1660-1661`). Added `import traceback` and a
`traceback.print_exc()` call alongside the existing message print, so
production failures now log a full stack trace instead of just the
exception message.

---

## P2 — Robustness & architecture

### 8. ~~`output.json` write is not atomic~~ **[FIXED 2026-07-24]**
```python
with open(filepath, "w", encoding="utf-8") as f:
    json.dump(existing, f, ...)
```
~~`output.json` is both the **published store** and the **dedup index**. Opening
in `"w"` truncates first; a crash / container kill mid-`json.dump` leaves a
truncated/corrupt file. On the next run `load_used_titles()` / the dashboard
silently get `[]` (the bare `except` swallows `JSONDecodeError`) → **all history
lost + dedup resets**.~~ `storage/save_output.py` now writes to a `.tmp`
file and `os.replace()`s it over the real path (atomic on the same
filesystem — no window where a crash leaves a truncated file). Also
added a module-level `BASE_DIR` (repo root, like `core/pipeline.py`'s)
so the output path no longer depends on the process cwd being `/app`.

### 9. ~~Chittorgarh IPO URL map never expires~~ **[FIXED 2026-07-24]**
~~`_build_ipo_map()` caches `_ipo_df_cache` (now `IPODetailScraper._ipo_df_cache`,
an instance attribute per the phase-b class refactor) with **no TTL**. The
per-company data cache `_ipo_data_cache` has a 6h TTL, but the *map of which
IPOs exist* was built once on the first fetch and reused for the entire
container lifetime (days/weeks). On a 24/7 scheduler, **IPOs filed after
process start were never found by the primary source** (Chittorgarh
`_find_ipo_url` returns "" → falls to InvestorGain/Moneycontrol or gets
skipped).~~ Added `self._ipo_df_cache_at` (timestamp) alongside the cached
`DataFrame` and gated the early-return in `_build_ipo_map()` on the same
`CACHE_TTL_HOURS` (6h) used by the per-company cache — a stale map now
triggers a rebuild instead of being reused forever. Verified with a unit
test: fresh cache (age < 6h) short-circuits with zero network calls; a
7h-old cache triggers a full rebuild.

### 10. ~~`requests.get` without timeout~~ **[STALE — already fixed, verified 2026-07-24]**
Re-checked `sources/fetch_nse_corporate.py`: its one `requests.get(NSE_RSS_URL, ...)`
call already has `timeout=20`. No code change needed.

### 11. ~~Country/category filter fails open~~ **[STALE — already fixed, verified 2026-07-24]**
```python
if not filtered:
    print("[FILTER] No match → returning all data")
    return data, "fallback"
```
Re-checked `utils/combined_filter.py` against the current tree: no such
fail-open branch exists. Both the "AI matched nothing" path and the
JSON-parse-failure path now return `([], "none")` — a genuinely-empty
match no longer floods the stack with unfiltered articles. No code
change needed.

### 12. ~~`USE_AI_IMAGES` duplicated, manual sync~~ **[FIXED 2026-07-24]**
~~Two hardcoded copies that "must match." If one is flipped without the other, the
dashboard reads the wrong JSON file and shows stale/empty data.~~ Both
`core/pipeline.py` and `app.py` now read `USE_AI_IMAGES` from the
environment (`os.getenv("USE_AI_IMAGES", "False")`, truthy on
`1`/`true`/`yes`), and `docker-compose.yml` sets it once via
`${USE_AI_IMAGES:-False}` in both services' `environment:` blocks. For
local (non-Docker) runs, `app.py` now calls `load_dotenv()` directly and
`core/pipeline.py` already picked up `.env` transitively via
`config.py`'s `load_dotenv()`. `CLAUDE.md` updated to match.

### 13. ~~Dead code — large~~ **[RESOLVED — mostly stale, dead files removed 2026-07-24]**
- ~~`pipeline.py`: active code is **941–1856** (~915 lines). Lines **1–940**
  and **1858–5415** are two full commented-out prior versions (~4,500 lines).~~
  Already cleaned up in the 2026-07 refactor per `CLAUDE.md` — `core/pipeline.py`
  is now 1666 lines, all live (longest run of consecutive comment lines is 15).
- ~~`generators/blog_generator.py`: active **1–803**; **805–2142** commented (~1,340).~~
  Now 1500 lines, no large commented block remains (longest run: 7 lines).
- ~~`content_engine/image_module/ipo_compositor.py`: active from **420**; ~400
  commented above.~~ Now 459 lines, no large commented block remains (longest
  run: 15 lines — a normal docstring-style header, not dead code).
- ~~`scheduler.py`: ~140 commented lines.~~ Now 69 lines total, essentially none.
- Dead files (only referenced by each other, not the live pipeline):
  ~~`mergeall.py`~~ and ~~`Filter_news/finance_filter.py`~~ (already removed,
  per `CLAUDE.md`'s 2026-07 rename note) confirmed gone. `utils/stack_manager.py`
  and `generators/filter_by_category_model.py` were still present with zero
  importers anywhere in the codebase — deleted 2026-07-24.

---

## P3 — Documentation vs code (code is the source of truth unless noted)

| # | README location | README says | Code actually does | Direction |
|---|---|---|---|---|
| 14 | ~~§1 Overview~~ | ~~"every 15 minutes"~~ | `scheduler.py:31` cron `minute='*/8'` = **8 min** (not the 5 min this row originally claimed — re-verified against current code) | **Fixed 2026-07-24** — `docs/architecture.md` overview + intro block corrected to "every 8 minutes" |
| 15 | ~~§11.5 + §12 + Changelog~~ | ~~Mandatory **internal links** (3, before FAQ); `fix_duplicate_links`/`fix_links_before_faq` active~~ | Neither post-processor exists in `blog_generator.py` any more, and the prompt has no internal-link rule at all (positive or negative) — the feature moved entirely to publish time (`keywords/related_links.py` + `publishing/webflow_poster.py`, injected before Conclusion). | **Resolved 2026-07-24 — docs corrected** |
| 16 | ~~§13.4/§13.5 + Changelog~~ | ~~keyword-rich `<h2>Key Takeaways – …>` / `<h2>FAQ – … For Investors>`~~ | `app.py` emits bare h2 (finding #5) | **Resolved 2026-07-24 — fixed docs** |
| 17 | ~~§7.7/§14~~ | ~~`TEST_MODE = True`, `TEST_COMPANY = "Aureate Tradde"`~~ | `TEST_MODE`/`TEST_COMPANY` **no longer exist at all** in `sources/ipo.py` — the `__main__` block calls `fetch_nse_ipo()` directly against the live feed, no toggle needed | **Fixed 2026-07-24** — `docs/architecture.md` §7.7/§14 corrected to describe current behavior; `CLAUDE.md`'s gotcha note about this flag is stale too |
| 18 | ~~§16 Deployment~~ | ~~`version: 3.8`, `env_file: .env` compose~~ | `docker-compose.yml` now exists in the repo (it didn't when this row was written) but never matched the doc's fabricated snippet — real file uses explicit `environment:` entries (no `env_file:`), `restart: unless-stopped`, no `container_name:`. `Dockerfile` is `python:3.10`; doc said Python 3.11 | **Fixed 2026-07-24** — `docs/architecture.md` §1 tech-stack table + §16 compose snippet corrected to match the real files |
| 19 | ~~§16 Deployment~~ | ~~no mention of `config.py`~~ | `config.py` is **required** (now `core/model_client.py:31` `from config import client, MODEL`), gitignored — must exist on server before first run | **Fixed 2026-07-24** — added a "Required gitignored files" subsection to `docs/architecture.md` §16 covering `config.py`, `.env`, and `google-ads.yaml` |

---

## Decisions for the owner (do NOT silently "fix")

These are **half-reverted product/SEO features**, not bugs. Git history shows the
prompt was deliberately changed. Resolving them by editing code to match the
stale README would *introduce* a regression. Choose per item:

- ~~**Internal links (#15)**~~ — **Resolved 2026-07-24:** turns out this
  wasn't actually half-reverted — the feature is live, just implemented
  in a different layer than the stale docs described (publish-time
  `keywords/related_links.py` + `publishing/webflow_poster.py`, not
  `blog_generator.py` post-processors). `docs/architecture.md` §11.5 +
  the func table + Changelog corrected to match. Also found and fixed a
  real bug while verifying this: `related_links.py`'s `KEYWORD_GRAPH_PATH`
  default was a hardcoded Windows dev path (`D:\Blogheading\output\...`)
  that would never resolve on the Linux production container, silently
  making the whole related-links feature a no-op in production. Changed
  the default to a `BASE_DIR`-relative path (repo root, matching
  `core/pipeline.py`'s and `storage/save_output.py`'s pattern) and
  removed a ~270-line dead first draft of the module that sat above the
  live code.
- ~~**Keyword-in-H2 (#16)**~~ — **Resolved 2026-07-24:** owner chose to keep
  bare `<h2>Key Takeaways</h2>` / `<h2>FAQ</h2>`, removed the now-fully-unused
  `extract_faq_keyword()` from `app.py`, and corrected
  `docs/architecture.md` §13.2/§13.4/§13.5 + Changelog to match.

---

## Minor / nice-to-have
- ~~`add_cached.py:36` hardcodes `$3/$15` per-M token pricing regardless of
  `MODEL` — cost log is wrong if the model changes.~~ **[FIXED 2026-07-24]**
  `core/model_client.py` (renamed from `add_cached.py`) now looks up a
  `PRICING` dict keyed by `MODEL`, with a fallback that prints a visible
  `[COST] WARNING` when the current model has no entry, instead of
  silently costing every model as if it were priced like the default.
- ~~`add_cached.py:19` `@lru_cache(maxsize=200)` keys on the full prompt (article
  body included) → near-zero hit rate; just holds 200 large strings in
  memory.~~ **[FIXED 2026-07-24]** Removed the `@lru_cache` from
  `cached_model_call()` entirely — with ~10 call sites across the
  codebase all passing prompts with unique article bodies, real hit
  rate was effectively zero, so it was pure memory waste while also
  creating a footgun (retrying with the same prompt after a downstream
  failure would silently replay the stale cached response instead of
  calling the API again). Also removed the now-pointless
  `cached_model_call.cache_clear()` call in `tools/test_title.py`.
- ~~Field name drift: `cnbc/paisa/livemint` emit `Blog_Links` (plural);
  `zerodha/nse_corporate` emit `Blog_Link` (singular). Handled defensively in
  `app.py` but fragile.~~ **[STALE — already fixed at the source, cleaned up
  2026-07-24]** Re-checked every `sources/*.py` fetcher: all of them
  (including `zerodha.py` and `fetch_nse_corporate.py`) now emit
  `Blog_Links` (plural) consistently — no fetcher emits singular
  `Blog_Link` anywhere. `app.py` still had three leftover
  `item.get("Blog_Link") or item.get("Blog_Links", ...)` defensive
  fallbacks for the field that no longer exists; simplified all three to
  a plain `item.get("Blog_Links", ...)`.
- ~~`sources/ipo.py:391` `_scrape_moneycontrol` → `name_clean.split()[0]` raises
  `IndexError` if the normalized name is empty (e.g. "India Ltd"); currently
  masked by the waterfall `try/except`.~~ **[FIXED 2026-07-24]** (the
  "India Ltd" example didn't actually reproduce it — `_normalize_company_key`
  only strips a suffix when preceded by a space, so that input normalizes to
  `"india"`, not empty — but an empty/whitespace-only `company_name` does
  produce an empty normalized key and hit the same crash.) Added an
  explicit empty-check before indexing `[0]`, returning `{}` with a clear
  log line instead of raising into the waterfall's generic
  `except Exception` (which would still have caught it, but with an
  unhelpful bare "list index out of range" message).
- ~~No `.dockerignore` — `COPY . .` ships `.git/`, `output/`, `__pycache__/`.~~
  **[FIXED 2026-07-24]** Added `.dockerignore` excluding `.git/` (~40MB),
  `output/`/`output_images/`/`logs/` (bind-mounted at runtime in
  `docker-compose.yml` anyway, so baking them into the image was pure
  waste), `__pycache__/`, and OS cruft. Deliberately does **not** exclude
  `config.py`/`.env`/`google-ads.yaml` — those are required at import
  time and aren't volume-mounted, so excluding them would break the
  container at startup. Verified the runtime code already
  `os.makedirs(..., exist_ok=True)`s every output directory it needs, so
  omitting the (empty at build time anyway) directories from the build
  context is safe.

---

## Suggested fix order
1. ~~`requirements.txt` += `pillow` (P0 #1)~~ — done 2026-07-24
2. ~~Guard all 5 RSS import-time calls (P0 #2)~~ — already fixed, stale finding
3. ~~`random.choice(fresh_zerodha)` (P1 #3)~~ — already fixed, stale finding
4. ~~Font filename casing in both compositors (P1 #4)~~ — done 2026-07-24
5. ~~`fix_garbage_characters` on `Blog_Content` (P1 #6)~~ — done 2026-07-24
6. ~~`traceback.print_exc()` (P1 #7)~~ — done 2026-07-24
7. ~~`timeout=15` on NSE corporate fetch (P2 #10)~~ — already fixed, stale finding
8. ~~Atomic `save_output` write (P2 #8)~~ — done 2026-07-24
9. ~~TTL on Chittorgarh map (P2 #9)~~ — done 2026-07-24
10. ~~(Owner) #15/#16 decisions~~ — both resolved 2026-07-24. #16: bare
    headings kept, docs fixed. #15: turned out not half-reverted at all —
    docs corrected to describe the live publish-time mechanism, plus a
    real production bug found & fixed along the way (`KEYWORD_GRAPH_PATH`
    hardcoded Windows path). Dead-code deletion done (#13).
    ~~`USE_AI_IMAGES` env var unification~~ — done 2026-07-24 (P2 #12).

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
