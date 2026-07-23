"""
tools/fetch_nse_index_data.py -- pull real same-day NSE index closing data
(open/high/low/close, point change, % change) for any index, straight from
NSE's own public archive.

WHY THIS EXISTS
────────────────
2026-07-23 blog review (see blog_review.md): a published market-pulse blog
had "To be announced" placeholders for Nifty Midcap 150 / Smallcap 250 /
Bank / IT / FMCG / Auto in its Close-Level and Point-Change columns, because
the RSS source article the blog was generated from only reported the
%-change for those sectoral indices -- never the absolute levels. Manually
fixing that blog required searching the web for a data source; this file
makes that lookup a one-line call instead of a research task, for both future
manual fixes and (if wired into generate_corporate_blog.py or blog_generator.py
later) a live pipeline source.

NOTE: standalone, NOT wired into the live pipeline yet -- see blog_review.md
2026-07-23 entry, "option (a)" for that decision. Run manually:
    python tools/fetch_nse_index_data.py 22-07-2026
    python tools/fetch_nse_index_data.py 22-07-2026 "Nifty Bank" "Nifty IT"

DATA SOURCE
───────────
https://archives.nseindia.com/content/indices/ind_close_all_DDMMYYYY.csv
NSE's own daily "close price of all indices" archive -- free, public, no
auth, no session/cookie dance (unlike the main nseindia.com site). One CSV
per trading day, going back years. No data on weekends/market holidays.
"""

import csv
import io
import sys
from datetime import datetime

import requests

ARCHIVE_URL = "https://archives.nseindia.com/content/indices/ind_close_all_{date}.csv"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/csv, */*",
}

FIELD_MAP = {
    "Index Name": "index_name",
    "Index Date": "date",
    "Open Index Value": "open",
    "High Index Value": "high",
    "Low Index Value": "low",
    "Closing Index Value": "close",
    "Points Change": "points_change",
    "Change(%)": "pct_change",
    "Volume": "volume",
    "Turnover (Rs. Cr.)": "turnover_cr",
    "P/E": "pe",
    "P/B": "pb",
    "Div Yield": "div_yield",
}


def _normalize(name: str) -> str:
    """Case/whitespace-insensitive key for matching index names."""
    return " ".join(name.split()).strip().lower()


def fetch_index_closing(date) -> dict[str, dict]:
    """
    Downloads NSE's daily "close price of all indices" CSV for one trading
    day and returns every index in it.

    Args:
        date: a trading date as "DD-MM-YYYY" string, or a datetime.date /
              datetime.datetime object.

    Returns:
        dict keyed by the exact NSE index name (e.g. "Nifty Bank"), each
        value a dict with open/high/low/close/points_change/pct_change/
        volume/turnover_cr/pe/pb/div_yield (all as their original string
        values from the CSV -- caller converts to float/Decimal as needed).
        Empty dict if the date has no trading (weekend/holiday) or the
        request fails.

    Raises:
        Nothing -- network/HTTP errors are caught and logged; callers get
        an empty dict rather than an exception, since "no data for this
        date" (weekend/holiday) is an expected, not exceptional, case.
    """
    if isinstance(date, str):
        date_str = date
    else:
        date_str = date.strftime("%d-%m-%Y")

    ddmmyyyy = date_str.replace("-", "")
    url = ARCHIVE_URL.format(date=ddmmyyyy)

    try:
        response = requests.get(url, headers=HEADERS, timeout=20)
    except requests.RequestException as e:
        print(f"[ERROR] NSE index archive fetch failed for {date_str}: {e}")
        return {}

    if response.status_code != 200:
        print(f"[ERROR] NSE index archive HTTP {response.status_code} for {date_str} "
              f"(no trading data for this date, or NSE archive layout changed)")
        return {}

    reader = csv.DictReader(io.StringIO(response.content.decode("utf-8-sig")))
    out = {}
    for row in reader:
        name = (row.get("Index Name") or "").strip()
        if not name:
            continue
        out[name] = {
            FIELD_MAP[k]: v.strip()
            for k, v in row.items()
            if k in FIELD_MAP and k != "Index Name"
        }
    return out


def get_index(date, index_name: str) -> dict | None:
    """
    Convenience wrapper around fetch_index_closing() for a single index,
    matched case/whitespace-insensitively (NSE's own CSV casing is
    inconsistent, e.g. "Nifty Bank" vs "NIFTY Midcap150 Quality 50").

    Returns None if the date has no data or the index name isn't found.
    """
    all_indices = fetch_index_closing(date)
    target = _normalize(index_name)
    for name, data in all_indices.items():
        if _normalize(name) == target:
            return {"index_name": name, **data}
    return None


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        date_str = datetime.now().strftime("%d-%m-%Y")
        names = None
    else:
        date_str = args[0]
        names = args[1:] or None

    if names:
        for n in names:
            result = get_index(date_str, n)
            if result is None:
                print(f"[NOT FOUND] {n!r} on {date_str}")
                continue
            print(f"{result['index_name']:<30} close={result['close']:>12}  "
                  f"points_change={result['points_change']:>10}  "
                  f"pct_change={result['pct_change']:>8}%")
    else:
        all_indices = fetch_index_closing(date_str)
        print(f"{len(all_indices)} indices found for {date_str}\n")
        for name, data in all_indices.items():
            print(f"{name:<45} close={data['close']:>12}  "
                  f"points_change={data['points_change']:>10}  "
                  f"pct_change={data['pct_change']:>8}%")
