# RSS/economic_times.py

import feedparser
import requests
import time
import re
from bs4 import BeautifulSoup

try:
    import trafilatura
    TRAFILATURA_AVAILABLE = True
except ImportError:
    TRAFILATURA_AVAILABLE = False

try:
    from newspaper import Article
    NEWSPAPER_AVAILABLE = True
except ImportError:
    NEWSPAPER_AVAILABLE = False


# ─────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────

ET_MARKETS_URL = "https://economictimes.indiatimes.com/markets/stocks/rssfeeds/2146842.cms"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
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

# ET-specific boilerplate to strip from scraped content
ET_STRIP_PATTERNS = [
    r"^also read:.*",
    r"^read more:.*",
    r"^follow us on.*",
    r"^subscribe to et prime.*",
    r"^et prime.*",
    r"^disclaimer:.*",
    r"^\(you can now subscribe.*",
    r"^get the latest.*",
    r"^click here to.*",
    r"^download the et app.*",
    r"^for all the latest.*",
    r"^stay updated with.*",
    r"^join et prime.*",
    r"^powered by.*automated.*",
    r"^this story is.*generated.*",
    r"^ai-generated.*",
     r"^listen to this article.*",          # ← new: audio prompt
    r"^\(what's moving sensex.*",           # ← new: ET footer paragraph
    r"^top trending stocks:.*",             # ← new: trending stocks line
    r"^sensex, nifty today:.*",             # ← new: live blog CTA
    r"^\(with inputs from.*",              # ← new: agency credit line
    r"^data:.*",                            # ← new: "Data: Ritesh Presswala"
    r"^[\(\[]?disclaimer:.*",  # matches both "Disclaimer:" and "(Disclaimer:" # already have r"^disclaimer:.*" but needs the ( variant
    r"^\(what's moving.*", # already catching this
]

# ET footer signal for tail stripping
# Update ET_FOOTER_SIGNALS to catch the ET footer block
ET_FOOTER_SIGNALS = re.compile(
    r"^(also read|read more|follow us|subscribe to et|et prime"
    r"|disclaimer|download the et app|get the latest|click here"
    r"|for all the latest|stay updated|join et prime"
    r"|\(what's moving sensex|top trending stocks"       # ← new
    r"|sensex, nifty today|\(with inputs from|data:)",   # ← new
    re.IGNORECASE
)

# ─────────────────────────────────────────────────────────────
# CONTENT CLEANER
# ─────────────────────────────────────────────────────────────
def dedup_repeated_paragraphs(text: str) -> str:
    """
    Removes consecutive duplicate paragraphs that ET
    sometimes appends twice at the end of articles.
    """
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    seen = []
    deduped = []
    for p in paragraphs:
        # Use first 60 chars as fingerprint to catch near-duplicates
        fingerprint = p[:60].lower()
        if fingerprint not in seen:
            seen.append(fingerprint)
            deduped.append(p)
    return "\n\n".join(deduped)




def strip_et_tail(text: str) -> str:
    """Remove trailing footer/promo lines from ET articles."""
    lines = text.split("\n")
    last_real = len(lines) - 1
    for i in range(len(lines) - 1, -1, -1):
        s = lines[i].strip()
        if not s:
            continue
        if ET_FOOTER_SIGNALS.match(s):
            last_real = i - 1
        else:
            break
    return "\n".join(lines[:last_real + 1]).strip()


def clean_et_content(text: str, title: str = "") -> str:
    """
    Removes ET-specific boilerplate, promo lines, and
    article headline duplication from scraped content.
    """
    if not text:
        return ""

    lines = text.split("\n")
    cleaned_lines = []

    for line in lines:
        s = line.strip()
        if not s:
            continue

        is_boilerplate = any(
            re.match(p, s, re.IGNORECASE) for p in ET_STRIP_PATTERNS
        )
        # Short promotional lines starting with common ET patterns
        is_promo = (
            len(s) < 80
            and re.match(r"^(read|follow|subscribe|download|click|join|get|stay)", s, re.IGNORECASE)
        )

        if not is_boilerplate and not is_promo:
            cleaned_lines.append(s)

    cleaned = "\n".join(cleaned_lines)

    # Strip article headline if it duplicates the RSS title
    lines = cleaned.split("\n")
    if lines and title:
        first = lines[0].strip()
        if (
            len(first) < 150
            and not first.endswith((".", "?", "!"))
        ):
            title_words = set(re.sub(r"[^\w\s]", "", title).lower().split())
            first_words = set(re.sub(r"[^\w\s]", "", first).lower().split())
            overlap = len(title_words & first_words) / max(len(title_words), 1)
            if overlap >= 0.5:
                lines = lines[1:]
        cleaned = "\n".join(lines)

    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    cleaned = strip_et_tail(cleaned)
    cleaned = dedup_repeated_paragraphs(cleaned)
    return cleaned.strip()


# ─────────────────────────────────────────────────────────────
# SCRAPERS
# ─────────────────────────────────────────────────────────────

def scrape_with_trafilatura(url: str) -> str:
    if not TRAFILATURA_AVAILABLE:
        return ""
    try:
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            return ""
        result = trafilatura.extract(
            downloaded,
            include_comments=False,
            include_tables=False,
            no_fallback=False,
        )
        return (result or "").strip()
    except Exception:
        return ""


def scrape_with_newspaper(url: str) -> str:
    if not NEWSPAPER_AVAILABLE:
        return ""
    try:
        article = Article(url)
        article.download()
        article.parse()
        return article.text.strip()
    except Exception:
        return ""


def scrape_with_requests(url: str) -> str:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=12)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        for tag in soup(["script", "style", "nav", "header",
                         "footer", "aside", "form", "iframe"]):
            tag.decompose()

        # ET-specific article body selectors
        body = (
            soup.find("div", class_=re.compile(r"artText|article[_-]?body|story[_-]?content", re.I))
            or soup.find("article")
            or soup.find("div", class_=re.compile(r"content|story|post", re.I))
            or soup.find("main")
        )
        paragraphs = (body or soup).find_all("p")
        text = " ".join(
            p.get_text(strip=True) for p in paragraphs
            if len(p.get_text(strip=True)) > 40
        )
        return text.strip()
    except Exception:
        return ""


def scrape_article(url: str, rss_summary: str = "", title: str = "") -> str:
    """
    Fallback chain: trafilatura → newspaper3k → requests+BS4 → RSS summary.
    Cleans ET boilerplate from whichever source succeeds.
    """
    MIN_WORDS = 150

    def wc(t: str) -> int:
        return len(t.split()) if t else 0

    # Skip slideshow/liveblog URLs — they have no article body to scrape
    if "/slideshow/" in url or "/liveblog/" in url:
        cleaned = clean_et_content(rss_summary, title=title)
        return cleaned if wc(cleaned) > 30 else ""

    for scraper in [scrape_with_trafilatura, scrape_with_newspaper, scrape_with_requests]:
        raw     = scraper(url)
        cleaned = clean_et_content(raw, title=title)
        if wc(cleaned) >= MIN_WORDS:
            return cleaned

    # Fallback: RSS summary
    if rss_summary:
        cleaned = clean_et_content(rss_summary, title=title)
        if wc(cleaned) > 30:
            return cleaned

    return ""


# ─────────────────────────────────────────────────────────────
# QUALITY GATE
# ─────────────────────────────────────────────────────────────

def assess_quality(content: str) -> dict:
    words = len(content.split()) if content else 0
    return {
        "word_count": words,
        "quality": (
            "rich"  if words >= 300 else
            "thin"  if words >= 150 else
            "bare"  if words >= 50  else
            "empty"
        ),
    }


# ─────────────────────────────────────────────────────────────
# MAIN FETCHER
# ─────────────────────────────────────────────────────────────

def fetch_economic_times(
    top_n: int = 50,
    scrape: bool = True,
    delay: float = 1.5
) -> list:
    """
    Fetches ET Markets RSS and enriches each article with
    full scraped content from the article URL.

    Args:
        top_n:  max articles to return after filtering
        scrape: fetch full article from URL (recommended: True)
        delay:  seconds between HTTP requests
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
            if len(articles) >= top_n:
                break

            title     = entry.get("title",     "").strip()
            link      = entry.get("link",      "").strip()
            published = entry.get("published", "").strip()
            summary   = entry.get("summary",   "").strip()

            if not title:
                continue

            # Skip live price tracker entries
            title_lower = title.lower()
            if any(pat in title_lower for pat in SKIP_PATTERNS):
                skipped += 1
                continue

            # Skip empty description entries that aren't worth scraping
            if not summary and not link:
                skipped += 1
                continue

            # Dedup
            if title_lower in seen_titles:
                continue
            seen_titles.add(title_lower)

            # Scrape full article
            if scrape and link:
                full_content = scrape_article(link, summary, title=title)
                time.sleep(delay)
            else:
                full_content = clean_et_content(summary, title=title)

            # Skip if nothing usable
            if not full_content or len(full_content.split()) < 30:
                skipped += 1
                continue

            quality = assess_quality(full_content)

            articles.append({
                "Blog_Title":       title,
                "Blog_Links":       link,
                "Blog_PublishDate": published,
                "Blog_Content":     full_content,
                "source_name":      "Economic Times",
                "source":           "economic_times",
                "_source_type":     "news",
                "_content_words":   quality["word_count"],
                "_content_quality": quality["quality"],
            })

    except Exception as e:
        print(f"[ET] Feed failed: {e}")

    print(f"[ET] Skipped: {skipped} | Valid: {len(articles)}")
    return articles


# ─────────────────────────────────────────────────────────────
# TEST
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  Economic Times Markets RSS Fetcher")
    print("=" * 60)

    results = fetch_economic_times(top_n=10, scrape=True, delay=1.5)

    print(f"\nTotal: {len(results)}")
    print("=" * 60)

    for i, r in enumerate(results, 1):
        print(f"\n[{i}] Title   : {r['Blog_Title']}")
        print(f"    Link    : {r['Blog_Links']}")
        print(f"    Date    : {r['Blog_PublishDate']}")
        print(f"    Quality : {r['_content_quality']} ({r['_content_words']} words)")
        print(f"    Content : {r['Blog_Content']}")
        print(f"    ---")