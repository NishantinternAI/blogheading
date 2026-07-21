"""
enrich_missing_keywords.py
----------------------------
Finds blogs in blogs_missing_keywords.json where primary_keyword and/or
secondary_keywords are still plain strings (never ran through Google
Keyword Planner), and enriches ONLY those raw entries using the existing
get_keyword_volumes() from keyword_volume.py.

Already-enriched entries (dicts with real volume) are left untouched —
this never re-queries or overwrites good data.

SAFETY:
    - Backs up the original file before any writes
    - Saves progress every CHECKPOINT_EVERY blogs, not just at the end,
      so a crash or API rate-limit mid-run doesn't lose completed work
    - Wraps each API call in try/except — one failing blog doesn't stop
      the whole batch, it's just logged and skipped for a retry later

Usage:
    python enrich_missing_keywords.py --path "D:\\Blogheading\\output\\blogs_missing_keywords.json"
    python enrich_missing_keywords.py --path "..." --dry-run   # preview only, no API calls, no writes
"""

import os
import sys
import json
import time
import shutil
import argparse
import tempfile
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # repo root, for keyword_researcher
from keyword_researcher import get_keyword_volumes

CHECKPOINT_EVERY = 10
DELAY_BETWEEN_CALLS = 1.0  # seconds — be gentle with the Keyword Planner API


def needs_enrichment(kw):
    """A keyword needs enrichment if it's a plain string, not the enriched dict."""
    return not isinstance(kw, dict)


def enrich_blog(blog):
    """
    Enriches only the raw (string) keyword fields on a single blog.
    Returns (blog, was_changed, error_or_None).
    """
    primary = blog.get("primary_keyword", "")
    secondary_list = blog.get("secondary_keywords", [])

    raw_primary_text = primary if needs_enrichment(primary) and primary else None
    raw_secondary_texts = [s for s in secondary_list if needs_enrichment(s) and s]

    if not raw_primary_text and not raw_secondary_texts:
        return blog, False, None  # already fully enriched, nothing to do

    try:
        result = get_keyword_volumes(
            primary=raw_primary_text or "",
            secondary=raw_secondary_texts,
        )
    except Exception as e:
        return blog, False, str(e)

    if raw_primary_text and result.get("primary_keyword"):
        blog["primary_keyword"] = result["primary_keyword"]

    if raw_secondary_texts:
        enriched_map = {
            e["original"].strip().lower(): e
            for e in result.get("secondary_keywords", [])
        }
        new_secondary = []
        for s in secondary_list:
            if needs_enrichment(s) and s:
                key = s.strip().lower()
                new_secondary.append(
                    enriched_map.get(key, {
                        "original": s,
                        "google_keyword": s.lower(),
                        "volume": 0,
                        "competition": "UNSPECIFIED",
                    })
                )
            else:
                new_secondary.append(s)  # already enriched — untouched
        blog["secondary_keywords"] = new_secondary

    return blog, True, None


def save_progress(blogs, path):
    """Atomic write — temp file then replace, same pattern as the rest of the pipeline."""
    dir_name = os.path.dirname(os.path.abspath(path))
    with tempfile.NamedTemporaryFile("w", dir=dir_name, delete=False, suffix=".tmp", encoding="utf-8") as tmp:
        json.dump(blogs, tmp, ensure_ascii=False, indent=2)
        tmp_path = tmp.name
    os.replace(tmp_path, path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", required=True, help="Path to blogs_missing_keywords.json")
    parser.add_argument("--dry-run", action="store_true", help="Preview what needs enrichment, no API calls, no writes")
    args = parser.parse_args()

    with open(args.path, "r", encoding="utf-8") as f:
        blogs = json.load(f)

    to_enrich = [
        b for b in blogs
        if needs_enrichment(b.get("primary_keyword", ""))
        or any(needs_enrichment(s) for s in b.get("secondary_keywords", []))
    ]

    print(f"[ENRICH] Total blogs: {len(blogs)}")
    print(f"[ENRICH] Blogs needing enrichment: {len(to_enrich)}")

    if args.dry_run:
        print("\n[ENRICH] Dry run — titles that would be enriched:")
        for b in to_enrich:
            title = b.get("blog", {}).get("Blog_Title") or b.get("Blog_Title", "")
            print(f"  - {title[:70]}")
        print("\n[ENRICH] Dry run — no API calls made, no changes written.")
        return

    if not to_enrich:
        print("[ENRICH] Nothing to do — all blogs already enriched.")
        return

    # ── Backup before making any changes ────────────────────────────────
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{args.path}.backup_{timestamp}.json"
    shutil.copy2(args.path, backup_path)
    print(f"[ENRICH] Backup saved to: {backup_path}")

    succeeded = 0
    failed = 0

    for i, blog in enumerate(to_enrich, 1):
        title = blog.get("blog", {}).get("Blog_Title") or blog.get("Blog_Title", "")
        updated_blog, changed, error = enrich_blog(blog)

        if error:
            print(f"[ENRICH] [{i}/{len(to_enrich)}] FAILED: '{title[:60]}' — {error}")
            failed += 1
        elif changed:
            print(f"[ENRICH] [{i}/{len(to_enrich)}] OK: '{title[:60]}'")
            succeeded += 1

        if i % CHECKPOINT_EVERY == 0:
            save_progress(blogs, args.path)
            print(f"[ENRICH] --- Checkpoint saved at {i}/{len(to_enrich)} ---")

        time.sleep(DELAY_BETWEEN_CALLS)

    # Final save, in case the last batch wasn't an exact multiple of CHECKPOINT_EVERY
    save_progress(blogs, args.path)

    print("\n[ENRICH] ── Summary ──────────────────────────")
    print(f"  Enriched successfully: {succeeded}")
    print(f"  Failed (kept as-is):   {failed}")
    print(f"  Saved to: {args.path}")
    if failed:
        print(f"  Re-run the same command again to retry the {failed} failed blogs.")


if __name__ == "__main__":
    main()