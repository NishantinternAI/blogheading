"""
Ad-hoc verification script for sources/google_trends.py's Daily Trends
RSS enrichment source -- run directly with
`python tools/test_google_trends_daily_rss.py`. No live network calls --
builds synthetic RSS matching the real ht:news_item structure observed
on trends.google.com/trending/rss?geo=IN.
"""
from unittest.mock import patch

import sources.google_trends as gt

failures = []


def check(label, condition):
    status = "OK" if condition else "FAIL"
    print(f"[{status}] {label}")
    if not condition:
        failures.append(label)


_FAKE_RSS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<rss xmlns:atom="http://www.w3.org/2005/Atom" xmlns:ht="https://trends.google.com/trending/rss" version="2.0">
<channel>
<title>Daily Search Trends</title>
<item>
<title>hul share price</title>
<ht:approx_traffic>500+</ht:approx_traffic>
<ht:news_item>
<ht:news_item_title>HUL Q1 results: Net profit falls 4%</ht:news_item_title>
<ht:news_item_url>https://www.moneycontrol.com/news/hul-q1-results.html</ht:news_item_url>
<ht:news_item_source>Moneycontrol.com</ht:news_item_source>
</ht:news_item>
<ht:news_item>
<ht:news_item_title>L&amp;T Q1 preview</ht:news_item_title>
<ht:news_item_url>https://www.business-standard.com/lt-q1-preview.html</ht:news_item_url>
<ht:news_item_source>Business Standard</ht:news_item_source>
</ht:news_item>
</item>
<item>
<title>namibia vs nepal</title>
<ht:approx_traffic>10K+</ht:approx_traffic>
<ht:news_item>
<ht:news_item_title>Namibia beat Nepal by 5 wickets</ht:news_item_title>
<ht:news_item_url>https://www.espncricinfo.com/namibia-vs-nepal.html</ht:news_item_url>
<ht:news_item_source>ESPN Cricinfo</ht:news_item_source>
</ht:news_item>
</item>
<item>
<title>no news items trend</title>
<ht:approx_traffic>1K+</ht:approx_traffic>
</item>
</channel>
</rss>"""


# ── _fetch_daily_trends_rss() ────────────────────────────────────────────
def test_fetch_daily_trends_rss_parses_items_and_news_urls():
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.return_value.read.return_value = _FAKE_RSS.encode("utf-8")
        items = gt._fetch_daily_trends_rss()

    check("parses all 3 items", len(items) == 3)
    check("first item has correct title", items[0]["title"] == "hul share price")
    check("first item has both news_urls in order",
          items[0]["news_urls"] == [
              "https://www.moneycontrol.com/news/hul-q1-results.html",
              "https://www.business-standard.com/lt-q1-preview.html",
          ])
    check("item with no ht:news_item elements gets an empty news_urls list",
          items[2]["news_urls"] == [])


test_fetch_daily_trends_rss_parses_items_and_news_urls()


def test_fetch_daily_trends_rss_network_failure():
    with patch("urllib.request.urlopen", side_effect=Exception("connection reset")):
        items = gt._fetch_daily_trends_rss()
    check("network failure returns empty list, not an exception", items == [])


test_fetch_daily_trends_rss_network_failure()


def test_fetch_daily_trends_rss_parse_failure():
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.return_value.read.return_value = b"not xml at all <<<"
        items = gt._fetch_daily_trends_rss()
    check("unparseable XML returns empty list, not an exception", items == [])


test_fetch_daily_trends_rss_parse_failure()

# ── ground_daily_rss_trend() ─────────────────────────────────────────────
_RICH_CONTENT = " ".join(["HUL reported a decline in quarterly net profit today."] * 30)  # well over 150 words


def test_ground_daily_rss_trend_success_uses_actually_scraped_url():
    item = {"title": "hul share price", "news_urls": ["https://a.example/fails", "https://b.example/works"]}
    with patch.object(gt, "_scrape_all_news_urls",
                       return_value=f"--- Source 2 (https://b.example/works) ---\n{_RICH_CONTENT}"):
        result = gt.ground_daily_rss_trend(item)

    check("returns an article dict on success", result is not None)
    check("Blog_Content has the source marker stripped out",
          result is not None and "--- Source" not in result["Blog_Content"])
    check("Blog_Content is the actual article text",
          result is not None and result["Blog_Content"] == _RICH_CONTENT)
    check("Blog_Links is the URL that actually succeeded (b.example), not news_urls[0] (a.example, which failed)",
          result is not None and result["Blog_Links"] == "https://b.example/works")
    check("Blog_PublishDate is empty (feed carries no per-article date)",
          result is not None and result["Blog_PublishDate"] == "")


test_ground_daily_rss_trend_success_uses_actually_scraped_url()


def test_ground_daily_rss_trend_no_news_urls():
    result = gt.ground_daily_rss_trend({"title": "no news items trend", "news_urls": []})
    check("returns None when there are no news_urls to try", result is None)


test_ground_daily_rss_trend_no_news_urls()


def test_ground_daily_rss_trend_scrape_fails():
    item = {"title": "hul share price", "news_urls": ["https://a.example/fails"]}
    with patch.object(gt, "_scrape_all_news_urls", return_value=""):
        result = gt.ground_daily_rss_trend(item)
    check("returns None when every news_url fails to scrape", result is None)


test_ground_daily_rss_trend_scrape_fails()


def test_ground_daily_rss_trend_content_too_thin():
    item = {"title": "hul share price", "news_urls": ["https://a.example/works"]}
    with patch.object(gt, "_scrape_all_news_urls",
                       return_value="--- Source 1 (https://a.example/works) ---\nHUL shares fell today."):
        result = gt.ground_daily_rss_trend(item)
    check("returns None when scraped content is too thin (assess_quality bare/empty)", result is None)


test_ground_daily_rss_trend_content_too_thin()

# ── _is_finance_related() ────────────────────────────────────────────────
def test_is_finance_related_true_for_genuine_finance_trends():
    check("'hul share price' matches on its own title", gt._is_finance_related("hul share price", []))
    check("'bel share' matches on its own title", gt._is_finance_related("bel share", []))
    check("a vernacular title matches via its related_queries",
          gt._is_finance_related("स्टॉक", ["stock market news"]))


test_is_finance_related_true_for_genuine_finance_trends()


def test_is_finance_related_false_for_mistagged_trend():
    # Real 2026-07-28 case: a Chennai power-outage story tagged category 3
    # by Google's own trends page despite having nothing to do with finance.
    check("a power-outage trend with no finance keyword is rejected",
          not gt._is_finance_related("மின்தடை", ["மின்தடை"]))


test_is_finance_related_false_for_mistagged_trend()

# ── fetch_trending_daily_rss_articles() ──────────────────────────────────
def test_fetch_trending_daily_rss_articles_filters_to_business_trends():
    daily_items = [
        {"title": "hul share price", "news_urls": ["https://a.example/works"]},
        {"title": "namibia vs nepal", "news_urls": ["https://b.example/works"]},  # not a business trend
    ]
    biz_trends = [{"title": "hul share price", "volume": 500, "related_queries": ["hul share price"]},
                  {"title": "some other trend", "volume": 100, "related_queries": []}]

    def fake_ground(item):
        return {"Blog_Title": item["title"], "Blog_Content": _RICH_CONTENT}

    with patch.object(gt, "_fetch_daily_trends_rss", return_value=daily_items):
        with patch.object(gt, "get_cached_business_trends", return_value=biz_trends):
            with patch.object(gt, "ground_daily_rss_trend", side_effect=fake_ground) as mock_ground:
                articles = gt.fetch_trending_daily_rss_articles()

    check("only grounds the RSS item that's also a tagged business trend", mock_ground.call_count == 1)
    check("returns exactly the business-relevant article", len(articles) == 1 and articles[0]["Blog_Title"] == "hul share price")


test_fetch_trending_daily_rss_articles_filters_to_business_trends()


def test_fetch_trending_daily_rss_articles_rejects_mistagged_business_trend():
    # Category-3-tagged by Google but not actually finance (no keyword match)
    daily_items = [{"title": "மின்தடை", "news_urls": ["https://a.example/works"]}]
    biz_trends = [{"title": "மின்தடை", "related_queries": ["மின்தடை"]}]

    with patch.object(gt, "_fetch_daily_trends_rss", return_value=daily_items):
        with patch.object(gt, "get_cached_business_trends", return_value=biz_trends):
            with patch.object(gt, "ground_daily_rss_trend") as mock_ground:
                articles = gt.fetch_trending_daily_rss_articles()

    check("never even attempts to ground a mistagged non-finance trend", mock_ground.call_count == 0)
    check("returns [] for an all-mistagged feed", articles == [])


test_fetch_trending_daily_rss_articles_rejects_mistagged_business_trend()


def test_fetch_trending_daily_rss_articles_isolates_per_item_failures():
    daily_items = [
        {"title": "hul share price", "news_urls": ["https://a.example/works"]},
        {"title": "bad share price trend", "news_urls": ["https://b.example/works"]},
    ]
    biz_trends = [{"title": "hul share price"}, {"title": "bad share price trend"}]

    def fake_ground(item):
        if item["title"] == "bad share price trend":
            raise RuntimeError("simulated crash grounding this one item")
        return {"Blog_Title": "hul share price", "Blog_Content": _RICH_CONTENT}

    with patch.object(gt, "_fetch_daily_trends_rss", return_value=daily_items):
        with patch.object(gt, "get_cached_business_trends", return_value=biz_trends):
            with patch.object(gt, "ground_daily_rss_trend", side_effect=fake_ground):
                articles = gt.fetch_trending_daily_rss_articles()

    check("one item's exception doesn't drop the other item's result", len(articles) == 1)


test_fetch_trending_daily_rss_articles_isolates_per_item_failures()


def test_fetch_trending_daily_rss_articles_empty_feed():
    with patch.object(gt, "_fetch_daily_trends_rss", return_value=[]):
        articles = gt.fetch_trending_daily_rss_articles()
    check("returns [] when the daily feed itself is empty", articles == [])


test_fetch_trending_daily_rss_articles_empty_feed()

if failures:
    print(f"\n{len(failures)} FAILURE(S)")
    raise SystemExit(1)
print("\nAll cases passed.")
