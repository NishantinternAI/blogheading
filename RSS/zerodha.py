# RSS/zerodha.py

import feedparser
import requests
import time
import re
from bs4 import BeautifulSoup
from urllib.parse import urlparse

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

try:
    from curl_cffi import requests as cf_requests
    CURL_CFFI_AVAILABLE = True
except ImportError:
    CURL_CFFI_AVAILABLE = False


# ─────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────

ZERODHA_FEED_URL = "https://pulse.zerodha.com/feed.php"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept":                    "text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language":           "en-US,en;q=0.9",
    "Accept-Encoding":           "gzip, deflate, br",
    "Connection":                "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

DOMAIN_HEADERS = {
    "ndtvprofit.com": {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Referer":                   "https://www.ndtvprofit.com/",
        "Accept":                    "text/html,application/xhtml+xml,*/*;q=0.8",
        "Accept-Language":           "en-IN,en;q=0.9",
        "Accept-Encoding":           "gzip, deflate, br",
        "DNT":                       "1",
        "Connection":                "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    },
    "thehindu.com": {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Referer":         "https://www.google.com/",
        "Accept-Language": "en-IN,en;q=0.9",
    },
    "livemint.com": {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Referer": "https://www.google.com/",
    },
    "business-standard.com": {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Referer": "https://www.google.com/",
    },
}


# ─────────────────────────────────────────────────────────────
# UNIVERSAL BOILERPLATE PATTERNS
# ─────────────────────────────────────────────────────────────

UNIVERSAL_STRIP_PATTERNS = [
    # ET
    r"^\(what's moving sensex.*",
    r"^top trending stocks:.*",
    r"^sensex, nifty today:.*",
    r"^\(with inputs from.*",
    r"^data:\s+\w+.*",
    r"^listen to this article.*",
    # The Hindu timestamps
    r"^published\s*[-–]\s*\w+.*\d{4}.*ist.*",
    r"^updated\s*[-–]\s*\w+.*\d{4}.*ist.*",
    # Mint
    r"^catch all the business news.*",
    r"^subscribe to mint newsletters.*",
    r"^download the mint app.*",
    r"^mint is now on whatsapp.*",
    r"^follow mint on.*",
    # Business Standard
    r"^dear reader.*",
    r"^business standard has always.*",
    r"^first published:.*",
    # NDTV Profit
    r"^get latest.*ndtv.*",
    r"^follow us.*ndtv.*",
    r"^ndtv profit.*",
    r"^also watch.*",
    r"^watch.*live.*",
    # General
    r"^also read.*",
    r"^read more.*",
    r"^[\(\[]?disclaimer:.*",
    r"^follow us on.*",
    r"^subscribe.*newsletter.*",
    r"^download.*app.*",
    r"^get.*latest.*news.*",
    r"^click here.*",
    r"^for.*latest.*updates.*",
    r"^stay.*updated.*",
    r"^powered by.*",
    r"^this.*(?:story|article).*(?:generated|automated|ai).*",
    r"^topics?:.*",
    r"^tags?:.*",
    r"^keywords?:.*",
    r"^share this.*",
    r"^print this.*",
    r"^email this.*",
    r"^comments?\s*\(\d*\).*",
    r"^related$",
    r"^related:.*",
]

FOOTER_SIGNALS = re.compile(
    r"^(disclaimer|\(disclaimer|also read|read more"
    r"|follow us|subscribe|download.*app|catch all"
    r"|mint is now|dear reader|first published"
    r"|\(what's moving|top trending|sensex, nifty"
    r"|topics?:|tags?:|share this|print this|email this"
    r"|comments?\s*\(|published\s*[-–]|updated\s*[-–]"
    r"|ndtv profit|get latest.*ndtv|also watch|watch.*live)",
    re.IGNORECASE
)


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────

def get_domain(url: str) -> str:
    try:
        return urlparse(url).netloc.replace("www.", "")
    except Exception:
        return "unknown"


def get_headers_for_url(url: str) -> dict:
    domain = get_domain(url)
    for key, headers in DOMAIN_HEADERS.items():
        if key in domain:
            return headers
    return HEADERS


def clean_ndtv_url(url: str) -> str:
    """Strip tracking fragment from NDTV Profit URLs."""
    return url.split("#")[0]


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


def dedup_paragraphs(text: str) -> str:
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    seen    = []
    deduped = []
    for p in paragraphs:
        fp = p[:60].lower()
        if fp not in seen:
            seen.append(fp)
            deduped.append(p)
    return "\n\n".join(deduped)


def clean_content(text: str, title: str = "") -> str:
    """
    Universal content cleaner for all Zerodha aggregated sources.
    Works across ET, Mint, Business Standard, Livemint,
    The Hindu, and NDTV Profit.
    """
    if not text:
        return ""

    lines         = text.split("\n")
    cleaned_lines = []

    for line in lines:
        s = line.strip()
        if not s:
            continue
        is_boilerplate = any(
            re.match(p, s, re.IGNORECASE)
            for p in UNIVERSAL_STRIP_PATTERNS
        )
        is_promo = (
            len(s) < 80
            and re.match(
                r"^(read|follow|subscribe|download|click"
                r"|join|get|stay|share|print|email)",
                s, re.IGNORECASE
            )
        )
        if not is_boilerplate and not is_promo:
            cleaned_lines.append(s)

    cleaned = "\n".join(cleaned_lines)

    # Strip duplicate headline
    lines = cleaned.split("\n")
    if lines and title:
        first = lines[0].strip()
        if len(first) < 150 and not first.endswith((".", "?", "!")):
            title_words = set(re.sub(r"[^\w\s]", "", title).lower().split())
            first_words = set(re.sub(r"[^\w\s]", "", first).lower().split())
            overlap = len(title_words & first_words) / max(len(title_words), 1)
            if overlap >= 0.5:
                lines = lines[1:]
        cleaned = "\n".join(lines)

    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    cleaned = strip_tail(cleaned)
    cleaned = dedup_paragraphs(cleaned)
    return cleaned.strip()


# ─────────────────────────────────────────────────────────────
# NDTV PROFIT — DEDICATED SCRAPING STRATEGIES
# Strategy 0 (curl_cffi) confirmed working via diagnostic test.
# Strategies 1-3 are fallbacks if curl_cffi ever fails.
# ─────────────────────────────────────────────────────────────

def scrape_ndtv_cffi(url: str) -> str:
    """
    Strategy 0: curl_cffi + Next.js JSON extraction.

    NDTV Profit is a Next.js app. Most pages are client-rendered,
    meaning BeautifulSoup sees an empty shell. However Next.js
    embeds all page data in a <script id="__NEXT_DATA__"> tag
    as JSON. We extract the article content from there.
    """
    if not CURL_CFFI_AVAILABLE:
        return ""

    clean_url = clean_ndtv_url(url)
    try:
        resp = cf_requests.get(
            clean_url,
            impersonate="chrome124",
            timeout=15
        )
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")

        # ── Strategy A: Extract from Next.js __NEXT_DATA__ JSON ──
        next_data_tag = soup.find("script", {"id": "__NEXT_DATA__"})
        if next_data_tag and next_data_tag.string:
            try:
                import json
                next_data = json.loads(next_data_tag.string)

                # Walk the JSON tree to find article text
                text = _extract_text_from_next_data(next_data)
                if text and len(text.split()) >= 50:
                    return text
            except Exception:
                pass

        # ── Strategy B: Direct paragraph extraction (server-rendered pages) ──
        for tag in soup(["script", "style", "nav", "header", "footer"]):
            tag.decompose()

        body = (
            soup.find("div", class_=re.compile(
                r"article[_-]?body|story[_-]?content"
                r"|sp-cn|storyPage|article-text|story__content",
                re.I
            ))
            or soup.find("article")
            or soup.find("main")
        )
        paragraphs = (body or soup).find_all("p")
        text = " ".join(
            p.get_text(strip=True) for p in paragraphs
            if len(p.get_text(strip=True)) > 40
        )
        return text.strip()

    except Exception as e:
        print(f"  [NDTV cffi] ERROR: {e}")
        return ""


def _extract_text_from_next_data(data: dict, depth: int = 0) -> str:
    """
    Recursively walks Next.js __NEXT_DATA__ JSON to find
    article body text. NDTV Profit stores article content
    in various nested keys depending on page type.
    """
    if depth > 10:
        return ""

    import json

    # Common keys where NDTV Profit stores article text
    TEXT_KEYS = [
        "body", "content", "articleBody", "description",
        "storyContent", "fullStory", "articleContent",
        "story", "text", "html", "bodyHtml"
    ]

    collected = []

    if isinstance(data, dict):
        for key, value in data.items():
            if key in TEXT_KEYS and isinstance(value, str) and len(value) > 100:
                # Strip HTML tags from the value
                clean = BeautifulSoup(value, "html.parser").get_text(
                    separator=" ", strip=True
                )
                if len(clean.split()) > 50:
                    collected.append(clean)
            elif isinstance(value, (dict, list)):
                result = _extract_text_from_next_data(value, depth + 1)
                if result:
                    collected.append(result)

    elif isinstance(data, list):
        for item in data:
            result = _extract_text_from_next_data(item, depth + 1)
            if result:
                collected.append(result)

    # Return the longest found text — most likely the article body
    if collected:
        return max(collected, key=lambda t: len(t.split()))
    return ""

def scrape_ndtv_amp(url: str) -> str:
    """
    Strategy 1: Fetch NDTV Profit article via its AMP version.
    AMP pages use Googlebot user-agent and have minimal bot protection.
    """
    clean_url = clean_ndtv_url(url)
    amp_url   = re.sub(
        r"(https?://(?:www\.)?ndtvprofit\.com/)",
        r"\1amp/",
        clean_url
    )
    if amp_url == clean_url:
        return ""
    try:
        resp = requests.get(
            amp_url,
            headers={"User-Agent": "Googlebot/2.1 (+http://www.google.com/bot.html)"},
            timeout=12
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "header",
                         "footer", "amp-ad", "amp-sidebar"]):
            tag.decompose()
        paragraphs = soup.find_all("p")
        return " ".join(
            p.get_text(strip=True) for p in paragraphs
            if len(p.get_text(strip=True)) > 40
        ).strip()
    except Exception:
        return ""


def scrape_ndtv_session(url: str) -> str:
    """
    Strategy 2: Session-based scraping.
    Visits homepage first to collect cookies, then fetches article.
    """
    clean_url = clean_ndtv_url(url)
    session   = requests.Session()
    browser_headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept":                    "text/html,application/xhtml+xml,*/*;q=0.8",
        "Accept-Language":           "en-IN,en;q=0.9",
        "Accept-Encoding":           "gzip, deflate, br",
        "DNT":                       "1",
        "Connection":                "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }
    try:
        session.get(
            "https://www.ndtvprofit.com",
            headers=browser_headers,
            timeout=10
        )
        resp = session.get(
            clean_url,
            headers={**browser_headers, "Referer": "https://www.ndtvprofit.com/"},
            timeout=12
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "header", "footer"]):
            tag.decompose()
        body = (
            soup.find("div", class_=re.compile(
                r"article[_-]?body|story[_-]?content"
                r"|sp-cn|storyPage|article-text", re.I
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


def scrape_via_google_cache(url: str) -> str:
    """
    Strategy 3: Google Cache fallback.
    Served from Google's servers — original site WAF never sees request.
    May be 1-2 days old for very recent articles.
    """
    clean_url = clean_ndtv_url(url)
    cache_url = f"https://webcache.googleusercontent.com/search?q=cache:{clean_url}"
    try:
        resp = requests.get(
            cache_url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                )
            },
            timeout=12
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "header", "footer"]):
            tag.decompose()
        paragraphs = soup.find_all("p")
        return " ".join(
            p.get_text(strip=True) for p in paragraphs
            if len(p.get_text(strip=True)) > 40
        ).strip()
    except Exception:
        return ""


# ─────────────────────────────────────────────────────────────
# STANDARD SCRAPERS (all non-NDTV sources)
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
        headers = get_headers_for_url(url)
        resp    = requests.get(url, headers=headers, timeout=12)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "header",
                         "footer", "aside", "form", "iframe"]):
            tag.decompose()
        body = (
            soup.find("article")
            or soup.find("div", class_=re.compile(
                r"article[_-]?body|story[_-]?content|artText"
                r"|post[_-]?content|entry[_-]?content",
                re.I
            ))
            or soup.find("main")
        )
        paragraphs = (body or soup).find_all("p")
        return " ".join(
            p.get_text(strip=True) for p in paragraphs
            if len(p.get_text(strip=True)) > 40
        ).strip()
    except Exception:
        return ""


# ─────────────────────────────────────────────────────────────
# UNIFIED SCRAPE DISPATCHER
# ─────────────────────────────────────────────────────────────

def scrape_article(url: str, rss_content: str = "", title: str = "") -> str:
    """
    Routes each URL to the right scraping strategy.

    NDTV Profit  → curl_cffi (TLS) → AMP → session → Google Cache → RSS
    Slideshows   → RSS only
    Everything else → trafilatura → newspaper3k → requests+BS4 → RSS
    """
    MIN_WORDS = 150

    def wc(t: str) -> int:
        return len(t.split()) if t else 0

    # Non-article pages — return RSS content directly
    if any(p in url for p in ["/slideshow/", "/liveblog/",
                               "/photos/", "/gallery/"]):
        return clean_content(rss_content, title=title)

    # ── NDTV Profit: four-strategy chain ─────────────────────
    if "ndtvprofit.com" in url:

        # Strategy 0: curl_cffi — confirmed working via diagnostic
        raw     = scrape_ndtv_cffi(url)
        cleaned = clean_content(raw, title=title)
        if wc(cleaned) >= MIN_WORDS:
            print(f"  [NDTV] curl_cffi ✓ ({wc(cleaned)} words)")
            return cleaned

        # Strategy 1: AMP page
        raw     = scrape_ndtv_amp(url)
        cleaned = clean_content(raw, title=title)
        if wc(cleaned) >= MIN_WORDS:
            print(f"  [NDTV] AMP ✓ ({wc(cleaned)} words)")
            return cleaned

        # Strategy 2: Session-based
        raw     = scrape_ndtv_session(url)
        cleaned = clean_content(raw, title=title)
        if wc(cleaned) >= MIN_WORDS:
            print(f"  [NDTV] Session ✓ ({wc(cleaned)} words)")
            return cleaned

        # Strategy 3: Google Cache
        raw     = scrape_via_google_cache(url)
        cleaned = clean_content(raw, title=title)
        if wc(cleaned) >= MIN_WORDS:
            print(f"  [NDTV] Cache ✓ ({wc(cleaned)} words)")
            return cleaned

        # All strategies failed — return RSS snippet
        print(f"  [NDTV] All strategies failed — using RSS snippet")
        return clean_content(rss_content, title=title)

    # ── All other sources: standard chain ────────────────────
    for scraper in [scrape_with_trafilatura,
                    scrape_with_newspaper,
                    scrape_with_requests]:
        raw     = scraper(url)
        cleaned = clean_content(raw, title=title)
        if wc(cleaned) >= MIN_WORDS:
            return cleaned

    # Always return something
    return clean_content(rss_content, title=title)


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
# DIAGNOSTIC (keep for future debugging)
# ─────────────────────────────────────────────────────────────

def diagnose_ndtv(url: str = "https://www.ndtvprofit.com/markets/wipro-buyback-it-giants-rs-15-000-crore-offer-opens-today-how-much-could-shareholders-gain-11621183"):
    """
    Diagnose what's blocking NDTV Profit scraping.
    Run this when NDTV articles start failing to find which
    strategy still works.
    """
    print("=" * 60)
    print("NDTV PROFIT DIAGNOSTIC")
    print("=" * 60)
    print(f"URL: {url}\n")

    print("[TEST 1] Plain requests.get...")
    try:
        resp = requests.get(url, timeout=10)
        print(f"  Status     : {resp.status_code}")
        print(f"  Server     : {resp.headers.get('server', 'not found')}")
        print(f"  CF-Ray     : {resp.headers.get('cf-ray', 'not found')}")
        print(f"  Body preview: {resp.text[:300]}")
        if "just a moment" in resp.text.lower():
            print("  >>> CLOUDFLARE JS CHALLENGE")
        elif resp.status_code == 403:
            print("  >>> 403 FORBIDDEN — hard block (Barracuda WAF)")
        elif "cf-ray" in str(resp.headers).lower():
            print("  >>> CLOUDFLARE headers present")
    except Exception as e:
        print(f"  ERROR: {e}")
    print()

    print("[TEST 2] With browser headers + referer...")
    try:
        resp = requests.get(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Referer":         "https://www.ndtvprofit.com/",
                "Accept-Language": "en-IN,en;q=0.9",
            },
            timeout=10
        )
        print(f"  Status     : {resp.status_code}")
        print(f"  CF-Ray     : {resp.headers.get('cf-ray', 'not found')}")
        print(f"  Body preview: {resp.text[:300]}")
        if resp.status_code == 200:
            soup  = BeautifulSoup(resp.text, "html.parser")
            paras = [p.get_text(strip=True) for p in soup.find_all("p")
                     if len(p.get_text(strip=True)) > 40]
            print(f"  Paragraphs found: {len(paras)}")
            if paras:
                print(f"  First para: {paras[0][:150]}")
    except Exception as e:
        print(f"  ERROR: {e}")
    print()

    print("[TEST 3] AMP version...")
    amp_url = re.sub(
        r"(https?://(?:www\.)?ndtvprofit\.com/)",
        r"\1amp/",
        url.split("#")[0]
    )
    print(f"  AMP URL: {amp_url}")
    try:
        resp = requests.get(
            amp_url,
            headers={"User-Agent": "Googlebot/2.1"},
            timeout=10
        )
        print(f"  Status     : {resp.status_code}")
        print(f"  CF-Ray     : {resp.headers.get('cf-ray', 'not found')}")
        print(f"  Body preview: {resp.text[:300]}")
        if resp.status_code == 200:
            soup  = BeautifulSoup(resp.text, "html.parser")
            paras = [p.get_text(strip=True) for p in soup.find_all("p")
                     if len(p.get_text(strip=True)) > 40]
            print(f"  Paragraphs found: {len(paras)}")
            if paras:
                print(f"  First para: {paras[0][:150]}")
                print("  >>> AMP WORKS")
    except Exception as e:
        print(f"  ERROR: {e}")
    print()

    print("[TEST 4] curl_cffi TLS impersonation...")
    try:
        resp = cf_requests.get(
            url.split("#")[0],
            impersonate="chrome124",
            timeout=15
        )
        print(f"  Status     : {resp.status_code}")
        print(f"  Body preview: {resp.text[:300]}")
        soup  = BeautifulSoup(resp.text, "html.parser")
        paras = [p.get_text(strip=True) for p in soup.find_all("p")
                 if len(p.get_text(strip=True)) > 40]
        print(f"  Paragraphs found: {len(paras)}")
        if paras:
            print(f"  First para: {paras[0][:150]}")
            print("  >>> curl_cffi WORKS")
    except ImportError:
        print("  curl_cffi not installed — run: pip install curl_cffi")
    except Exception as e:
        print(f"  ERROR: {e}")

    print()
    print("=" * 60)
    print("DIAGNOSIS COMPLETE")
    print("=" * 60)


# ─────────────────────────────────────────────────────────────
# MAIN FETCHER
# ─────────────────────────────────────────────────────────────

def fetch_zerodha(
    top_n: int = 50,
    scrape: bool = True,
    delay: float = 1.5,
) -> list:
    """
    Fetches ALL articles from Zerodha Pulse RSS feed and enriches
    each with full scraped content from the original source URL.

    Zerodha Pulse is a news aggregator. Links point to:
      - economictimes.indiatimes.com  → trafilatura (400-900 words)
      - thehindu.com                  → trafilatura (300-600 words)
      - livemint.com                  → trafilatura (300-700 words)
      - business-standard.com         → trafilatura (300-600 words)
      - ndtvprofit.com                → curl_cffi (TLS bypass, confirmed working)

    Args:
        top_n:  max articles to return (50 = fetch all ~25 entries)
        scrape: fetch full article from original source URL
        delay:  seconds between HTTP requests
    """
    print(f"[ZERODHA] Fetching Zerodha Pulse...")

    feed = feedparser.parse(ZERODHA_FEED_URL)
    print(f"[ZERODHA] {len(feed.entries)} raw entries")

    data        = []
    seen_titles = set()
    skipped     = 0

    for entry in feed.entries:
        if len(data) >= top_n:
            break

        title = entry.get("title", "").strip()
        if not title:
            continue

        title_lower = title.lower()
        if title_lower in seen_titles:
            skipped += 1
            continue
        seen_titles.add(title_lower)

        link     = entry.get("link", "").strip()
        pub_date = entry.get("published") or entry.get("updated") or ""

        # Extract RSS content — Zerodha embeds HTML snippets
        rss_content = ""
        if "content" in entry and entry["content"]:
            rss_content = entry["content"][0].get("value", "")
        if not rss_content:
            rss_content = entry.get("summary", "")

        # Strip HTML from RSS snippet
        if rss_content:
            rss_content = BeautifulSoup(
                rss_content, "html.parser"
            ).get_text(separator=" ", strip=True)

        # Scrape full article from original source
        if scrape and link:
            domain = get_domain(link)
            print(f"  [{domain}] {title[:55]}...")
            full_content = scrape_article(link, rss_content, title=title)
            time.sleep(delay)
        else:
            full_content = clean_content(rss_content, title=title)

        quality = assess_quality(full_content)
        domain  = get_domain(link)

        data.append({
            "Blog_Title":       title,
            "Blog_Links":       link,
            "Blog_PublishDate": pub_date,
            "Blog_Content":     full_content,
            "source_name":      f"Zerodha Pulse ({domain})",
            "source":           "zerodha_pulse",
            "_source_type":     "news",
            "_content_words":   quality["word_count"],
            "_content_quality": quality["quality"],
            "_origin_domain":   domain,
        })

    print(f"[ZERODHA] Skipped (dedup): {skipped} | Returned: {len(data)}")
    return data


# ─────────────────────────────────────────────────────────────
# TEST
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Uncomment to run diagnostic on a single NDTV URL
    # diagnose_ndtv()

    results = fetch_zerodha(top_n=50, scrape=True, delay=1.5)

    print(f"\nTotal: {len(results)}")
    print("=" * 60)

    for i, r in enumerate(results, 1):
        print(f"\n[{i}] Title   : {r['Blog_Title']}")
        print(f"    Link  : {r['Blog_Links']}")

        print(f"    Source  : {r['source_name']}")
        print(f"    Date    : {r['Blog_PublishDate']}")
        print(f"    Quality : {r['_content_quality']} ({r['_content_words']} words)")
        print(f"    Content : {r['Blog_Content']}")
        print(f"    ---")