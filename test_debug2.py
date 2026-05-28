# test_debug2.py
# Runs full pipeline locally to test IPO image generation

import json
import os

# ── Reset pattern index to 0 so priority is tried first ──────
os.makedirs("output", exist_ok=True)
with open("output/pattern_index.json", "w") as f:
    json.dump({"current_index": 0, "last_type": "news"}, f)
print("✅ Pattern index reset to 0")

# ── Clear stacks so pipeline does a fresh fetch ───────────────
for fname in ["stack_priority.json", "stack_news.json", "stack_corporate.json"]:
    with open(f"output/{fname}", "w") as f:
        json.dump([], f)
print("✅ All stacks cleared")

print()
print("=" * 55)
print("  RUNNING FULL PIPELINE")
print("=" * 55)

from mergeall_engine import run_pipeline
results = run_pipeline(selected_country="India", category="finance")

print()
print("=" * 55)
print("  RESULT")
print("=" * 55)

if results:
    item = results[0]
    print(f"source_type  : {item.get('source_type', 'N/A')}")
    print(f"Blog_Title   : {item.get('Blog_Title', '')[:60]}")
    print()

    blog_img = item.get("blog_image", {})
    inner_img = item.get("blog_image_inner", {})
    insta_img = item.get("instagram_image", {})

    print(f"blog_image   : {blog_img.get('jpg', 'NOT FOUND')}")
    print(f"blog_inner   : {inner_img.get('jpg', 'NOT FOUND')}")
    print(f"instagram    : {insta_img.get('jpg', 'NOT FOUND')}")

    print()
    if item.get("source_type") == "priority":
        print("✅ IPO flow used — ipo_compositor.py")
        print("   Open the JPG files to check zone text positions")
    else:
        print("⚠️  News flow used — check why priority stack was empty")
else:
    print("❌ No results")