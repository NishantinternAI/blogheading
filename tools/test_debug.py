# import requests

# TOKEN = "cc7855e28203d7e1c2aadb5dc01e5cb0b730407497c61fb3a99a77d8be0b6db3"

# headers = {
#     "Authorization": f"Bearer {TOKEN}",
#     "Accept": "application/json"
# }

# # Blog Post Categories collection id
# CAT_COLLECTION_ID = "64d4a3104a337a3283ef9437"

# print("\n=== Blog Post Categories ===\n")
# r = requests.get(
#     f"https://api.webflow.com/v2/collections/{CAT_COLLECTION_ID}/items",
#     headers=headers
# )
# items = r.json().get("items", [])
# for item in items:
#     print(f"item_id: {item.get('id')} | name: {item.get('fieldData', {}).get('name')}")




"""
fix_oyo_blog.py
---------------
One-time script to fix double <li> nesting in the Oyo IPO blog
that was published with broken Key Takeaways HTML.

Run once from D:\Blogheading:
    python fix_oyo_blog.py
"""

import re
import requests

TOKEN         = "cc7855e28203d7e1c2aadb5dc01e5cb0b730407497c61fb3a99a77d8be0b6db3"
COLLECTION_ID = "64d4a2b7bcb8f41bb4083979"
ITEM_ID       = "6a45fb0ea683fc7471a9a2e6"   # Oyo IPO blog item_id
BASE          = "https://api.webflow.com/v2"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept":        "application/json",
    "Content-Type":  "application/json",
}

# ── Step 1: Fetch current content ─────────────────────────────────────────
print("[FIX] Fetching current blog content...")
r = requests.get(
    f"{BASE}/collections/{COLLECTION_ID}/items/{ITEM_ID}",
    headers=headers,
    timeout=30,
)
if r.status_code >= 400:
    print(f"[FIX] ❌ Failed to fetch: {r.status_code} — {r.text[:200]}")
    exit(1)

item    = r.json()
content = item.get("fieldData", {}).get("content", "")
print(f"[FIX] Content fetched — {len(content)} characters")

# ── Step 2: Fix double <li> tags ───────────────────────────────────────────
print("[FIX] Fixing double <li> nesting...")
before = content.count("<li><li>") + content.count("</li></li>")

content = re.sub(r"<li>\s*<li>",   "<li>",   content)
content = re.sub(r"</li>\s*</li>", "</li>",  content)

after = content.count("<li><li>") + content.count("</li></li>")
print(f"[FIX] Fixed {before} instances → {after} remaining")

# Preview the Key Takeaways section
kt_match = re.search(r"Key Takeaways.*?</ul>", content, re.DOTALL | re.IGNORECASE)
if kt_match:
    print(f"\n[FIX] Key Takeaways preview:\n{kt_match.group(0)[:400]}\n")

# ── Step 3: Patch the item ─────────────────────────────────────────────────
print("[FIX] Patching Webflow CMS item...")
patch = requests.patch(
    f"{BASE}/collections/{COLLECTION_ID}/items/{ITEM_ID}",
    headers=headers,
    json={"fieldData": {"content": content}},
    timeout=30,
)
if patch.status_code >= 400:
    print(f"[FIX] ❌ Patch failed: {patch.status_code} — {patch.text[:200]}")
    exit(1)
print(f"[FIX] ✅ Patch successful: {patch.status_code}")

# ── Step 4: Republish ──────────────────────────────────────────────────────
print("[FIX] Republishing blog live...")
pub = requests.post(
    f"{BASE}/collections/{COLLECTION_ID}/items/publish",
    headers=headers,
    json={"itemIds": [ITEM_ID]},
    timeout=30,
)
if pub.status_code in (200, 201, 202, 204):
    print(f"[FIX] ✅ Published live successfully")
else:
    print(f"[FIX] ⚠️  Publish status: {pub.status_code} — {pub.text[:200]}")

print("\n[FIX] Done — check the blog on Webflow to confirm ✅")