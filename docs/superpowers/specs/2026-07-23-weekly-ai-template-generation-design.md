# Weekly AI template generation — design

## Problem

The current on-disk template pool (`content_engine/templates/{finance,general}/{outer,inner}/`,
17 pairs each) is stale — every non-IPO blog reuses the same small set of
images regardless of topic, and they no longer relate to the actual content
being published. The user wants a small, cheap, automated weekly refresh:
generate 10 (max 15) new AI template images every week, store them (the pool
only grows, never shrinks/replaces), and eventually cover more topic
categories than just finance/general — while keeping AI image generation out
of the hot path (`USE_AI_IMAGES` stays off; per-blog generation is still too
slow/expensive to run on every one of the ~180 pipeline runs/day).

## Non-goals

- Not touching `USE_AI_IMAGES` / per-blog AI image generation (`ai_image_generator.py`
  stays as-is, still gated off in production).
- Not touching `ipo_compositor.py` or IPO's fixed template — IPO is
  deliberately a separate, fixed-template path because of its outsized
  traffic priority; it is not part of this template pool.
- Not touching the news-fetch category filter (`filter_by_country_and_category`,
  the `category` param used to decide *which articles* get fetched into a
  pipeline run). Only image/template selection changes.

## 1. Per-blog template-category classification

New pure function `classify_template_category(title, content) -> str` in
`content_engine/image_module/template_selector.py`, reusing the exact
keyword bins already defined in `ai_image_generator.build_image_prompt()`:

| Category      | Trigger keywords (any match, checked in this order) |
|---------------|-------------------------------------------------------|
| `dividend`    | dividend, ex-date, record date, payout, buyback |
| `rbi_policy`  | rbi, reserve bank, rate, monetary, inflation, cpi, repo |
| `gold_oil`    | gold, silver, bullion, precious metal — OR — oil, crude, petroleum, fuel, ongc, bpcl, hpcl |
| `tech`        | infosys, tcs, wipro, it sector, tech, software |
| `banking`     | bank, banking, psu bank, private bank, npa, credit growth, sbi, hdfc bank, icici bank, axis bank, kotak, deposit (new bin, not in `ai_image_generator.py` today) |
| `finance`     | bullish/bearish/rupee-forex keywords already in `build_image_prompt` (fallback bucket for generic market-direction stories) |
| `general`     | none of the above matched |

`ipo` is deliberately **not** a template category — IPO posts never reach
`select_template_pair_smart` at all (they use `ipo_compositor.py`'s fixed
`ipo_alert.png`/`ipo_inner.png`, chosen for that path's high traffic
priority).

**Wiring**: in `core/pipeline.py`, the two/three call sites that currently
pass the pipeline's `category`/`final_category` variable into
`select_template_pair_smart(...)` and `extract_image_text(..., category.upper())`
switch to a freshly computed `classify_template_category(img_title, img_content)`
instead. The `category` variable itself (used for `filter_by_country_and_category`,
i.e. which news gets fetched) is untouched.

## 2. Weekly batch template generation

New module: `content_engine/image_module/template_batch_generator.py`.

- **Model**: `gpt-image-1.5` (not `gpt-image-1` — that model is deprecating
  2026-10-23, and 1.5 is also cheaper per image at the same resolutions).
  Confirmed Batch-API-supported as of Feb 2026 (50% cost discount vs
  synchronous calls).
- **Categories**: the 7 from Section 1 (`finance, general, dividend,
  rbi_policy, gold_oil, tech, banking`).
- **Volume**: `WEEKLY_TEMPLATE_COUNT = 10` (hard cap 15), distributed
  round-robin across the 7 categories. The round-robin start offset rotates
  by ISO week number so the 3 "extra" images (10 % 7) land on different
  categories each week rather than always the same 3.
- **Prompt per template**: the `emotion` / `visual_scene` / `color_mood`
  triple already defined per category in `ai_image_generator.py`, minus the
  per-blog "Title/Context" section (these are generic reusable backgrounds,
  not tied to one article). The `banking` category needs a new triple
  authored in the same style (no existing analogue).
- **Master image size**: `1536x1024` (same as the existing outer-image call
  in `ai_image_generator.py`).
- **Outer/inner derivation — no crop**: contain-fit (preserve aspect, no
  content loss) the master into 640×480 (outer) and into 1920×490 (inner),
  padding the leftover space with a background color derived from that
  template's `color_mood` string (e.g. "rich gold and deep green" → gold;
  falls back to a neutral navy if a mood string doesn't parse to a color).
- **Storage**: `content_engine/templates/<category>/{outer,inner}/ai_<category>_<batchdate>_<idx>.png`.
  The 5 new category folders are created on first successful fetch. Never
  deleted — the pool only grows over time.
- **Descriptions**: each new template gets an entry appended to that
  category's `image_descriptions.json` (reusing the `visual_scene` text as
  the description), so `select_template_pair_smart`'s existing LLM-matching
  picks up new templates immediately with no separate description-generation
  step.

## 3. Scheduling, tracking, and failure handling

**Tracking file**: `output/template_batch_state.json` — single active
record: `{batch_id, submitted_at, category_assignments: [{category, idx,
prompt}], status}`, where `status` is one of `submitted`, `fetched`,
`fetched_via_fallback`, `failed`.

**Two new APScheduler cron jobs in `scheduler.py`**:

- **Saturday ~02:00 IST** → `submit_weekly_batch()`. Builds the 10 prompts
  per Section 2, writes a `.jsonl` batch input file (one
  `/v1/images/generations` request per line per OpenAI's Batch API format),
  uploads it, creates the batch job, records `batch_id` + the category
  assignments (status `submitted`). **Guard**: if the tracking file already
  has an active `submitted` record, skip and log a warning rather than
  starting a second concurrent batch.

- **Monday ~09:00 IST** → `fetch_completed_batch()`. No-op if there's no
  active record. Otherwise checks the batch status once:
  - `completed` → download the output file, run the pad-resize step from
    Section 2 for each image, write files + `image_descriptions.json`
    entries, mark the record `fetched`.
  - `in_progress` / `validating` → log and leave the record as `submitted`
    (picked up again whenever this job next runs).
  - `failed` / `expired` / `cancelled` → **fall back to synchronous
    generation immediately**, re-using the same `category_assignments`
    (and their prompts) already recorded in the tracking file, so the week
    isn't lost entirely. Mark the record `fetched_via_fallback` once done.

No third retry-scheduler job — recovery for a stuck `in_progress` batch is
just "the next time this job runs," and recovery for an outright failure is
the same-run synchronous fallback above.
