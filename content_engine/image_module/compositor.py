"""
content_engine/image_module/compositor.py -- Non-IPO blog image compositor.

Builds the blog-outer / blog-inner / Instagram images for regular
(non-IPO) articles: picks a template, overlays the extracted headline
text, and exports both a JPG and a WebP version. Used from
pipeline.py's run_pipeline() whenever USE_AI_IMAGES is False and
the article isn't an IPO (IPO articles always go through
ipo_compositor.py instead, regardless of USE_AI_IMAGES -- see
pipeline.py's image-branch comments).
"""

from PIL import Image, ImageDraw, ImageFont
import os

from content_engine.image_module.base_compositor import BaseImageCompositor

# --- Base Path ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# FONTS / get_font moved to base_compositor.BaseImageCompositor (shared
# with ipo_compositor.py, which had a byte-identical copy of both).
FONTS    = BaseImageCompositor.FONTS
get_font = BaseImageCompositor.get_font


def wrap_text_by_pixels(text, font, max_width, draw):
    """
    Word-wrap text to fit within max_width pixels for the given font.

    Args:
        text: text to wrap.
        font: ImageFont instance used to measure rendered width.
        max_width: max line width in pixels.
        draw: an ImageDraw.Draw instance used only for textbbox measurement.

    Returns:
        List of wrapped line strings (no line exceeds max_width; long
        single words are not force-broken and may still overflow).
    """
    words = text.split()
    lines = []
    current_line = ""

    for word in words:
        test_line = current_line + " " + word if current_line else word
        bbox = draw.textbbox((0, 0), test_line, font=font)
        text_width = bbox[2] - bbox[0]

        if text_width <= max_width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = word

    if current_line:
        lines.append(current_line)

    return lines


def convert_to_instagram(img):
    """Center crop to 1080×1080."""
    target = 1080
    src_w, src_h = img.size
    scale  = max(target / src_w, target / src_h)
    new_w  = int(src_w * scale)
    new_h  = int(src_h * scale)
    img    = img.resize((new_w, new_h), Image.LANCZOS)
    left   = (new_w - target) // 2
    top    = (new_h - target) // 2
    right  = left + target
    bottom = top  + target
    img    = img.crop((left, top, right, bottom))
    return img


def _save_both_formats(img_rgb, jpg_path: str, webp_path: str, image_type: str):
    """
    Save an RGB image to disk as both JPG and WebP, creating parent
    directories as needed. Instagram images use higher JPEG quality
    (98, subsampling=0) and WebP quality (92) than blog images (95/90).

    Args:
        img_rgb: a PIL Image already converted to RGB mode.
        jpg_path: output path for the JPEG file.
        webp_path: output path for the WebP file.
        image_type: "instagram" selects the higher-quality preset;
            anything else uses the blog preset.

    Returns:
        (jpg_path, webp_path) tuple, unchanged from the inputs. Writes
        both files to disk as a side effect (no in-memory-only mode).
    """
    os.makedirs(os.path.dirname(jpg_path),  exist_ok=True)
    os.makedirs(os.path.dirname(webp_path), exist_ok=True)

    if image_type == "instagram":
        img_rgb.save(jpg_path,  "JPEG", quality=98, subsampling=0)
        img_rgb.save(webp_path, "WEBP", quality=92, method=6)
    else:
        img_rgb.save(jpg_path,  "JPEG", quality=95)
        img_rgb.save(webp_path, "WEBP", quality=90, method=6)

    print(f"[IMAGE CREATED] JPG  → {jpg_path}")
    print(f"[IMAGE CREATED] WebP → {webp_path}")

    return jpg_path, webp_path


def _compose_with_text(img: Image.Image, texts: dict, image_type: str) -> Image.Image:
    """
    Overlay a bottom gradient plus tag/headline/subtext onto an image.

    Draws a black gradient overlay across the lower portion of the
    image for readability, then renders texts["tag"] as a small pill,
    texts["headline"] auto-shrunk to fit within max_lines, and
    texts["subtext"] (up to 2 lines) below it. Font sizes, gradient
    zone height, and layout differ between "blog" and "instagram".

    Args:
        img: RGBA PIL Image to draw onto (already sized for image_type).
        texts: dict with optional "tag", "headline", "subtext" keys.
        image_type: "blog" or "instagram" -- selects font sizes,
            gradient strength, and max headline lines (2 vs 3).

    Returns:
        The composited RGBA Image (same object, modified in place via
        its ImageDraw context, then returned).
    """
    W, H = img.size

    # ── Gradient Overlay — stronger for better readability ────
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw_ov = ImageDraw.Draw(overlay)

    if image_type == "instagram":
        zone               = int(H * 0.60)   # ← was 0.55
        gradient_max_alpha = 240             # ← was 220
    else:
        zone               = int(H * 0.55)   # ← was 0.45
        gradient_max_alpha = 220             # ← was 200

    for i in range(zone):
        alpha = int((i / zone) * gradient_max_alpha)
        draw_ov.rectangle(
            [(0, H - zone + i), (W, H - zone + i + 1)],
            fill=(0, 0, 0, alpha)
        )

    img  = Image.alpha_composite(img, overlay)
    draw = ImageDraw.Draw(img)

    # ── Font sizes ────────────────────────────────────────────
    if image_type == "blog":
        headline_size = 42       # ← was 52 (slightly smaller)
        subtext_size  = 22       # ← was 26
        tag_size      = 20       # ← was 22
        line_spacing  = 55       # ← was 65
        max_lines     = 2        # ← was 3
    else:  # instagram
        headline_size = 64       # ← was 72
        subtext_size  = 30       # ← was 34
        tag_size      = 26       # ← was 28
        line_spacing  = 80       # ← was 88
        max_lines     = 3

    try:
        sub_font = get_font('regular', subtext_size)
        tag_font = get_font('bold',    tag_size)
    except OSError:
        raise Exception("Font files not found or invalid.")

    # ── TAG — position from bottom ────────────────────────────
    tag_text = texts.get("tag", "NEWS").upper()
    tag_bbox = draw.textbbox((0, 0), tag_text, font=tag_font)
    tag_w    = tag_bbox[2] - tag_bbox[0] + 32
    tag_x    = 30             # ← was 60
    tag_y    = H - int(H * 0.52)  # ← was 0.42 (moved up)

    draw.rectangle(
        [tag_x, tag_y, tag_x + tag_w, tag_y + 32],
        fill=(26, 86, 219, 230)
    )
    draw.text((tag_x + 14, tag_y + 4), tag_text, font=tag_font, fill="white")

    # ── HEADLINE ──────────────────────────────────────────────
    headline        = texts.get("headline", "")
    max_text_width  = W - 80     # ← was 120
    max_text_height = int(H * 0.32)  # ← was 0.28
    current_size    = headline_size

    while current_size > 24:
        hl_font       = get_font('extrabold', current_size)
        wrapped_lines = wrap_text_by_pixels(headline, hl_font, max_text_width, draw)

        if len(wrapped_lines) > max_lines:
            wrapped_lines = wrapped_lines[:max_lines]
            wrapped_lines[-1] += "..."

        total_height = len(wrapped_lines) * line_spacing

        if total_height <= max_text_height:
            break

        current_size -= 2

    y = tag_y + 42
    for line in wrapped_lines:
        draw.text((30, y), line, font=hl_font, fill="white")
        y += line_spacing

    # ── SUBTEXT — with padding from bottom ───────────────────
    subtext    = texts.get("subtext", "")
    sub_lines  = wrap_text_by_pixels(subtext, sub_font, max_text_width, draw)
    sub_lines  = sub_lines[:2]

    # ── Check if subtext fits before drawing ─────────────────
    bottom_limit = H - 15   # ← 15px padding from bottom
    for line in sub_lines:
        if y + subtext_size + 5 < bottom_limit:
            draw.text((30, y + 5), line, font=sub_font, fill=(200, 200, 200, 255))
            y += 36 if image_type == "blog" else 44

    return img

# --- Main Function ---
def compose_image(
    template_path: str,
    texts: dict,
    jpg_path: str,
    webp_path: str,
    image_type: str = "instagram"
) -> dict:
    """
    Compose a non-IPO blog/Instagram image from a template and save it
    as both JPG and WebP.

    Behavior depends on image_type:
      "blog_inner" -> template used as-is (expected 1920x490), no text,
          no overlay.
      "instagram"  -> center-cropped to 1080x1080 via
          convert_to_instagram(), then text overlaid via
          _compose_with_text().
      anything else ("blog"/outer) -> template used as-is (expected
          640x480), text overlaid via _compose_with_text().

    Args:
        template_path: path to the background template image.
        texts: dict with "tag"/"headline"/"subtext" keys used by
            _compose_with_text() (ignored for blog_inner).
        jpg_path: output path for the JPEG file.
        webp_path: output path for the WebP file.
        image_type: "blog", "blog_inner", or "instagram" (default
            "instagram").

    Returns:
        {"jpg": jpg_path, "webp": webp_path} -- both files are written
        to disk as a side effect via _save_both_formats().

    Raises:
        FileNotFoundError: if template_path does not exist.
    """
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"Template not found: {template_path}")

    img = Image.open(template_path).convert("RGBA")
    print(f"[IMAGE] Template size: {img.size} | type: {image_type}")

    if image_type == "blog_inner":
        # ── INNER — plain image, NO text, NO overlay ─────────
        # Use template as-is (1920×490) — no resize needed
        print(f"[IMAGE] blog_inner — plain image, no text")
        final_img = img.convert("RGB")

    elif image_type == "instagram":
        # ── INSTAGRAM — resize to 1080×1080 + text ───────────
        img       = convert_to_instagram(img)
        img       = _compose_with_text(img, texts, image_type)
        final_img = img.convert("RGB")
        print(f"[IMAGE] instagram — resized to 1080×1080 + text")

    else:
        # ── BLOG OUTER — use template as-is (640×480) + text ─
        # Template already correct size from outer/ folder
        img       = _compose_with_text(img, texts, image_type)
        final_img = img.convert("RGB")
        print(f"[IMAGE] blog outer — size {img.size} + text")

    # ── Save JPG + WebP ───────────────────────────────────────
    jpg_out, webp_out = _save_both_formats(
        final_img,
        jpg_path,
        webp_path,
        image_type
    )

    return {
        "jpg":  jpg_out,
        "webp": webp_out
    }
