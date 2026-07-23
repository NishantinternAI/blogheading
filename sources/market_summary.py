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
        rows = [
            {
                (k.strip() if isinstance(k, str) else k):
                    (v.strip() if isinstance(v, str) else v)
                for k, v in row.items()
            }
            for row in reader
        ]
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

Nifty 50 Pivot Levels
  Pivot : {nifty_levels['pivot']}
  R1    : {nifty_levels['r1']}   R2 : {nifty_levels['r2']}
  S1    : {nifty_levels['s1']}   S2 : {nifty_levels['s2']}

Nifty Bank Pivot Levels
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


if __name__ == "__main__":
    print("Run tools/test_market_summary_calculations.py to check this module's "
          "pure functions, or tools/test_market_summary_fetch.py for the live "
          "network-fetching half (added in a later task).")
