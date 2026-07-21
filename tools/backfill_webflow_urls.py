"""
backfill_webflow_urls.py
-------------------------
ONE-TIME repair script — NOT part of the ongoing scheduler pipeline.

Problem it solves:
    ~100+ blogs are already published on Webflow, but blogs_missing_keywords.json
    only ever stored the source news URL (Blog_Links), never the Webflow
    published URL. This script fills that gap by:

        1. Pulling every item from your Webflow CMS collection (title + slug)
        2. Matching each local blog record to a Webflow item by title
        3. Writing the resulting live URL back into blogs_missing_keywords.json

    Going forward, save_webflow_url() in webflow_poster.py captures this at
    publish-time automatically — this script only needs to run ONCE to
    catch up the historical backlog.

Usage:
    python backfill_webflow_urls.py --dry-run     # preview matches, no writes
    python backfill_webflow_urls.py               # actually write the file
"""

import os
import re
import json
import time
import argparse
import tempfile
import difflib

import requests

# ── Config — reuse the same values as webflow_poster.py ───────────────────
TOKEN         = os.environ.get("WEBFLOW_API_TOKEN", "")
COLLECTION_ID = os.environ.get("COLLECTION_ID", "64d4a2b7bcb8f41bb4083979")
SITE_DOMAIN   = os.environ.get("SITE_DOMAIN", "www.swastika.co.in")
BASE          = "https://api.webflow.com/v2"

BLOGS_JSON_PATH = os.environ.get(
    "BLOGS_JSON_PATH",
    r"D:\Blogheading\output\blogs_missing_keywords.json",
)

FUZZY_MATCH_CUTOFF = 0.90   # below this, a near-match is flagged, not auto-applied


def _headers():
    return {
        "Authorization": f"Bearer {TOKEN}",
        "Accept": "application/json",
    }


def _normalize_title(title: str) -> str:
    """Lowercase, strip punctuation and extra whitespace for comparison."""
    t = title.lower().strip()
    t = re.sub(r"[^\w\s]", "", t)
    t = re.sub(r"\s+", " ", t)
    return t


# ── Step 1: pull every item from Webflow, with pagination ─────────────────

def fetch_all_webflow_items(collection_id: str) -> list:
    """
    Returns a list of dicts: [{"title": ..., "slug": ...}, ...]
    Handles pagination — Webflow v2 returns up to 100 items per page.
    """
    items = []
    offset = 0
    limit = 100

    while True:
        r = requests.get(
            f"{BASE}/collections/{collection_id}/items",
            headers=_headers(),
            params={"limit": limit, "offset": offset},
            timeout=30,
        )
        if r.status_code >= 400:
            print(f"[BACKFILL] ERROR fetching items ({r.status_code}): {r.text[:200]}")
            break

        data = r.json()
        page_items = data.get("items", [])
        if not page_items:
            break

        for it in page_items:
            field_data = it.get("fieldData", {})
            title = field_data.get("name", "")
            slug = field_data.get("slug", "")
            if title and slug:
                items.append({"title": title, "slug": slug})

        print(f"[BACKFILL] Fetched {len(page_items)} items (offset={offset})")

        if len(page_items) < limit:
            break
        offset += limit
        time.sleep(0.3)  # be polite to the rate limit

    print(f"[BACKFILL] Total Webflow items fetched: {len(items)}")
    return items


# ── Step 2: build lookup table ─────────────────────────────────────────────

def build_title_lookup(webflow_items: list) -> dict:
    """{ normalized_title: slug }"""
    lookup = {}
    for item in webflow_items:
        norm = _normalize_title(item["title"])
        lookup[norm] = item["slug"]
    return lookup


# ── Step 3: match local blogs against the lookup ───────────────────────────

def backfill(blogs_path: str, dry_run: bool = False):
    with open(blogs_path, "r", encoding="utf-8") as f:
        blogs = json.load(f)

    webflow_items = fetch_all_webflow_items(COLLECTION_ID)
    lookup = build_title_lookup(webflow_items)
    all_norm_titles = list(lookup.keys())

    exact_matches = 0
    fuzzy_flagged = 0
    already_had_url = 0
    no_match = 0

    for blog in blogs:
        if blog.get("webflow_url"):
            already_had_url += 1
            continue

        gen_title = blog.get("blog", {}).get("Blog_Title") or blog.get("Blog_Title", "")
        norm_title = _normalize_title(gen_title)

        # 1. Exact match
        slug = lookup.get(norm_title)
        if slug:
            blog["webflow_url"] = f"https://{SITE_DOMAIN}/blog/{slug}"
            exact_matches += 1
            continue

        # 2. Fuzzy fallback — flag for manual review, do NOT auto-write
        close = difflib.get_close_matches(norm_title, all_norm_titles, n=1, cutoff=FUZZY_MATCH_CUTOFF)
        if close:
            matched_slug = lookup[close[0]]
            blog["webflow_url_suggested"] = f"https://{SITE_DOMAIN}/blog/{matched_slug}"
            blog["webflow_url_match_confidence"] = "fuzzy_needs_review"
            fuzzy_flagged += 1
            print(f"[BACKFILL] FUZZY (needs review): '{gen_title[:60]}' → slug '{matched_slug}'")
            continue

        # 3. No match at all
        blog["webflow_url"] = None
        no_match += 1
        print(f"[BACKFILL] NO MATCH: '{gen_title[:60]}'")

    print("\n[BACKFILL] ── Summary ──────────────────────────")
    print(f"  Already had URL:   {already_had_url}")
    print(f"  Exact matches:     {exact_matches}")
    print(f"  Fuzzy — review:    {fuzzy_flagged}")
    print(f"  No match:          {no_match}")
    print(f"  Total blogs:       {len(blogs)}")

    if dry_run:
        print("\n[BACKFILL] Dry run — no changes written to disk.")
        return blogs

    # Atomic write — temp file then replace
    dir_name = os.path.dirname(os.path.abspath(blogs_path))
    with tempfile.NamedTemporaryFile("w", dir=dir_name, delete=False, suffix=".tmp", encoding="utf-8") as tmp:
        json.dump(blogs, tmp, ensure_ascii=False, indent=2)
        tmp_path = tmp.name
    os.replace(tmp_path, blogs_path)
    print(f"\n[BACKFILL] Saved updates to {blogs_path}")

    return blogs


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backfill Webflow published URLs onto local blog records.")
    parser.add_argument("--dry-run", action="store_true", help="Preview matches without writing to disk")
    parser.add_argument("--path", default=BLOGS_JSON_PATH, help="Path to blogs_missing_keywords.json")
    args = parser.parse_args()

    if not TOKEN:
        raise SystemExit("WEBFLOW_API_TOKEN not set — export it before running this script.")

    backfill(args.path, dry_run=args.dry_run)