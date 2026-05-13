import os
import base64
import re
import unicodedata
from openai import OpenAI

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


# ── Build prompt ──────────────────────────────────────────────
def build_image_prompt(blog_title: str, blog_content: str, image_type: str) -> str:
    content_preview = blog_content if blog_content else ""

    if image_type in ("blog_outer", "blog_inner"):
        return f"""
Create a professional stock market and financial news image.

Topic: {blog_title}
Context: {content_preview}

Style requirements:
- Professional financial news look
- Modern, clean, corporate feel
- NO text overlay on the image
- NO watermarks
- High quality, sharp details
- Suitable for a financial blog header
"""
    else:  # instagram
        return f"""
Create a bold, eye-catching square financial news image for Instagram.

Topic: {blog_title}
Context: {content_preview}

Style requirements:
- Stock market / trading themed
- Modern and dynamic composition
- Square format optimized for Instagram
- NO text overlay on the image
- NO watermarks
- High contrast, vibrant colors
- Professional financial news aesthetic
"""


# ── Save image in all required formats ───────────────────────
def save_image_formats(image_bytes: bytes, paths: dict, image_type: str):
    from PIL import Image
    import io

    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")

    saved = {}

    if image_type == "blog_outer":
        # Thumbnail outer → 640x480
        resized = img.resize((640, 480), Image.LANCZOS)
        os.makedirs(os.path.dirname(paths["jpg"]),  exist_ok=True)
        os.makedirs(os.path.dirname(paths["webp"]), exist_ok=True)
        resized.save(paths["jpg"],  "JPEG")
        resized.save(paths["webp"], "WEBP")
        print(f"[AI IMAGE] blog_outer JPG  → {paths['jpg']}")
        print(f"[AI IMAGE] blog_outer WebP → {paths['webp']}")
        saved = {"jpg": paths["jpg"], "webp": paths["webp"]}

    elif image_type == "blog_inner":
        # Thumbnail inner → 1920x490
        resized = img.resize((1920, 490), Image.LANCZOS)
        os.makedirs(os.path.dirname(paths["jpg"]),  exist_ok=True)
        os.makedirs(os.path.dirname(paths["webp"]), exist_ok=True)
        resized.save(paths["jpg"],  "JPEG")
        resized.save(paths["webp"], "WEBP")
        print(f"[AI IMAGE] blog_inner JPG  → {paths['jpg']}")
        print(f"[AI IMAGE] blog_inner WebP → {paths['webp']}")
        saved = {"jpg": paths["jpg"], "webp": paths["webp"]}

    elif image_type == "instagram":
        # Instagram → 1080x1080
        resized = img.resize((1080, 1080), Image.LANCZOS)
        os.makedirs(os.path.dirname(paths["jpg"]),  exist_ok=True)
        os.makedirs(os.path.dirname(paths["webp"]), exist_ok=True)
        resized.save(paths["jpg"],  "JPEG", quality=98, subsampling=0)
        resized.save(paths["webp"], "WEBP", quality=92, method=6)
        print(f"[AI IMAGE] instagram JPG  → {paths['jpg']}")
        print(f"[AI IMAGE] instagram WebP → {paths['webp']}")
        saved = {"jpg": paths["jpg"], "webp": paths["webp"]}

    return saved


# ── Single API call → reuse bytes for blog_outer + blog_inner ─
def generate_ai_image(
    blog_title:        str,
    blog_content:      str,
    blog_outer_paths:  dict,
    blog_inner_paths:  dict,
    instagram_paths:   dict,
    quality:           str = "medium"
) -> dict:
    """
    Makes 2 API calls:
      Call 1 → blog image (reused for outer 640x480 + inner 1920x490)
      Call 2 → instagram image (1080x1080)

    Returns:
    {
      "blog_outer":  {"jpg": "...", "webp": "..."},
      "blog_inner":  {"jpg": "...", "webp": "..."},
      "instagram":   {"jpg": "...", "webp": "..."}
    }
    """

    # ── Call 1 — Blog image (reuse for outer + inner) ─────────
    print(f"[AI IMAGE] Generating blog image: {blog_title[:50]}...")

    blog_prompt  = build_image_prompt(blog_title, blog_content, "blog_outer")
    blog_response = client.images.generate(
        model   = "gpt-image-1",
        prompt  = blog_prompt,
        size    = "1536x1024",   # landscape — best for blog
        quality = quality,
        n       = 1,
    )
    blog_bytes = base64.b64decode(blog_response.data[0].b64_json)

    # Save outer (640x480) from same blog bytes
    outer_saved = save_image_formats(blog_bytes, blog_outer_paths, "blog_outer")

    # Save inner (1920x490) from same blog bytes
    inner_saved = save_image_formats(blog_bytes, blog_inner_paths, "blog_inner")

    # ── Call 2 — Instagram image ──────────────────────────────
    print(f"[AI IMAGE] Generating instagram image: {blog_title[:50]}...")

    insta_prompt   = build_image_prompt(blog_title, blog_content, "instagram")
    insta_response = client.images.generate(
        model   = "gpt-image-1",
        prompt  = insta_prompt,
        size    = "1024x1024",   # square — best for instagram
        quality = quality,
        n       = 1,
    )
    insta_bytes  = base64.b64decode(insta_response.data[0].b64_json)
    insta_saved  = save_image_formats(insta_bytes, instagram_paths, "instagram")

    return {
        "blog_outer": outer_saved,
        "blog_inner": inner_saved,
        "instagram":  insta_saved
    }