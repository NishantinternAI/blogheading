"""
sources/ipo.py — NSE IPO feed + multi-source detail enrichment.

Fetches the list of currently open IPOs from NSE (API first, Selenium
fallback for SME issues the API misses), then enriches each one with
price/date/financial detail by merging data scraped from Chittorgarh,
InvestorGain, and Moneycontrol, plus an AI web-search fallback
(fetch_ipo_live_data_via_ai, in add_cached.py) for GMP and live
subscription status -- fields that only exist on JS-rendered pages plain
requests/BeautifulSoup scraping can't reach.

Entry point: fetch_nse_ipo() -- called from mergeall_engine.py's live
run_pipeline() as the "nse_ipo" source. Returns a list of article dicts
(Blog_Title/Blog_Content/company/source=...) ready for generate_ipo_blog().

TEST_MODE (see bottom of file, __main__ block) lets this module be run
standalone via `python sources/ipo.py` to inspect scraped output without
running the full pipeline.
"""



import re
import time
import urllib.request
import feedparser
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime

from add_cached import fetch_ipo_live_data_via_ai


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

# Cache TTL / cache dicts moved into IPODetailScraper (below) as instance
# state (self.CACHE_TTL_HOURS / self._ipo_df_cache / self._ipo_data_cache).


# ══════════════════════════════════════════════════════════════
#  NSE SESSION
# ══════════════════════════════════════════════════════════════

def _build_nse_session() -> requests.Session:
    """
    Builds a `requests.Session` primed with the cookies NSE's API expects.

    NSE's API rejects cold requests, so this visits the homepage and then
    the IPO listing page first (in that order, with real browser headers)
    to pick up the session cookies NSE sets before returning JSON. Both
    warm-up requests are best-effort: failures are logged and swallowed so
    the caller still gets a session back (which may then fail the actual
    API call — that's handled by the caller, not here).

    Returns:
        A `requests.Session` with `NSE_HEADERS` applied and (if the warm-up
        succeeded) NSE's cookies set.
    """
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
    """
    Normalizes a company name into a stable cache/lookup key.

    Lowercases the name and strips common IPO-listing suffixes/words
    ("limited", "ltd", "ipo", "india") so that e.g. "Foo India Limited",
    "Foo Ltd", and "Foo IPO" all collapse to the same key. Used both as
    the `_ipo_data_cache` key and (via substring matching) to match a
    company against Chittorgarh's IPO name list in `_find_ipo_url`.

    Args:
        company_name: Raw company name as reported by NSE.

    Returns:
        The normalized, lowercased key.
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
    """
    Scrapes Chittorgarh's mainboard + SME IPO list pages (`LIST_URLS`) into
    a DataFrame mapping IPO name → detail-page URL, used by
    `_find_ipo_url` to locate a given company's Chittorgarh page.

    Cached for the lifetime of the process in the module-level
    `_ipo_df_cache` global — there is no TTL, so a company that lists
    after the cache was first built will not be found until the process
    restarts (see CLAUDE.md gotchas). Per-URL scrape failures are caught
    and logged; the map is simply built from whatever URLs succeeded.

    Returns:
        DataFrame with columns `ipo_name`, `url`, `source`,
        `ipo_name_lower`. Empty (but correctly-columned) if every list
        page failed to scrape or yielded no matching links.
    """
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
    """
    Looks up `company_name`'s Chittorgarh IPO detail-page URL in the map
    built by `_build_ipo_map`.

    Two-pass fuzzy match: first tries a direct substring match (normalized
    name is a substring of the map's lowercased IPO name, or vice versa);
    if that fails, falls back to a word-overlap match requiring at least 2
    shared words longer than 3 characters. This tolerates naming
    differences between NSE ("Foo Industries Limited") and Chittorgarh
    ("Foo Industries IPO") but can occasionally mismatch on generic word
    overlap for very short or generic company names.

    Args:
        company_name: Raw company name (as reported by NSE).
        df: The IPO map DataFrame from `_build_ipo_map`.

    Returns:
        The matched detail-page URL, or "" if `df` is empty or no row
        matched either pass.
    """
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
    Splits a scraped "IPO Date" range string into separate open/close date
    strings, and backfills whichever side of the range is missing its
    month/year (source sites often print only "12 to 16 Jan, 2025", i.e.
    the open side has just a day number).

    Args:
        value: Raw date-range text (e.g. "Jan 12, 2025 to Jan 16, 2025" or
            "12 to 16 Jan, 2025"). If it has no " to " separator at all,
            the whole string is treated as the open date with no close
            date.

    Returns:
        `(open_date, close_date)` tuple of strings. `close_date` is ""
        when `value` had no " to " separator.
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
#  GMP FORMAT VALIDATOR
# ══════════════════════════════════════════════════════════════

def _looks_like_valid_gmp(text: str) -> bool:
    """
    GMP must read as an actual rupee amount (optionally with a % in
    parens), not page furniture that happens to sit near the words
    "GMP" / "grey market" (nav labels, ad snippets, etc).
    """
    if not text or len(text) > 30:
        return False
    return bool(re.match(r'^₹\s*-?[\d,]+(\.\d+)?\s*(\([^)]*%\))?$', text.strip()))


class IPODetailScraper:
    """
    Multi-source IPO detail enrichment.

    Merges data scraped from three sites (Chittorgarh, InvestorGain,
    Moneycontrol) that each cover a different subset of fields, plus an AI
    web-search fallback (`fetch_ipo_live_data_via_ai`) for GMP/live
    subscription status that only exists on JS-rendered pages plain
    scraping can't reach. Results are cached per-company for
    `CACHE_TTL_HOURS`.

    Instantiated once at module scope (`_scraper`, below) so the cache
    persists across pipeline runs within the same process — this class
    holds no per-request state, only the shared caches, so a single
    long-lived instance is intentional, not incidental.
    """

    CACHE_TTL_HOURS = 6

    def __init__(self):
        self._ipo_df_cache   = None
        self._ipo_data_cache = {}

    # ── SCRAPER 1 — CHITTORGARH ──────────────────────────────────

    def _build_ipo_map(self) -> pd.DataFrame:
        """
        Scrapes Chittorgarh's mainboard + SME IPO list pages (`LIST_URLS`)
        into a DataFrame mapping IPO name → detail-page URL, used by
        `_find_ipo_url` to locate a given company's Chittorgarh page.

        Cached for the lifetime of this instance in `self._ipo_df_cache` —
        there is no TTL, so a company that lists after the cache was first
        built will not be found until the process restarts (see
        CLAUDE.md gotchas). Per-URL scrape failures are caught and
        logged; the map is simply built from whatever URLs succeeded.

        Returns:
            DataFrame with columns `ipo_name`, `url`, `source`,
            `ipo_name_lower`. Empty (but correctly-columned) if every list
            page failed to scrape or yielded no matching links.
        """
        if self._ipo_df_cache is not None:
            return self._ipo_df_cache

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

        self._ipo_df_cache = df
        return df

    def _find_ipo_url(self, company_name: str, df: pd.DataFrame) -> str:
        """
        Looks up `company_name`'s Chittorgarh IPO detail-page URL in the
        map built by `_build_ipo_map`.

        Two-pass fuzzy match: first tries a direct substring match
        (normalized name is a substring of the map's lowercased IPO name,
        or vice versa); if that fails, falls back to a word-overlap match
        requiring at least 2 shared words longer than 3 characters. This
        tolerates naming differences between NSE ("Foo Industries
        Limited") and Chittorgarh ("Foo Industries IPO") but can
        occasionally mismatch on generic word overlap for very short or
        generic company names.

        Args:
            company_name: Raw company name (as reported by NSE).
            df: The IPO map DataFrame from `_build_ipo_map`.

        Returns:
            The matched detail-page URL, or "" if `df` is empty or no row
            matched either pass.
        """
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

    def _scrape_chittorgarh(self, company_name: str) -> dict:
        """
        Scrapes a single company's Chittorgarh IPO detail page for the bulk of
        the structured IPO fields: dates, price band, lot size, issue size,
        quotas, registrar/lead manager, GMP, a business-description snippet,
        and a parsed financials summary (revenue/PAT/net worth/borrowings with
        YoY growth) built from the page's "custom-ipo-table" RHP financials
        table. This is the richest of the three scrapers in practice — GMP and
        financials in `get_details` have historically only ever come
        from this source.

        Looks up the detail-page URL via `_build_ipo_map`/`_find_ipo_url`
        first; if the company isn't in the map, returns {} immediately without
        making a request.

        Args:
            company_name: Raw company name (as reported by NSE).

        Returns:
            Dict of whatever fields were found on the page (subset of:
            ipo_url, ipo_date, open_date, close_date, listing_date,
            price_band, lot_size, issue_size, face_value, exchange,
            issue_type, sale_type, fresh_issue, ofs, min_investment, registrar,
            lead_manager, qib_quota, nii_quota, retail_quota,
            pre_issue_shares, post_issue_shares, gmp, business, financials,
            market_cap). Returns {} if the company has no mapped URL.
        """
        df      = self._build_ipo_map()
        ipo_url = self._find_ipo_url(company_name, df)

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
                # Only the top-level "X Shares Offered" rows carry the real quota —
                # sub-rows like "− QIB (Ex. Anchor)..." / "bNII > ₹10L" / "sNII < ₹10L"
                # and "Retail (Min)"/"Retail (Max)" (lot-count rows, not quotas) also
                # match a loose "qib"/"nii"/"retail" substring check and were
                # clobbering the real value with whichever matched last.
                if "shares offered" in key and not key.startswith(("−", "-")):
                    if key.startswith("qib"):    data["qib_quota"]    = value
                    elif key.startswith("nii"):  data["nii_quota"]    = value
                    elif key.startswith("retail"): data["retail_quota"] = value
                if "share holding pre"  in key: data["pre_issue_shares"] = value
                if "share holding post" in key: data["post_issue_shares"]= value
    
        for tag in soup.find_all(["td","span"]):
            text = tag.get_text(strip=True)
            if (len(text) < 30 and "₹" in text and
                    ("grey market" in text.lower() or "gmp" in text.lower()) and
                    _looks_like_valid_gmp(text)):
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
            classes = " ".join(div.get("class", []))
            if "custom-ipo-table" not in classes:
                continue
            fin_table = div.find("table")
            if not fin_table:
                continue
            row_data = {}
            for row in fin_table.find_all("tr"):
                cells = [c.get_text(strip=True) for c in row.find_all(["td", "th"])]
                if len(cells) < 2:
                    continue
                row_data[cells[0]] = cells[1:]
            if "Period Ended" not in row_data or not any(
                k in row_data for k in ("Total Income", "Profit After Tax", "Assets")
            ):
                continue
    
            periods   = row_data.get("Period Ended", [])
            income    = row_data.get("Total Income", [])
            pat       = row_data.get("Profit After Tax", [])
            networth  = row_data.get("NET Worth", [])
            borrowing = row_data.get("Total Borrowing", [])
    
            def _growth(cur, prev):
                try:
                    cur_f  = float(cur.replace(",", ""))
                    prev_f = float(prev.replace(",", ""))
                    if prev_f == 0:
                        return None
                    return f"{((cur_f - prev_f) / prev_f) * 100:+.1f}%"
                except (ValueError, IndexError):
                    return None
    
            lines = ["Financials (₹ Crore, from RHP):"]
            for i, period in enumerate(periods[:2]):
                parts = [f"Period: {period}"]
                if i < len(income):
                    parts.append(f"Revenue: ₹{income[i]} Cr")
                if i < len(pat):
                    parts.append(f"PAT: ₹{pat[i]} Cr")
                if i < len(networth):
                    parts.append(f"Net Worth: ₹{networth[i]} Cr")
                if i < len(borrowing):
                    parts.append(f"Borrowings: ₹{borrowing[i]} Cr")
                lines.append("  " + ", ".join(parts))
            if len(income) >= 2:
                g = _growth(income[0], income[1])
                if g:
                    lines.append(f"  Revenue YoY growth: {g}")
            if len(pat) >= 2:
                g = _growth(pat[0], pat[1])
                if g:
                    lines.append(f"  PAT YoY growth: {g}")
    
            data["financials"] = "\n".join(lines)
            break
    
        match = re.search(r"Market Cap.*?₹([\d,.]+\s*Cr)", soup.get_text())
        if match:
            data["market_cap"] = "₹" + match.group(1)
    
        print(f"[IPO] Chittorgarh fields: {list(data.keys())}")
        return data


# ══════════════════════════════════════════════════════════════
#  SCRAPER 2 — INVESTORGAIN
# ══════════════════════════════════════════════════════════════

    def _scrape_investorgain(self, company_name: str) -> dict:
        """
        Searches InvestorGain's live-subscription and upcoming-IPO listing
        pages for `company_name`, then scrapes its detail page for date/price/
        lot/issue-size style fields.
    
        GOTCHA: confirmed by live testing this session, this scraper is
        effectively non-functional in practice. InvestorGain's real data
        table (subscription figures, GMP) is rendered client-side by
        JavaScript; plain `requests` + BeautifulSoup only ever sees the
        pre-render HTML shell, so the fields this function is nominally meant
        to contribute typically come back empty even when a matching IPO page
        is found. It is kept in `get_details`'s scraper waterfall mainly as
        a low-cost no-op fallback, not a reliable data source — GMP/live
        subscription data actually comes from the AI web-search fallback
        (`fetch_ipo_live_data_via_ai`), not from this scraper.
    
        Args:
            company_name: Raw company name (as reported by NSE).
    
        Returns:
            Dict of whatever fields were found (subset of: ipo_url, open_date,
            close_date, ipo_date, listing_date, price_band, lot_size,
            issue_size, face_value, exchange, issue_type, min_investment).
            Returns {} if no matching IPO page could be found on either
            search page.
        """
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

    def _scrape_moneycontrol(self, company_name: str) -> dict:
        """
        Searches Moneycontrol's IPO listing page for `company_name` and, if
        found, extracts price band / open-close dates / lot size / issue size
        / listing date from the detail page's raw text via regex (there's no
        structured table parsing here, unlike the Chittorgarh/InvestorGain
        scrapers). If no matching link is found, falls back to regexing a
        600-character text window around the company's first name mention on
        the listing page itself, which is much lower-fidelity.
    
        Args:
            company_name: Raw company name (as reported by NSE).
    
        Returns:
            Dict of whatever fields the regexes matched (subset of:
            price_band, open_date, close_date, lot_size, issue_size,
            listing_date). Returns {} if nothing matched.
        """
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

    def get_details(self, company_name: str) -> dict:
        """
        Returns the merged, cached IPO detail dict for `company_name` — the
        single entry point the rest of the module uses to get enriched IPO
        data (called from `fetch_nse_ipo` via the module-level `_scraper`
        instance).

        Behavior:
          1. Serves from `self._ipo_data_cache` (keyed by
             `_normalize_company_key`) if a fresh (< `CACHE_TTL_HOURS`)
             entry exists.
          2. Otherwise runs all three scrapers (Chittorgarh, InvestorGain,
             Moneycontrol) and merges their output field-by-field, first
             non-empty value for each key wins (does not stop at the first
             scraper that returns *anything* — each site tends to cover
             different fields, and stopping early throws away data the other
             scrapers had).
          3. If the merge produced at least a price band or open date, also
             calls the AI web-search fallback (`fetch_ipo_live_data_via_ai`)
             for GMP/subscription fields specifically when the scraped GMP
             doesn't pass `_looks_like_valid_gmp` or subscription data is
             missing — these fields live on JS-rendered pages the requests-
             based scrapers can't read. The AI result is only trusted after
             the same GMP format validation.
          4. Caches and returns the merged dict (with a `data_source` field
             describing which sources contributed, e.g.
             "Chittorgarh + AI-web-search").
          5. If all live scrapers fail entirely but a stale cache entry
             exists, returns that stale entry (tagged `data_source =
             "cache_stale"`) rather than nothing.

        Args:
            company_name: Raw company name (as reported by NSE).

        Returns:
            Merged detail dict (see `_scrape_chittorgarh`/
            `_scrape_investorgain`/`_scrape_moneycontrol` for possible keys),
            plus `data_source`. Returns {} only if there is no cache at all
            and every scraper (including the AI fallback) failed to produce
            even a price band or open date.
        """
        cache_key = _normalize_company_key(company_name)

        if cache_key in self._ipo_data_cache:
            cached_data, cached_at = self._ipo_data_cache[cache_key]
            age_hours = (datetime.now() - cached_at).total_seconds() / 3600
            if age_hours < self.CACHE_TTL_HOURS:
                src = cached_data.get("data_source", "cache")
                print(f"[IPO] Cache hit: '{cache_key}' "
                      f"(age={age_hours:.1f}h source={src})")
                return cached_data
            else:
                print(f"[IPO] Cache stale: '{cache_key}' — re-fetching")

        scrapers = [
            ("Chittorgarh",  self._scrape_chittorgarh),
            ("InvestorGain", self._scrape_investorgain),
            ("Moneycontrol", self._scrape_moneycontrol),
        ]

        # Merge across all three sources instead of stopping at the first one
        # that returns a price band — each site covers different fields (e.g.
        # GMP/financials only ever came from Chittorgarh in practice), so
        # stopping early silently threw away data the other scrapers had.
        merged       = {}
        sources_used = []

        for source_name, scraper_fn in scrapers:
            try:
                data = scraper_fn(company_name)
            except Exception as e:
                print(f"[IPO] {source_name} failed: {e} → skipping")
                continue

            if not data:
                print(f"[IPO] {source_name} → no usable data")
                continue

            sources_used.append(source_name)
            for key, value in data.items():
                if value and not merged.get(key):
                    merged[key] = value
            print(f"[IPO] {source_name} → contributed fields: {list(data.keys())}")

        if merged.get("price_band") or merged.get("open_date"):
            # GMP and live subscription status live on JS-rendered pages the
            # requests+BeautifulSoup scrapers above can't see (confirmed:
            # InvestorGain's tables never resolve via plain requests). Fall back
            # to the AI web_search tool for just these fields — cheaper than
            # calling it for everything, and every value it returns is strictly
            # format-validated before being trusted (see fetch_ipo_live_data_via_ai).
            if not _looks_like_valid_gmp(merged.get("gmp", "")) or not merged.get("retail_sub"):
                try:
                    ai_data = fetch_ipo_live_data_via_ai(company_name)
                except Exception as e:
                    print(f"[IPO] AI live-data fetch failed: {e} → skipping")
                    ai_data = {}

                if ai_data:
                    sources_used.append("AI-web-search")
                    if not _looks_like_valid_gmp(merged.get("gmp", "")) and ai_data.get("gmp"):
                        merged["gmp"] = ai_data["gmp"]
                    for field in ("retail_sub", "nii_sub", "qib_sub", "overall_sub"):
                        if ai_data.get(field) and not merged.get(field):
                            merged[field] = ai_data[field]

            merged["data_source"]           = " + ".join(sources_used)
            self._ipo_data_cache[cache_key] = (merged, datetime.now())
            print(f"[IPO] ✅ Merged from [{merged['data_source']}] → cached (key='{cache_key}')")
            return merged

        if cache_key in self._ipo_data_cache:
            stale_data, cached_at = self._ipo_data_cache[cache_key]
            age_hours = (datetime.now() - cached_at).total_seconds() / 3600
            print(f"[IPO] ⚠️  Using stale cache (age={age_hours:.1f}h)")
            stale_data["data_source"] = "cache_stale"
            return stale_data

        print(f"[IPO] ❌ All sources failed: {company_name}")
        return {}


# Single shared instance — its caches (`_ipo_df_cache`/`_ipo_data_cache`)
# persist across pipeline runs within the same process, matching the
# original module-level global-cache behavior.
_scraper = IPODetailScraper()


# ══════════════════════════════════════════════════════════════
#  VALIDATE
# ══════════════════════════════════════════════════════════════

def _validate_ipo_article(article: dict, company: str) -> bool:
    """
    Validates a fully-built article dict before it's added to the feed,
    and mutates it in place to tag data-completeness state for downstream
    review (does not just log — see `missing_critical_fields`/
    `needs_review` below).

    Checks (non-exhaustive):
      - open_date/close_date don't contain more than one month name
        (a sign the date range wasn't split correctly) → hard error.
      - open_date has a month and a year, price_band has a ₹ sign, and
        lot_size is numeric → soft warnings only, logged but not fatal.
      - Sets `article["missing_critical_fields"]` (list of "gmp"/
        "financials" if absent) and `article["needs_review"] = bool(...)`
        — missing GMP/financials is expected for freshly-filed IPOs so
        it's not an error, but needs to be visible so a human can tell
        "not published yet" apart from "the scraper failed."

    Args:
        article: The built article dict (mutated in place — gains
            `missing_critical_fields` and `needs_review` keys).
        company: Company name, used only for log messages.

    Returns:
        False if any hard error was found (malformed dates) — caller
        should skip/retry the article next cycle. True otherwise
        (including when there are warnings or `needs_review` is set).
    """
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

    # ── Completeness check — flags for review, does not block ──────────
    # GMP/financials genuinely aren't available yet for freshly-filed IPOs,
    # so missing them isn't an error, but it must be visible so a human can
    # tell "not published yet" apart from "the scraper failed."
    missing_critical = []
    if not article.get("gmp"):
        missing_critical.append("gmp")
    if not article.get("financials"):
        missing_critical.append("financials")
    article["missing_critical_fields"] = missing_critical
    article["needs_review"]            = bool(missing_critical)

    if errors:
        print(f"[IPO VALIDATE] ❌ {company} (source={src})")
        for e in errors:
            print(f"[IPO VALIDATE]    ERROR: {e}")
        return False

    if warnings or missing_critical:
        print(f"[IPO VALIDATE] ⚠️  {company} (source={src})")
        for w in warnings:
            print(f"[IPO VALIDATE]    WARNING: {w}")
        if missing_critical:
            print(f"[IPO VALIDATE]    NEEDS REVIEW — missing: {', '.join(missing_critical)}")
    else:
        print(f"[IPO VALIDATE] ✅ {company} (source={src})")

    return True


# ══════════════════════════════════════════════════════════════
#  BUILD BLOG TITLE + CONTENT
# ══════════════════════════════════════════════════════════════

def _build_blog_title(company: str, nse_data: dict, extra: dict) -> str:
    """
    Builds the blog post title for an IPO article, picking the most
    specific phrasing available based on what data was found.

    Prefers `extra` (scraped waterfall data) over `nse_data` (raw NSE
    fields) for price and open date, falling back gracefully through
    four title templates depending on whether price and/or open date are
    known, down to a generic title if neither is available.

    Args:
        company: Company name to include in the title.
        nse_data: Raw NSE company dict (has `issue_price`/`open_date`
            fallback values).
        extra: Merged scraper dict from `get_details` (preferred
            source for `price_band`/`open_date`).

    Returns:
        The generated title string.
    """
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
    """
    Builds the raw structured brief handed to the blog-generation LLM
    (not the final blog copy itself) — a plain-text field-by-field dump
    of every known IPO detail, followed by a fixed instruction block
    telling the model what to write and to not invent financial figures
    beyond what's given.

    Every field falls back to a human-readable placeholder ("To be
    announced" / "Not available yet" / "Not disclosed in available
    sources") when missing, so the LLM prompt never contains empty
    values. `extra` (scraped waterfall data) takes priority over
    `nse_data` (raw NSE fields) wherever both exist.

    Args:
        company: Company name.
        nse_data: Raw NSE company dict, used as fallback for
            status/open_date/close_date/issue_price/issue_size/
            issue_type.
        extra: Merged scraper dict from `get_details`, preferred
            source for nearly every field.

    Returns:
        The formatted plain-text brief string (stripped of leading/
        trailing whitespace).
    """
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
Subscription — Retail  : {extra.get('retail_sub',  'Not available yet')}
Subscription — NII     : {extra.get('nii_sub',     'Not available yet')}
Subscription — QIB     : {extra.get('qib_sub',     'Not available yet')}
Subscription — Overall : {extra.get('overall_sub', 'Not available yet')}
Registrar      : {extra.get('registrar',        'To be announced')}
Lead Manager   : {extra.get('lead_manager',     'To be announced')}
Market Cap     : {extra.get('market_cap',       'Not disclosed in available sources')}
Business       : {extra.get('business', company + ' is currently open for IPO subscription.')}

{extra.get('financials', 'Financials: Not disclosed in available sources for this IPO.')}

Write a complete IPO analysis blog covering all the details above.
For fields showing "To be announced" mention they will be revealed soon.
Use the Financials block above exactly as given — do not invent revenue,
profit, or growth figures beyond what is stated there.
Include: company background, IPO details, financial highlights (as a table,
using the exact figures above), GMP analysis, should investors apply
(pros and cons), how to apply via UPI/ASBA, and final recommendation.
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

        extra = _scraper.get_details(company)

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
            "financials":   extra.get("financials",   ""),
            "retail_sub":   extra.get("retail_sub",   ""),
            "nii_sub":      extra.get("nii_sub",      ""),
            "qib_sub":      extra.get("qib_sub",      ""),
            "overall_sub":  extra.get("overall_sub",  ""),
            "ipo_url":      extra.get("ipo_url",      ""),
            "status":       nse_item.get("status",    "Active"),
            "published":    nse_item.get("open_date", ""),
        }

        if _validate_ipo_article(article, company):
            articles.append(article)
            review_note = " [NEEDS REVIEW]" if article.get("needs_review") else ""
            print(f"[IPO FEED] ✅ Added: '{company}' "
                  f"(source={article['data_source']}){review_note}")
        else:
            print(f"[IPO FEED] ❌ Skipped '{company}' — malformed dates/data "
                  f"failed validation, will retry next cycle")

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
        print(f"\n[{i}] {a['Blog_Content']}")
        # print(f"     company      : {a['company']}")
        # print(f"     status       : {a['status']}")
        # print(f"     data_source  : {a['data_source']}")
        # print(f"     open_date    : {a.get('open_date',   'N/A')}")
        # print(f"     close_date   : {a.get('close_date',  'N/A')}")
        # print(f"     price_band   : {a.get('price_band',  'N/A')}")
        # print(f"     lot_size     : {a.get('lot_size',     'N/A')}")
        # print(f"     listing_date : {a.get('listing_date','N/A')}")
        # print(f"     gmp          : {a.get('gmp',         'N/A')}")