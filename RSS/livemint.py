# RSS/livemint.py

import feedparser
import requests
import time
import re
from bs4 import BeautifulSoup
from datetime import datetime

from RSS.common import assess_quality

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

MINT_FEEDS = [
    "https://www.livemint.com/rss/news",
    "https://www.livemint.com/rss/markets",
    "https://www.livemint.com/rss/companies",
    "https://www.livemint.com/rss/money",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept":          "text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "en-IN,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer":         "https://www.google.com/",
    "Connection":      "keep-alive",
}

SKIP_PATTERNS = [
    "quote of the day",
    "live updates",
    "live blog",
    "live:",
    "weather",
    "imd issues",
    "imd alert",
    "google doodle",
    "watch:",
    "videos",
    "in photos",
    "in pictures",
    "cockroach janta party",
    "world news today live",
]


# ─────────────────────────────────────────────────────────────
# BOILERPLATE PATTERNS
# ─────────────────────────────────────────────────────────────

MINT_STRIP_PATTERNS = [
    r"^catch all the business news.*",
    r"^subscribe to mint newsletters.*",
    r"^download the mint app.*",
    r"^mint is now on whatsapp.*",
    r"^follow mint on.*",
    r"^also read.*",
    r"^read more.*",
    r"^[\(\[]?disclaimer:.*",
    r"^follow us on.*",
    r"^click here.*",
    r"^for.*latest.*news.*",
    r"^stay.*updated.*",
    r"^topics?:.*",
    r"^tags?:.*",
    r"^first published.*",
    r"^updated.*\d{4}.*",
    r"^milestone alert.*",
    r"^unlock a world.*",
    r"^log in.*to read.*",
    r"^subscribe.*to read.*",
    r"^premium.*article.*",
    r"^\(edited by.*\)$",
    r"^\(with.*inputs.*\)$",
    r"^\(source:.*\)$",
    r"^oops!\s*looks like.*",
    r"^remove some to bookmark.*",
    r"^--with (assistance|reporting) from.*",
    r"^more stories like this.*bloomberg.*",
    r"^\(reporting by.*\)$",
    r"^\(—\s*with inputs from.*\)$",
    r"^x/\s*twitter handle:.*",
    r"^linkedin:.*",
    r"^she can be (found|reached).*",
    r"^he can be (found|reached).*",
    r"^outside (of work|work),.*",
    r"^quick answers to key questions\s*$",   # Mint AI FAQ box header
]

FOOTER_SIGNALS = re.compile(
    r"^(catch all|subscribe to mint|download the mint"
    r"|mint is now|follow mint|also read|read more"
    r"|disclaimer|\(disclaimer|follow us|first published"
    r"|updated.*\d{4}|topics?:|tags?:|milestone alert"
    r"|unlock a world|log in.*to read|subscribe.*to read"
    r"|\(edited by|\(with.*inputs|\(source:"
    r"|oops!|remove some to"
    r"|--with assistance|--with reporting"
    r"|more stories like this"
    r"|she can be found|he can be found|she can be reached"
    r"|outside of work|x/\s*twitter handle|linkedin:)",
    re.IGNORECASE
)

# Wire service prefix at start of article
WIRE_PREFIX = re.compile(r"^\([A-Za-z]+\)\s*--?\s*", re.IGNORECASE)

# Bio trigger: "Name is [Role] at [Publication]"
# Covers: "Gulam Jeelani is Political Desk Editor at LiveMint"
#         "Jocelyn Fernandes is a journalist and editor..."
BIO_TRIGGERS = re.compile(
    r"^[A-Z][a-z]+ [A-Z][a-z]+\s+is\s+(a |an )?\w.{5,80}"
    r"\s+at\s+(livemint|mint|hindustan times|bloomberg|reuters"
    r"|ht digital|htdigital|cnbc|economic times|business standard)",
    re.IGNORECASE
)

# Bio continuation lines
BIO_CONTINUATION = re.compile(
    r"^(he|she|they)\s+(has|have|holds?|is|was|can be|enjoys?"
    r"|attended|worked|travels?|publishes?|covers?|focuses?"
    r"|joined|honed|based in|holds a bachelors|holds a masters"
    r"|is a bachelors)",
    re.IGNORECASE
)


# ─────────────────────────────────────────────────────────────
# AUTHOR BIO DETECTOR
# ─────────────────────────────────────────────────────────────

# Replace the BIO_TRIGGERS and find_bio_start with this smarter version

# Any line containing these signals is NOT article content
BIO_SIGNAL_PATTERNS = re.compile(
    r"as chief content producer|"
r"as (a |an )?(senior |deputy |chief )?(editor|journalist|reporter)|"
r"publishes breaking|"
r"covers? (the )?\w+ (beat|desk)|"
    r"(years of experience|"
    r"has previously worked|"
    r"writing philosophy|"
    r"covers? the .{5,30} beat|"
    r"based in (new delhi|mumbai|bengaluru|delhi)|"
    r"can be reached at|"
    r"holds? a (bachelors?|masters?|pgd|diploma|degree)|"
    r"graduated from|"
    r"journalism and (mass )?communication|"
    r"formerly (with|at)|"
    r"prior to (joining|this)|"
    r"@htdigital\.in|"
    r"@livemint\.com|"
    r"\.fernandes@|"
    r"publishes breaking stories|"
    r"explainers, features and live blogs|"
    r"is a journalist and editor|"
    r"is an editor (with|at)|"
    r"is a senior (journalist|editor|reporter)|"
    r"is (a |an )(journalist|editor|reporter|writer|analyst|correspondent)"
    r")",
    re.IGNORECASE
)


def find_bio_start(lines: list) -> int:
    """
    Finds the line index where article content ends and
    author bio begins.

    Strategy: scan backwards. The first line that contains
    a bio signal pattern is the start of the bio block.
    Walk backwards from there to capture any bio lines
    that appeared before the trigger.
    """
    # Forward scan from end — find last bio signal line
    bio_start = len(lines)

    for i in range(len(lines) - 1, -1, -1):
        s = lines[i].strip()
        if not s:
            continue

        # Email address on its own line — definitely bio
        if re.match(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$', s):
            bio_start = i
            continue

        # Twitter handle on its own line
        if re.match(r'^@[a-zA-Z0-9_]{3,}$', s):
            bio_start = i
            continue

        if BIO_SIGNAL_PATTERNS.search(s):
            bio_start = i
        else:
            # First non-bio line from the end — stop here
            # but only if we've already found some bio lines
            if bio_start < len(lines):
                break

    return bio_start


# ─────────────────────────────────────────────────────────────
# CONTENT CLEANER
# ─────────────────────────────────────────────────────────────

def clean_mint_content(text: str, title: str = "") -> str:
    """
    Cleans Livemint article content with dynamic bio detection.

    Operations:
      1. Strip HTML tags if present
      2. Remove boilerplate lines
      3. Strip wire service prefix (Bloomberg/Reuters)
      4. Remove duplicate headline
      5. Detect and remove author bio block
      6. Normalise whitespace
      7. Strip trailing footer block
      8. Deduplicate paragraphs
    """
    if not text:
        return ""

    # Strip HTML if leaked
    if "<" in text and ">" in text:
        text = BeautifulSoup(text, "html.parser").get_text(
            separator="\n", strip=True
        )

    lines         = text.split("\n")
    cleaned_lines = []

    for line in lines:
        s = line.strip()
        if not s:
            continue
        is_boilerplate = any(
            re.match(p, s, re.IGNORECASE)
            for p in MINT_STRIP_PATTERNS
        )
        is_promo = (
            len(s) < 80
            and re.match(
                r"^(read|follow|subscribe|download|click"
                r"|join|get|stay|share|log in|unlock)",
                s, re.IGNORECASE
            )
        )
        if not is_boilerplate and not is_promo:
            cleaned_lines.append(s)

    # Strip wire prefix from first line
    if cleaned_lines:
        first = WIRE_PREFIX.sub("", cleaned_lines[0]).strip()
        if first:
            cleaned_lines[0] = first

    # Strip duplicate headline
    if cleaned_lines and title:
        first = cleaned_lines[0].strip()
        if len(first) < 150 and not first.endswith((".", "?", "!")):
            t_words = set(re.sub(r"[^\w\s]", "", title).lower().split())
            f_words = set(re.sub(r"[^\w\s]", "", first).lower().split())
            overlap = len(t_words & f_words) / max(len(t_words), 1)
            if overlap >= 0.5:
                cleaned_lines = cleaned_lines[1:]

    # ── Remove author bio block ───────────────────────────────
    bio_start = find_bio_start(cleaned_lines)
    if bio_start < len(cleaned_lines):
        cleaned_lines = cleaned_lines[:bio_start]

    cleaned = "\n".join(cleaned_lines)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

    # Strip trailing footer
    lines     = cleaned.split("\n")
    last_real = len(lines) - 1
    for i in range(len(lines) - 1, -1, -1):
        s = lines[i].strip()
        if not s:
            continue
        if FOOTER_SIGNALS.match(s):
            last_real = i - 1
        else:
            break
    cleaned = "\n".join(lines[:last_real + 1]).strip()

    # Deduplicate paragraphs
    paragraphs = [p.strip() for p in cleaned.split("\n\n") if p.strip()]
    seen    = []
    deduped = []
    for p in paragraphs:
        fp = p[:60].lower()
        if fp not in seen:
            seen.append(fp)
            deduped.append(p)

    return "\n\n".join(deduped).strip()


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
        body = (
            soup.find("div", class_=re.compile(
                r"articleBody|storyContent|contentSec"
                r"|mainContent|storyPage|article[_-]?body",
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
    MIN_WORDS = 150

    def wc(t): return len(t.split()) if t else 0

    if any(p in url for p in ["/live-", "-live-", "live-updates",
                               "/slideshow/", "/photos/", "/videos/"]):
        return clean_mint_content(rss_summary, title=title)

    for scraper in [scrape_with_trafilatura,
                    scrape_with_newspaper,
                    scrape_with_requests]:
        raw     = scraper(url)
        cleaned = clean_mint_content(raw, title=title)
        if wc(cleaned) >= MIN_WORDS:
            return cleaned

    return clean_mint_content(rss_summary, title=title)


# ─────────────────────────────────────────────────────────────
# QUALITY GATE
# ─────────────────────────────────────────────────────────────



# ─────────────────────────────────────────────────────────────
# MAIN FETCHER
# ─────────────────────────────────────────────────────────────

def fetch_livemint(
    top_n: int = 10,
    scrape: bool = True,
    delay: float = 1.5,
) -> list:
    """
    Fetches articles from Livemint RSS feeds and enriches each
    with full scraped content from the article URL.

    Covers news, markets, companies, and money sections.
    Filters out non-financial content (quotes, weather, live blogs).
    Dynamically strips author bios and wire service boilerplate.
    """
    print(f"[MINT] Fetching Livemint...")

    articles    = []
    seen_titles = set()
    skipped     = 0

    for feed_url in MINT_FEEDS:
        if len(articles) >= top_n:
            break

        try:
            feed    = feedparser.parse(feed_url)
            section = feed_url.split("/")[-1]

            if not feed.entries:
                print(f"[MINT] {section}: 0 entries (may be blocked)")
                continue

            print(f"[MINT] {section}: {len(feed.entries)} entries")

            for entry in feed.entries:
                if len(articles) >= top_n:
                    break

                title = entry.get("title", "").strip()
                if not title:
                    continue

                title_lower = title.lower()

                if any(p in title_lower for p in SKIP_PATTERNS):
                    skipped += 1
                    continue

                if title_lower in seen_titles:
                    skipped += 1
                    continue
                seen_titles.add(title_lower)

                link     = entry.get("link", "").strip()
                pub_date = entry.get("published", "").strip()

                iso_date = ""
                if "published_parsed" in entry and entry.published_parsed:
                    try:
                        iso_date = datetime(
                            *entry.published_parsed[:6]
                        ).isoformat()
                    except Exception:
                        pass

                summary = (
                    entry.get("summary", "")
                    or entry.get("description", "")
                ).strip()
                if summary and "<" in summary:
                    summary = BeautifulSoup(
                        summary, "html.parser"
                    ).get_text(separator=" ", strip=True)

                if scrape and link:
                    full_content = scrape_article(
                        link, summary, title=title
                    )
                    time.sleep(delay)
                else:
                    full_content = clean_mint_content(summary, title=title)

                quality = assess_quality(full_content)

                articles.append({
                    "Blog_Title":       title,
                    "Blog_Links":       link,
                    "Blog_PublishDate": pub_date,
                    "Blog_Content":     full_content,
                    "source_name":      "Livemint",
                    "source":           "livemint",
                    "_source_type":     "news",
                    "_content_words":   quality["word_count"],
                    "_content_quality": quality["quality"],
                    "_iso_date":        iso_date,
                })

        except Exception as e:
            print(f"[MINT] Feed error ({feed_url}): {e}")

    print(f"[MINT] Skipped: {skipped} | Valid: {len(articles)}")
    return articles


# ─────────────────────────────────────────────────────────────
# TEST
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    results = fetch_livemint(top_n=10, scrape=True, delay=1.5)

    print(f"\nTotal: {len(results)}")
    print("=" * 60)

    for i, r in enumerate(results, 1):
        print(f"\n[{i}] Title   : {r['Blog_Title']}")
        print(f"    Link    : {r['Blog_Links']}")
        print(f"    Date    : {r['Blog_PublishDate']}")
        print(f"    Quality : {r['_content_quality']} ({r['_content_words']} words)")
        print(f"    Content : {r['Blog_Content']}...")
        print(f"    ---")