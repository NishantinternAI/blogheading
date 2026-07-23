"""
tools/test_market_summary_source.py -- end-to-end live check of
sources/market_summary.py's fetch_morning_summary(), which is what
core/pipeline.py will actually call. Hits real NSE archives.

Run: python tools/test_market_summary_source.py
Expected: prints the built article dict's Blog_Title and a preview of
Blog_Content, plus "[PASS]" lines, nothing raises.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # repo root

from sources.market_summary import fetch_morning_summary


def check(label, condition):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label}")
    if not condition:
        raise AssertionError(label)


articles = fetch_morning_summary()
check("fetch_morning_summary returns a list", isinstance(articles, list))
check("fetch_morning_summary returns exactly one article", len(articles) == 1)

article = articles[0]
check("article has source=market_summary", article.get("source") == "market_summary")
check("article has a non-empty Blog_Title", bool(article.get("Blog_Title")))
check("article has a non-empty Blog_Content", bool(article.get("Blog_Content")))
check("article has a Blog_Links URL", article.get("Blog_Links", "").startswith("http"))
check("Blog_Content mentions Nifty 50", "Nifty 50" in article["Blog_Content"])
check("Blog_Content mentions Bank Nifty or Nifty Bank", (
    "Bank Nifty" in article["Blog_Content"] or "Nifty Bank" in article["Blog_Content"]
))

print(f"\nBlog_Title: {article['Blog_Title']}")
print(f"\nBlog_Content preview:\n{article['Blog_Content'][:600]}")
print("\nAll checks passed.")
