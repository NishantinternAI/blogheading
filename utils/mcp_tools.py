"""
article_scraper_mcp.py
─────────────────────────────────────────────────────────────
FastMCP tool: fetch_article_content
Accepts a URL, scrapes the full article, cleans boilerplate,
and returns clean readable text for LLM consumption.

Scraper cascade: trafilatura → newspaper3k → requests+BeautifulSoup
Falls back gracefully when libraries are missing or site blocks scrapers.

Usage (stdio, drop into your existing MCP server or run standalone):
    python article_scraper_mcp.py

Dependencies:
    pip install "mcp[cli]" trafilatura newspaper3k requests beautifulsoup4 lxml
"""

from __future__ import annotations

import re
import time
from typing import Optional

import requests
from bs4 import BeautifulSoup
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field, ConfigDict

# ─────────────────────────────────────────────────────────────
# OPTIONAL DEPENDENCY GUARDS
# ─────────────────────────────────────────────────────────────

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
# CONSTANTS
# ─────────────────────────────────────────────────────────────

MIN_WORDS = 150          # minimum words to consider a scrape "successful"

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

# ── General boilerplate line patterns (case-insensitive match at line start) ──
BOILERPLATE_PATTERNS: list[str] = [
    r"^also read[:\s]",
    r"^read more[:\s]",
    r"^[\(\[]?disclaimer[:\s]",
    r"^follow us on",
    r"^subscribe (to|now|for)",
    r"^download.*app",
    r"^for (the )?entire discussion",
    r"^watch (the )?(accompanying|full|entire) video",
    r"^for (the )?latest.*news",
    r"^click here",
    r"^stay (updated|tuned)",
    r"^share this",
    r"^topics?[:\s]",
    r"^tags?[:\s]",
    r"^first published",
    r"^updated.*\d{4}",
    r"^catch (all |the )?latest",
    r"^check (out |the )?live",
    r"^get (the )?latest",
    r"^sign up",
    r"^newsletter",
    r"^advertisement$",
    r"^sponsored content",
    r"^related (articles?|stories?|news)",
    r"^recommended for you",
    r"^you may also like",
    r"^more from",
    r"^all rights reserved",
    r"^copyright \d{4}",
    r"^published by",
    r"^written by",          # byline duplicates
    r"^edited by",
    r"^\(with agency",
    r"^\(source:",
    r"^\d+\s+min\s+read",    # "3 min read"
    r"^share$",
    r"^print$",
    r"^comments?$",
    # NDTV Profit newsletter promo block
    r"^essential\s*business\s*intelligence",
    r"^essentialbusinessintelligence",
]

# Footer signals — once matched, everything below is dropped
FOOTER_RE = re.compile(
    r"^(disclaimer|\(?disclaimer"
    r"|follow us|subscribe|download.*app|first published"
    r"|updated.*\d{4}|catch.*latest|topics?:|tags?:"
    r"|share this|check.*live|all rights reserved"
    r"|copyright \d{4}|\(with agency|\(source:)",
    re.IGNORECASE,
)

# NOTE: "also read" and "read more" removed from FOOTER_RE
# They appear mid-article (NDTV, BS) and cause premature content cutoff
# Handled as inline removals in clean_content instead
# Short promo-style lines (CTA verbs, <80 chars)
PROMO_RE = re.compile(
    r"^(read|follow|subscribe|download|click|join|get|stay"
    r"|share|check|catch|sign up|register|visit)",
    re.IGNORECASE,
)


# ─────────────────────────────────────────────────────────────
# CONTENT CLEANING UTILITIES
# ─────────────────────────────────────────────────────────────

def _strip_footer(lines: list[str]) -> list[str]:
    """Drop everything from the first footer-signal line downward."""
    for i, line in enumerate(lines):
        if FOOTER_RE.match(line.strip()):
            return lines[:i]
    return lines


def _is_boilerplate(line: str) -> bool:
    s = line.strip()
    if not s:
        return False
    if any(re.match(p, s, re.IGNORECASE) for p in BOILERPLATE_PATTERNS):
        return True
    if len(s) < 80 and PROMO_RE.match(s):
        return True
    return False


def _is_section_subheading(line: str) -> bool:
    """
    Detect short subheadings that trafilatura/newspaper captures as orphan lines.

    Handles two forms:
    - Title-cased phrases with no terminal punctuation  ("Key Market Drivers")
    - Sentence-case short questions (≤10 words ending in ?)
      e.g. "Why have foreign investors been selling Indian equities?"
      These are Q&A section headers, not body sentences.
    """
    s = line.strip()
    if not s or len(s) > 80:
        return False

    words = s.split()

    # Short question-form subheadings (sentence-case, ≤10 words)
    if s.endswith("?") and 2 <= len(words) <= 10:
        return True

    # Longer questions are genuine body sentences — keep them
    if s.endswith("?"):
        return False

    # Drop other terminal punctuation (full sentences)
    if s[-1] in ".!:\"'":
        return False

    if not (2 <= len(words) <= 10):
        return False

    # Title-cased subheadings (≥75% words start uppercase)
    title_ratio = sum(1 for w in words if w and w[0].isupper()) / len(words)
    return title_ratio >= 0.75


def _dedup_paragraphs(text: str) -> str:
    """Remove duplicate paragraphs (60-char fingerprint)."""
    seen: list[str] = []
    result: list[str] = []
    for p in (p.strip() for p in text.split("\n\n") if p.strip()):
        fp = p[:60].lower()
        if fp not in seen:
            seen.append(fp)
            result.append(p)
    return "\n\n".join(result)


def _dedup_sentences(text: str) -> str:
    """Remove duplicate sentences and drop sub-4-word non-sentence fragments."""
    # Normalise single newlines to spaces so sentence splitter doesn't miss
    # boundaries like "...markets\nWhy have..." where \n isn't preceded by .?!
    text = re.sub(r"(?<![.!?])\n", " ", text)
    seen: list[str] = []
    result: list[str] = []
    for s in (s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()):
        if len(s.split()) < 4 and not s[-1:] in ".!?":
            continue
        fp = re.sub(r"\s+", " ", s[:80]).lower()
        if fp not in seen:
            seen.append(fp)
            result.append(s)
    return " ".join(result)


def clean_content(text: str, title: str = "") -> str:
    """
    Generic article cleaner:
    - Strips HTML remnants
    - Removes boilerplate / promo / footer lines
    - Optionally strips duplicate headline from top
    - Deduplicates paragraphs and sentences
    - Normalises whitespace
    """
    if not text:
        return ""

    # Strip NDTV inline newsletter promo (appears at end of last sentence)
    text = re.sub(
        r"Essential.{0,10}Business.{0,10}Intelligence.*",
        "",
        text,
        flags=re.IGNORECASE | re.DOTALL
    ).strip()

    # Strip date/timestamp lines at start
    # e.g. "Last Updated: 19th June 2026 - 09:45 am"
    text = re.sub(
        r"^(last updated|published|updated on|posted on)[^\n]{0,60}\n",
        "",
        text,
        flags=re.IGNORECASE
    )

    # Fix words running together from stripped hyperlinks
    # e.g. "theforeign exchange market" -> "the foreign exchange market"
    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)

    # Strip inline "ALSO READ: Headline" references
    text = re.sub(r"ALSO READ:[^\n]*", "", text, flags=re.IGNORECASE)

    # Strip "A post shared by X (@handle)" social embed captions
    text = re.sub(r"A post shared by[^\n]*", "", text, flags=re.IGNORECASE)

    # Strip 5paisa legal disclaimer block (inline at end of article)
    text = re.sub(
        r"Disclaimer\s*:?\s*Investment in securities.*",
        "",
        text,
        flags=re.IGNORECASE | re.DOTALL
    ).strip()

    # Strip 5paisa community CTA
    text = re.sub(
        r"Be a part of 5paisa community.*",
        "",
        text,
        flags=re.IGNORECASE | re.DOTALL
    ).strip()

    # Clean up extra spaces left behind
    text = re.sub(r"  +", " ", text)

    # Strip any leaked HTML
    if "<" in text and ">" in text:
        text = BeautifulSoup(text, "html.parser").get_text(
            separator=" ", strip=True
        )

    lines = text.splitlines()
    lines = _strip_footer(lines)

    cleaned: list[str] = []
    for line in lines:
        s = line.strip()
        if not s:
            continue
        if _is_section_subheading(s):
            continue
        if _is_boilerplate(s):
            continue
        cleaned.append(s)

    # Remove duplicate headline at top
    if title and cleaned:
        t_words = set(re.sub(r"[^\w\s]", "", title).lower().split())
        f_words = set(re.sub(r"[^\w\s]", "", cleaned[0]).lower().split())
        if t_words and len(cleaned[0]) < 160:
            overlap = len(t_words & f_words) / max(len(t_words), 1)
            if overlap >= 0.5:
                cleaned = cleaned[1:]

    joined = "\n".join(cleaned)
    joined = _dedup_paragraphs(joined)
    joined = _dedup_sentences(joined)
    return joined.strip()


# ─────────────────────────────────────────────────────────────
# SCRAPERS
# ─────────────────────────────────────────────────────────────

def _scrape_trafilatura(url: str) -> str:
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


def _scrape_newspaper(url: str) -> str:
    if not NEWSPAPER_AVAILABLE:
        return ""
    try:
        art = Article(url)
        art.download()
        art.parse()
        return art.text.strip()
    except Exception:
        return ""


def _scrape_requests(url: str) -> str:
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
                r"|content[_-]?body|storybody|article-detail"
                r"|entry[_-]?content|main[_-]?content",
                re.I,
            ))
            or soup.find("article")
            or soup.find("main")
        )
        paragraphs = (body or soup).find_all("p")
        return " ".join(
            p.get_text(strip=True)
            for p in paragraphs
            if len(p.get_text(strip=True)) > 40
        ).strip()
    except Exception:
        return ""


# ─────────────────────────────────────────────────────────────
# CURL_CFFI SCRAPER  (bypasses bot detection — best for NDTV etc)
# ─────────────────────────────────────────────────────────────

def _scrape_curl_cffi(url: str) -> str:
    if not CURL_CFFI_AVAILABLE:
        return ""
    try:
        from bs4 import BeautifulSoup
        resp = cf_requests.get(url, impersonate="chrome124", timeout=12)
        if resp.status_code != 200:
            return ""
        soup = BeautifulSoup(resp.text, "html.parser")

        # Remove non-content elements
        for tag in soup(["script", "style", "nav", "header",
                          "footer", "aside", "form", "iframe",
                          "noscript", "button", "input"]):
            tag.decompose()

        # Find article body
        body = (
            soup.find("div", class_=re.compile(
                r"article[_-]?body|story[_-]?content"
                r"|post[_-]?content|article[_-]?text"
                r"|content[_-]?body|storybody|article-detail"
                r"|entry[_-]?content|main[_-]?content",
                re.I,
            ))
            or soup.find("article")
            or soup.find("main")
        )
        # ── Extract content from body container ──────────────
        def extract_text(root_el, min_p_len=40):
            parts = []
            seen  = set()
            for el in root_el.find_all(["p", "li", "h2", "h3", "h4", "td"]):
                text = el.get_text(separator=" ", strip=True)
                if not text:
                    continue
                if el.name == "li" and len(text) < 15:
                    continue
                if el.name == "p" and len(text) < min_p_len:
                    continue
                fp = text[:80].lower()
                if fp in seen:
                    continue
                seen.add(fp)
                if el.name == "li":
                    parts.append(f"• {text}")
                elif el.name in ("h2", "h3", "h4"):
                    parts.append(f"\n{text}:")
                else:
                    parts.append(text)
            return " ".join(parts).strip()

        # Try narrow body container first
        result = extract_text(body) if body else ""

        # If too thin — fall back to full page scan
        # This handles sites where content spans multiple containers
        if len(result.split()) < 200:
            result = extract_text(soup, min_p_len=60)

        return result.strip()
    except Exception:
        return ""


# ─────────────────────────────────────────────────────────────
# CORE FUNCTION  (importable, testable independently)
# ─────────────────────────────────────────────────────────────

def fetch_and_clean(url: str, title: str = "",
                    fallback_text: str = "") -> dict:
    """
    Scrape a URL and return cleaned article content.

    Cascade:
      1. trafilatura
      2. newspaper3k
      3. requests + BeautifulSoup
      4. fallback_text  (RSS summary — always available from your pipeline)

    Pass the RSS summary as fallback_text so the server-side WAF block
    on CNBC never leaves the LLM with empty content.

    Returns:
        {
            "url":         str,
            "content":     str,   # cleaned article text
            "word_count":  int,
            "quality":     str,   # "rich" | "thin" | "bare" | "empty"
            "method":      str,   # which scraper succeeded
        }
    """
    scrapers = [
        ("curl_cffi",   _scrape_curl_cffi),    # bypasses bot detection (NDTV, ET etc)
        ("trafilatura", _scrape_trafilatura),
        ("newspaper",   _scrape_newspaper),
        ("requests",    _scrape_requests),
    ]

    best_content = ""
    best_method  = "none"

    for method, scraper in scrapers:
        raw     = scraper(url)
        cleaned = clean_content(raw, title=title)
        words   = len(cleaned.split()) if cleaned else 0
        if words >= MIN_WORDS:
            best_content = cleaned
            best_method  = method
            break
        # keep the longest result even if below threshold
        if words > len(best_content.split()):
            best_content = cleaned
            best_method  = method

    # ── RSS fallback ──────────────────────────────────────────
    # If all scrapers failed or returned thin content AND we have
    # an RSS summary, use that instead. This ensures the LLM always
    # gets something meaningful even when CNBC's WAF blocks the server.
    if len(best_content.split()) < MIN_WORDS and fallback_text:
        rss_cleaned = clean_content(fallback_text, title=title)
        if len(rss_cleaned.split()) > len(best_content.split()):
            best_content = rss_cleaned
            best_method  = "fallback_rss"

    word_count = len(best_content.split()) if best_content else 0
    quality    = (
        "rich"  if word_count >= 300 else
        "thin"  if word_count >= 150 else
        "bare"  if word_count >= 50  else
        "empty"
    )

    return {
        "url":        url,
        "content":    best_content,
        "word_count": word_count,
        "quality":    quality,
        "method":     best_method,
    }


# ─────────────────────────────────────────────────────────────
# MCP SERVER
# ─────────────────────────────────────────────────────────────

mcp = FastMCP("article_scraper_mcp")


class FetchArticleInput(BaseModel):
    """Input model for fetch_article_content."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid",
    )

    url: str = Field(
        ...,
        description=(
            "Fully-qualified article URL to scrape, e.g. "
            "'https://www.cnbctv18.com/market/some-article.html'"
        ),
        min_length=10,
        max_length=2048,
    )
    title: Optional[str] = Field(
        default="",
        description=(
            "Optional article headline. When provided, the cleaner strips "
            "duplicate headline text that sometimes appears at the top of "
            "the scraped body."
        ),
        max_length=300,
    )
    fallback_text: Optional[str] = Field(
        default="",
        description=(
            "RSS summary text to use if all scrapers fail or return < 150 words. "
            "Pass item['Blog_Content'] from your RSS fetch here. "
            "Ensures the LLM always gets something when the site blocks server IPs."
        ),
        max_length=5000,
    )


@mcp.tool(
    name="fetch_article_content",
    annotations={
        "title": "Fetch and Clean Article Content",
        "readOnlyHint":    True,
        "destructiveHint": False,
        "idempotentHint":  True,
        "openWorldHint":   True,
    },
)
async def fetch_article_content(params: FetchArticleInput) -> str:
    """
    Scrape a news article URL and return clean, boilerplate-free text.

    Tries three scraping methods in cascade order:
      1. trafilatura  (best structural extraction)
      2. newspaper3k  (good general fallback)
      3. requests + BeautifulSoup  (CSS-selector fallback)

    The cleaner removes ads, navigation, footer boilerplate, duplicate
    headlines, orphaned subheadings, promo lines, and duplicate sentences.

    Args:
        params (FetchArticleInput): Validated input containing:
            - url (str): Article URL to scrape (required)
            - title (str): Article headline for duplicate-title removal (optional)

    Returns:
        str: JSON with keys:
            - url         (str)  original URL
            - content     (str)  cleaned article text
            - word_count  (int)  number of words in cleaned content
            - quality     (str)  "rich" ≥300w | "thin" ≥150w | "bare" ≥50w | "empty"
            - method      (str)  scraper that produced the result
    """
    import json

    result = fetch_and_clean(url=params.url, title=params.title or "", fallback_text=params.fallback_text or "")
    return json.dumps(result, ensure_ascii=False, indent=2)


# ─────────────────────────────────────────────────────────────
# ENTRY POINT
# run as MCP server : python article_scraper_mcp.py --serve
# run test directly : python article_scraper_mcp.py [url]
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    if "--serve" in sys.argv:
        # HTTP transport — required for OpenAI Responses API MCP integration
        port = 8001
        for i, arg in enumerate(sys.argv):
            if arg == "--port" and i + 1 < len(sys.argv):
                port = int(sys.argv[i + 1])
        print(f"[MCP] article_scraper_mcp running on http://localhost:{port}/mcp")
        mcp.settings.port = port
        mcp.settings.host = "0.0.0.0"
        mcp.run(transport="streamable-http")

    else:
        # ── quick standalone test ──────────────────────────────
        import json

        def _get_live_test_url() -> str:
            """Pull the first article URL from CNBC TV18 RSS — always valid."""
            try:
                import feedparser
                feed = feedparser.parse(
                    "https://www.cnbctv18.com/commonfeeds/v1/cne/rss/economy.xml"
                )
                if feed.entries:
                    url = feed.entries[0].get("link", "")
                    print(f"  (auto-picked from RSS feed)")
                    return url
            except Exception:
                pass
            return ""

        if len(sys.argv) > 1:
            test_url = sys.argv[1]
        else:
            test_url = _get_live_test_url()

        if not test_url:
            print("No URL provided and RSS fetch failed. Pass a URL as argument:")
            print("  python article_scraper_mcp.py https://example.com/article")
            sys.exit(1)

        print(f"\n{'='*60}")
        print(f"  article_scraper_mcp — standalone test")
        print(f"{'='*60}")
        print(f"  URL : {test_url}\n")

        result = fetch_and_clean(test_url)

        print(f"  Method     : {result['method']}")
        print(f"  Quality    : {result['quality']}  ({result['word_count']} words)")
        print(f"{'='*60}\n")
        print(result["content"] if result["content"] else "⚠  No content extracted.")
        print(f"\n{'='*60}")
        print("  Full JSON output:")
        print('='*60)
        print(json.dumps({**result, "content": result["content"][:300] + "..."
                          if len(result["content"]) > 300 else result["content"]},
                         indent=2, ensure_ascii=False))