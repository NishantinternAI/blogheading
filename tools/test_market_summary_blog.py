"""
tools/test_market_summary_blog.py -- exercises the full
fetch_morning_summary() -> generate_market_summary_blog() path for one
run, without touching the live stacks/output files (mirrors the
existing tools/test_ipo_blog.py pattern).

Run: python tools/test_market_summary_blog.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # repo root

from sources.market_summary import fetch_morning_summary
from generators.blog_generator import generate_market_summary_blog

print("=" * 60)
print("  Market Summary Blog Generation Test")
print("=" * 60)

articles = fetch_morning_summary()
assert articles, "fetch_morning_summary() returned no article -- check tools/test_market_summary_source.py first"
item = articles[0]
print(f"\nSource item Blog_Title: {item['Blog_Title']}")

result = generate_market_summary_blog(item)
assert result, "generate_market_summary_blog() returned {} -- check for a JSON parse failure above"

print("\nBlog Title :", result.get("Blog_Title"))
print("Meta Title :", result.get("Meta_Title"))
print("Meta Desc  :", result.get("Meta_Description"))
print("TLDR       :", result.get("TLDR"))
print("\nBlog_Content preview:\n", (result.get("Blog_Content") or "")[:800])
print("\n[PASS] generate_market_summary_blog produced a non-empty result")
