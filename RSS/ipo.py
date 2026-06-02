# RSS/ipo.py
# Fetches IPO news from NSE India official RSS feed
# Enriches with full IPO details from scraping
# Source tagged as 'nse_ipo' -> auto-classified as PRIORITY in pipeline
#
# Data source waterfall:
#   Primary:    Chittorgarh  ← best structured data
#   Fallback 1: InvestorGain ← good alternative
#   Fallback 2: Moneycontrol ← mainstream, always up
#   Cache:      In-memory    ← survives 6h of outages

import re
import feedparser
import urllib.request
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime


# ══════════════════════════════════════════════════════════════
#  CONFIG
# ══════════════════════════════════════════════════════════════

IPO_FEED_URL = "https://nsearchives.nseindia.com/content/RSS/Offer_Documents.xml"

LIST_URLS = [
    "https://www.chittorgarh.com/report/ipo-in-india-list-main-board-sme/82/all/",
    "https://www.chittorgarh.com/report/ipo-in-india-list-main-board-sme/82/sme/",
]

HEADERS_CHITTORGARH = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Accept":     "text/html,application/xhtml+xml",
    "Referer":    "https://www.chittorgarh.com/",
}

HEADERS_INVESTORGAIN = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Accept":     "text/html,application/xhtml+xml",
    "Referer":    "https://www.investorgain.com/",
}

HEADERS_MONEYCONTROL = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Accept":     "text/html,application/xhtml+xml",
    "Referer":    "https://www.moneycontrol.com/",
}

IPO_INCLUDE_KEYWORD = "for its ipo"

IPO_EXCLUDE_KEYWORDS = [
    "cp-ni", "disclosure document", "letter of offer",
    "rights issue", "buyback", "open offer", "ncd",
]

BUSINESS_SKIP_PHRASES = [
    "equity dilution", "eps is calculated", "advertise with us",
    "active visitors", "boost your brand", "open account",
    "newportal", "cookie", "privacy", "terms of",
    "all rights reserved", "download our app", "stock broker",
]

MONTHS = ["jan","feb","mar","apr","may","jun",
          "jul","aug","sep","oct","nov","dec"]

CACHE_TTL_HOURS = 6

# ── In-memory caches ──────────────────────────────────────────
_ipo_df_cache   = None   # Chittorgarh map cache
_ipo_data_cache = {}     # {normalized_key: (data, cached_at)}


# ══════════════════════════════════════════════════════════════
#  CACHE KEY NORMALIZER
#  Ensures same company with different name formats
#  maps to the same cache entry
#
#  Examples:
#    "Hexagon Nutrition Limited" → "hexagon nutrition"
#    "Hexagon Nutrition"         → "hexagon nutrition"
#    "Hexagon Nutrition IPO"     → "hexagon nutrition"
#    "HEXAGON NUTRITION LTD"     → "hexagon nutrition"
# ══════════════════════════════════════════════════════════════

def _normalize_company_key(company_name: str) -> str:
    """
    Normalizes company name for use as cache key.
    Strips common suffixes so same company always
    maps to the same cache entry regardless of how
    the name arrives (NSE feed vs TEST_MODE vs Chittorgarh).
    """
    return company_name.lower()\
        .replace(" limited", "")\
        .replace(" ltd",     "")\
        .replace(" ipo",     "")\
        .replace(" india",   "")\
        .strip()


# ══════════════════════════════════════════════════════════════
#  CHITTORGARH — BUILD IPO URL MAP
# ══════════════════════════════════════════════════════════════

def _build_ipo_map() -> pd.DataFrame:
    """Scrapes Chittorgarh list pages. Cached per session."""
    global _ipo_df_cache
    if _ipo_df_cache is not None:
        return _ipo_df_cache

    print("[IPO] Building Chittorgarh IPO map...")
    ipo_links = []

    for url in LIST_URLS:
        print(f"[IPO] Scraping list: {url}")
        try:
            response = requests.get(
                url, headers=HEADERS_CHITTORGARH, timeout=10
            )
            print(f"[IPO] Status: {response.status_code}")
            soup = BeautifulSoup(response.text, "html.parser")

            for a in soup.find_all("a", href=True):
                href = a["href"]
                name = a.get_text(strip=True)

                if any(skip in href for skip in [
                    "ipo_dashboard", "ipo_perf_tracker",
                    "ipo_discussions", "investorgain.com",
                ]):
                    continue

                if ("/ipo/" in href and "-ipo/" in href and
                        name and len(name) > 3):
                    full_url = href if href.startswith("http") \
                               else "https://www.chittorgarh.com" + href
                    source   = url.split("/")[6] \
                               if len(url.split("/")) > 6 else "list"
                    ipo_links.append({
                        "ipo_name": name,
                        "url":      full_url,
                        "source":   source,
                    })

        except Exception as e:
            print(f"[IPO] List scrape error {url}: {e}")

    if ipo_links:
        df = pd.DataFrame(ipo_links).drop_duplicates(subset=["url"])
        df["ipo_name_lower"] = df["ipo_name"].str.lower()
    else:
        df = pd.DataFrame(
            columns=["ipo_name","url","source","ipo_name_lower"]
        )

    print(f"[IPO] Map built: {len(df)} unique IPOs")
    if not df.empty:
        print(df[["ipo_name", "url"]].to_string(index=False))

    _ipo_df_cache = df
    return df


def _find_ipo_url(company_name: str, df: pd.DataFrame) -> str:
    """Fuzzy matches company name against Chittorgarh IPO map."""
    if df.empty:
        return ""

    name_clean = _normalize_company_key(company_name)

    for _, row in df.iterrows():
        key = row["ipo_name_lower"]
        if name_clean in key or key in name_clean:
            return row["url"]

    words = [w for w in name_clean.split() if len(w) > 3]
    for _, row in df.iterrows():
        key     = row["ipo_name_lower"]
        matches = sum(1 for w in words if w in key)
        if matches >= 2:
            return row["url"]

    return ""


# ══════════════════════════════════════════════════════════════
#  DATE PARSER
# ══════════════════════════════════════════════════════════════

def _parse_ipo_date(value: str) -> tuple:
    """
    Parses IPO Date field into (open_date, close_date).
    Format A: "5 to 9 Jun, 2026"      → open="5 Jun, 2026"
    Format B: "29 May to 2 Jun, 2026" → open="29 May, 2026"
    """
    if " to " not in value.lower():
        return value.strip(), ""

    parts      = value.split(" to ")
    open_part  = parts[0].strip()
    close_part = parts[1].strip()

    open_has_month = any(m in open_part.lower() for m in MONTHS)

    if open_has_month:
        year_match = re.search(r'\d{4}', close_part)
        year_str   = f", {year_match.group()}" if year_match else ""
        open_date  = f"{open_part}{year_str}"
    else:
        month_year = re.sub(r"^\d+\s*", "", close_part).strip()
        open_date  = f"{open_part} {month_year}"

    return open_date, close_part


# ══════════════════════════════════════════════════════════════
#  SCRAPER 1 — CHITTORGARH (PRIMARY)
# ══════════════════════════════════════════════════════════════

def _scrape_chittorgarh(company_name: str) -> dict:
    """Primary scraper — Chittorgarh detail page."""
    df      = _build_ipo_map()
    ipo_url = _find_ipo_url(company_name, df)

    if not ipo_url:
        print(f"[IPO] Chittorgarh: {company_name} not in map")
        return {}

    print(f"[IPO] Chittorgarh: {ipo_url}")

    resp = requests.get(ipo_url, headers=HEADERS_CHITTORGARH, timeout=15)
    soup = BeautifulSoup(resp.text, "html.parser")
    data = {"ipo_url": ipo_url}

    for table in soup.find_all("table"):
        for row in table.find_all("tr"):
            cols = row.find_all(["td","th"])
            if len(cols) < 2:
                continue
            key   = cols[0].get_text(strip=True).lower()
            value = cols[1].get_text(strip=True)
            if not key or not value:
                continue

            if "ipo date" in key:
                data["ipo_date"] = value
                open_d, close_d  = _parse_ipo_date(value)
                data["open_date"]  = open_d
                data["close_date"] = close_d

            if "listing date"       in key:
                data["listing_date"] = value.rstrip("T").strip()
            if "price band"         in key: data["price_band"]       = value
            if "lot size"           in key: data["lot_size"]          = value
            if "market lot"         in key: data["lot_size"]          = value
            if "total issue size"   in key: data["issue_size"]       = value
            if "issue size"         in key: data["issue_size"]       = value
            if "face value"         in key: data["face_value"]       = value
            if "listing at"         in key: data["exchange"]         = value
            if "issue type"         in key: data["issue_type"]       = value
            if "sale type"          in key: data["sale_type"]        = value
            if "fresh issue"        in key: data["fresh_issue"]      = value
            if "offer for sale"     in key: data["ofs"]              = value
            if "min investment"     in key: data["min_investment"]   = value
            if "registrar"          in key: data["registrar"]        = value
            if "lead manager"       in key: data["lead_manager"]     = value
            if "qib"                in key: data["qib_quota"]        = value
            if "nii"                in key: data["nii_quota"]        = value
            if "retail"             in key: data["retail_quota"]     = value
            if "share holding pre"  in key: data["pre_issue_shares"] = value
            if "share holding post" in key: data["post_issue_shares"]= value

    # GMP
    for tag in soup.find_all(["td","span"]):
        text = tag.get_text(strip=True)
        if (len(text) < 30 and "₹" in text and
                ("grey market" in text.lower() or "gmp" in text.lower())):
            data["gmp"] = text
            break

    # Business description
    company_lower = _normalize_company_key(company_name)
    company_words = [w for w in company_lower.split() if len(w) > 3]
    for div in soup.find_all("div", class_="accordion-body"):
        text = div.get_text(strip=True)
        if (len(text) > 80 and "ipo" in text.lower() and
                any(w in text.lower() for w in company_words)):
            data["business"] = text[:500]
            break

    # Financials
    for div in soup.find_all("div", class_=True):
        classes = " ".join(div.get("class",[]))
        if "custom-ipo-table" in classes:
            text = div.get_text(strip=True)
            if "period ended" in text.lower() or "assets" in text.lower():
                data["financials"] = text[:300]
                break

    # Market cap
    match = re.search(r"Market Cap.*?₹([\d,.]+\s*Cr)", soup.get_text())
    if match:
        data["market_cap"] = "₹" + match.group(1)

    print(f"[IPO] Chittorgarh fields: {list(data.keys())}")
    return data


# ══════════════════════════════════════════════════════════════
#  SCRAPER 2 — INVESTORGAIN (FALLBACK 1)
# ══════════════════════════════════════════════════════════════

def _scrape_investorgain(company_name: str) -> dict:
    """Fallback 1 — investorgain.com"""
    print(f"[IPO] InvestorGain: searching for {company_name}...")

    name_clean = _normalize_company_key(company_name)

    # Search live IPO page first
    for search_url in [
        "https://www.investorgain.com/report/ipo-subscription-live/331/",
        "https://www.investorgain.com/report/upcoming-ipo/331/",
    ]:
        resp = requests.get(
            search_url, headers=HEADERS_INVESTORGAIN, timeout=15
        )
        soup = BeautifulSoup(resp.text, "html.parser")

        ipo_url = ""
        for a in soup.find_all("a", href=True):
            text = a.get_text(strip=True).lower()
            href = a["href"]
            if name_clean[:8] in text and "/ipo/" in href:
                ipo_url = href
                if not ipo_url.startswith("http"):
                    ipo_url = "https://www.investorgain.com" + ipo_url
                break

        if ipo_url:
            break

    if not ipo_url:
        print(f"[IPO] InvestorGain: {company_name} not found")
        return {}

    print(f"[IPO] InvestorGain: {ipo_url}")
    resp2 = requests.get(ipo_url, headers=HEADERS_INVESTORGAIN, timeout=15)
    soup2 = BeautifulSoup(resp2.text, "html.parser")
    data  = {"ipo_url": ipo_url}

    for row in soup2.find_all("tr"):
        cols = row.find_all(["td","th"])
        if len(cols) < 2:
            continue
        key   = cols[0].get_text(strip=True).lower()
        value = cols[1].get_text(strip=True)
        if not key or not value:
            continue

        if "open date" in key or "ipo date" in key:
            open_d, close_d  = _parse_ipo_date(value)
            data["open_date"]  = open_d
            data["close_date"] = close_d
            data["ipo_date"]   = value
        if "close date"     in key: data["close_date"]     = value
        if "listing date"   in key: data["listing_date"]   = value.rstrip("T").strip()
        if "price band"     in key: data["price_band"]     = value
        if "lot size"       in key: data["lot_size"]        = value
        if "issue size"     in key: data["issue_size"]     = value
        if "face value"     in key: data["face_value"]     = value
        if "listing at"     in key: data["exchange"]       = value
        if "issue type"     in key: data["issue_type"]     = value
        if "min investment" in key: data["min_investment"] = value

    print(f"[IPO] InvestorGain fields: {list(data.keys())}")
    return data


# ══════════════════════════════════════════════════════════════
#  SCRAPER 3 — MONEYCONTROL (FALLBACK 2)
# ══════════════════════════════════════════════════════════════

def _scrape_moneycontrol(company_name: str) -> dict:
    """Fallback 2 — moneycontrol.com IPO section."""
    print(f"[IPO] Moneycontrol: searching for {company_name}...")

    name_clean = _normalize_company_key(company_name)
    name_short = name_clean.split()[0]

    search_url = "https://www.moneycontrol.com/ipo"
    resp = requests.get(search_url, headers=HEADERS_MONEYCONTROL, timeout=15)
    soup = BeautifulSoup(resp.text, "html.parser")

    ipo_url = ""
    for a in soup.find_all("a", href=True):
        text = a.get_text(strip=True).lower()
        href = a["href"]
        if (name_short in text and
                "ipo" in href.lower() and
                "moneycontrol.com" in href):
            ipo_url = href
            break

    data = {}

    if ipo_url:
        print(f"[IPO] Moneycontrol: {ipo_url}")
        resp2 = requests.get(
            ipo_url, headers=HEADERS_MONEYCONTROL, timeout=15
        )
        soup2     = BeautifulSoup(resp2.text, "html.parser")
        full_text = soup2.get_text()
    else:
        full_text = soup.get_text()
        idx       = full_text.lower().find(name_short)
        full_text = full_text[idx:idx+600] if idx != -1 else ""

    if full_text:
        m = re.search(r'₹[\d,]+\s*(?:to|-)\s*₹[\d,]+', full_text)
        if m: data["price_band"] = m.group()

        m = re.search(
            r'(\w+ \d{1,2},?\s*\d{4})\s*(?:to|-)\s*(\w+ \d{1,2},?\s*\d{4})',
            full_text
        )
        if m:
            data["open_date"]  = m.group(1).strip()
            data["close_date"] = m.group(2).strip()

        m = re.search(r'(\d[\d,]*)\s*shares', full_text, re.IGNORECASE)
        if m: data["lot_size"] = f"{m.group(1)} Shares"

        m = re.search(r'₹([\d,.]+\s*(?:Cr|crore))', full_text, re.IGNORECASE)
        if m: data["issue_size"] = f"₹{m.group(1)}"

        m = re.search(
            r'(?:listing|list)\s*(?:date|on)[:\s]+(\w+ \d{1,2},?\s*\d{4})',
            full_text, re.IGNORECASE
        )
        if m: data["listing_date"] = m.group(1).strip()

    if data:
        print(f"[IPO] Moneycontrol fields: {list(data.keys())}")
    else:
        print(f"[IPO] Moneycontrol: no data found for {company_name}")

    return data


# ══════════════════════════════════════════════════════════════
#  SCRAPE IPO DETAILS — WATERFALL + CACHE
#
#  Key change: uses _normalize_company_key() for cache lookup
#  so "Hexagon Nutrition Limited", "Hexagon Nutrition",
#  "Hexagon Nutrition IPO" all map to same cache entry
# ══════════════════════════════════════════════════════════════

def _scrape_ipo_details(company_name: str) -> dict:
    """
    Main scraping function with waterfall fallback + cache.

    Order:
      1. Check in-memory cache (if fresh < 6h)
      2. Chittorgarh  (primary — best structured data)
      3. InvestorGain (fallback 1)
      4. Moneycontrol (fallback 2)
      5. Stale cache  (if all sources fail)

    Cache key is NORMALIZED so:
      "Hexagon Nutrition Limited" → key = "hexagon nutrition"
      "Hexagon Nutrition"         → key = "hexagon nutrition"
      Both hit the SAME cache entry ✅

    Returns:
        dict with IPO fields, or {} if everything fails
    """
    # ── Normalize key for consistent cache lookup ─────────────
    cache_key = _normalize_company_key(company_name)

    # ── Check fresh cache ─────────────────────────────────────
    if cache_key in _ipo_data_cache:
        cached_data, cached_at = _ipo_data_cache[cache_key]
        age_hours = (datetime.now() - cached_at).total_seconds() / 3600
        if age_hours < CACHE_TTL_HOURS:
            src = cached_data.get("data_source", "cache")
            print(f"[IPO] Cache hit: '{cache_key}' "
                  f"(age={age_hours:.1f}h source={src})")
            return cached_data
        else:
            print(f"[IPO] Cache stale: '{cache_key}' "
                  f"(age={age_hours:.1f}h) — re-fetching")

    # ── Waterfall: try 3 sources ──────────────────────────────
    scrapers = [
        ("Chittorgarh",  _scrape_chittorgarh),
        ("InvestorGain", _scrape_investorgain),
        ("Moneycontrol", _scrape_moneycontrol),
    ]

    for source_name, scraper_fn in scrapers:
        try:
            data = scraper_fn(company_name)

            if data.get("price_band") or data.get("open_date"):
                # Tag source + save to cache under normalized key
                data["data_source"]          = source_name
                _ipo_data_cache[cache_key]   = (data, datetime.now())
                print(f"[IPO] ✅ {source_name} → data found + cached "
                      f"(key='{cache_key}')")
                return data
            else:
                print(f"[IPO] {source_name} → no usable data, "
                      f"trying next...")

        except Exception as e:
            print(f"[IPO] {source_name} failed: {e} → trying next...")

    # ── All scrapers failed — use stale cache if available ────
    if cache_key in _ipo_data_cache:
        stale_data, cached_at = _ipo_data_cache[cache_key]
        age_hours = (datetime.now() - cached_at).total_seconds() / 3600
        print(f"[IPO] ⚠️  All sources failed — using stale cache "
              f"for '{cache_key}' (age={age_hours:.1f}h)")
        stale_data["data_source"] = "cache_stale"
        return stale_data

    print(f"[IPO] ❌ All sources + cache failed: {company_name}")
    return {}


# ══════════════════════════════════════════════════════════════
#  VALIDATE IPO DATA
# ══════════════════════════════════════════════════════════════

def _validate_ipo_article(article: dict, company: str) -> bool:
    """
    Validates IPO article data quality.
    Returns True if usable (warnings OK, errors block).
    """
    warnings = []
    errors   = []

    open_date = article.get("open_date", "")
    if open_date:
        month_count = sum(1 for m in MONTHS if m in open_date.lower())
        if month_count > 1:
            errors.append(
                f"open_date has {month_count} month names: '{open_date}'"
            )
        if month_count == 0:
            warnings.append(f"open_date has no month: '{open_date}'")
        if not re.search(r'\d{4}', open_date):
            warnings.append(f"open_date has no year: '{open_date}'")

    close_date = article.get("close_date", "")
    if close_date:
        month_count = sum(1 for m in MONTHS if m in close_date.lower())
        if month_count > 1:
            errors.append(
                f"close_date has {month_count} month names: '{close_date}'"
            )

    price = article.get("price_band", "")
    if price and price != "TBA" and "₹" not in price:
        warnings.append(f"price_band missing ₹: '{price}'")

    lot = article.get("lot_size", "")
    if lot:
        lot_num = lot.replace(" Shares","").replace(",","").strip()
        if not lot_num.isdigit():
            warnings.append(f"lot_size not a number: '{lot}'")

    src = article.get("data_source", "unknown")

    if errors:
        print(f"[IPO VALIDATE] ❌ {company} (source={src})")
        for e in errors:
            print(f"[IPO VALIDATE]    ERROR   : {e}")
        return False

    if warnings:
        print(f"[IPO VALIDATE] ⚠️  {company} (source={src} — warnings ok)")
        for w in warnings:
            print(f"[IPO VALIDATE]    WARNING : {w}")
    else:
        print(f"[IPO VALIDATE] ✅ {company} (source={src})")

    return True


# ══════════════════════════════════════════════════════════════
#  BUILD BLOG TITLE + CONTENT
# ══════════════════════════════════════════════════════════════

def _build_blog_title(company: str, doc_type: str, extra: dict) -> str:
    if doc_type == "PROSP":
        if extra.get("open_date"):
            return f"{company} IPO Opens {extra['open_date']} — Apply or Avoid?"
        return f"{company} IPO — Prospectus Filed, Opening Soon"
    elif doc_type == "RHP":
        if extra.get("price_band"):
            return f"{company} IPO — Price Band {extra['price_band']}, RHP Filed"
        return f"{company} IPO Opening Soon — RHP Filed"
    else:
        return f"{company} Files DRHP for IPO — What Investors Should Know"


def _build_blog_content(company: str, doc_type: str,
                        pub_date: str, extra: dict) -> str:
    return f"""
Company        : {company}
Document Type  : {doc_type}
Filed Date     : {pub_date}
Data Source    : {extra.get('data_source', 'Chittorgarh')}
IPO Date       : {extra.get('ipo_date',       'To be announced')}
Open Date      : {extra.get('open_date',      'To be announced')}
Close Date     : {extra.get('close_date',     'To be announced')}
Listing Date   : {extra.get('listing_date',   'To be announced')}
Price Band     : {extra.get('price_band',     'To be announced')}
Lot Size       : {extra.get('lot_size',        'To be announced')}
Issue Size     : {extra.get('issue_size',     'To be announced')}
Min Investment : {extra.get('min_investment', 'To be announced')}
Face Value     : {extra.get('face_value',     'To be announced')}
Exchange       : {extra.get('exchange',       'NSE / BSE')}
Issue Type     : {extra.get('issue_type',     'Book Built Issue')}
Sale Type      : {extra.get('sale_type',      'To be announced')}
Fresh Issue    : {extra.get('fresh_issue',    'To be announced')}
OFS            : {extra.get('ofs',            'To be announced')}
GMP            : {extra.get('gmp',            'Not available yet')}
QIB Quota      : {extra.get('qib_quota',      'To be announced')}
NII Quota      : {extra.get('nii_quota',      'To be announced')}
Retail Quota   : {extra.get('retail_quota',   'To be announced')}
Registrar      : {extra.get('registrar',      'To be announced')}
Lead Manager   : {extra.get('lead_manager',   'To be announced')}
Business       : {extra.get('business',       company + ' is filing for IPO.')}

Write a complete IPO analysis blog covering all the details above.
For fields showing "To be announced" mention they will be revealed soon.
Include: company background, IPO details, GMP analysis,
should investors apply (pros and cons), how to apply via UPI/ASBA,
and final recommendation.
    """.strip()


# ══════════════════════════════════════════════════════════════
#  MAIN FETCHER — fetch_nse_ipo()
# ══════════════════════════════════════════════════════════════

def fetch_nse_ipo(top_n: int = 6) -> list:
    """
    Fetches IPO news from NSE India official RSS feed.
    Enriches each IPO using waterfall:
      Chittorgarh → InvestorGain → Moneycontrol → stale cache
    Validates data before adding to priority stack.
    """
    articles = []

    # ══════════════════════════════════════════════════════════
    # TEST MODE — set False before production push
    # Change TEST_COMPANY to test any IPO
    #
    # Available companies (from current Chittorgarh map):
    #   "Aureate Tradde"
    #   "Liotech Industries"
    #   "Merritronix"
    #   "Hexagon Nutrition"
    #   "SMR Jewels"
    #   "Harikanta Overseas"
    #   "Rajnandini Fashion India"
    #   "Yaashvi Jewellers"
    #   "Vegorama Punjabi Angithi"
    # ══════════════════════════════════════════════════════════

    TEST_MODE    = False            # ← set False to disable
    TEST_COMPANY = "Q-Line Biotech Limited"  # ← change company here

    if TEST_MODE:
        print(f"[IPO TEST] Injecting {TEST_COMPANY} as fake NSE entry")
        extra = _scrape_ipo_details(TEST_COMPANY)

        if extra.get("price_band") or extra.get("open_date"):
            test_article = {
                "Blog_Title":   _build_blog_title(TEST_COMPANY, "PROSP", extra),
                "Blog_Content": _build_blog_content(TEST_COMPANY, "PROSP",
                                                     "22-May-2026", extra),
                "source":       "nse_ipo",
                "company":      TEST_COMPANY,
                "doc_type":     "PROSP",
                "data_source":  extra.get("data_source", "unknown"),
                "ipo_date":     extra.get("ipo_date",     ""),
                "open_date":    extra.get("open_date",    ""),
                "close_date":   extra.get("close_date",   ""),
                "listing_date": extra.get("listing_date", ""),
                "price_band":   extra.get("price_band",   ""),
                "lot_size":     extra.get("lot_size",      ""),
                "issue_size":   extra.get("issue_size",   ""),
                "face_value":   extra.get("face_value",   ""),
                "exchange":     extra.get("exchange",     ""),
                "issue_type":   extra.get("issue_type",   ""),
                "sale_type":    extra.get("sale_type",    ""),
                "gmp":          extra.get("gmp",          ""),
                "market_cap":   extra.get("market_cap",   ""),
                "ipo_url":      extra.get("ipo_url",      ""),
                "url":          "https://nsearchives.nseindia.com/test",
                "published":    "22-May-2026",
            }

            if _validate_ipo_article(test_article, TEST_COMPANY):
                articles.append(test_article)
                print(f"[IPO TEST] ✅ Added   : {test_article['Blog_Title']}")
                print(f"[IPO TEST]    company    : {TEST_COMPANY}")
                print(f"[IPO TEST]    data_source: {extra.get('data_source','?')}")
                print(f"[IPO TEST]    open_date  : {extra.get('open_date',  'N/A')}")
                print(f"[IPO TEST]    price_band : {extra.get('price_band', 'N/A')}")
                print(f"[IPO TEST]    lot_size   : {extra.get('lot_size',    'N/A')}")
                print(f"[IPO TEST]    listing    : {extra.get('listing_date','N/A')}")
            else:
                print(f"[IPO TEST] ❌ Blocked by validation")
        else:
            print(f"[IPO TEST] ❌ {TEST_COMPANY} — all sources returned no data")

        return articles

    # ── Real NSE feed ─────────────────────────────────────────
    try:
        req = urllib.request.Request(
            IPO_FEED_URL,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                              "AppleWebKit/537.36 Chrome/120.0.0.0",
                "Accept":     "application/rss+xml, application/xml, */*",
                "Referer":    "https://www.nseindia.com/",
            }
        )
        resp = urllib.request.urlopen(req, timeout=15)
        xml  = resp.read().decode("utf-8")
        feed = feedparser.parse(xml)
        print(f"[IPO FEED] NSE raw entries: {len(feed.entries)}")

    except Exception as e:
        print(f"[IPO FEED] NSE feed error: {e}")
        return []

    for entry in feed.entries:
        if len(articles) >= top_n:
            break

        title   = entry.get("title",       "").strip()
        desc    = entry.get("description", "").strip()
        link    = entry.get("link",        "").strip()
        pubdate = entry.get("published",   "").strip()

        desc_lower = desc.lower()
        combined   = desc_lower + link.lower()

        if IPO_INCLUDE_KEYWORD not in desc_lower:
            continue
        if any(kw in combined for kw in IPO_EXCLUDE_KEYWORDS):
            print(f"[IPO FEED] Skipped (not IPO): {title[:50]}")
            continue
        if not title:
            continue

        if "prosp"  in combined: doc_type = "PROSP"
        elif "rhp"  in combined: doc_type = "RHP"
        elif "drhp" in combined or "dp_drhp" in combined: doc_type = "DRHP"
        else: doc_type = "IPO Filing"

        print(f"[IPO FEED] [{doc_type}] {title}")

        extra = _scrape_ipo_details(title)

        if not extra.get("price_band") and not extra.get("open_date"):
            print(f"[IPO FEED] ⏭  Skipped (no data from any source): "
                  f"{title[:50]}")
            continue

        article = {
            "Blog_Title":   _build_blog_title(title, doc_type, extra),
            "Blog_Content": _build_blog_content(title, doc_type, pubdate, extra),
            "source":       "nse_ipo",
            "company":      title,
            "doc_type":     doc_type,
            "data_source":  extra.get("data_source", "unknown"),
            "ipo_date":     extra.get("ipo_date",     ""),
            "open_date":    extra.get("open_date",    ""),
            "close_date":   extra.get("close_date",   ""),
            "listing_date": extra.get("listing_date", ""),
            "price_band":   extra.get("price_band",   ""),
            "lot_size":     extra.get("lot_size",      ""),
            "issue_size":   extra.get("issue_size",   ""),
            "face_value":   extra.get("face_value",   ""),
            "exchange":     extra.get("exchange",     ""),
            "issue_type":   extra.get("issue_type",   ""),
            "sale_type":    extra.get("sale_type",    ""),
            "gmp":          extra.get("gmp",          ""),
            "ipo_url":      extra.get("ipo_url",      link),
            "url":          link,
            "published":    pubdate,
        }

        if _validate_ipo_article(article, title):
            articles.append(article)
            src = extra.get("data_source","?")
            print(f"[IPO FEED] ✅ Added (source={src}): {title[:50]}")
        else:
            print(f"[IPO FEED] ❌ Blocked (validation failed): {title[:50]}")

    print(f"[IPO FEED] Final: {len(articles)} confirmed IPO articles")
    return articles


# ══════════════════════════════════════════════════════════════
#  STANDALONE TEST — run: python RSS/ipo.py
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":

    print("=" * 60)
    print("  STEP 1 — Date Parser Test")
    print("=" * 60)
    for d in ["5 to 9 Jun, 2026", "29 May to 2 Jun, 2026",
              "20 to 24 Mar, 2026", "30 Mar to 3 Apr, 2026"]:
        open_d, close_d = _parse_ipo_date(d)
        ok = "✅" if sum(1 for m in MONTHS if m in open_d.lower()) == 1 else "❌"
        print(f"  {ok} '{d}'")
        print(f"     → open : '{open_d}'")
        print(f"     → close: '{close_d}'")

    print("\n" + "=" * 60)
    print("  STEP 2 — Normalize Key Test")
    print("=" * 60)
    names = [
        "Hexagon Nutrition Limited",
        "Hexagon Nutrition",
        "Hexagon Nutrition IPO",
        "HEXAGON NUTRITION LTD",
    ]
    for n in names:
        key = _normalize_company_key(n)
        print(f"  '{n}' → '{key}'")
    print("  All should be: 'hexagon nutrition'")

    print("\n" + "=" * 60)
    print("  STEP 3 — Waterfall Scrape (Hexagon Nutrition)")
    print("=" * 60)
    result = _scrape_ipo_details("Hexagon Nutrition")
    print(f"\ndata_source  : {result.get('data_source', 'N/A')}")
    print(f"open_date    : {result.get('open_date',   'N/A')}")
    print(f"close_date   : {result.get('close_date',  'N/A')}")
    print(f"price_band   : {result.get('price_band',  'N/A')}")
    print(f"lot_size     : {result.get('lot_size',     'N/A')}")

    print("\n" + "=" * 60)
    print("  STEP 4 — Cache Test (different name formats)")
    print("=" * 60)
    r1 = _scrape_ipo_details("Hexagon Nutrition Limited")
    print(f"'Hexagon Nutrition Limited' → source: {r1.get('data_source')}")
    r2 = _scrape_ipo_details("Hexagon Nutrition")
    print(f"'Hexagon Nutrition'         → source: {r2.get('data_source')}")
    print("Both should show 'cache hit' on second call ✅")

    print("\n" + "=" * 60)
    print("  STEP 5 — Full fetch_nse_ipo()")
    print("=" * 60)
    articles = fetch_nse_ipo(top_n=5)
    print(f"\nTotal articles: {len(articles)}")
    for i, a in enumerate(articles, 1):
        print(f"\n[{i}] {a['Blog_Title']}")
        print(f"     data_source  : {a.get('data_source', 'N/A')}")
        print(f"     open_date    : {a.get('open_date',   'N/A')}")
        print(f"     price_band   : {a.get('price_band',  'N/A')}")
        print(f"     lot_size     : {a.get('lot_size',     'N/A')}")
        print(f"     listing_date : {a.get('listing_date','N/A')}")