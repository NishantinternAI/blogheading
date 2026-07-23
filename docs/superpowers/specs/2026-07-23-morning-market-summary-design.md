# Morning Market Summary — Design

## Goal

Add a new recurring blog type — a "morning market summary" — that gets
generated from real NSE data (previous trading day's close) and competes for
the priority publishing slot alongside IPO articles, so it actually gets
published promptly rather than waiting in the regular news queue.

Scope for this iteration: **morning summary only**. Mid-day and closing
summaries are explicitly out of scope for now (paused per
`docs/scratchpad.md`).

## Content

Three data points, computed entirely from NSE's public archive CSVs (same
family as `tools/fetch_nse_index_data.py` already uses) — no live scraping,
no anti-bot session dance:

1. **Support/resistance levels** for Nifty 50 and Sensex — classic pivot
   point formula from the previous trading day's OHLC
   (`ind_close_all_DDMMYYYY.csv`):
   - Pivot `P = (High + Low + Close) / 3`
   - `R1 = 2P - Low`, `S1 = 2P - High`
   - `R2 = P + (High - Low)`, `S2 = P - (High - Low)`

2. **Top 5 gainers + top 5 losers** — from `sec_bhavdata_full_DDMMYYYY.csv`
   (every `EQ`-series stock's `PREV_CLOSE`/`CLOSE_PRICE`). We compute %
   change ourselves and rank. Filtered by a minimum `NO_OF_TRADES` threshold
   so illiquid/penny-stock noise doesn't dominate the list.

3. **Market-wide PCR (Put-Call Ratio)** — from
   `fao_participant_oi_DDMMYYYY.csv`'s `TOTAL` row: `Put OI / Call OI`.
   **Caveat, stated explicitly in the generated content**: this is
   aggregate *index options* OI (Nifty + Bank Nifty combined) — not a
   Nifty-only PCR. Getting a Nifty-only figure would require parsing NSE's
   zipped per-contract F&O bhavcopy, which is out of scope for this
   iteration.

All three archives are dated by trading day; none of them publish intraday,
so this is explicitly a "here's where things stood at yesterday's close, and
the levels to watch today" framing — not live data.

## New source: `sources/market_summary.py`

`fetch_morning_summary() -> list[dict]`

1. Resolve the last trading day: start at "yesterday" (calendar), step back
   day by day (cap at 7 days) until an `ind_close_all_*.csv` fetch succeeds —
   this naturally skips weekends and market holidays without needing a
   separate holiday calendar.
2. Fetch and parse the three archives for that resolved date.
3. Compute pivot levels (Nifty 50 + Sensex), top 5/top 5 gainers/losers, and
   PCR.
4. Build one article dict in the same shape the pipeline expects
   (`Blog_Title`, `Blog_Content`, `Blog_Links`, `source`) — see
   `sources/fetch_nse_corporate.py`'s `_build_item()` for the existing
   convention to follow. `Blog_Title` includes the resolved date (e.g.
   "Nifty 50, Sensex Morning Market Summary — Support, Resistance & Top
   Movers (23 Jul 2026)") so the pipeline's existing title-based "already
   published" dedup naturally prevents re-publishing the same day's summary
   twice — no new dedup mechanism needed.
5. **Error handling**: support/resistance and gainers/losers are required —
   if either archive fetch/parse fails after retrying back through recent
   trading days, return `[]` (no article this cycle; the next pipeline run
   retries). PCR is best-effort — if that one archive fails, omit the PCR
   section from `Blog_Content` and continue; don't block the whole article
   over it.

`Blog_Links` won't point to a real fetchable news article (there isn't
one — this is synthesized, not sourced from a news site). The blog generator
for this content type must NOT try to re-fetch it (see below).

## New generator function: `generate_market_summary_blog()` in `generators/blog_generator.py`

Added alongside the existing `generate_blog()` and `generate_ipo_blog()` in
the same file (not a new standalone file) — this matches the codebase's
actual live pattern: `generate_blog()` fetches the source URL via
`fetch_via_websearch()` and does keyword-volume lookups; `generate_ipo_blog()`
skips both and builds its prompt directly from `item["Blog_Title"]` /
`item["Blog_Content"]` since IPO items are structured data, not a news
article to re-fetch. (Note: `generators/generate_corporate_blog.py` is a
similar-looking standalone file but is **not actually wired into
`core/pipeline.py`**'s dispatch — corporate items go through the generic
`generate_blog()` too. Don't copy that file's pattern; follow
`generate_ipo_blog()`'s instead.)

`generate_market_summary_blog(item)` follows `generate_ipo_blog()`'s shape:
prompt built directly from `item["Blog_Title"]`/`item["Blog_Content"]`, no
external fetch, no keyword-volume lookup. Prompt instructs the model to
present the pivot levels and gainers/losers as HTML tables (per the existing
TABLES rule already in the file), explain what support/resistance means for
a retail reader, and include the PCR caveat verbatim if PCR data is present.
Returns the same shape as `generate_blog()`/`generate_ipo_blog()`
(`Blog_Title`, `Meta_Title`, `Meta_Description`, `TLDR`, `Blog_Content`,
`Conclusion`, `FAQ_Schema`), passed through `fix_all_fields()`.

## `core/pipeline.py` changes

1. Add `"market_summary"` to `PRIORITY_SOURCES` (currently
   `["nse_ipo", "google_trends"]`) — this is the whole mechanism that makes
   it "jump the queue" like IPOs: `classify_source()` buckets it into the
   priority stack, and when the priority stack has no IPO articles, popping
   falls back to `random.choice()` over whatever's left in priority — with
   usually just one market-summary article present, it wins every time.
2. Add `(fetch_morning_summary, "market_summary")` to the fetcher list in
   `_fetch_all_sources()`.
3. Add a third dispatch branch (next to the existing `nse_ipo` check) around
   line 1453: `if pop_type == "priority" and article_source ==
   "market_summary": blog_result = clean_newlines(_generate_market_summary_blog(final_item))`
   with a corresponding `_generate_market_summary_blog` timed wrapper (same
   pattern as `_generate_blog`/`_generate_ipo_blog` at line ~1077).
4. **Images: no changes needed.** Since `market_summary` isn't `nse_ipo`, it
   falls straight into the existing non-IPO image branches (AI or template
   compositor per `USE_AI_IMAGES`), which only read `Blog_Title`/
   `Blog_Content` — already present on the synthesized item.

## Out of scope (this iteration)

- Mid-day and closing summaries (explicitly paused)
- Nifty-only PCR (would need the zipped per-contract F&O bhavcopy)
- A dedicated image template/compositor for market summaries (uses the
  existing generic non-IPO image path)
- Any change to `publishing/webflow_poster.py` (confirmed: publishing is
  already source-agnostic, no per-source branching there)

## Testing

Manual, matching the repo's existing convention (no test runner/CI):
- `python -c "from sources.market_summary import fetch_morning_summary;
  print(fetch_morning_summary())"` — verify a well-formed article dict comes
  back, including on a Monday (to confirm the weekend-stepback logic works)
  and check behavior when run on/after a known market holiday.
- A `tools/test_market_summary_blog.py` ad-hoc script (mirroring
  `tools/test_ipo_blog.py`) to run
  `fetch_morning_summary()` → `generate_market_summary_blog()` end to end
  and print the result, without touching the live stacks/output files.
