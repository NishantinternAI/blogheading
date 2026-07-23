# Morning Market Summary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a "morning market summary" blog type — built entirely from NSE's public end-of-day archive CSVs (pivot support/resistance for Nifty 50 + Bank Nifty, top gainers/losers, market-wide PCR) — that competes for the priority publishing slot alongside IPO articles.

**Architecture:** A new `sources/market_summary.py` module computes everything from three NSE archive CSVs and returns one structured article dict (no live scraping, no LLM calls in the source layer). A new `generate_market_summary_blog()` function in `generators/blog_generator.py` turns that structured data into the final blog (following the existing `generate_ipo_blog()` pattern — build the prompt directly from `Blog_Title`/`Blog_Content`, no external fetch). `core/pipeline.py` gets three small, additive edits to register the new source as a priority source and route it to the new generator.

**Tech Stack:** Python 3, `requests` (already a dependency), stdlib `csv`/`io`/`datetime` — no new dependencies.

## Global Constraints

- No pytest / test runner in this repo — "tests" are ad-hoc scripts run directly with `python`, matching the existing convention in `tools/test_ipo_blog.py`, `tools/test_title.py`, etc. (per `CLAUDE.md`).
- Support/resistance covers **Nifty 50 and Nifty Bank only** — Sensex was in the original spec draft but corrected out: `ind_close_all` is an NSE-only archive and never contains a Sensex row (verified during planning, see the spec's correction note).
- PCR is **market-wide index-options** (Nifty + Bank Nifty combined), never to be presented as "Nifty PCR" — the generated blog content must state this caveat explicitly.
- Support/resistance and gainers/losers are **required** — if either can't be resolved, `fetch_morning_summary()` returns `[]` (no article this cycle, next pipeline run retries). PCR is **best-effort** — if its archive fails, omit the PCR section, don't block the article.
- Mid-day and closing summaries are explicitly out of scope for this plan.
- All new file paths and existing file line references below were confirmed by reading the actual files during planning (not assumed).

---

### Task 1: Pure calculation functions (pivot levels, top movers, market PCR)

**Files:**
- Create: `sources/market_summary.py` (this task only adds the pure-function section at the top of the file — no network code yet)
- Test: `tools/test_market_summary_calculations.py`

**Interfaces:**
- Produces:
  - `pivot_levels(high: float, low: float, close: float) -> dict` — returns `{"pivot": float, "r1": float, "r2": float, "s1": float, "s2": float}`, each rounded to 2 decimals.
  - `index_pivot_levels(index_rows: list[dict], index_name: str) -> dict | None` — looks up one index's row by name (case/whitespace-insensitive) in NSE `ind_close_all`-shaped rows (`"Index Name"`, `"High Index Value"`, `"Low Index Value"`, `"Closing Index Value"` keys) and returns `pivot_levels(...)`, or `None` if not found/unparseable.
  - `top_movers(bhav_rows: list[dict], min_trades: int = 500, top_n: int = 5) -> tuple[list[dict], list[dict]]` — ranks NSE `sec_bhavdata_full`-shaped rows (`"SERIES"`, `"SYMBOL"`, `"PREV_CLOSE"`, `"CLOSE_PRICE"`, `"NO_OF_TRADES"` keys) by % change, filtered to `SERIES == "EQ"` and `NO_OF_TRADES >= min_trades`. Returns `(gainers, losers)`, each a list of up to `top_n` dicts `{"symbol": str, "prev_close": float, "close": float, "pct_change": float}` — gainers sorted highest-first, losers sorted most-negative-first.
  - `market_pcr(oi_rows: list[dict]) -> float | None` — computes Put OI / Call OI from the `"TOTAL"` row of NSE `fao_participant_oi`-shaped rows (`"Client Type"`, `"Option Index Call Long"`, `"Option Index Put Long"` keys). Returns `None` if the TOTAL row or its numeric fields are missing/unparseable.

- [ ] **Step 1: Write the failing test**

Create `tools/test_market_summary_calculations.py`:

```python
"""
tools/test_market_summary_calculations.py -- pure-function checks for
sources/market_summary.py's pivot/top-movers/PCR calculations. No
network calls; uses fixture rows shaped exactly like NSE's real CSVs.

Run: python tools/test_market_summary_calculations.py
Expected: every line prints "PASS" and nothing raises.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # repo root

from sources.market_summary import pivot_levels, index_pivot_levels, top_movers, market_pcr


def check(label, condition):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label}")
    if not condition:
        raise AssertionError(label)


# ── pivot_levels: real Nifty 50 OHLC from 22-Jul-2026 ──────────────────
# High=24166.3, Low=23961.4, Close=23996.25 (confirmed live against NSE's
# archive during planning)
levels = pivot_levels(high=24166.3, low=23961.4, close=23996.25)
check("pivot ~ 24041.32", abs(levels["pivot"] - 24041.32) < 0.01)
check("r1 ~ 24121.23",    abs(levels["r1"]    - 24121.23) < 0.01)
check("s1 ~ 23916.33",    abs(levels["s1"]    - 23916.33) < 0.01)
check("r2 ~ 24246.22",    abs(levels["r2"]    - 24246.22) < 0.01)
check("s2 ~ 23836.42",    abs(levels["s2"]    - 23836.42) < 0.01)

# ── index_pivot_levels: row lookup, case/whitespace-insensitive ───────
index_rows = [
    {"Index Name": "Nifty 50", "Open Index Value": "24150.45",
     "High Index Value": "24166.3", "Low Index Value": "23961.4",
     "Closing Index Value": "23996.25"},
    {"Index Name": "Nifty Bank", "Open Index Value": "57768.4",
     "High Index Value": "57824", "Low Index Value": "56970.6",
     "Closing Index Value": "57126.8"},
]
nifty = index_pivot_levels(index_rows, "nifty 50")   # lowercase on purpose
check("index_pivot_levels finds Nifty 50 case-insensitively", nifty is not None)
check("index_pivot_levels Nifty 50 pivot matches", abs(nifty["pivot"] - 24041.32) < 0.01)
missing = index_pivot_levels(index_rows, "Sensex")
check("index_pivot_levels returns None for a missing index", missing is None)

# ── top_movers: filters SERIES, min_trades, ranks correctly ───────────
bhav_rows = [
    {"SYMBOL": "GAINALOT", "SERIES": "EQ", "PREV_CLOSE": "100", "CLOSE_PRICE": "110", "NO_OF_TRADES": "1000"},
    {"SYMBOL": "LOSEALOT", "SERIES": "EQ", "PREV_CLOSE": "100", "CLOSE_PRICE": "90",  "NO_OF_TRADES": "1000"},
    {"SYMBOL": "THINLYTRADED", "SERIES": "EQ", "PREV_CLOSE": "100", "CLOSE_PRICE": "150", "NO_OF_TRADES": "10"},  # below min_trades
    {"SYMBOL": "BONDNOTSTOCK", "SERIES": "GS", "PREV_CLOSE": "100", "CLOSE_PRICE": "200", "NO_OF_TRADES": "1000"},  # not EQ
]
gainers, losers = top_movers(bhav_rows, min_trades=500, top_n=5)
check("top_movers excludes thinly-traded rows", all(g["symbol"] != "THINLYTRADED" for g in gainers))
check("top_movers excludes non-EQ series", all(g["symbol"] != "BONDNOTSTOCK" for g in gainers))
check("top_movers top gainer is GAINALOT", gainers[0]["symbol"] == "GAINALOT")
check("top_movers top gainer pct_change ~ 10.0", abs(gainers[0]["pct_change"] - 10.0) < 0.01)
check("top_movers top loser is LOSEALOT", losers[0]["symbol"] == "LOSEALOT")
check("top_movers top loser pct_change ~ -10.0", abs(losers[0]["pct_change"] - (-10.0)) < 0.01)

# ── market_pcr: real TOTAL row from 22-Jul-2026 ────────────────────────
oi_rows = [
    {"Client Type": "Client", "Option Index Call Long": "3016955", "Option Index Put Long": "2004385"},
    {"Client Type": "TOTAL",  "Option Index Call Long": "4697731", "Option Index Put Long": "3945113"},
]
pcr = market_pcr(oi_rows)
check("market_pcr ~ 0.84", pcr is not None and abs(pcr - 0.84) < 0.01)
check("market_pcr returns None with no TOTAL row", market_pcr([{"Client Type": "Client"}]) is None)

print("\nAll checks passed.")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `py tools/test_market_summary_calculations.py`
Expected: `ModuleNotFoundError: No module named 'sources.market_summary'` (the file doesn't exist yet)

- [ ] **Step 3: Write minimal implementation**

Create `sources/market_summary.py`:

```python
"""
sources/market_summary.py -- morning market summary source, built entirely
from NSE's public end-of-day archive CSVs (no live scraping, no anti-bot
session dance). See docs/superpowers/specs/2026-07-23-morning-market-summary-design.md
for the full design rationale and NOTE the Sensex correction there.

Three archives, one trading day at a time:
  - ind_close_all_DDMMYYYY.csv       -> Nifty 50 / Bank Nifty OHLC (pivot levels)
  - sec_bhavdata_full_DDMMYYYY.csv   -> every EQ stock's prev/close (gainers/losers)
  - fao_participant_oi_DDMMYYYY.csv  -> aggregate index-options OI (market PCR)
"""


def pivot_levels(high: float, low: float, close: float) -> dict:
    """
    Classic floor-trader pivot point formula from one trading day's OHLC.

    Returns:
        dict with keys pivot/r1/r2/s1/s2, each a float rounded to 2
        decimal places.
    """
    pivot = (high + low + close) / 3
    r1 = 2 * pivot - low
    s1 = 2 * pivot - high
    r2 = pivot + (high - low)
    s2 = pivot - (high - low)
    return {
        "pivot": round(pivot, 2),
        "r1": round(r1, 2),
        "r2": round(r2, 2),
        "s1": round(s1, 2),
        "s2": round(s2, 2),
    }


def index_pivot_levels(index_rows: list, index_name: str):
    """
    Finds one index's row (case/whitespace-insensitive match on
    "Index Name") in ind_close_all-shaped rows and computes its pivot
    levels from High/Low/Closing Index Value.

    Args:
        index_rows: rows from the ind_close_all_DDMMYYYY.csv archive.
        index_name: index to look up, e.g. "Nifty 50" or "Nifty Bank".

    Returns:
        pivot_levels(...) dict, or None if the index isn't found in
        index_rows or its OHLC fields aren't parseable as floats.
    """
    target = " ".join(index_name.split()).strip().lower()
    for row in index_rows:
        name = " ".join((row.get("Index Name") or "").split()).strip().lower()
        if name != target:
            continue
        try:
            high  = float(row["High Index Value"])
            low   = float(row["Low Index Value"])
            close = float(row["Closing Index Value"])
        except (KeyError, ValueError):
            return None
        return pivot_levels(high, low, close)
    return None


def top_movers(bhav_rows: list, min_trades: int = 500, top_n: int = 5):
    """
    Ranks EQ-series stocks by % change from PREV_CLOSE to CLOSE_PRICE.

    Filters out rows that aren't SERIES == "EQ", have a non-positive
    PREV_CLOSE, or have fewer than min_trades trades (NO_OF_TRADES) --
    this keeps illiquid penny-stock noise out of the gainers/losers list.

    Args:
        bhav_rows: rows from the sec_bhavdata_full_DDMMYYYY.csv archive.
        min_trades: minimum NO_OF_TRADES to be eligible.
        top_n: how many gainers/losers to return.

    Returns:
        (gainers, losers) -- each a list of up to top_n dicts:
        {"symbol": str, "prev_close": float, "close": float, "pct_change": float}.
        gainers sorted highest pct_change first; losers sorted most
        negative pct_change first.
    """
    candidates = []
    for row in bhav_rows:
        if (row.get("SERIES") or "").strip() != "EQ":
            continue
        try:
            prev_close = float(row["PREV_CLOSE"])
            close      = float(row["CLOSE_PRICE"])
            trades     = int(float(row["NO_OF_TRADES"]))
        except (KeyError, ValueError):
            continue
        if prev_close <= 0 or trades < min_trades:
            continue
        pct_change = (close - prev_close) / prev_close * 100
        candidates.append({
            "symbol": (row.get("SYMBOL") or "").strip(),
            "prev_close": prev_close,
            "close": close,
            "pct_change": round(pct_change, 2),
        })

    candidates.sort(key=lambda c: c["pct_change"], reverse=True)
    gainers = candidates[:top_n]
    losers  = list(reversed(candidates[-top_n:]))
    return gainers, losers


def market_pcr(oi_rows: list):
    """
    Computes market-wide index-options Put/Call OI ratio from the
    participant-wise OI archive's TOTAL row.

    NOTE: this is aggregate index-options OI across ALL index contracts
    (Nifty + Bank Nifty combined) -- not a Nifty-only PCR. Callers must
    present it with that caveat, never as "Nifty PCR".

    Args:
        oi_rows: rows from the fao_participant_oi_DDMMYYYY.csv archive.

    Returns:
        Put OI / Call OI as a float rounded to 2 decimals, or None if
        no TOTAL row is found or its OI columns aren't parseable --
        callers should treat None as "omit the PCR section", not as an
        error to propagate.
    """
    for row in oi_rows:
        if (row.get("Client Type") or "").strip().upper() != "TOTAL":
            continue
        try:
            call_oi = float(row["Option Index Call Long"])
            put_oi  = float(row["Option Index Put Long"])
        except (KeyError, ValueError):
            return None
        if call_oi <= 0:
            return None
        return round(put_oi / call_oi, 2)
    return None


if __name__ == "__main__":
    print("Run tools/test_market_summary_calculations.py to check this module's "
          "pure functions, or tools/test_market_summary_fetch.py for the live "
          "network-fetching half (added in a later task).")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `py tools/test_market_summary_calculations.py`
Expected: every `check(...)` line prints `[PASS] ...`, then `All checks passed.` at the end, exit code 0.

- [ ] **Step 5: Commit**

```bash
git add sources/market_summary.py tools/test_market_summary_calculations.py
git commit -m "Add pure pivot/top-movers/PCR calculations for market summary"
```

---

### Task 2: Live archive fetching + trading-day resolution

**Files:**
- Modify: `sources/market_summary.py` (add network-fetching section)
- Test: `tools/test_market_summary_fetch.py`

**Interfaces:**
- Consumes: nothing from Task 1 directly (these are independent network helpers), but Task 3 will consume both.
- Produces:
  - `_fetch_csv(url: str) -> list | None` — GETs a CSV URL, returns parsed rows as `list[dict]` via `csv.DictReader`, or `None` (never raises) on any network/HTTP/parse failure.
  - `resolve_last_trading_day(start: date) -> tuple | None` — steps backward from `start` (exclusive) through up to `MAX_LOOKBACK_DAYS` (7) calendar days, returns `(resolved_date: date, index_rows: list[dict])` for the first date whose `ind_close_all` archive fetches successfully, or `None` if nothing found within the window.
  - Module-level constants `HEADERS`, `INDEX_CLOSE_URL`, `SEC_BHAV_URL`, `PARTICIPANT_OI_URL`, `MAX_LOOKBACK_DAYS` (all `{ddmmyyyy}`-templated URL strings).

- [ ] **Step 1: Write the failing test**

Create `tools/test_market_summary_fetch.py`:

```python
"""
tools/test_market_summary_fetch.py -- live network checks for
sources/market_summary.py's archive-fetching helpers. Hits NSE's real
archive endpoints (same convention as tools/fetch_nse_index_data.py and
tools/test_ipo_blog.py, which also make live calls -- this repo has no
mocking framework).

Run: python tools/test_market_summary_fetch.py
Expected: every line prints "PASS" and nothing raises.
"""

import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # repo root

from sources.market_summary import _fetch_csv, resolve_last_trading_day, INDEX_CLOSE_URL


def check(label, condition):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label}")
    if not condition:
        raise AssertionError(label)


# ── _fetch_csv: known-good date (confirmed live during planning) ──────
rows = _fetch_csv(INDEX_CLOSE_URL.format(ddmmyyyy="22072026"))
check("_fetch_csv returns rows for a known trading day", rows is not None and len(rows) > 0)
check("_fetch_csv rows have Index Name column", "Index Name" in rows[0])

# ── _fetch_csv: a date far enough out that NSE won't have it ───────────
future_rows = _fetch_csv(INDEX_CLOSE_URL.format(ddmmyyyy="01012099"))
check("_fetch_csv returns None for a non-existent date", future_rows is None)

# ── resolve_last_trading_day: Thursday 23-Jul-2026 -> Wednesday 22-Jul-2026 ──
resolved = resolve_last_trading_day(date(2026, 7, 23))
check("resolve_last_trading_day finds a trading day", resolved is not None)
if resolved:
    resolved_date, index_rows = resolved
    check("resolve_last_trading_day resolves to 22-Jul-2026", resolved_date == date(2026, 7, 22))
    check("resolve_last_trading_day returns non-empty index rows", len(index_rows) > 0)

print("\nAll checks passed.")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `py tools/test_market_summary_fetch.py`
Expected: `ImportError: cannot import name '_fetch_csv' from 'sources.market_summary'`

- [ ] **Step 3: Write minimal implementation**

Append to `sources/market_summary.py` (after the pure-function section from Task 1, before the `if __name__ == "__main__":` block — move that block to the end of the file after this new code):

```python
import csv
import io
from datetime import date, timedelta

import requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/csv, */*",
}

INDEX_CLOSE_URL    = "https://archives.nseindia.com/content/indices/ind_close_all_{ddmmyyyy}.csv"
SEC_BHAV_URL       = "https://archives.nseindia.com/products/content/sec_bhavdata_full_{ddmmyyyy}.csv"
PARTICIPANT_OI_URL = "https://archives.nseindia.com/content/nsccl/fao_participant_oi_{ddmmyyyy}.csv"

MAX_LOOKBACK_DAYS = 7


def _fetch_csv(url: str):
    """
    GETs a CSV URL and parses it into a list of row dicts.

    Never raises -- returns None on any network error, non-200 status,
    or parse failure. Callers treat None as "no data for this date"
    (weekend/holiday/not-yet-published), not as an error to propagate.
    """
    try:
        response = requests.get(url, headers=HEADERS, timeout=20)
    except requests.RequestException:
        return None
    if response.status_code != 200:
        return None
    try:
        reader = csv.DictReader(io.StringIO(response.content.decode("utf-8-sig")))
        rows = list(reader)
    except (csv.Error, UnicodeDecodeError):
        return None
    return rows or None


def resolve_last_trading_day(start: date):
    """
    Steps backward from `start` (exclusive) through up to
    MAX_LOOKBACK_DAYS calendar days, returning the first date whose
    index-closing archive fetches successfully -- this is how weekends
    and market holidays get skipped without a separate holiday calendar.

    Args:
        start: the date to step back from (pass date.today() in
            production; a fixed date in tests for determinism).

    Returns:
        (resolved_date, index_rows) for the first date with data, or
        None if nothing was found within MAX_LOOKBACK_DAYS.
    """
    for offset in range(1, MAX_LOOKBACK_DAYS + 1):
        candidate = start - timedelta(days=offset)
        ddmmyyyy = candidate.strftime("%d%m%Y")
        rows = _fetch_csv(INDEX_CLOSE_URL.format(ddmmyyyy=ddmmyyyy))
        if rows:
            return candidate, rows
    return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `py tools/test_market_summary_fetch.py`
Expected: every `check(...)` line prints `[PASS] ...`, then `All checks passed.`, exit code 0.

(If this fails with a network/HTTP error rather than an assertion — e.g. NSE archive layout changed, or an outbound-network-restricted environment — that's a real integration finding, not a code bug in this task; note it and continue, since `tools/fetch_nse_index_data.py` already proved this exact archive is reachable from this machine as of 2026-07-23.)

- [ ] **Step 5: Commit**

```bash
git add sources/market_summary.py tools/test_market_summary_fetch.py
git commit -m "Add live NSE archive fetching + trading-day resolution to market summary source"
```

---

### Task 3: `fetch_morning_summary()` orchestration + Blog_Content builder

**Files:**
- Modify: `sources/market_summary.py` (add orchestration section)
- Test: `tools/test_market_summary_source.py`

**Interfaces:**
- Consumes: everything from Tasks 1 and 2 (`pivot_levels`, `index_pivot_levels`, `top_movers`, `market_pcr`, `_fetch_csv`, `resolve_last_trading_day`, `SEC_BHAV_URL`, `PARTICIPANT_OI_URL`).
- Produces: `fetch_morning_summary() -> list` — the function `core/pipeline.py` will call in Task 5. Returns `[]` on required-data failure, else a single-item list containing one article dict with keys `Blog_Title` (str), `Blog_Content` (str), `Blog_Links` (str), `source` (`"market_summary"`).

- [ ] **Step 1: Write the failing test**

Create `tools/test_market_summary_source.py`:

```python
"""
tools/test_market_summary_source.py -- end-to-end live check of
sources/market_summary.py's fetch_morning_summary(), which is what
core/pipeline.py will actually call. Hits real NSE archives.

Run: python tools/test_market_summary_source.py
Expected: prints the built article dict's Blog_Title and a preview of
Blog_Content, plus "[PASS]" lines, nothing raises.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # repo root

from sources.market_summary import fetch_morning_summary


def check(label, condition):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label}")
    if not condition:
        raise AssertionError(label)


articles = fetch_morning_summary()
check("fetch_morning_summary returns a list", isinstance(articles, list))
check("fetch_morning_summary returns exactly one article", len(articles) == 1)

article = articles[0]
check("article has source=market_summary", article.get("source") == "market_summary")
check("article has a non-empty Blog_Title", bool(article.get("Blog_Title")))
check("article has a non-empty Blog_Content", bool(article.get("Blog_Content")))
check("article has a Blog_Links URL", article.get("Blog_Links", "").startswith("http"))
check("Blog_Content mentions Nifty 50", "Nifty 50" in article["Blog_Content"])
check("Blog_Content mentions Bank Nifty or Nifty Bank", (
    "Bank Nifty" in article["Blog_Content"] or "Nifty Bank" in article["Blog_Content"]
))

print(f"\nBlog_Title: {article['Blog_Title']}")
print(f"\nBlog_Content preview:\n{article['Blog_Content'][:600]}")
print("\nAll checks passed.")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `py tools/test_market_summary_source.py`
Expected: `ImportError: cannot import name 'fetch_morning_summary' from 'sources.market_summary'`

- [ ] **Step 3: Write minimal implementation**

Append to `sources/market_summary.py` (after the Task 2 section, before `if __name__ == "__main__":`):

```python
def _build_blog_content(date_label, nifty_levels, bank_nifty_levels, gainers, losers, pcr):
    """
    Builds the plain-text brief handed to generate_market_summary_blog()
    (not the final blog copy itself) -- field-by-field numbers followed
    by a fixed instruction block, matching the convention
    sources/ipo.py's _build_blog_content() uses for the IPO generator.

    Args:
        date_label: human-readable resolved trading date, e.g. "22 Jul 2026".
        nifty_levels: pivot_levels() dict for Nifty 50.
        bank_nifty_levels: pivot_levels() dict for Nifty Bank.
        gainers: top_movers() gainers list.
        losers: top_movers() losers list.
        pcr: market_pcr() result, or None if unavailable.

    Returns:
        The formatted plain-text brief string (stripped of leading/
        trailing whitespace).
    """
    gainers_lines = "\n".join(
        f"  {i+1}. {g['symbol']}: {g['prev_close']} -> {g['close']} ({g['pct_change']:+.2f}%)"
        for i, g in enumerate(gainers)
    ) or "  None available"
    losers_lines = "\n".join(
        f"  {i+1}. {l['symbol']}: {l['prev_close']} -> {l['close']} ({l['pct_change']:+.2f}%)"
        for i, l in enumerate(losers)
    ) or "  None available"

    pcr_block = (
        f"Market-wide Index Options PCR (Put OI / Call OI, Nifty + Bank Nifty combined): {pcr}\n"
        f"IMPORTANT: this PCR figure is AGGREGATE across all index options -- "
        f"it is NOT a Nifty-only PCR. State this clearly if you mention it; "
        f"never call it \"Nifty PCR\"."
        if pcr is not None else
        "Market-wide Index Options PCR: Not available for this session."
    )

    return f"""
Trading Day    : {date_label} (previous session's close -- NOT live/intraday data)

NIFTY 50 PIVOT LEVELS
  Pivot : {nifty_levels['pivot']}
  R1    : {nifty_levels['r1']}   R2 : {nifty_levels['r2']}
  S1    : {nifty_levels['s1']}   S2 : {nifty_levels['s2']}

NIFTY BANK PIVOT LEVELS
  Pivot : {bank_nifty_levels['pivot']}
  R1    : {bank_nifty_levels['r1']}   R2 : {bank_nifty_levels['r2']}
  S1    : {bank_nifty_levels['s1']}   S2 : {bank_nifty_levels['s2']}

TOP 5 GAINERS ({date_label} session, EQ series, liquid names only):
{gainers_lines}

TOP 5 LOSERS ({date_label} session, EQ series, liquid names only):
{losers_lines}

{pcr_block}

Write a "morning market summary" blog using ONLY the numbers above.
Do not invent any price, level, or percentage not stated here. Explain what
support/resistance pivot levels mean for a retail reader in plain language,
present gainers/losers as a table, and if PCR is available, present it with
its stated caveat exactly as given -- never imply it is Nifty-specific.
Make clear throughout that these are PREVIOUS SESSION closing levels being
used as reference points for today's trading, not live intraday data.
""".strip()


def fetch_morning_summary():
    """
    Builds the morning market summary article from NSE's public
    end-of-day archives. See module docstring / design spec for the
    full data-source rationale.

    Returns:
        [] if support/resistance or gainers/losers data (both
        required) couldn't be resolved. Otherwise a single-item list
        containing one article dict:
        {"Blog_Title", "Blog_Content", "Blog_Links", "source"}.

    PCR is best-effort: if the participant-OI archive fetch/parse
    fails, the PCR section is simply omitted from Blog_Content rather
    than blocking the whole article.
    """
    resolved = resolve_last_trading_day(date.today())
    if resolved is None:
        print("[MARKET SUMMARY] No trading day found within lookback window -- skipping")
        return []
    trade_date, index_rows = resolved
    ddmmyyyy = trade_date.strftime("%d%m%Y")

    nifty_levels      = index_pivot_levels(index_rows, "Nifty 50")
    bank_nifty_levels = index_pivot_levels(index_rows, "Nifty Bank")
    if not nifty_levels or not bank_nifty_levels:
        print(f"[MARKET SUMMARY] Missing Nifty 50/Bank Nifty pivot data for {trade_date} -- skipping")
        return []

    bhav_rows = _fetch_csv(SEC_BHAV_URL.format(ddmmyyyy=ddmmyyyy))
    if not bhav_rows:
        print(f"[MARKET SUMMARY] No bhavcopy data for {trade_date} -- skipping")
        return []
    gainers, losers = top_movers(bhav_rows)

    oi_rows = _fetch_csv(PARTICIPANT_OI_URL.format(ddmmyyyy=ddmmyyyy))
    pcr = market_pcr(oi_rows) if oi_rows else None

    date_label = trade_date.strftime("%d %b %Y")
    title = (
        f"Nifty 50, Bank Nifty Morning Market Summary — Support, Resistance "
        f"& Top Movers ({date_label})"
    )
    content = _build_blog_content(date_label, nifty_levels, bank_nifty_levels, gainers, losers, pcr)

    print(f"[MARKET SUMMARY] Built article for {trade_date}")
    return [{
        "Blog_Title":   title,
        "Blog_Content": content,
        "Blog_Links":   "https://www.nseindia.com/market-data/live-market-indices",
        "source":       "market_summary",
    }]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `py tools/test_market_summary_source.py`
Expected: every `check(...)` line prints `[PASS] ...`, followed by the printed title/content preview, then `All checks passed.`

- [ ] **Step 5: Commit**

```bash
git add sources/market_summary.py tools/test_market_summary_source.py
git commit -m "Add fetch_morning_summary() orchestration to market summary source"
```

---

### Task 4: `generate_market_summary_blog()` in the blog generator

**Files:**
- Modify: `generators/blog_generator.py` (add new function after `generate_ipo_blog`, which ends around line 1292 — insert before the `if __name__ == "__main__":` block at line 1301)
- Test: `tools/test_market_summary_blog.py`

**Interfaces:**
- Consumes: `sources.market_summary.fetch_morning_summary()` (Task 3) for its test fixture; `core.model_client.cached_model_call` (already imported at the top of `blog_generator.py`, line 6/8); `fix_all_fields` (already defined in the same file, line 590).
- Produces: `generate_market_summary_blog(item: dict) -> dict` — same return shape as `generate_blog()`/`generate_ipo_blog()`: `{"Blog_Title", "Meta_Title", "Meta_Description", "TLDR", "Blog_Content", "FAQ_Schema"}`, or `{}` if the model's JSON is unrecoverable.

- [ ] **Step 1: Write the failing test**

Create `tools/test_market_summary_blog.py` (mirrors the existing `tools/test_ipo_blog.py` convention — live LLM call, no mocking):

```python
"""
tools/test_market_summary_blog.py -- exercises the full
fetch_morning_summary() -> generate_market_summary_blog() path for one
run, without touching the live stacks/output files (mirrors the
existing tools/test_ipo_blog.py pattern).

Run: python tools/test_market_summary_blog.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # repo root

from sources.market_summary import fetch_morning_summary
from generators.blog_generator import generate_market_summary_blog

print("=" * 60)
print("  Market Summary Blog Generation Test")
print("=" * 60)

articles = fetch_morning_summary()
assert articles, "fetch_morning_summary() returned no article -- check tools/test_market_summary_source.py first"
item = articles[0]
print(f"\nSource item Blog_Title: {item['Blog_Title']}")

result = generate_market_summary_blog(item)
assert result, "generate_market_summary_blog() returned {} -- check for a JSON parse failure above"

print("\nBlog Title :", result.get("Blog_Title"))
print("Meta Title :", result.get("Meta_Title"))
print("Meta Desc  :", result.get("Meta_Description"))
print("TLDR       :", result.get("TLDR"))
print("\nBlog_Content preview:\n", (result.get("Blog_Content") or "")[:800])
print("\n[PASS] generate_market_summary_blog produced a non-empty result")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `py tools/test_market_summary_blog.py`
Expected: `ImportError: cannot import name 'generate_market_summary_blog' from 'generators.blog_generator'`

- [ ] **Step 3: Write minimal implementation**

In `generators/blog_generator.py`, insert this new function immediately after `generate_ipo_blog()` ends (after line 1292, i.e. right before the blank lines that precede `if __name__ == "__main__":` at line 1301):

```python
def generate_market_summary_blog(item: dict) -> dict:
    """
    Generate an SEO/GEO-optimised blog for a morning market summary item.

    Builds the prompt directly from item["Blog_Title"] / item["Blog_Content"]
    (no external fetch or keyword-volume lookup, same as generate_ipo_blog) --
    the source data is already fully structured by
    sources.market_summary.fetch_morning_summary(). Calls cached_model_call(),
    with a newline-sanitization fallback if the first JSON parse fails.

    Args:
        item: dict expected to contain "Blog_Title" and "Blog_Content"
            (see sources/market_summary.py's fetch_morning_summary()).

    Returns:
        Post-processed blog dict (same shape as generate_blog()/
        generate_ipo_blog()), or {} if the JSON is unrecoverable.
    """
    prompt = f"""
You are a senior financial journalist and SEO strategist writing for Swastika Investmart —
a SEBI-registered Indian stockbroker serving retail investors across India.

You write morning market summary blogs that rank on Google and get cited by AI search
engines like Perplexity and ChatGPT. Retail investors read these first thing before the
market opens to know what to watch.

---

THE SOURCE MATERIAL

{item['Blog_Content']}

---

YOUR MISSION

Turn this data into a blog a retail investor reads over morning coffee before the market
opens. They want to know: where did we close, what levels matter today, which stocks moved
and why it's worth noting, and what the options market is signaling. Every sentence must
earn its place. Never invent a number not present in the source material above.

---

BLOG TITLE

Write a title containing "Nifty 50" or "Bank Nifty" plus the trading date, signaling this
is a same-day-relevant market summary a retail investor would search for each morning.

---

OPENING

Start with the single most useful fact from the source data — the closing level, the key
support/resistance level to watch, or the standout mover. Do not open with a generic
"markets closed mixed yesterday" line with no number in it.

---

BODY STRUCTURE

Each H2 must be a specific, dated question or claim a retail investor would search
("Nifty 50 Support and Resistance Levels for [date]", "Top Gainers and Losers on [date]",
etc.). Cover, using ONLY the numbers given in the source material:

- Nifty 50 and Nifty Bank pivot support/resistance levels, explained in plain language —
  what a pivot, R1/R2, S1/S2 level actually means for a trader watching today's session
- Top 5 gainers and top 5 losers from the previous session, as a table
- Market-wide index-options PCR, if present in the source data, with its stated caveat
  reproduced faithfully (this is an aggregate Nifty+Bank Nifty figure, never call it
  "Nifty PCR" specifically)

Make clear throughout that the levels and movers are from the PREVIOUS session's close,
being used as reference points for today — never imply this is live/intraday data.

---

TLDR

Write exactly 4 short, punchy sentences covering: the previous close, the key level to
watch, the standout mover, and the PCR signal (if available). Each sentence must stand
alone and deliver real information.

---

TABLES

Present the top 5 gainers and top 5 losers as HTML tables — never as a prose list of
tickers and percentages. Use the exact figures from the source material.

---

FAQ

Write 4–6 questions a retail investor would actually search about today's market open.
Every question must be tied to the specific levels/movers/PCR given, not generic
"how does the stock market work" filler. Answers must be grounded in source data only.

---

CONCLUSION

Write 1–2 paragraphs under <h2>Conclusion</h2> — the heading first, paragraphs after.
Tell the investor plainly what to watch for at today's open given yesterday's close and
levels, and end with one concrete, actionable sentence. Plain prose only — never begin a
sentence with "Conclusion:", "Takeaway:", "In summary:", or similar labels.

---

SWASTIKA CONTEXT

Swastika offers: stocks, F&O, mutual funds, IPOs, ETFs, bonds, MCX, SLBM, pledging,
research reports, and Sarthi — an AI stock assistant that gives institutional-level
research on any stock or index to retail investors.

Place one implicit CTA in the body where it genuinely fits. Always format the Sarthi
mention as a clickable hyperlink using exactly this format:
<a href="https://www.swastika.co.in/sarthi" rel="noopener" target="_blank">Swastika's Sarthi AI stock assistant</a>
Never mention Sarthi as plain text — it must always be a hyperlink.

---

SEO OUTPUT REQUIREMENTS

Meta Title: Under 60 characters. Must contain "Nifty 50" or "Bank Nifty" plus a sense of
timeliness (date or "today"). Count the characters.

Meta Description: Under 155 characters. One sentence telling the reader what they'll learn
about today's key levels and movers. Count the characters.

---

HTML RULES

Use only these tags: <h1> <h2> <h3> <h4> <p> <ul> <li> <strong> <u> <a href="">
<table> <tr> <th> <td>

TLDR points go in <li> tags. No paragraph after the closing </ul> of TLDR.
FAQ questions use <h4>. Answers use <p>. No nested <p> tags inside <p> tags.
Tables use <table><tr><th><td> only. No inline styles.
Every major section uses <h2>. Use <h3> only for genuine subsections.

---

MANDATORY BLOG STRUCTURE

Blog_Content must follow this exact section order:

1. <h1> — blog title
2. <h2>TLDR</h2> — followed immediately by <ul> with exactly 4 <li> items, nothing after
3. Opening <p> — the hook paragraph
4. Body <h2> sections — pivot levels, gainers/losers, PCR (if available)
5. <h2>FAQ</h2> — followed by <h4>/<p> pairs, no nested <p> tags
6. <h2>Conclusion</h2> — followed by 1–2 <p> paragraphs, content immediately after the
   heading, never before it, and never left empty

---

OUTPUT

Return only valid JSON. No markdown. No explanation. No code fences.

{{
  "Blog_Title": "",
  "Meta_Title": "",
  "Meta_Description": "",
  "TLDR": ["", "", "", ""],
  "Blog_Content": "",
  "FAQ_Schema": {{
    "@context": "https://schema.org",
    "@type": "FAQPage",
    "mainEntity": []
  }}
}}
"""
    result = cached_model_call(prompt)
    try:
        data = json.loads(result)
    except json.JSONDecodeError as e:
        print(f"[MARKET SUMMARY BLOG] ⚠️  JSON parse failed: {e} — attempting fix...")
        sanitized = result.replace('\r\n', '\\n').replace('\r', '\\n').replace('\n', '\\n')
        try:
            data = json.loads(sanitized)
            print(f"[MARKET SUMMARY BLOG] ✅ JSON recovered — blog content preserved")
        except json.JSONDecodeError as e2:
            print(f"[MARKET SUMMARY BLOG] ❌ JSON unrecoverable: {e2} — skipping article")
            return {}
    source = item.get("source", "")
    data = fix_all_fields(data, source=source)
    return data
```

- [ ] **Step 4: Run test to verify it passes**

Run: `py tools/test_market_summary_blog.py`
Expected: prints the source item's title, then the generated `Blog Title`/`Meta Title`/`Meta Desc`/`TLDR`/content preview, ending with `[PASS] generate_market_summary_blog produced a non-empty result`.

(This makes a real, billed LLM call via `cached_model_call` — same cost/behavior as running `tools/test_ipo_blog.py` or `tools/test_title.py` today.)

- [ ] **Step 5: Commit**

```bash
git add generators/blog_generator.py tools/test_market_summary_blog.py
git commit -m "Add generate_market_summary_blog() for the morning market summary content type"
```

---

### Task 5: Wire the new source into `core/pipeline.py`

**Files:**
- Modify: `core/pipeline.py` (four small, additive edits — line numbers below are from the file as read during planning; re-check them if earlier tasks in this plan shifted line numbers in files you've already touched, though none of those are `pipeline.py` itself)

**Interfaces:**
- Consumes: `sources.market_summary.fetch_morning_summary` (Task 3), `generators.blog_generator.generate_market_summary_blog` (Task 4).
- Produces: nothing new for later tasks — this is the final integration point.

- [ ] **Step 1: Add the import**

In `core/pipeline.py`, find this existing import block around line 56-57:

```python
from sources.fetch_nse_corporate import fetch_nse_corporate
from sources.ipo                 import fetch_nse_ipo
```

Add a new line immediately after it:

```python
from sources.fetch_nse_corporate import fetch_nse_corporate
from sources.ipo                 import fetch_nse_ipo
from sources.market_summary      import fetch_morning_summary
```

- [ ] **Step 2: Register it as a priority source**

Find this line around line 135:

```python
PRIORITY_SOURCES  = ["nse_ipo", "google_trends"]
```

Change it to:

```python
PRIORITY_SOURCES  = ["nse_ipo", "google_trends", "market_summary"]
```

- [ ] **Step 3: Add it to the fetcher list**

Find the `sources` list inside `_fetch_all_sources()` around line 717-727:

```python
    sources = [
        (fetch_nse_ipo,       "nse_ipo"),
        (fetch_google_trends,  "google_trends"),
        (fetch_google_news_business, "google_news_business"),
        (fetch_economic_times,       "economic_times"),
        (fetch_ndtv_profit,        "ndtv_profit"),
        (fetch_zerodha,       "zerodha"),
        (fetch_5paisa,        "5paisa"),
        (fetch_livemint,      "livemint"),
        (fetch_business_standard, "business_standard"),
    ]
```

Add `(fetch_morning_summary, "market_summary")` as a new entry:

```python
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
```

Then find the dispatch logic just below it, around line 729-739:

```python
    for fetcher, source_name in sources:
        try:
            with Timer(f"fetch_{source_name}"):
                if source_name == "nse_ipo":
                    data = fetcher()        # IPO — limited to top_n
                elif source_name == "google_trends":
                    data = fetcher()
                elif source_name == "google_news_business":
                    data = fetcher(top_n=top_n)          # Business news — pass top_n to fetcher
                else:
                    data = fetcher()[:top_n]     # Others — limited to top_n
```

Add a `market_summary` branch (it takes no arguments and returns its own natural count, same as `nse_ipo`/`google_trends`):

```python
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
```

- [ ] **Step 4: Add the generator dispatch branch + timed wrapper**

Find the timed wrapper functions around line 1076-1087:

```python
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
```

Add a third wrapper immediately after:

```python
@timed
def _generate_market_summary_blog(item):
    """Timed wrapper around generators.blog_generator.generate_market_summary_blog(item) —
    used only for priority-stack articles whose source is "market_summary"; builds
    the prompt directly from the structured data fetch_morning_summary() produces,
    same as _generate_ipo_blog does for IPO items."""
    return generate_market_summary_blog(item)
```

This requires `generate_market_summary_blog` to be imported at the top of `core/pipeline.py`. Find this existing import at line 81:

```python
from generators.blog_generator import generate_blog, generate_ipo_blog
```

Change it to:

```python
from generators.blog_generator import generate_blog, generate_ipo_blog, generate_market_summary_blog
```

Then find the dispatch logic around line 1450-1461:

```python
        final_item["_source_type"] = pop_type
        article_source             = final_item.get("source", "")

        if pop_type == "priority" and article_source == "nse_ipo":
            print(f"[BLOG] IPO article (priority + nse_ipo) → generate_ipo_blog")
            print(f"[KEYWORDS] Fetching keyword data from Google...")
            blog_result = clean_newlines(_generate_ipo_blog(final_item))
        else:
            print(f"[BLOG] {pop_type.upper()} article "
                  f"(source={article_source}) → generate_blog")
            print(f"[KEYWORDS] Fetching keyword data from Google...")
            blog_result= clean_newlines(_generate_blog(final_item))
```

Add a third branch:

```python
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
```

No image-step changes are needed: `market_summary` isn't `nse_ipo`, so it falls straight into the existing non-IPO image branches (Branch B/C, AI or template compositor per `USE_AI_IMAGES`), which only read `final_item["Blog_Title"]`/`["Blog_Content"]` — already present on the item this source produces.

- [ ] **Step 5: Smoke-test the wiring**

Run:

```bash
py -c "from core.pipeline import PRIORITY_SOURCES, _fetch_all_sources; print(PRIORITY_SOURCES); import inspect; print('market_summary' in inspect.getsource(_fetch_all_sources))"
```

Expected: prints `['nse_ipo', 'google_trends', 'market_summary']` then `True`, with no import errors (an import error here means one of the new import lines has a typo or the wrong path).

Then run a real dry run against a *copy* of the stack files so a live run doesn't get triggered against production output — do NOT run `run_pipeline()` directly yet:

```bash
py -c "
from core.pipeline import _fetch_all_sources
data = _fetch_all_sources(top_n=6)
summary_articles = [a for a in data if a.get('source') == 'market_summary']
print(f'Total articles fetched: {len(data)}')
print(f'Market summary articles: {len(summary_articles)}')
if summary_articles:
    print('Title:', summary_articles[0]['Blog_Title'])
"
```

Expected: `Market summary articles: 1` (assuming it's a trading day within the lookback window) and the title printed.

- [ ] **Step 6: Commit**

```bash
git add core/pipeline.py
git commit -m "Wire market_summary into the priority stack and blog-generation dispatch"
```

---

### Task 6: Update the architecture doc

**Files:**
- Modify: `docs/architecture.md`

**Interfaces:**
- Consumes: nothing (documentation-only task).
- Produces: nothing (documentation-only task).

- [ ] **Step 1: Add market_summary to the source config table**

`docs/architecture.md` documents `PRIORITY_SOURCES`/stack routing (see the table around the "Three-Stack Priority System" section referenced in this doc's table of contents, and the `stack_priority.json` row currently described as "`nse_ipo` | `ipo_compositor.py` always"). Add a row/note for `market_summary`: routes to the priority stack, uses the normal non-IPO image path (AI or template compositor per `USE_AI_IMAGES`), and its own dedicated `generate_market_summary_blog()` prompt rather than the generic `generate_blog()` — mirroring how the doc already distinguishes `nse_ipo`'s dedicated prompt from everything else's generic one.

- [ ] **Step 2: Commit**

```bash
git add docs/architecture.md
git commit -m "Document market_summary in the priority-stack architecture doc"
```
