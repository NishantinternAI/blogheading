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

import re
import urllib.request


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