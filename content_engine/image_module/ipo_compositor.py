# # content_engine/image_module/ipo_compositor.py
# #
# # Dedicated compositor for IPO Alert template.
# # Writes company name + IPO data values at exact positions.
# #
# #   Template zones (1080×1350 original):
# #   ┌─────────────────────────────────────────┐
# #   │  IPO ALERT          ← already on image  │
# #   │  COMPANY NAME       ← written by code   │
# #   │  [coal image] [logo/funnel]             │
# #   │               Date ──┐  ┌── Price      │
# #   │               Lot ───┤  ├── Size       │
# #   │           Allotment  ┘  └── Listing    │
# #   └─────────────────────────────────────────┘

# import os
# import re
# from PIL import Image, ImageDraw, ImageFont


# BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# FONTS = {
#     'extrabold': os.path.join(BASE_DIR, '../fonts/ExtraBold.ttf'),
#     'bold':      os.path.join(BASE_DIR, '../fonts/GoogleSans_17pt-Bold.ttf'),
#     'regular':   os.path.join(BASE_DIR, '../fonts/Regular.ttf'),
# }


# def _get_font(style: str = 'bold', size: int = 28) -> ImageFont.FreeTypeFont:
#     path = FONTS.get(style)
#     if path and os.path.exists(path):
#         return ImageFont.truetype(path, size)
#     fallbacks = [
#         "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
#         "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
#     ]
#     for f in fallbacks:
#         if os.path.exists(f):
#             return ImageFont.truetype(f, size)
#     return ImageFont.load_default()


# # ══════════════════════════════════════════════════════════════
# #  ZONE COORDINATES
# #  (x%, y%) = center position as % of image size
# #
# #  COMPANY NAME:
# #    Positioned between "IPO ALERT" text and logo/funnel
# #    y=0.22 puts it just below IPO ALERT heading
# #
# #  DATA ZONES:
# #    Match the label positions on the template
# #
# #  Adjust if text appears in wrong position:
# #    Increase y% → moves text DOWN
# #    Decrease y% → moves text UP
# # ══════════════════════════════════════════════════════════════

# COMPANY_ZONE = (0.62, 0.22)   # center-right, below IPO ALERT

# ZONES = {
#    # NEW zones (values placed BELOW labels):
# "date":      (0.32, 0.46),   # +6% below Date label
# "price":     (0.74, 0.46),  # +6% below Price label
# "lot":       (0.32, 0.64),   # +12% below Lot label
# "size":      (0.74, 0.64),   # +12% below Size label
# "allotment": (0.30, 0.82) ,  # +14% below Tentative Allotment ← big fix
# "listing":   (0.74, 0.82)   # +14% below Tentative Listing   ← big fix
# }

# VALUE_COLOR   = (255, 210, 50)    # yellow — matches template labels
# COMPANY_COLOR = (255, 210, 50)    # same yellow for company name


# def _save_both_formats(img_rgb, jpg_path, webp_path, image_type):
#     os.makedirs(os.path.dirname(jpg_path),  exist_ok=True)
#     os.makedirs(os.path.dirname(webp_path), exist_ok=True)
#     if image_type == "instagram":
#         img_rgb.save(jpg_path,  "JPEG", quality=98, subsampling=0)
#         img_rgb.save(webp_path, "WEBP", quality=92, method=6)
#     else:
#         img_rgb.save(jpg_path,  "JPEG", quality=95)
#         img_rgb.save(webp_path, "WEBP", quality=90, method=6)
#     print(f"[IMAGE CREATED] JPG  → {jpg_path}")
#     print(f"[IMAGE CREATED] WebP → {webp_path}")
#     return jpg_path, webp_path


# def _wrap_text(text: str, font, draw, max_width: int) -> list:
#     """Wrap text into lines that fit within max_width pixels."""
#     words = text.split()
#     lines = []
#     current = ""
#     for word in words:
#         test = f"{current} {word}".strip()
#         bbox = draw.textbbox((0, 0), test, font=font)
#         if bbox[2] - bbox[0] <= max_width:
#             current = test
#         else:
#             if current:
#                 lines.append(current)
#             current = word
#     if current:
#         lines.append(current)
#     return lines


# def _write_company_name(
#     img: Image.Image,
#     company: str,
#     font_size: int = 40
# ) -> Image.Image:
#     """
#     Writes company name on image between IPO ALERT and data zones.
#     Auto-wraps long names to 2 lines.
#     Uses bold yellow text matching the template style.
#     """
#     W, H   = img.size
#     draw   = ImageDraw.Draw(img)

#     # Clean company name
#     company_clean = company\
#         .replace(" Limited", "")\
#         .replace(" Ltd", "")\
#         .strip()\
#         .upper()

#     # Font — try extrabold first for impact
#     font = _get_font('extrabold', font_size)

#     # Available width for text (right half of image, avoiding coal photo)
#     # Coal photo occupies left ~35% → text in right 65%
#     text_x_start = int(W * 0.33)   # start after coal photo
#     max_width    = int(W * 0.63)   # width available for text

#     # Wrap text
#     lines = _wrap_text(company_clean, font, draw, max_width)
#     lines = lines[:3]   # max 3 lines

#     # Position: center of text block at COMPANY_ZONE y%
#     x_pct, y_pct  = COMPANY_ZONE
#     center_x       = int(W * x_pct)
#     center_y       = int(H * y_pct)

#     # Calculate total text block height
#     line_height    = font_size + 6
#     total_height   = len(lines) * line_height
#     start_y        = center_y - total_height // 2

#     for i, line in enumerate(lines):
#         bbox   = draw.textbbox((0, 0), line, font=font)
#         text_w = bbox[2] - bbox[0]
#         text_x = center_x - text_w // 2

#         # Shadow
#         draw.text((text_x + 2, start_y + i * line_height + 2),
#                   line, font=font, fill=(0, 0, 0))
#         # Text
#         draw.text((text_x, start_y + i * line_height),
#                   line, font=font, fill=COMPANY_COLOR)

#     print(f"[IPO ZONE] company name  → '{company_clean}' "
#           f"({len(lines)} lines) at center ({center_x}, {center_y})")
#     return img


# def _write_ipo_values(
#     img: Image.Image,
#     ipo_data: dict,
#     font_size: int = 36
# ) -> Image.Image:
#     """
#     Writes IPO data values at exact zone positions on template.
#     """
#     W, H   = img.size
#     draw   = ImageDraw.Draw(img)
#     font   = _get_font('bold', font_size)

#     fields = {
#         "date":      ipo_data.get("date",      "TBA"),
#         "price":     ipo_data.get("price",     "TBA"),
#         "lot":       ipo_data.get("lot",       "TBA"),
#         "size":      ipo_data.get("size",      "TBA"),
#         "allotment": ipo_data.get("allotment", "TBA"),
#         "listing":   ipo_data.get("listing",   "TBA"),
#     }

#     for field, value in fields.items():
#         if field not in ZONES:
#             continue

#         x_pct, y_pct = ZONES[field]
#         x = int(W * x_pct)
#         y = int(H * y_pct)

#         bbox   = draw.textbbox((0, 0), str(value), font=font)
#         text_w = bbox[2] - bbox[0]
#         text_x = x - text_w // 2

#         # Shadow
#         draw.text((text_x + 2, y + 2), str(value),
#                   font=font, fill=(0, 0, 0, 200))
#         # Value
#         draw.text((text_x, y), str(value),
#                   font=font, fill=VALUE_COLOR)

#         print(f"[IPO ZONE] {field:<12} → '{value}' at ({x}, {y})")

#     return img


# def _prepare_ipo_data(article: dict) -> dict:
#     """Extracts and cleans IPO fields for zone text placement."""
#     open_date  = article.get("open_date",    "")
#     close_date = article.get("close_date",   "")
#     listing    = article.get("listing_date", "")
#     price      = article.get("price_band",   "")
#     lot        = article.get("lot_size",      "")
#     issue_size = article.get("issue_size",   "")

#     # Date range: "5-9 Jun, 2026"
#     if open_date and close_date:
#         open_day   = open_date.split()[0]
#         date_str   = f"{open_day}-{close_date.strip()}"
#     elif open_date:
#         date_str = open_date
#     else:
#         date_str = "TBA"

#     # Lot: "333 Shares" → "333"
#     lot_short = lot.replace(" Shares","").replace(" shares","").strip() \
#                 if lot else "TBA"

#     # Size: extract ₹XXXCr
#     size_short = issue_size
#     if issue_size and "₹" in issue_size:
#         match = re.search(r'₹([\d,.]+\s*Cr)', issue_size)
#         if match:
#             size_short = f"₹{match.group(1)}"

#     # Listing: strip day name
#     listing_short = listing\
#         .replace("Mon, ","").replace("Tue, ","").replace("Wed, ","")\
#         .replace("Thu, ","").replace("Fri, ","").replace("Sat, ","")\
#         .replace("Sun, ","").strip() if listing else "TBA"

#     # Allotment: clean close_date
#     allotment_short = close_date\
#         .replace("Mon, ","").replace("Tue, ","").replace("Wed, ","")\
#         .replace("Thu, ","").replace("Fri, ","").replace("Sat, ","")\
#         .replace("Sun, ","").strip() if close_date else "TBA"

#     return {
#         "date":      date_str,
#         "price":     price        if price      else "TBA",
#         "lot":       lot_short,
#         "size":      size_short   if size_short else "TBA",
#         "allotment": allotment_short,
#         "listing":   listing_short,
#     }


# def compose_ipo_image(
#     template_path: str,
#     article: dict,
#     jpg_path: str,
#     webp_path: str,
#     image_type: str = "blog"
# ) -> dict:
#     """
#     Composes IPO Alert image.

#     Writes on image:
#       1. Company name  → bold yellow, between IPO ALERT and funnel
#       2. Data values   → Date/Price/Lot/Size/Allotment/Listing at zones

#     image_type:
#       "blog"       → resize to 640×480  + company name + zone values
#       "blog_inner" → resize to 1920×490 + NO text (plain)
#       "instagram"  → crop to 1080×1080  + company name + zone values
#     """
#     if not os.path.exists(template_path):
#         raise FileNotFoundError(f"IPO template not found: {template_path}")

#     img  = Image.open(template_path).convert("RGBA")
#     W, H = img.size
#     print(f"[IPO IMAGE] Template {W}×{H} | type={image_type}")

#     ipo_data = _prepare_ipo_data(article)
#     company  = article.get("company", article.get("Blog_Title", "IPO"))
#     print(f"[IPO IMAGE] Company: {company}")
#     print(f"[IPO IMAGE] Data: {ipo_data}")

#     # ── BLOG INNER — plain resize, NO text ───────────────────
#     if image_type == "blog_inner":
#         final_img = img.resize((1920, 490), Image.LANCZOS).convert("RGB")
#         print("[IPO IMAGE] blog_inner — plain 1920×490, no text")

#     # ── INSTAGRAM — crop to 1080×1080 + text ─────────────────
#     elif image_type == "instagram":
#         target = 1080
#         scale  = max(target / W, target / H)
#         new_w, new_h = int(W * scale), int(H * scale)
#         img    = img.resize((new_w, new_h), Image.LANCZOS)
#         left   = (new_w - target) // 2
#         top    = (new_h - target) // 2
#         img    = img.crop((left, top, left + target, top + target))

#         # Font sizes scaled for 1080
#         company_font_size = int(target * 0.042)   # ~45px
#         value_font_size   = int(target * 0.038)   # ~41px

#         img = _write_company_name(img, company, company_font_size)
#         img = _write_ipo_values(img, ipo_data, value_font_size)
#         final_img = img.convert("RGB")
#         print(f"[IPO IMAGE] instagram — {target}×{target} + company + values")

#     # ── BLOG OUTER — resize to 640×480 + text ────────────────
#     else:
#         target_w, target_h = 640, 480
#         img = img.resize((target_w, target_h), Image.LANCZOS)

#         # Font sizes scaled for 640×480
#         company_font_size = int(target_w * 0.048)  # ~31px
#         value_font_size   = int(target_w * 0.040)  # ~26px

#         img = _write_company_name(img, company, company_font_size)
#         img = _write_ipo_values(img, ipo_data, value_font_size)
#         final_img = img.convert("RGB")
#         print(f"[IPO IMAGE] blog outer — {target_w}×{target_h} + company + values")

#     _save_both_formats(final_img, jpg_path, webp_path, image_type)
#     return {"jpg": jpg_path, "webp": webp_path}


# # ══════════════════════════════════════════════════════════════
# #  STANDALONE TEST
# # ══════════════════════════════════════════════════════════════

# if __name__ == "__main__":
#     import sys
#     import glob
#     import tempfile

#     print("=" * 60)
#     print("  IPO COMPOSITOR TEST")
#     print("=" * 60)

#     # Find template
#     template_dirs = [
#         os.path.join(os.path.dirname(__file__), "templates"),
#         os.path.join(os.path.dirname(__file__), "templates", "outer"),
#     ]
#     template = None
#     for d in template_dirs:
#         if not os.path.exists(d):
#             continue
#         matches = (glob.glob(os.path.join(d, "*ipo*")) +
#                    glob.glob(os.path.join(d, "*IPO*")))
#         if matches:
#             template = matches[0]
#             break

#     if not template:
#         print("❌ No IPO template found")
#         print("   Place as: content_engine/image_module/templates/ipo_alert.png")
#         sys.exit(1)

#     print(f"Template: {template}")

#     article = {
#         "company":      "Hexagon Nutrition Limited",
#         "open_date":    "5 Jun, 2026",
#         "close_date":   "9 Jun, 2026",
#         "listing_date": "Fri, Jun 12, 2026",
#         "price_band":   "₹42 to ₹45",
#         "lot_size":     "333 Shares",
#         "issue_size":   "3,08,59,704shares(agg. up to ₹139Cr)",
#     }

#     tmp = tempfile.mkdtemp()

#     print("\n--- Blog Outer (640×480) ---")
#     compose_ipo_image(template, article,
#         os.path.join(tmp, "blog_hexagon.jpg"),
#         os.path.join(tmp, "blog_hexagon.webp"), "blog")

#     print("\n--- Instagram (1080×1080) ---")
#     compose_ipo_image(template, article,
#         os.path.join(tmp, "insta_hexagon.jpg"),
#         os.path.join(tmp, "insta_hexagon.webp"), "instagram")

#     print("\n--- Blog Inner (1920×490) ---")
#     compose_ipo_image(template, article,
#         os.path.join(tmp, "inner_hexagon.jpg"),
#         os.path.join(tmp, "inner_hexagon.webp"), "blog_inner")

#     print(f"\n✅ Test images saved to: {tmp}")

# content_engine/image_module/ipo_compositor.py
#
# Dedicated compositor for IPO Alert template.
# Dynamically fits company name in available space — no overlap guaranteed.
#
# Layout on template:
#   Header (logo + Sanskrit):  y=0-7%
#   IPO ALERT text:            y=13-17%
#   ── COMPANY NAME fits here (y=17-28%) ──
#   Funnel/bowl icon:          y=28-37%
#   Date / Price labels:       y=37-40%
#   Lot  / Size  labels:       y=56-57%
#   Allotment / Listing:       y=70-76%
#
# image_type:
#   "blog"       → 640×480  full resize   + company name + zone values
#   "blog_inner" → 1920×490 plain resize  + NO text
#   "instagram"  → 1080×1080 center crop  + company name + zone values

import os
import re
from PIL import Image, ImageDraw, ImageFont


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

FONTS = {
    'extrabold': os.path.join(BASE_DIR, '../fonts/ExtraBold.ttf'),
    'bold':      os.path.join(BASE_DIR, '../fonts/GoogleSans_17pt-Bold.ttf'),
    'regular':   os.path.join(BASE_DIR, '../fonts/Regular.ttf'),
}

VALUE_COLOR = (255, 210, 50)    # yellow — matches template labels


# ══════════════════════════════════════════════════════════════
#  ZONE COORDINATES  (x%, y%) as fraction of final image size
#
#  BLOG OUTER (640×480) — full portrait squished to landscape
#    IPO ALERT ends at y=17% (80px)
#    Funnel starts at y=28% (136px)
#    Company name CENTER at y=22.5% (fits 56px gap)
#    Left values at x=0.32 (coal photo ends at ~25% on 640px)
#
#  INSTAGRAM (1080×1080) — center crop from portrait
#    IPO ALERT ends at y=13% (~140px)
#    Funnel starts at y=23% (~245px)
#    Company name CENTER at y=17.5% (fits 105px gap)
#    Left values at x=0.38 (coal photo ends at ~35% on 1080px)
# ══════════════════════════════════════════════════════════════

COMPANY_ZONE = {
    "blog":      (0.62, 0.225),
    "instagram": (0.62, 0.175),
}

ZONES = {
    "blog": {
        "date":      (0.32, 0.46),
        "price":     (0.74, 0.46),
        "lot":       (0.32, 0.64),
        "size":      (0.74, 0.64),
        "allotment": (0.30, 0.82),
        "listing":   (0.74, 0.82),
    },
    "instagram": {
        # Left values at x=0.38 — clears coal photo (ends at 35%)
        "date":      (0.38, 0.46),
        "price":     (0.74, 0.46),
        "lot":       (0.38, 0.64),
        "size":      (0.74, 0.64),
        "allotment": (0.38, 0.82),
        "listing":   (0.74, 0.82),
    },
}

# Gap available for company name text (px) per image type
# Prevents text from bleeding into IPO ALERT or funnel
COMPANY_GAP = {
    "blog":      56,    # 56px between IPO ALERT (ends 80px) and funnel (136px)
    "instagram": 105,   # 105px between IPO ALERT (ends 140px) and funnel (245px)
}

# Font size range for auto-sizing
COMPANY_FONT_MAX = {"blog": 24, "instagram": 43}
COMPANY_FONT_MIN = {"blog": 14, "instagram": 20}


def _get_font(style: str = 'bold', size: int = 28) -> ImageFont.FreeTypeFont:
    path = FONTS.get(style)
    if path and os.path.exists(path):
        return ImageFont.truetype(path, size)
    for f in ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"]:
        if os.path.exists(f):
            return ImageFont.truetype(f, size)
    return ImageFont.load_default()


def _fit_company_name(
    company: str,
    draw: ImageDraw.Draw,
    image_type: str,
    img_width: int,
) -> tuple[list, int]:
    """
    Auto-sizes and wraps company name to fit in available gap.
    Tries font sizes from max down to min.
    Tries 1 line first, then 2 lines.
    Guarantees no overlap with IPO ALERT or funnel.

    Returns:
        (lines_list, font_size)
    """
    name      = company.replace(" Limited","").replace(" Ltd","").strip().upper()
    max_w     = int(img_width * 0.60)          # 60% of image width
    gap_h     = COMPANY_GAP[image_type]        # available height in px
    font_max  = COMPANY_FONT_MAX[image_type]
    font_min  = COMPANY_FONT_MIN[image_type]

    for font_size in range(font_max, font_min - 1, -1):
        font = _get_font('extrabold', font_size)
        lh   = font_size + 4   # line height with small gap

        # ── Try 1 line ────────────────────────────────────────
        bbox = draw.textbbox((0, 0), name, font=font)
        if bbox[2] - bbox[0] <= max_w:
            if lh <= gap_h:
                return [name], font_size

        # ── Try 2 lines — smart word split ───────────────────
        words = name.split()
        if len(words) >= 2:
            # Find best split point (closest to middle by chars)
            best_split = len(words) // 2
            best_diff  = float('inf')
            for split in range(1, len(words)):
                l1 = " ".join(words[:split])
                l2 = " ".join(words[split:])
                diff = abs(len(l1) - len(l2))
                if diff < best_diff:
                    best_diff  = diff
                    best_split = split

            l1 = " ".join(words[:best_split])
            l2 = " ".join(words[best_split:])
            b1 = draw.textbbox((0, 0), l1, font=font)
            b2 = draw.textbbox((0, 0), l2, font=font)
            total_h = lh * 2

            if (b1[2]-b1[0] <= max_w and
                    b2[2]-b2[0] <= max_w and
                    total_h <= gap_h):
                return [l1, l2], font_size

    # Fallback — use min font, truncate with ellipsis
    font_size = font_min
    font      = _get_font('extrabold', font_size)
    bbox      = draw.textbbox((0, 0), name, font=font)
    if bbox[2] - bbox[0] > max_w:
        # Truncate char by char
        while len(name) > 3:
            name = name[:-1]
            test = name + "..."
            bbox = draw.textbbox((0, 0), test, font=font)
            if bbox[2] - bbox[0] <= max_w:
                name = test
                break
    return [name], font_size


def _write_company_name(
    img: Image.Image,
    company: str,
    image_type: str,
) -> Image.Image:
    """
    Writes company name on image between IPO ALERT and funnel.
    Auto-sizes font to fit without overlap — works for any name length.
    """
    W, H   = img.size
    draw   = ImageDraw.Draw(img)
    zone   = COMPANY_ZONE[image_type]
    cx, cy = int(W * zone[0]), int(H * zone[1])

    lines, font_size = _fit_company_name(company, draw, image_type, W)
    font = _get_font('extrabold', font_size)
    lh   = font_size + 4
    sy   = cy - (len(lines) * lh) // 2

    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        tx   = cx - (bbox[2] - bbox[0]) // 2
        # Shadow
        draw.text((tx + 2, sy + i*lh + 2), line, font=font, fill=(0, 0, 0))
        # Text
        draw.text((tx,     sy + i*lh),     line, font=font, fill=VALUE_COLOR)

    print(f"[IPO ZONE] company       → '{' / '.join(lines)}' "
          f"font={font_size}px center=({cx},{cy})")
    return img


def _write_ipo_values(
    img: Image.Image,
    ipo_data: dict,
    image_type: str,
) -> Image.Image:
    """
    Writes 6 IPO data values at zone positions matching template labels.
    Zone x/y positions are different for blog vs instagram.
    """
    W, H   = img.size
    draw   = ImageDraw.Draw(img)
    zones  = ZONES[image_type]

    # Font size: 3.8% of width for both types
    font_size = int(W * 0.038)
    font      = _get_font('bold', font_size)

    fields = {
        "date":      ipo_data.get("date",      "TBA"),
        "price":     ipo_data.get("price",     "TBA"),
        "lot":       ipo_data.get("lot",       "TBA"),
        "size":      ipo_data.get("size",      "TBA"),
        "allotment": ipo_data.get("allotment", "TBA"),
        "listing":   ipo_data.get("listing",   "TBA"),
    }

    for field, value in fields.items():
        if field not in zones:
            continue
        x, y = int(W * zones[field][0]), int(H * zones[field][1])
        bbox  = draw.textbbox((0, 0), str(value), font=font)
        tx    = x - (bbox[2] - bbox[0]) // 2
        # Shadow
        draw.text((tx + 2, y + 2), str(value), font=font, fill=(0, 0, 0))
        # Value
        draw.text((tx,     y),     str(value), font=font, fill=VALUE_COLOR)
        print(f"[IPO ZONE] {field:<12} → '{value}' at ({x},{y})")

    return img


def _prepare_ipo_data(article: dict) -> dict:
    """Extracts and cleans IPO fields for zone text placement."""
    open_date  = article.get("open_date",    "")
    close_date = article.get("close_date",   "")
    listing    = article.get("listing_date", "")
    price      = article.get("price_band",   "")
    lot        = article.get("lot_size",      "")
    issue_size = article.get("issue_size",   "")

    # Date: "5-9 Jun, 2026"
    if open_date and close_date:
        date_str = f"{open_date.split()[0]}-{close_date.strip()}"
    elif open_date:
        date_str = open_date
    else:
        date_str = "TBA"

    # Lot: "333 Shares" → "333"
    lot_short = lot.replace(" Shares","").replace(" shares","").strip() \
                if lot else "TBA"

    # Size: extract ₹XXXCr
    size_short = issue_size
    if issue_size and "₹" in issue_size:
        m = re.search(r'₹([\d,.]+\s*Cr)', issue_size)
        if m:
            size_short = f"₹{m.group(1)}"

    # Strip day name from listing/allotment
    def strip_day(s):
        for d in ["Mon, ","Tue, ","Wed, ","Thu, ","Fri, ","Sat, ","Sun, "]:
            s = s.replace(d, "")
        return s.strip()

    return {
        "date":      date_str,
        "price":     price        if price      else "TBA",
        "lot":       lot_short,
        "size":      size_short   if size_short else "TBA",
        "allotment": strip_day(close_date)  if close_date else "TBA",
        "listing":   strip_day(listing)     if listing    else "TBA",
    }


def _save_both_formats(img_rgb, jpg_path, webp_path, image_type):
    os.makedirs(os.path.dirname(jpg_path),  exist_ok=True)
    os.makedirs(os.path.dirname(webp_path), exist_ok=True)
    q = {"instagram": (98, 92)}.get(image_type, (95, 90))
    img_rgb.save(jpg_path,  "JPEG", quality=q[0])
    img_rgb.save(webp_path, "WEBP", quality=q[1], method=6)
    print(f"[IMAGE CREATED] JPG  → {jpg_path}")
    print(f"[IMAGE CREATED] WebP → {webp_path}")
    return jpg_path, webp_path


def compose_ipo_image(
    template_path: str,
    article: dict,
    jpg_path: str,
    webp_path: str,
    image_type: str = "blog"
) -> dict:
    """
    Composes IPO Alert image.

    Writes:
      1. Company name — auto-sized font, fits in gap between IPO ALERT and funnel
      2. Zone values  — Date/Price/Lot/Size/Allotment/Listing at label positions

    Guarantees no overlap for any company name length.

    Args:
        template_path: path to IPO Alert PNG template
        article:       IPO article dict (from ipo.py)
        jpg_path:      output JPG path
        webp_path:     output WebP path
        image_type:    "blog" | "blog_inner" | "instagram"

    Returns:
        {"jpg": jpg_path, "webp": webp_path}
    """
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"IPO template not found: {template_path}")

    img       = Image.open(template_path).convert("RGBA")
    W, H      = img.size
    ipo_data  = _prepare_ipo_data(article)
    company   = article.get("company", article.get("Blog_Title", "IPO"))

    print(f"[IPO IMAGE] Template {W}×{H} | type={image_type}")
    print(f"[IPO IMAGE] Company : {company}")
    print(f"[IPO IMAGE] Data    : {ipo_data}")

    # ── BLOG INNER — plain resize, NO text ───────────────────
    if image_type == "blog_inner":
        final = img.resize((1920, 490), Image.LANCZOS).convert("RGB")
        print("[IPO IMAGE] blog_inner — plain 1920×490, no text")

    # ── INSTAGRAM — center crop to 1080×1080 + text ──────────
    elif image_type == "instagram":
        scale       = max(1080 / W, 1080 / H)
        nw, nh      = int(W * scale), int(H * scale)
        img         = img.resize((nw, nh), Image.LANCZOS)
        left        = (nw - 1080) // 2
        top         = (nh - 1080) // 2
        img         = img.crop((left, top, left + 1080, top + 1080))
        img         = _write_company_name(img, company, "instagram")
        img         = _write_ipo_values(img, ipo_data, "instagram")
        final       = img.convert("RGB")
        print("[IPO IMAGE] instagram — 1080×1080 + company + values")

    # ── BLOG OUTER — full resize to 640×480 + text ───────────
    else:
        img   = img.resize((640, 480), Image.LANCZOS)
        img   = _write_company_name(img, company, "blog")
        img   = _write_ipo_values(img, ipo_data, "blog")
        final = img.convert("RGB")
        print("[IPO IMAGE] blog outer — 640×480 + company + values")

    _save_both_formats(final, jpg_path, webp_path, image_type)
    return {"jpg": jpg_path, "webp": webp_path}


# ══════════════════════════════════════════════════════════════
#  STANDALONE TEST — tests ALL company name lengths
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import glob
    import tempfile

    template_dirs = [
        os.path.join(os.path.dirname(__file__), "templates"),
        os.path.join(os.path.dirname(__file__), "templates", "outer"),
    ]
    template = None
    for d in template_dirs:
        if not os.path.exists(d): continue
        for pat in ["*ipo*", "*IPO*"]:
            m = glob.glob(os.path.join(d, pat))
            if m: template = m[0]; break
        if template: break

    if not template:
        print("❌ No IPO template found")
        print("   Place as: templates/ipo_alert.png")
        raise SystemExit(1)

    print(f"Template: {template}\n")

    # Test companies of various lengths
    test_cases = [
        {
            "company": "SMR Jewels Limited",
            "open_date": "26 May, 2026", "close_date": "28 May, 2026",
            "listing_date": "Fri, Jun 2, 2026", "price_band": "₹95 to ₹100",
            "lot_size": "150 Shares", "issue_size": "₹48Cr",
        },
        {
            "company": "Hexagon Nutrition Limited",
            "open_date": "5 Jun, 2026", "close_date": "9 Jun, 2026",
            "listing_date": "Fri, Jun 12, 2026", "price_band": "₹42 to ₹45",
            "lot_size": "333 Shares", "issue_size": "3,08,59,704shares(agg. up to ₹139Cr)",
        },
        {
            "company": "Rajnandini Fashion India Limited",
            "open_date": "1 Jun, 2026", "close_date": "3 Jun, 2026",
            "listing_date": "Mon, Jun 8, 2026", "price_band": "₹60 to ₹65",
            "lot_size": "200 Shares", "issue_size": "₹75Cr",
        },
        {
            "company": "Central Mine Planning Design Institute Limited",
            "open_date": "20 Mar, 2026", "close_date": "24 Mar, 2026",
            "listing_date": "Fri, Mar 30, 2026", "price_band": "₹163 to ₹172",
            "lot_size": "80 Shares", "issue_size": "₹1,842Cr",
        },
    ]

    tmp = tempfile.mkdtemp()
    print(f"Output dir: {tmp}\n")

    for article in test_cases:
        name = article["company"].replace(" Limited","").upper()
        print(f"{'='*55}")
        print(f"Testing: {name}")
        print(f"{'='*55}")

        safe = name.replace(" ","_")[:30]

        compose_ipo_image(template, article,
            os.path.join(tmp, f"blog_{safe}.jpg"),
            os.path.join(tmp, f"blog_{safe}.webp"), "blog")

        compose_ipo_image(template, article,
            os.path.join(tmp, f"insta_{safe}.jpg"),
            os.path.join(tmp, f"insta_{safe}.webp"), "instagram")
        print()

    print(f"✅ All test images saved to: {tmp}")