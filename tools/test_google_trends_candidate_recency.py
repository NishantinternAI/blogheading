"""
Ad-hoc verification script for sources/google_trends.py's
_pick_best_candidate() recency gate -- run directly with
`python tools/test_google_trends_candidate_recency.py`.

Covers the 2026-07-28 incident: a Google News search for a trending
phrase like "NSE market closed today" can surface a month-old article
(e.g. a 25 Jun Muharram holiday-calendar piece) that still title-overlaps
the phrase. Before this fix, _pick_best_candidate() picked the first
title-overlapping candidate regardless of age, and google_trends_business
is exempt from utils/date_filter.py's freshness check entirely (see that
file's BYPASS_SOURCES comment) -- so a stale article would sail through
and get published as if it were current. _pick_best_candidate() must now
reject any candidate older than MAX_CANDIDATE_AGE_DAYS before applying
the title-overlap check.
"""
from datetime import datetime, timedelta, timezone

from sources.google_trends import _pick_best_candidate, MAX_CANDIDATE_AGE_DAYS

failures = []


def check(label, condition):
    status = "OK" if condition else "FAIL"
    print(f"[{status}] {label}")
    if not condition:
        failures.append(label)


def _rfc2822(dt):
    return dt.strftime("%a, %d %b %Y %H:%M:%S +0000")


now = datetime.now(timezone.utc)
stale_date  = _rfc2822(now - timedelta(days=33))
recent_date = _rfc2822(now - timedelta(hours=5))

# -- a stale but title-relevant candidate must be skipped in favor of a recent one --
best = _pick_best_candidate(
    "NSE market closed today",
    [
        {"title": "NSE market closed today for Muharram holiday", "link": "stale", "pub_date": stale_date, "source": "aajtak"},
        {"title": "Stock market NSE closed today for holiday", "link": "recent", "pub_date": recent_date, "source": "moneycontrol"},
    ],
)
check("picks the recent candidate over an older title-overlapping one",
      best is not None and best["link"] == "recent")

# -- when every title-relevant candidate is stale, must return None, not the stale one --
best_all_stale = _pick_best_candidate(
    "NSE market closed today",
    [
        {"title": "NSE market closed today for Muharram holiday", "link": "stale", "pub_date": stale_date, "source": "aajtak"},
    ],
)
check("returns None when every title-relevant candidate is stale (never falls back to stale content)",
      best_all_stale is None)

# -- an unparseable pub_date is treated as recent (not evidence of staleness) --
best_unparseable = _pick_best_candidate(
    "NSE market closed today",
    [
        {"title": "NSE market closed today update", "link": "unparseable", "pub_date": "not a date", "source": "x"},
    ],
)
check("an unparseable pub_date does not get rejected as stale",
      best_unparseable is not None and best_unparseable["link"] == "unparseable")

check("MAX_CANDIDATE_AGE_DAYS is tight (<=1 day) given trending searches are same-day phenomena",
      MAX_CANDIDATE_AGE_DAYS <= 1)

if failures:
    print(f"\n{len(failures)} FAILURE(S)")
    raise SystemExit(1)
print("\nAll cases passed.")
