"""
nse_corporate_fetcher.py
════════════════════════
Drop-in replacement for your existing fetch_nse_corporate().

WHAT CHANGED vs your original
──────────────────────────────
  Before:  entry.summary stored raw as Blog_Content string → LLM ignored it
  After :  entry.title + entry.summary parsed into named fields →
           generate_corporate_blog() gets exact ₹ figures, dates, action type

UNCHANGED
──────────
  - Same RSS URL
  - Same feedparser approach
  - Same requests session
  - Same function name — drop-in compatible
"""

import re
import logging
from datetime import datetime
from typing import Optional

import feedparser
import requests

log = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────

NSE_RSS_URL = "https://nsearchives.nseindia.com/content/RSS/Corporate_action.xml"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept"         : "application/xml, text/xml, */*",
    "Accept-Language": "en-IN,en;q=0.9",
    "Referer"        : "https://www.nseindia.com/",
}


# ─────────────────────────────────────────────────────────────────────────────
# PARSERS  (all pure string operations — no LLM, no network)
# ─────────────────────────────────────────────────────────────────────────────

def _parse_title(title: str) -> dict:
    """
    "GHCL Limited - Ex-Date: 18-Jun-2026"
    → {"company_name": "GHCL Limited", "ex_date_raw": "18-Jun-2026"}
    """
    m = re.match(r"^(.+?)\s*-\s*Ex-Date:\s*(.+)$", title.strip(), re.IGNORECASE)
    if m:
        return {"company_name": m.group(1).strip(),
                "ex_date_raw" : m.group(2).strip()}
    return {"company_name": title.strip(), "ex_date_raw": None}


def _parse_summary(summary: str) -> dict:
    """
    "SERIES:EQ |PURPOSE:DIVIDEND - RS 12 PER SHARE |FACE VALUE:10 |RECORD DATE:18-Jun-2026 ..."
    → {"series":"EQ", "purpose":"DIVIDEND - RS 12 PER SHARE",
       "face_value":"10", "record_date":"18-Jun-2026", ...}
    """
    KEY_MAP = {
        "SERIES"                 : "series",
        "PURPOSE"                : "purpose",
        "FACE_VALUE"             : "face_value",
        "RECORD_DATE"            : "record_date",
        "BOOK_CLOSURE_START_DATE": "book_closure_start",
        "BOOK_CLOSURE_END_DATE"  : "book_closure_end",
    }
    out = {}
    for part in re.split(r"\s*\|\s*", summary.strip()):
        if ":" not in part:
            continue
        key, _, val = part.partition(":")
        norm = KEY_MAP.get(key.strip().upper().replace(" ", "_"), key.strip().lower())
        out[norm] = None if val.strip() in ("-", "", "N/A") else val.strip()
    return out


def _classify(purpose: str) -> str:
    """Classifies action type from the NSE PURPOSE string."""
    p = purpose.lower()
    if any(k in p for k in ["dividend", "div - rs", "div rs"]):
        return "dividend"
    if "bonus" in p:
        return "bonus"
    if any(k in p for k in ["split", "sub-division", "face value change"]):
        return "split"
    if any(k in p for k in ["rights issue", "rights entitlement"]):
        return "rights"
    if any(k in p for k in ["buy back", "buyback", "buy-back"]):
        return "buyback"
    if "annual general meeting" in p or " agm" in p:
        return "agm"
    if "extraordinary general" in p or " egm" in p:
        return "egm"
    return "general"


def _extract_amount(purpose: str, action_type: str) -> str:
    """Parses the human-readable amount from the raw NSE purpose string."""
    p = purpose.upper()
    if action_type == "dividend":
        m = re.search(r"RS\.?\s*([\d,]+(?:\.\d+)?)\s*(?:PER\s+SHARE)?", p)
        if m:
            return f"₹{m.group(1).replace(',','')} per share"
    elif action_type == "bonus":
        m = re.search(r"(\d+)\s*:\s*(\d+)", p)
        if m: return f"{m.group(1)}:{m.group(2)}"
        m = re.search(r"(\d+)\s+FOR\s+(\d+)", p)
        if m: return f"{m.group(1)}:{m.group(2)}"
    elif action_type == "split":
        m = re.search(r"FROM\s+RS\.?\s*(\d+)\s+TO\s+RS\.?\s*(\d+)", p)
        if m:
            old, new = int(m.group(1)), int(m.group(2))
            return f"₹{old} to ₹{new} ({old//new}:1 split)"
    elif action_type in ("buyback", "rights"):
        m = re.search(r"RS\.?\s*([\d,]+(?:\.\d+)?)\s*(?:PER\s+SHARE)?", p)
        if m: return f"₹{m.group(1).replace(',','')} per share"
    return purpose.title()


def _format_date(raw: Optional[str]) -> Optional[str]:
    """Converts "18-Jun-2026" or "2026-06-18" → "18 Jun 2026"."""
    if not raw or raw.strip() in ("-", ""):
        return None
    ds = raw.strip().split()[0]
    for fmt in ("%d-%b-%Y", "%Y-%m-%d", "%d/%m/%Y", "%d-%B-%Y"):
        try:
            return datetime.strptime(ds, fmt).strftime("%-d %b %Y")
        except ValueError:
            continue
    return raw.strip()


def _div_subtype(purpose: str) -> str:
    p = purpose.upper()
    if "INTERIM" in p: return "Interim"
    if "FINAL"   in p: return "Final"
    if "SPECIAL" in p: return "Special"
    return "Dividend"


# ─────────────────────────────────────────────────────────────────────────────
# ITEM BUILDER  (converts one feedparser entry into a pipeline item dict)
# ─────────────────────────────────────────────────────────────────────────────

def _build_item(entry) -> dict:
    """
    Takes one feedparser entry and returns a fully structured item dict
    ready for generate_corporate_blog().

    entry.title   → company name + ex-date
    entry.summary → pipe-delimited fields (purpose, face value, record date, etc.)
    entry.link    → always the generic NSE corporate actions page
    entry.published → publication date
    """
    raw_title   = (entry.get("title",     "") or "").strip()
    raw_summary = (entry.get("summary",   "") or "").strip()
    raw_link    = (entry.get("link",      "") or "").strip()
    raw_pub     = (entry.get("published", "") or "").strip()

    tf = _parse_title(raw_title)
    sf = _parse_summary(raw_summary)

    company     = tf.get("company_name", "")
    ex_raw      = tf.get("ex_date_raw")
    purpose     = sf.get("purpose", "")
    face_value  = sf.get("face_value")
    record_raw  = sf.get("record_date")
    series      = sf.get("series", "EQ")

    action_type = _classify(purpose)
    amount      = _extract_amount(purpose, action_type)
    subtype     = _div_subtype(purpose) if action_type == "dividend" else None

    ex_fmt  = _format_date(ex_raw)
    rec_fmt = _format_date(record_raw)
    pub_fmt = _format_date(raw_pub.split()[0] if raw_pub else None)

    # Human-readable title for image compositor and notification
    if action_type == "dividend":
        label      = subtype if subtype != "Dividend" else "Dividend"
        title_hint = f"{company} {label} {amount} | Ex-Date {ex_fmt}"
    elif action_type == "bonus":
        title_hint = f"{company} Bonus Issue {amount} | Ex-Date {ex_fmt}"
    elif action_type == "split":
        title_hint = f"{company} Stock Split {amount} | Ex-Date {ex_fmt}"
    elif action_type == "buyback":
        title_hint = f"{company} Buyback at {amount} | Record Date {rec_fmt}"
    elif action_type == "rights":
        title_hint = f"{company} Rights Issue {amount} | Closes {ex_fmt}"
    elif action_type in ("agm", "egm"):
        title_hint = f"{company} {action_type.upper()} | Date {ex_fmt}"
    else:
        title_hint = f"{company} {purpose.title()} | Ex-Date {ex_fmt}"

    return {
        # ── identity ──────────────────────────────────────────
        "company_name"      : company,
        "isin"              : None,       # NSE RSS doesn't include ISIN
        "symbol"            : None,       # populate via lookup if needed
        "series"            : series,

        # ── corporate action ──────────────────────────────────
        "action_type"       : action_type,
        "purpose"           : purpose,
        "amount"            : amount,
        "subtype"           : subtype,

        # ── dates ─────────────────────────────────────────────
        "ex_date"           : ex_fmt,
        "record_date"       : rec_fmt,
        "payment_date"      : None,
        "book_closure_start": sf.get("book_closure_start"),
        "book_closure_end"  : sf.get("book_closure_end"),
        "pub_date"          : pub_fmt,

        # ── financials ────────────────────────────────────────
        "face_value"        : f"₹{face_value}" if face_value else None,

        # ── pipeline ──────────────────────────────────────────
        "Blog_Links"        : raw_link,
        "source"            : "nse_corporate",
        "title"             : title_hint,   # for image compositor
        "Blog_Title"        : "",           # filled by generate_corporate_blog
    }


# ─────────────────────────────────────────────────────────────────────────────
# MAIN FETCHER  (drop-in for your existing fetch_nse_corporate)
# ─────────────────────────────────────────────────────────────────────────────

def fetch_nse_corporate() -> list[dict]:
    """
    Fetches NSE Corporate Actions RSS and returns structured item dicts.
    Drop-in replacement for your existing fetch_nse_corporate().

    Returns:
        list of item dicts ready for generate_corporate_blog()
    """
    try:
        response = requests.get(NSE_RSS_URL, headers=HEADERS, timeout=20)
    except requests.RequestException as e:
        log.error(f"[NSE CORPORATE] Network error: {e}")
        print(f"[ERROR] NSE Corporate fetch failed: {e}")
        return []

    if response.status_code != 200:
        log.error(f"[NSE CORPORATE] HTTP {response.status_code}")
        print(f"[ERROR] NSE Corporate fetch failed: HTTP {response.status_code}")
        return []

    feed = feedparser.parse(response.content)
    print(f"[NSE CORPORATE] Entries found: {len(feed.entries)}")

    items = []
    for entry in feed.entries:
        try:
            item = _build_item(entry)
            items.append(item)
        except Exception as e:
            title = entry.get("title", "unknown")
            log.warning(f"[NSE CORPORATE] Failed to parse entry '{title}': {e}")
            continue

    print(f"[INFO] NSE Corporate fetched: {len(items)}")
    return items


# ─────────────────────────────────────────────────────────────────────────────
# DEBUG RUNNER
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    results = fetch_nse_corporate()

    print(f"\nTotal: {len(results)}")
    print("=" * 70)

    for i, r in enumerate(results, 1):
        print(f"\n[{i}] Company     : {r['company_name']}")
        print(f"    Action      : {r['action_type']} | {r['amount']}")
        print(f"    Ex-Date     : {r['ex_date']}")
        print(f"    Record Date : {r['record_date']}")
        print(f"    Face Value  : {r['face_value']}")
        print(f"    Purpose     : {r['purpose']}")
        print(f"    Title hint  : {r['title']}")
        print(f"    Blog_Links  : {r['Blog_Links']}")