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


if __name__ == "__main__":
    print("Run tools/test_market_summary_calculations.py to check this module's "
          "pure functions, or tools/test_market_summary_fetch.py for the live "
          "network-fetching half (added in a later task).")
