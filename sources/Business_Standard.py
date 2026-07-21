import re
import feedparser
import requests

from sources.common import assess_quality

try:
    from curl_cffi import requests as cf_requests
    CURL_CFFI_AVAILABLE = True
    print("[BS] curl_cffi available ✅")
except ImportError:
    CURL_CFFI_AVAILABLE = False
    print("[BS] curl_cffi not available — using requests fallback")


# ══════════════════════════════════════════════════════════════
#  CONFIG
# ══════════════════════════════════════════════════════════════

BUSINESS_STANDARD_FEEDS = [
    "https://www.business-standard.com/rss/markets-106.rss",
    "https://www.business-standard.com/rss/finance-103.rss",
    "https://www.business-standard.com/rss/economy-policy-102.rss",
    "https://www.business-standard.com/rss/latest.rss",
]

HEADERS = {
    "User-Agent":      (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection":      "keep-alive",
    "Referer":         "https://www.business-standard.com/",
    "Cache-Control":   "no-cache",
}

SKIP_PATTERNS = [
    "leads gainers",
    "leads losers",
    "most active",
    "52-week high",
    "52-week low",
    "share price today",
    "stock price today",
    "live updates",
    "live blog",
    "market at close",
    "market at open",
    "top gainers",
    "top losers",
]


# ══════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════

def clean_html(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r'<[^>]+>', ' ', text)
    text = text.replace('&amp;',  '&')
    text = text.replace('&lt;',   '<')
    text = text.replace('&gt;',   '>')
    text = text.replace('&nbsp;', ' ')
    text = text.replace('&#39;',  "'")
    text = text.replace('&quot;', '"')
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def fetch_feed_text(feed_url: str) -> str:
    # ── Method 1: curl_cffi ───────────────────────────────────
    if CURL_CFFI_AVAILABLE:
        try:
            resp = cf_requests.get(
                feed_url,
                impersonate="chrome124",
                timeout=15
            )
            if resp.status_code == 200:
                print(f"[BS] curl_cffi ✅ ({resp.status_code})")
                return resp.text
            else:
                print(f"[BS] curl_cffi ❌ status {resp.status_code}")
        except Exception as e:
            print(f"[BS] curl_cffi error: {e}")

    # ── Method 2: requests ────────────────────────────────────
    try:
        resp = requests.get(feed_url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            print(f"[BS] requests ✅ ({resp.status_code})")
            return resp.text
        else:
            print(f"[BS] requests ❌ status {resp.status_code}")
    except Exception as e:
        print(f"[BS] requests error: {e}")

    return ""




# ══════════════════════════════════════════════════════════════
#  SINGLE FEED FETCHER — fetches ALL entries, no top_n limit
# ══════════════════════════════════════════════════════════════

def _fetch_single_feed(feed_url: str) -> list:
    """
    Fetches ALL available entries from one RSS feed.
    No top_n limit here — merging and limiting happens later.
    Returns raw list of articles from this feed only.
    """
    articles = []
    skipped  = 0

    feed_name = feed_url.split('/')[-1]
    print(f"\n[BS] ── Fetching: {feed_name}")

    raw_text = fetch_feed_text(feed_url)

    if raw_text:
        feed = feedparser.parse(raw_text)
    else:
        feed = feedparser.parse(
            feed_url,
            agent=HEADERS["User-Agent"]
        )

    print(f"[BS] {len(feed.entries)} raw entries in {feed_name}")

    if not feed.entries:
        print(f"[BS] No entries found in {feed_name}")
        return articles

    for entry in feed.entries:

        # ── Title ─────────────────────────────────────────────
        title = clean_html(entry.get("title", "")).strip()
        if not title:
            skipped += 1
            continue

        # ── Skip low-value entries ─────────────────────────────
        title_lower = title.lower()
        if any(pat in title_lower for pat in SKIP_PATTERNS):
            skipped += 1
            continue

        # ── Blog_Links ────────────────────────────────────────
        link = (
            entry.get("link", "") or
            entry.get("guid", "")
        ).strip()

        # ── Published date ─────────────────────────────────────
        published = entry.get("published", "").strip()

        # ── Blog_Content ──────────────────────────────────────
        raw_summary = (
            entry.get("summary",     "") or
            entry.get("description", "")
        )
        summary = clean_html(raw_summary).strip()

        if not summary:
            skipped += 1
            continue

        quality = assess_quality(summary)

        articles.append({
            "Blog_Title":       title,
            "Blog_Links":       link,
            "Blog_PublishDate": published,
            "Blog_Content":     summary,
            "source":           "business_standard",
            "source_name":      "Business Standard",
            "_source_type":     "news",
            "_content_words":   quality["word_count"],
            "_content_quality": quality["quality"],
        })

    print(f"[BS] {feed_name} → {len(articles)} valid | {skipped} skipped")
    return articles


# ══════════════════════════════════════════════════════════════
#  MERGE + DEDUP
# ══════════════════════════════════════════════════════════════

def _merge_and_dedup(all_articles: list) -> list:
    """
    Merges articles from all feeds and removes duplicates.
    Dedup is based on normalised title.
    First occurrence wins — preserves article order.
    """
    seen_titles = set()
    unique      = []
    removed     = 0

    for article in all_articles:
        title_norm = re.sub(
            r'\s+', ' ',
            article.get("Blog_Title", "").lower().strip()
        )
        if title_norm in seen_titles:
            removed += 1
            continue
        seen_titles.add(title_norm)
        unique.append(article)

    print(f"[BS] Dedup → {len(all_articles)} total "
          f"→ {len(unique)} unique ({removed} duplicates removed)")
    return unique


# ══════════════════════════════════════════════════════════════
#  MAIN FETCHER
# ══════════════════════════════════════════════════════════════

def fetch_business_standard(top_n: int = 10) -> list:
    """
    Fetches ALL entries from all 4 Business Standard RSS feeds,
    merges them, deduplicates by title, then returns top_n.

    Flow:
      Feed 1 → all articles
      Feed 2 → all articles
      Feed 3 → all articles
      Feed 4 → all articles
           ↓
        MERGE (combine all)
           ↓
        DEDUP (remove duplicate titles)
           ↓
        RETURN top_n
    """
    print(f"[BS] Fetching Business Standard "
          f"({len(BUSINESS_STANDARD_FEEDS)} feeds)...")
    print("=" * 50)

    all_articles = []

    # ── Step 1: Fetch all feeds independently ─────────────────
    for feed_url in BUSINESS_STANDARD_FEEDS:
        feed_articles = _fetch_single_feed(feed_url)
        all_articles += feed_articles

    print(f"\n[BS] ── Raw total from all feeds: {len(all_articles)}")

    # ── Step 2: Merge and deduplicate ─────────────────────────
    unique_articles = _merge_and_dedup(all_articles)

    # ── Step 3: Apply top_n after merge ───────────────────────
    final = unique_articles[:top_n]

    print(f"[BS] ── Final after top_n={top_n}: {len(final)} articles")
    return final


# ══════════════════════════════════════════════════════════════
#  STANDALONE TEST
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("  Business Standard RSS Fetcher")
    print("=" * 60)

    results = fetch_business_standard(top_n=40)

    print(f"\nTotal returned: {len(results)}")
    print("=" * 60)

    for i, r in enumerate(results, 1):
        print(f"\n[{i}] Title   : {r['Blog_Title']}")
        print(f"    Link    : {r['Blog_Links']}")
        print(f"    Date    : {r['Blog_PublishDate']}")
        print(f"    Quality : {r['_content_quality']} "
              f"({r['_content_words']} words)")
        print(f"    Content : {r['Blog_Content']}...")
        print(f"    ---")