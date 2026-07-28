# import urllib.request
# import re


# def fetch_google_trends():
#     url = "https://trends.google.co.in/trending/rss?geo=IN"

#     try:
#         req  = urllib.request.Request(url, headers={
#             "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
#                           "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
#             "Accept":     "application/rss+xml, application/xml, */*",
#         })
#         resp = urllib.request.urlopen(req, timeout=15)
#         xml  = resp.read().decode("utf-8")
#     except Exception as e:
#         print(f"[TRENDS] Fetch error: {e}")
#         return []

#     data = []

#     # ── Split into individual <item> blocks ───────────────────
#     items = re.findall(r'<item>(.*?)</item>', xml, re.DOTALL)
#     print(f"[TRENDS] Raw items found: {len(items)}")

#     for item_xml in items:

#         # Title
#         title_match = re.search(r'<title>(.*?)</title>', item_xml, re.DOTALL)
#         title = title_match.group(1).strip() if title_match else ""

#         # PubDate
#         pub_match = re.search(r'<pubDate>(.*?)</pubDate>', item_xml, re.DOTALL)
#         published = pub_match.group(1).strip() if pub_match else ""

#         # Traffic
#         traffic_match = re.search(r'<ht:approx_traffic>(.*?)</ht:approx_traffic>', item_xml, re.DOTALL)
#         traffic = traffic_match.group(1).strip() if traffic_match else ""

#         # First news item URL
#         url_match = re.search(r'<ht:news_item_url>(.*?)</ht:news_item_url>', item_xml, re.DOTALL)
#         first_url = url_match.group(1).strip() if url_match else ""

#         # All news item titles + sources for Blog_Content
#         news_titles  = re.findall(r'<ht:news_item_title>(.*?)</ht:news_item_title>',  item_xml, re.DOTALL)
#         news_sources = re.findall(r'<ht:news_item_source>(.*?)</ht:news_item_source>', item_xml, re.DOTALL)
#         news_urls    = re.findall(r'<ht:news_item_url>(.*?)</ht:news_item_url>',       item_xml, re.DOTALL)

#         content_parts = []
#         for i, nt in enumerate(news_titles):
#             part = nt.strip()
#             if i < len(news_sources):
#                 part += f" ({news_sources[i].strip()})"
#             if i < len(news_urls):
#                 part += f"\n{news_urls[i].strip()}"
#             content_parts.append(part)

#         blog_content = "\n\n".join(content_parts)

#         data.append({
#             "Blog_Title":       title,
#             "Blog_Links":       first_url,
#             "Blog_PublishDate": published,
#             "Blog_Content":     blog_content,
#             "traffic":          traffic,
#         })

#         print(f"[TRENDS] + '{title[:50]}' | traffic={traffic} | url={first_url[:40] if first_url else 'MISSING'}")

#     print(f"[TRENDS] Fetched: {len(data)} articles")
#     return data


# if __name__ == "__main__":
#     results = fetch_google_trends()
#     print(f"\nTotal: {len(results)}")
#     print("=" * 60)
#     for r in results:
#         print(f"Title   : {r['Blog_Title']}")
#         print(f"Link    : {r['Blog_Links']}")
#         print(f"Traffic : {r['traffic']}")
#         print(f"Date    : {r['Blog_PublishDate']}")
#         print(f"Content : {r['Blog_Content'][:120]}")
#         print(f"---")

import json
import os
import re
import tempfile
import urllib.request
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

from core.model_client import fetch_article_via_headline_search
from sources.common import assess_quality
from utils.date_filter import _parse_date

MAX_CANDIDATE_AGE_DAYS = 1


# ── Try importing trafilatura ─────────────────────────────────
try:
    import trafilatura
    TRAFILATURA_AVAILABLE = True
    print("[TRENDS] trafilatura available ✅")
except ImportError:
    TRAFILATURA_AVAILABLE = False
    print("[TRENDS] trafilatura not installed — using headlines only")


# ══════════════════════════════════════════════════════════════
#  TITLE RESOLVER
# ══════════════════════════════════════════════════════════════

def _get_best_news_title(news_titles: list) -> str:
    """
    Picks the best news_item_title as fallback.
    Prefers English titles over regional language titles.
    """
    if not news_titles:
        return ""

    for nt in news_titles:
        nt = nt.strip()
        ascii_ratio = sum(1 for c in nt if ord(c) < 128) / max(len(nt), 1)
        if ascii_ratio > 0.7 and len(nt) > 10:
            return nt

    return news_titles[0].strip() if news_titles else ""


def _resolve_title(title: str, news_titles: list) -> str:
    """
    Returns the best available title.

    Cases where <title> is bad and we fallback to news_item_title:
      - Empty string
      - Just a number: "1", "2"
      - Very short: 1-2 chars
      - Date only: "३ जून", "3 June"
      - Pure regional script with no finance meaning
    """
    title = title.strip()

    # Bad 1 — empty
    if not title:
        return _get_best_news_title(news_titles)

    # Bad 2 — just a number
    if title.isdigit():
        return _get_best_news_title(news_titles)

    # Bad 3 — very short
    if len(title) <= 2:
        return _get_best_news_title(news_titles)

    # Bad 4 — date or pure regional script
    date_patterns = [
        r'^\d{1,2}\s+\w+$',           # "3 June"
        r'^\d{1,2}[/-]\d{1,2}$',      # "3/6"
        r'^[\u0900-\u097F\s\d]+$',     # Hindi only
        r'^[\u0B80-\u0BFF\s]+$',       # Tamil only
        r'^[\u0C00-\u0C7F\s]+$',       # Telugu only
        r'^[\u0980-\u09FF\s]+$',       # Bengali only
        r'^[\u0A80-\u0AFF\s]+$',       # Gujarati only
    ]
    for pattern in date_patterns:
        if re.match(pattern, title):
            fallback = _get_best_news_title(news_titles)
            print(f"[TITLE] Bad title '{title[:20]}' → fallback '{fallback[:50]}'")
            return fallback

    return title


# ══════════════════════════════════════════════════════════════
#  CONTENT SCRAPER — trafilatura
# ══════════════════════════════════════════════════════════════

def _scrape_with_trafilatura(url: str, max_chars: int = 800) -> str:
    """
    Fetches and extracts clean article text from any URL.
    Returns empty string if scraping fails.
    """
    if not url or not TRAFILATURA_AVAILABLE:
        return ""

    try:
        downloaded = trafilatura.fetch_url(url)

        if not downloaded:
            print(f"[SCRAPE] Download failed: {url[:60]}")
            return ""

        content = trafilatura.extract(
            downloaded,
            include_comments = False,
            include_tables   = False,
            no_fallback      = False,
            favor_precision  = True,
        )

        if not content:
            print(f"[SCRAPE] No content: {url[:60]}")
            return ""

        content = re.sub(r'\s+', ' ', content).strip()
        print(f"[SCRAPE] ✅ {len(content)} chars from {url[:60]}")
        return content[:max_chars]

    except Exception as e:
        print(f"[SCRAPE] Failed ({url[:50]}): {e}")
        return ""


# ══════════════════════════════════════════════════════════════
#  SCRAPE ALL 3 NEWS URLS
# ══════════════════════════════════════════════════════════════

def _scrape_all_news_urls(news_urls: list, trend_title: str,
                           max_chars_each: int = 800,
                           min_chars_needed: int = 400) -> str:
    """
    Tries URLs in order 1 → 2 → 3.
    Stops as soon as enough content is collected.
    Only moves to next URL if current one fails or is too short.

    Strategy:
      URL 1 works and has 800 chars → STOP, use URL 1 only
      URL 1 fails → try URL 2
      URL 1 + URL 2 both fail → try URL 3
      URL 1 gives 200 chars (too short) → also try URL 2
    """
    if not news_urls:
        return ""

    combined_parts  = []
    total_chars     = 0
    success_count   = 0

    for i, url in enumerate(news_urls, 1):
        url = url.strip()
        if not url:
            continue

        print(f"[SCRAPE] Trying URL {i}/{len(news_urls)}: {url[:60]}")
        content = _scrape_with_trafilatura(url, max_chars=max_chars_each)

        if _is_content_valid(content, trend_title):
            combined_parts.append(
                f"--- Source {i} ({url}) ---\n{content}"
            )
            total_chars   += len(content)
            success_count += 1
            print(f"[SCRAPE] URL {i} ✅ — total so far: {total_chars} chars")

            # ── Stop if we have enough content ────────────────
            if total_chars >= min_chars_needed:
                print(f"[SCRAPE] Enough content ({total_chars} chars) "
                      f"— skipping remaining URLs")
                break   # ← STOP HERE, don't scrape URL 2 or 3

        else:
            print(f"[SCRAPE] URL {i} failed — trying next")

    if not combined_parts:
        return ""

    print(f"[SCRAPE] Done: {success_count} URLs used, {total_chars} chars total")
    return "\n\n".join(combined_parts)

# ══════════════════════════════════════════════════════════════
#  CONTENT VALIDATOR
# ══════════════════════════════════════════════════════════════

def _is_content_valid(content: str, trend_title: str) -> bool:
    """
    Validates scraped content is relevant and useful.
    Rejects paywalls, error pages, and unrelated content.
    """
    if not content or len(content) < 100:
        return False

    error_signals = [
        "sign in to continue", "subscribe to read",
        "create your account", "access denied",
        "page not found", "enable javascript",
        "please log in", "premium content",
        "cookie policy", "we use cookies",
    ]
    content_lower = content.lower()
    for signal in error_signals:
        if signal in content_lower:
            print(f"[VALIDATE] ❌ Blocked: '{signal}'")
            return False

    # Check at least one word from trend title appears in content
    title_words = [w.lower() for w in trend_title.split() if len(w) > 3]
    if title_words:
        matches = sum(1 for w in title_words if w in content_lower)
        if matches == 0:
            print(f"[VALIDATE] ❌ Not related to '{trend_title[:30]}'")
            return False

    return True


def _search_google_news_for_trend(phrase: str) -> list:
    """
    Searches Google News RSS for real articles matching a trending phrase
    -- free, no AI cost. Returns a list of candidate dicts
    {"title", "link", "pub_date", "source"}, most-recent-first (Google
    News RSS's own default ordering). Returns [] on any network failure
    (caught, logged, not raised) -- callers treat that as "nothing found
    for this trend", not a hard error.
    """
    url = f"https://news.google.com/rss/search?q={quote(phrase)}&hl=en-IN&gl=IN&ceid=IN:en"
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
            "Accept":     "application/rss+xml, application/xml, */*",
        })
        resp = urllib.request.urlopen(req, timeout=15)
        xml = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"[BIZ TRENDS] Google News search failed for '{phrase}': {e}")
        return []

    candidates = []
    for item_xml in re.findall(r"<item>(.*?)</item>", xml, re.DOTALL):
        title_match = re.search(r"<title>(.*?)</title>", item_xml, re.DOTALL)
        link_match = re.search(r"<link>(.*?)</link>", item_xml, re.DOTALL)
        pub_match = re.search(r"<pubDate>(.*?)</pubDate>", item_xml, re.DOTALL)
        source_match = re.search(r"<source[^>]*>(.*?)</source>", item_xml, re.DOTALL)

        if not title_match or not link_match:
            continue

        candidates.append({
            "title":    title_match.group(1).strip(),
            "link":     link_match.group(1).strip(),
            "pub_date": pub_match.group(1).strip() if pub_match else "",
            "source":   source_match.group(1).strip() if source_match else "",
        })

    return candidates


def _is_recent(pub_date: str) -> bool:
    """
    True if pub_date parses to within the last MAX_CANDIDATE_AGE_DAYS
    days, or if it can't be parsed at all (Google News RSS dates are
    reliably formatted in practice, so an unparseable string is treated
    as an upstream format quirk, not evidence of staleness).
    """
    if not pub_date:
        return True

    pub_dt = _parse_date(pub_date)
    if pub_dt is None:
        return True

    return datetime.now(timezone.utc) - pub_dt <= timedelta(days=MAX_CANDIDATE_AGE_DAYS)


def _pick_best_candidate(phrase: str, candidates: list) -> dict | None:
    """
    Title-level prefilter (no AI call) -- keeps only candidates whose
    title shares at least one word (len > 3, case-insensitive) with the
    trend phrase, same shape as _is_content_valid()'s title-overlap
    check, AND whose pub_date is within MAX_CANDIDATE_AGE_DAYS days.
    Google News RSS search can surface old articles that happen to
    resurface (e.g. reposted/re-indexed) well after their real event
    date. Trending-search spikes are same-day-or-yesterday phenomena, so
    a 1-day cutoff is deliberately tight -- without this check a trend
    like "NSE market closed today"
    can get grounded in a month-old holiday-calendar article and
    published as if it were current (2026-07-28 incident: a 25 Jun
    Muharram holiday piece got published under a "today" headline).
    Returns the first surviving candidate (Google News RSS already
    orders by relevance/recency), or None if nothing qualifies.
    """
    phrase_words = [w.lower() for w in phrase.split() if len(w) > 3]

    for candidate in candidates:
        if not _is_recent(candidate.get("pub_date", "")):
            continue
        title_lower = candidate.get("title", "").lower()
        if not phrase_words or any(w in title_lower for w in phrase_words):
            return candidate

    return None


def ground_trend_in_news(trend: dict) -> dict | None:
    """
    Grounds one trending phrase (from get_cached_business_trends()) in a
    real, verified news article. Returns an article dict shaped like
    every other source's output, or None if real news can't be verified
    at ANY step -- this is the hard gate against generating a blog from a
    bare search-volume spike with no real facts behind it (see the
    2026-07-24 hallucinated-blog incident in docs/review.md). Uses
    fetch_article_via_headline_search() rather than fetching the Google
    News candidate's URL directly, since that URL is an opaque
    client-side-redirect token neither a plain fetch nor the web_search
    tool can resolve (verified 2026-07-27) -- Blog_Links still stores it
    for reference even though it's never dereferenced.
    """
    phrase = trend["title"]

    candidates = _search_google_news_for_trend(phrase)
    if not candidates:
        print(f"[BIZ TRENDS] No Google News candidates for '{phrase}' -- skipping")
        return None

    best = _pick_best_candidate(phrase, candidates)
    if not best:
        print(f"[BIZ TRENDS] No title-relevant candidate for '{phrase}' -- skipping")
        return None

    content = fetch_article_via_headline_search(best["title"], best.get("source", ""))
    if not content:
        print(f"[BIZ TRENDS] No content found for '{phrase}' (headline: '{best['title']}') -- skipping")
        return None

    if not _is_content_valid(content, phrase):
        print(f"[BIZ TRENDS] Content failed validity check for '{phrase}' -- skipping")
        return None

    quality = assess_quality(content)
    if quality["quality"] in ("empty", "bare"):
        print(f"[BIZ TRENDS] Content too thin for '{phrase}' ({quality['word_count']} words) -- skipping")
        return None

    return {
        "Blog_Title":      best["title"],
        "Blog_Content":    content,
        "Blog_Links":      best["link"],
        "Blog_PublishDate": best["pub_date"],
        "trending_signal": f"{phrase} ({trend['volume']:,} searches, +{trend['growth_pct']}%)",
    }


def fetch_trending_business_articles(max_trends: int = 5) -> list:
    """
    Fetcher plugged into core/pipeline.py's _fetch_all_sources(). Takes
    the top `max_trends` cached Business & Finance trends (by volume,
    already sorted by get_cached_business_trends()) and grounds each in
    real news via ground_trend_in_news(). Each trend is wrapped in its
    own try/except so one trend's failure never drops the others in the
    batch. Returns 0-max_trends article dicts.
    """
    trends = get_cached_business_trends()[:max_trends]

    articles = []
    for trend in trends:
        try:
            article = ground_trend_in_news(trend)
        except Exception as e:
            print(f"[BIZ TRENDS] Error grounding '{trend.get('title', '?')}': {e}")
            continue
        if article:
            articles.append(article)

    print(f"[BIZ TRENDS] Grounded {len(articles)}/{len(trends)} trends into real articles")
    return articles


# ══════════════════════════════════════════════════════════════
#  DAILY TRENDS RSS ENRICHMENT
#
# Google's official Daily Search Trends feed (different endpoint from
# the "Trending Now" scrape above) embeds each trend's own pre-matched
# <ht:news_item> elements -- real, directly resolvable article URLs
# (not the Google News redirect tokens _search_google_news_for_trend()
# has to route around via an AI headline search), already relevance-
# matched by Google's own trends engine rather than our title-overlap
# heuristic. Only 10 items/day and, like the main scrape, ignores its
# own geo/category/hours query params server-side (confirmed
# empirically 2026-07-28) -- it mixes non-finance trends (cricket
# scores, regional news) in with finance ones, so results are
# cross-referenced against get_cached_business_trends() (the same
# category-3-tagged list fetch_trending_business_articles() ranks by
# volume) to keep only trends Google itself already tagged Business &
# Finance. This is a narrow supplement, not a replacement: on
# 2026-07-28 none of that day's top-5-by-volume trends appeared in
# this feed, but 7 of the ~52 tagged trends did (e.g. "hul share
# price", "bel share", "tcs share") -- topics the volume-ranked path
# alone would never reach.
# ══════════════════════════════════════════════════════════════

DAILY_TRENDS_RSS_URL = "https://trends.google.com/trending/rss?geo=IN"
_RSS_NS = {"ht": "https://trends.google.com/trending/rss"}


def _fetch_daily_trends_rss() -> list:
    """
    Fetches Google's Daily Search Trends RSS feed via a single plain GET
    and returns one dict per trend: {"title", "news_urls"} -- news_urls
    is the list of real article URLs from that trend's <ht:news_item>
    elements, in Google's own relevance order. Returns [] on any
    network/parse failure (caught, logged, not raised), same
    best-effort contract as _search_google_news_for_trend().
    """
    import xml.etree.ElementTree as ET

    req = urllib.request.Request(DAILY_TRENDS_RSS_URL, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        "Accept":     "application/rss+xml, application/xml, */*",
    })
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        xml_bytes = resp.read()
    except Exception as e:
        print(f"[DAILY RSS] Fetch failed: {e}")
        return []

    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as e:
        print(f"[DAILY RSS] Parse failed: {e}")
        return []

    items = []
    for item_el in root.findall("./channel/item"):
        title_el = item_el.find("title")
        title = (title_el.text or "").strip() if title_el is not None else ""
        if not title:
            continue

        news_urls = []
        for news_item_el in item_el.findall("ht:news_item", _RSS_NS):
            url_el = news_item_el.find("ht:news_item_url", _RSS_NS)
            if url_el is not None and url_el.text:
                news_urls.append(url_el.text.strip())

        items.append({"title": title, "news_urls": news_urls})

    return items


def ground_daily_rss_trend(item: dict) -> dict | None:
    """
    Grounds one Daily Trends RSS item using its own Google-curated
    news_urls -- fetched directly via _scrape_all_news_urls() (real
    URLs, no AI headline-search call needed), same quality bar as
    ground_trend_in_news(). Returns None if there are no news_urls, or
    scraping/quality checks fail at any step. No Blog_PublishDate is
    available from this feed (news_item elements carry no per-article
    date) -- utils/date_filter.py's is_fresh() already treats a missing
    date as "allow" for every source, so this relies on that existing
    behavior rather than needing a BYPASS_SOURCES entry of its own.
    """
    title = item["title"]
    news_urls = item.get("news_urls", [])
    if not news_urls:
        print(f"[DAILY RSS] No news_item URLs for '{title}' -- skipping")
        return None

    raw_content = _scrape_all_news_urls(news_urls, title, max_chars_each=2000, min_chars_needed=1000)
    if not raw_content:
        print(f"[DAILY RSS] No scrapeable content for '{title}' -- skipping")
        return None

    # _scrape_all_news_urls() prefixes each source's text with a
    # "--- Source N (url) ---" marker -- pull the actually-used URL(s)
    # out of that (news_urls[0] can be a URL that failed and got
    # skipped in favor of a later one) and strip the markers so they
    # don't leak into the blog prompt as literal text.
    used_urls = re.findall(r"--- Source \d+ \((.*?)\) ---", raw_content)
    content = re.sub(r"--- Source \d+ \(.*?\) ---\n?", "", raw_content).strip()

    quality = assess_quality(content)
    if quality["quality"] in ("empty", "bare"):
        print(f"[DAILY RSS] Content too thin for '{title}' ({quality['word_count']} words) -- skipping")
        return None

    return {
        "Blog_Title":      title,
        "Blog_Content":    content,
        "Blog_Links":      used_urls[0] if used_urls else news_urls[0],
        "Blog_PublishDate": "",
        "trending_signal": f"{title} (daily trends RSS)",
    }


_FINANCE_KEYWORDS = {
    "share", "shares", "stock", "stocks", "price", "prices", "ipo", "gmp",
    "bank", "banks", "banking", "nifty", "sensex", "rupee", "index", "ltd",
    "limited", "dividend", "profit", "profits", "revenue", "results",
    "earnings", "market", "markets", "trading", "invest", "investment",
    "investor", "investors", "crore", "lakh", "listing", "allotment",
    "mutual", "fund", "funds", "gold", "rate", "rates", "loan", "loans",
    "emi", "insurance", "premium", "subsidy", "tax", "itr", "rbi", "sebi",
    "nse", "bse", "gst", "petrol", "diesel", "lpg", "cylinder", "sip",
    "portfolio", "capital", "equity", "bond", "bonds", "cpi", "gdp",
}


def _is_finance_related(title: str, related_queries: list) -> bool:
    """
    Cheap language-agnostic-enough finance filter -- Google tags this
    feed's items with the same category-3 label used elsewhere in this
    module, but that tagging is unreliable (e.g. a Chennai power-outage
    story showed up tagged Business & Finance on 2026-07-28). Unlike
    fetch_trending_business_articles(), which is implicitly guarded by
    only grounding the top 5 by search volume, this daily-feed path has
    no volume filter, so a mistagged trend here reaches grounding (and,
    since publishing is live with no draft review, the site) far more
    easily. Checked empirically: every genuine finance trend in a
    52-trend sample (e.g. "hul share price", "bel share", "tcs share")
    carries an English finance term in its own title/related_queries,
    even when other fields are in a vernacular script -- so this is a
    pre-scrape filter (cheaper than scraping first and filtering after).
    """
    text = (title + " " + " ".join(related_queries)).lower()
    words = re.findall(r"[a-z0-9]+", text)
    return any(w in _FINANCE_KEYWORDS for w in words)


def fetch_trending_daily_rss_articles() -> list:
    """
    Fetcher plugged into core/pipeline.py's _fetch_all_sources(). Pulls
    the 10-item Daily Trends RSS feed, keeps only items whose title also
    appears in get_cached_business_trends() (i.e. Google itself already
    tagged it Business & Finance) AND pass _is_finance_related() (a
    second, keyword-based check -- Google's own category tagging isn't
    reliable enough to trust alone here, see that function's docstring),
    and grounds each via ground_daily_rss_trend(). Each item is wrapped
    in its own try/except so one item's failure never drops the rest of
    the batch. Returns 0-10 article dicts.
    """
    daily_items = _fetch_daily_trends_rss()
    if not daily_items:
        return []

    biz_by_title = {t["title"].strip().lower(): t for t in get_cached_business_trends()}
    relevant = []
    for item in daily_items:
        biz_trend = biz_by_title.get(item["title"].strip().lower())
        if not biz_trend:
            continue
        if not _is_finance_related(item["title"], biz_trend.get("related_queries", [])):
            print(f"[DAILY RSS] '{item['title']}' tagged Business & Finance but no finance "
                  f"keyword found -- skipping (likely Google mistag)")
            continue
        relevant.append(item)

    articles = []
    for item in relevant:
        try:
            article = ground_daily_rss_trend(item)
        except Exception as e:
            print(f"[DAILY RSS] Error grounding '{item.get('title', '?')}': {e}")
            continue
        if article:
            articles.append(article)

    print(f"[DAILY RSS] {len(daily_items)} daily trends, {len(relevant)} finance-relevant, "
          f"{len(articles)} grounded into real articles")
    return articles


# ══════════════════════════════════════════════════════════════
#  MAIN FETCHER
# ══════════════════════════════════════════════════════════════

def fetch_google_trends():
    url = "https://trends.google.co.in/trending/rss?geo=IN"

    # ── Fetch raw XML ─────────────────────────────────────────
    try:
        req  = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
            "Accept":     "application/rss+xml, application/xml, */*",
        })
        resp = urllib.request.urlopen(req, timeout=15)
        xml  = resp.read().decode("utf-8")
    except Exception as e:
        print(f"[TRENDS] Fetch error: {e}")
        return []

    # ── Split into individual <item> blocks ───────────────────
    items = re.findall(r'<item>(.*?)</item>', xml, re.DOTALL)
    print(f"[TRENDS] Raw items found: {len(items)}")

    data        = []
    seen_titles = set()

    for item_xml in items:

        # ── Extract raw fields from XML ───────────────────────
        title_match = re.search(r'<title>(.*?)</title>', item_xml, re.DOTALL)
        raw_title   = title_match.group(1).strip() if title_match else ""

        pub_match = re.search(r'<pubDate>(.*?)</pubDate>', item_xml, re.DOTALL)
        published = pub_match.group(1).strip() if pub_match else ""

        traffic_match = re.search(
            r'<ht:approx_traffic>(.*?)</ht:approx_traffic>',
            item_xml, re.DOTALL
        )
        traffic = traffic_match.group(1).strip() if traffic_match else ""

        # All 3 news items
        news_titles  = re.findall(
            r'<ht:news_item_title>(.*?)</ht:news_item_title>',
            item_xml, re.DOTALL
        )
        news_sources = re.findall(
            r'<ht:news_item_source>(.*?)</ht:news_item_source>',
            item_xml, re.DOTALL
        )
        news_urls = re.findall(
            r'<ht:news_item_url>(.*?)</ht:news_item_url>',
            item_xml, re.DOTALL
        )

        news_titles  = [t.strip() for t in news_titles]
        news_sources = [s.strip() for s in news_sources]
        news_urls    = [u.strip() for u in news_urls]

        # ── Resolve best title ────────────────────────────────
        # Falls back to news_item_title if <title> is bad
        title = _resolve_title(raw_title, news_titles)

        if not title:
            print(f"[TRENDS] Skipped — no usable title")
            continue

        # ── Dedup ─────────────────────────────────────────────
        title_norm = re.sub(r'\s+', ' ', title.lower().strip())
        if title_norm in seen_titles:
            print(f"[TRENDS] Duplicate skipped: '{title[:40]}'")
            continue
        seen_titles.add(title_norm)

        first_url = news_urls[0] if news_urls else ""

        # ── Scrape all 3 news URLs ────────────────────────────
        print(f"\n[TRENDS] Processing: '{title[:50]}'")
        scraped_content = _scrape_all_news_urls(
            news_urls,
            trend_title    = title,
            max_chars_each = 800
        )

        # ── Build headlines block ─────────────────────────────
        headlines_block = ""
        for i, nt in enumerate(news_titles):
            source = news_sources[i] if i < len(news_sources) else ""
            nurl   = news_urls[i]    if i < len(news_urls)    else ""
            headlines_block += f"[{i+1}] {nt} ({source})\n"
            if nurl:
                headlines_block += f"     {nurl}\n"

        # ── Build Blog_Content ────────────────────────────────
        blog_content = f"""Trending in India: {title}
Search Volume  : {traffic} searches today
Published      : {published}

Related News Headlines:
{headlines_block}"""

        if scraped_content:
            src_count    = scraped_content.count("--- Source")
            blog_content += f"""
Full Article Content ({src_count} sources scraped):
{scraped_content}"""

        blog_content = blog_content.strip()

        data.append({
            "Blog_Title":       title,
            "Blog_Links":       first_url,
            "Blog_PublishDate": published,
            "Blog_Content":     blog_content,
            "traffic":          traffic,
        })

        src_info = f"scraped {len(scraped_content)} chars" \
                   if scraped_content else "headlines only"
        print(f"[TRENDS] ✅ '{title[:40]}' | {src_info} | traffic={traffic}")

    print(f"\n[TRENDS] Fetched: {len(data)} articles")
    return data


# ══════════════════════════════════════════════════════════════
#  BUSINESS-CATEGORY TRENDING TOPICS (cached, low-frequency fetch)
# ══════════════════════════════════════════════════════════════
#
# The "Trending Now" page (trends.google.com/trending) is a JS app with no
# documented public API, but it embeds its full initial dataset server-side
# via Google's standard AF_initDataCallback mechanism -- a plain HTTPS GET
# with a browser User-Agent returns it directly, no headless browser or JS
# execution needed. The category/sort query params turned out to be
# cosmetic (applied client-side only): the embedded payload always
# contains ALL ~289 India trends across every category, each tagged with
# its own category-code list, so we filter to category 3 (Business &
# Finance -- confirmed empirically: "indo mim ipo gmp today" and similar
# known finance queries all carry category_ids == [3]) ourselves.
#
# Fetched at most once per BUSINESS_TRENDS_CACHE_HOURS via a JSON cache
# file -- deliberately infrequent (2h, not every 8-min pipeline cycle) to
# avoid hammering Google with an unauthenticated scrape from one server IP.

BUSINESS_TRENDS_URL = "https://trends.google.com/trending?geo=IN&sort=search-volume&category=3"
BUSINESS_TRENDS_CATEGORY_ID = 3
BUSINESS_TRENDS_CACHE_HOURS = 2
BUSINESS_TRENDS_CACHE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "output", "google_trends_business_cache.json",
)


def _extract_trends_payload(html: str) -> list:
    """
    Finds the AF_initDataCallback block carrying the trends dataset (the
    page has several such blocks for unrelated app state) and returns its
    parsed `data[1]` array -- one entry per trending query, each shaped
    like:
        [title, None, geo, [started_unix, ...], None, None,
         volume, None, growth_pct, [related_queries...],
         [category_ids...], [[story_id, lang, geo], ...], normalized_title]
    Returns [] if no matching block is found or parsing fails (e.g. Google
    changes the page structure) -- callers treat that as "no data" rather
    than raising, since this is a best-effort scrape, not an API contract.
    """
    for block in re.findall(r"AF_initDataCallback\((\{.*?\})\);", html, re.DOTALL):
        m = re.search(r"data:(\[.*\]), sideChannel", block, re.DOTALL)
        if not m:
            continue
        try:
            parsed = json.loads(m.group(1))
        except (json.JSONDecodeError, ValueError):
            continue
        if (
            isinstance(parsed, list) and len(parsed) == 2
            and isinstance(parsed[1], list) and len(parsed[1]) > 50
            and isinstance(parsed[1][0], list)
        ):
            return parsed[1]
    return []


def _parse_trend_record(record: list) -> dict:
    """Maps one raw AF_initDataCallback trend record into a plain dict."""
    return {
        "title":           record[0],
        "volume":          record[6],
        "growth_pct":      record[8],
        "started_unix":    (record[3] or [None])[0],
        "related_queries": record[9] or [],
        "category_ids":    record[10] or [],
    }


def fetch_business_trends() -> list:
    """
    Fetches the current India "Trending Now" dataset via a single plain
    GET (see module docstring above for why no browser is needed) and
    returns only the Business & Finance-tagged entries, sorted by volume
    descending. Returns [] on any network/parsing failure -- callers
    should treat this as "nothing new right now", not a hard error.
    """
    req = urllib.request.Request(
        BUSINESS_TRENDS_URL,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
            "Accept":     "text/html,application/xhtml+xml",
        },
    )
    try:
        resp = urllib.request.urlopen(req, timeout=20)
        html = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"[BIZ TRENDS] Fetch error: {e}")
        return []

    records = _extract_trends_payload(html)
    if not records:
        print("[BIZ TRENDS] Could not locate trends payload in page (structure may have changed)")
        return []

    business = [
        _parse_trend_record(r) for r in records
        if r and len(r) > 10 and r[10] and BUSINESS_TRENDS_CATEGORY_ID in r[10]
    ]
    business.sort(key=lambda t: t["volume"] or 0, reverse=True)
    print(f"[BIZ TRENDS] Fetched {len(records)} total trends, {len(business)} tagged Business & Finance")
    return business


def get_cached_business_trends(force_refresh: bool = False) -> list:
    """
    Returns Business & Finance trending queries, re-fetching at most once
    every BUSINESS_TRENDS_CACHE_HOURS hours to keep our request volume to
    Google low. Falls back to a stale cache (rather than an empty list)
    if a refresh attempt fails, so a single transient failure doesn't
    blank out an otherwise-working feed.
    """
    cache = {}
    if os.path.exists(BUSINESS_TRENDS_CACHE_PATH):
        try:
            with open(BUSINESS_TRENDS_CACHE_PATH, "r", encoding="utf-8") as f:
                cache = json.load(f)
        except (json.JSONDecodeError, OSError):
            cache = {}

    fetched_at = cache.get("fetched_at")
    is_stale = True
    if fetched_at and not force_refresh:
        age_hours = (
            datetime.now(timezone.utc) - datetime.fromisoformat(fetched_at)
        ).total_seconds() / 3600
        is_stale = age_hours >= BUSINESS_TRENDS_CACHE_HOURS

    if not is_stale:
        print(f"[BIZ TRENDS] Using cached trends ({fetched_at}, {len(cache.get('trends', []))} items)")
        return cache["trends"]

    fresh = fetch_business_trends()
    if not fresh and cache.get("trends"):
        print("[BIZ TRENDS] Refresh failed — falling back to stale cache")
        return cache["trends"]

    new_cache = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "trends": fresh,
    }
    dir_name = os.path.dirname(BUSINESS_TRENDS_CACHE_PATH)
    os.makedirs(dir_name, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", dir=dir_name, delete=False, suffix=".tmp", encoding="utf-8"
    ) as tmp:
        json.dump(new_cache, tmp, ensure_ascii=False, indent=2)
        tmp_path = tmp.name
    os.replace(tmp_path, BUSINESS_TRENDS_CACHE_PATH)
    return fresh


# ══════════════════════════════════════════════════════════════
#  STANDALONE TEST
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("  Google Trends India — Fetch Test")
    print("=" * 60)

    results = fetch_google_trends()

    print(f"\nTotal: {len(results)}")
    print("=" * 60)

    for i, r in enumerate(results, 1):
        print(f"\n[{i}] Title   : {r['Blog_Title']}")
        print(f"    Link    : {r['Blog_Links']}")
        print(f"    Traffic : {r['traffic']}")
        print(f"    Date    : {r['Blog_PublishDate']}")
        print(f"    Content : {r['Blog_Content']}")
        print(f"    ---")