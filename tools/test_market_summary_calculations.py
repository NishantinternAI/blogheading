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
