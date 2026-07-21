# # sources/ndtv_profit.py

# import re
# import feedparser
# import requests
# from bs4 import BeautifulSoup


# NDTV_PROFIT_URL = "https://feeds.feedburner.com/ndtvprofit-latest"

# HEADERS = {
#     "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
#                   "AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
#     "Accept": "application/rss+xml, application/xml, */*",
# }

# SKIP_PATTERNS = [
#     "share price live",
#     "stock price live",
#     "price live update",
#     "live blog",
#     "live updates",
# ]


# def _clean_summary(raw: str) -> str:
#     if not raw:
#         return ""
#     soup = BeautifulSoup(raw, "html.parser")
#     for tag in soup.find_all(["img", "a"]):
#         tag.decompose()
#     text = soup.get_text(separator=" ", strip=True)
#     text = re.sub(r'\s+', ' ', text).strip()
#     return text


# def fetch_ndtv_profit(top_n: int = 6) -> list:
#     """
#     Fetches articles from NDTV Profit RSS feed.
#     URL: feeds.feedburner.com/ndtvprofit-latest
#     Content from <summary> field — clean text summaries.
#     """
#     print(f"[NDTV] Fetching NDTV Profit RSS...")

#     articles    = []
#     seen_titles = set()

#     try:
#         r    = requests.get(NDTV_PROFIT_URL, headers=HEADERS, timeout=10)
#         feed = feedparser.parse(r.text)
#         print(f"[NDTV] [{r.status_code}] {len(feed.entries)} entries")

#         for entry in feed.entries:
#             title     = entry.get("title",     "").strip()
#             link      = entry.get("link",      "").strip()
#             published = entry.get("published", "").strip()
#             summary   = entry.get("summary",   "").strip()

#             if not title:
#                 continue

#             title_lower = title.lower()
#             if any(pat in title_lower for pat in SKIP_PATTERNS):
#                 continue

#             if title_lower in seen_titles:
#                 continue
#             seen_titles.add(title_lower)

#             summary = _clean_summary(summary)
#             if not summary or len(summary) < 30:
#                 continue

#             blog_content = f"""{summary}

# Source    : NDTV Profit
# Published : {published}
# URL       : {link}""".strip()

#             articles.append({
#                 "Blog_Title":       title,
#                 "Blog_Links":       link,
#                 "Blog_PublishDate": published,
#                 "Blog_Content":     blog_content,
#                 "source_name":      "NDTV Profit",
#             })

#     except Exception as e:
#         print(f"[NDTV] Feed failed: {e}")

#     print(f"[NDTV] Total: {len(articles)}")
#     return articles


# if __name__ == "__main__":
#     print("=" * 60)
#     print("  NDTV Profit RSS Fetcher")
#     print("=" * 60)

#     results = fetch_ndtv_profit()

#     print(f"\nTotal: {len(results)}")
#     print("=" * 60)

#     for i, r in enumerate(results, 1):
#         print(f"\n[{i}] Title   : {r['Blog_Title']}")
#         print(f"    Link    : {r['Blog_Links'][:70]}")
#         print(f"    Date    : {r['Blog_PublishDate']}")
#         print(f"    Content : {r['Blog_Content'][:300]}")
#         print(f"    ---")




# sources/ndtv_profit.py
# sources/ndtv_profit.py

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import re
import time
import feedparser
import requests
from bs4 import BeautifulSoup

try:
    from curl_cffi import requests as cf_requests
    CURL_CFFI_AVAILABLE = True
except ImportError:
    CURL_CFFI_AVAILABLE = False

from utils.mcp_tools import fetch_and_clean
from sources.common import assess_quality


# ─────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────

NDTV_FEEDS = [
    "https://feeds.feedburner.com/ndtvprofit-latest",
    
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/rss+xml, application/xml, */*",
}

SKIP_PATTERNS = [
    "share price live",
    "stock price live",
    "price live update",
    "live blog",
    "live updates",
    "live:",
    "in photos",
    "in pictures",
    "watch:",
]


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────

def _clean_summary(raw: str) -> str:
    """Strip HTML from RSS summary — used as fallback_text."""
    if not raw:
        return ""
    soup = BeautifulSoup(raw, "html.parser")
    for tag in soup.find_all(["img", "a"]):
        tag.decompose()
    text = soup.get_text(separator=" ", strip=True)
    return re.sub(r'\s+', ' ', text).strip()


def _scrape_ndtv(url: str) -> str:
    """
    curl_cffi works well on NDTV Profit (confirmed in pipeline logs).
    Used as the primary scraper before falling back to trafilatura chain.
    """
    if not CURL_CFFI_AVAILABLE:
        return ""
    try:
        resp = cf_requests.get(url, impersonate="chrome124", timeout=12)
        if resp.status_code != 200:
            return ""
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav",
                         "header", "footer", "aside"]):
            tag.decompose()
        body = (
            soup.find("div", class_=re.compile(
                r"article[_-]?body|story[_-]?content"
                r"|content[_-]?body|main[_-]?content",
                re.I
            ))
            or soup.find("article")
            or soup.find("main")
        )
        paragraphs = (body or soup).find_all("p")
        return " ".join(
            p.get_text(strip=True) for p in paragraphs
            if len(p.get_text(strip=True)) > 40
        ).strip()
    except Exception:
        return ""


NDTV_NEWSLETTER_RE = re.compile(
    r"Essential\s*Business\s*Intelligence.*?On NDTV Profit\.+",
    re.IGNORECASE | re.DOTALL
)

def _clean_ndtv_content(text: str) -> str:
    """Strip NDTV-specific newsletter promo and ALSO READ lines."""
    if not text:
        return text
    text = NDTV_NEWSLETTER_RE.sub("", text).strip()
    lines = [l for l in text.splitlines()
             if not re.match(r"^ALSO READ:", l.strip(), re.IGNORECASE)]
    return "\n".join(lines).strip()




def scrape_article(url: str, rss_summary: str = "",
                   title: str = "") -> tuple:
    """
    Scrape full article content.
    Tries curl_cffi first (works well on NDTV), then falls back
    to the trafilatura → newspaper → requests chain via fetch_and_clean.

    Returns: (content, method)
    """
    MIN_WORDS = 150

    # ── Try curl_cffi first (NDTV-specific) ──────────────────
    raw = _scrape_ndtv(url)
    if raw:
        raw = _clean_ndtv_content(raw)
    if raw and len(raw.split()) >= MIN_WORDS:
        return raw, "curl_cffi"

    # ── Fall back to generic trafilatura chain ────────────────
    result = fetch_and_clean(
        url=url,
        title=title,
        fallback_text=rss_summary
    )
    return result["content"], result["method"]


# ─────────────────────────────────────────────────────────────
# MAIN FETCHER
# ─────────────────────────────────────────────────────────────

def fetch_ndtv_profit(top_n: int = 20, scrape: bool = True,
                      delay: float = 1.5) -> list:
    """
    Fetches articles from NDTV Profit RSS feed with full
    article scraping.

    Scraper cascade:
      1. curl_cffi    (works well on NDTV Profit)
      2. trafilatura
      3. newspaper3k
      4. requests + BeautifulSoup
      5. RSS summary  (fallback)

    Args:
        top_n:  max articles to return
        scrape: attempt full article scraping (True recommended)
        delay:  seconds between scrape requests
    """
    print(f"[NDTV] Fetching NDTV Profit RSS...")

    articles    = []
    seen_titles = set()
    skipped     = 0

    for feed_url in NDTV_FEEDS:
        if len(articles) >= top_n:
            break

        try:
            r    = requests.get(feed_url, headers=HEADERS, timeout=10)
            feed = feedparser.parse(r.text)
            print(f"[NDTV] [{r.status_code}] {len(feed.entries)} entries")

            for entry in feed.entries:
                if len(articles) >= top_n:
                    break

                title     = entry.get("title",     "").strip()
                link      = entry.get("link",      "").strip()
                published = entry.get("published", "").strip()
                raw_sum   = entry.get("summary",   "").strip()

                if not title:
                    continue

                title_lower = title.lower()
                if any(pat in title_lower for pat in SKIP_PATTERNS):
                    skipped += 1
                    continue

                if title_lower in seen_titles:
                    skipped += 1
                    continue
                seen_titles.add(title_lower)

                # Clean RSS summary — always available as fallback
                rss_summary = _clean_summary(raw_sum)
                if not rss_summary or len(rss_summary) < 30:
                    skipped += 1
                    continue

                # ── Scrape full article ───────────────────────
                # Strip #publisher=newsstand and other tracking fragments
                clean_link = link.split("#")[0].strip()

                if scrape and clean_link:
                    content, method = scrape_article(
                        url=clean_link,
                        rss_summary=rss_summary,
                        title=title
                    )
                    time.sleep(delay)
                else:
                    content = rss_summary
                    method  = "rss_only"

                quality = assess_quality(content)
                print(f"   [NDTV] {method} ✓ ({quality['word_count']} words)")

                articles.append({
                    "Blog_Title":       title,
                    "Blog_Links":       link,
                    "Blog_PublishDate": published,
                    "Blog_Content":     content,
                    "source_name":      "NDTV Profit",
                    "source":           "ndtv_profit",
                    "_source_type":     "news",
                    "_content_words":   quality["word_count"],
                    "_content_quality": quality["quality"],
                    "_scrape_method":   method,
                })

        except Exception as e:
            print(f"[NDTV] Feed failed: {e}")

    print(f"[NDTV] Skipped: {skipped} | Valid: {len(articles)}")
    return articles


# ─────────────────────────────────────────────────────────────
# STANDALONE TEST
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  NDTV Profit RSS Fetcher + Scraper")
    print("=" * 60)

    results = fetch_ndtv_profit(top_n=6, scrape=True, delay=1.5)

    print(f"\nTotal: {len(results)}")
    print("=" * 60)

    for i, r in enumerate(results, 1):
        print(f"\n[{i}] Title   : {r['Blog_Title']}")
        print(f"    Link    : {r['Blog_Links']}")
        print(f"    Date    : {r['Blog_PublishDate']}")
        print(f"    Quality : {r['_content_quality']} "
              f"({r['_content_words']} words) via {r['_scrape_method']}")
        print(f"    Content : {r['Blog_Content']}...")
        print(f"    ---")