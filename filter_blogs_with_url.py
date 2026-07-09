"""
filter_blogs_with_url.py
--------------------------
Keeps ONLY blogs that have a real, confirmed "webflow_url" inside
blogs_missing_keywords.json. Removes any blog where webflow_url is
null/missing (i.e. the "no match" and unconverted "fuzzy" results
from backfill_webflow_urls.py).

SAFETY: takes an automatic timestamped backup of the original file
before overwriting anything, since this operation is destructive —
removed blog records (content, keywords, images, etc.) are gone from
this file once saved.

Usage:
    python filter_blogs_with_url.py --path "D:\\Blogheading\\output\\blogs_missing_keywords.json"

    # Preview only, no changes written:
    python filter_blogs_with_url.py --path "..." --dry-run
"""

import os
import json
import shutil
import argparse
import tempfile
from datetime import datetime


def filter_blogs(path: str, dry_run: bool = False):
    with open(path, "r", encoding="utf-8") as f:
        blogs = json.load(f)

    total = len(blogs)
    kept = [b for b in blogs if b.get("webflow_url")]
    removed = [b for b in blogs if not b.get("webflow_url")]

    print(f"[FILTER] Total blogs before: {total}")
    print(f"[FILTER] Blogs with webflow_url (kept):    {len(kept)}")
    print(f"[FILTER] Blogs without webflow_url (removed): {len(removed)}")

    if removed:
        print("\n[FILTER] Titles being removed:")
        for b in removed:
            title = b.get("blog", {}).get("Blog_Title") or b.get("Blog_Title", "(no title)")
            reason = "fuzzy_suggested_not_confirmed" if b.get("webflow_url_suggested") else "no_match"
            print(f"  - [{reason}] {title[:70]}")

    if dry_run:
        print("\n[FILTER] Dry run — no changes written, no backup taken.")
        return kept, removed

    # ── Backup original file first — non-negotiable for a destructive op ──
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{path}.backup_{timestamp}.json"
    shutil.copy2(path, backup_path)
    print(f"\n[FILTER] Backup saved to: {backup_path}")

    # ── Atomic write of the filtered list ──────────────────────────────────
    dir_name = os.path.dirname(os.path.abspath(path))
    with tempfile.NamedTemporaryFile("w", dir=dir_name, delete=False, suffix=".tmp", encoding="utf-8") as tmp:
        json.dump(kept, tmp, ensure_ascii=False, indent=2)
        tmp_path = tmp.name
    os.replace(tmp_path, path)

    print(f"[FILTER] Saved {len(kept)} blogs to: {path}")
    print(f"[FILTER] If you need any of the {len(removed)} removed blogs back, restore from the backup file above.")

    return kept, removed


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", required=True, help="Path to blogs_missing_keywords.json")
    parser.add_argument("--dry-run", action="store_true", help="Preview only, no changes written")
    args = parser.parse_args()

    filter_blogs(args.path, dry_run=args.dry_run)