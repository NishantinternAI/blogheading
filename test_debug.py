# test_debug.py
import json
import os

# ── Check 1: Is Hexagon already in output.json? ───────────────
print("=== Check 1: Already published? ===")
filepath = "output/output.json"
if os.path.exists(filepath):
    with open(filepath, encoding="utf-8") as f:
        data = json.load(f)
    titles = [item.get("Blog_Title", "") for item in data]
    hexagon_found = [t for t in titles if "hexagon" in t.lower()]
    if hexagon_found:
        print("YES — found in output.json:")
        for t in hexagon_found:
            print(f"  {t}")
    else:
        print("NO — not in output.json")
else:
    print("output.json does not exist")

# ── Check 2: Does filter keep IPO articles? ───────────────────
print()
print("=== Check 2: Test filter directly ===")

from RSS.ipo import fetch_nse_ipo
from utils.combined_filter import filter_by_country_and_category

articles = fetch_nse_ipo(top_n=1)
print(f"IPO articles before filter: {len(articles)}")

if articles:
    print(f"  Title      : {articles[0]['Blog_Title']}")
    print(f"  source     : {articles[0]['source']}")
    print(f"  price_band : {articles[0].get('price_band', 'N/A')}")
    print(f"  open_date  : {articles[0].get('open_date', 'N/A')}")

    filtered, source = filter_by_country_and_category(
        articles, "India", "finance"
    )
    print(f"\nIPO articles after filter : {len(filtered)}")

    if filtered:
        print("  Result: ✅ Filter KEPT IPO article")
    else:
        print("  Result: ❌ Filter REMOVED IPO article — this is the problem")