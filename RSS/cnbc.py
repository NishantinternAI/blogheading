# RSS/cnbc.py

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

# Multiple CNBC TV18 RSS feeds — economy, markets, finance
CNBC_FEEDS = [
    "https://www.cnbctv18.com/commonfeeds/v1/cne/rss/economy.xml",
    "https://www.cnbctv18.com/commonfeeds/v1/cne/rss/market.xml",
    "https://www.cnbctv18.com/commonfeeds/v1/cne/rss/finance.xml",
    "https://www.cnbctv18.com/commonfeeds/v1/cne/rss/india.xml",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept":          "text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "en-IN,en;q=0.9",
    "Referer":         "https://www.google.com/",
}

# CNBC TV18 boilerplate patterns
CNBC_STRIP_PATTERNS = [
    r"^\d+\s+min\s+read.*",           # ← new: "2 Min Read", "5 Min Read"
    r"^\(edited by\s*:.*\)",          # ← new: "(Edited by : Prashant)"
    r"^\(with agency inputs.*\)",     # ← new: "(With agency inputs)"
    r"^\(source:.*\)",                # ← new: "(Source: RBI, as of...)"
    r"^also read.*",
    r"^read more.*",
    r"^[\(\[]?disclaimer:.*",
    r"^follow us on.*",
    r"^subscribe.*",
    r"^download.*app.*",
    r"^for.*latest.*news.*",
    r"^click here.*",
    r"^stay.*updated.*",
    r"^share this.*",
    r"^topics?:.*",
    r"^tags?:.*",
    r"^first published.*",
    r"^updated.*\d{4}.*",
    r"^catch.*latest.*",
    r"^check.*live.*",
    r"^sr\s*no\s+company\s+name.*",     # table header
    r"^\d+\s+[A-Z][A-Za-z\s&().]+$",
    r"^the monsoon$",
r"^oil prices surge.*$",      # section subheadings in the Hormuz article
r"^why is the strait.*$",
r"^is india particularly.*$",
r"^what happens to oil.*$",
r"^could petrol and diesel.*$",
r"^impact on lpg.*$",
r"^inflation risks.*$",
r"^fertiliser and agriculture.*$",
]

FOOTER_SIGNALS = re.compile(
    r"^(also read|read more|disclaimer|\(disclaimer"
    r"|follow us|subscribe|download.*app|first published"
    r"|updated.*\d{4}|catch.*latest|topics?:|tags?:"
    r"|share this|check.*live"
    r"|\(edited by|\(with agency|\(source:)",   # ← new
    re.IGNORECASE
)
# Skip live update / price tracker entries
SKIP_PATTERNS = [
    "live updates",
    "live blog",
    "live: ",
    "share price live",
    "stock price live",
    "market live",
    "nifty live",
    "sensex live",
]


# ─────────────────────────────────────────────────────────────
# CONTENT CLEANER
# ─────────────────────────────────────────────────────────────

def strip_tail(text: str) -> str:
    lines     = text.split("\n")
    last_real = len(lines) - 1
    for i in range(len(lines) - 1, -1, -1):
        s = lines[i].strip()
        if not s:
            continue
        if FOOTER_SIGNALS.match(s):
            last_real = i - 1
        else:
            break
    return "\n".join(lines[:last_real + 1]).strip()





def is_section_subheading(line: str) -> bool:
    """
    Detects CNBC TV18 section subheadings that trafilatura
    captures as plain text lines. These are short, title-cased
    lines with no terminal punctuation that appear mid-article.
    """
    s = line.strip()
    if not s or len(s) > 80:
        return False
    if s.endswith(('.', '?', '!', ':', '"', "'")):
        return False
    words = s.split()
    if len(words) < 2 or len(words) > 10:
        return False
    # Title-cased or all-caps short phrase with no sentence structure
    title_case_ratio = sum(1 for w in words if w and w[0].isupper()) / len(words)
    return title_case_ratio >= 0.7

def dedup_paragraphs(text: str) -> str:
    """Remove duplicate paragraphs using 60-char fingerprint."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    seen    = []
    deduped = []
    for p in paragraphs:
        fp = p[:60].lower()
        if fp not in seen:
            seen.append(fp)
            deduped.append(p)
    return "\n\n".join(deduped)



def dedup_sentences(text: str) -> str:
    sentences = re.split(r'(?<=[.!?])\s+', text)
    seen    = []
    deduped = []
    for s in sentences:
        s = s.strip()
        if not s:
            continue
        # Skip very short fragments — likely broken section headers
        if len(s.split()) < 4 and not s.endswith(('.', '!', '?')):
            continue
        fp = re.sub(r'\s+', ' ', s[:80]).lower()
        if fp not in seen:
            seen.append(fp)
            deduped.append(s)
    return " ".join(deduped)


def clean_cnbc_content(text: str, title: str = "") -> str:
    """
    Cleans CNBC TV18 article text — strips boilerplate,
    removes duplicate headline, normalises whitespace.
    """
    if not text:
        return ""

    # Strip HTML tags if any leaked through
    if "<" in text and ">" in text:
        text = BeautifulSoup(text, "html.parser").get_text(
            separator=" ", strip=True
        )

    lines         = text.split("\n")
    cleaned_lines = []

    for line in lines:
        s = line.strip()
        if not s:
            continue
        if is_section_subheading(s):
            continue

        is_boilerplate = any(
            re.match(p, s, re.IGNORECASE)
            for p in CNBC_STRIP_PATTERNS
        )
        is_promo = (
            len(s) < 80
            and re.match(
                r"^(read|follow|subscribe|download|click"
                r"|join|get|stay|share|check|catch)",
                s, re.IGNORECASE
            )
        )
        if not is_boilerplate and not is_promo:
            cleaned_lines.append(s)

    cleaned = "\n".join(cleaned_lines)

    # Strip duplicate headline from top
    lines = cleaned.split("\n")
    if lines and title:
        first = lines[0].strip()
        if len(first) < 150 and not first.endswith((".", "?", "!")):
            t_words = set(re.sub(r"[^\w\s]", "", title).lower().split())
            f_words = set(re.sub(r"[^\w\s]", "", first).lower().split())
            overlap = len(t_words & f_words) / max(len(t_words), 1)
            if overlap >= 0.5:
                lines = lines[1:]
        cleaned = "\n".join(lines)

    cleaned = re.sub(
    r'\s+([A-Z][a-zA-Z ]{2,30})\n([A-Z,])',  # "The monsoon\nBased on..."
    r' \2',
    cleaned
)
    cleaned = strip_tail(cleaned)
    cleaned = dedup_paragraphs(cleaned)
    cleaned = dedup_sentences(cleaned)
    return cleaned.strip()


# ─────────────────────────────────────────────────────────────
# SCRAPERS
# CNBC TV18 blocks server/cloud IPs (IP allowlist WAF).
# These scrapers are attempted but will fall back to
# RSS summary on your production server.
# They WILL work when running locally.
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
        for tag in soup(["script", "style", "nav",
                         "header", "footer", "aside"]):
            tag.decompose()
        body = (
            soup.find("div", class_=re.compile(
                r"article[_-]?body|story[_-]?content"
                r"|post[_-]?content|article[_-]?text"
                r"|storybody|article-detail",
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


def scrape_article(url: str, rss_summary: str = "",
                   title: str = "") -> str:
    """
    Tries full article scraping, falls back to RSS summary.

    NOTE: CNBC TV18 blocks server/cloud IPs via IP allowlist WAF.
    Scraping works locally but will fall back to RSS summary
    when running on a server. RSS summaries are 50-150 words
    and routed to generate_brief in the pipeline.
    """
    MIN_WORDS = 150

    def wc(t): return len(t.split()) if t else 0

    # Try full scrapers
    for scraper in [scrape_with_trafilatura,
                    scrape_with_newspaper,
                    scrape_with_requests]:
        raw     = scraper(url)
        cleaned = clean_cnbc_content(raw, title=title)
        if wc(cleaned) >= MIN_WORDS:
            return cleaned

    # Fall back to RSS summary — always available
    return clean_cnbc_content(rss_summary, title=title)


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

def fetch_cnbc(
    top_n: int = 10,
    scrape: bool = True,
    delay: float = 1.5,
) -> list:
    """
    Fetches articles from CNBC TV18 RSS feeds.

    Covers economy, market, finance, and india sections.
    Tries to scrape full article content from each URL.
    Falls back to RSS summary if scraping is blocked
    (CNBC TV18 uses an IP allowlist WAF on server IPs).

    Args:
        top_n:  max articles to return across all feeds
        scrape: attempt full article scraping (True recommended)
        delay:  seconds between HTTP requests
    """
    print(f"[CNBC] Fetching CNBC TV18...")

    articles    = []
    seen_titles = set()
    skipped     = 0

    for feed_url in CNBC_FEEDS:
        if len(articles) >= top_n:
            break

        try:
            feed = feedparser.parse(feed_url)

            if not feed.entries:
                print(f"[CNBC] {feed_url.split('/')[-1]}: 0 entries (may be blocked)")
                continue

            section = feed_url.split("/")[-1].replace(".xml", "")
            print(f"[CNBC] {section}: {len(feed.entries)} entries")

            for entry in feed.entries:
                if len(articles) >= top_n:
                    break

                title = entry.get("title", "").strip()
                if not title:
                    continue

                title_lower = title.lower()

                # Skip live update entries
                if any(p in title_lower for p in SKIP_PATTERNS):
                    skipped += 1
                    continue

                # Dedup
                if title_lower in seen_titles:
                    skipped += 1
                    continue
                seen_titles.add(title_lower)

                link     = entry.get("link", "").strip()
                pub_date = entry.get("published", "").strip()

                # Get RSS summary — strip HTML if present
                summary = entry.get("summary", "").strip()
                if summary and "<" in summary:
                    summary = BeautifulSoup(
                        summary, "html.parser"
                    ).get_text(separator=" ", strip=True)

                # Try to scrape full article
                if scrape and link:
                    full_content = scrape_article(
                        link, summary, title=title
                    )
                    time.sleep(delay)
                else:
                    full_content = clean_cnbc_content(summary, title=title)

                quality = assess_quality(full_content)

                articles.append({
                    "Blog_Title":       title,
                    "Blog_Links":       link,
                    "Blog_PublishDate": pub_date,
                    "Blog_Content":     full_content,
                    "source_name":      "CNBC TV18",
                    "source":           "cnbc_tv18",
                    "_source_type":     "news",
                    "_content_words":   quality["word_count"],
                    "_content_quality": quality["quality"],
                })

        except Exception as e:
            print(f"[CNBC] Feed error for {feed_url}: {e}")

    print(f"[CNBC] Skipped: {skipped} | Valid: {len(articles)}")
    return articles


# ─────────────────────────────────────────────────────────────
# TEST
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    results = fetch_cnbc(top_n=10, scrape=True, delay=1.5)

    print(f"\nTotal: {len(results)}")
    print("=" * 60)

    for i, r in enumerate(results, 1):
        print(f"\n[{i}] Title   : {r['Blog_Title']}")
        print(f"    Link    : {r['Blog_Links']}")
        print(f"    Date    : {r['Blog_PublishDate']}")
        print(f"    Quality : {r['_content_quality']} ({r['_content_words']} words)")
        print(f"    Content : {r['Blog_Content']}")
        print(f"    ---")