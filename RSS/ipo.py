
# import re
# import feedparser
# import urllib.request
# import requests
# from bs4 import BeautifulSoup
# import pandas as pd
# from datetime import datetime


# # ══════════════════════════════════════════════════════════════
# #  CONFIG
# # ══════════════════════════════════════════════════════════════

# IPO_FEED_URL = "https://nsearchives.nseindia.com/content/RSS/Offer_Documents.xml"

# LIST_URLS = [
#     "https://www.chittorgarh.com/report/ipo-in-india-list-main-board-sme/82/all/",
#     "https://www.chittorgarh.com/report/ipo-in-india-list-main-board-sme/82/sme/",
# ]

# HEADERS_CHITTORGARH = {
#     "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
#                   "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
#     "Accept":     "text/html,application/xhtml+xml",
#     "Referer":    "https://www.chittorgarh.com/",
# }

# HEADERS_INVESTORGAIN = {
#     "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
#                   "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
#     "Accept":     "text/html,application/xhtml+xml",
#     "Referer":    "https://www.investorgain.com/",
# }

# HEADERS_MONEYCONTROL = {
#     "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
#                   "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
#     "Accept":     "text/html,application/xhtml+xml",
#     "Referer":    "https://www.moneycontrol.com/",
# }

# IPO_INCLUDE_KEYWORD = "for its ipo"

# IPO_EXCLUDE_KEYWORDS = [
#     "cp-ni", "disclosure document", "letter of offer",
#     "rights issue", "buyback", "open offer", "ncd",
# ]

# BUSINESS_SKIP_PHRASES = [
#     "equity dilution", "eps is calculated", "advertise with us",
#     "active visitors", "boost your brand", "open account",
#     "newportal", "cookie", "privacy", "terms of",
#     "all rights reserved", "download our app", "stock broker",
# ]

# MONTHS = ["jan","feb","mar","apr","may","jun",
#           "jul","aug","sep","oct","nov","dec"]

# CACHE_TTL_HOURS = 6

# # ── In-memory caches ──────────────────────────────────────────
# _ipo_df_cache   = None   # Chittorgarh map cache
# _ipo_data_cache = {}     # {normalized_key: (data, cached_at)}


# # ══════════════════════════════════════════════════════════════
# #  CACHE KEY NORMALIZER
# #  Ensures same company with different name formats
# #  maps to the same cache entry
# #
# #  Examples:
# #    "Hexagon Nutrition Limited" → "hexagon nutrition"
# #    "Hexagon Nutrition"         → "hexagon nutrition"
# #    "Hexagon Nutrition IPO"     → "hexagon nutrition"
# #    "HEXAGON NUTRITION LTD"     → "hexagon nutrition"
# # ══════════════════════════════════════════════════════════════

# def _normalize_company_key(company_name: str) -> str:
#     """
#     Normalizes company name for use as cache key.
#     Strips common suffixes so same company always
#     maps to the same cache entry regardless of how
#     the name arrives (NSE feed vs TEST_MODE vs Chittorgarh).
#     """
#     return company_name.lower()\
#         .replace(" limited", "")\
#         .replace(" ltd",     "")\
#         .replace(" ipo",     "")\
#         .replace(" india",   "")\
#         .strip()


# # ══════════════════════════════════════════════════════════════
# #  CHITTORGARH — BUILD IPO URL MAP
# # ══════════════════════════════════════════════════════════════

# def _build_ipo_map() -> pd.DataFrame:
#     """Scrapes Chittorgarh list pages. Cached per session."""
#     global _ipo_df_cache
#     if _ipo_df_cache is not None:
#         return _ipo_df_cache

#     print("[IPO] Building Chittorgarh IPO map...")
#     ipo_links = []

#     for url in LIST_URLS:
#         print(f"[IPO] Scraping list: {url}")
#         try:
#             response = requests.get(
#                 url, headers=HEADERS_CHITTORGARH, timeout=10
#             )
#             print(f"[IPO] Status: {response.status_code}")
#             soup = BeautifulSoup(response.text, "html.parser")

#             for a in soup.find_all("a", href=True):
#                 href = a["href"]
#                 name = a.get_text(strip=True)

#                 if any(skip in href for skip in [
#                     "ipo_dashboard", "ipo_perf_tracker",
#                     "ipo_discussions", "investorgain.com",
#                 ]):
#                     continue

#                 if ("/ipo/" in href and "-ipo/" in href and
#                         name and len(name) > 3):
#                     full_url = href if href.startswith("http") \
#                                else "https://www.chittorgarh.com" + href
#                     source   = url.split("/")[6] \
#                                if len(url.split("/")) > 6 else "list"
#                     ipo_links.append({
#                         "ipo_name": name,
#                         "url":      full_url,
#                         "source":   source,
#                     })

#         except Exception as e:
#             print(f"[IPO] List scrape error {url}: {e}")

#     if ipo_links:
#         df = pd.DataFrame(ipo_links).drop_duplicates(subset=["url"])
#         df["ipo_name_lower"] = df["ipo_name"].str.lower()
#     else:
#         df = pd.DataFrame(
#             columns=["ipo_name","url","source","ipo_name_lower"]
#         )

#     print(f"[IPO] Map built: {len(df)} unique IPOs")
#     if not df.empty:
#         print(df[["ipo_name", "url"]].to_string(index=False))

#     _ipo_df_cache = df
#     return df


# def _find_ipo_url(company_name: str, df: pd.DataFrame) -> str:
#     """Fuzzy matches company name against Chittorgarh IPO map."""
#     if df.empty:
#         return ""

#     name_clean = _normalize_company_key(company_name)

#     for _, row in df.iterrows():
#         key = row["ipo_name_lower"]
#         if name_clean in key or key in name_clean:
#             return row["url"]

#     words = [w for w in name_clean.split() if len(w) > 3]
#     for _, row in df.iterrows():
#         key     = row["ipo_name_lower"]
#         matches = sum(1 for w in words if w in key)
#         if matches >= 2:
#             return row["url"]

#     return ""


# # ══════════════════════════════════════════════════════════════
# #  DATE PARSER
# # ══════════════════════════════════════════════════════════════

# def _parse_ipo_date(value: str) -> tuple:
#     """
#     Parses IPO Date field into (open_date, close_date).
#     Format A: "5 to 9 Jun, 2026"      → open="5 Jun, 2026"
#     Format B: "29 May to 2 Jun, 2026" → open="29 May, 2026"
#     """
#     if " to " not in value.lower():
#         return value.strip(), ""

#     parts      = value.split(" to ")
#     open_part  = parts[0].strip()
#     close_part = parts[1].strip()

#     open_has_month = any(m in open_part.lower() for m in MONTHS)

#     if open_has_month:
#         year_match = re.search(r'\d{4}', close_part)
#         year_str   = f", {year_match.group()}" if year_match else ""
#         open_date  = f"{open_part}{year_str}"
#     else:
#         month_year = re.sub(r"^\d+\s*", "", close_part).strip()
#         open_date  = f"{open_part} {month_year}"

#     return open_date, close_part


# # ══════════════════════════════════════════════════════════════
# #  SCRAPER 1 — CHITTORGARH (PRIMARY)
# # ══════════════════════════════════════════════════════════════

# def _scrape_chittorgarh(company_name: str) -> dict:
#     """Primary scraper — Chittorgarh detail page."""
#     df      = _build_ipo_map()
#     ipo_url = _find_ipo_url(company_name, df)

#     if not ipo_url:
#         print(f"[IPO] Chittorgarh: {company_name} not in map")
#         return {}

#     print(f"[IPO] Chittorgarh: {ipo_url}")

#     resp = requests.get(ipo_url, headers=HEADERS_CHITTORGARH, timeout=15)
#     soup = BeautifulSoup(resp.text, "html.parser")
#     data = {"ipo_url": ipo_url}

#     for table in soup.find_all("table"):
#         for row in table.find_all("tr"):
#             cols = row.find_all(["td","th"])
#             if len(cols) < 2:
#                 continue
#             key   = cols[0].get_text(strip=True).lower()
#             value = cols[1].get_text(strip=True)
#             if not key or not value:
#                 continue

#             if "ipo date" in key:
#                 data["ipo_date"] = value
#                 open_d, close_d  = _parse_ipo_date(value)
#                 data["open_date"]  = open_d
#                 data["close_date"] = close_d

#             if "listing date"       in key:
#                 data["listing_date"] = value.rstrip("T").strip()
#             if "price band"         in key: data["price_band"]       = value
#             if "lot size"           in key: data["lot_size"]          = value
#             if "market lot"         in key: data["lot_size"]          = value
#             if "total issue size"   in key: data["issue_size"]       = value
#             if "issue size"         in key: data["issue_size"]       = value
#             if "face value"         in key: data["face_value"]       = value
#             if "listing at"         in key: data["exchange"]         = value
#             if "issue type"         in key: data["issue_type"]       = value
#             if "sale type"          in key: data["sale_type"]        = value
#             if "fresh issue"        in key: data["fresh_issue"]      = value
#             if "offer for sale"     in key: data["ofs"]              = value
#             if "min investment"     in key: data["min_investment"]   = value
#             if "registrar"          in key: data["registrar"]        = value
#             if "lead manager"       in key: data["lead_manager"]     = value
#             if "qib"                in key: data["qib_quota"]        = value
#             if "nii"                in key: data["nii_quota"]        = value
#             if "retail"             in key: data["retail_quota"]     = value
#             if "share holding pre"  in key: data["pre_issue_shares"] = value
#             if "share holding post" in key: data["post_issue_shares"]= value

#     # GMP
#     for tag in soup.find_all(["td","span"]):
#         text = tag.get_text(strip=True)
#         if (len(text) < 30 and "₹" in text and
#                 ("grey market" in text.lower() or "gmp" in text.lower())):
#             data["gmp"] = text
#             break

#     # Business description
#     company_lower = _normalize_company_key(company_name)
#     company_words = [w for w in company_lower.split() if len(w) > 3]
#     for div in soup.find_all("div", class_="accordion-body"):
#         text = div.get_text(strip=True)
#         if (len(text) > 80 and "ipo" in text.lower() and
#                 any(w in text.lower() for w in company_words)):
#             data["business"] = text[:500]
#             break

#     # Financials
#     for div in soup.find_all("div", class_=True):
#         classes = " ".join(div.get("class",[]))
#         if "custom-ipo-table" in classes:
#             text = div.get_text(strip=True)
#             if "period ended" in text.lower() or "assets" in text.lower():
#                 data["financials"] = text[:300]
#                 break

#     # Market cap
#     match = re.search(r"Market Cap.*?₹([\d,.]+\s*Cr)", soup.get_text())
#     if match:
#         data["market_cap"] = "₹" + match.group(1)

#     print(f"[IPO] Chittorgarh fields: {list(data.keys())}")
#     return data


# # ══════════════════════════════════════════════════════════════
# #  SCRAPER 2 — INVESTORGAIN (FALLBACK 1)
# # ══════════════════════════════════════════════════════════════

# def _scrape_investorgain(company_name: str) -> dict:
#     """Fallback 1 — investorgain.com"""
#     print(f"[IPO] InvestorGain: searching for {company_name}...")

#     name_clean = _normalize_company_key(company_name)

#     # Search live IPO page first
#     for search_url in [
#         "https://www.investorgain.com/report/ipo-subscription-live/331/",
#         "https://www.investorgain.com/report/upcoming-ipo/331/",
#     ]:
#         resp = requests.get(
#             search_url, headers=HEADERS_INVESTORGAIN, timeout=15
#         )
#         soup = BeautifulSoup(resp.text, "html.parser")

#         ipo_url = ""
#         for a in soup.find_all("a", href=True):
#             text = a.get_text(strip=True).lower()
#             href = a["href"]
#             if name_clean[:8] in text and "/ipo/" in href:
#                 ipo_url = href
#                 if not ipo_url.startswith("http"):
#                     ipo_url = "https://www.investorgain.com" + ipo_url
#                 break

#         if ipo_url:
#             break

#     if not ipo_url:
#         print(f"[IPO] InvestorGain: {company_name} not found")
#         return {}

#     print(f"[IPO] InvestorGain: {ipo_url}")
#     resp2 = requests.get(ipo_url, headers=HEADERS_INVESTORGAIN, timeout=15)
#     soup2 = BeautifulSoup(resp2.text, "html.parser")
#     data  = {"ipo_url": ipo_url}

#     for row in soup2.find_all("tr"):
#         cols = row.find_all(["td","th"])
#         if len(cols) < 2:
#             continue
#         key   = cols[0].get_text(strip=True).lower()
#         value = cols[1].get_text(strip=True)
#         if not key or not value:
#             continue

#         if "open date" in key or "ipo date" in key:
#             open_d, close_d  = _parse_ipo_date(value)
#             data["open_date"]  = open_d
#             data["close_date"] = close_d
#             data["ipo_date"]   = value
#         if "close date"     in key: data["close_date"]     = value
#         if "listing date"   in key: data["listing_date"]   = value.rstrip("T").strip()
#         if "price band"     in key: data["price_band"]     = value
#         if "lot size"       in key: data["lot_size"]        = value
#         if "issue size"     in key: data["issue_size"]     = value
#         if "face value"     in key: data["face_value"]     = value
#         if "listing at"     in key: data["exchange"]       = value
#         if "issue type"     in key: data["issue_type"]     = value
#         if "min investment" in key: data["min_investment"] = value

#     print(f"[IPO] InvestorGain fields: {list(data.keys())}")
#     return data


# # ══════════════════════════════════════════════════════════════
# #  SCRAPER 3 — MONEYCONTROL (FALLBACK 2)
# # ══════════════════════════════════════════════════════════════

# def _scrape_moneycontrol(company_name: str) -> dict:
#     """Fallback 2 — moneycontrol.com IPO section."""
#     print(f"[IPO] Moneycontrol: searching for {company_name}...")

#     name_clean = _normalize_company_key(company_name)
#     name_short = name_clean.split()[0]

#     search_url = "https://www.moneycontrol.com/ipo"
#     resp = requests.get(search_url, headers=HEADERS_MONEYCONTROL, timeout=15)
#     soup = BeautifulSoup(resp.text, "html.parser")

#     ipo_url = ""
#     for a in soup.find_all("a", href=True):
#         text = a.get_text(strip=True).lower()
#         href = a["href"]
#         if (name_short in text and
#                 "ipo" in href.lower() and
#                 "moneycontrol.com" in href):
#             ipo_url = href
#             break

#     data = {}

#     if ipo_url:
#         print(f"[IPO] Moneycontrol: {ipo_url}")
#         resp2 = requests.get(
#             ipo_url, headers=HEADERS_MONEYCONTROL, timeout=15
#         )
#         soup2     = BeautifulSoup(resp2.text, "html.parser")
#         full_text = soup2.get_text()
#     else:
#         full_text = soup.get_text()
#         idx       = full_text.lower().find(name_short)
#         full_text = full_text[idx:idx+600] if idx != -1 else ""

#     if full_text:
#         m = re.search(r'₹[\d,]+\s*(?:to|-)\s*₹[\d,]+', full_text)
#         if m: data["price_band"] = m.group()

#         m = re.search(
#             r'(\w+ \d{1,2},?\s*\d{4})\s*(?:to|-)\s*(\w+ \d{1,2},?\s*\d{4})',
#             full_text
#         )
#         if m:
#             data["open_date"]  = m.group(1).strip()
#             data["close_date"] = m.group(2).strip()

#         m = re.search(r'(\d[\d,]*)\s*shares', full_text, re.IGNORECASE)
#         if m: data["lot_size"] = f"{m.group(1)} Shares"

#         m = re.search(r'₹([\d,.]+\s*(?:Cr|crore))', full_text, re.IGNORECASE)
#         if m: data["issue_size"] = f"₹{m.group(1)}"

#         m = re.search(
#             r'(?:listing|list)\s*(?:date|on)[:\s]+(\w+ \d{1,2},?\s*\d{4})',
#             full_text, re.IGNORECASE
#         )
#         if m: data["listing_date"] = m.group(1).strip()

#     if data:
#         print(f"[IPO] Moneycontrol fields: {list(data.keys())}")
#     else:
#         print(f"[IPO] Moneycontrol: no data found for {company_name}")

#     return data


# # ══════════════════════════════════════════════════════════════
# #  SCRAPE IPO DETAILS — WATERFALL + CACHE
# #
# #  Key change: uses _normalize_company_key() for cache lookup
# #  so "Hexagon Nutrition Limited", "Hexagon Nutrition",
# #  "Hexagon Nutrition IPO" all map to same cache entry
# # ══════════════════════════════════════════════════════════════

# def _scrape_ipo_details(company_name: str) -> dict:
#     """
#     Main scraping function with waterfall fallback + cache.

#     Order:
#       1. Check in-memory cache (if fresh < 6h)
#       2. Chittorgarh  (primary — best structured data)
#       3. InvestorGain (fallback 1)
#       4. Moneycontrol (fallback 2)
#       5. Stale cache  (if all sources fail)

#     Cache key is NORMALIZED so:
#       "Hexagon Nutrition Limited" → key = "hexagon nutrition"
#       "Hexagon Nutrition"         → key = "hexagon nutrition"
#       Both hit the SAME cache entry ✅

#     Returns:
#         dict with IPO fields, or {} if everything fails
#     """
#     # ── Normalize key for consistent cache lookup ─────────────
#     cache_key = _normalize_company_key(company_name)

#     # ── Check fresh cache ─────────────────────────────────────
#     if cache_key in _ipo_data_cache:
#         cached_data, cached_at = _ipo_data_cache[cache_key]
#         age_hours = (datetime.now() - cached_at).total_seconds() / 3600
#         if age_hours < CACHE_TTL_HOURS:
#             src = cached_data.get("data_source", "cache")
#             print(f"[IPO] Cache hit: '{cache_key}' "
#                   f"(age={age_hours:.1f}h source={src})")
#             return cached_data
#         else:
#             print(f"[IPO] Cache stale: '{cache_key}' "
#                   f"(age={age_hours:.1f}h) — re-fetching")

#     # ── Waterfall: try 3 sources ──────────────────────────────
#     scrapers = [
#         ("Chittorgarh",  _scrape_chittorgarh),
#         ("InvestorGain", _scrape_investorgain),
#         ("Moneycontrol", _scrape_moneycontrol),
#     ]

#     for source_name, scraper_fn in scrapers:
#         try:
#             data = scraper_fn(company_name)

#             if data.get("price_band") or data.get("open_date"):
#                 # Tag source + save to cache under normalized key
#                 data["data_source"]          = source_name
#                 _ipo_data_cache[cache_key]   = (data, datetime.now())
#                 print(f"[IPO] ✅ {source_name} → data found + cached "
#                       f"(key='{cache_key}')")
#                 return data
#             else:
#                 print(f"[IPO] {source_name} → no usable data, "
#                       f"trying next...")

#         except Exception as e:
#             print(f"[IPO] {source_name} failed: {e} → trying next...")

#     # ── All scrapers failed — use stale cache if available ────
#     if cache_key in _ipo_data_cache:
#         stale_data, cached_at = _ipo_data_cache[cache_key]
#         age_hours = (datetime.now() - cached_at).total_seconds() / 3600
#         print(f"[IPO] ⚠️  All sources failed — using stale cache "
#               f"for '{cache_key}' (age={age_hours:.1f}h)")
#         stale_data["data_source"] = "cache_stale"
#         return stale_data

#     print(f"[IPO] ❌ All sources + cache failed: {company_name}")
#     return {}


# # ══════════════════════════════════════════════════════════════
# #  VALIDATE IPO DATA
# # ══════════════════════════════════════════════════════════════

# def _validate_ipo_article(article: dict, company: str) -> bool:
#     """
#     Validates IPO article data quality.
#     Returns True if usable (warnings OK, errors block).
#     """
#     warnings = []
#     errors   = []

#     open_date = article.get("open_date", "")
#     if open_date:
#         month_count = sum(1 for m in MONTHS if m in open_date.lower())
#         if month_count > 1:
#             errors.append(
#                 f"open_date has {month_count} month names: '{open_date}'"
#             )
#         if month_count == 0:
#             warnings.append(f"open_date has no month: '{open_date}'")
#         if not re.search(r'\d{4}', open_date):
#             warnings.append(f"open_date has no year: '{open_date}'")

#     close_date = article.get("close_date", "")
#     if close_date:
#         month_count = sum(1 for m in MONTHS if m in close_date.lower())
#         if month_count > 1:
#             errors.append(
#                 f"close_date has {month_count} month names: '{close_date}'"
#             )

#     price = article.get("price_band", "")
#     if price and price != "TBA" and "₹" not in price:
#         warnings.append(f"price_band missing ₹: '{price}'")

#     lot = article.get("lot_size", "")
#     if lot:
#         lot_num = lot.replace(" Shares","").replace(",","").strip()
#         if not lot_num.isdigit():
#             warnings.append(f"lot_size not a number: '{lot}'")

#     src = article.get("data_source", "unknown")

#     if errors:
#         print(f"[IPO VALIDATE] ❌ {company} (source={src})")
#         for e in errors:
#             print(f"[IPO VALIDATE]    ERROR   : {e}")
#         return False

#     if warnings:
#         print(f"[IPO VALIDATE] ⚠️  {company} (source={src} — warnings ok)")
#         for w in warnings:
#             print(f"[IPO VALIDATE]    WARNING : {w}")
#     else:
#         print(f"[IPO VALIDATE] ✅ {company} (source={src})")

#     return True


# # ══════════════════════════════════════════════════════════════
# #  BUILD BLOG TITLE + CONTENT
# # ══════════════════════════════════════════════════════════════

# def _build_blog_title(company: str, doc_type: str, extra: dict) -> str:
#     if doc_type == "PROSP":
#         if extra.get("open_date"):
#             return f"{company} IPO Opens {extra['open_date']} — Apply or Avoid?"
#         return f"{company} IPO — Prospectus Filed, Opening Soon"
#     elif doc_type == "RHP":
#         if extra.get("price_band"):
#             return f"{company} IPO — Price Band {extra['price_band']}, RHP Filed"
#         return f"{company} IPO Opening Soon — RHP Filed"
#     else:
#         return f"{company} Files DRHP for IPO — What Investors Should Know"


# def _build_blog_content(company: str, doc_type: str,
#                         pub_date: str, extra: dict) -> str:
#     return f"""
# Company        : {company}
# Document Type  : {doc_type}
# Filed Date     : {pub_date}
# Data Source    : {extra.get('data_source', 'Chittorgarh')}
# IPO Date       : {extra.get('ipo_date',       'To be announced')}
# Open Date      : {extra.get('open_date',      'To be announced')}
# Close Date     : {extra.get('close_date',     'To be announced')}
# Listing Date   : {extra.get('listing_date',   'To be announced')}
# Price Band     : {extra.get('price_band',     'To be announced')}
# Lot Size       : {extra.get('lot_size',        'To be announced')}
# Issue Size     : {extra.get('issue_size',     'To be announced')}
# Min Investment : {extra.get('min_investment', 'To be announced')}
# Face Value     : {extra.get('face_value',     'To be announced')}
# Exchange       : {extra.get('exchange',       'NSE / BSE')}
# Issue Type     : {extra.get('issue_type',     'Book Built Issue')}
# Sale Type      : {extra.get('sale_type',      'To be announced')}
# Fresh Issue    : {extra.get('fresh_issue',    'To be announced')}
# OFS            : {extra.get('ofs',            'To be announced')}
# GMP            : {extra.get('gmp',            'Not available yet')}
# QIB Quota      : {extra.get('qib_quota',      'To be announced')}
# NII Quota      : {extra.get('nii_quota',      'To be announced')}
# Retail Quota   : {extra.get('retail_quota',   'To be announced')}
# Registrar      : {extra.get('registrar',      'To be announced')}
# Lead Manager   : {extra.get('lead_manager',   'To be announced')}
# Business       : {extra.get('business',       company + ' is filing for IPO.')}

# Write a complete IPO analysis blog covering all the details above.
# For fields showing "To be announced" mention they will be revealed soon.
# Include: company background, IPO details, GMP analysis,
# should investors apply (pros and cons), how to apply via UPI/ASBA,
# and final recommendation.
#     """.strip()


# # ══════════════════════════════════════════════════════════════
# #  MAIN FETCHER — fetch_nse_ipo()
# # ══════════════════════════════════════════════════════════════

# def fetch_nse_ipo() -> list:
#     """
#     Fetches IPO news from NSE India official RSS feed.
#     Enriches each IPO using waterfall:
#       Chittorgarh → InvestorGain → Moneycontrol → stale cache
#     Validates data before adding to priority stack.
#     """
#     articles = []

#     # ══════════════════════════════════════════════════════════
#     # TEST MODE — set False before production push
#     # Change TEST_COMPANY to test any IPO
#     #
#     # Available companies (from current Chittorgarh map):
#     #   "Aureate Tradde"
#     #   "Liotech Industries"
#     #   "Merritronix"
#     #   "Hexagon Nutrition"
#     #   "SMR Jewels"
#     #   "Harikanta Overseas"
#     #   "Rajnandini Fashion India"
#     #   "Yaashvi Jewellers"
#     #   "Vegorama Punjabi Angithi"
#     # ══════════════════════════════════════════════════════════

#     TEST_MODE    = False            # ← set False to disable
#     TEST_COMPANY = "Q-Line Biotech Limited"  # ← change company here

#     if TEST_MODE:
#         print(f"[IPO TEST] Injecting {TEST_COMPANY} as fake NSE entry")
#         extra = _scrape_ipo_details(TEST_COMPANY)

#         if extra.get("price_band") or extra.get("open_date"):
#             test_article = {
#                 "Blog_Title":   _build_blog_title(TEST_COMPANY, "PROSP", extra),
#                 "Blog_Content": _build_blog_content(TEST_COMPANY, "PROSP",
#                                                      "22-May-2026", extra),
#                 "source":       "nse_ipo",
#                 "company":      TEST_COMPANY,
#                 "doc_type":     "PROSP",
#                 "data_source":  extra.get("data_source", "unknown"),
#                 "ipo_date":     extra.get("ipo_date",     ""),
#                 "open_date":    extra.get("open_date",    ""),
#                 "close_date":   extra.get("close_date",   ""),
#                 "listing_date": extra.get("listing_date", ""),
#                 "price_band":   extra.get("price_band",   ""),
#                 "lot_size":     extra.get("lot_size",      ""),
#                 "issue_size":   extra.get("issue_size",   ""),
#                 "face_value":   extra.get("face_value",   ""),
#                 "exchange":     extra.get("exchange",     ""),
#                 "issue_type":   extra.get("issue_type",   ""),
#                 "sale_type":    extra.get("sale_type",    ""),
#                 "gmp":          extra.get("gmp",          ""),
#                 "market_cap":   extra.get("market_cap",   ""),
#                 "ipo_url":      extra.get("ipo_url",      ""),
#                 "url":          "https://nsearchives.nseindia.com/test",
#                 "published":    "22-May-2026",
#             }

#             if _validate_ipo_article(test_article, TEST_COMPANY):
#                 articles.append(test_article)
#                 print(f"[IPO TEST] ✅ Added   : {test_article['Blog_Title']}")
#                 print(f"[IPO TEST]    company    : {TEST_COMPANY}")
#                 print(f"[IPO TEST]    data_source: {extra.get('data_source','?')}")
#                 print(f"[IPO TEST]    open_date  : {extra.get('open_date',  'N/A')}")
#                 print(f"[IPO TEST]    price_band : {extra.get('price_band', 'N/A')}")
#                 print(f"[IPO TEST]    lot_size   : {extra.get('lot_size',    'N/A')}")
#                 print(f"[IPO TEST]    listing    : {extra.get('listing_date','N/A')}")
#             else:
#                 print(f"[IPO TEST] ❌ Blocked by validation")
#         else:
#             print(f"[IPO TEST] ❌ {TEST_COMPANY} — all sources returned no data")

#         return articles

#     # ── Real NSE feed ─────────────────────────────────────────
#     try:
#         req = urllib.request.Request(
#             IPO_FEED_URL,
#             headers={
#                 "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
#                               "AppleWebKit/537.36 Chrome/120.0.0.0",
#                 "Accept":     "application/rss+xml, application/xml, */*",
#                 "Referer":    "https://www.nseindia.com/",
#             }
#         )
#         resp = urllib.request.urlopen(req, timeout=15)
#         xml  = resp.read().decode("utf-8")
#         feed = feedparser.parse(xml)
#         print(f"[IPO FEED] NSE raw entries: {len(feed.entries)}")

#     except Exception as e:
#         print(f"[IPO FEED] NSE feed error: {e}")
#         return []

#     for entry in feed.entries:

#         title   = entry.get("title",       "").strip()
#         desc    = entry.get("description", "").strip()
#         link    = entry.get("link",        "").strip()
#         pubdate = entry.get("published",   "").strip()

#         desc_lower = desc.lower()
#         combined   = desc_lower + link.lower()

#         if IPO_INCLUDE_KEYWORD not in desc_lower:
#             continue
#         if any(kw in combined for kw in IPO_EXCLUDE_KEYWORDS):
#             print(f"[IPO FEED] Skipped (not IPO): {title[:50]}")
#             continue
#         if not title:
#             continue

#         if "prosp"  in combined: doc_type = "PROSP"
#         elif "rhp"  in combined: doc_type = "RHP"
#         elif "drhp" in combined or "dp_drhp" in combined: doc_type = "DRHP"
#         else: doc_type = "IPO Filing"

#         print(f"[IPO FEED] [{doc_type}] {title}")

#         extra = _scrape_ipo_details(title)

#         if not extra.get("price_band") and not extra.get("open_date"):
#             print(f"[IPO FEED] ⏭  Skipped (no data from any source): "
#                   f"{title[:50]}")
#             continue

#         article = {
#             "Blog_Title":   _build_blog_title(title, doc_type, extra),
#             "Blog_Content": _build_blog_content(title, doc_type, pubdate, extra),
#             "source":       "nse_ipo",
#             "company":      title,
#             "doc_type":     doc_type,
#             "data_source":  extra.get("data_source", "unknown"),
#             "ipo_date":     extra.get("ipo_date",     ""),
#             "open_date":    extra.get("open_date",    ""),
#             "close_date":   extra.get("close_date",   ""),
#             "listing_date": extra.get("listing_date", ""),
#             "price_band":   extra.get("price_band",   ""),
#             "lot_size":     extra.get("lot_size",      ""),
#             "issue_size":   extra.get("issue_size",   ""),
#             "face_value":   extra.get("face_value",   ""),
#             "exchange":     extra.get("exchange",     ""),
#             "issue_type":   extra.get("issue_type",   ""),
#             "sale_type":    extra.get("sale_type",    ""),
#             "gmp":          extra.get("gmp",          ""),
#             "ipo_url":      extra.get("ipo_url",      link),
#             "url":          link,
#             "published":    pubdate,
#         }

#         if _validate_ipo_article(article, title):
#             articles.append(article)
#             src = extra.get("data_source","?")
#             print(f"[IPO FEED] ✅ Added (source={src}): {title[:50]}")
#         else:
#             print(f"[IPO FEED] ❌ Blocked (validation failed): {title[:50]}")

#     print(f"[IPO FEED] Final: {len(articles)} confirmed IPO articles")
#     return articles


# # ══════════════════════════════════════════════════════════════
# #  STANDALONE TEST — run: python RSS/ipo.py
# # ══════════════════════════════════════════════════════════════

# if __name__ == "__main__":

#     print("=" * 60)
#     print("  STEP 1 — Date Parser Test")
#     print("=" * 60)
#     for d in ["5 to 9 Jun, 2026", "29 May to 2 Jun, 2026",
#               "20 to 24 Mar, 2026", "30 Mar to 3 Apr, 2026"]:
#         open_d, close_d = _parse_ipo_date(d)
#         ok = "✅" if sum(1 for m in MONTHS if m in open_d.lower()) == 1 else "❌"
#         print(f"  {ok} '{d}'")
#         print(f"     → open : '{open_d}'")
#         print(f"     → close: '{close_d}'")

#     print("\n" + "=" * 60)
#     print("  STEP 2 — Normalize Key Test")
#     print("=" * 60)
#     names = [
#         "Hexagon Nutrition Limited",
#         "Hexagon Nutrition",
#         "Hexagon Nutrition IPO",
#         "HEXAGON NUTRITION LTD",
#     ]
#     for n in names:
#         key = _normalize_company_key(n)
#         print(f"  '{n}' → '{key}'")
#     print("  All should be: 'hexagon nutrition'")

#     print("\n" + "=" * 60)
#     print("  STEP 3 — Waterfall Scrape (Hexagon Nutrition)")
#     print("=" * 60)
#     result = _scrape_ipo_details("Hexagon Nutrition")
#     print(f"\ndata_source  : {result.get('data_source', 'N/A')}")
#     print(f"open_date    : {result.get('open_date',   'N/A')}")
#     print(f"close_date   : {result.get('close_date',  'N/A')}")
#     print(f"price_band   : {result.get('price_band',  'N/A')}")
#     print(f"lot_size     : {result.get('lot_size',     'N/A')}")

#     print("\n" + "=" * 60)
#     print("  STEP 4 — Cache Test (different name formats)")
#     print("=" * 60)
#     r1 = _scrape_ipo_details("Hexagon Nutrition Limited")
#     print(f"'Hexagon Nutrition Limited' → source: {r1.get('data_source')}")
#     r2 = _scrape_ipo_details("Hexagon Nutrition")
#     print(f"'Hexagon Nutrition'         → source: {r2.get('data_source')}")
#     print("Both should show 'cache hit' on second call ✅")

#     print("\n" + "=" * 60)
#     print("  STEP 5 — Full fetch_nse_ipo()")
#     print("=" * 60)
#     articles = fetch_nse_ipo(top_n=5)
#     print(f"\nTotal articles: {len(articles)}")
#     for i, a in enumerate(articles, 1):
#         print(f"\n[{i}] {a['Blog_Title']}")
#         print(f"     data_source  : {a.get('data_source', 'N/A')}")
#         print(f"     open_date    : {a.get('open_date',   'N/A')}")
#         print(f"     price_band   : {a.get('price_band',  'N/A')}")
#         print(f"     lot_size     : {a.get('lot_size',     'N/A')}")
#         print(f"     listing_date : {a.get('listing_date','N/A')}")








# import re
# import time
# import urllib.request
# import feedparser
# import requests
# from bs4 import BeautifulSoup
# import pandas as pd
# from datetime import datetime


# # ══════════════════════════════════════════════════════════════
# #  CONFIG
# # ══════════════════════════════════════════════════════════════

# # ── NSE Direct API (replaces XML feed) ───────────────────────
# NSE_HOME_URL    = "https://www.nseindia.com"
# NSE_IPO_URL     = "https://www.nseindia.com/market-data/all-upcoming-issues-ipo"
# NSE_CURRENT_API = "https://www.nseindia.com/api/all-upcoming-issues?category=ipo"
# NSE_SME_API     = "https://www.nseindia.com/api/all-upcoming-issues?category=sme"

# NSE_HEADERS = {
#     "User-Agent":      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
#                        "AppleWebKit/537.36 (KHTML, like Gecko) "
#                        "Chrome/124.0.0.0 Safari/537.36",
#     "Accept-Language": "en-US,en;q=0.9",
#     "Connection":      "keep-alive",
# }

# # Only these statuses = currently open for subscription
# CURRENT_STATUSES = {"active", "open", "live", "ongoing"}

# # ── Chittorgarh + fallback scrapers ──────────────────────────
# LIST_URLS = [
#     "https://www.chittorgarh.com/report/ipo-in-india-list-main-board-sme/82/all/",
#     "https://www.chittorgarh.com/report/ipo-in-india-list-main-board-sme/82/sme/",
# ]

# HEADERS_CHITTORGARH = {
#     "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
#                   "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
#     "Accept":     "text/html,application/xhtml+xml",
#     "Referer":    "https://www.chittorgarh.com/",
# }

# HEADERS_INVESTORGAIN = {
#     "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
#                   "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
#     "Accept":     "text/html,application/xhtml+xml",
#     "Referer":    "https://www.investorgain.com/",
# }

# HEADERS_MONEYCONTROL = {
#     "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
#                   "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
#     "Accept":     "text/html,application/xhtml+xml",
#     "Referer":    "https://www.moneycontrol.com/",
# }

# MONTHS = ["jan","feb","mar","apr","may","jun",
#           "jul","aug","sep","oct","nov","dec"]

# CACHE_TTL_HOURS = 6

# # ── In-memory caches ──────────────────────────────────────────
# _ipo_df_cache   = None
# _ipo_data_cache = {}


# # ══════════════════════════════════════════════════════════════
# #  NSE DIRECT API — get current IPO company names
# # ══════════════════════════════════════════════════════════════

# def _build_nse_session() -> requests.Session:
#     """Builds NSE session with cookies."""
#     session = requests.Session()
#     session.headers.update(NSE_HEADERS)

#     print(f"[NSE] Visiting homepage...")
#     try:
#         session.headers.update({"Accept": "text/html,application/xhtml+xml,*/*"})
#         r = session.get(NSE_HOME_URL, timeout=10)
#         print(f"[NSE] Homepage: {r.status_code} | "
#               f"cookies: {list(session.cookies.keys())}")
#         time.sleep(0.5)
#     except Exception as e:
#         print(f"[NSE] Homepage failed: {e}")

#     print(f"[NSE] Visiting IPO page...")
#     try:
#         session.headers.update({
#             "Referer": NSE_HOME_URL,
#             "Accept":  "text/html,application/xhtml+xml,*/*",
#         })
#         r = session.get(NSE_IPO_URL, timeout=10)
#         print(f"[NSE] IPO page: {r.status_code} | "
#               f"cookies: {list(session.cookies.keys())}")
#         time.sleep(0.5)
#     except Exception as e:
#         print(f"[NSE] IPO page failed: {e}")

#     return session


# def _fetch_nse_current_companies() -> list:
#     """
#     Fetches currently active IPO company names from NSE direct API.
#     Filters: Status = Active only (not Forthcoming/Upcoming).

#     Returns list of dicts:
#     [
#         {
#             "company_name": "CMR Green Technologies Limited",
#             "open_date":    "03-Jun-2026",
#             "close_date":   "05-Jun-2026",
#             "issue_price":  "Rs.182 to Rs.192",
#             "issue_size":   "23043930",
#             "issue_type":   "EQ",
#             "status":       "Active",
#         },
#         ...
#     ]
#     """
#     session = _build_nse_session()
#     session.headers.update({
#         "Referer":          NSE_IPO_URL,
#         "Accept":           "application/json, text/plain, */*",
#         "X-Requested-With": "XMLHttpRequest",
#     })

#     companies = []
#     seen      = set()

#     for api_url, label in [
#         (NSE_CURRENT_API, "mainboard"),
#         (NSE_SME_API,     "sme"),
#     ]:
#         try:
#             r = session.get(api_url, timeout=10)
#             print(f"[NSE] [{r.status_code}] {label}: {api_url}")

#             if r.status_code != 200:
#                 continue

#             raw = r.text.strip()
#             if not raw or raw in ("[]", "{}", "null"):
#                 print(f"[NSE] {label}: empty")
#                 continue

#             data  = r.json()
#             items = data if isinstance(data, list) else []

#             print(f"[NSE] {label}: {len(items)} total items")

#             for item in items:
#                 name   = (
#                     item.get("companyName") or
#                     item.get("name")        or
#                     item.get("issueName")   or
#                     ""
#                 ).strip()

#                 status = item.get("status", "").lower()

#                 if not name:
#                     continue

#                 # ── Filter: only currently active ─────────────
#                 if status not in CURRENT_STATUSES:
#                     print(f"[NSE] Skip [{item.get('status','?')}]: '{name}'")
#                     continue

#                 if name.lower() in seen:
#                     continue
#                 seen.add(name.lower())

#                 companies.append({
#                     "company_name": name,
#                     "open_date":    item.get("issueStartDate") or
#                                     item.get("openDate", ""),
#                     "close_date":   item.get("issueEndDate")   or
#                                     item.get("closeDate", ""),
#                     "issue_price":  item.get("issuePrice")     or
#                                     item.get("priceBand", ""),
#                     "issue_size":   item.get("issueSize", ""),
#                     "issue_type":   item.get("series")         or
#                                     item.get("issueType", ""),
#                     "status":       item.get("status", "Active"),
#                 })
#                 print(f"[NSE] ✅ Active: '{name}' "
#                       f"| {item.get('issueStartDate','')} "
#                       f"→ {item.get('issueEndDate','')}")

#         except Exception as e:
#             print(f"[NSE] {label} error: {e}")

#     print(f"[NSE] Current IPOs found: {len(companies)}")
#     return companies


# # ══════════════════════════════════════════════════════════════
# #  CACHE KEY NORMALIZER
# # ══════════════════════════════════════════════════════════════

# def _normalize_company_key(company_name: str) -> str:
#     return company_name.lower()\
#         .replace(" limited", "")\
#         .replace(" ltd",     "")\
#         .replace(" ipo",     "")\
#         .replace(" india",   "")\
#         .strip()


# # ══════════════════════════════════════════════════════════════
# #  CHITTORGARH — BUILD IPO URL MAP
# # ══════════════════════════════════════════════════════════════

# def _build_ipo_map() -> pd.DataFrame:
#     global _ipo_df_cache
#     if _ipo_df_cache is not None:
#         return _ipo_df_cache

#     print("[IPO] Building Chittorgarh IPO map...")
#     ipo_links = []

#     for url in LIST_URLS:
#         print(f"[IPO] Scraping list: {url}")
#         try:
#             response = requests.get(
#                 url, headers=HEADERS_CHITTORGARH, timeout=10
#             )
#             print(f"[IPO] Status: {response.status_code}")
#             soup = BeautifulSoup(response.text, "html.parser")

#             for a in soup.find_all("a", href=True):
#                 href = a["href"]
#                 name = a.get_text(strip=True)

#                 if any(skip in href for skip in [
#                     "ipo_dashboard", "ipo_perf_tracker",
#                     "ipo_discussions", "investorgain.com",
#                 ]):
#                     continue

#                 if ("/ipo/" in href and "-ipo/" in href and
#                         name and len(name) > 3):
#                     full_url = href if href.startswith("http") \
#                                else "https://www.chittorgarh.com" + href
#                     source   = url.split("/")[6] \
#                                if len(url.split("/")) > 6 else "list"
#                     ipo_links.append({
#                         "ipo_name": name,
#                         "url":      full_url,
#                         "source":   source,
#                     })

#         except Exception as e:
#             print(f"[IPO] List scrape error {url}: {e}")

#     if ipo_links:
#         df = pd.DataFrame(ipo_links).drop_duplicates(subset=["url"])
#         df["ipo_name_lower"] = df["ipo_name"].str.lower()
#     else:
#         df = pd.DataFrame(
#             columns=["ipo_name","url","source","ipo_name_lower"]
#         )

#     print(f"[IPO] Map built: {len(df)} unique IPOs")
#     if not df.empty:
#         print(df[["ipo_name", "url"]].to_string(index=False))

#     _ipo_df_cache = df
#     return df


# def _find_ipo_url(company_name: str, df: pd.DataFrame) -> str:
#     if df.empty:
#         return ""

#     name_clean = _normalize_company_key(company_name)

#     for _, row in df.iterrows():
#         key = row["ipo_name_lower"]
#         if name_clean in key or key in name_clean:
#             return row["url"]

#     words = [w for w in name_clean.split() if len(w) > 3]
#     for _, row in df.iterrows():
#         key     = row["ipo_name_lower"]
#         matches = sum(1 for w in words if w in key)
#         if matches >= 2:
#             return row["url"]

#     return ""


# # ══════════════════════════════════════════════════════════════
# #  DATE PARSER
# # ══════════════════════════════════════════════════════════════

# def _parse_ipo_date(value: str) -> tuple:
#     if " to " not in value.lower():
#         return value.strip(), ""

#     parts      = value.split(" to ")
#     open_part  = parts[0].strip()
#     close_part = parts[1].strip()

#     open_has_month = any(m in open_part.lower() for m in MONTHS)

#     if open_has_month:
#         year_match = re.search(r'\d{4}', close_part)
#         year_str   = f", {year_match.group()}" if year_match else ""
#         open_date  = f"{open_part}{year_str}"
#     else:
#         month_year = re.sub(r"^\d+\s*", "", close_part).strip()
#         open_date  = f"{open_part} {month_year}"

#     return open_date, close_part


# # ══════════════════════════════════════════════════════════════
# #  SCRAPER 1 — CHITTORGARH
# # ══════════════════════════════════════════════════════════════

# def _scrape_chittorgarh(company_name: str) -> dict:
#     df      = _build_ipo_map()
#     ipo_url = _find_ipo_url(company_name, df)

#     if not ipo_url:
#         print(f"[IPO] Chittorgarh: {company_name} not in map")
#         return {}

#     print(f"[IPO] Chittorgarh: {ipo_url}")

#     resp = requests.get(ipo_url, headers=HEADERS_CHITTORGARH, timeout=15)
#     soup = BeautifulSoup(resp.text, "html.parser")
#     data = {"ipo_url": ipo_url}

#     for table in soup.find_all("table"):
#         for row in table.find_all("tr"):
#             cols = row.find_all(["td","th"])
#             if len(cols) < 2:
#                 continue
#             key   = cols[0].get_text(strip=True).lower()
#             value = cols[1].get_text(strip=True)
#             if not key or not value:
#                 continue

#             if "ipo date" in key:
#                 data["ipo_date"] = value
#                 open_d, close_d  = _parse_ipo_date(value)
#                 data["open_date"]  = open_d
#                 data["close_date"] = close_d

#             if "listing date"       in key: data["listing_date"]    = value.rstrip("T").strip()
#             if "price band"         in key: data["price_band"]      = value
#             if "lot size"           in key: data["lot_size"]         = value
#             if "market lot"         in key: data["lot_size"]         = value
#             if "total issue size"   in key: data["issue_size"]      = value
#             if "issue size"         in key: data["issue_size"]      = value
#             if "face value"         in key: data["face_value"]      = value
#             if "listing at"         in key: data["exchange"]        = value
#             if "issue type"         in key: data["issue_type"]      = value
#             if "sale type"          in key: data["sale_type"]       = value
#             if "fresh issue"        in key: data["fresh_issue"]     = value
#             if "offer for sale"     in key: data["ofs"]             = value
#             if "min investment"     in key: data["min_investment"]  = value
#             if "registrar"          in key: data["registrar"]       = value
#             if "lead manager"       in key: data["lead_manager"]    = value
#             if "qib"                in key: data["qib_quota"]       = value
#             if "nii"                in key: data["nii_quota"]       = value
#             if "retail"             in key: data["retail_quota"]    = value
#             if "share holding pre"  in key: data["pre_issue_shares"]= value
#             if "share holding post" in key: data["post_issue_shares"]= value

#     for tag in soup.find_all(["td","span"]):
#         text = tag.get_text(strip=True)
#         if (len(text) < 30 and "₹" in text and
#                 ("grey market" in text.lower() or "gmp" in text.lower())):
#             data["gmp"] = text
#             break

#     company_lower = _normalize_company_key(company_name)
#     company_words = [w for w in company_lower.split() if len(w) > 3]
#     for div in soup.find_all("div", class_="accordion-body"):
#         text = div.get_text(strip=True)
#         if (len(text) > 80 and "ipo" in text.lower() and
#                 any(w in text.lower() for w in company_words)):
#             data["business"] = text[:500]
#             break

#     for div in soup.find_all("div", class_=True):
#         classes = " ".join(div.get("class",[]))
#         if "custom-ipo-table" in classes:
#             text = div.get_text(strip=True)
#             if "period ended" in text.lower() or "assets" in text.lower():
#                 data["financials"] = text[:300]
#                 break

#     match = re.search(r"Market Cap.*?₹([\d,.]+\s*Cr)", soup.get_text())
#     if match:
#         data["market_cap"] = "₹" + match.group(1)

#     print(f"[IPO] Chittorgarh fields: {list(data.keys())}")
#     return data


# # ══════════════════════════════════════════════════════════════
# #  SCRAPER 2 — INVESTORGAIN
# # ══════════════════════════════════════════════════════════════

# def _scrape_investorgain(company_name: str) -> dict:
#     print(f"[IPO] InvestorGain: searching for {company_name}...")

#     name_clean = _normalize_company_key(company_name)

#     for search_url in [
#         "https://www.investorgain.com/report/ipo-subscription-live/331/",
#         "https://www.investorgain.com/report/upcoming-ipo/331/",
#     ]:
#         resp = requests.get(
#             search_url, headers=HEADERS_INVESTORGAIN, timeout=15
#         )
#         soup = BeautifulSoup(resp.text, "html.parser")

#         ipo_url = ""
#         for a in soup.find_all("a", href=True):
#             text = a.get_text(strip=True).lower()
#             href = a["href"]
#             if name_clean[:8] in text and "/ipo/" in href:
#                 ipo_url = href
#                 if not ipo_url.startswith("http"):
#                     ipo_url = "https://www.investorgain.com" + ipo_url
#                 break

#         if ipo_url:
#             break

#     if not ipo_url:
#         print(f"[IPO] InvestorGain: {company_name} not found")
#         return {}

#     print(f"[IPO] InvestorGain: {ipo_url}")
#     resp2 = requests.get(ipo_url, headers=HEADERS_INVESTORGAIN, timeout=15)
#     soup2 = BeautifulSoup(resp2.text, "html.parser")
#     data  = {"ipo_url": ipo_url}

#     for row in soup2.find_all("tr"):
#         cols = row.find_all(["td","th"])
#         if len(cols) < 2:
#             continue
#         key   = cols[0].get_text(strip=True).lower()
#         value = cols[1].get_text(strip=True)
#         if not key or not value:
#             continue

#         if "open date" in key or "ipo date" in key:
#             open_d, close_d  = _parse_ipo_date(value)
#             data["open_date"]  = open_d
#             data["close_date"] = close_d
#             data["ipo_date"]   = value
#         if "close date"     in key: data["close_date"]    = value
#         if "listing date"   in key: data["listing_date"]  = value.rstrip("T").strip()
#         if "price band"     in key: data["price_band"]    = value
#         if "lot size"       in key: data["lot_size"]       = value
#         if "issue size"     in key: data["issue_size"]    = value
#         if "face value"     in key: data["face_value"]    = value
#         if "listing at"     in key: data["exchange"]      = value
#         if "issue type"     in key: data["issue_type"]    = value
#         if "min investment" in key: data["min_investment"]= value

#     print(f"[IPO] InvestorGain fields: {list(data.keys())}")
#     return data


# # ══════════════════════════════════════════════════════════════
# #  SCRAPER 3 — MONEYCONTROL
# # ══════════════════════════════════════════════════════════════

# def _scrape_moneycontrol(company_name: str) -> dict:
#     print(f"[IPO] Moneycontrol: searching for {company_name}...")

#     name_clean = _normalize_company_key(company_name)
#     name_short = name_clean.split()[0]

#     search_url = "https://www.moneycontrol.com/ipo"
#     resp = requests.get(search_url, headers=HEADERS_MONEYCONTROL, timeout=15)
#     soup = BeautifulSoup(resp.text, "html.parser")

#     ipo_url = ""
#     for a in soup.find_all("a", href=True):
#         text = a.get_text(strip=True).lower()
#         href = a["href"]
#         if (name_short in text and
#                 "ipo" in href.lower() and
#                 "moneycontrol.com" in href):
#             ipo_url = href
#             break

#     data = {}

#     if ipo_url:
#         print(f"[IPO] Moneycontrol: {ipo_url}")
#         resp2     = requests.get(ipo_url, headers=HEADERS_MONEYCONTROL, timeout=15)
#         soup2     = BeautifulSoup(resp2.text, "html.parser")
#         full_text = soup2.get_text()
#     else:
#         full_text = soup.get_text()
#         idx       = full_text.lower().find(name_short)
#         full_text = full_text[idx:idx+600] if idx != -1 else ""

#     if full_text:
#         m = re.search(r'₹[\d,]+\s*(?:to|-)\s*₹[\d,]+', full_text)
#         if m: data["price_band"] = m.group()

#         m = re.search(
#             r'(\w+ \d{1,2},?\s*\d{4})\s*(?:to|-)\s*(\w+ \d{1,2},?\s*\d{4})',
#             full_text
#         )
#         if m:
#             data["open_date"]  = m.group(1).strip()
#             data["close_date"] = m.group(2).strip()

#         m = re.search(r'(\d[\d,]*)\s*shares', full_text, re.IGNORECASE)
#         if m: data["lot_size"] = f"{m.group(1)} Shares"

#         m = re.search(r'₹([\d,.]+\s*(?:Cr|crore))', full_text, re.IGNORECASE)
#         if m: data["issue_size"] = f"₹{m.group(1)}"

#         m = re.search(
#             r'(?:listing|list)\s*(?:date|on)[:\s]+(\w+ \d{1,2},?\s*\d{4})',
#             full_text, re.IGNORECASE
#         )
#         if m: data["listing_date"] = m.group(1).strip()

#     if data:
#         print(f"[IPO] Moneycontrol fields: {list(data.keys())}")
#     else:
#         print(f"[IPO] Moneycontrol: no data found for {company_name}")

#     return data


# # ══════════════════════════════════════════════════════════════
# #  WATERFALL SCRAPER + CACHE
# # ══════════════════════════════════════════════════════════════

# def _scrape_ipo_details(company_name: str) -> dict:
#     cache_key = _normalize_company_key(company_name)

#     if cache_key in _ipo_data_cache:
#         cached_data, cached_at = _ipo_data_cache[cache_key]
#         age_hours = (datetime.now() - cached_at).total_seconds() / 3600
#         if age_hours < CACHE_TTL_HOURS:
#             src = cached_data.get("data_source", "cache")
#             print(f"[IPO] Cache hit: '{cache_key}' "
#                   f"(age={age_hours:.1f}h source={src})")
#             return cached_data
#         else:
#             print(f"[IPO] Cache stale: '{cache_key}' — re-fetching")

#     scrapers = [
#         ("Chittorgarh",  _scrape_chittorgarh),
#         ("InvestorGain", _scrape_investorgain),
#         ("Moneycontrol", _scrape_moneycontrol),
#     ]

#     for source_name, scraper_fn in scrapers:
#         try:
#             data = scraper_fn(company_name)

#             if data.get("price_band") or data.get("open_date"):
#                 data["data_source"]        = source_name
#                 _ipo_data_cache[cache_key] = (data, datetime.now())
#                 print(f"[IPO] ✅ {source_name} → cached (key='{cache_key}')")
#                 return data
#             else:
#                 print(f"[IPO] {source_name} → no usable data, trying next...")

#         except Exception as e:
#             print(f"[IPO] {source_name} failed: {e} → trying next...")

#     if cache_key in _ipo_data_cache:
#         stale_data, cached_at = _ipo_data_cache[cache_key]
#         age_hours = (datetime.now() - cached_at).total_seconds() / 3600
#         print(f"[IPO] ⚠️  Using stale cache (age={age_hours:.1f}h)")
#         stale_data["data_source"] = "cache_stale"
#         return stale_data

#     print(f"[IPO] ❌ All sources failed: {company_name}")
#     return {}


# # ══════════════════════════════════════════════════════════════
# #  VALIDATE
# # ══════════════════════════════════════════════════════════════

# def _validate_ipo_article(article: dict, company: str) -> bool:
#     warnings = []
#     errors   = []

#     open_date = article.get("open_date", "")
#     if open_date:
#         month_count = sum(1 for m in MONTHS if m in open_date.lower())
#         if month_count > 1:
#             errors.append(f"open_date has {month_count} month names: '{open_date}'")
#         if month_count == 0:
#             warnings.append(f"open_date has no month: '{open_date}'")
#         if not re.search(r'\d{4}', open_date):
#             warnings.append(f"open_date has no year: '{open_date}'")

#     close_date = article.get("close_date", "")
#     if close_date:
#         month_count = sum(1 for m in MONTHS if m in close_date.lower())
#         if month_count > 1:
#             errors.append(f"close_date has {month_count} month names: '{close_date}'")

#     price = article.get("price_band", "")
#     if price and price != "TBA" and "₹" not in price:
#         warnings.append(f"price_band missing ₹: '{price}'")

#     lot = article.get("lot_size", "")
#     if lot:
#         lot_num = lot.replace(" Shares","").replace(",","").strip()
#         if not lot_num.isdigit():
#             warnings.append(f"lot_size not a number: '{lot}'")

#     src = article.get("data_source", "unknown")

#     if errors:
#         print(f"[IPO VALIDATE] ❌ {company} (source={src})")
#         for e in errors:
#             print(f"[IPO VALIDATE]    ERROR: {e}")
#         return False

#     if warnings:
#         print(f"[IPO VALIDATE] ⚠️  {company} (source={src})")
#         for w in warnings:
#             print(f"[IPO VALIDATE]    WARNING: {w}")
#     else:
#         print(f"[IPO VALIDATE] ✅ {company} (source={src})")

#     return True


# # ══════════════════════════════════════════════════════════════
# #  BUILD BLOG TITLE + CONTENT
# # ══════════════════════════════════════════════════════════════

# def _build_blog_title(company: str, nse_data: dict, extra: dict) -> str:
#     status = nse_data.get("status", "Active")
#     price  = extra.get("price_band") or nse_data.get("issue_price", "")
#     open_d = extra.get("open_date")  or nse_data.get("open_date", "")

#     if price and open_d:
#         return (f"Should You Apply for {company} IPO "
#                 f"at {price} — Opens {open_d}?")
#     elif price:
#         return f"{company} IPO at {price} — Should You Apply or Avoid?"
#     elif open_d:
#         return f"{company} IPO Opens {open_d} — Apply or Avoid?"
#     else:
#         return f"{company} IPO Now Open — Should You Invest Today?"


# def _build_blog_content(company: str, nse_data: dict,
#                         extra: dict) -> str:
#     """
#     Builds rich blog content combining:
#     - NSE direct API data (confirmed open/close dates, price, size)
#     - Chittorgarh/waterfall data (lot size, GMP, business, financials)
#     """
#     # Prefer extra (Chittorgarh) for detailed fields
#     # Fall back to nse_data for basic fields
#     return f"""
# Company        : {company}
# Status         : {nse_data.get('status',       'Active')}
# Data Source    : {extra.get('data_source',      'NSE Direct')}

# IPO Date       : {extra.get('ipo_date',         'See open/close dates')}
# Open Date      : {extra.get('open_date')  or nse_data.get('open_date',  'To be announced')}
# Close Date     : {extra.get('close_date') or nse_data.get('close_date', 'To be announced')}
# Listing Date   : {extra.get('listing_date',     'To be announced')}
# Price Band     : {extra.get('price_band')  or nse_data.get('issue_price','To be announced')}
# Lot Size       : {extra.get('lot_size',          'To be announced')}
# Issue Size     : {extra.get('issue_size')  or nse_data.get('issue_size', 'To be announced')}
# Min Investment : {extra.get('min_investment',   'To be announced')}
# Face Value     : {extra.get('face_value',       'To be announced')}
# Exchange       : {extra.get('exchange',         'NSE / BSE')}
# Issue Type     : {extra.get('issue_type')  or nse_data.get('issue_type', 'Book Built Issue')}
# Sale Type      : {extra.get('sale_type',        'To be announced')}
# Fresh Issue    : {extra.get('fresh_issue',      'To be announced')}
# OFS            : {extra.get('ofs',              'To be announced')}
# GMP            : {extra.get('gmp',              'Not available yet')}
# QIB Quota      : {extra.get('qib_quota',        'To be announced')}
# NII Quota      : {extra.get('nii_quota',        'To be announced')}
# Retail Quota   : {extra.get('retail_quota',     'To be announced')}
# Registrar      : {extra.get('registrar',        'To be announced')}
# Lead Manager   : {extra.get('lead_manager',     'To be announced')}
# Business       : {extra.get('business',          company + ' is currently open for IPO subscription.')}

# Write a complete IPO analysis blog covering all the details above.
# For fields showing "To be announced" mention they will be revealed soon.
# Include: company background, IPO details, GMP analysis,
# should investors apply (pros and cons), how to apply via UPI/ASBA,
# and final recommendation.
#     """.strip()


# # ══════════════════════════════════════════════════════════════
# #  MAIN FETCHER — fetch_nse_ipo()
# # ══════════════════════════════════════════════════════════════

# def fetch_nse_ipo() -> list:
#     """
#     Fetches currently active IPOs from NSE direct API.
#     Enriches each with full details from:
#       Chittorgarh → InvestorGain → Moneycontrol → stale cache

#     Flow:
#       Step 1 — NSE API → get company names (Active only)
#       Step 2 — For each company → waterfall scrape details
#       Step 3 — Validate → add to articles list
#     """
#     articles = []

#     # ── Step 1: Get current IPO company names from NSE ────────
#     print(f"\n[IPO FEED] Fetching current IPOs from NSE...")
#     current_ipos = _fetch_nse_current_companies()

#     if not current_ipos:
#         print(f"[IPO FEED] No active IPOs found on NSE today")
#         return []

#     print(f"[IPO FEED] {len(current_ipos)} active IPOs to process")

#     # ── Step 2: Enrich each company with waterfall scraper ────
#     for nse_item in current_ipos:
#         company = nse_item["company_name"]
#         print(f"\n[IPO FEED] Processing: '{company}'")

#         extra = _scrape_ipo_details(company)

#         # ── Step 3: Build article ─────────────────────────────
#         # Use NSE data as base, enrich with waterfall data
#         article = {
#             "Blog_Title":   _build_blog_title(company, nse_item, extra),
#             "Blog_Content": _build_blog_content(company, nse_item, extra),
#             "source":       "nse_ipo",
#             "company":      company,
#             "doc_type":     "CURRENT",
#             "data_source":  extra.get("data_source", "nse_direct"),

#             # Dates — prefer waterfall, fallback to NSE direct
#             "ipo_date":     extra.get("ipo_date",     ""),
#             "open_date":    extra.get("open_date")    or nse_item.get("open_date",  ""),
#             "close_date":   extra.get("close_date")   or nse_item.get("close_date", ""),
#             "listing_date": extra.get("listing_date", ""),

#             # Pricing — prefer waterfall, fallback to NSE direct
#             "price_band":   extra.get("price_band")   or nse_item.get("issue_price",""),
#             "lot_size":     extra.get("lot_size",      ""),
#             "issue_size":   extra.get("issue_size")   or nse_item.get("issue_size", ""),

#             # Details
#             "face_value":   extra.get("face_value",   ""),
#             "exchange":     extra.get("exchange",     ""),
#             "issue_type":   extra.get("issue_type")   or nse_item.get("issue_type", ""),
#             "sale_type":    extra.get("sale_type",    ""),
#             "gmp":          extra.get("gmp",          ""),
#             "market_cap":   extra.get("market_cap",   ""),
#             "ipo_url":      extra.get("ipo_url",      ""),
#             "status":       nse_item.get("status",    "Active"),
#             "published":    nse_item.get("open_date", ""),
#         }

#         if _validate_ipo_article(article, company):
#             articles.append(article)
#             print(f"[IPO FEED] ✅ Added: '{company}' "
#                   f"(source={article['data_source']})")
#         else:
#             # Even if validation fails — still add with NSE base data
#             # so the pipeline doesn't miss active IPOs
#             print(f"[IPO FEED] ⚠️  Validation warning — adding anyway: '{company}'")
#             articles.append(article)

#     print(f"\n[IPO FEED] Final: {len(articles)} confirmed IPO articles")
#     return articles


# # ══════════════════════════════════════════════════════════════
# #  STANDALONE TEST
# # ══════════════════════════════════════════════════════════════

# if __name__ == "__main__":
#     print("=" * 60)
#     print("  fetch_nse_ipo() — Current IPOs with Full Details")
#     print("=" * 60)

#     articles = fetch_nse_ipo()

#     print(f"\nTotal: {len(articles)}")
#     print("=" * 60)

#     for i, a in enumerate(articles, 1):
#         print(f"\n[{i}] {a['Blog_Title']}")
#         print(f"     company      : {a['company']}")
#         print(f"     status       : {a['status']}")
#         print(f"     data_source  : {a['data_source']}")
#         print(f"     open_date    : {a.get('open_date',   'N/A')}")
#         print(f"     close_date   : {a.get('close_date',  'N/A')}")
#         print(f"     price_band   : {a.get('price_band',  'N/A')}")
#         print(f"     lot_size     : {a.get('lot_size',     'N/A')}")
#         print(f"     listing_date : {a.get('listing_date','N/A')}")
#         print(f"     gmp          : {a.get('gmp',         'N/A')}")

# RSS/ipo.py

import re
import time
import urllib.request
import feedparser
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime


# ══════════════════════════════════════════════════════════════
#  CONFIG
# ══════════════════════════════════════════════════════════════

NSE_HOME_URL    = "https://www.nseindia.com"
NSE_IPO_URL     = "https://www.nseindia.com/market-data/all-upcoming-issues-ipo"
NSE_CURRENT_API = "https://www.nseindia.com/api/all-upcoming-issues?category=ipo"
NSE_SME_API     = "https://www.nseindia.com/api/all-upcoming-issues?category=sme"

NSE_HEADERS = {
    "User-Agent":      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection":      "keep-alive",
}

CURRENT_STATUSES = {"active", "open", "live", "ongoing"}

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

MONTHS = ["jan","feb","mar","apr","may","jun",
          "jul","aug","sep","oct","nov","dec"]

CACHE_TTL_HOURS = 6

_ipo_df_cache   = None
_ipo_data_cache = {}


# ══════════════════════════════════════════════════════════════
#  NSE SESSION
# ══════════════════════════════════════════════════════════════

def _build_nse_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(NSE_HEADERS)

    print(f"[NSE] Visiting homepage...")
    try:
        session.headers.update({"Accept": "text/html,application/xhtml+xml,*/*"})
        r = session.get(NSE_HOME_URL, timeout=10)
        print(f"[NSE] Homepage: {r.status_code} | "
              f"cookies: {list(session.cookies.keys())}")
        time.sleep(0.5)
    except Exception as e:
        print(f"[NSE] Homepage failed: {e}")

    print(f"[NSE] Visiting IPO page...")
    try:
        session.headers.update({
            "Referer": NSE_HOME_URL,
            "Accept":  "text/html,application/xhtml+xml,*/*",
        })
        r = session.get(NSE_IPO_URL, timeout=10)
        print(f"[NSE] IPO page: {r.status_code} | "
              f"cookies: {list(session.cookies.keys())}")
        time.sleep(0.5)
    except Exception as e:
        print(f"[NSE] IPO page failed: {e}")

    return session


# ══════════════════════════════════════════════════════════════
#  SELENIUM SCRAPER — catches SME IPOs missed by API
# ══════════════════════════════════════════════════════════════

def _scrape_nse_page_selenium() -> list:
    """
    Scrapes NSE IPO current issues page using Selenium.
    Handles JavaScript-rendered table that API misses (SME IPOs).
    Returns list of active IPO company dicts.
    """
    companies = []

    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from webdriver_manager.chrome import ChromeDriverManager

        print(f"[NSE SELENIUM] Starting Chrome headless...")

        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36"
        )

        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )

        print(f"[NSE SELENIUM] Loading NSE IPO page...")
        driver.get(NSE_IPO_URL)

        # Wait for table to appear
        wait = WebDriverWait(driver, 15)
        wait.until(
            EC.presence_of_element_located((By.TAG_NAME, "table"))
        )

        # Extra wait for JS data to render
        time.sleep(3)

        # ── Parse table rows ──────────────────────────────────
        rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
        print(f"[NSE SELENIUM] Found {len(rows)} table rows")

        for row in rows:
            try:
                cols = row.find_elements(By.TAG_NAME, "td")
                if len(cols) < 5:
                    continue

                company_name  = cols[0].text.strip()
                security_type = cols[1].text.strip()
                start_date    = cols[2].text.strip()
                end_date      = cols[3].text.strip()
                status        = cols[4].text.strip()

                if not company_name:
                    continue

                if status.lower() not in CURRENT_STATUSES:
                    print(f"[NSE SELENIUM] Skip [{status}]: '{company_name}'")
                    continue

                companies.append({
                    "company_name": company_name,
                    "open_date":    start_date,
                    "close_date":   end_date,
                    "issue_price":  "",
                    "issue_size":   "",
                    "issue_type":   security_type,
                    "status":       status,
                })
                print(f"[NSE SELENIUM] ✅ '{company_name}' "
                      f"[{security_type}] | {start_date} → {end_date}")

            except Exception as e:
                print(f"[NSE SELENIUM] Row parse error: {e}")

        driver.quit()
        print(f"[NSE SELENIUM] Done: {len(companies)} companies")

    except ImportError:
        print(f"[NSE SELENIUM] Not installed — run: "
              f"pip install selenium webdriver-manager")
    except Exception as e:
        print(f"[NSE SELENIUM] Failed: {e}")

    return companies


# ══════════════════════════════════════════════════════════════
#  FETCH CURRENT COMPANIES
#  Step 1 — API (mainboard + sme)
#  Step 2 — Selenium (catches SME IPOs API misses)
# ══════════════════════════════════════════════════════════════

def _fetch_nse_current_companies() -> list:
    """
    Fetches all currently active IPO company names from NSE.

    Two-step approach:
      Step 1 — NSE direct API (fast)
               mainboard API → EQ type IPOs
               SME API       → SME type IPOs (often returns empty)

      Step 2 — Selenium page scrape (catches what API misses)
               Loads actual NSE page in headless Chrome
               Scrapes rendered table → all active IPOs

      Dedup between both sources — no duplicates.
    """
    companies = []
    seen      = set()

    # ── Step 1: Direct API ────────────────────────────────────
    print(f"[NSE] Step 1: Direct API fetch...")
    session = _build_nse_session()
    session.headers.update({
        "Referer":          NSE_IPO_URL,
        "Accept":           "application/json, text/plain, */*",
        "X-Requested-With": "XMLHttpRequest",
    })

    for api_url, label in [
        (NSE_CURRENT_API, "mainboard"),
        (NSE_SME_API,     "sme"),
    ]:
        try:
            r = session.get(api_url, timeout=10)
            print(f"[NSE] [{r.status_code}] {label}")

            if r.status_code != 200:
                continue

            raw = r.text.strip()
            if not raw or raw in ("[]", "{}", "null"):
                print(f"[NSE] {label}: empty")
                continue

            data  = r.json()
            items = data if isinstance(data, list) else []

            if isinstance(data, dict):
                for key in ["data", "upcoming", "ipo", "results"]:
                    if isinstance(data.get(key), list):
                        items = data[key]
                        break

            print(f"[NSE] {label}: {len(items)} items")

            for item in items:
                name   = (item.get("companyName") or "").strip()
                status = item.get("status", "").lower()

                if not name:
                    continue

                if status not in CURRENT_STATUSES:
                    print(f"[NSE] Skip [{item.get('status','?')}]: '{name}'")
                    continue

                if name.lower() in seen:
                    continue
                seen.add(name.lower())

                companies.append({
                    "company_name": name,
                    "open_date":    item.get("issueStartDate") or
                                    item.get("openDate", ""),
                    "close_date":   item.get("issueEndDate")   or
                                    item.get("closeDate", ""),
                    "issue_price":  item.get("issuePrice")     or
                                    item.get("priceBand", ""),
                    "issue_size":   item.get("issueSize", ""),
                    "issue_type":   item.get("series")         or
                                    item.get("issueType", ""),
                    "status":       item.get("status", "Active"),
                })
                print(f"[NSE] ✅ API: '{name}' "
                      f"[{item.get('series','?')}] "
                      f"| {item.get('issueStartDate','')} "
                      f"→ {item.get('issueEndDate','')}")

        except Exception as e:
            print(f"[NSE] API error ({label}): {e}")

    api_count = len(companies)
    print(f"[NSE] API found: {api_count} companies")

    # ── Step 2: Selenium scrape ───────────────────────────────
    print(f"\n[NSE] Step 2: Selenium scrape for missing SME IPOs...")
    selenium_companies = _scrape_nse_page_selenium()

    added_by_selenium = 0
    for item in selenium_companies:
        name = item["company_name"]
        if name.lower() not in seen:
            seen.add(name.lower())
            companies.append(item)
            added_by_selenium += 1
            print(f"[NSE] ✅ Selenium added: '{name}' "
                  f"[{item.get('issue_type','?')}]")
        else:
            print(f"[NSE] Selenium dedup (already from API): '{name}'")

    print(f"\n[NSE] Summary:")
    print(f"[NSE]   API found       : {api_count}")
    print(f"[NSE]   Selenium added  : {added_by_selenium}")
    print(f"[NSE]   Total           : {len(companies)}")

    return companies


# ══════════════════════════════════════════════════════════════
#  CACHE KEY NORMALIZER
# ══════════════════════════════════════════════════════════════

def _normalize_company_key(company_name: str) -> str:
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
#  SCRAPER 1 — CHITTORGARH
# ══════════════════════════════════════════════════════════════

def _scrape_chittorgarh(company_name: str) -> dict:
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

            if "listing date"       in key: data["listing_date"]     = value.rstrip("T").strip()
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

    for tag in soup.find_all(["td","span"]):
        text = tag.get_text(strip=True)
        if (len(text) < 30 and "₹" in text and
                ("grey market" in text.lower() or "gmp" in text.lower())):
            data["gmp"] = text
            break

    company_lower = _normalize_company_key(company_name)
    company_words = [w for w in company_lower.split() if len(w) > 3]
    for div in soup.find_all("div", class_="accordion-body"):
        text = div.get_text(strip=True)
        if (len(text) > 80 and "ipo" in text.lower() and
                any(w in text.lower() for w in company_words)):
            data["business"] = text[:500]
            break

    for div in soup.find_all("div", class_=True):
        classes = " ".join(div.get("class",[]))
        if "custom-ipo-table" in classes:
            text = div.get_text(strip=True)
            if "period ended" in text.lower() or "assets" in text.lower():
                data["financials"] = text[:300]
                break

    match = re.search(r"Market Cap.*?₹([\d,.]+\s*Cr)", soup.get_text())
    if match:
        data["market_cap"] = "₹" + match.group(1)

    print(f"[IPO] Chittorgarh fields: {list(data.keys())}")
    return data


# ══════════════════════════════════════════════════════════════
#  SCRAPER 2 — INVESTORGAIN
# ══════════════════════════════════════════════════════════════

def _scrape_investorgain(company_name: str) -> dict:
    print(f"[IPO] InvestorGain: searching for {company_name}...")

    name_clean = _normalize_company_key(company_name)

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
            open_d, close_d    = _parse_ipo_date(value)
            data["open_date"]  = open_d
            data["close_date"] = close_d
            data["ipo_date"]   = value
        if "close date"     in key: data["close_date"]    = value
        if "listing date"   in key: data["listing_date"]  = value.rstrip("T").strip()
        if "price band"     in key: data["price_band"]    = value
        if "lot size"       in key: data["lot_size"]       = value
        if "issue size"     in key: data["issue_size"]    = value
        if "face value"     in key: data["face_value"]    = value
        if "listing at"     in key: data["exchange"]      = value
        if "issue type"     in key: data["issue_type"]    = value
        if "min investment" in key: data["min_investment"]= value

    print(f"[IPO] InvestorGain fields: {list(data.keys())}")
    return data


# ══════════════════════════════════════════════════════════════
#  SCRAPER 3 — MONEYCONTROL
# ══════════════════════════════════════════════════════════════

def _scrape_moneycontrol(company_name: str) -> dict:
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
        resp2     = requests.get(ipo_url, headers=HEADERS_MONEYCONTROL, timeout=15)
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
#  WATERFALL SCRAPER + CACHE
# ══════════════════════════════════════════════════════════════

def _scrape_ipo_details(company_name: str) -> dict:
    cache_key = _normalize_company_key(company_name)

    if cache_key in _ipo_data_cache:
        cached_data, cached_at = _ipo_data_cache[cache_key]
        age_hours = (datetime.now() - cached_at).total_seconds() / 3600
        if age_hours < CACHE_TTL_HOURS:
            src = cached_data.get("data_source", "cache")
            print(f"[IPO] Cache hit: '{cache_key}' "
                  f"(age={age_hours:.1f}h source={src})")
            return cached_data
        else:
            print(f"[IPO] Cache stale: '{cache_key}' — re-fetching")

    scrapers = [
        ("Chittorgarh",  _scrape_chittorgarh),
        ("InvestorGain", _scrape_investorgain),
        ("Moneycontrol", _scrape_moneycontrol),
    ]

    for source_name, scraper_fn in scrapers:
        try:
            data = scraper_fn(company_name)

            if data.get("price_band") or data.get("open_date"):
                data["data_source"]        = source_name
                _ipo_data_cache[cache_key] = (data, datetime.now())
                print(f"[IPO] ✅ {source_name} → cached (key='{cache_key}')")
                return data
            else:
                print(f"[IPO] {source_name} → no usable data, trying next...")

        except Exception as e:
            print(f"[IPO] {source_name} failed: {e} → trying next...")

    if cache_key in _ipo_data_cache:
        stale_data, cached_at = _ipo_data_cache[cache_key]
        age_hours = (datetime.now() - cached_at).total_seconds() / 3600
        print(f"[IPO] ⚠️  Using stale cache (age={age_hours:.1f}h)")
        stale_data["data_source"] = "cache_stale"
        return stale_data

    print(f"[IPO] ❌ All sources failed: {company_name}")
    return {}


# ══════════════════════════════════════════════════════════════
#  VALIDATE
# ══════════════════════════════════════════════════════════════

def _validate_ipo_article(article: dict, company: str) -> bool:
    warnings = []
    errors   = []

    open_date = article.get("open_date", "")
    if open_date:
        month_count = sum(1 for m in MONTHS if m in open_date.lower())
        if month_count > 1:
            errors.append(f"open_date has {month_count} month names: '{open_date}'")
        if month_count == 0:
            warnings.append(f"open_date has no month: '{open_date}'")
        if not re.search(r'\d{4}', open_date):
            warnings.append(f"open_date has no year: '{open_date}'")

    close_date = article.get("close_date", "")
    if close_date:
        month_count = sum(1 for m in MONTHS if m in close_date.lower())
        if month_count > 1:
            errors.append(f"close_date has {month_count} month names: '{close_date}'")

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
            print(f"[IPO VALIDATE]    ERROR: {e}")
        return False

    if warnings:
        print(f"[IPO VALIDATE] ⚠️  {company} (source={src})")
        for w in warnings:
            print(f"[IPO VALIDATE]    WARNING: {w}")
    else:
        print(f"[IPO VALIDATE] ✅ {company} (source={src})")

    return True


# ══════════════════════════════════════════════════════════════
#  BUILD BLOG TITLE + CONTENT
# ══════════════════════════════════════════════════════════════

def _build_blog_title(company: str, nse_data: dict, extra: dict) -> str:
    price  = extra.get("price_band") or nse_data.get("issue_price", "")
    open_d = extra.get("open_date")  or nse_data.get("open_date",   "")

    if price and open_d:
        return (f"Should You Apply for {company} IPO "
                f"at {price} — Opens {open_d}?")
    elif price:
        return f"{company} IPO at {price} — Should You Apply or Avoid?"
    elif open_d:
        return f"{company} IPO Opens {open_d} — Apply or Avoid?"
    else:
        return f"{company} IPO Now Open — Should You Invest Today?"


def _build_blog_content(company: str, nse_data: dict, extra: dict) -> str:
    return f"""
Company        : {company}
Status         : {nse_data.get('status',       'Active')}
Data Source    : {extra.get('data_source',      'NSE Direct')}

IPO Date       : {extra.get('ipo_date',         'See open/close dates')}
Open Date      : {extra.get('open_date')  or nse_data.get('open_date',  'To be announced')}
Close Date     : {extra.get('close_date') or nse_data.get('close_date', 'To be announced')}
Listing Date   : {extra.get('listing_date',     'To be announced')}
Price Band     : {extra.get('price_band')  or nse_data.get('issue_price','To be announced')}
Lot Size       : {extra.get('lot_size',          'To be announced')}
Issue Size     : {extra.get('issue_size')  or nse_data.get('issue_size', 'To be announced')}
Min Investment : {extra.get('min_investment',   'To be announced')}
Face Value     : {extra.get('face_value',       'To be announced')}
Exchange       : {extra.get('exchange',         'NSE / BSE')}
Issue Type     : {extra.get('issue_type')  or nse_data.get('issue_type', 'Book Built Issue')}
Sale Type      : {extra.get('sale_type',        'To be announced')}
Fresh Issue    : {extra.get('fresh_issue',      'To be announced')}
OFS            : {extra.get('ofs',              'To be announced')}
GMP            : {extra.get('gmp',              'Not available yet')}
QIB Quota      : {extra.get('qib_quota',        'To be announced')}
NII Quota      : {extra.get('nii_quota',        'To be announced')}
Retail Quota   : {extra.get('retail_quota',     'To be announced')}
Registrar      : {extra.get('registrar',        'To be announced')}
Lead Manager   : {extra.get('lead_manager',     'To be announced')}
Business       : {extra.get('business', company + ' is currently open for IPO subscription.')}

Write a complete IPO analysis blog covering all the details above.
For fields showing "To be announced" mention they will be revealed soon.
Include: company background, IPO details, GMP analysis,
should investors apply (pros and cons), how to apply via UPI/ASBA,
and final recommendation.
    """.strip()


# ══════════════════════════════════════════════════════════════
#  MAIN FETCHER
# ══════════════════════════════════════════════════════════════

def fetch_nse_ipo() -> list:
    """
    Fetches all currently active IPOs from NSE.

    Flow:
      Step 1 — NSE API → mainboard IPOs (EQ)
      Step 2 — Selenium → catches SME IPOs API misses
      Step 3 — Waterfall scrape → Chittorgarh/InvestorGain/Moneycontrol
      Step 4 — Validate → add to articles list
    """
    articles = []

    print(f"\n[IPO FEED] Fetching current IPOs from NSE...")
    current_ipos = _fetch_nse_current_companies()

    if not current_ipos:
        print(f"[IPO FEED] No active IPOs found on NSE today")
        return []

    print(f"[IPO FEED] {len(current_ipos)} active IPOs to process")

    for nse_item in current_ipos:
        company = nse_item["company_name"]
        print(f"\n[IPO FEED] Processing: '{company}'")

        extra = _scrape_ipo_details(company)

        article = {
            "Blog_Title":   _build_blog_title(company, nse_item, extra),
            "Blog_Content": _build_blog_content(company, nse_item, extra),
            "source":       "nse_ipo",
            "company":      company,
            "doc_type":     "CURRENT",
            "data_source":  extra.get("data_source", "nse_direct"),
            "ipo_date":     extra.get("ipo_date",     ""),
            "open_date":    extra.get("open_date")    or nse_item.get("open_date",  ""),
            "close_date":   extra.get("close_date")   or nse_item.get("close_date", ""),
            "listing_date": extra.get("listing_date", ""),
            "price_band":   extra.get("price_band")   or nse_item.get("issue_price",""),
            "lot_size":     extra.get("lot_size",      ""),
            "issue_size":   extra.get("issue_size")   or nse_item.get("issue_size", ""),
            "face_value":   extra.get("face_value",   ""),
            "exchange":     extra.get("exchange",     ""),
            "issue_type":   extra.get("issue_type")   or nse_item.get("issue_type", ""),
            "sale_type":    extra.get("sale_type",    ""),
            "gmp":          extra.get("gmp",          ""),
            "market_cap":   extra.get("market_cap",   ""),
            "ipo_url":      extra.get("ipo_url",      ""),
            "status":       nse_item.get("status",    "Active"),
            "published":    nse_item.get("open_date", ""),
        }

        if _validate_ipo_article(article, company):
            articles.append(article)
            print(f"[IPO FEED] ✅ Added: '{company}' "
                  f"(source={article['data_source']})")
        else:
            print(f"[IPO FEED] ⚠️  Validation warning — adding anyway: '{company}'")
            articles.append(article)

    print(f"\n[IPO FEED] Final: {len(articles)} confirmed IPO articles")
    return articles


# ══════════════════════════════════════════════════════════════
#  STANDALONE TEST
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("  fetch_nse_ipo() — Current IPOs with Full Details")
    print("=" * 60)

    articles = fetch_nse_ipo()

    print(f"\nTotal: {len(articles)}")
    print("=" * 60)

    for i, a in enumerate(articles, 1):
        print(f"\n[{i}] {a['Blog_Title']}")
        print(f"     company      : {a['company']}")
        print(f"     status       : {a['status']}")
        print(f"     data_source  : {a['data_source']}")
        print(f"     open_date    : {a.get('open_date',   'N/A')}")
        print(f"     close_date   : {a.get('close_date',  'N/A')}")
        print(f"     price_band   : {a.get('price_band',  'N/A')}")
        print(f"     lot_size     : {a.get('lot_size',     'N/A')}")
        print(f"     listing_date : {a.get('listing_date','N/A')}")
        print(f"     gmp          : {a.get('gmp',         'N/A')}")