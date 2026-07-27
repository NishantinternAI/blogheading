# Trending business topics integration — design

## Problem

Google Trends' actual "Trending Now" page shows finance-relevant spikes
(e.g. "indo mim ipo gmp today", "idfc first bank share", "itr filing last
date") that the pipeline currently has no way to catch. The existing
`google_trends` source (`sources/google_trends.py`'s `fetch_google_trends()`)
uses a fixed, unfilterable RSS feed capped at the top-10 *general-interest*
India trends — entertainment/sports/global-news-heavy, rarely finance.

A separate fetcher, `get_cached_business_trends()`, was already built and
deployed in this session (2026-07-27): it fetches the same "Trending Now"
data Google's UI shows, filtered to category 3 (Business & Finance,
confirmed empirically), cached for 2 hours to keep request volume to
Google low. It currently returns bare trending *query phrases* with
volume/growth metadata but no underlying article — nothing to write a
blog from yet.

This spec covers turning those bare phrases into real, safely-generated
blog candidates that flow through the existing pipeline.

## Non-goals

- Not replacing the existing `fetch_google_trends()` RSS source — it stays
  as a separate, additional `PRIORITY_SOURCES` entry (decided: add
  alongside, not replace).
- Not attempting semantic dedup against other sources that might cover the
  same underlying story under different headline text (e.g. a
  `business_standard` article and a Google-News-discovered article both
  about the same IDFC First Bank move, with different exact titles) — the
  pipeline's existing title-based dedup is the only dedup layer, same as
  every other source pair today.
- Not calling Selenium/a headless browser anywhere in this flow — the
  cached business-trends fetcher already proved a plain GET is sufficient,
  and this spec's grounding step uses Google News RSS (also a plain
  fetch) plus the existing `fetch_via_websearch()`.

## Critical constraint: no hallucinated blogs

`docs/review.md` records a 2026-07-24 incident: an article with a
genuinely on-topic title but empty real content caused the LLM to
hallucinate a completely unrelated, fabricated blog that published
successfully. The fix added a shared quality gate
(`sources/common.py`'s `assess_quality()`) that skips any article whose
content is too thin before it ever reaches the blog generator.

A bare trending phrase is *by definition* content-free — exactly this
failure shape. **Non-negotiable rule for this feature: a trend only
becomes a candidate article if real, substantiated news is found and
validated behind it. If nothing solid turns up, that trend is skipped
outright for this cycle — never passed to the blog generator with "write
something about X" and no real facts.**

## 1. Grounding a trend phrase in real news

New functions in `sources/google_trends.py` (same file `get_cached_business_trends()`
already lives in):

### `_search_google_news_for_trend(phrase: str) -> list[dict]`

Queries `https://news.google.com/rss/search?q=<url-encoded phrase>&hl=en-IN&gl=IN&ceid=IN:en`
(free, no AI cost) and parses the RSS `<item>` entries into
`{"title": ..., "link": ..., "pub_date": ..., "source": ...}` candidates,
same parsing shape `fetch_google_trends()` already uses for its own RSS
items. Returns `[]` on any network failure (caught, logged, not raised).

### `_pick_best_candidate(phrase: str, candidates: list[dict]) -> dict | None`

Title-level prefilter only (no AI call yet): keeps candidates whose title
shares at least one word (len > 3, case-insensitive) with the trend
phrase, same shape as the existing `_is_content_valid()` title-overlap
check. Returns the first (most relevant / most recent) surviving
candidate, or `None` if nothing overlaps.

### `ground_trend_in_news(trend: dict) -> dict | None`

Orchestrates the full grounding step for one trend dict (as returned by
`get_cached_business_trends()`):

1. `_search_google_news_for_trend(trend["title"])` → candidates. Empty →
   return `None`.
2. `_pick_best_candidate(...)` → best candidate. `None` → return `None`.
3. `core.model_client.fetch_via_websearch(best["link"])` → extracted
   content (one AI call — only spent once a real candidate URL exists).
   Empty/exception → return `None`.
4. `_is_content_valid(content, trend["title"])` (already exists in this
   file) — rejects paywalls/error pages and confirms topical relevance.
   Fails → return `None`.
5. `sources.common.assess_quality(content)` — rejects `"empty"`/`"bare"`
   (require at least `"thin"`, i.e. ≥150 words), matching the bar every
   other RSS-based fetcher already enforces. Fails → return `None`.
6. All pass → return an article dict:
   ```python
   {
       "Blog_Title":       best["title"],          # the REAL article's headline
       "Blog_Content":      content,
       "Blog_Links":        best["link"],
       "Blog_PublishDate":  best["pub_date"],
       "trending_signal":   f'{trend["title"]} ({trend["volume"]:,} searches, +{trend["growth_pct"]}%)',
   }
   ```
   `Blog_Title` is the real discovered headline, not the bare trend
   phrase — this keeps dedup-by-title behaving consistently with every
   other source (the pipeline's stack/dedup logic keys off this field).
   `trending_signal` is carried as extra metadata only (visible in
   `output.json` for later analysis of which trends actually converted to
   posts) — it is not read by `generate_blog()`'s prompt in this spec;
   wiring it into the prompt (e.g. to nudge keyword phrasing toward the
   exact trending query) is an explicit follow-up, not part of this pass.

### `fetch_trending_business_articles(max_trends: int = 5) -> list`

The actual fetcher plugged into `core/pipeline.py`:
1. `get_cached_business_trends()` → trends (already sorted by volume
   descending).
2. Take the top `max_trends` (default 5 — cost/latency control; higher-
   volume trends are also more likely to have real news behind them).
3. `ground_trend_in_news(t)` for each, dropping any `None` results.
4. Stamp `article["source"] = "google_trends_business"` is done by the
   existing `_fetch_all_sources()` loop (same as every other source), not
   here.
5. Return the surviving article list (0–5 items).

Each trend's grounding step is wrapped in its own try/except so one
trend's failure (e.g. a transient network error) never drops the other
four.

## 2. Wiring into `core/pipeline.py`

- Import `fetch_trending_business_articles` from `sources.google_trends`.
- Add `(fetch_trending_business_articles, "google_trends_business")` to
  the `sources` list in `_fetch_all_sources()`.
- Add `"google_trends_business"` to `PRIORITY_SOURCES` (currently
  `["nse_ipo", "google_trends", "market_summary"]`).
- Add `"google_trends_business"` to the bypass-country/category-filter
  treatment `nse_ipo` / `market_summary` / `google_trends` already get, in
  both `_fetch_after_timestamp()` and `_full_fetch_and_build_stack()` —
  it's already India+finance-scoped (`gl=IN`, category 3), so re-running
  `filter_by_country_and_category()` on it would be redundant.

No changes needed to `_build_stacks_from_articles()`, dedup, stacking, the
posting-pattern rotation, or `run_pipeline()` itself — articles from this
source are shaped identically to every other source's output and flow
through the exact same path unmodified.

## Data flow

```
get_cached_business_trends()   [2h cache, already live]
  → top 5 by volume
  → per trend: Google News RSS search (free)
      → title-prefilter candidates
      → fetch_via_websearch() on best candidate (1 AI call, only if a candidate exists)
      → _is_content_valid() relevance/paywall check
      → assess_quality() word-count gate
      → article dict, or skip (no fallback, no improvising)
  → 0-5 article dicts
  → merged into _fetch_all_sources()'s all_data
  → existing dedup / stack / pop / generate / publish pipeline, unchanged
```

## Error handling

- No Google News candidates for a trend → skip, log, continue to next
  trend.
- No candidate passes the title-prefilter → skip.
- `fetch_via_websearch()` returns empty or raises → skip.
- `_is_content_valid()` fails (paywall, error page, or no topical overlap
  with the trend phrase) → skip.
- `assess_quality()` returns `"empty"` or `"bare"` → skip.
- Network failure fetching Google News RSS for one phrase → caught,
  logged, that phrase is skipped — never aborts the other trends in the
  batch (same per-source isolation convention `_fetch_all_sources()`
  already uses).
- `get_cached_business_trends()` itself failing → already handled by the
  existing stale-cache fallback; if that's also empty, `max_trends` items
  is just `0` and `fetch_trending_business_articles()` returns `[]`.

## Cost / frequency profile

- Business-trends fetch itself: unchanged, ≤1 plain GET per 2 hours
  (already built and deployed).
- Per stack-rebuild event (irregular — only when priority+news+corporate
  all drain, same cadence every existing source already lives with, not
  every 8-minute pipeline cycle): ≤5 free Google News RSS queries + ≤5
  `fetch_via_websearch()` AI calls, and only for trends where a real
  candidate was actually found (often fewer than 5 calls in practice).
  Bounded, predictable ceiling — no risk of the runaway-cost or
  block-risk profile a higher-frequency or higher-volume approach would
  have carried.

## Testing

Extend `tools/test_google_trends_business.py` with mocked Google News RSS
responses and a mocked `fetch_via_websearch()`, covering:
- A trend with a relevant, sufficiently long real article → produces a
  correct article dict with the real headline as `Blog_Title`.
- A trend whose only candidates have no title-word overlap → skipped,
  returns `None`.
- A trend whose candidate content fails `_is_content_valid()` (paywall
  marker present) → skipped.
- A trend whose candidate content is real but too short (`assess_quality()`
  returns `"bare"`) → skipped.
- A Google News RSS network failure for one trend doesn't prevent the
  other trends in the same `fetch_trending_business_articles()` call from
  being processed.

No live network calls in the test file, consistent with this repo's
existing test convention (`tools/test_*.py`, ad-hoc scripts, no pytest).
