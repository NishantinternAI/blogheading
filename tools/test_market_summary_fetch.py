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
