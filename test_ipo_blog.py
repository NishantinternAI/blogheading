# test_ipo_blog.py
# Run: python test_ipo_blog.py
# Tests IPO scraping + blog generation for one company

import json
from RSS.ipo import (
    _scrape_ipo_details,
    _build_blog_title,
    _build_blog_content,
    _validate_ipo_article,
)
from AI_GEN.blog_generator import generate_ipo_blog

# ── Change this to any currently active IPO ──────────────────
TEST_COMPANY = "Hexagon Nutrition IPO Details"   # ← swap to a live IPO name

print("=" * 60)
print(f"  IPO Blog Generation Test: {TEST_COMPANY}")
print("=" * 60)

# Step 1: Scrape IPO details
print(f"\n[1] Scraping IPO details...")
extra = _scrape_ipo_details(TEST_COMPANY)

if not extra:
    print("❌ No data scraped. Check company name or source availability.")
    exit()

print(f"\n    data_source  : {extra.get('data_source', 'N/A')}")
print(f"    open_date    : {extra.get('open_date',   'N/A')}")
print(f"    close_date   : {extra.get('close_date',  'N/A')}")
print(f"    price_band   : {extra.get('price_band',  'N/A')}")
print(f"    lot_size     : {extra.get('lot_size',     'N/A')}")
print(f"    listing_date : {extra.get('listing_date','N/A')}")
print(f"    gmp          : {extra.get('gmp',         'N/A')}")

# Step 2: Build article dict (same structure as main pipeline)
nse_stub = {
    "status":      "Active",
    "open_date":   extra.get("open_date",  ""),
    "close_date":  extra.get("close_date", ""),
    "issue_price": extra.get("price_band", ""),
    "issue_size":  extra.get("issue_size", ""),
    "issue_type":  extra.get("issue_type", "Book Built Issue"),
}

article = {
    "Blog_Title":   _build_blog_title(TEST_COMPANY, nse_stub, extra),
    "Blog_Content": _build_blog_content(TEST_COMPANY, nse_stub, extra),
    "source":       "nse_ipo",
    "company":      TEST_COMPANY,
}

print(f"\n[2] Source title  : {article['Blog_Title']}")
print(f"\n[2] Source content preview:")
print(article["Blog_Content"][:400])

# Step 3: Validate
print(f"\n[3] Validating...")
valid = _validate_ipo_article(article, TEST_COMPANY)
print(f"    Valid: {valid}")

# Step 4: Generate blog
print(f"\n[4] Generating blog with LLM...")
try:
    blog = generate_ipo_blog(article)

    print(f"\n{'='*60}")
    print(f"  GENERATED BLOG")
    print(f"{'='*60}")
    print(f"\nBlog_Title      : {blog.get('Blog_Title','')}")
    print(f"Meta_Title      : {blog.get('Meta_Title','')} ({len(blog.get('Meta_Title',''))} chars)")
    print(f"Meta_Description: {blog.get('Meta_Description','')} ({len(blog.get('Meta_Description',''))} chars)")
    print(f"\nTLDR:")
    for i, t in enumerate(blog.get("TLDR", []), 1):
        print(f"  {i}. {t}")

    content = blog.get("Blog_Content", "")
    print(f"\nBlog_Content ({len(content)} chars):")
    print(content[:800])
    print("..." if len(content) > 800 else "")

    # Check for required sections
    print(f"\n{'='*60}")
    print("  SECTION CHECK")
    print(f"{'='*60}")
    checks = {
        "<h1>"           : "H1 title",
        "<h2>TLDR</h2>"  : "TLDR section",
        "<h2>FAQ</h2>"   : "FAQ section",
        "<h2>Conclusion" : "Conclusion section",
        "Swastika"       : "Swastika CTA",
        "<table"         : "Data table (optional)",
    }
    for tag, label in checks.items():
        found = tag.lower() in content.lower()
        icon  = "✅" if found else ("⚠️ " if "optional" in label else "❌")
        print(f"  {icon} {label}")

    # Save output for inspection
    output_path = f"test_ipo_output_{TEST_COMPANY.replace(' ','_')}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({
            "source_article": article,
            "blog":           blog,
        }, f, ensure_ascii=False, indent=2)
    print(f"\n💾 Full output saved: {output_path}")

except Exception as e:
    import traceback
    print(f"❌ Blog generation failed: {e}")
    traceback.print_exc()