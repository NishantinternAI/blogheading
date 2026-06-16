# RSS/google_news_business.py

import re
import feedparser
from bs4 import BeautifulSoup

try:
    import trafilatura
    TRAFILATURA_AVAILABLE = True
    print("[GNB] trafilatura available ✅")
except ImportError:
    TRAFILATURA_AVAILABLE = False
    print("[GNB] trafilatura not available")


# ══════════════════════════════════════════════════════════════
#  CONFIG
# ══════════════════════════════════════════════════════════════

GOOGLE_NEWS_BUSINESS_URL = (
    "https://news.google.com/rss/topics/"
    "CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx6TVdZU0FtVnVHZ0pWVXlnQVAB"
    "?hl=en-IN&gl=IN&ceid=IN:en"
)


# ══════════════════════════════════════════════════════════════
#  PARSE DESCRIPTION
#  Description HTML structure:
#  <ol>
#    <li>
#      <a href="google_url">Headline text</a>
#      <font>Source Name</font>
#    </li>
#  </ol>
# ══════════════════════════════════════════════════════════════

def _parse_description(desc: str) -> list:
    """
    Parses Google News description HTML.
    Extracts (headline, source_name, google_url) for each item.

    Description format:
      <li>
        <a href="https://news.google.com/...">Headline</a>
        <font color="#6f6f6f">Source Name</font>
      </li>

    Returns list of dicts:
      [
        {
          "headline":    "SEBI bars Rajesh Exports CMD...",
          "source":      "Moneycontrol.com",
          "google_url":  "https://news.google.com/rss/articles/...",
        },
        ...
      ]
    """
    if not desc:
        return []

    soup  = BeautifulSoup(desc, "html.parser")
    items = []
    seen  = set()

    for li in soup.find_all("li"):
        a    = li.find("a", href=True)
        font = li.find("font")

        if not a:
            continue

        headline   = a.get_text(strip=True)
        google_url = a["href"]
        source     = font.get_text(strip=True) if font else ""

        # Skip navigation links
        if not headline or len(headline) < 10:
            continue
        if "see more" in headline.lower():
            continue
        if headline.lower() in seen:
            continue

        seen.add(headline.lower())
        items.append({
            "headline":   headline,
            "source":     source,
            "google_url": google_url,
        })

    return items


def _scrape_url(url: str, max_chars: int = 1200) -> str:
    """Scrapes content from a URL using trafilatura."""
    if not url or not TRAFILATURA_AVAILABLE:
        return ""

    # Skip Google URLs — they won't give real content
    if "google.com" in url:
        return ""

    try:
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            print(f"[GNB] Download failed: {url[:60]}")
            return ""

        content = trafilatura.extract(
            downloaded,
            include_comments = False,
            include_tables   = False,
            no_fallback      = False,
            favor_precision  = True,
        )

        if not content or len(content) < 150:
            print(f"[GNB] No content: {url[:60]}")
            return ""

        content = re.sub(r'\s+', ' ', content).strip()
        print(f"[GNB] ✅ {len(content)} chars scraped")
        return content[:max_chars]

    except Exception as e:
        print(f"[GNB] Scrape error: {e}")
        return ""


# ══════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════

def _clean_title(title: str) -> str:
    return re.sub(r'\s+-\s+[^-]+$', '', title).strip()


def _extract_source(item) -> tuple:
    name = ""
    url  = ""
    if hasattr(item, "source"):
        src = item.source
        if hasattr(src, "title"): name = src.title.strip()
        if hasattr(src, "href"):  url  = src.href.strip()
    if not name and item.get("source", {}).get("title"):
        name = item["source"]["title"].strip()
    if not url and item.get("source", {}).get("href"):
        url = item["source"]["href"].strip()
    return name, url


# ══════════════════════════════════════════════════════════════
#  MAIN FETCHER
# ══════════════════════════════════════════════════════════════

def fetch_google_news_business(top_n: int = 6) -> list:
    """
    Fetches India Business news from Google News RSS.

    Description links are all Google redirect URLs so we cannot
    directly scrape them. Instead we:

      1. Parse description → extract headlines + source names
      2. Build Blog_Content from those headlines (always works)
      3. Optionally try scraping source website for more content
    """
    print(f"[GNB] Fetching Google News Business India...")

    try:
        feed    = feedparser.parse(GOOGLE_NEWS_BUSINESS_URL)
        entries = feed.entries
        print(f"[GNB] Raw entries: {len(entries)}")
    except Exception as e:
        print(f"[GNB] Feed failed: {e}")
        return []

    articles    = []
    seen_titles = set()

    for entry in entries:
        if len(articles) >= top_n:
            break

        raw_title   = entry.get("title",       "").strip()
        link        = entry.get("link",        "").strip()
        published   = entry.get("published",   "").strip()
        desc        = entry.get("description", "").strip()
        source_name, source_url = _extract_source(entry)

        if not raw_title:
            continue

        title = _clean_title(raw_title)

        norm = re.sub(r'\s+', ' ', title.lower().strip())
        if norm in seen_titles:
            continue
        seen_titles.add(norm)

        # ── Parse description → related articles ──────────────
        related = _parse_description(desc)

        print(f"\n[GNB] Processing : '{title[:55]}'")
        print(f"[GNB] Source      : {source_name} ({source_url})")
        print(f"[GNB] Related     : {len(related)} articles in description")

        for r in related:
            print(f"[GNB]   • {r['headline'][:50]} — {r['source']}")

        # ── Build related headlines block ─────────────────────
        # Format: "Headline — Source"
        related_block = "\n".join(
            r['headline']
            for r in related
        )

        # ── Build Blog_Content ────────────────────────────────
        # Content = all related headlines with sources
        # This is what the AI uses to write the blog
        blog_content = f"""Source         : Google News Business India
Primary Source : {source_name}
Published      : {published}
Source Website : {source_url}

Related Coverage (from multiple sources):
{related_block}

Write a detailed blog post on the above topic.
Use all the related headlines as reference points.
Each headline represents how a different publication covered the story."""

        blog_content = blog_content.strip()

        print(f"[GNB] ✅ '{title[:50]}' | "
              f"{len(related)} related headlines")

        articles.append({
            "Blog_Title":       title,
            "Blog_Links":       source_url or link,
            "Blog_PublishDate": published,
            "Blog_Content":     blog_content,
            "source_name":      source_name,
        })

    print(f"\n[GNB] Fetched: {len(articles)} articles")
    return articles


# ══════════════════════════════════════════════════════════════
#  STANDALONE TEST
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("  Google News Business India — RSS Fetcher")
    print("=" * 60)

    results = fetch_google_news_business(top_n=10)

    print(f"\nTotal: {len(results)}")
    print("=" * 60)

    for i, r in enumerate(results, 1):
        print(f"\n[{i}] Title   : {r['Blog_Title']}")
        print(f"    Source  : {r['source_name']}")
        print(f"    Link    : {r['Blog_Links']}")
        print(f"    Date    : {r['Blog_PublishDate']}")
        print(f"    ---CONTENT---")
        print(r['Blog_Content'])      # ← print directly, no indent confusion
        print(f"---END---")

        