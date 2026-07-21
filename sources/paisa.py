import feedparser
import requests
import time
import re
from bs4 import BeautifulSoup

from sources.common import assess_quality

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
# CONTENT CLEANER
# ─────────────────────────────────────────────────────────────

# Boilerplate lines to strip from 5paisa articles
# STRIP_PATTERNS = [
#     r"join 5paisa and stay updated.*",
#     r"flat\s*₹20 brokerage.*",
#     r"next-gen trading.*",
#     r"advanced charting.*",
#     r"actionable ideas.*",
#     r"trending on 5paisa.*",
#     r"disclaimer:.*",
#     r"investment in securities.*",
#     r"read all the related documents.*",
#     r"for detailed disclaimer.*",
#     r"0 transaction cost.*",
#     r"curated fund lists.*",
#     r"4,000\+ mf schemes.*",
#     r"start sip with ease.*",
#     r"free ipo application.*",
#     r"apply with ease.*",
#     r"pre-apply for ipos.*",
#     r"upi bid instantly.*",
#     r"last updated:.*",
#     r"summary:.*\n",
#     r"^ps d:\\.*", 
#                           # strip the "Summary:" label line
# ]
def strip_5paisa_tail(text: str) -> str:
    """
    Removes the promotional footer block that 5paisa appends to
    every article. These lines always appear at the end and start
    with a dash followed by a short promotional phrase.

    Pattern: after the real article ends, there's a cluster of
    short "- Feature Name" lines like:
        - Flat ₹20 Brokerage
        - Next-gen Trading
        - 0 Transaction cost
        - 4,000+ MF Schemes
    """
    lines = text.split("\n")

    # Walk backwards from the end, dropping lines that look like
    # footer bullets or are empty
    FOOTER_SIGNALS = re.compile(
        r"^-\s*(flat|next-gen|advanced|actionable|trending|0 trans"
        r"|curated|4,000|start sip|free ipo|apply with|pre-apply"
        r"|upi bid|\d+,?\d*\+?\s*(mf|etf|scheme|sip|transaction))",
        re.IGNORECASE
    )

    # Find the last line that is clearly article content
    last_real_line = len(lines) - 1
    for i in range(len(lines) - 1, -1, -1):
        stripped = lines[i].strip()
        if not stripped:
            continue
        if FOOTER_SIGNALS.match(stripped):
            last_real_line = i - 1
        else:
            break

    return "\n".join(lines[:last_real_line + 1]).strip()






def clean_5paisa_content(text: str) -> str:
    if not text:
        return ""

    STRIP_PATTERNS = [
        r"^join 5paisa.*",
        r"^flat\s*₹20 brokerage.*",
        r"^next-gen trading.*",
        r"^advanced charting.*",
        r"^actionable ideas.*",
        r"^trending on 5paisa.*",
        r"^disclaimer:.*",
        r"^investment in securities.*",
        r"^read all the related documents.*",
        r"^for detailed disclaimer.*",
        r"^0 transaction cost.*",
        r"^curated fund lists.*",
        r"^4,000\+ mf schemes.*",
        r"^start sip with ease.*",
        r"^free ipo application.*",
        r"^apply with ease.*",
        r"^pre-apply for ipos.*",
        r"^upi bid instantly.*",
        r"^last updated:.*",
        r"^summary:$",               # ← strip standalone "Summary:" label line
        r"^ps d:\\.*",               # ← strip any shell prompt leakage
    ]

    lines = text.split("\n")
    cleaned_lines = []

    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue

        is_boilerplate = any(
            re.match(pattern, line_stripped, re.IGNORECASE)
            for pattern in STRIP_PATTERNS
        )

        # Short bullet-point ad lines starting with "-"
        is_ad_bullet = (
            line_stripped.startswith("-")
            and len(line_stripped) < 60
            and not any(c.isdigit() for c in line_stripped)  # keep lines with numbers
        )

        if not is_boilerplate and not is_ad_bullet:
            cleaned_lines.append(line_stripped)

    cleaned = "\n".join(cleaned_lines)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

    cleaned = strip_5paisa_tail(cleaned)
    return cleaned.strip()

def deduplicate_opener(content: str, title: str) -> str:
    """
    Removes the first paragraph of scraped content if it's essentially
    just a restatement of the title (common in 5paisa articles).
    """
    lines = content.strip().split("\n")
    if not lines:
        return content

    first_para = lines[0].strip()

    # Calculate word overlap between first paragraph and title
    title_words  = set(title.lower().split())
    para_words   = set(first_para.lower().split())
    overlap      = len(title_words & para_words)
    overlap_pct  = overlap / max(len(title_words), 1)

    # If more than 60% of title words appear in the first paragraph, it's a restatement
    if overlap_pct > 0.6 and len(first_para) < 250:
        return "\n".join(lines[1:]).strip()

    return content
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
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }
        response = requests.get(url, headers=headers, timeout=12)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        for tag in soup(["script", "style", "nav", "header",
                         "footer", "aside", "form", "iframe"]):
            tag.decompose()

        article_body = (
            soup.find("article")
            or soup.find("div", class_=re.compile(
                r"article|content|story|post", re.I))
            or soup.find("main")
        )

        paragraphs = (article_body or soup).find_all("p")
        text = " ".join(
            p.get_text(strip=True) for p in paragraphs
            if len(p.get_text(strip=True)) > 40
        )
        return text.strip()
    except Exception:
        return ""


def scrape_article(url: str, rss_summary: str = "",title: str = "") -> str:
    """
    Fallback chain: trafilatura → newspaper3k → requests+BS4 → RSS summary.
    Cleans 5paisa boilerplate from whichever source succeeds.
    """
    MIN_WORDS = 150

    def word_count(t: str) -> int:
        return len(t.split()) if t else 0

    for scraper in [
        scrape_with_trafilatura,
        scrape_with_newspaper,
        scrape_with_requests,
    ]:
        raw = scraper(url)
        cleaned = clean_5paisa_content(raw)
        cleaned = deduplicate_opener(cleaned, title)
        if word_count(cleaned) >= MIN_WORDS:
            return cleaned

    # Last resort: RSS summary (clean it too)
    if rss_summary:
        cleaned = clean_5paisa_content(rss_summary)
        if word_count(cleaned) > 30:
            return cleaned

    return ""


# ─────────────────────────────────────────────────────────────
# QUALITY GATE
# ─────────────────────────────────────────────────────────────



# ─────────────────────────────────────────────────────────────
# MAIN FETCHER
# ─────────────────────────────────────────────────────────────

def fetch_5paisa(scrape: bool = True, delay: float = 1.5) -> list:
    """
    Fetches 5paisa RSS and enriches each item with full cleaned article.

    Args:
        scrape: fetch full article from URL (recommended: True)
        delay:  seconds between requests — be polite to the server
    """
    url  = "https://www.5paisa.com/rss/news.xml"
    feed = feedparser.parse(url)
    data = []

    for entry in feed.entries:
        rss_summary = entry.get("summary", "")
        article_url = entry.get("link", "")
        title=entry.get("title","")

        if scrape and article_url:
            full_content = scrape_article(article_url, rss_summary,title)
            time.sleep(delay)
        else:
            full_content = clean_5paisa_content(rss_summary)

        quality = assess_quality(full_content)

        item = {
            "Blog_Title":       entry.get("title", ""),
            "Blog_Links":       article_url,
            "Blog_PublishDate": entry.get("published", ""),
            "Blog_Content":     full_content,
            "source_name":      "5paisa",
            "source":           "5paisa",
            "_source_type":     "news",
            "_content_words":   quality["word_count"],
            "_content_quality": quality["quality"],
        }
        data.append(item)

    return data


# ─────────────────────────────────────────────────────────────
# TEST
# ─────────────────────────────────────────────────────────────


if __name__ == "__main__":
    results = fetch_5paisa(scrape=True, delay=1.5)
    print(f"\nTotal fetched: {len(results)}")
    print("=" * 60)
    for r in results:
        print(f"Title   : {r['Blog_Title']}")
        print("LINK :", r["Blog_Links"])
        print("DATE :", r["Blog_PublishDate"])
        print(f"Quality : {r['_content_quality']} ({r['_content_words']} words)")
        print(f"Content : {r['Blog_Content']}")
        print("---")