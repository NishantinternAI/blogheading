"""
webflow_poster.py
-----------------
Sync Webflow CMS poster — called by scheduler.py after each pipeline run.
Uses only `requests` (already in requirements.txt), no extra deps.

Also imported by blog_post_mcp.py so the MCP server and the scheduler
share the same logic.
"""

import os
import re
import json
import hashlib
import base64
from pathlib import Path

import requests

TOKEN         = os.environ.get("WEBFLOW_API_TOKEN", "")
SITE_ID       = os.environ.get("SITE_ID", "649a7bd9d30be4bdd61239e5")
COLLECTION_ID = os.environ.get("COLLECTION_ID", "64d4a2b7bcb8f41bb4083979")
BASE          = "https://api.webflow.com/v2"

IMAGE_JPG_DIR = os.environ.get(
    "IMAGE_JPG_DIR",
    "/app/output_images/jpg_images",   # default inside Docker
)


# ── Helpers ────────────────────────────────────────────────────────────────

def _headers():
    return {
        "Authorization": f"Bearer {TOKEN}",
        "Accept":        "application/json",
        "Content-Type":  "application/json",
    }


def _make_slug(title: str) -> str:
    s = title.lower()
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"\s+", "-", s.strip())
    s = re.sub(r"-+", "-", s)
    return s[:80]


def _add_h2_spacing(html: str) -> str:
    return re.sub(r"</h2>", "</h2><p>&nbsp;</p><p>&nbsp;</p>", html)


def _faq_script(faq_schema: dict) -> str:
    return (
        '<script type="application/ld+json">'
        + json.dumps(faq_schema, ensure_ascii=False)
        + "</script>"
    )


def _md5_b64(path: Path) -> str:
    return base64.b64encode(hashlib.md5(path.read_bytes()).digest()).decode()


# ── Image upload ───────────────────────────────────────────────────────────

def upload_image(file_path: Path) -> str | None:
    """
    Upload a JPEG to Webflow assets.
    Returns CDN URL on success, None on failure.
    """
    if not TOKEN or not file_path.exists():
        return None

    try:
        # Step 1 — get S3 credentials
        r = requests.post(
            f"{BASE}/sites/{SITE_ID}/assets",
            headers=_headers(),
            json={"fileName": file_path.name, "fileHash": _md5_b64(file_path)},
            timeout=30,
        )
        if r.status_code >= 400:
            print(f"[WEBFLOW] Asset pre-sign failed ({r.status_code}): {r.text[:150]}")
            return None

        data    = r.json()
        details = data.get("uploadDetails", {})
        bucket  = details.pop("bucket", "webflow-prod-assets")
        s3_key  = details.get("key", "")

        # Step 2 — multipart POST to S3
        file_bytes = file_path.read_bytes()
        fields = {k: (None, v) for k, v in details.items()}
        fields["file"] = (file_path.name, file_bytes, "image/jpeg")

        s3 = requests.post(
            f"https://{bucket}.s3.amazonaws.com/",
            files=fields,
            timeout=60,
        )
        if s3.status_code not in (200, 201, 204):
            print(f"[WEBFLOW] S3 upload failed ({s3.status_code})")
            return None

        return f"https://uploads-ssl.webflow.com/{s3_key}"

    except Exception as e:
        print(f"[WEBFLOW] Image upload error: {e}")
        return None


# ── Draft creation ─────────────────────────────────────────────────────────

def post_entry_as_draft(entry: dict, image_dir: str = "") -> dict:
    """
    Post one pipeline output entry as a Webflow CMS draft.

    `entry` is a single item from output.json — must have a `blog` key.
    Returns {"item_id": ..., "name": ..., "isDraft": True} or {"error": ...}
    """
    if not TOKEN:
        return {"error": "WEBFLOW_API_TOKEN not set"}

    blog       = entry.get("blog", {})
    name       = blog.get("Blog_Title", entry.get("Blog_Title", "Untitled"))
    slug       = _make_slug(name)
    content    = _add_h2_spacing(blog.get("Blog_Content", ""))
    meta_title = blog.get("Meta_Title", name)
    meta_desc  = blog.get("Meta_Description", "")
    faq_schema = blog.get("FAQ_Schema", {})
    faq_html   = _faq_script(faq_schema) if faq_schema else ""

    img_dir = image_dir or IMAGE_JPG_DIR

    # Upload thumbnail + cover images
    thumb_url = cover_url = None
    if img_dir:
        def _local(server_path):
            return Path(img_dir) / Path(server_path).name

        thumb_server = entry.get("blog_image", {}).get("jpg", "")
        cover_server = entry.get("blog_image_inner", {}).get("jpg", "")

        if thumb_server:
            thumb_url = upload_image(_local(thumb_server))
            if thumb_url:
                print(f"[WEBFLOW] Thumbnail uploaded: {Path(thumb_server).name}")

        if cover_server:
            cover_url = upload_image(_local(cover_server))
            if cover_url:
                print(f"[WEBFLOW] Cover uploaded:     {Path(cover_server).name}")

    field_data: dict = {
        "name":                name,
        "slug":                slug,
        "content":             content,
        "title-tag-seo":       meta_title,
        "meta-description-seo": meta_desc,
    }
    if faq_html:
        field_data["faq-schema-script-2"] = faq_html
    if thumb_url:
        field_data["blog-thumbnail-image"] = {"url": thumb_url, "alt": name}
    if cover_url:
        field_data["blog-cover-image"] = {"url": cover_url, "alt": name}

    payload = {
        "isArchived": False,
        "isDraft":    True,
        "fieldData":  field_data,
    }

    try:
        r = requests.post(
            f"{BASE}/collections/{COLLECTION_ID}/items",
            headers=_headers(),
            json=payload,
            timeout=30,
        )
        data = r.json()
        if r.status_code >= 400:
            return {"error": True, "status": r.status_code, "detail": data}

        return {
            "item_id": data.get("id"),
            "name":    data.get("fieldData", {}).get("name", name),
            "slug":    data.get("fieldData", {}).get("slug", slug),
            "isDraft": data.get("isDraft", True),
        }
    except Exception as e:
        return {"error": str(e)}


def post_results_as_drafts(results: list, image_dir: str = "") -> list:
    """
    Post a list of pipeline result entries as Webflow drafts.
    Called by scheduler.py after run_pipeline() returns.
    """
    posted = []
    for entry in results:
        name = entry.get("blog", {}).get("Blog_Title", entry.get("Blog_Title", "?"))
        print(f"[WEBFLOW] Posting draft: {name[:60]}")
        result = post_entry_as_draft(entry, image_dir)
        if result.get("error"):
            print(f"[WEBFLOW] FAILED: {result}")
        else:
            print(f"[WEBFLOW] Draft saved — item_id={result.get('item_id')}")
        posted.append(result)
    return posted
