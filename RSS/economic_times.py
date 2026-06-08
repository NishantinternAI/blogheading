# RSS/economic_times.py

import feedparser
import requests


ET_MARKETS_URL = "https://economictimes.indiatimes.com/markets/stocks/rssfeeds/2146842.cms"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/rss+xml, application/xml, */*",
}

# Skip live blog / price tracker entries — no real content
SKIP_PATTERNS = [
    "share price live updates",
    "stock price live updates",
    "price live updates",
    "live updates:",
    "market movement",
    "trading insights",
    "performance snapshot",
    "price movement today",
    "daily performance update",
    "market performance",
    "financial highlights",
    "current price update",
    "price and sma update",
    "market activity",
    "market update",
    "trading activity",
    "performance overview",
]


def fetch_economic_times(top_n: int = 6) -> list:
    """
    Fetches articles from Economic Times RSS feed.

    XML structure:
      <item>
        <title>    → Blog_Title
        <link>     → Blog_Links
        <pubDate>  → Blog_PublishDate
        <description> → Blog_Content (2-3 sentence summary)
      </item>

    Content comes directly from <description> tag.
    No scraping needed — ET provides summaries in RSS.
    """
    print(f"[ET] Fetching Economic Times Markets...")

    articles    = []
    seen_titles = set()
    skipped     = 0

    try:
        r    = requests.get(ET_MARKETS_URL, headers=HEADERS, timeout=10)
        feed = feedparser.parse(r.text)
        print(f"[ET] [{r.status_code}] {len(feed.entries)} raw entries")

        for entry in feed.entries:

            # ── Extract fields directly from XML ──────────────
            title     = entry.get("title",     "").strip()
            link      = entry.get("link",      "").strip()
            published = entry.get("published", "").strip()
            summary   = entry.get("summary",   "").strip()  # ← from <description>

            if not title:
                continue

            # ── Skip live price update entries ─────────────────
            title_lower = title.lower()
            if any(pat in title_lower for pat in SKIP_PATTERNS):
                skipped += 1
                continue

            # ── Skip entries with no description ──────────────
            if not summary or len(summary) < 50:
                skipped += 1
                continue

            # ── Dedup ──────────────────────────────────────────
            if title_lower in seen_titles:
                continue
            seen_titles.add(title_lower)

            # ── Build Blog_Content from XML fields ─────────────
            blog_content = f"""{summary}
            Source    : Economic Times Markets
            Published : {published}
            URL       : {link}""".strip()

            articles.append({
                "Blog_Title":       title,
                "Blog_Links":       link,
                "Blog_PublishDate": published,
                "Blog_Content":     blog_content,
                "source_name":      "Economic Times",
            })

    except Exception as e:
        print(f"[ET] Feed failed: {e}")

    print(f"[ET] Skipped: {skipped} | Valid: {len(articles)}")
    return articles


if __name__ == "__main__":
    print("=" * 60)
    print("  Economic Times Markets RSS Fetcher")
    print("=" * 60)

    results = fetch_economic_times()

    print(f"\nTotal: {len(results)}")
    print("=" * 60)

    for i, r in enumerate(results, 1):
        print(f"\n[{i}] Title   : {r['Blog_Title']}")
        print(f"    Link    : {r['Blog_Links'][:70]}")
        print(f"    Date    : {r['Blog_PublishDate']}")
        print(f"    Content : {r['Blog_Content']}")  # ← inline, not newline
        print(f"    ---")
        