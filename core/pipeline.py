"""
pipeline.py — core pipeline orchestrator for Blogheading.

This module owns the end-to-end content pipeline: turning fetched Indian
financial news / NSE IPO filings / corporate-action data into a single
published blog record per run. The live entry point is ``run_pipeline()``
(near the bottom of this file) — it is called every 8 minutes by
``scheduler.py`` in production (see docker-compose.yml / Dockerfile CMD).

High-level flow of ``run_pipeline()``:
    1. Fetch   — pull articles from RSS feeds, Google Trends/News, NSE IPO
                 filings and (when configured) NSE corporate actions.
    2. Filter  — dedupe by normalized title, drop already-published titles,
                 filter by country/category (IPO articles bypass this filter).
    3. Stack   — bucket fresh articles into three on-disk JSON queues
                 (priority / news / corporate) that persist between runs.
    4. Pop     — a fixed posting-pattern rotation (``POSTING_PATTERN``,
                 evaluated by ``decide_pop_type()``) decides which stack to
                 pop an article from on this run.
    5. Generate — call the AI blog generator (IPO articles get a dedicated
                 prompt via ``generate_ipo_blog``), then generate the
                 accompanying image(s) (IPO articles always use
                 ``ipo_compositor.py`` regardless of ``USE_AI_IMAGES``) and
                 the push-notification / Instagram caption text.
    6. Save    — write the finished record to ``output/output.json`` (or
                 ``output/testing_webp_output.json`` when ``USE_AI_IMAGES``
                 is True) via ``storage/save_output.py``, which also doubles
                 as the dedup index for future runs.

Historical note: this file previously carried 5,600+ lines of commented-out
prior pipeline versions above and below the live code block; those dead
blocks have been removed (see git history for the old versions if needed).

See also: ``Blogheading docs·md`` (architecture reference) and
``REVIEW.md`` (known bugs / doc-code mismatches) for deeper context.
"""

import os
import glob
import random
import re
import traceback
import unicodedata
import json
from datetime import datetime
# Change this line
from datetime import datetime

# To this
from datetime import datetime, timezone, timedelta       # ← ADD

# ── RSS Fetchers ──────────────────────────────────────────────
from sources.zerodha             import fetch_zerodha
from sources.cnbc                import fetch_cnbc
from sources.paisa               import fetch_5paisa
from sources.livemint            import fetch_livemint
from sources.fetch_nse_corporate import fetch_nse_corporate
from sources.ipo                 import fetch_nse_ipo
from sources.market_summary      import fetch_morning_summary
from sources.google_trends import fetch_google_trends
from sources.google_news_business import fetch_google_news_business
from sources.economic_times import fetch_economic_times
from sources.ndtv_profit         import fetch_ndtv_profit
from sources.business_standard import fetch_business_standard

# ── Image modules ─────────────────────────────────────────────
from content_engine.image_module.text_extractor import extract_image_text
from content_engine.image_module.template_selector import (
    select_template,
    select_template_pair,
    select_template_pair_smart,
    classify_template_category,
)
from content_engine.image_module.compositor     import compose_image
from content_engine.image_module.ipo_compositor import compose_ipo_image
from content_engine.image_module.validator      import validate_template
from content_engine.image_module.ai_image_generator import generate_ai_image

# ── Utilities & AI ────────────────────────────────────────────
from utils.combined_filter import filter_by_country_and_category
from generators.notify_generator            import generate_notification
from generators.generate_instagram_caption  import generate_instagram_caption
from generators.get_system_timestamp        import get_run_timestamp
from generators.blog_generator import generate_blog, generate_ipo_blog, generate_market_summary_blog
from storage.save_output                import save_output
from utils.timer import timed, Timer, print_timing_summary, reset_timings
from utils.date_filter import filter_fresh_articles


# ══════════════════════════════════════════════════════════════
#  BASE DIRECTORIES
# ══════════════════════════════════════════════════════════════

# pipeline.py lives in core/; the repo root — where output/, output_images/ and
# content_engine/templates/ live — is the PARENT of this file's directory.
# (Was dirname(abspath(__file__)) when this module sat at the repo root; after the
# move into core/ that pointed one level too deep, at /app/core.)
BASE_DIR            = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_IMG_DIR      = os.path.join(BASE_DIR, "output_images")
OUTPUT_IMG_JPG_DIR  = os.path.join(BASE_DIR, "output_images", "jpg_images")
OUTPUT_IMG_WEBP_DIR = os.path.join(BASE_DIR, "output_images", "webp_images")
TIMESTAMP_FILE      = os.path.join(BASE_DIR, "output", "stack_timestamp.json")
PATTERN_INDEX_FILE  = os.path.join(BASE_DIR, "output", "pattern_index.json")

STACK_FILES = {
    "priority":  os.path.join(BASE_DIR, "output", "stack_priority.json"),
    "news":      os.path.join(BASE_DIR, "output", "stack_news.json"),
    "corporate": os.path.join(BASE_DIR, "output", "stack_corporate.json"),
}

# USE_AI_IMAGES is read from the environment (set in docker-compose.yml /
# .env) so app.py (Streamlit dashboard) and this file always agree without
# a manual two-file edit. It switches both which output JSON file is read/
# written (output.json vs testing_webp_output.json) and which image
# generation path (AI generator vs template compositor) run_pipeline() uses.
# Exception: IPO articles always use ipo_compositor.py regardless of this flag.
USE_AI_IMAGES   = os.getenv("USE_AI_IMAGES", "False").strip().lower() in ("1", "true", "yes")
OUTPUT_FILENAME = "testing_webp_output.json" if USE_AI_IMAGES else "output.json"
print(f"[MODE] USE_AI_IMAGES={USE_AI_IMAGES} → saving to output/{OUTPUT_FILENAME}")


# ══════════════════════════════════════════════════════════════
#  POSTING PATTERN CONFIG
# ══════════════════════════════════════════════════════════════

POSTING_PATTERN = [
    "priority",
    "news",
    "priority",
    "corporate",
]


# ══════════════════════════════════════════════════════════════
#  SOURCE CONFIG
# ══════════════════════════════════════════════════════════════

PRIORITY_SOURCES  = ["nse_ipo", "google_trends", "market_summary"]
CORPORATE_SOURCES = []
NEWS_SOURCES      = ["zerodha", "5paisa", "livemint","google_news_business","economic_times","ndtv_profit","business_standard"]


# ══════════════════════════════════════════════════════════════
#  IPO TEMPLATE FINDERS
# ══════════════════════════════════════════════════════════════


def _parse_blog_output(raw: str) -> dict:
    """
    Parses blog generator output into clean dict.

    Handles 3 cases:
      Case 1: Already a dict → return as-is
      Case 2: JSON string    → parse and return
      Case 3: ```json wrapped string → strip and parse

    Always returns a dict — never a string.
    """
    # Case 1 — already parsed dict
    if isinstance(raw, dict):
        return raw

    if not isinstance(raw, str):
        print(f"[BLOG PARSE] Unexpected type: {type(raw)}")
        return {}

    # Case 2 + 3 — strip ```json wrapper if present
    text = raw.strip()

    if text.startswith("```"):
        # Remove ```json or ``` at start
        lines  = text.split("\n")
        lines  = lines[1:]  # remove first line (```json)

        # Remove ``` at end
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        text = "\n".join(lines).strip()

    # Parse JSON
    try:
        data = json.loads(text)
        print(f"[BLOG PARSE] ✅ Parsed successfully")
        return data
    except json.JSONDecodeError as e:
        print(f"[BLOG PARSE] ❌ JSON parse failed: {e}")
        print(f"[BLOG PARSE] Raw (first 200 chars): {text[:200]}")
        return {"Blog_Content": raw, "parse_error": str(e)}
    


def _get_ipo_template_path() -> str:
    """Returns the branded IPO Alert template path (blog outer + instagram), if present.

    `content_engine/templates/ipo_alert.png` is an OPTIONAL branded background.
    It is not shipped in the repo; when absent, the IPO image path falls back to
    smart-template selection + IPO text overlay (see the caller in run_pipeline
    and `_extract_ipo_image_text`), which produces a valid image. To use a branded
    IPO background instead, drop `ipo_alert.png` into `content_engine/templates/`.
    Returns "" when the asset is not present (the documented fallback signal)."""
    ipo_template = os.path.join(
        BASE_DIR, "content_engine", "templates", "ipo_alert.png"
    )
    if os.path.exists(ipo_template):
        print(f"[IPO TEMPLATE] Using branded template: {ipo_template}")
        return ipo_template
    print("[IPO TEMPLATE] Optional ipo_alert.png not present → using smart-template fallback")
    return ""

def _clear_stale_stacks():
    """
    Clears all stack files if they were built on a previous date.
    Ensures stack only contains today's articles.
    Called at start of every pipeline run.
    """
    saved_ts = load_timestamp()
    if not saved_ts:
        return

    try:
        IST          = timezone(timedelta(hours=5, minutes=30))
        now_ist      = datetime.now(IST)
        saved_dt     = datetime.strptime(saved_ts, "%Y-%m-%d %H:%M:%S")
        saved_dt_ist = saved_dt.replace(tzinfo=IST)

        if saved_dt_ist.date() < now_ist.date():
            print(f"[STACK] Stale stack from {saved_dt_ist.date()} "
                  f"— today is {now_ist.date()} → clearing")

            for source_type, path in STACK_FILES.items():
                if os.path.exists(path):
                    with open(path, "w") as f:
                        json.dump([], f)
                    print(f"[STACK] Cleared: {source_type}")

            if os.path.exists(TIMESTAMP_FILE):
                os.remove(TIMESTAMP_FILE)

            print(f"[STACK] All stacks cleared ✅")

    except Exception as e:
        print(f"[STACK] Clear stale check failed: {e}")


def _get_ipo_inner_template_path() -> str:
    """
    Returns the branded IPO Blog Inner template path (1920×490), if present.

    `content_engine/templates/ipo_inner.png` is an OPTIONAL branded asset, not
    shipped in the repo. When absent this falls back to `ipo_alert.png`, and if
    that is also absent the caller uses smart-template selection (see
    `_get_ipo_template_path`). Drop `ipo_inner.png` into `content_engine/templates/`
    to use a dedicated branded inner background.
    """
    ipo_inner = os.path.join(
        BASE_DIR, "content_engine", "templates", "ipo_inner.png"
    )
    if os.path.exists(ipo_inner):
        print(f"[IPO INNER] Using branded template: {ipo_inner}")
        return ipo_inner
    print("[IPO INNER] Optional ipo_inner.png not present → trying ipo_alert.png, else smart-template fallback")
    return _get_ipo_template_path()


# ══════════════════════════════════════════════════════════════
#  IPO IMAGE TEXT EXTRACTOR
#  Fallback when IPO template not found
# ══════════════════════════════════════════════════════════════

def _extract_ipo_image_text(article: dict) -> dict:
    """
    Builds fallback tag/headline/subtext strings for an IPO image overlay.

    Used only when the dedicated ipo_alert.png template can't be found (see
    _get_ipo_template_path) and image text must be composited onto a
    generic smart-selected template instead.

    Args:
        article: IPO article dict — reads company/Blog_Title, open_date,
            listing_date, price_band, lot_size, issue_size, doc_type.

    Returns:
        dict with keys "tag", "headline" (<=6 words), "subtext" (<=10 words).
    """
    company    = article.get("company", article.get("Blog_Title", ""))
    open_date  = article.get("open_date",    "")
    listing    = article.get("listing_date", "")
    price      = article.get("price_band",   "")
    lot        = article.get("lot_size",      "")
    issue_size = article.get("issue_size",   "")
    doc_type   = article.get("doc_type",     "IPO")

    company_short = company\
        .replace(" Limited", "").replace(" Ltd", "")\
        .replace(" (India)", "").strip()

    tag = "IPO"

    if open_date:
        headline = f"{company_short} IPO Opens {open_date}"
    elif doc_type == "RHP":
        headline = f"{company_short} IPO Opening Soon"
    elif doc_type == "PROSP":
        headline = f"{company_short} IPO Prospectus Filed"
    else:
        headline = f"{company_short} Files for IPO"

    words = headline.split()
    if len(words) > 6:
        headline = " ".join(words[:6])

    parts = []
    if price:
        parts.append(f"Price {price}")
    if lot:
        lot_num = lot.replace(" Shares","").replace(" shares","").strip()
        parts.append(f"Lot {lot_num}")
    if listing:
        listing_short = listing\
            .replace("Fri, ","").replace("Mon, ","").replace("Tue, ","")\
            .replace("Wed, ","").replace("Thu, ","").replace("Sat, ","")\
            .replace("Sun, ","").replace(", 2026","").replace(", 2025","")\
            .strip()
        parts.append(f"Listing {listing_short}")
    elif issue_size:
        parts.append(f"Size {issue_size[:10]}")

    subtext = " · ".join(parts) if parts else f"IPO Alert — {doc_type} Filed"
    subtext_words = subtext.split()
    if len(subtext_words) > 10:
        subtext = " ".join(subtext_words[:10])

    result = {"tag": tag, "headline": headline, "subtext": subtext}
    print(f"[IPO IMAGE TEXT] tag={result['tag']} | "
          f"headline={result['headline']} | subtext={result['subtext']}")
    return result


# ══════════════════════════════════════════════════════════════
#  SOURCE CLASSIFIER
# ══════════════════════════════════════════════════════════════

def classify_source(article: dict) -> str:
    """
    Maps an article's "source" field to its stack bucket name.

    Args:
        article: article dict with a "source" key (e.g. "nse_ipo", "zerodha").

    Returns:
        "priority" if source in PRIORITY_SOURCES, "corporate" if in
        CORPORATE_SOURCES, else "news" (the default bucket).
    """
    source = article.get("source", "").lower().strip()
    if source in PRIORITY_SOURCES:
        return "priority"
    if source in CORPORATE_SOURCES:
        return "corporate"
    return "news"


# ══════════════════════════════════════════════════════════════
#  STACK HELPERS
# ══════════════════════════════════════════════════════════════

def save_stack(stack: list, source_type: str):
    """
    Writes a stack (list of article dicts) to its JSON file on disk.

    Args:
        stack: list of article dicts to persist.
        source_type: one of "priority" / "news" / "corporate" — selects the
            path via STACK_FILES.

    Gotcha: overwrites output/stack_<source_type>.json in place (no atomic
    temp-file + os.replace); creates the parent directory if missing.
    """
    path = STACK_FILES[source_type]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(stack, f, ensure_ascii=False, indent=2)
    print(f"[STACK] {source_type:<10} → {len(stack)} articles saved")


def load_stack(source_type: str) -> list:
    """
    Reads one stack's JSON file from disk.

    Args:
        source_type: one of "priority" / "news" / "corporate".

    Returns:
        The stored list of article dicts, or [] if the file doesn't exist
        or fails to parse as JSON.
    """
    path = STACK_FILES[source_type]
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except:
            return []


def load_all_stacks() -> dict:
    """
    Loads all three stacks (priority/news/corporate) from disk and prunes
    stale articles out of each one.

    Gotcha: this mutates state on disk — any stack that loses articles to
    filter_fresh_articles() is immediately re-saved via save_stack(), so
    calling this function can shrink the on-disk queues even before a pop.

    Returns:
        dict mapping "priority"/"news"/"corporate" -> list of article dicts.
    """
    stacks = {t: load_stack(t) for t in STACK_FILES}

    # ── Remove stale articles from loaded stacks ──────────────
    total_before = sum(len(v) for v in stacks.values())

    for source_type in stacks:
        filtered = filter_fresh_articles(stacks[source_type])
        if len(filtered) != len(stacks[source_type]):
            stacks[source_type] = filtered
            save_stack(filtered, source_type)

    total_after = sum(len(v) for v in stacks.values())
    if total_before != total_after:
        print(f"[STACK] Removed {total_before - total_after} "
              f"stale articles from loaded stacks")

    print(f"[STACK] Loaded → Priority:{len(stacks['priority'])} | "
          f"News:{len(stacks['news'])} | Corporate:{len(stacks['corporate'])}")
    return stacks


def total_stack_size(stacks: dict) -> int:
    """Returns the combined article count across all stacks in `stacks`."""
    return sum(len(v) for v in stacks.values())


def save_timestamp():
    """
    Records "now" (local time) as the stack-build timestamp.

    Writes output/stack_timestamp.json with {"stack_built_at": <str>}, used
    by run_pipeline() / _fetch_after_timestamp() to know how far back to
    look when refetching after the stacks run dry.

    Returns:
        The timestamp string that was written ("%Y-%m-%d %H:%M:%S").
    """
    os.makedirs(os.path.dirname(TIMESTAMP_FILE), exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(TIMESTAMP_FILE, "w") as f:
        json.dump({"stack_built_at": ts}, f)
    print(f"[TIMESTAMP] Stack built at: {ts}")
    return ts


def load_timestamp():
    """
    Reads the last stack-build timestamp from output/stack_timestamp.json.

    Returns:
        The stored "stack_built_at" string, or None if the file is missing
        or unparseable.
    """
    if not os.path.exists(TIMESTAMP_FILE):
        return None
    with open(TIMESTAMP_FILE) as f:
        try:
            return json.load(f).get("stack_built_at")
        except:
            return None


# ══════════════════════════════════════════════════════════════
#  PATTERN INDEX
# ══════════════════════════════════════════════════════════════

def load_pattern_index() -> int:
    """
    Reads the current position in POSTING_PATTERN from disk.

    Returns:
        The stored "current_index" int from output/pattern_index.json, or
        0 if the file is missing or unparseable (i.e. start of pattern).
    """
    if not os.path.exists(PATTERN_INDEX_FILE):
        return 0
    with open(PATTERN_INDEX_FILE) as f:
        try:
            return json.load(f).get("current_index", 0)
        except:
            return 0


def save_pattern_index(index: int, source_type: str):
    """
    Persists the next POSTING_PATTERN index to output/pattern_index.json.

    Args:
        index: the next index into POSTING_PATTERN to use on the following run.
        source_type: the stack type that was just popped (stored for
            logging/debugging as "last_type", not read back for logic).

    Gotcha: overwrites the file non-atomically; called from decide_pop_type()
    every time a stack type is chosen, so this is an order-dependent side
    effect — calling decide_pop_type() twice advances the pattern twice.
    """
    os.makedirs(os.path.dirname(PATTERN_INDEX_FILE), exist_ok=True)
    with open(PATTERN_INDEX_FILE, "w") as f:
        json.dump({
            "current_index": index,
            "last_type":     source_type,
            "at":            datetime.now().isoformat()
        }, f)
    print(f"[PATTERN] Saved index={index} last_type={source_type}")


# ══════════════════════════════════════════════════════════════
#  PATTERN-BASED POP DECISION
# ══════════════════════════════════════════════════════════════

def decide_pop_type(stacks: dict) -> str | None:
    """
    Picks which stack to pop from next, per the fixed POSTING_PATTERN rotation.

    Starting at the on-disk pattern index (load_pattern_index()), walks
    POSTING_PATTERN forward (wrapping) until it finds a stack type that
    currently has articles, then advances and saves the index for next time
    (save_pattern_index()) so each call moves the rotation forward exactly
    once when a type is found.

    Args:
        stacks: dict with "priority"/"news"/"corporate" -> list of articles.

    Returns:
        The chosen stack type ("priority"/"news"/"corporate"), or None if
        every stack is empty (in which case the pattern index is left
        untouched).

    Gotcha: has a side effect (advances output/pattern_index.json) whenever
    it successfully picks a type — not a pure query.
    """
    has = {
        "priority":  len(stacks.get("priority",  [])) > 0,
        "news":      len(stacks.get("news",      [])) > 0,
        "corporate": len(stacks.get("corporate", [])) > 0,
    }

    print(f"[POP] Stack sizes → "
          f"Priority:{len(stacks.get('priority',[]))} | "
          f"News:{len(stacks.get('news',[]))} | "
          f"Corporate:{len(stacks.get('corporate',[]))}")

    if not any(has.values()):
        print("[POP] All stacks empty")
        return None

    current_index = load_pattern_index()
    pattern_len   = len(POSTING_PATTERN)
    print(f"[PATTERN] index={current_index} | Pattern={POSTING_PATTERN}")

    for attempt in range(pattern_len):
        idx         = (current_index + attempt) % pattern_len
        wanted_type = POSTING_PATTERN[idx]

        if has[wanted_type]:
            next_index = (idx + 1) % pattern_len
            save_pattern_index(next_index, wanted_type)
            print(f"[PATTERN] idx={idx} → {wanted_type} ✅ → next={next_index}")
            return wanted_type

        print(f"[PATTERN] idx={idx} → {wanted_type} empty, skip")

    return None


# ══════════════════════════════════════════════════════════════
#  DATE PARSER — for IPO oldest-first sorting
# ══════════════════════════════════════════════════════════════

def _parse_published_date(pub_str: str) -> datetime:
    """
    Parses a published-date string (in any of several known feed formats)
    into a datetime, for oldest-first sorting of IPO articles in the
    priority stack (see _pop_article_from_stack).

    Args:
        pub_str: raw published-date string from an article dict.

    Returns:
        Parsed datetime, or datetime.min if empty/unparseable (treated as
        the oldest possible date so malformed dates sort first, not last).
    """
    if not pub_str:
        return datetime.min

    formats = [
        "%d-%b-%Y",
        "%d-%B-%Y",
        "%Y-%m-%d",
        "%d %b, %Y",
        "%d %B, %Y",
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y",
        "%d %b %Y",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(pub_str.strip(), fmt)
        except ValueError:
            continue

    return datetime.min


# ══════════════════════════════════════════════════════════════
#  STEP 4 — ARTICLE SELECTION FROM STACK
# ══════════════════════════════════════════════════════════════

def _pop_article_from_stack(stack: list, pop_type: str) -> tuple:
    """
    Selects and removes one article from a stack.

    Selection rule:
      - "priority" stack containing nse_ipo articles: picks the oldest by
        published date, tiebroken by _stack_index (the order it was added
        to the stack in _build_stacks_from_articles) — non-IPO articles in
        the same stack are ignored for this comparison.
      - Everything else (non-IPO priority, news, corporate): random.choice().

    Args:
        stack: list of article dicts to pop from.
        pop_type: "priority" / "news" / "corporate" — determines the
            selection rule above.

    Returns:
        (selected_article, updated_stack) — updated_stack is a new list
        with the selected article removed (identity-based, via `is not`).
        Returns (None, stack) if the input stack is empty.
    """
    if not stack:
        return None, stack

    ipo_articles = [a for a in stack if a.get("source") == "nse_ipo"]

    if pop_type == "priority" and ipo_articles:
        def sort_key(a):
            """Sort key for IPO articles: (published date, _stack_index) —
            oldest published date first, ties broken by fetch order."""
            published   = _parse_published_date(a.get("published", ""))
            stack_index = a.get("_stack_index", 9999)
            return (published, stack_index)

        ipo_sorted = sorted(ipo_articles, key=sort_key)
        selected   = ipo_sorted[0]

        print(f"[POP] IPO → oldest-first (published + _stack_index)")
        print(f"[POP] Selected   : '{selected.get('Blog_Title','')[:50]}'")
        print(f"[POP] Published  : {selected.get('published',    'N/A')}")
        print(f"[POP] StackIndex : {selected.get('_stack_index', 'N/A')}")

        if len(ipo_articles) > 1:
            print(f"[POP] Skipped {len(ipo_articles)-1} newer IPO article(s):")
            for s in ipo_sorted[1:]:
                print(f"[POP]   · idx={s.get('_stack_index','?')} "
                      f"pub={s.get('published','N/A')} "
                      f"'{s.get('Blog_Title','')[:35]}'")
    else:
        selected = random.choice(stack)
        label = {
            "priority":  "PRIORITY (non-IPO)",
            "news":      "NEWS",
            "corporate": "CORPORATE",
        }.get(pop_type, pop_type.upper())
        print(f"[POP] Random → [{label}]")
        print(f"[POP] Selected : '{selected.get('Blog_Title','')[:50]}'")

    updated_stack = [a for a in stack if a is not selected]
    return selected, updated_stack


# ══════════════════════════════════════════════════════════════
#  FETCH ALL SOURCES
# ══════════════════════════════════════════════════════════════

def _fetch_all_sources(top_n: int = 6) -> list:
    """
    Fetches fresh articles from every configured source in one pass.

    Sources: NSE IPO filings, Google Trends, Google News (business), NSE
    Economic Times, NDTV Profit, Zerodha, 5paisa, Livemint, Business
    Standard. Each fetcher call is individually wrapped in try/except so
    one source failing (e.g. an upstream site down) doesn't abort the rest;
    a failure is logged and that source simply contributes 0 articles.

    Each returned article dict gets a "source" key stamped on it, and the
    combined list is passed through filter_fresh_articles() before being
    added to the running total.

    Args:
        top_n: max articles to keep per source (ignored for nse_ipo and
            google_trends, which return their own natural counts).

    Returns:
        Combined list of article dicts from all sources.

    Gotcha: several RSS fetcher modules fire an HTTP request at *import*
    time (not just when called here) — see REVIEW.md.
    """
    all_data = []

    sources = [
        (fetch_nse_ipo,       "nse_ipo"),
        (fetch_morning_summary, "market_summary"),
        (fetch_google_trends,  "google_trends"),
        (fetch_google_news_business, "google_news_business"),
        (fetch_economic_times,       "economic_times"),
        (fetch_ndtv_profit,        "ndtv_profit"),
        (fetch_zerodha,       "zerodha"),
        (fetch_5paisa,        "5paisa"),
        (fetch_livemint,      "livemint"),
        (fetch_business_standard, "business_standard"),
    ]

    for fetcher, source_name in sources:
        try:
            with Timer(f"fetch_{source_name}"):
                if source_name == "nse_ipo":
                    data = fetcher()        # IPO — limited to top_n
                elif source_name == "market_summary":
                    data = fetcher()        # Market summary — returns 0 or 1 article
                elif source_name == "google_trends":
                    data = fetcher()
                elif source_name == "google_news_business":
                    data = fetcher(top_n=top_n)          # Business news — pass top_n to fetcher
                else:
                    data = fetcher()[:top_n]     # Others — limited to top_n

                for article in data:
                    article["source"] = source_name
                data = filter_fresh_articles(data)
                all_data.extend(data)
                print(f"[FETCH] {source_name:<15} → {len(data)} articles")
        except Exception as e:
            print(f"[FETCH] {source_name} failed: {e}")

    print(f"[FETCH] Total: {len(all_data)}")
    return all_data

# ══════════════════════════════════════════════════════════════
#  BUILD STACKS
# ══════════════════════════════════════════════════════════════

def _build_stacks_from_articles(articles: list) -> dict:
    """
    Dedupes, filters, and buckets a flat article list into the three stacks.

    Steps: (1) drop duplicate titles within `articles` itself (normalized
    via normalize_title), (2) drop titles already present in the output
    file (load_used_titles()), (3) classify each remaining article into
    priority/news/corporate via classify_source(), stamping "_source_type"
    on each article, and adding a "_stack_index" counter (IPO articles
    only) that records fetch order for later oldest-first tiebreaking in
    _pop_article_from_stack().

    Args:
        articles: flat list of article dicts (already source-filtered).

    Returns:
        dict {"priority": [...], "news": [...], "corporate": [...]}.

    Gotcha: side-effecting — overwrites all three stack JSON files on disk
    (save_stack per bucket) and updates output/stack_timestamp.json
    (save_timestamp()) as part of this call, not just building the dict.
    """
    seen_titles     = set()
    unique_articles = []

    for article in articles:
        norm = normalize_title(article.get("Blog_Title", ""))
        if norm not in seen_titles:
            seen_titles.add(norm)
            unique_articles.append(article)
        else:
            print(f"[DEDUP] Removed: {article['Blog_Title'][:50]}")

    print(f"[DEDUP] {len(articles)} → {len(unique_articles)} after stack dedup")

    used_titles = load_used_titles()
    fresh = [
        item for item in unique_articles
        if normalize_title(item.get("Blog_Title", "")) not in used_titles
    ]
    removed = len(unique_articles) - len(fresh)
    if removed:
        print(f"[DEDUP] Removed {removed} already published")
    print(f"[DEDUP] {len(unique_articles)} → {len(fresh)} fresh remain")

    buckets     = {"priority": [], "news": [], "corporate": []}
    ipo_counter = 0

    for article in fresh:
        st = classify_source(article)
        article["_source_type"] = st

        if article.get("source") == "nse_ipo":
            article["_stack_index"] = ipo_counter
            ipo_counter += 1
            print(f"[STACK IDX] IPO #{article['_stack_index']} → "
                  f"'{article.get('Blog_Title','')[:45]}'")

        buckets[st].append(article)

    print(f"\n[STACK BUILD] Priority:{len(buckets['priority'])} | "
          f"News:{len(buckets['news'])} | Corporate:{len(buckets['corporate'])}")

    for st, stack in buckets.items():
        save_stack(stack, st)

    save_timestamp()
    return buckets


# ══════════════════════════════════════════════════════════════
#  FULL FETCH + FETCH AFTER TIMESTAMP
# ══════════════════════════════════════════════════════════════

def _full_fetch_and_build_stack(selected_country: str, category: str) -> dict:
    """
    Cold-start path: fetches from all sources with no timestamp cutoff and
    builds the three stacks from scratch. Used when no prior
    stack_timestamp.json exists (first run ever, or after a reset).

    IPO articles and Google Trends articles bypass/receive separate
    country+category filtering: IPO bypasses entirely; Google Trends is
    filtered for finance category only (already India-scoped via geo=IN);
    all other sources go through filter_by_country_and_category().

    Args:
        selected_country: country to filter non-IPO/non-trends articles by.
        category: category to filter by (e.g. "finance").

    Returns:
        dict of the three stacks (see _build_stacks_from_articles), or
        {"priority": [], "news": [], "corporate": []} if nothing survives
        filtering.

    Gotcha: delegates to _build_stacks_from_articles(), which writes the
    stack JSON files and timestamp file to disk as a side effect.
    """
    print("\n" + "="*50)
    print("  PHASE 1 — BUILDING FRESH STACK")
    print("="*50)

    all_data = _fetch_all_sources(top_n=6)

    # ipo_articles   = [a for a in all_data if a.get("source") == "nse_ipo"]
    # other_articles = [a for a in all_data if a.get("source") != "nse_ipo"]
    ipo_articles = [
    a for a in all_data
    if a.get("source") == "nse_ipo"
    ]

    market_summary_articles = [
    a for a in all_data
    if a.get("source") == "market_summary"
    ]

    google_trends_articles = [
    a for a in all_data
    if a.get("source") == "google_trends"
    ]
    print(
    f"[DEBUG] Finance Google Trends: "
    f"{len(google_trends_articles)}"
    )

    other_articles = [
    a for a in all_data
    if a.get("source") not in ["nse_ipo", "google_trends", "market_summary"]
    ]
    finance_trends, _ = filter_by_country_and_category(
    google_trends_articles,
    selected_country,
    category
    )

    if not finance_trends:
        print(f"[FILTER] No finance trends found in Google Trends today")

    print(f"[FILTER] IPO articles (bypass filter): {len(ipo_articles)}")
    print(f"[FILTER] Market summary articles (bypass filter): {len(market_summary_articles)}")

    filtered_other, source = filter_by_country_and_category(
        other_articles, selected_country, category
    )
    print(f"[FILTER] Other articles after filter: {len(filtered_other)}")

    filtered_data = (
    ipo_articles +
    market_summary_articles +
    finance_trends +
    filtered_other
    )
    print(f"[FILTER] Total combined: {len(filtered_data)}")

    if not filtered_data:
        print("[STACK] No articles after filter!")
        return {"priority": [], "news": [], "corporate": []}

    stacks = _build_stacks_from_articles(filtered_data)
    print("="*50 + "\n")
    return stacks


def _fetch_after_timestamp(
    selected_country: str,
    category: str,
    saved_ts: str
) -> dict:
    """
    Warm-start path: re-fetches from all sources and rebuilds the stacks
    when all three stacks have drained empty but a prior build already
    happened (saved_ts exists). Same fetch/filter/split logic as
    _full_fetch_and_build_stack(), just logged with the reference timestamp.

    Args:
        selected_country: country to filter non-IPO/non-trends articles by.
        category: category to filter by.
        saved_ts: the previous stack-build timestamp (from load_timestamp()),
            used only for logging here — the actual "freshness" cutoff is
            applied by filter_fresh_articles()/the individual fetchers, not
            by this function directly.

    Returns:
        dict of the three stacks, or all-empty stacks if nothing new is
        available yet (caller should retry on the next scheduled run).

    Gotcha: delegates to _build_stacks_from_articles(), which writes stack
    JSON files and the timestamp file to disk as a side effect (only when
    filtered_data is non-empty).
    """
    print(f"\n[STACK EMPTY] Fetching after: {saved_ts}")

    all_data = _fetch_all_sources(top_n=6)

    # ── Split into groups ──────────────────────────────────────
    ipo_articles = [
        a for a in all_data
        if a.get("source") == "nse_ipo"
    ]

    market_summary_articles = [
        a for a in all_data
        if a.get("source") == "market_summary"
    ]

    google_trends_articles = [
        a for a in all_data
        if a.get("source") == "google_trends"
    ]

    other_articles = [
        a for a in all_data
        if a.get("source") not in ["nse_ipo", "google_trends", "market_summary"]
    ]

    print(f"[FILTER] IPO articles (bypass filter)    : {len(ipo_articles)}")
    print(f"[FILTER] Market summary articles (bypass filter) : {len(market_summary_articles)}")
    print(f"[FILTER] Google Trends articles           : {len(google_trends_articles)}")
    print(f"[FILTER] Other articles (to filter)      : {len(other_articles)}")

    # ── Filter google_trends separately ──────────────────────
    # Google Trends is already India-specific (geo=IN)
    # but we still filter for finance category only
    finance_trends, _ = filter_by_country_and_category(
        google_trends_articles, selected_country, category
    )

    if not finance_trends:
        print(f"[FILTER] No finance trends found in Google Trends today")
    print(f"[FILTER] Google Trends after filter      : {len(finance_trends)}")

    # ── Filter other sources normally ────────────────────────
    filtered_other, source = filter_by_country_and_category(
        other_articles, selected_country, category
    )
    print(f"[FILTER] Other articles after filter     : {len(filtered_other)}")

    # ── Combine all groups ─────────────────────────────────────
    filtered_data = ipo_articles + market_summary_articles + finance_trends + filtered_other
    print(f"[FILTER] Total combined                  : {len(filtered_data)}")

    if not filtered_data:
        print("[STACK] No new articles yet — retrying next cycle")
        return {"priority": [], "news": [], "corporate": []}

    return _build_stacks_from_articles(filtered_data)


# ══════════════════════════════════════════════════════════════
#  UTILITY
# ══════════════════════════════════════════════════════════════

def normalize_title(title: str) -> str:
    """Lowercases and collapses whitespace in a title, for dedup comparisons."""
    return re.sub(r'\s+', ' ', title.strip().lower())


def clean_newlines(text):
    """
    Strips literal (escaped) "\\n" / "\\n\\n" sequences out of generated text.

    Args:
        text: any value; non-strings are returned unchanged.

    Returns:
        The cleaned string, or the original value if not a string.
    """
    if not isinstance(text, str):
        return text
    return text.replace('\\n\\n', '').replace('\\n', '')


def clean_filename(text: str) -> str:
    """
    Converts a title into a filesystem-safe filename stem.

    Strips non-ASCII characters (transliterating where possible via NFKD
    normalization), removes filesystem-illegal characters, replaces spaces
    with underscores, and collapses repeated underscores.

    Args:
        text: source string (typically a Blog_Title).

    Returns:
        A safe filename stem, truncated to 60 chars. If ASCII-stripping
        leaves fewer than 3 characters (e.g. an all-regional-language
        title), falls back to a "%Y%m%d_%H%M%S" timestamp instead so image
        filenames never collide or come out empty.
    """
    ascii_text = unicodedata.normalize("NFKD", text)\
                             .encode("ascii", "ignore")\
                             .decode()
    ascii_text = re.sub(r'[\\/*?:"<>|]', '', ascii_text)
    ascii_text = ascii_text.replace(" ", "_")
    ascii_text = re.sub(r'_+', '_', ascii_text).strip("_")

    # Fallback for regional language titles
    # that become empty after ASCII stripping
    if len(ascii_text) < 3:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        print(f"[FILENAME] Regional title → using timestamp: {timestamp}")
        return timestamp

    return ascii_text[:60]


def load_used_titles() -> set:
    """
    Loads the set of already-published (normalized) blog titles, used as
    the dedup index so the same story isn't published twice.

    Reads directly from OUTPUT_FILENAME (output/output.json or
    output/testing_webp_output.json depending on USE_AI_IMAGES) — this file
    doubles as both the published-article store and the dedup index.

    Returns:
        A set of normalize_title() strings, or an empty set if the output
        file doesn't exist or fails to parse.
    """
    filepath = f"output/{OUTPUT_FILENAME}"
    if not os.path.exists(filepath):
        return set()
    with open(filepath, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
            return {normalize_title(item.get("Blog_Title", "")) for item in data}
        except:
            return set()


# ══════════════════════════════════════════════════════════════
#  TIMED WRAPPERS
# ══════════════════════════════════════════════════════════════

@timed
def _generate_blog(item):
    """Timed wrapper around generators.blog_generator.generate_blog(item) — used
    for non-IPO articles (news/corporate/priority-non-IPO)."""
    return generate_blog(item)

@timed
def _generate_ipo_blog(item):          # ← add this
    """Timed wrapper around generators.blog_generator.generate_ipo_blog(item) —
    used only for priority-stack articles whose source is "nse_ipo"; uses a
    dedicated IPO prompt instead of the generic blog prompt."""
    return generate_ipo_blog(item)

@timed
def _generate_market_summary_blog(item):
    """Timed wrapper around generators.blog_generator.generate_market_summary_blog(item) —
    used only for priority-stack articles whose source is "market_summary"; builds
    the prompt directly from the structured data fetch_morning_summary() produces,
    same as _generate_ipo_blog does for IPO items."""
    return generate_market_summary_blog(item)

@timed
def _generate_notification(item):
    """Timed wrapper around generators.notify_generator.generate_notification(item).
    Note: currently unused/commented out in run_pipeline()'s live calls."""
    return generate_notification(item)

@timed
def _generate_instagram(item):
    """Timed wrapper around generators.generate_instagram_caption.generate_instagram_caption(item).
    Note: currently unused/commented out in run_pipeline()'s live calls."""
    return generate_instagram_caption(item)

@timed
def _extract_image_text(title, content, category):
    """Timed wrapper around content_engine.image_module.text_extractor.extract_image_text —
    derives the tag/headline/subtext overlay text for a non-IPO blog image."""
    return extract_image_text(title, content, category)

@timed
def _select_template_pair_smart(category, title, content=""):
    """Timed wrapper around template_selector.select_template_pair_smart —
    picks a matching outer+inner template pair for a given category/title/content."""
    return select_template_pair_smart(category, title, content)


def _imaging_text_source(final_item):
    """Return (title, content) that should drive image overlay text AND template
    selection.

    Prefers the *generated* blog (final_item["blog"] — the SEO article that
    actually gets published) over the raw source snippet (final_item["Blog_Title"]/
    ["Blog_Content"], which is only the pre-generation input). Using the raw
    source made the overlay headline and the chosen template describe a different
    story than the reader sees. Falls back to the raw fields when generation is
    missing or failed to parse (e.g. a parse error leaves no Blog_Title)."""
    blog = final_item.get("blog")
    if not isinstance(blog, dict):
        blog = {}
    title   = blog.get("Blog_Title")   or final_item.get("Blog_Title", "")
    content = blog.get("Blog_Content") or final_item.get("Blog_Content", "")
    return title, content

@timed
def _compose_image(template, image_text, jpg_path, webp_path, image_type):
    """
    Timed wrapper around content_engine.image_module.compositor.compose_image.

    Renders `image_text` onto `template` and writes both a .jpg and .webp
    copy to the given paths.

    Args:
        template: path to the background template image.
        image_text: dict of overlay text (tag/headline/subtext), or {} for
            templates with no text (e.g. blog_inner).
        jpg_path: output path for the .jpg render.
        webp_path: output path for the .webp render.
        image_type: one of "blog" / "blog_inner" / "instagram" — controls
            the compositor's crop/layout for that slot.

    Gotcha: writes files to disk at jpg_path/webp_path (overwrites if present).
    """
    return compose_image(
        template, image_text, jpg_path, webp_path,
        image_type=image_type
    )

@timed
def _compose_ipo_image(template, article, jpg_path, webp_path, image_type):
    """
    Timed wrapper around content_engine.image_module.ipo_compositor.compose_ipo_image.

    Same contract as _compose_image(), but reads IPO-specific fields
    (open_date, price_band, lot_size, etc.) directly off `article` for the
    ipo_alert.png / ipo_inner.png template zones.

    Gotcha: writes files to disk at jpg_path/webp_path (overwrites if present).
    """
    return compose_ipo_image(
        template, article, jpg_path, webp_path,
        image_type=image_type
    )

@timed
def _generate_ai_image(
    blog_title, blog_content,
    blog_outer_paths, blog_inner_paths,
    instagram_paths, quality="medium"
):
    """
    Timed wrapper around content_engine.image_module.ai_image_generator.generate_ai_image.

    Used only for non-IPO articles when USE_AI_IMAGES is True (IPO articles
    always use _compose_ipo_image() regardless of this flag).

    Args:
        blog_title: article's Blog_Title, used as the image generation prompt seed.
        blog_content: article body text, additional generation context.
        blog_outer_paths / blog_inner_paths / instagram_paths: each a dict
            {"jpg": <path>, "webp": <path>} for that image slot's output files.
        quality: image generation quality setting passed through to the
            underlying AI image generator.

    Returns:
        dict with keys "blog_outer", "blog_inner", "instagram" mapping to
        whatever generate_ai_image() returns per slot (e.g. saved paths).

    Gotcha: makes an external (paid) AI image generation API call and
    writes files to disk at the given paths.
    """
    return generate_ai_image(
        blog_title, blog_content,
        blog_outer_paths, blog_inner_paths,
        instagram_paths, quality
    )

@timed
def _save_output(item, filename):
    """
    Timed wrapper around storage.save_output.save_output(item, filename=filename).

    Args:
        item: the finished article dict to persist.
        filename: target output file (OUTPUT_FILENAME — output.json or
            testing_webp_output.json).

    Returns:
        Whatever save_output() returns — truthy if saved, falsy if skipped
        (e.g. duplicate already present).

    Gotcha: writes output/<filename> non-atomically (no temp-file +
    os.replace); this file also serves as the dedup index read by
    load_used_titles().
    """
    return save_output(item, filename=filename)


# ══════════════════════════════════════════════════════════════
#  MAIN PIPELINE
# ══════════════════════════════════════════════════════════════

def run_pipeline(selected_country="India", category="finance"):
    """
    Runs one full cycle of the content pipeline and returns 0 or 1 finished
    article. This is the live entry point, called every 8 minutes by
    scheduler.py in production.

    Flow: fetch -> filter -> stack -> pop -> generate blog -> generate
    image -> save.
        1. Clears any stack left over from a previous calendar day
           (_clear_stale_stacks) and loads the three on-disk stacks
           (load_all_stacks).
        2. If all stacks are empty, rebuilds them by fetching fresh articles
           (first run: _full_fetch_and_build_stack; subsequent empty-stack
           runs: _fetch_after_timestamp). If still empty after that, falls
           back to picking a random fresh Zerodha article directly (bypassing
           the stack/pattern system entirely) so the pipeline never goes
           fully idle.
        3. Picks which stack to pop from next via the fixed POSTING_PATTERN
           rotation (decide_pop_type) and pops one article from it
           (_pop_article_from_stack), persisting the updated stack.
        4. Runs a duplicate-title safety check against already-published
           titles (load_used_titles) before doing any generation work.
        5. Generates the blog body — IPO articles (priority stack,
           source == "nse_ipo") use the dedicated IPO prompt
           (_generate_ipo_blog); everything else uses the generic blog
           prompt (_generate_blog). Parses the raw model output
           (_parse_blog_output) and lifts out primary/secondary keywords.
        6. Generates images: IPO articles always go through
           _compose_ipo_image (ipo_alert.png / ipo_inner.png), regardless of
           USE_AI_IMAGES. Non-IPO articles use _generate_ai_image when
           USE_AI_IMAGES is True, or _compose_image with a smart-selected
           template pair otherwise.
        7. Saves the finished article dict to OUTPUT_FILENAME via
           _save_output, appending it to the returned results list only if
           it wasn't a duplicate.

    Args:
        selected_country: country filter applied to non-IPO/non-trends
            articles when (re)building stacks.
        category: category filter (e.g. "finance") applied the same way,
            and used to select image templates.

    Returns:
        A list containing zero or one article dict — empty when nothing
        was available, a duplicate was hit, blog generation returned
        empty, or an exception was caught mid-generation (logged, not raised).

    Gotchas:
        - Reads and writes several JSON files as side effects: all three
          stack_*.json files, pattern_index.json, stack_timestamp.json, and
          the OUTPUT_FILENAME output file — none of these writes are atomic.
        - The image-generation branch order is load-bearing: the IPO check
          is evaluated first specifically so IPO articles are unaffected by
          USE_AI_IMAGES.
        - Generation exceptions are caught and logged but swallow the
          result silently (returns whatever was accumulated in `results`,
          typically []) rather than propagating.
    """
    reset_timings()
    os.makedirs(OUTPUT_IMG_DIR,      exist_ok=True)
    os.makedirs(OUTPUT_IMG_JPG_DIR,  exist_ok=True)
    os.makedirs(OUTPUT_IMG_WEBP_DIR, exist_ok=True)
    results = []

    # ── Clear stale stacks from previous day ──────────────────
    _clear_stale_stacks()

    # ══════════════════════════════════════════════════════════
    # STEP 1 — Load all 3 stacks from disk
    # ══════════════════════════════════════════════════════════
    stacks = load_all_stacks()

    # ══════════════════════════════════════════════════════════
    # STEP 2 — Rebuild stacks if all empty
    # ══════════════════════════════════════════════════════════
    if total_stack_size(stacks) == 0:
        saved_ts = load_timestamp()

        if saved_ts is None:
            print("[STACK] First run — full fetch...")
            stacks = _full_fetch_and_build_stack(selected_country, category)
        else:
            print(f"[STACK] All empty — fetching after: {saved_ts}")
            stacks = _fetch_after_timestamp(selected_country, category, saved_ts)

        if total_stack_size(stacks) == 0:
            print("[WAITING] No new articles — fallback Zerodha...")

            zerodha_data = fetch_zerodha()
            if not zerodha_data:
                print("[FALLBACK] Zerodha also empty — aborting")
                return []

            used_titles   = load_used_titles()
            fresh_zerodha = [
                a for a in zerodha_data
                if normalize_title(a.get("Blog_Title", "")) not in used_titles
            ]
            if not fresh_zerodha:
                print("[FALLBACK] All Zerodha articles already published — aborting")
                return []
            print(
                f"[FALLBACK] {len(zerodha_data)} fetched → "
                f"{len(fresh_zerodha)} fresh after dedup"
            )

            final_item                 = random.choice(fresh_zerodha)
            final_item["source"]       = "zerodha"
            final_item["_source_type"] = "news"
            final_item["source_type"]  = "news"
            print(f"[FALLBACK] Selected: '{final_item.get('Blog_Title','')[:50]}'")

            # Fallback always uses standard blog generator (zerodha = news)
            print(f"[BLOG] FALLBACK news article → generate_blog")
            print(f"[KEYWORDS] Fetching keyword data from Google...")
            blog_result          = clean_newlines(generate_blog(final_item))
            if not blog_result:
                print(f"[PIPELINE] ⚠️  Blog generation returned empty — "
                  f"skipping article: '{final_item.get('Blog_Title','')[:60]}'")
                return []
            final_item["blog"] = blog_result
            # final_item["notify"]           = clean_newlines(generate_notification(final_item))
            # final_item["instagram_notify"] = clean_newlines(generate_instagram_caption(final_item))
            final_item["Run_Timestamp"]    = get_run_timestamp()
            final_item["blog"]             = _parse_blog_output(final_item["blog"])
            blog_dict = final_item.get("blog", {})
            if isinstance(blog_dict, dict):
                final_item["primary_keyword"]    = blog_dict.pop("primary_keyword", {})
                final_item["secondary_keywords"] = blog_dict.pop("secondary_keywords", [])

            safe_title = clean_filename(final_item["Blog_Title"])
            img_title, img_content = _imaging_text_source(final_item)
            template_category = classify_template_category(img_title, img_content)
            image_text = extract_image_text(
                img_title,
                img_content,
                template_category.upper()
            )
            final_item["image_text"] = image_text

            template_pair  = select_template_pair_smart(
                template_category,
                img_title,
                img_content
            )
            outer_template = template_pair["outer"]
            inner_template = template_pair["inner"]

            final_item["blog_image"] = compose_image(
                outer_template, image_text,
                os.path.join(OUTPUT_IMG_JPG_DIR,  f"blog_{safe_title}.jpg"),
                os.path.join(OUTPUT_IMG_WEBP_DIR, f"blog_{safe_title}.webp"),
                image_type="blog"
            )
            final_item["blog_image_inner"] = compose_image(
                inner_template, {},
                os.path.join(OUTPUT_IMG_JPG_DIR,  f"blog_inner_{safe_title}.jpg"),
                os.path.join(OUTPUT_IMG_WEBP_DIR, f"blog_inner_{safe_title}.webp"),
                image_type="blog_inner"
            )
            # final_item["instagram_image"] = compose_image(
            #     outer_template, image_text,
            #     os.path.join(OUTPUT_IMG_JPG_DIR,  f"insta_{safe_title}.jpg"),
            #     os.path.join(OUTPUT_IMG_WEBP_DIR, f"insta_{safe_title}.webp"),
            #     image_type="instagram"
            # )
            save_output(final_item, filename=OUTPUT_FILENAME)
            return [final_item]

    # ══════════════════════════════════════════════════════════
    # STEP 3 — Decide which stack to pop (pattern-based)
    # ══════════════════════════════════════════════════════════
    pop_type = decide_pop_type(stacks)

    if pop_type is None:
        print("[STACK] All stacks empty — nothing to process")
        return []

    # ══════════════════════════════════════════════════════════
    # STEP 4 — Select article from chosen stack
    # ══════════════════════════════════════════════════════════
    chosen_stack          = stacks[pop_type]
    final_item, new_stack = _pop_article_from_stack(chosen_stack, pop_type)

    stacks[pop_type] = new_stack
    save_stack(new_stack, pop_type)

    print(f"\n[POPPED]  [{pop_type.upper()}] "
          f"{final_item.get('Blog_Title', '')[:60]}")
    print(f"[STACK]   Priority:{len(stacks['priority'])} | "
          f"News:{len(stacks['news'])} | "
          f"Corporate:{len(stacks['corporate'])}")

    # ══════════════════════════════════════════════════════════
    # STEP 5 — Duplicate check (safety net)
    # ══════════════════════════════════════════════════════════
    used_titles = load_used_titles()
    if normalize_title(final_item.get("Blog_Title", "")) in used_titles:
        print("[SKIPPED] Already published — next cycle will retry")
        return []

    print(f"[SELECTED] [{pop_type.upper()}] "
          f"{final_item.get('Blog_Title', '')[:50]}")

    try:
        # ══════════════════════════════════════════════════════
        # STEP 6 — Generate blog + notification + instagram (AI)
        #
        # BLOG GENERATOR ROUTING:
        #   IPO  (priority + nse_ipo)    → generate_ipo_blog
        #   NEWS (news sources)          → generate_blog
        #   CORPORATE (nse_corporate)    → generate_blog
        #   PRIORITY non-IPO             → generate_blog
        #                                  (e.g. google_trends)
        #
        # WHY double condition for IPO:
        #   PRIORITY_SOURCES contains both nse_ipo and google_trends.
        #   google_trends priority articles must use generate_blog,
        #   not the IPO prompt. Only nse_ipo gets generate_ipo_blog.
        # ══════════════════════════════════════════════════════
        final_item["_source_type"] = pop_type
        article_source             = final_item.get("source", "")

        if pop_type == "priority" and article_source == "nse_ipo":
            print(f"[BLOG] IPO article (priority + nse_ipo) → generate_ipo_blog")
            print(f"[KEYWORDS] Fetching keyword data from Google...")
            blog_result = clean_newlines(_generate_ipo_blog(final_item))
        elif pop_type == "priority" and article_source == "market_summary":
            print(f"[BLOG] Market summary article (priority + market_summary) → generate_market_summary_blog")
            blog_result = clean_newlines(_generate_market_summary_blog(final_item))
        else:
            print(f"[BLOG] {pop_type.upper()} article "
                  f"(source={article_source}) → generate_blog")
            print(f"[KEYWORDS] Fetching keyword data from Google...")
            blog_result= clean_newlines(_generate_blog(final_item))

        if not blog_result:
            print(f"[PIPELINE] ⚠️  Blog generation returned empty — "
                  f"skipping article: '{final_item.get('Blog_Title','')[:60]}'")
            return []
        
        final_item["blog"] = blog_result

        # final_item["notify"]           = clean_newlines(_generate_notification(final_item))
        # final_item["instagram_notify"] = clean_newlines(_generate_instagram(final_item))
        final_item["Run_Timestamp"]    = get_run_timestamp()
        final_item["source_type"]      = pop_type
        final_item["blog"]             = _parse_blog_output(final_item["blog"])

        blog_dict = final_item.get("blog", {})
        if isinstance(blog_dict, dict):
            final_item["primary_keyword"]    = blog_dict.pop("primary_keyword", {})
            final_item["secondary_keywords"] = blog_dict.pop("secondary_keywords", [])

        safe_title = clean_filename(final_item["Blog_Title"])

        # File paths — shared by all image branches
        blog_jpg_path        = os.path.join(OUTPUT_IMG_JPG_DIR,  f"blog_{safe_title}.jpg")
        blog_webp_path       = os.path.join(OUTPUT_IMG_WEBP_DIR, f"blog_{safe_title}.webp")
        blog_inner_jpg_path  = os.path.join(OUTPUT_IMG_JPG_DIR,  f"blog_inner_{safe_title}.jpg")
        blog_inner_webp_path = os.path.join(OUTPUT_IMG_WEBP_DIR, f"blog_inner_{safe_title}.webp")
        insta_jpg_path       = os.path.join(OUTPUT_IMG_JPG_DIR,  f"insta_{safe_title}.jpg")
        insta_webp_path      = os.path.join(OUTPUT_IMG_WEBP_DIR, f"insta_{safe_title}.webp")

        # ══════════════════════════════════════════════════════
        # STEP 7 — Generate images
        #
        # ORDER OF CHECKS (critical):
        #   1st: IPO article? → ALWAYS ipo_compositor (ignores USE_AI_IMAGES)
        #   2nd: USE_AI_IMAGES? → AI generation for non-IPO
        #   3rd: else → template compositor for non-IPO
        #
        # WHY IPO IS FIRST:
        #   USE_AI_IMAGES=True was causing IPO articles to use
        #   OpenAI image generation instead of the IPO Alert template.
        #   IPO articles MUST always use ipo_compositor regardless
        #   of the USE_AI_IMAGES flag.
        # ══════════════════════════════════════════════════════

        # ── BRANCH A: IPO article — ALWAYS template ───────────
        if pop_type == "priority" and article_source == "nse_ipo":
            print(f"[IMAGE] IPO article → ipo_compositor.py "
                  f"(always template, ignores USE_AI_IMAGES)")

            ipo_template       = _get_ipo_template_path()
            ipo_inner_template = _get_ipo_inner_template_path()

            if ipo_template:
                print(f"[IMAGE] Blog outer  (640×480)   + IPO zone values")
                final_item["blog_image"] = _compose_ipo_image(
                    ipo_template, final_item,
                    blog_jpg_path, blog_webp_path, "blog"
                )

                print(f"[IMAGE] Blog inner  (1920×490)  — dedicated template")
                final_item["blog_image_inner"] = _compose_ipo_image(
                    ipo_inner_template, final_item,
                    blog_inner_jpg_path, blog_inner_webp_path, "blog_inner"
                )

                # print(f"[IMAGE] Instagram   (1080×1080) + IPO zone values")
                # final_item["instagram_image"] = _compose_ipo_image(
                #     ipo_template, final_item,
                #     insta_jpg_path, insta_webp_path, "instagram"
                # )
            else:
                # Fallback: ipo_alert.png missing
                print(f"[IMAGE] IPO fallback → smart template + text overlay")
                ipo_text      = _extract_ipo_image_text(final_item)
                _ipo_img_title, _ipo_img_content = _imaging_text_source(final_item)
                _ipo_template_category = classify_template_category(_ipo_img_title, _ipo_img_content)
                template_pair = _select_template_pair_smart(
                    _ipo_template_category,
                    _ipo_img_title,
                    _ipo_img_content
                )
                final_item["blog_image"] = _compose_image(
                    template_pair["outer"], ipo_text,
                    blog_jpg_path, blog_webp_path, "blog"
                )
                final_item["blog_image_inner"] = _compose_image(
                    template_pair["inner"], {},
                    blog_inner_jpg_path, blog_inner_webp_path, "blog_inner"
                )
                # final_item["instagram_image"] = _compose_image(
                #     template_pair["outer"], ipo_text,
                #     insta_jpg_path, insta_webp_path, "instagram"
                # )

            final_item["image_text"] = _extract_ipo_image_text(final_item)

        # ── BRANCH B: non-IPO + USE_AI_IMAGES=True ───────────
        elif USE_AI_IMAGES:
            print(f"[IMAGE MODE] AI images → {OUTPUT_FILENAME}")
            images = _generate_ai_image(
                final_item["Blog_Title"],
                final_item.get("Blog_Content", ""),
                blog_outer_paths={
                    "jpg":  os.path.join(OUTPUT_IMG_JPG_DIR,  f"blog_outer_{safe_title}.jpg"),
                    "webp": os.path.join(OUTPUT_IMG_WEBP_DIR, f"blog_outer_{safe_title}.webp"),
                },
                blog_inner_paths={
                    "jpg":  os.path.join(OUTPUT_IMG_JPG_DIR,  f"blog_inner_{safe_title}.jpg"),
                    "webp": os.path.join(OUTPUT_IMG_WEBP_DIR, f"blog_inner_{safe_title}.webp"),
                },
                instagram_paths={
                    "jpg":  os.path.join(OUTPUT_IMG_JPG_DIR,  f"insta_{safe_title}.jpg"),
                    "webp": os.path.join(OUTPUT_IMG_WEBP_DIR, f"insta_{safe_title}.webp"),
                },
                quality="medium"
            )
            final_item["blog_image_outer"] = images["blog_outer"]
            final_item["blog_image_inner"] = images["blog_inner"]
            final_item["instagram_image"]  = images["instagram"]

        # ── BRANCH C: non-IPO + USE_AI_IMAGES=False ──────────
        else:
            print(f"[IMAGE] {pop_type.upper()} "
                  f"(source={article_source}) → compositor.py")

            img_title, img_content = _imaging_text_source(final_item)
            template_category = classify_template_category(img_title, img_content)

            final_item["image_text"] = _extract_image_text(
                img_title,
                img_content,
                template_category.upper()
            )

            template_pair  = _select_template_pair_smart(
                template_category,
                img_title,
                img_content
            )
            outer_template = template_pair["outer"]
            inner_template = template_pair["inner"]

            print(f"[IMAGE] Blog outer  → {os.path.basename(outer_template)}")
            final_item["blog_image"] = _compose_image(
                outer_template, final_item["image_text"],
                blog_jpg_path, blog_webp_path, "blog"
            )
            print(f"[IMAGE] Blog inner  → {os.path.basename(inner_template)}")
            final_item["blog_image_inner"] = _compose_image(
                inner_template, {},
                blog_inner_jpg_path, blog_inner_webp_path, "blog_inner"
            )
            # print(f"[IMAGE] Instagram   → {os.path.basename(outer_template)}")
            # final_item["instagram_image"] = _compose_image(
            #     outer_template, final_item["image_text"],
            #     insta_jpg_path, insta_webp_path, "instagram"
            # )

        # ══════════════════════════════════════════════════════
        # STEP 8 — Save to output file
        # ══════════════════════════════════════════════════════
        saved = _save_output(final_item, OUTPUT_FILENAME)

        if saved:
            results.append(final_item)
            print(f"[DONE] [{pop_type.upper()}] Saved → output/{OUTPUT_FILENAME}")
            print(f"[DONE] {final_item['Blog_Title'][:60]}")
        else:
            print(f"[SKIPPED] Already exists: {final_item['Blog_Title'][:60]}")

    except Exception as e:
        print(f"[ERROR] {e}")
        traceback.print_exc()

    print_timing_summary()
    return results
