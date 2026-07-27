# utils/date_filter.py

import re
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime


# ══════════════════════════════════════════════════════════════
#  CONFIG
#  Accept articles published between:
#    Today 12:00 AM IST → Today 6:00 PM IST
# ══════════════════════════════════════════════════════════════

IST = timezone(timedelta(hours=5, minutes=30))

WINDOW_START_HOUR = 0   # 12:00 AM
WINDOW_END_HOUR   = 18  # 6:00 PM


# ══════════════════════════════════════════════════════════════
#  BYPASS SOURCES — always pass regardless of date
# ══════════════════════════════════════════════════════════════

BYPASS_SOURCES = {"nse_ipo", "nse_corporate", "market_summary", "google_trends_business"}


# ══════════════════════════════════════════════════════════════
#  PARSE DATE
# ══════════════════════════════════════════════════════════════

def _parse_date(date_str: str) -> datetime | None:
    """Parses article date string → timezone aware datetime."""
    if not date_str:
        return None

    date_str = date_str.strip()

    # Method 1 — RSS standard format
    # "Thu, 04 Jun 2026 14:59:20 +0530"
    try:
        dt = parsedate_to_datetime(date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        pass

    # Method 2 — ISO format
    # "2026-06-04T14:59:20+05:30"
    try:
        dt = datetime.fromisoformat(date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        pass

    # Method 3 — Simple date formats
    formats = [
        "%d-%b-%Y",
        "%d-%B-%Y",
        "%Y-%m-%d",
        "%d %b, %Y",
        "%d %b %Y",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue

    return None


# ══════════════════════════════════════════════════════════════
#  GET TODAY'S WINDOW IN IST
# ══════════════════════════════════════════════════════════════

def _get_today_window() -> tuple:
    """
    Returns (window_start, window_end) in IST for today.

    Example on 04 Jun 2026:
      window_start = 04 Jun 2026 00:00:00 IST
      window_end   = 04 Jun 2026 18:00:00 IST
    """
    now_ist = datetime.now(IST)
    today   = now_ist.date()

    window_start = datetime(
        today.year, today.month, today.day,
        WINDOW_START_HOUR, 0, 0,
        tzinfo=IST
    )
    window_end = datetime(
        today.year, today.month, today.day,
        WINDOW_END_HOUR, 0, 0,
        tzinfo=IST
    )

    return window_start, window_end


# ══════════════════════════════════════════════════════════════
#  CHECK IF ARTICLE IS FRESH
# ══════════════════════════════════════════════════════════════

def is_fresh(article: dict) -> bool:

    source = article.get("source", "")
    if source in BYPASS_SOURCES:
        return True

    # ── Check ALL possible date field names ───────────────────
    pub_str = (
        article.get("Blog_PublishDate", "") or
        article.get("Publish_Date",     "") or  # zerodha
        article.get("published",        "") or  # some sources
        article.get("Is_Date",          "") or  # zerodha alternate
        ""
    )

    if not pub_str or pub_str == "Not Available":
        print(f"[DATE FILTER] No date — allowing: "
              f"'{article.get('Blog_Title','')[:45]}'")
        return True

    pub_dt = _parse_date(pub_str)
    if pub_dt is None:
        print(f"[DATE FILTER] Cannot parse '{pub_str}' — allowing")
        return True

    pub_ist                  = pub_dt.astimezone(IST)
    window_start, window_end = _get_today_window()

    if window_start <= pub_ist <= window_end:
        return True

    print(
        f"[DATE FILTER] ❌ Outside window "
        f"({pub_ist.strftime('%d %b %H:%M')} IST) "
        f"| Window: {window_start.strftime('%H:%M')} - "
        f"{window_end.strftime('%H:%M')} IST "
        f"| '{article.get('Blog_Title','')[:40]}'"
    )
    return False


# ══════════════════════════════════════════════════════════════
#  FILTER ARTICLE LIST
# ══════════════════════════════════════════════════════════════

def filter_fresh_articles(articles: list) -> list:
    """
    Filters articles — keeps only those within today's window.
    Window: Today 12:00 AM IST → Today 6:00 PM IST
    """
    if not articles:
        return []

    now_ist                  = datetime.now(IST)
    window_start, window_end = _get_today_window()

    print(f"[DATE FILTER] Window: "
          f"{window_start.strftime('%d %b %Y %H:%M')} → "
          f"{window_end.strftime('%d %b %Y %H:%M')} IST")
    print(f"[DATE FILTER] Current time: "
          f"{now_ist.strftime('%d %b %Y %H:%M')} IST")

    fresh   = [a for a in articles if is_fresh(a)]
    removed = len(articles) - len(fresh)

    if removed:
        print(f"[DATE FILTER] Removed {removed} articles outside window | "
              f"{len(fresh)}/{len(articles)} kept")
    else:
        print(f"[DATE FILTER] All {len(articles)} articles within window ✅")

    return fresh


# ══════════════════════════════════════════════════════════════
#  STANDALONE TEST
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":

    test_articles = [
        {
            "Blog_Title":       "Morning article 9 AM today",
            "Blog_PublishDate": "Thu, 05 Jun 2026 09:00:00 +0530",
            "source":           "economic_times",
        },
        {
            "Blog_Title":       "Afternoon article 3 PM today",
            "Blog_PublishDate": "Thu, 05 Jun 2026 15:00:00 +0530",
            "source":           "ndtv_profit",
        },
        {
            "Blog_Title":       "Evening article 7 PM today — outside window",
            "Blog_PublishDate": "Thu, 05 Jun 2026 19:00:00 +0530",
            "source":           "zerodha",
        },
        {
            "Blog_Title":       "Yesterday article — outside window",
            "Blog_PublishDate": "Wed, 04 Jun 2026 14:00:00 +0530",
            "source":           "cnbc",
        },
        {
            "Blog_Title":       "IPO article — always passes",
            "Blog_PublishDate": "Mon, 01 Jun 2026 10:00:00 +0530",
            "source":           "nse_ipo",
        },
        {
            "Blog_Title":       "No date article — allowed through",
            "Blog_PublishDate": "",
            "source":           "livemint",
        },
    ]

    print("=" * 55)
    print("  Date Filter Test")
    print("=" * 55)

    fresh = filter_fresh_articles(test_articles)

    print(f"\nResult: {len(fresh)}/{len(test_articles)} passed")
    print("=" * 55)
    for a in fresh:
        print(f"  ✅ {a['Blog_Title']}")