from PIL import Image, ImageDraw, ImageFont
import os

# --- Base Path ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

FONTS = {
    'extrabold': os.path.join(BASE_DIR, '../fonts/ExtraBold.ttf'),
    'bold':      os.path.join(BASE_DIR, '../fonts/GoogleSans_17pt-Bold.ttf'),
    'regular':   os.path.join(BASE_DIR, '../fonts/Regular.ttf'),
}

def get_font(style='regular', size=24):
    path = FONTS.get(style)
    if path and os.path.exists(path):
        return ImageFont.truetype(path, size)
    fallbacks = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for f in fallbacks:
        if os.path.exists(f):
            print(f"[FONT] Using fallback: {f}")
            return ImageFont.truetype(f, size)
    return ImageFont.load_default()


def wrap_text_by_pixels(text, font, max_width, draw):
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
    target = 1080
    src_w, src_h = img.size
    scale = max(target / src_w, target / src_h)
    new_w = int(src_w * scale)
    new_h = int(src_h * scale)
    img = img.resize((new_w, new_h), Image.LANCZOS)
    left   = (new_w - target) // 2
    top    = (new_h - target) // 2
    right  = left + target
    bottom = top  + target
    img = img.crop((left, top, right, bottom))
    return img


# ── Helper: save image in both JPG + WebP to separate folders ─
def _save_both_formats(img_rgb, jpg_path: str, webp_path: str, image_type: str):
    """
    Saves image in two formats to separate folders:
      1. JPG  → jpg_path  (jpg_images folder)
      2. WebP → webp_path (webp_images folder)
    """
    os.makedirs(os.path.dirname(jpg_path),  exist_ok=True)
    os.makedirs(os.path.dirname(webp_path), exist_ok=True)

    # ── Save JPG ─────────────────────────────────────────────
    if image_type == "instagram":
        img_rgb.save(jpg_path, "JPEG", quality=98, subsampling=0)
    else:
        img_rgb.save(jpg_path, "JPEG", quality=95)
    print(f"[IMAGE CREATED] JPG  → {jpg_path}")

    # ── Save WebP ─────────────────────────────────────────────
    if image_type == "instagram":
        img_rgb.save(webp_path, "WEBP", quality=92, method=6)
    else:
        img_rgb.save(webp_path, "WEBP", quality=90, method=6)
    print(f"[IMAGE CREATED] WebP → {webp_path}")

    return jpg_path, webp_path


# --- Main Function ---
def compose_image(template_path: str, texts: dict, jpg_path: str, webp_path: str, image_type: str = "instagram") -> dict:

    if not os.path.exists(template_path):
        raise FileNotFoundError(f"Template not found: {template_path}")

    img = Image.open(template_path).convert("RGBA")

    if image_type == "instagram":
        img = convert_to_instagram(img)

    W, H = img.size

    # --- Gradient Overlay ---
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw_ov = ImageDraw.Draw(overlay)

    if image_type == "instagram":
        zone               = int(H * 0.55)
        gradient_max_alpha = 220
    else:
        zone               = int(H * 0.45)
        gradient_max_alpha = 200

    for i in range(zone):
        alpha = int((i / zone) * gradient_max_alpha)
        draw_ov.rectangle(
            [(0, H - zone + i), (W, H - zone + i + 1)],
            fill=(0, 0, 0, alpha)
        )

    img = Image.alpha_composite(img, overlay)
    draw = ImageDraw.Draw(img)

    # --- Font and Layout Sizes ---
    if image_type == "blog":
        headline_size = 52
        subtext_size  = 26
        tag_size      = 22
        line_spacing  = 65
        max_lines     = 3
    else:
        headline_size = 72
        subtext_size  = 34
        tag_size      = 28
        line_spacing  = 88
        max_lines     = 3

    try:
        sub_font = get_font('regular', subtext_size)
        tag_font = get_font('bold',    tag_size)
    except OSError:
        raise Exception("Font files not found or invalid.")

    # ── TAG ───────────────────────────────────────────────────
    tag_text = texts.get("tag", "NEWS").upper()
    tag_bbox = draw.textbbox((0, 0), tag_text, font=tag_font)
    tag_w    = tag_bbox[2] - tag_bbox[0] + 32
    tag_x    = 60
    tag_y    = H - int(H * 0.42)

    draw.rectangle(
        [tag_x, tag_y, tag_x + tag_w, tag_y + 36],
        fill=(26, 86, 219, 230)
    )
    draw.text((tag_x + 16, tag_y + 4), tag_text, font=tag_font, fill="white")

    # ── HEADLINE ──────────────────────────────────────────────
    headline        = texts.get("headline", "")
    max_text_width  = W - 120
    max_text_height = int(H * 0.28)
    current_size    = headline_size

    while current_size > 30:
        hl_font       = get_font('extrabold', current_size)
        wrapped_lines = wrap_text_by_pixels(headline, hl_font, max_text_width, draw)

        if len(wrapped_lines) > max_lines:
            wrapped_lines = wrapped_lines[:max_lines]
            wrapped_lines[-1] += "..."

        total_height = len(wrapped_lines) * line_spacing

        if total_height <= max_text_height:
            break

        current_size -= 2

    y = tag_y + 50
    for line in wrapped_lines:
        draw.text((60, y), line, font=hl_font, fill="white")
        y += line_spacing

    # ── SUBTEXT ───────────────────────────────────────────────
    subtext   = texts.get("subtext", "")
    sub_lines = wrap_text_by_pixels(subtext, sub_font, max_text_width, draw)
    sub_lines = sub_lines[:2]

    for line in sub_lines:
        draw.text((60, y + 5), line, font=sub_font, fill=(200, 200, 200, 255))
        y += 40 if image_type == "blog" else 48

    # ── Save to separate jpg_images and webp_images folders ───
    jpg_out, webp_out = _save_both_formats(
        img.convert("RGB"),
        jpg_path,
        webp_path,
        image_type
    )

    return {
        "jpg":  jpg_out,
        "webp": webp_out
    }

















# from PIL import Image, ImageDraw, ImageFont
# import os

# # --- Base Path ---
# BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# # --- Fonts ---
# # FONTS = {
# #     'extrabold': os.path.abspath(os.path.join(BASE_DIR, '../fonts/ExtraBold.ttf')),
# #     'bold': os.path.abspath(os.path.join(BASE_DIR, '../fonts/GoogleSans_17pt-Bold.ttf')),
# #     'regular': os.path.abspath(os.path.join(BASE_DIR, '../fonts/Regular.ttf')),
# # }



# # 
# FONTS = {
#     'extrabold': os.path.join(BASE_DIR, '../fonts/ExtraBold.ttf'),
#     'bold':      os.path.join(BASE_DIR, '../fonts/GoogleSans_17pt-Bold.ttf'),
#     'regular':   os.path.join(BASE_DIR, '../fonts/Regular.ttf'),
# }

# def get_font(style='regular', size=24):
#     path = FONTS.get(style)
#     if path and os.path.exists(path):
#         return ImageFont.truetype(path, size)
#     fallbacks = [
#         "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
#         "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
#     ]
#     for f in fallbacks:
#         if os.path.exists(f):
#             print(f"[FONT] Using fallback: {f}")
#             return ImageFont.truetype(f, size)
#     return ImageFont.load_default()


# # --- Smart Pixel-Based Text Wrapping ---
# def wrap_text_by_pixels(text, font, max_width, draw):
#     words = text.split()
#     lines = []
#     current_line = ""

#     for word in words:
#         test_line = current_line + " " + word if current_line else word
#         bbox = draw.textbbox((0, 0), test_line, font=font)
#         text_width = bbox[2] - bbox[0]

#         if text_width <= max_width:
#             current_line = test_line
#         else:
#             lines.append(current_line)
#             current_line = word

#     if current_line:
#         lines.append(current_line)

#     return lines


# # --- Convert Blog Image → Instagram Square (Center Crop, No Black Bars) ---
# def convert_to_instagram(img):
#     """
#     Converts any image → 1080x1080 Instagram square
#     - Center crop (no black bars)
#     - LANCZOS for sharp quality
#     """
#     target = 1080

#     src_w, src_h = img.size

#     # Scale to fill full 1080x1080
#     scale = max(target / src_w, target / src_h)

#     new_w = int(src_w * scale)
#     new_h = int(src_h * scale)

#     img = img.resize((new_w, new_h), Image.LANCZOS)

#     # Center crop to exact 1080x1080
#     left   = (new_w - target) // 2
#     top    = (new_h - target) // 2
#     right  = left + target
#     bottom = top  + target

#     img = img.crop((left, top, right, bottom))

#     return img


# # --- Main Function ---
# def compose_image(template_path: str, texts: dict, output_path: str, image_type: str = "instagram") -> str:

#     if not os.path.exists(template_path):
#         raise FileNotFoundError(f"Template not found: {template_path}")

#     img = Image.open(template_path).convert("RGBA")

#     # Convert if Instagram
#     if image_type == "instagram":
#         img = convert_to_instagram(img)

#     W, H = img.size

#     # --- Gradient Overlay ---
#     overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
#     draw_ov = ImageDraw.Draw(overlay)

#     # Stronger gradient for instagram (text must pop on mobile)
#     if image_type == "instagram":
#         zone               = int(H * 0.55)
#         gradient_max_alpha = 220
#     else:
#         zone               = int(H * 0.45)
#         gradient_max_alpha = 200

#     for i in range(zone):
#         alpha = int((i / zone) * gradient_max_alpha)
#         draw_ov.rectangle(
#             [(0, H - zone + i), (W, H - zone + i + 1)],
#             fill=(0, 0, 0, alpha)
#         )

#     img = Image.alpha_composite(img, overlay)
#     draw = ImageDraw.Draw(img)

#     # --- Font and Layout Sizes ---
#     if image_type == "blog":
#         headline_size = 52
#         subtext_size  = 26
#         tag_size      = 22
#         line_spacing  = 65
#         max_lines     = 3
#     else:  # instagram — larger for mobile readability
#         headline_size = 72
#         subtext_size  = 34
#         tag_size      = 28
#         line_spacing  = 88
#         max_lines     = 3

#     try:
#         sub_font = get_font('regular',   subtext_size)
#         tag_font =  get_font('bold',      tag_size)
#     except OSError:
#         raise Exception("Font files not found or invalid.")

#     # ===============================
#     # TAG
#     # ===============================
#     tag_text = texts.get("tag", "NEWS").upper()

#     tag_bbox = draw.textbbox((0, 0), tag_text, font=tag_font)
#     tag_w    = tag_bbox[2] - tag_bbox[0] + 32

#     tag_x = 60
#     tag_y = H - int(H * 0.42)

#     draw.rectangle(
#         [tag_x, tag_y, tag_x + tag_w, tag_y + 36],
#         fill=(26, 86, 219, 230)
#     )

#     draw.text((tag_x + 16, tag_y + 4), tag_text, font=tag_font, fill="white")

#     # ===============================
#     # HEADLINE AUTO FIT
#     # ===============================
#     headline = texts.get("headline", "")

#     max_text_width  = W - 120
#     max_text_height = int(H * 0.28)
#     current_size    = headline_size

#     while current_size > 30:
#         # hl_font = ImageFont.truetype(FONTS['extrabold'], current_size)
#         hl_font = get_font('extrabold', current_size)  # ✅ use get_font

#         wrapped_lines = wrap_text_by_pixels(
#             headline,
#             hl_font,
#             max_text_width,
#             draw
#         )

#         if len(wrapped_lines) > max_lines:
#             wrapped_lines = wrapped_lines[:max_lines]
#             wrapped_lines[-1] += "..."

#         total_height = len(wrapped_lines) * line_spacing

#         if total_height <= max_text_height:
#             break

#         current_size -= 2

#     # Draw Headline
#     y = tag_y + 50

#     for line in wrapped_lines:
#         draw.text((60, y), line, font=hl_font, fill="white")
#         y += line_spacing

#     # ===============================
#     # SUBTEXT
#     # ===============================
#     subtext = texts.get("subtext", "")

#     sub_lines = wrap_text_by_pixels(
#         subtext,
#         sub_font,
#         max_text_width,
#         draw
#     )

#     sub_lines = sub_lines[:2]

#     for line in sub_lines:
#         draw.text((60, y + 5), line, font=sub_font, fill=(200, 200, 200, 255))
#         y += 40 if image_type == "blog" else 48  # more spacing on instagram

#     # --- Save with max quality for Instagram ---
#     os.makedirs(os.path.dirname(output_path), exist_ok=True)

#     if image_type == "instagram":
#         img.convert("RGB").save(output_path, "JPEG", quality=98, subsampling=0)
#     else:
#         img.convert("RGB").save(output_path, "JPEG", quality=95)

#     print(f"[IMAGE CREATED] {output_path}")

#     return output_path
















































































































# from PIL import Image, ImageDraw, ImageFont
# import os

# # --- Base Path ---
# BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# # --- Fonts ---
# FONTS = {
#     'extrabold': os.path.abspath(os.path.join(BASE_DIR, '../fonts/ExtraBold.ttf')),
#     'bold': os.path.abspath(os.path.join(BASE_DIR, '../fonts/GoogleSans_17pt-Bold.ttf')),
#     'regular': os.path.abspath(os.path.join(BASE_DIR, '../fonts/Regular.ttf')),
# }


# # --- Smart Pixel-Based Text Wrapping ---
# def wrap_text_by_pixels(text, font, max_width, draw):
#     words = text.split()
#     lines = []
#     current_line = ""

#     for word in words:
#         test_line = current_line + " " + word if current_line else word
#         bbox = draw.textbbox((0, 0), test_line, font=font)
#         text_width = bbox[2] - bbox[0]

#         if text_width <= max_width:
#             current_line = test_line
#         else:
#             lines.append(current_line)
#             current_line = word

#     if current_line:
#         lines.append(current_line)

#     return lines


# # --- Convert Blog Image → Instagram Square ---
# def convert_to_instagram(img):
#     """
#     Converts rectangular image (1200x630) → 1080x1080 square
#     """
#     size = 1080

#     # Resize maintaining aspect ratio
#     img = img.resize((1080, int(img.height * (1080 / img.width))))

#     # Create square canvas
#     bg = Image.new("RGBA", (size, size), (0, 0, 0, 255))

#     # Center image vertically
#     y_offset = (size - img.height) // 2
#     bg.paste(img, (0, y_offset))

#     return bg


# # --- Main Function ---
# def compose_image(template_path: str, texts: dict, output_path: str, image_type: str = "instagram") -> str:

#     if not os.path.exists(template_path):
#         raise FileNotFoundError(f"Template not found: {template_path}")

#     img = Image.open(template_path).convert("RGBA")

#     # 🔥 Convert if Instagram
#     if image_type == "instagram":
#         img = convert_to_instagram(img)

#     W, H = img.size

#     # --- Gradient Overlay ---
#     overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
#     draw_ov = ImageDraw.Draw(overlay)

#     zone = int(H * 0.45)

#     for i in range(zone):
#         alpha = int((i / zone) * 200)
#         draw_ov.rectangle(
#             [(0, H - zone + i), (W, H - zone + i + 1)],
#             fill=(0, 0, 0, alpha)
#         )

#     img = Image.alpha_composite(img, overlay)
#     draw = ImageDraw.Draw(img)

#     # --- Font Sizes ---
#     if image_type == "blog":
#         headline_size = 52
#         subtext_size = 26
#         tag_size = 22
#         line_spacing = 65
#     else:
#         headline_size = 64
#         subtext_size = 30
#         tag_size = 24
#         line_spacing = 75

#     try:
#         sub_font = ImageFont.truetype(FONTS['regular'], subtext_size)
#         tag_font = ImageFont.truetype(FONTS['bold'], tag_size)
#     except OSError:
#         raise Exception("Font files not found or invalid.")

#     # ===============================
#     # 🔵 TAG
#     # ===============================
#     tag_text = texts.get("tag", "NEWS").upper()

#     tag_bbox = draw.textbbox((0, 0), tag_text, font=tag_font)
#     tag_w = tag_bbox[2] - tag_bbox[0] + 32

#     tag_x = 60
#     tag_y = H - int(H * 0.42)

#     draw.rectangle(
#         [tag_x, tag_y, tag_x + tag_w, tag_y + 36],
#         fill=(26, 86, 219, 230)
#     )

#     draw.text((tag_x + 16, tag_y + 4), tag_text, font=tag_font, fill="white")

#     # ===============================
#     # 🔥 HEADLINE AUTO FIT
#     # ===============================
#     headline = texts.get("headline", "")

#     max_text_width = W - 120
#     max_lines = 3
#     max_text_height = int(H * 0.28)

#     current_size = headline_size

#     while current_size > 30:
#         hl_font = ImageFont.truetype(FONTS['extrabold'], current_size)

#         wrapped_lines = wrap_text_by_pixels(
#             headline,
#             hl_font,
#             max_text_width,
#             draw
#         )

#         if len(wrapped_lines) > max_lines:
#             wrapped_lines = wrapped_lines[:max_lines]
#             wrapped_lines[-1] += "..."

#         total_height = len(wrapped_lines) * line_spacing

#         if total_height <= max_text_height:
#             break

#         current_size -= 2

#     # --- Draw Headline ---
#     y = tag_y + 50

#     for line in wrapped_lines:
#         draw.text((60, y), line, font=hl_font, fill="white")
#         y += line_spacing

#     # ===============================
#     # 🔥 SUBTEXT
#     # ===============================
#     subtext = texts.get("subtext", "")

#     sub_lines = wrap_text_by_pixels(
#         subtext,
#         sub_font,
#         max_text_width,
#         draw
#     )

#     sub_lines = sub_lines[:2]

#     for line in sub_lines:
#         draw.text((60, y + 5), line, font=sub_font, fill=(200, 200, 200, 255))
#         y += 40

#     # --- Save ---
#     os.makedirs(os.path.dirname(output_path), exist_ok=True)

#     img.convert("RGB").save(output_path, "JPEG", quality=95)

#     print(f"[IMAGE CREATED] {output_path}")

#     return output_path




















































































































# from PIL import Image, ImageDraw, ImageFont
# import os

# # --- Base Path ---
# BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# # --- Fonts ---
# FONTS = {
#     'extrabold': os.path.abspath(os.path.join(BASE_DIR, '../fonts/ExtraBold.ttf')),
#     'bold': os.path.abspath(os.path.join(BASE_DIR, '../fonts/GoogleSans_17pt-Bold.ttf')),
#     'regular': os.path.abspath(os.path.join(BASE_DIR, '../fonts/Regular.ttf')),
# }


# # --- Smart Pixel-Based Text Wrapping ---
# def wrap_text_by_pixels(text, font, max_width, draw):
#     words = text.split()
#     lines = []
#     current_line = ""

#     for word in words:
#         test_line = current_line + " " + word if current_line else word
#         bbox = draw.textbbox((0, 0), test_line, font=font)
#         text_width = bbox[2] - bbox[0]

#         if text_width <= max_width:
#             current_line = test_line
#         else:
#             lines.append(current_line)
#             current_line = word

#     if current_line:
#         lines.append(current_line)

#     return lines


# # --- Main Function ---
# def compose_image(template_path: str, texts: dict, output_path: str, image_type: str = "instagram") -> str:

#     if not os.path.exists(template_path):
#         raise FileNotFoundError(f"Template not found: {template_path}")

#     img = Image.open(template_path).convert("RGBA")
#     W, H = img.size

#     # --- Gradient Overlay ---
#     overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
#     draw_ov = ImageDraw.Draw(overlay)

#     zone = int(H * 0.45)  # slightly increased for better readability

#     for i in range(zone):
#         alpha = int((i / zone) * 200)
#         draw_ov.rectangle(
#             [(0, H - zone + i), (W, H - zone + i + 1)],
#             fill=(0, 0, 0, alpha)
#         )

#     img = Image.alpha_composite(img, overlay)
#     draw = ImageDraw.Draw(img)

#     # --- Font Sizes ---
#     if image_type == "blog":
#         headline_size = 52
#         subtext_size = 26
#         tag_size = 22
#         line_spacing = 65
#     else:
#         headline_size = 68
#         subtext_size = 32
#         tag_size = 26
#         line_spacing = 80

#     try:
#         sub_font = ImageFont.truetype(FONTS['regular'], subtext_size)
#         tag_font = ImageFont.truetype(FONTS['bold'], tag_size)
#     except OSError:
#         raise Exception("Font files not found or invalid.")

#     # ===============================
#     # 🔵 TAG
#     # ===============================
#     tag_text = texts.get("tag", "NEWS").upper()

#     tag_bbox = draw.textbbox((0, 0), tag_text, font=tag_font)
#     tag_w = tag_bbox[2] - tag_bbox[0] + 32

#     tag_x = 60
#     tag_y = H - int(H * 0.42)   # 🔥 FIXED POSITION

#     draw.rectangle(
#         [tag_x, tag_y, tag_x + tag_w, tag_y + 36],
#         fill=(26, 86, 219, 230)
#     )

#     draw.text((tag_x + 16, tag_y + 4), tag_text, font=tag_font, fill="white")

#     # ===============================
#     # 🔥 HEADLINE (AUTO FIT + NO OVERFLOW)
#     # ===============================
#     headline = texts.get("headline", "")

#     max_text_width = W - 120
#     max_lines = 3 if image_type == "instagram" else 2
#     max_text_height = int(H * 0.28)

#     current_size = headline_size

#     while current_size > 30:
#         hl_font = ImageFont.truetype(FONTS['extrabold'], current_size)

#         wrapped_lines = wrap_text_by_pixels(
#             headline,
#             hl_font,
#             max_text_width,
#             draw
#         )

#         if len(wrapped_lines) > max_lines:
#             wrapped_lines = wrapped_lines[:max_lines]
#             wrapped_lines[-1] += "..."

#         total_height = len(wrapped_lines) * line_spacing

#         if total_height <= max_text_height:
#             break

#         current_size -= 2

#     # 🔥 KEY FIX: MOVE TEXT UP BASED ON HEIGHT
#     text_block_height = len(wrapped_lines) * line_spacing
#     y = tag_y + 50   # start just below tag (controlled spacing)

#     for line in wrapped_lines:
#         draw.text((60, y), line, font=hl_font, fill="white")
#         y += line_spacing

#     # ===============================
#     # 🔥 SUBTEXT (SAFE)
#     # ===============================
#     subtext = texts.get("subtext", "")

#     sub_lines = wrap_text_by_pixels(
#         subtext,
#         sub_font,
#         max_text_width,
#         draw
#     )

#     sub_lines = sub_lines[:2]  # limit lines

#     for line in sub_lines:
#         draw.text((60, y + 5), line, font=sub_font, fill=(200, 200, 200, 255))
#         y += 40

#     # --- Save ---
#     os.makedirs(os.path.dirname(output_path), exist_ok=True)

#     img.convert("RGB").save(output_path, "JPEG", quality=95)

#     print(f"[IMAGE CREATED] {output_path}")

#     return output_path













































# from PIL import Image, ImageDraw, ImageFont
# import os

# # --- Base Path ---
# BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# # --- Fonts ---
# FONTS = {
#     'extrabold': os.path.abspath(os.path.join(BASE_DIR, '../fonts/ExtraBold.ttf')),
#     'bold': os.path.abspath(os.path.join(BASE_DIR, '../fonts/GoogleSans_17pt-Bold.ttf')),
#     'regular': os.path.abspath(os.path.join(BASE_DIR, '../fonts/Regular.ttf')),
# }


# # --- Smart Pixel-Based Text Wrapping ---
# def wrap_text_by_pixels(text, font, max_width, draw):
#     words = text.split()
#     lines = []
#     current_line = ""

#     for word in words:
#         test_line = current_line + " " + word if current_line else word

#         bbox = draw.textbbox((0, 0), test_line, font=font)
#         text_width = bbox[2] - bbox[0]

#         if text_width <= max_width:
#             current_line = test_line
#         else:
#             lines.append(current_line)
#             current_line = word

#     if current_line:
#         lines.append(current_line)

#     return lines


# # --- Main Function ---
# def compose_image(template_path: str, texts: dict, output_path: str, image_type: str = "instagram") -> str:

#     if not os.path.exists(template_path):
#         raise FileNotFoundError(f"Template not found: {template_path}")

#     img = Image.open(template_path).convert("RGBA")
#     W, H = img.size

#     # --- Gradient Overlay ---
#     overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
#     draw_ov = ImageDraw.Draw(overlay)

#     zone = int(H * 0.4)

#     for i in range(zone):
#         alpha = int((i / zone) * 200)
#         draw_ov.rectangle(
#             [(0, H - zone + i), (W, H - zone + i + 1)],
#             fill=(0, 0, 0, alpha)
#         )

#     img = Image.alpha_composite(img, overlay)
#     draw = ImageDraw.Draw(img)

#     # --- Font Sizes ---
#     if image_type == "blog":
#         headline_size = 52
#         subtext_size = 26
#         tag_size = 22
#         line_spacing = 65
#     else:
#         headline_size = 68
#         subtext_size = 32
#         tag_size = 26
#         line_spacing = 80

#     # --- Load Fonts ---
#     try:
#         sub_font = ImageFont.truetype(FONTS['regular'], subtext_size)
#         tag_font = ImageFont.truetype(FONTS['bold'], tag_size)
#     except OSError:
#         raise Exception("Font files not found or invalid. Check font paths.")

#     # --- TAG ---
#     tag_text = texts.get("tag", "NEWS").upper()

#     tag_bbox = draw.textbbox((0, 0), tag_text, font=tag_font)
#     tag_w = tag_bbox[2] - tag_bbox[0] + 32

#     tag_x = 60
#     tag_y = H - int(H * 0.38)

#     draw.rectangle(
#         [tag_x, tag_y, tag_x + tag_w, tag_y + 36],
#         fill=(26, 86, 219, 230)
#     )

#     draw.text((tag_x + 16, tag_y + 4), tag_text, font=tag_font, fill="white")

#     # =========================================================
#     # 🔥 HEADLINE (AUTO-FIT SOLUTION)
#     # =========================================================

#     headline = texts.get("headline", "")

#     max_text_width = W - 120
#     max_lines = 3 if image_type == "instagram" else 2
#     max_text_height = int(H * 0.30)

#     current_size = headline_size

#     while current_size > 30:
#         hl_font = ImageFont.truetype(FONTS['extrabold'], current_size)

#         wrapped_lines = wrap_text_by_pixels(
#             headline,
#             hl_font,
#             max_text_width,
#             draw
#         )

#         # Limit lines
#         if len(wrapped_lines) > max_lines:
#             wrapped_lines = wrapped_lines[:max_lines]
#             wrapped_lines[-1] += "..."

#         total_height = len(wrapped_lines) * line_spacing

#         if total_height <= max_text_height:
#             break

#         current_size -= 2  # reduce font size

#     y = tag_y + 56

#     for line in wrapped_lines:
#         draw.text((60, y), line, font=hl_font, fill="white")
#         y += line_spacing

#     # =========================================================
#     # 🔥 SUBTEXT (SAFE)
#     # =========================================================

#     subtext = texts.get("subtext", "")

#     sub_lines = wrap_text_by_pixels(
#         subtext,
#         sub_font,
#         max_text_width,
#         draw
#     )

#     # limit subtext lines
#     sub_lines = sub_lines[:2]

#     for line in sub_lines:
#         draw.text((60, y + 10), line, font=sub_font, fill=(200, 200, 200, 255))
#         y += 40

#     # --- Save ---
#     os.makedirs(os.path.dirname(output_path), exist_ok=True)

#     img.convert("RGB").save(output_path, "JPEG", quality=95)

#     print(f"[IMAGE CREATED] {output_path}")

#     return output_path










































































# from PIL import Image, ImageDraw, ImageFont
# import os

# # --- Base Path ---
# BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# # --- Fonts (FIXED PATHS) ---
# FONTS = {
#     'extrabold': os.path.abspath(os.path.join(BASE_DIR, '../fonts/ExtraBold.ttf')),
#     'bold': os.path.abspath(os.path.join(BASE_DIR, '../fonts/GoogleSans_17pt-Bold.ttf')),
#     'regular': os.path.abspath(os.path.join(BASE_DIR, '../fonts/Regular.ttf')),
# }


# # --- Smart Pixel-Based Text Wrapping ---
# def wrap_text_by_pixels(text, font, max_width, draw):
#     words = text.split()
#     lines = []
#     current_line = ""

#     for word in words:
#         test_line = current_line + " " + word if current_line else word

#         bbox = draw.textbbox((0, 0), test_line, font=font)
#         text_width = bbox[2] - bbox[0]

#         if text_width <= max_width:
#             current_line = test_line
#         else:
#             lines.append(current_line)
#             current_line = word

#     if current_line:
#         lines.append(current_line)

#     return lines


# # --- Main Function ---
# def compose_image(template_path: str, texts: dict, output_path: str, image_type: str = "instagram") -> str:
#     """
#     texts = { headline, subtext, tag }
#     Returns: output_path
#     """

#     # --- Load Template ---
#     if not os.path.exists(template_path):
#         raise FileNotFoundError(f"Template not found: {template_path}")

#     img = Image.open(template_path).convert("RGBA")
#     W, H = img.size

#     # --- Gradient Overlay (Bottom 40%) ---
#     overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
#     draw_ov = ImageDraw.Draw(overlay)

#     zone = int(H * 0.4)

#     for i in range(zone):
#         alpha = int((i / zone) * 200)
#         draw_ov.rectangle(
#             [(0, H - zone + i), (W, H - zone + i + 1)],
#             fill=(0, 0, 0, alpha)
#         )

#     img = Image.alpha_composite(img, overlay)
#     draw = ImageDraw.Draw(img)

#     # --- Font Sizes ---
#     if image_type == "blog":
#         headline_size = 52
#         subtext_size = 26
#         tag_size = 22
#         line_spacing = 65
#     else:
#         headline_size = 68
#         subtext_size = 32
#         tag_size = 26
#         line_spacing = 80

#     # --- Load Fonts ---
#     try:
#         hl_font = ImageFont.truetype(FONTS['extrabold'], headline_size)
#         sub_font = ImageFont.truetype(FONTS['regular'], subtext_size)
#         tag_font = ImageFont.truetype(FONTS['bold'], tag_size)
#     except OSError:
#         raise Exception("Font files not found or invalid. Check font paths.")

#     # --- TAG Badge ---
#     tag_text = texts.get("tag", "NEWS").upper()

#     tag_bbox = draw.textbbox((0, 0), tag_text, font=tag_font)
#     tag_w = tag_bbox[2] - tag_bbox[0] + 32

#     tag_x = 60
#     tag_y = H - int(H * 0.38)

#     draw.rectangle(
#         [tag_x, tag_y, tag_x + tag_w, tag_y + 36],
#         fill=(26, 86, 219, 230)
#     )

#     draw.text(
#         (tag_x + 16, tag_y + 4),
#         tag_text,
#         font=tag_font,
#         fill="white"
#     )

#     # --- HEADLINE (SMART) ---
#     headline = texts.get("headline", "")

#     # Auto font scaling
#     if len(headline) > 80:
#         headline_size = int(headline_size * 0.75)
#     elif len(headline) > 50:
#         headline_size = int(headline_size * 0.85)

#     hl_font = ImageFont.truetype(FONTS['extrabold'], headline_size)

#     max_text_width = W - 120

#     wrapped_lines = wrap_text_by_pixels(
#         headline,
#         hl_font,
#         max_text_width,
#         draw
#     )

#     # Limit lines
#     max_lines = 3 if image_type == "instagram" else 2

#     if len(wrapped_lines) > max_lines:
#         wrapped_lines = wrapped_lines[:max_lines]
#         wrapped_lines[-1] += "..."

#     y = tag_y + 56

#     for line in wrapped_lines:
#         draw.text((60, y), line, font=hl_font, fill="white")
#         y += line_spacing

#     # --- SUBTEXT ---
#     subtext = texts.get("subtext", "")

#     sub_lines = wrap_text_by_pixels(
#         subtext,
#         sub_font,
#         max_text_width,
#         draw
#     )

#     for line in sub_lines:
#         draw.text((60, y + 10), line, font=sub_font, fill=(200, 200, 200, 255))
#         y += 40

#     # --- Save Image ---
#     os.makedirs(os.path.dirname(output_path), exist_ok=True)

#     img.convert("RGB").save(output_path, "JPEG", quality=95)

#     print(f"[IMAGE CREATED] {output_path}")

#     return output_path








































































































# from PIL import Image, ImageDraw, ImageFont
# import textwrap
# import os

# # Absolute base path (important for stability)
# BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# # Font paths (adjust if needed)
# FONTS = {
#      'extrabold': os.path.abspath(os.path.join(BASE_DIR, '../fonts/extrabold.ttf')),
#     'bold': os.path.abspath(os.path.join(BASE_DIR, '../fonts/GoogleSans_17pt-Bold.ttf')),
#     'regular': os.path.abspath(os.path.join(BASE_DIR, '../fonts/regular.ttf')),
# }


# def compose_image(template_path: str, texts: dict, output_path: str, image_type: str = "instagram") -> str:
#     """
#     Generate final image with overlay text.

#     Args:
#         template_path (str): Path to template image
#         texts (dict): {
#             "headline": str,
#             "subtext": str,
#             "tag": str
#         }
#         output_path (str): Where to save final image
#         image_type (str): "instagram" or "blog"

#     Returns:
#         str: output_path
#     """

#     # --- Step 0: Load image ---
#     if not os.path.exists(template_path):
#         raise FileNotFoundError(f"Template not found: {template_path}")

#     img = Image.open(template_path).convert("RGBA")
#     W, H = img.size

#     # --- Step 1: Gradient overlay (bottom 40%) ---
#     overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
#     draw_ov = ImageDraw.Draw(overlay)

#     zone = int(H * 0.4)

#     for i in range(zone):
#         alpha = int((i / zone) * 200)  # smooth gradient
#         draw_ov.rectangle(
#             [(0, H - zone + i), (W, H - zone + i + 1)],
#             fill=(0, 0, 0, alpha)
#         )

#     img = Image.alpha_composite(img, overlay)
#     draw = ImageDraw.Draw(img)

#     # --- Step 2: Font sizes based on image type ---
#     if image_type == "blog":
#         headline_size = 52
#         subtext_size = 26
#         tag_size = 22
#         line_spacing = 65
#     else:  # instagram
#         headline_size = 68
#         subtext_size = 32
#         tag_size = 26
#         line_spacing = 80

#     # Load fonts safely
#     try:
#         hl_font = ImageFont.truetype(FONTS['extrabold'], headline_size)
#         sub_font = ImageFont.truetype(FONTS['regular'], subtext_size)
#         tag_font = ImageFont.truetype(FONTS['bold'], tag_size)
#     except OSError:
#         raise Exception("Font files not found. Check font paths.")

#     # --- Step 3: TAG badge ---
#     tag_text = texts.get("tag", "NEWS").upper()

#     tag_bbox = draw.textbbox((0, 0), tag_text, font=tag_font)
#     tag_w = tag_bbox[2] - tag_bbox[0] + 32

#     tag_x = 60
#     tag_y = H - int(H * 0.38)

#     draw.rectangle(
#         [tag_x, tag_y, tag_x + tag_w, tag_y + 36],
#         fill=(26, 86, 219, 230)  # blue badge
#     )

#     draw.text(
#         (tag_x + 16, tag_y + 4),
#         tag_text,
#         font=tag_font,
#         fill="white"
#     )

#     # --- Step 4: Headline ---
#     headline = texts.get("headline", "")

#     # Wrap text to avoid overflow
#     wrapped_lines = textwrap.wrap(headline, width=18)

#     y = tag_y + 56

#     for line in wrapped_lines:
#         draw.text(
#             (60, y),
#             line,
#             font=hl_font,
#             fill="white"
#         )
#         y += line_spacing

#     # --- Step 5: Subtext ---
#     subtext = texts.get("subtext", "")

#     draw.text(
#         (60, y + 10),
#         subtext,
#         font=sub_font,
#         fill=(200, 200, 200, 255)
#     )

#     # --- Step 6: Save Image ---
#     os.makedirs(os.path.dirname(output_path), exist_ok=True)

#     img.convert("RGB").save(output_path, "JPEG", quality=95)

#     print(f"[IMAGE CREATED] {output_path}")

#     return output_path