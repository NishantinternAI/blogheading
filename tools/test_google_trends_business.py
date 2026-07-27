"""
Ad-hoc verification script for sources/google_trends.py's business-trends
scraper -- run directly with `python tools/test_google_trends_business.py`.
No live network calls -- builds a synthetic page matching the real
AF_initDataCallback structure observed on trends.google.com/trending.
"""
import json
import os
import tempfile
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

import sources.google_trends as gt

failures = []


def check(label, condition):
    status = "OK" if condition else "FAIL"
    print(f"[{status}] {label}")
    if not condition:
        failures.append(label)


def _fake_record(title, volume, growth, category_ids):
    return [title, None, "IN", [1785120000], None, None, volume, None, growth,
            [title], category_ids, [[123456789, "en", "IN"]], title]


def _build_fake_html(records):
    data = [None, records]
    unrelated_block = "AF_initDataCallback({key: 'ds:1', hash: '1', data:[\"India\"], sideChannel: {}});"
    trends_block = "AF_initDataCallback({key: 'ds:2', hash: '2', data:" + json.dumps(data) + ", sideChannel: {}});"
    return f"<html><script>{unrelated_block}\n{trends_block}</script></html>"


# -- _extract_trends_payload finds the right block among several ----------
records = [_fake_record(f"trend {i}", 100 * i, 50, [4]) for i in range(60)]
records[5] = _fake_record("indo mim ipo gmp today", 50000, 1000, [3])
html = _build_fake_html(records)

payload = gt._extract_trends_payload(html)
check("finds the trends payload among multiple AF_initDataCallback blocks", len(payload) == 60)

# -- fetch_business_trends filters to category 3 and sorts by volume ------
with patch("urllib.request.urlopen") as mock_urlopen:
    mock_urlopen.return_value.__enter__ = lambda s: s
    mock_urlopen.return_value.read.return_value = html.encode("utf-8")
    business = gt.fetch_business_trends()

check("filters to only category-3 (Business & Finance) entries", len(business) == 1)
check("keeps the correct title", business[0]["title"] == "indo mim ipo gmp today" if business else False)
check("keeps volume/growth fields", business[0]["volume"] == 50000 and business[0]["growth_pct"] == 1000 if business else False)

# -- _extract_trends_payload returns [] on unparseable page ----------------
empty = gt._extract_trends_payload("<html>nothing here</html>")
check("returns [] when no matching block exists", empty == [])

# -- get_cached_business_trends: fresh fetch, then cache reuse -------------
with tempfile.TemporaryDirectory() as tmp_dir:
    cache_path = os.path.join(tmp_dir, "cache.json")
    with patch.object(gt, "BUSINESS_TRENDS_CACHE_PATH", cache_path):
        with patch.object(gt, "fetch_business_trends", return_value=[{"title": "a", "volume": 1}]) as mock_fetch:
            first = gt.get_cached_business_trends()
            check("first call fetches fresh data", mock_fetch.call_count == 1)
            check("first call returns fetched data", first == [{"title": "a", "volume": 1}])

            second = gt.get_cached_business_trends()
            check("second call within cache window does NOT re-fetch", mock_fetch.call_count == 1)
            check("second call returns cached data", second == [{"title": "a", "volume": 1}])

        # -- staleness triggers a re-fetch --------------------------------
        with open(cache_path, "r", encoding="utf-8") as f:
            cache = json.load(f)
        cache["fetched_at"] = (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat()
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(cache, f)

        with patch.object(gt, "fetch_business_trends", return_value=[{"title": "b", "volume": 2}]) as mock_fetch:
            third = gt.get_cached_business_trends()
            check("stale (>2h) cache triggers a re-fetch", mock_fetch.call_count == 1)
            check("stale refresh returns the new data", third == [{"title": "b", "volume": 2}])

        # -- a failed refresh falls back to the stale cache ---------------
        with open(cache_path, "r", encoding="utf-8") as f:
            cache = json.load(f)
        cache["fetched_at"] = (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat()
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(cache, f)

        with patch.object(gt, "fetch_business_trends", return_value=[]):
            fourth = gt.get_cached_business_trends()
            check("failed refresh falls back to stale cache, not []", fourth == [{"title": "b", "volume": 2}])

if failures:
    print(f"\n{len(failures)} FAILURE(S)")
    raise SystemExit(1)
print("\nAll cases passed.")
