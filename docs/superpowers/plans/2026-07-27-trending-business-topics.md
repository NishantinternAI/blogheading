# Trending Business Topics Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn `get_cached_business_trends()`'s bare trending finance query phrases into real, verified article dicts (grounded in an actual discovered news article, never fabricated), and wire them into `core/pipeline.py` as a new source alongside the existing ones.

**Architecture:** Four new functions in `sources/google_trends.py` form a pipeline: search Google News RSS for a trend phrase (free) → title-prefilter candidates → extract full content from the best candidate via the existing `fetch_via_websearch()` (one AI call) → validate with the existing `_is_content_valid()` and `sources.common.assess_quality()` gates → return an article dict or `None`. `fetch_trending_business_articles()` orchestrates this for the top 5 trends by volume. `core/pipeline.py` then plugs this in as a fifth `PRIORITY_SOURCES` entry, bypassing the country/category filter the same way `nse_ipo`/`market_summary` already do.

**Tech Stack:** Python 3.10, stdlib `urllib.request`/`urllib.parse`/`re` (no new dependencies), existing `core.model_client.fetch_via_websearch`, existing `sources.common.assess_quality`.

## Global Constraints

- Design spec: `docs/superpowers/specs/2026-07-27-trending-business-topics-design.md` — read it before implementing; this plan implements it task-by-task.
- **Non-negotiable (from the spec's "Critical constraint" section):** a trend only becomes an article if real, substantiated news is verified behind it. Any failure at any gate (no candidates, no title match, invalid content, content too thin) means `None` is returned and that trend is skipped — never pass a bare trend phrase to the blog generator with no real facts behind it.
- No Selenium / headless browser anywhere in this feature.
- `max_trends` defaults to 5 (cost/latency control, per spec).
- New source name (used everywhere): `"google_trends_business"`. Do not reuse or collide with the existing `"google_trends"` source name — both run side by side.
- All new tests are ad-hoc scripts run directly (`python tools/test_X.py`), matching this repo's existing convention — no pytest, no test framework config exists in this repo.
- Every commit message follows this repo's existing style (see `git log` — descriptive body explaining *why*, not just *what*).

---

### Task 1: Google News RSS search for a trend phrase

**Files:**
- Modify: `sources/google_trends.py` (add imports, add function after `_is_content_valid`, i.e. after line 294 and before `fetch_google_trends` on line 305)
- Test: `tools/test_google_trends_business.py` (append)

**Interfaces:**
- Produces: `_search_google_news_for_trend(phrase: str) -> list[dict]`, where each dict is `{"title": str, "link": str, "pub_date": str, "source": str}`. Returns `[]` on any network failure.

- [ ] **Step 1: Write the failing test**

Append to `tools/test_google_trends_business.py`, right before the final `if failures:` block:

```python
# ── Task 1: _search_google_news_for_trend() ────────────────────────────
_FAKE_NEWS_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
<title>"idfc first bank share" - Google News</title>
<item>
  <title>IDFC First Bank shares surge 5% after Q1 results - Economic Times</title>
  <link>https://news.google.com/rss/articles/CBMifake1</link>
  <pubDate>Sun, 27 Jul 2026 09:00:00 GMT</pubDate>
  <source url="https://economictimes.indiatimes.com">Economic Times</source>
</item>
<item>
  <title>Why IDFC First Bank stock is trending today - Moneycontrol</title>
  <link>https://news.google.com/rss/articles/CBMifake2</link>
  <pubDate>Sun, 27 Jul 2026 08:30:00 GMT</pubDate>
  <source url="https://www.moneycontrol.com">Moneycontrol</source>
</item>
</channel>
</rss>"""


def test_search_google_news_for_trend():
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.return_value.__enter__ = lambda s: s
        mock_urlopen.return_value.read.return_value = _FAKE_NEWS_RSS.encode("utf-8")
        results = gt._search_google_news_for_trend("idfc first bank share")

    check("finds both news items", len(results) == 2)
    check("first item has correct title", results[0]["title"] == "IDFC First Bank shares surge 5% after Q1 results - Economic Times")
    check("first item has correct link", results[0]["link"] == "https://news.google.com/rss/articles/CBMifake1")
    check("first item has correct pub_date", results[0]["pub_date"] == "Sun, 27 Jul 2026 09:00:00 GMT")
    check("first item has correct source", results[0]["source"] == "Economic Times")


test_search_google_news_for_trend()


def test_search_google_news_for_trend_network_failure():
    with patch("urllib.request.urlopen", side_effect=Exception("connection reset")):
        results = gt._search_google_news_for_trend("some trend")
    check("network failure returns empty list, not an exception", results == [])


test_search_google_news_for_trend_network_failure()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "D:/content_engine_testing/blogheading" && PYTHONPATH=. python tools/test_google_trends_business.py`

Expected: `AttributeError: module 'sources.google_trends' has no attribute '_search_google_news_for_trend'` (raised before any `[OK]`/`[FAIL]` lines for the new tests print, since the test script itself will crash at that line).

- [ ] **Step 3: Write minimal implementation**

In `sources/google_trends.py`, add `from urllib.parse import quote` to the top imports (next to the existing `import urllib.request` on line 90), then add this function immediately after `_is_content_valid` (after line 294, before the `# MAIN FETCHER` section comment on line 297):

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd "D:/content_engine_testing/blogheading" && PYTHONPATH=. python tools/test_google_trends_business.py`

Expected: all prior `[OK]` lines still present, plus:
```
[OK] finds both news items
[OK] first item has correct title
[OK] first item has correct link
[OK] first item has correct pub_date
[OK] first item has correct source
[OK] network failure returns empty list, not an exception
```

- [ ] **Step 5: Commit**

```bash
git add sources/google_trends.py tools/test_google_trends_business.py
git commit -m "feat: add Google News RSS search for trending business phrases

First step of grounding get_cached_business_trends()'s bare query
phrases in real news -- a free RSS search, no AI cost, before spending
anything on content extraction."
```

---

### Task 2: Title-overlap candidate prefilter

**Files:**
- Modify: `sources/google_trends.py` (add function after `_search_google_news_for_trend`)
- Test: `tools/test_google_trends_business.py` (append)

**Interfaces:**
- Consumes: candidate dicts shaped like Task 1's `_search_google_news_for_trend()` output (`{"title", "link", "pub_date", "source"}`).
- Produces: `_pick_best_candidate(phrase: str, candidates: list) -> dict | None`.

- [ ] **Step 1: Write the failing test**

Append to `tools/test_google_trends_business.py`:

```python
# ── Task 2: _pick_best_candidate() ──────────────────────────────────────
def test_pick_best_candidate_finds_overlap():
    candidates = [
        {"title": "Completely unrelated cricket score update", "link": "/a", "pub_date": "", "source": ""},
        {"title": "IDFC First Bank shares surge 5% after Q1 results", "link": "/b", "pub_date": "", "source": ""},
    ]
    best = gt._pick_best_candidate("idfc first bank share", candidates)
    check("picks the candidate whose title overlaps the phrase", best is not None and best["link"] == "/b")


test_pick_best_candidate_finds_overlap()


def test_pick_best_candidate_no_overlap_returns_none():
    candidates = [
        {"title": "Completely unrelated cricket score update", "link": "/a", "pub_date": "", "source": ""},
    ]
    best = gt._pick_best_candidate("idfc first bank share", candidates)
    check("returns None when no candidate title overlaps the phrase", best is None)


test_pick_best_candidate_no_overlap_returns_none()


def test_pick_best_candidate_empty_list_returns_none():
    best = gt._pick_best_candidate("idfc first bank share", [])
    check("returns None for an empty candidate list", best is None)


test_pick_best_candidate_empty_list_returns_none()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "D:/content_engine_testing/blogheading" && PYTHONPATH=. python tools/test_google_trends_business.py`

Expected: `AttributeError: module 'sources.google_trends' has no attribute '_pick_best_candidate'`

- [ ] **Step 3: Write minimal implementation**

Add immediately after `_search_google_news_for_trend`:

```python
def _pick_best_candidate(phrase: str, candidates: list) -> dict | None:
    """
    Title-level prefilter (no AI call) -- keeps only candidates whose
    title shares at least one word (len > 3, case-insensitive) with the
    trend phrase, same shape as _is_content_valid()'s title-overlap
    check. Returns the first surviving candidate (Google News RSS already
    orders by relevance/recency), or None if nothing overlaps.
    """
    phrase_words = [w.lower() for w in phrase.split() if len(w) > 3]
    if not phrase_words:
        return candidates[0] if candidates else None

    for candidate in candidates:
        title_lower = candidate.get("title", "").lower()
        if any(w in title_lower for w in phrase_words):
            return candidate

    return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd "D:/content_engine_testing/blogheading" && PYTHONPATH=. python tools/test_google_trends_business.py`

Expected: all prior `[OK]` lines, plus:
```
[OK] picks the candidate whose title overlaps the phrase
[OK] returns None when no candidate title overlaps the phrase
[OK] returns None for an empty candidate list
```

- [ ] **Step 5: Commit**

```bash
git add sources/google_trends.py tools/test_google_trends_business.py
git commit -m "feat: add title-overlap prefilter for Google News candidates

Cheap check before spending an AI call on content extraction -- rejects
candidates whose title shares nothing with the trending phrase."
```

---

### Task 3: Ground one trend in verified real news

**Files:**
- Modify: `sources/google_trends.py` (add `from core.model_client import fetch_via_websearch` and `from sources.common import assess_quality` to imports; add function after `_pick_best_candidate`)
- Test: `tools/test_google_trends_business.py` (append)

**Interfaces:**
- Consumes: `_search_google_news_for_trend()` (Task 1), `_pick_best_candidate()` (Task 2), existing `_is_content_valid(content: str, trend_title: str) -> bool` (line 269 of this same file), `core.model_client.fetch_via_websearch(url: str) -> str`, `sources.common.assess_quality(content: str) -> dict` with `{"word_count": int, "quality": "rich"|"thin"|"bare"|"empty"}`.
- Produces: `ground_trend_in_news(trend: dict) -> dict | None`, where `trend` is one entry from `get_cached_business_trends()`'s return list (`{"title", "volume", "growth_pct", "started_unix", "related_queries", "category_ids"}`). Returns an article dict `{"Blog_Title", "Blog_Content", "Blog_Links", "Blog_PublishDate", "trending_signal"}` or `None`.

- [ ] **Step 1: Write the failing test**

Append to `tools/test_google_trends_business.py`:

```python
# ── Task 3: ground_trend_in_news() ──────────────────────────────────────
_FAKE_TREND = {
    "title": "idfc first bank share",
    "volume": 5000,
    "growth_pct": 100,
    "started_unix": 1785120000,
    "related_queries": ["idfc first bank share"],
    "category_ids": [3],
}

_REAL_CONTENT = " ".join(["IDFC First Bank shares rose sharply today after strong quarterly results."] * 30)  # well over 150 words


def test_ground_trend_in_news_success():
    with patch.object(gt, "_search_google_news_for_trend", return_value=[
        {"title": "IDFC First Bank shares surge 5% after Q1 results", "link": "https://example.com/a", "pub_date": "Sun, 27 Jul 2026 09:00:00 GMT", "source": "Economic Times"},
    ]):
        with patch.object(gt, "fetch_via_websearch", return_value=_REAL_CONTENT):
            result = gt.ground_trend_in_news(_FAKE_TREND)

    check("returns an article dict on success", result is not None)
    check("Blog_Title is the REAL article headline, not the bare phrase",
          result["Blog_Title"] == "IDFC First Bank shares surge 5% after Q1 results" if result else False)
    check("Blog_Content is the extracted content", result["Blog_Content"] == _REAL_CONTENT if result else False)
    check("Blog_Links is the real article URL", result["Blog_Links"] == "https://example.com/a" if result else False)
    check("trending_signal carries the trend metadata", "idfc first bank share" in result["trending_signal"] if result else False)


test_ground_trend_in_news_success()


def test_ground_trend_in_news_no_candidates():
    with patch.object(gt, "_search_google_news_for_trend", return_value=[]):
        result = gt.ground_trend_in_news(_FAKE_TREND)
    check("returns None when no Google News candidates exist", result is None)


test_ground_trend_in_news_no_candidates()


def test_ground_trend_in_news_no_title_overlap():
    with patch.object(gt, "_search_google_news_for_trend", return_value=[
        {"title": "Completely unrelated cricket score update", "link": "https://example.com/z", "pub_date": "", "source": ""},
    ]):
        result = gt.ground_trend_in_news(_FAKE_TREND)
    check("returns None when no candidate title overlaps the phrase", result is None)


test_ground_trend_in_news_no_title_overlap()


def test_ground_trend_in_news_websearch_empty():
    with patch.object(gt, "_search_google_news_for_trend", return_value=[
        {"title": "IDFC First Bank shares surge 5% after Q1 results", "link": "https://example.com/a", "pub_date": "", "source": ""},
    ]):
        with patch.object(gt, "fetch_via_websearch", return_value=""):
            result = gt.ground_trend_in_news(_FAKE_TREND)
    check("returns None when fetch_via_websearch returns nothing", result is None)


test_ground_trend_in_news_websearch_empty()


def test_ground_trend_in_news_invalid_content():
    with patch.object(gt, "_search_google_news_for_trend", return_value=[
        {"title": "IDFC First Bank shares surge 5% after Q1 results", "link": "https://example.com/a", "pub_date": "", "source": ""},
    ]):
        with patch.object(gt, "fetch_via_websearch", return_value="Please sign in to continue reading this premium content."):
            result = gt.ground_trend_in_news(_FAKE_TREND)
    check("returns None when content fails _is_content_valid (paywall)", result is None)


test_ground_trend_in_news_invalid_content()


def test_ground_trend_in_news_content_too_thin():
    with patch.object(gt, "_search_google_news_for_trend", return_value=[
        {"title": "IDFC First Bank shares surge 5% after Q1 results", "link": "https://example.com/a", "pub_date": "", "source": ""},
    ]):
        with patch.object(gt, "fetch_via_websearch", return_value="IDFC First Bank shares rose today."):
            result = gt.ground_trend_in_news(_FAKE_TREND)
    check("returns None when content is too thin (assess_quality bare/empty)", result is None)


test_ground_trend_in_news_content_too_thin()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "D:/content_engine_testing/blogheading" && PYTHONPATH=. python tools/test_google_trends_business.py`

Expected: `AttributeError: module 'sources.google_trends' has no attribute 'ground_trend_in_news'`

- [ ] **Step 3: Write minimal implementation**

Add these two imports near the top of `sources/google_trends.py`, right after the existing `from datetime import datetime, timezone` line (91):

```python
from core.model_client import fetch_via_websearch
from sources.common import assess_quality
```

Add this function immediately after `_pick_best_candidate`:

```python
def ground_trend_in_news(trend: dict) -> dict | None:
    """
    Grounds one trending phrase (from get_cached_business_trends()) in a
    real, verified news article. Returns an article dict shaped like
    every other source's output, or None if real news can't be verified
    at ANY step -- this is the hard gate against generating a blog from a
    bare search-volume spike with no real facts behind it (see the
    2026-07-24 hallucinated-blog incident in docs/review.md).
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

    content = fetch_via_websearch(best["link"])
    if not content:
        print(f"[BIZ TRENDS] No content extracted for '{phrase}' ({best['link']}) -- skipping")
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd "D:/content_engine_testing/blogheading" && PYTHONPATH=. python tools/test_google_trends_business.py`

Expected: all prior `[OK]` lines, plus:
```
[OK] returns an article dict on success
[OK] Blog_Title is the REAL article headline, not the bare phrase
[OK] Blog_Content is the extracted content
[OK] Blog_Links is the real article URL
[OK] trending_signal carries the trend metadata
[OK] returns None when no Google News candidates exist
[OK] returns None when no candidate title overlaps the phrase
[OK] returns None when fetch_via_websearch returns nothing
[OK] returns None when content fails _is_content_valid (paywall)
[OK] returns None when content is too thin (assess_quality bare/empty)
```

**Why the test patches `gt.fetch_via_websearch`, not `core.model_client.fetch_via_websearch`:** `sources/google_trends.py` imports it via `from core.model_client import fetch_via_websearch`, which binds a *new* name in `google_trends`'s own module namespace at import time. Patching `core.model_client.fetch_via_websearch` would not affect calls made from inside `google_trends.py` — `patch.object(gt, "fetch_via_websearch", ...)` is the correct target, matching the pattern already used for `_search_google_news_for_trend` in this same test file.

- [ ] **Step 5: Commit**

```bash
git add sources/google_trends.py tools/test_google_trends_business.py
git commit -m "feat: ground trending phrases in verified real news

ground_trend_in_news() is the hard gate against generating a blog from
a bare search-volume spike with no real facts behind it -- chains
Google News discovery, title prefilter, fetch_via_websearch content
extraction, and the existing _is_content_valid()/assess_quality() gates.
Any failure returns None; the trend is simply skipped, never passed to
the blog generator with nothing real to write about."
```

---

### Task 4: Fetch entry point (top-N by volume, per-trend isolation)

**Files:**
- Modify: `sources/google_trends.py` (add function after `ground_trend_in_news`)
- Test: `tools/test_google_trends_business.py` (append)

**Interfaces:**
- Consumes: `get_cached_business_trends()` (already exists in this file), `ground_trend_in_news()` (Task 3).
- Produces: `fetch_trending_business_articles(max_trends: int = 5) -> list`.

- [ ] **Step 1: Write the failing test**

Append to `tools/test_google_trends_business.py`:

```python
# ── Task 4: fetch_trending_business_articles() ──────────────────────────
def test_fetch_trending_business_articles_caps_and_filters_none():
    fake_trends = [{"title": f"trend {i}", "volume": 100 - i, "growth_pct": 50} for i in range(8)]

    def fake_ground(trend):
        # Every other trend "fails" to ground (simulates real-world skip rate)
        idx = int(trend["title"].split()[-1])
        if idx % 2 == 0:
            return {"Blog_Title": f"real headline {idx}", "Blog_Content": "x" * 200}
        return None

    with patch.object(gt, "get_cached_business_trends", return_value=fake_trends):
        with patch.object(gt, "ground_trend_in_news", side_effect=fake_ground) as mock_ground:
            articles = gt.fetch_trending_business_articles(max_trends=5)

    check("only calls ground_trend_in_news for the top max_trends", mock_ground.call_count == 5)
    check("drops None results, keeping only grounded articles", len(articles) == 3)  # trends 0,2,4 ground successfully out of top 5 (0-4)


test_fetch_trending_business_articles_caps_and_filters_none()


def test_fetch_trending_business_articles_isolates_per_trend_failures():
    fake_trends = [{"title": "good trend", "volume": 100, "growth_pct": 50},
                   {"title": "bad trend", "volume": 90, "growth_pct": 50}]

    def fake_ground(trend):
        if trend["title"] == "bad trend":
            raise RuntimeError("simulated crash grounding this one trend")
        return {"Blog_Title": "real headline", "Blog_Content": "x" * 200}

    with patch.object(gt, "get_cached_business_trends", return_value=fake_trends):
        with patch.object(gt, "ground_trend_in_news", side_effect=fake_ground):
            articles = gt.fetch_trending_business_articles(max_trends=5)

    check("one trend's exception doesn't drop the other trend's result", len(articles) == 1)
    check("the surviving article is the one that didn't crash", articles[0]["Blog_Title"] == "real headline" if articles else False)


test_fetch_trending_business_articles_isolates_per_trend_failures()


def test_fetch_trending_business_articles_empty_trends():
    with patch.object(gt, "get_cached_business_trends", return_value=[]):
        articles = gt.fetch_trending_business_articles()
    check("returns [] when there are no cached trends at all", articles == [])


test_fetch_trending_business_articles_empty_trends()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "D:/content_engine_testing/blogheading" && PYTHONPATH=. python tools/test_google_trends_business.py`

Expected: `AttributeError: module 'sources.google_trends' has no attribute 'fetch_trending_business_articles'`

- [ ] **Step 3: Write minimal implementation**

Add immediately after `ground_trend_in_news`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd "D:/content_engine_testing/blogheading" && PYTHONPATH=. python tools/test_google_trends_business.py`

Expected: all prior `[OK]` lines, plus:
```
[OK] only calls ground_trend_in_news for the top max_trends
[OK] drops None results, keeping only grounded articles
[OK] one trend's exception doesn't drop the other trend's result
[OK] the surviving article is the one that didn't crash
[OK] returns [] when there are no cached trends at all
```

Then run the FULL test file end-to-end one more time to confirm every test from Tasks 1-4 (and the pre-existing cache tests) still passes together:

Run: `cd "D:/content_engine_testing/blogheading" && PYTHONPATH=. python tools/test_google_trends_business.py`
Expected: ends with `All cases passed.` and exit code 0.

- [ ] **Step 5: Commit**

```bash
git add sources/google_trends.py tools/test_google_trends_business.py
git commit -m "feat: add fetch_trending_business_articles() entry point

Takes the top-5-by-volume cached business trends and grounds each in
real news, with per-trend error isolation so one failure never drops
the rest of the batch. This is the function core/pipeline.py plugs in
as a new source in the next task."
```

---

### Task 5: Wire into core/pipeline.py

**Files:**
- Modify: `core/pipeline.py:60` (import), `core/pipeline.py:138` (PRIORITY_SOURCES), `core/pipeline.py:720-731` (`_fetch_all_sources`'s `sources` list), `core/pipeline.py:867-889` (`_full_fetch_and_build_stack`'s bypass grouping), `core/pipeline.py:956-974` (`_fetch_after_timestamp`'s bypass grouping)
- Test: `tools/test_pipeline_trending_business_wiring.py` (new file)

**Interfaces:**
- Consumes: `sources.google_trends.fetch_trending_business_articles` (Task 4).
- Produces: nothing new consumed by later tasks — this is the final integration task.

- [ ] **Step 1: Write the failing test**

Create `tools/test_pipeline_trending_business_wiring.py`:

```python
"""
Ad-hoc verification script confirming the trending-business-topics
source is correctly wired into core/pipeline.py -- run directly with
`python tools/test_pipeline_trending_business_wiring.py`. Inspects
source code/module state rather than running a full pipeline cycle,
since simulating one would require mocking all 10 existing fetchers.
"""
import inspect

import core.pipeline as pipeline

failures = []


def check(label, condition):
    status = "OK" if condition else "FAIL"
    print(f"[{status}] {label}")
    if not condition:
        failures.append(label)


check(
    "google_trends_business is in PRIORITY_SOURCES",
    "google_trends_business" in pipeline.PRIORITY_SOURCES,
)

fetch_all_src = inspect.getsource(pipeline._fetch_all_sources)
check(
    "fetch_trending_business_articles is wired into _fetch_all_sources' source list",
    "fetch_trending_business_articles" in fetch_all_src and "google_trends_business" in fetch_all_src,
)

full_fetch_src = inspect.getsource(pipeline._full_fetch_and_build_stack)
check(
    "google_trends_business gets bypass treatment in _full_fetch_and_build_stack",
    "google_trends_business" in full_fetch_src,
)

after_ts_src = inspect.getsource(pipeline._fetch_after_timestamp)
check(
    "google_trends_business gets bypass treatment in _fetch_after_timestamp",
    "google_trends_business" in after_ts_src,
)

if failures:
    print(f"\n{len(failures)} FAILURE(S)")
    raise SystemExit(1)
print("\nAll cases passed.")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "D:/content_engine_testing/blogheading" && PYTHONPATH=. python tools/test_pipeline_trending_business_wiring.py`

Expected:
```
[FAIL] google_trends_business is in PRIORITY_SOURCES
[FAIL] fetch_trending_business_articles is wired into _fetch_all_sources' source list
[FAIL] google_trends_business gets bypass treatment in _full_fetch_and_build_stack
[FAIL] google_trends_business gets bypass treatment in _fetch_after_timestamp

4 FAILURE(S)
```
(exits with code 1)

- [ ] **Step 3: Write minimal implementation**

**3a.** In `core/pipeline.py`, change line 60 from:
```python
from sources.google_trends import fetch_google_trends
```
to:
```python
from sources.google_trends import fetch_google_trends, fetch_trending_business_articles
```

**3b.** Change line 138 from:
```python
PRIORITY_SOURCES  = ["nse_ipo", "google_trends", "market_summary"]
```
to:
```python
PRIORITY_SOURCES  = ["nse_ipo", "google_trends", "google_trends_business", "market_summary"]
```

**3c.** In `_fetch_all_sources` (around line 720), change:
```python
    sources = [
        (fetch_nse_ipo,       "nse_ipo"),
        (fetch_morning_summary, "market_summary"),
        (fetch_google_trends,  "google_trends"),
        (fetch_google_news_business, "google_news_business"),
        (fetch_economic_times,       "economic_times"),
        (fetch_ndtv_profit,        "ndtv_profit"),
        (fetch_zerodha,       "zerodha"),
        (fetch_5paisa,        "5paisa"),
        (fetch_livemint,      "livemint"),
        (fetch_business_standard, "business_standard"),
    ]
```
to:
```python
    sources = [
        (fetch_nse_ipo,       "nse_ipo"),
        (fetch_morning_summary, "market_summary"),
        (fetch_google_trends,  "google_trends"),
        (fetch_trending_business_articles, "google_trends_business"),
        (fetch_google_news_business, "google_news_business"),
        (fetch_economic_times,       "economic_times"),
        (fetch_ndtv_profit,        "ndtv_profit"),
        (fetch_zerodha,       "zerodha"),
        (fetch_5paisa,        "5paisa"),
        (fetch_livemint,      "livemint"),
        (fetch_business_standard, "business_standard"),
    ]
```

Also in the fetch loop right below it (the `for fetcher, source_name in sources:` block), the `else` branch does `data = fetcher()[:top_n]` for anything not explicitly named — `google_trends_business` must NOT be truncated to `top_n` (it's already capped to 5 inside `fetch_trending_business_articles` itself) and must NOT be called with `top_n=` as a kwarg. Add an explicit branch: change

```python
                elif source_name == "google_trends":
                    data = fetcher()
                elif source_name == "google_news_business":
```
to
```python
                elif source_name == "google_trends":
                    data = fetcher()
                elif source_name == "google_trends_business":
                    data = fetcher()        # already capped to max_trends internally
                elif source_name == "google_news_business":
```

**3d.** In `_full_fetch_and_build_stack` (around line 867-889), change:
```python
    ipo_articles = [
    a for a in all_data
    if a.get("source") == "nse_ipo"
    ]

    market_summary_articles = [
    a for a in all_data
    if a.get("source") == "market_summary"
    ]

    google_trends_articles = [
    a for a in all_data
    if a.get("source") == "google_trends"
    ]
    print(
    f"[DEBUG] Finance Google Trends: "
    f"{len(google_trends_articles)}"
    )

    other_articles = [
    a for a in all_data
    if a.get("source") not in ["nse_ipo", "google_trends", "market_summary"]
    ]
```
to:
```python
    ipo_articles = [
    a for a in all_data
    if a.get("source") == "nse_ipo"
    ]

    market_summary_articles = [
    a for a in all_data
    if a.get("source") == "market_summary"
    ]

    google_trends_articles = [
    a for a in all_data
    if a.get("source") == "google_trends"
    ]
    print(
    f"[DEBUG] Finance Google Trends: "
    f"{len(google_trends_articles)}"
    )

    google_trends_business_articles = [
    a for a in all_data
    if a.get("source") == "google_trends_business"
    ]
    print(
    f"[DEBUG] Trending business topics (bypass filter): "
    f"{len(google_trends_business_articles)}"
    )

    other_articles = [
    a for a in all_data
    if a.get("source") not in ["nse_ipo", "google_trends", "google_trends_business", "market_summary"]
    ]
```

And a few lines down, change:
```python
    filtered_data = (
    ipo_articles +
    market_summary_articles +
    finance_trends +
    filtered_other
    )
```
to:
```python
    filtered_data = (
    ipo_articles +
    market_summary_articles +
    finance_trends +
    google_trends_business_articles +
    filtered_other
    )
```

**3e.** In `_fetch_after_timestamp` (around line 956-999), change:
```python
    google_trends_articles = [
        a for a in all_data
        if a.get("source") == "google_trends"
    ]

    other_articles = [
        a for a in all_data
        if a.get("source") not in ["nse_ipo", "google_trends", "market_summary"]
    ]

    print(f"[FILTER] IPO articles (bypass filter)    : {len(ipo_articles)}")
    print(f"[FILTER] Market summary articles (bypass filter) : {len(market_summary_articles)}")
    print(f"[FILTER] Google Trends articles           : {len(google_trends_articles)}")
    print(f"[FILTER] Other articles (to filter)      : {len(other_articles)}")
```
to:
```python
    google_trends_articles = [
        a for a in all_data
        if a.get("source") == "google_trends"
    ]

    google_trends_business_articles = [
        a for a in all_data
        if a.get("source") == "google_trends_business"
    ]

    other_articles = [
        a for a in all_data
        if a.get("source") not in ["nse_ipo", "google_trends", "google_trends_business", "market_summary"]
    ]

    print(f"[FILTER] IPO articles (bypass filter)    : {len(ipo_articles)}")
    print(f"[FILTER] Market summary articles (bypass filter) : {len(market_summary_articles)}")
    print(f"[FILTER] Google Trends articles           : {len(google_trends_articles)}")
    print(f"[FILTER] Trending business topics (bypass filter): {len(google_trends_business_articles)}")
    print(f"[FILTER] Other articles (to filter)      : {len(other_articles)}")
```

And change:
```python
    filtered_data = ipo_articles + market_summary_articles + finance_trends + filtered_other
```
to:
```python
    filtered_data = ipo_articles + market_summary_articles + finance_trends + google_trends_business_articles + filtered_other
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd "D:/content_engine_testing/blogheading" && PYTHONPATH=. python tools/test_pipeline_trending_business_wiring.py`

Expected:
```
[OK] google_trends_business is in PRIORITY_SOURCES
[OK] fetch_trending_business_articles is wired into _fetch_all_sources' source list
[OK] google_trends_business gets bypass treatment in _full_fetch_and_build_stack
[OK] google_trends_business gets bypass treatment in _fetch_after_timestamp

All cases passed.
```

Then confirm the whole module still imports cleanly (no syntax errors from the edits):

Run: `cd "D:/content_engine_testing/blogheading" && python -m py_compile core/pipeline.py sources/google_trends.py && echo COMPILE_OK`
Expected: `COMPILE_OK`

- [ ] **Step 5: Commit**

```bash
git add core/pipeline.py tools/test_pipeline_trending_business_wiring.py
git commit -m "feat: wire trending-business-topics source into the pipeline

Adds google_trends_business as a fifth PRIORITY_SOURCES entry, alongside
(not replacing) the existing general google_trends RSS source. Gets the
same bypass-country/category-filter treatment as nse_ipo/market_summary
since it's already India+finance-scoped and individually verified via
ground_trend_in_news() before ever reaching this point."
```

---

### Task 6: Deploy and verify live on sarthi-server

**Files:** none (deployment/verification only, no code changes)

**Interfaces:** none — this task confirms Tasks 1-5 work end-to-end against the real network from the production server.

- [ ] **Step 1: Push all commits**

Run: `cd "D:/content_engine_testing/blogheading" && git push origin test_ipo_news`
Expected: all 5 commits from Tasks 1-5 pushed successfully.

- [ ] **Step 2: Pull and rebuild on the server**

Run: `ssh sarthi-server "cd '/home/swastika-ai/Content Engine/Blogheading' && git pull origin test_ipo_news && docker compose up --build -d"`
Expected: fast-forward pull showing the 5 new commits, followed by a successful image rebuild and container recreation (same pattern used earlier this session).

- [ ] **Step 3: Run both new test files live in the container**

Run: `ssh sarthi-server "docker exec blogheading-scheduler-1 python3 tools/test_google_trends_business.py"`
Expected: `All cases passed.` (all mocked tests, no live network needed, confirms the code is correctly deployed)

Run: `ssh sarthi-server "docker exec blogheading-scheduler-1 python3 tools/test_pipeline_trending_business_wiring.py"`
Expected: `All cases passed.`

- [ ] **Step 4: Live end-to-end smoke test against the real network**

Run:
```bash
ssh sarthi-server "docker exec blogheading-scheduler-1 python3 -c \"
from sources.google_trends import fetch_trending_business_articles
articles = fetch_trending_business_articles()
print(f'grounded {len(articles)} article(s) from live trends')
for a in articles:
    print('-', a['Blog_Title'], '|', a['trending_signal'])
\""
```
Expected: a real run against live Google Trends + Google News + the AI web-search tool, printing 0-5 grounded articles with real headlines and their originating trend signal. `0` is an acceptable result (means none of the top 5 current trends had verifiable real news behind them right now) — the key thing to confirm is it runs without crashing and every printed article has a real, sensible headline (not a fabricated one).

- [ ] **Step 5: No commit for this task** (deployment/verification only — nothing to commit beyond what Tasks 1-5 already committed)

---

## Post-implementation notes for the next session

- `trending_signal` is stored on the article dict but not yet consumed anywhere downstream (by design — see the spec's note on this). If a future session wants to nudge `generate_blog()`'s prompt using the exact trending phrase, that's a separate follow-up, not part of this plan.
- This plan does not touch semantic/cross-source dedup (e.g. the same underlying stock move being covered by both `business_standard` and a `google_trends_business`-discovered article under different headlines) — pre-existing limitation shared with every other source pair, out of scope per the spec's Non-goals.
