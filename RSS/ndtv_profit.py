# RSS/ndtv_profit.py

import re
import feedparser
import requests
from bs4 import BeautifulSoup


NDTV_PROFIT_URL = "https://feeds.feedburner.com/ndtvprofit-latest"

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
]


def _clean_summary(raw: str) -> str:
    if not raw:
        return ""
    soup = BeautifulSoup(raw, "html.parser")
    for tag in soup.find_all(["img", "a"]):
        tag.decompose()
    text = soup.get_text(separator=" ", strip=True)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def fetch_ndtv_profit(top_n: int = 6) -> list:
    """
    Fetches articles from NDTV Profit RSS feed.
    URL: feeds.feedburner.com/ndtvprofit-latest
    Content from <summary> field — clean text summaries.
    """
    print(f"[NDTV] Fetching NDTV Profit RSS...")

    articles    = []
    seen_titles = set()

    try:
        r    = requests.get(NDTV_PROFIT_URL, headers=HEADERS, timeout=10)
        feed = feedparser.parse(r.text)
        print(f"[NDTV] [{r.status_code}] {len(feed.entries)} entries")

        for entry in feed.entries:
            title     = entry.get("title",     "").strip()
            link      = entry.get("link",      "").strip()
            published = entry.get("published", "").strip()
            summary   = entry.get("summary",   "").strip()

            if not title:
                continue

            title_lower = title.lower()
            if any(pat in title_lower for pat in SKIP_PATTERNS):
                continue

            if title_lower in seen_titles:
                continue
            seen_titles.add(title_lower)

            summary = _clean_summary(summary)
            if not summary or len(summary) < 30:
                continue

            blog_content = f"""{summary}

Source    : NDTV Profit
Published : {published}
URL       : {link}""".strip()

            articles.append({
                "Blog_Title":       title,
                "Blog_Links":       link,
                "Blog_PublishDate": published,
                "Blog_Content":     blog_content,
                "source_name":      "NDTV Profit",
            })

    except Exception as e:
        print(f"[NDTV] Feed failed: {e}")

    print(f"[NDTV] Total: {len(articles)}")
    return articles


if __name__ == "__main__":
    print("=" * 60)
    print("  NDTV Profit RSS Fetcher")
    print("=" * 60)

    results = fetch_ndtv_profit()

    print(f"\nTotal: {len(results)}")
    print("=" * 60)

    for i, r in enumerate(results, 1):
        print(f"\n[{i}] Title   : {r['Blog_Title']}")
        print(f"    Link    : {r['Blog_Links'][:70]}")
        print(f"    Date    : {r['Blog_PublishDate']}")
        print(f"    Content : {r['Blog_Content'][:300]}")
        print(f"    ---")