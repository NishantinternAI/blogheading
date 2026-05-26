# migrate_output.py

import json
import os
import re

def migrate_paths(old_path: str, prefix: str) -> dict:
    """
    Convert old flat path to new jpg/webp subfolder format.
    Also fixes prefix (blog_ → blog_outer_, insta_ stays insta_)
    """
    if not old_path:
        return {"jpg": "", "webp": ""}

    # Normalize to forward slashes
    path = old_path.replace("\\", "/")

    # Extract filename only
    filename = os.path.basename(path)

    # Remove old prefix and add new prefix
    # e.g. blog_AWL_Agri... → blog_outer_AWL_Agri...
    for old_prefix in ["blog_outer_", "blog_inner_", "blog_", "insta_"]:
        if filename.startswith(old_prefix):
            filename = filename[len(old_prefix):]
            break

    # Force jpg extension for jpg path
    base = os.path.splitext(filename)[0]

    jpg_path  = f"D:/Blogheading/output_images/jpg_images/{prefix}{base}.jpg"
    webp_path = f"D:/Blogheading/output_images/webp_images/{prefix}{base}.webp"

    return {"jpg": jpg_path, "webp": webp_path}


def migrate_item(item: dict) -> dict:
    """Convert single blog item from old format to new format."""

    # ── Blog image outer ─────────────────────────────────────
    old_blog = item.get("blog_image") or item.get("blog_image_webp", {})
    old_path = old_blog.get("jpg", "") if isinstance(old_blog, dict) else old_blog

    item["blog_image_outer"] = migrate_paths(old_path, "blog_outer_")

    # ── Blog image inner — copy from outer (same template) ───
    item["blog_image_inner"] = migrate_paths(old_path, "blog_inner_")

    # ── Instagram image ───────────────────────────────────────
    old_insta = item.get("instagram_image", {})
    old_insta_path = old_insta.get("jpg", "") if isinstance(old_insta, dict) else old_insta

    item["instagram_image"] = migrate_paths(old_insta_path, "insta_")

    # ── Remove old fields ─────────────────────────────────────
    item.pop("blog_image",      None)
    item.pop("blog_image_webp", None)
    item.pop("instagram_image_webp", None)

    return item


def migrate_output_json(
    input_file:  str = "output/output.json",
    output_file: str = "output/output_migrated.json"
):
    print(f"Reading: {input_file}")

    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"Total items: {len(data)}")

    migrated = []
    for i, item in enumerate(data):
        migrated_item = migrate_item(item)
        migrated.append(migrated_item)
        print(f"[{i+1}/{len(data)}] Migrated: {item.get('Blog_Title', '')[:50]}")

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(migrated, f, indent=4, ensure_ascii=False)

    print(f"\nDone! Saved to: {output_file}")
    print(f"Total migrated: {len(migrated)}")


if __name__ == "__main__":
    migrate_output_json(
        input_file  = "output/output.json",
        output_file = "output/output_migrated.json"
    )