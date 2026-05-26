# import os
# import random
# import re
# import unicodedata
# import json
# from datetime import datetime

# from RSS.zerodha import fetch_zerodha
# from RSS.cnbc import fetch_cnbc
# from RSS.paisa import fetch_5paisa
# from RSS.livemint import fetch_livemint
# from RSS.fetch_nse_corporate import fetch_nse_corporate

# from content_engine.image_module.text_extractor import extract_image_text
# from content_engine.image_module.tempalte_selector import select_template, select_template_pair
# from content_engine.image_module.compositor import compose_image
# from content_engine.image_module.validator import validate_template
# from content_engine.image_module.ai_image_generator import generate_ai_image

# from utils.combined_filter import filter_by_country_and_category
# from AI_GEN.notify_generator import generate_notification
# from AI_GEN.generate_instagram_caption import generate_instagram_caption
# from AI_GEN.get_system_timestamp import get_run_timestamp
# from AI_GEN.blog_generator import generate_blog
# from storage.save_output import save_output
# from utils.timer import timed, Timer, print_timing_summary, reset_timings


# # ── Base directory ────────────────────────────────────────────
# BASE_DIR            = os.path.dirname(os.path.abspath(__file__))
# OUTPUT_IMG_DIR      = os.path.join(BASE_DIR, "output_images")
# OUTPUT_IMG_JPG_DIR  = os.path.join(BASE_DIR, "output_images", "jpg_images")
# OUTPUT_IMG_WEBP_DIR = os.path.join(BASE_DIR, "output_images", "webp_images")
# STACK_FILE          = os.path.join(BASE_DIR, "output", "article_stack.json")
# TIMESTAMP_FILE      = os.path.join(BASE_DIR, "output", "stack_timestamp.json")

# # ── Image generation mode ─────────────────────────────────────
# # True  → AI generated images  → saves to testing_webp_output.json
# # False → Template based images → saves to output.json
# USE_AI_IMAGES   = True
# OUTPUT_FILENAME = "testing_webp_output.json" if USE_AI_IMAGES else "output.json"

# print(f"[MODE] USE_AI_IMAGES={USE_AI_IMAGES} → saving to output/{OUTPUT_FILENAME}")


# # ══════════════════════════════════════════════════════════════
# # Stack helpers
# # ══════════════════════════════════════════════════════════════

# def save_stack(stack):
#     os.makedirs(os.path.dirname(STACK_FILE), exist_ok=True)
#     with open(STACK_FILE, "w", encoding="utf-8") as f:
#         json.dump(stack, f, ensure_ascii=False, indent=2)
#     print(f"[STACK] {len(stack)} articles saved to disk")


# def load_stack():
#     if not os.path.exists(STACK_FILE):
#         return []
#     with open(STACK_FILE, "r", encoding="utf-8") as f:
#         try:
#             return json.load(f)
#         except:
#             return []


# def pop_from_stack(stack):
#     if not stack:
#         return None, stack
#     item = random.choice(stack)
#     stack.remove(item)
#     return item, stack


# def save_timestamp():
#     os.makedirs(os.path.dirname(TIMESTAMP_FILE), exist_ok=True)
#     ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#     with open(TIMESTAMP_FILE, "w") as f:
#         json.dump({"stack_built_at": ts}, f)
#     print(f"[TIMESTAMP] Stack built at: {ts}")
#     return ts


# def load_timestamp():
#     if not os.path.exists(TIMESTAMP_FILE):
#         return None
#     with open(TIMESTAMP_FILE, "r") as f:
#         try:
#             data = json.load(f)
#             return data.get("stack_built_at")
#         except:
#             return None


# # ══════════════════════════════════════════════════════════════
# # Pehli baar full fetch karke stack banao
# # ══════════════════════════════════════════════════════════════

# def _full_fetch_and_build_stack(selected_country, category):
#     print("\n" + "="*50)
#     print("  PHASE 1 — BUILDING FRESH STACK")
#     print("="*50)

#     TOP_N    = 6
#     all_data = []

#     with Timer("fetch_zerodha"):       all_data.extend(fetch_zerodha()[:TOP_N])
#     with Timer("fetch_cnbc"):          all_data.extend(fetch_cnbc()[:TOP_N])
#     with Timer("fetch_5paisa"):        all_data.extend(fetch_5paisa()[:TOP_N])
#     with Timer("fetch_livemint"):      all_data.extend(fetch_livemint()[:TOP_N])
#     with Timer("fetch_nse_corporate"): all_data.extend(fetch_nse_corporate()[:TOP_N])

#     print(f"Total collected: {len(all_data)}")

#     filtered_data, source = filter_by_country_and_category(
#         all_data, selected_country, category
#     )
#     print(f"After country+category filter: {len(filtered_data)} (source={source})")

#     used_titles = load_used_titles()
#     fresh = [
#         item for item in filtered_data
#         if normalize_title(item.get("Blog_Title", "")) not in used_titles
#     ]
#     print(f"Fresh unique articles: {len(fresh)}")

#     if fresh:
#         save_stack(fresh)
#         save_timestamp()
#         print(f"[STACK] Built with {len(fresh)} articles!")
#     else:
#         print("[STACK] No fresh articles found!")

#     print("="*50 + "\n")
#     return fresh


# # ══════════════════════════════════════════════════════════════
# # Stack empty hone ke baad timestamp ke baad fetch karo
# # ══════════════════════════════════════════════════════════════

# def _fetch_after_timestamp(selected_country, category, saved_ts):
#     print(f"\n[STACK EMPTY] Fetching new articles after: {saved_ts}")

#     TOP_N    = 6
#     all_data = []

#     all_data.extend(fetch_zerodha()[:TOP_N])
#     all_data.extend(fetch_cnbc()[:TOP_N])
#     all_data.extend(fetch_5paisa()[:TOP_N])
#     all_data.extend(fetch_livemint()[:TOP_N])
#     all_data.extend(fetch_nse_corporate()[:TOP_N])

#     filtered_data, source = filter_by_country_and_category(
#         all_data, selected_country, category
#     )
#     print(f"After country+category filter: {len(filtered_data)} (source={source})")

#     used_titles = load_used_titles()
#     fresh = [
#         item for item in filtered_data
#         if normalize_title(item.get("Blog_Title", "")) not in used_titles
#     ]

#     if fresh:
#         save_stack(fresh)
#         save_timestamp()
#         print(f"[STACK] Refilled with {len(fresh)} new articles")
#     else:
#         print("[STACK] Abhi koi naya article nahi — 5 min baad retry karega")

#     return fresh


# # ── Normalize Title ───────────────────────────────────────────
# def normalize_title(title):
#     title = title.strip().lower()
#     title = re.sub(r'\s+', ' ', title)
#     return title


# # ── Load used titles — reads from correct file based on mode ──
# def load_used_titles():
#     filepath = f"output/{OUTPUT_FILENAME}"
#     if not os.path.exists(filepath):
#         return set()
#     with open(filepath, "r", encoding="utf-8") as f:
#         try:
#             data = json.load(f)
#             return {
#                 normalize_title(item.get("Blog_Title", ""))
#                 for item in data
#             }
#         except:
#             return set()


# # ── Utility ───────────────────────────────────────────────────
# def clean_filename(text):
#     text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
#     text = re.sub(r'[\\/*?:"<>|]', '', text)
#     text = text.replace(" ", "_")
#     text = re.sub(r'_+', '_', text)
#     return text[:60]


# # ── Timed wrappers ────────────────────────────────────────────
# @timed
# def _generate_blog(item):
#     return generate_blog(item)

# @timed
# def _generate_notification(item):
#     return generate_notification(item)

# @timed
# def _generate_instagram(item):
#     return generate_instagram_caption(item)

# @timed
# def _extract_image_text(title, content, category):
#     return extract_image_text(title, content, category)

# @timed
# def _select_template_pair(category, title):
#     return select_template_pair(category, title)

# @timed
# def _compose_image(template, image_text, jpg_path, webp_path, image_type):
#     return compose_image(template, image_text, jpg_path, webp_path, image_type=image_type)

# @timed
# def _generate_ai_image(blog_title, blog_content, blog_outer_paths, blog_inner_paths, instagram_paths, quality="medium"):
#     return generate_ai_image(blog_title, blog_content, blog_outer_paths, blog_inner_paths, instagram_paths, quality)

# @timed
# def _save_output(item, filename):
#     return save_output(item, filename=filename)

# @timed
# def _filter_combined(data, country, category):
#     return filter_by_country_and_category(data, country, category)


# # ── Main pipeline ─────────────────────────────────────────────
# def run_pipeline(selected_country="India", category="finance"):

#     reset_timings()
#     os.makedirs(OUTPUT_IMG_DIR,      exist_ok=True)
#     os.makedirs(OUTPUT_IMG_JPG_DIR,  exist_ok=True)
#     os.makedirs(OUTPUT_IMG_WEBP_DIR, exist_ok=True)
#     results = []

#     # ── Stack load karo ──────────────────────────────────────
#     stack = load_stack()
#     print(f"[STACK] {len(stack)} articles remaining in stack")

#     # ── Stack empty hai → decide karo kya karna hai ──────────
#     if not stack:
#         saved_ts = load_timestamp()

#         if saved_ts is None:
#             print("[STACK] Pehli baar start — full fetch karo...")
#             stack = _full_fetch_and_build_stack(selected_country, category)
#         else:
#             print(f"[STACK] Empty — timestamp ke baad fetch karo: {saved_ts}")
#             stack = _fetch_after_timestamp(selected_country, category, saved_ts)

#         # ── Fallback Zerodha ──────────────────────────────────
#         if not stack:
#             print("[WAITING] Koi naya article nahi mila — fallback Zerodha...")

#             zerodha_data = fetch_zerodha()
#             if not zerodha_data:
#                 return []

#             final_item = random.choice(zerodha_data)

#             final_item["blog"]             = generate_blog(final_item)
#             final_item["notify"]           = generate_notification(final_item)
#             final_item["instagram_notify"] = generate_instagram_caption(final_item)
#             final_item["Run_Timestamp"]    = get_run_timestamp()

#             # ── Save to correct file based on mode ───────────
#             save_output(final_item, filename=OUTPUT_FILENAME)
#             return [final_item]

#     # ── Stack se ek random article pop karo ──────────────────
#     final_item, stack = pop_from_stack(stack)
#     save_stack(stack)
#     print(f"[POPPED]  {final_item.get('Blog_Title', '')[:60]}")
#     print(f"[STACK]   {len(stack)} articles remaining")

#     final_category = category

#     # ── Used titles check karo ────────────────────────────────
#     used_titles = load_used_titles()

#     if normalize_title(final_item.get("Blog_Title", "")) in used_titles:
#         print("[SKIPPED] Title already used — next cycle me try karega")
#         return []

#     print(f"[SELECTED] Fresh blog: {final_item.get('Blog_Title', '')[:50]}")

#     try:
#         # ── AI Content Generation ─────────────────────────────
#         final_item["blog"]             = _generate_blog(final_item)
#         final_item["notify"]           = _generate_notification(final_item)
#         final_item["instagram_notify"] = _generate_instagram(final_item)

#         # ── File paths ────────────────────────────────────────
#         safe_title = clean_filename(final_item["Blog_Title"])

#         if USE_AI_IMAGES:
#             # ══════════════════════════════════════════════════
#             # AI Image Generation
#             # Saves to → testing_webp_output.json
#             # ══════════════════════════════════════════════════
#             print(f"[IMAGE MODE] AI generated images → {OUTPUT_FILENAME}")

#             blog_outer_jpg  = os.path.join(OUTPUT_IMG_JPG_DIR,  f"blog_outer_{safe_title}.jpg")
#             blog_outer_webp = os.path.join(OUTPUT_IMG_WEBP_DIR, f"blog_outer_{safe_title}.webp")
#             blog_inner_jpg  = os.path.join(OUTPUT_IMG_JPG_DIR,  f"blog_inner_{safe_title}.jpg")
#             blog_inner_webp = os.path.join(OUTPUT_IMG_WEBP_DIR, f"blog_inner_{safe_title}.webp")
#             insta_jpg       = os.path.join(OUTPUT_IMG_JPG_DIR,  f"insta_{safe_title}.jpg")
#             insta_webp      = os.path.join(OUTPUT_IMG_WEBP_DIR, f"insta_{safe_title}.webp")

#             images = _generate_ai_image(
#                 final_item["Blog_Title"],
#                 final_item.get("Blog_Content", ""),
#                 blog_outer_paths = {"jpg": blog_outer_jpg,  "webp": blog_outer_webp},
#                 blog_inner_paths = {"jpg": blog_inner_jpg,  "webp": blog_inner_webp},
#                 instagram_paths  = {"jpg": insta_jpg,       "webp": insta_webp},
#                 quality          = "medium"
#             )

#             final_item["blog_image_outer"] = images["blog_outer"]
#             final_item["blog_image_inner"] = images["blog_inner"]
#             final_item["instagram_image"]  = images["instagram"]

#         else:
#             # ══════════════════════════════════════════════════
#             # Template Image Generation
#             # Saves to → output.json
#             # ══════════════════════════════════════════════════
#             print(f"[IMAGE MODE] Template based images → {OUTPUT_FILENAME}")

#             final_item["image_text"] = _extract_image_text(
#                 final_item["Blog_Title"],
#                 final_item.get("Blog_Content", ""),
#                 final_category.upper()
#             )

#             template_pair  = _select_template_pair(
#                 final_category,
#                 final_item["Blog_Title"]
#             )
#             outer_template = template_pair["outer"]
#             inner_template = template_pair["inner"]

#             blog_jpg_path        = os.path.join(OUTPUT_IMG_JPG_DIR,  f"blog_{safe_title}.jpg")
#             blog_webp_path       = os.path.join(OUTPUT_IMG_WEBP_DIR, f"blog_{safe_title}.webp")
#             blog_inner_jpg_path  = os.path.join(OUTPUT_IMG_JPG_DIR,  f"blog_inner_{safe_title}.jpg")
#             blog_inner_webp_path = os.path.join(OUTPUT_IMG_WEBP_DIR, f"blog_inner_{safe_title}.webp")
#             insta_jpg_path       = os.path.join(OUTPUT_IMG_JPG_DIR,  f"insta_{safe_title}.jpg")
#             insta_webp_path      = os.path.join(OUTPUT_IMG_WEBP_DIR, f"insta_{safe_title}.webp")

#             # ── Blog Outer (640×480) + text ───────────────────
#             print(f"[IMAGE] Blog outer → {os.path.basename(outer_template)}")
#             final_item["blog_image"] = _compose_image(
#                 outer_template,
#                 final_item["image_text"],
#                 blog_jpg_path,
#                 blog_webp_path,
#                 "blog"
#             )

#             # ── Blog Inner (1920×490) plain ───────────────────
#             print(f"[IMAGE] Blog inner → {os.path.basename(inner_template)}")
#             final_item["blog_image_inner"] = _compose_image(
#                 inner_template,
#                 {},
#                 blog_inner_jpg_path,
#                 blog_inner_webp_path,
#                 "blog_inner"
#             )

#             # ── Instagram (1080×1080) + text ──────────────────
#             print(f"[IMAGE] Instagram → {os.path.basename(outer_template)}")
#             final_item["instagram_image"] = _compose_image(
#                 outer_template,
#                 final_item["image_text"],
#                 insta_jpg_path,
#                 insta_webp_path,
#                 "instagram"
#             )

#         final_item["Run_Timestamp"] = get_run_timestamp()

#         # ── Save to correct file based on mode ────────────────
#         saved = _save_output(final_item, OUTPUT_FILENAME)

#         if saved:
#             results.append(final_item)
#             print(f"[DONE] Blog saved to output/{OUTPUT_FILENAME}")
#             print(f"[DONE] {final_item['Blog_Title'][:60]}")
#         else:
#             print(f"[SKIPPED PIPELINE] Already exists: {final_item['Blog_Title'][:60]}")

#     except Exception as e:
#         print(f"[ERROR] {e}")

#     print_timing_summary()
#     return results



import os
import random
import re
import unicodedata
import json
from datetime import datetime

from RSS.zerodha import fetch_zerodha
from RSS.cnbc import fetch_cnbc
from RSS.paisa import fetch_5paisa
from RSS.livemint import fetch_livemint
from RSS.fetch_nse_corporate import fetch_nse_corporate

from content_engine.image_module.text_extractor import extract_image_text
from content_engine.image_module.tempalte_selector import (
    select_template,
    select_template_pair,
    select_template_pair_smart        # ← added
)
from content_engine.image_module.compositor import compose_image
from content_engine.image_module.validator import validate_template
from content_engine.image_module.ai_image_generator import generate_ai_image

from utils.combined_filter import filter_by_country_and_category
from AI_GEN.notify_generator import generate_notification
from AI_GEN.generate_instagram_caption import generate_instagram_caption
from AI_GEN.get_system_timestamp import get_run_timestamp
from AI_GEN.blog_generator import generate_blog
from storage.save_output import save_output
from utils.timer import timed, Timer, print_timing_summary, reset_timings


# ── Base directory ────────────────────────────────────────────
BASE_DIR            = os.path.dirname(os.path.abspath(__file__))
OUTPUT_IMG_DIR      = os.path.join(BASE_DIR, "output_images")
OUTPUT_IMG_JPG_DIR  = os.path.join(BASE_DIR, "output_images", "jpg_images")
OUTPUT_IMG_WEBP_DIR = os.path.join(BASE_DIR, "output_images", "webp_images")
STACK_FILE          = os.path.join(BASE_DIR, "output", "article_stack.json")
TIMESTAMP_FILE      = os.path.join(BASE_DIR, "output", "stack_timestamp.json")

# ── Image generation mode ─────────────────────────────────────
# True  → AI generated images  → saves to testing_webp_output.json
# False → Template based images → saves to output.json
USE_AI_IMAGES   = False
OUTPUT_FILENAME = "testing_webp_output.json" if USE_AI_IMAGES else "output.json"

print(f"[MODE] USE_AI_IMAGES={USE_AI_IMAGES} → saving to output/{OUTPUT_FILENAME}")

def clean_newlines(text):
    if not isinstance(text, str):
        return text
    return text.replace('\\n\\n', '').replace('\\n', '')
# ══════════════════════════════════════════════════════════════
# Stack helpers
# ══════════════════════════════════════════════════════════════

def save_stack(stack):
    os.makedirs(os.path.dirname(STACK_FILE), exist_ok=True)
    with open(STACK_FILE, "w", encoding="utf-8") as f:
        json.dump(stack, f, ensure_ascii=False, indent=2)
    print(f"[STACK] {len(stack)} articles saved to disk")


def load_stack():
    if not os.path.exists(STACK_FILE):
        return []
    with open(STACK_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except:
            return []


def pop_from_stack(stack):
    if not stack:
        return None, stack
    item = random.choice(stack)
    stack.remove(item)
    return item, stack


def save_timestamp():
    os.makedirs(os.path.dirname(TIMESTAMP_FILE), exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(TIMESTAMP_FILE, "w") as f:
        json.dump({"stack_built_at": ts}, f)
    print(f"[TIMESTAMP] Stack built at: {ts}")
    return ts


def load_timestamp():
    if not os.path.exists(TIMESTAMP_FILE):
        return None
    with open(TIMESTAMP_FILE, "r") as f:
        try:
            data = json.load(f)
            return data.get("stack_built_at")
        except:
            return None


# ══════════════════════════════════════════════════════════════
# Pehli baar full fetch karke stack banao
# ══════════════════════════════════════════════════════════════

def _full_fetch_and_build_stack(selected_country, category):
    print("\n" + "="*50)
    print("  PHASE 1 — BUILDING FRESH STACK")
    print("="*50)

    TOP_N    = 6
    all_data = []

    with Timer("fetch_zerodha"):       all_data.extend(fetch_zerodha()[:TOP_N])
    with Timer("fetch_cnbc"):          all_data.extend(fetch_cnbc()[:TOP_N])
    with Timer("fetch_5paisa"):        all_data.extend(fetch_5paisa()[:TOP_N])
    with Timer("fetch_livemint"):      all_data.extend(fetch_livemint()[:TOP_N])
    with Timer("fetch_nse_corporate"): all_data.extend(fetch_nse_corporate()[:TOP_N])

    print(f"Total collected: {len(all_data)}")

    filtered_data, source = filter_by_country_and_category(
        all_data, selected_country, category
    )
    print(f"After country+category filter: {len(filtered_data)} (source={source})")

    used_titles = load_used_titles()
    fresh = [
        item for item in filtered_data
        if normalize_title(item.get("Blog_Title", "")) not in used_titles
    ]
    print(f"Fresh unique articles: {len(fresh)}")

    if fresh:
        save_stack(fresh)
        save_timestamp()
        print(f"[STACK] Built with {len(fresh)} articles!")
    else:
        print("[STACK] No fresh articles found!")

    print("="*50 + "\n")
    return fresh


# ══════════════════════════════════════════════════════════════
# Stack empty hone ke baad timestamp ke baad fetch karo
# ══════════════════════════════════════════════════════════════

def _fetch_after_timestamp(selected_country, category, saved_ts):
    print(f"\n[STACK EMPTY] Fetching new articles after: {saved_ts}")

    TOP_N    = 6
    all_data = []

    all_data.extend(fetch_zerodha()[:TOP_N])
    all_data.extend(fetch_cnbc()[:TOP_N])
    all_data.extend(fetch_5paisa()[:TOP_N])
    all_data.extend(fetch_livemint()[:TOP_N])
    all_data.extend(fetch_nse_corporate()[:TOP_N])

    filtered_data, source = filter_by_country_and_category(
        all_data, selected_country, category
    )
    print(f"After country+category filter: {len(filtered_data)} (source={source})")

    used_titles = load_used_titles()
    fresh = [
        item for item in filtered_data
        if normalize_title(item.get("Blog_Title", "")) not in used_titles
    ]

    if fresh:
        save_stack(fresh)
        save_timestamp()
        print(f"[STACK] Refilled with {len(fresh)} new articles")
    else:
        print("[STACK] Abhi koi naya article nahi — 5 min baad retry karega")

    return fresh


# ── Normalize Title ───────────────────────────────────────────
def normalize_title(title):
    title = title.strip().lower()
    title = re.sub(r'\s+', ' ', title)
    return title


# ── Load used titles — reads from correct file based on mode ──
def load_used_titles():
    filepath = f"output/{OUTPUT_FILENAME}"
    if not os.path.exists(filepath):
        return set()
    with open(filepath, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
            return {
                normalize_title(item.get("Blog_Title", ""))
                for item in data
            }
        except:
            return set()


# ── Utility ───────────────────────────────────────────────────
def clean_filename(text):
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r'[\\/*?:"<>|]', '', text)
    text = text.replace(" ", "_")
    text = re.sub(r'_+', '_', text)
    return text[:60]


# ── Timed wrappers ────────────────────────────────────────────
@timed
def _generate_blog(item):
    return generate_blog(item)

@timed
def _generate_notification(item):
    return generate_notification(item)

@timed
def _generate_instagram(item):
    return generate_instagram_caption(item)

@timed
def _extract_image_text(title, content, category):
    return extract_image_text(title, content, category)

@timed
def _select_template_pair_smart(category, title, content=""):
    # ── Smart selection using descriptions + OpenAI ───────────
    # Falls back to MD5 if descriptions missing or API fails
    return select_template_pair_smart(category, title, content)

@timed
def _compose_image(template, image_text, jpg_path, webp_path, image_type):
    return compose_image(template, image_text, jpg_path, webp_path, image_type=image_type)

@timed
def _generate_ai_image(blog_title, blog_content, blog_outer_paths, blog_inner_paths, instagram_paths, quality="medium"):
    return generate_ai_image(blog_title, blog_content, blog_outer_paths, blog_inner_paths, instagram_paths, quality)

@timed
def _save_output(item, filename):
    return save_output(item, filename=filename)

@timed
def _filter_combined(data, country, category):
    return filter_by_country_and_category(data, country, category)


# ── Main pipeline ─────────────────────────────────────────────
def run_pipeline(selected_country="India", category="finance"):

    reset_timings()
    os.makedirs(OUTPUT_IMG_DIR,      exist_ok=True)
    os.makedirs(OUTPUT_IMG_JPG_DIR,  exist_ok=True)
    os.makedirs(OUTPUT_IMG_WEBP_DIR, exist_ok=True)
    results = []

    # ── Stack load karo ──────────────────────────────────────
    stack = load_stack()
    print(f"[STACK] {len(stack)} articles remaining in stack")

    # ── Stack empty hai → decide karo kya karna hai ──────────
    if not stack:
        saved_ts = load_timestamp()

        if saved_ts is None:
            print("[STACK] Pehli baar start — full fetch karo...")
            stack = _full_fetch_and_build_stack(selected_country, category)
        else:
            print(f"[STACK] Empty — timestamp ke baad fetch karo: {saved_ts}")
            stack = _fetch_after_timestamp(selected_country, category, saved_ts)

        # ── Fallback Zerodha ──────────────────────────────────
        # ── Fallback Zerodha ──────────────────────────────────
        if not stack:
            print("[WAITING] Koi naya article nahi mila — fallback Zerodha...")

            zerodha_data = fetch_zerodha()
            if not zerodha_data:
                return []

            final_item = random.choice(zerodha_data)

            final_item["blog"]             = clean_newlines(generate_blog(final_item))
            final_item["notify"]           = clean_newlines(generate_notification(final_item))
            final_item["instagram_notify"] = clean_newlines(generate_instagram_caption(final_item))
            final_item["Run_Timestamp"]    = get_run_timestamp()

            safe_title = clean_filename(final_item["Blog_Title"])

            if USE_AI_IMAGES:
                # ── AI Image Generation ───────────────────────
                blog_outer_jpg  = os.path.join(OUTPUT_IMG_JPG_DIR,  f"blog_outer_{safe_title}.jpg")
                blog_outer_webp = os.path.join(OUTPUT_IMG_WEBP_DIR, f"blog_outer_{safe_title}.webp")
                blog_inner_jpg  = os.path.join(OUTPUT_IMG_JPG_DIR,  f"blog_inner_{safe_title}.jpg")
                blog_inner_webp = os.path.join(OUTPUT_IMG_WEBP_DIR, f"blog_inner_{safe_title}.webp")
                insta_jpg       = os.path.join(OUTPUT_IMG_JPG_DIR,  f"insta_{safe_title}.jpg")
                insta_webp      = os.path.join(OUTPUT_IMG_WEBP_DIR, f"insta_{safe_title}.webp")

                images = generate_ai_image(
                    final_item["Blog_Title"],
                    final_item.get("Blog_Content", ""),
                    blog_outer_paths = {"jpg": blog_outer_jpg,  "webp": blog_outer_webp},
                    blog_inner_paths = {"jpg": blog_inner_jpg,  "webp": blog_inner_webp},
                    instagram_paths  = {"jpg": insta_jpg,       "webp": insta_webp},
                    quality          = "medium"
                )
                final_item["blog_image_outer"] = images["blog_outer"]
                final_item["blog_image_inner"] = images["blog_inner"]
                final_item["instagram_image"]  = images["instagram"]

            else:
                # ── Template Image Generation ─────────────────
                image_text = extract_image_text(
                    final_item["Blog_Title"],
                    final_item.get("Blog_Content", ""),
                    category.upper()
                )
                final_item["image_text"] = image_text

                template_pair  = select_template_pair_smart(
                    category,
                    final_item["Blog_Title"],
                    final_item.get("Blog_Content", "")
                )
                outer_template = template_pair["outer"]
                inner_template = template_pair["inner"]

                final_item["blog_image"] = compose_image(
                    outer_template, image_text,
                    os.path.join(OUTPUT_IMG_JPG_DIR,  f"blog_{safe_title}.jpg"),
                    os.path.join(OUTPUT_IMG_WEBP_DIR, f"blog_{safe_title}.webp"),
                    image_type="blog"
                )
                final_item["blog_image_inner"] = compose_image(
                    inner_template, {},
                    os.path.join(OUTPUT_IMG_JPG_DIR,  f"blog_inner_{safe_title}.jpg"),
                    os.path.join(OUTPUT_IMG_WEBP_DIR, f"blog_inner_{safe_title}.webp"),
                    image_type="blog_inner"
                )
                final_item["instagram_image"] = compose_image(
                    outer_template, image_text,
                    os.path.join(OUTPUT_IMG_JPG_DIR,  f"insta_{safe_title}.jpg"),
                    os.path.join(OUTPUT_IMG_WEBP_DIR, f"insta_{safe_title}.webp"),
                    image_type="instagram"
                )

            save_output(final_item, filename=OUTPUT_FILENAME)
            return [final_item]

    # ── Stack se ek random article pop karo ──────────────────
    final_item, stack = pop_from_stack(stack)
    save_stack(stack)
    print(f"[POPPED]  {final_item.get('Blog_Title', '')[:60]}")
    print(f"[STACK]   {len(stack)} articles remaining")

    final_category = category

    # ── Used titles check karo ────────────────────────────────
    used_titles = load_used_titles()

    if normalize_title(final_item.get("Blog_Title", "")) in used_titles:
        print("[SKIPPED] Title already used — next cycle me try karega")
        return []

    print(f"[SELECTED] Fresh blog: {final_item.get('Blog_Title', '')[:50]}")

    try:
        # ── AI Content Generation ─────────────────────────────
        final_item["blog"]             = clean_newlines(_generate_blog(final_item))
        final_item["notify"]           = clean_newlines(_generate_notification(final_item))
        final_item["instagram_notify"] = clean_newlines(_generate_instagram(final_item))

        # ── File paths ────────────────────────────────────────
        safe_title = clean_filename(final_item["Blog_Title"])

        if USE_AI_IMAGES:
            # ══════════════════════════════════════════════════
            # AI Image Generation
            # Saves to → testing_webp_output.json
            # ══════════════════════════════════════════════════
            print(f"[IMAGE MODE] AI generated images → {OUTPUT_FILENAME}")

            blog_outer_jpg  = os.path.join(OUTPUT_IMG_JPG_DIR,  f"blog_outer_{safe_title}.jpg")
            blog_outer_webp = os.path.join(OUTPUT_IMG_WEBP_DIR, f"blog_outer_{safe_title}.webp")
            blog_inner_jpg  = os.path.join(OUTPUT_IMG_JPG_DIR,  f"blog_inner_{safe_title}.jpg")
            blog_inner_webp = os.path.join(OUTPUT_IMG_WEBP_DIR, f"blog_inner_{safe_title}.webp")
            insta_jpg       = os.path.join(OUTPUT_IMG_JPG_DIR,  f"insta_{safe_title}.jpg")
            insta_webp      = os.path.join(OUTPUT_IMG_WEBP_DIR, f"insta_{safe_title}.webp")

            images = _generate_ai_image(
                final_item["Blog_Title"],
                final_item.get("Blog_Content", ""),
                blog_outer_paths = {"jpg": blog_outer_jpg,  "webp": blog_outer_webp},
                blog_inner_paths = {"jpg": blog_inner_jpg,  "webp": blog_inner_webp},
                instagram_paths  = {"jpg": insta_jpg,       "webp": insta_webp},
                quality          = "medium"
            )

            final_item["blog_image_outer"] = images["blog_outer"]
            final_item["blog_image_inner"] = images["blog_inner"]
            final_item["instagram_image"]  = images["instagram"]

        else:
            # ══════════════════════════════════════════════════
            # Template Image Generation
            # Saves to → output.json
            # ══════════════════════════════════════════════════
            print(f"[IMAGE MODE] Template based images → {OUTPUT_FILENAME}")

            final_item["image_text"] = _extract_image_text(
                final_item["Blog_Title"],
                final_item.get("Blog_Content", ""),
                final_category.upper()
            )

            # ── Smart template selection ──────────────────────
            # Reads image_descriptions.json → OpenAI picks best match
            # Falls back to MD5 if file missing or API fails
            template_pair  = _select_template_pair_smart(
                final_category,
                final_item["Blog_Title"],
                final_item.get("Blog_Content", "") # ← pass content
                
            )
            outer_template = template_pair["outer"]
            inner_template = template_pair["inner"]

            blog_jpg_path        = os.path.join(OUTPUT_IMG_JPG_DIR,  f"blog_{safe_title}.jpg")
            blog_webp_path       = os.path.join(OUTPUT_IMG_WEBP_DIR, f"blog_{safe_title}.webp")
            blog_inner_jpg_path  = os.path.join(OUTPUT_IMG_JPG_DIR,  f"blog_inner_{safe_title}.jpg")
            blog_inner_webp_path = os.path.join(OUTPUT_IMG_WEBP_DIR, f"blog_inner_{safe_title}.webp")
            insta_jpg_path       = os.path.join(OUTPUT_IMG_JPG_DIR,  f"insta_{safe_title}.jpg")
            insta_webp_path      = os.path.join(OUTPUT_IMG_WEBP_DIR, f"insta_{safe_title}.webp")

            # ── Blog Outer (640×480) + text ───────────────────
            print(f"[IMAGE] Blog outer → {os.path.basename(outer_template)}")
            final_item["blog_image"] = _compose_image(
                outer_template,
                final_item["image_text"],
                blog_jpg_path,
                blog_webp_path,
                "blog"
            )

            # ── Blog Inner (1920×490) plain ───────────────────
            print(f"[IMAGE] Blog inner → {os.path.basename(inner_template)}")
            final_item["blog_image_inner"] = _compose_image(
                inner_template,
                {},
                blog_inner_jpg_path,
                blog_inner_webp_path,
                "blog_inner"
            )

            # ── Instagram (1080×1080) + text ──────────────────
            print(f"[IMAGE] Instagram → {os.path.basename(outer_template)}")
            final_item["instagram_image"] = _compose_image(
                outer_template,
                final_item["image_text"],
                insta_jpg_path,
                insta_webp_path,
                "instagram"
            )

        final_item["Run_Timestamp"] = get_run_timestamp()

        # ── Save to correct file based on mode ────────────────
        saved = _save_output(final_item, OUTPUT_FILENAME)

        if saved:
            results.append(final_item)
            print(f"[DONE] Blog saved to output/{OUTPUT_FILENAME}")
            print(f"[DONE] {final_item['Blog_Title'][:60]}")
        else:
            print(f"[SKIPPED PIPELINE] Already exists: {final_item['Blog_Title'][:60]}")

    except Exception as e:
        print(f"[ERROR] {e}")

    print_timing_summary()
    return results


























# import os
# import random
# import re
# import unicodedata
# import json
# from datetime import datetime

# from RSS.zerodha import fetch_zerodha
# from RSS.cnbc import fetch_cnbc
# from RSS.paisa import fetch_5paisa
# from RSS.livemint import fetch_livemint
# from RSS.fetch_nse_corporate import fetch_nse_corporate

# from content_engine.image_module.text_extractor import extract_image_text
# from content_engine.image_module.tempalte_selector import select_template, select_template_pair
# from content_engine.image_module.compositor import compose_image
# from content_engine.image_module.validator import validate_template

# from utils.combined_filter import filter_by_country_and_category
# from AI_GEN.notify_generator import generate_notification
# from AI_GEN.generate_instagram_caption import generate_instagram_caption
# from AI_GEN.get_system_timestamp import get_run_timestamp
# from AI_GEN.blog_generator import generate_blog
# from storage.save_output import save_output
# from utils.timer import timed, Timer, print_timing_summary, reset_timings


# # ── Base directory ────────────────────────────────────────────
# BASE_DIR            = os.path.dirname(os.path.abspath(__file__))
# OUTPUT_IMG_DIR      = os.path.join(BASE_DIR, "output_images")
# OUTPUT_IMG_JPG_DIR  = os.path.join(BASE_DIR, "output_images", "jpg_images")
# OUTPUT_IMG_WEBP_DIR = os.path.join(BASE_DIR, "output_images", "webp_images")
# STACK_FILE          = os.path.join(BASE_DIR, "output", "article_stack.json")
# TIMESTAMP_FILE      = os.path.join(BASE_DIR, "output", "stack_timestamp.json")


# # ══════════════════════════════════════════════════════════════
# # Stack helpers
# # ══════════════════════════════════════════════════════════════

# def save_stack(stack):
#     os.makedirs(os.path.dirname(STACK_FILE), exist_ok=True)
#     with open(STACK_FILE, "w", encoding="utf-8") as f:
#         json.dump(stack, f, ensure_ascii=False, indent=2)
#     print(f"[STACK] {len(stack)} articles saved to disk")


# def load_stack():
#     if not os.path.exists(STACK_FILE):
#         return []
#     with open(STACK_FILE, "r", encoding="utf-8") as f:
#         try:
#             return json.load(f)
#         except:
#             return []


# def pop_from_stack(stack):
#     if not stack:
#         return None, stack
#     item = random.choice(stack)
#     stack.remove(item)
#     return item, stack


# def save_timestamp():
#     os.makedirs(os.path.dirname(TIMESTAMP_FILE), exist_ok=True)
#     ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#     with open(TIMESTAMP_FILE, "w") as f:
#         json.dump({"stack_built_at": ts}, f)
#     print(f"[TIMESTAMP] Stack built at: {ts}")
#     return ts


# def load_timestamp():
#     if not os.path.exists(TIMESTAMP_FILE):
#         return None
#     with open(TIMESTAMP_FILE, "r") as f:
#         try:
#             data = json.load(f)
#             return data.get("stack_built_at")
#         except:
#             return None


# # ══════════════════════════════════════════════════════════════
# # Pehli baar full fetch karke stack banao
# # ══════════════════════════════════════════════════════════════

# def _full_fetch_and_build_stack(selected_country, category):
#     print("\n" + "="*50)
#     print("  PHASE 1 — BUILDING FRESH STACK")
#     print("="*50)

#     TOP_N    = 6
#     all_data = []

#     with Timer("fetch_zerodha"):       all_data.extend(fetch_zerodha()[:TOP_N])
#     with Timer("fetch_cnbc"):          all_data.extend(fetch_cnbc()[:TOP_N])
#     with Timer("fetch_5paisa"):        all_data.extend(fetch_5paisa()[:TOP_N])
#     with Timer("fetch_livemint"):      all_data.extend(fetch_livemint()[:TOP_N])
#     with Timer("fetch_nse_corporate"): all_data.extend(fetch_nse_corporate()[:TOP_N])

#     print(f"Total collected: {len(all_data)}")

#     filtered_data, source = filter_by_country_and_category(
#         all_data, selected_country, category
#     )
#     print(f"After country+category filter: {len(filtered_data)} (source={source})")

#     used_titles = load_used_titles()
#     fresh = [
#         item for item in filtered_data
#         if normalize_title(item.get("Blog_Title", "")) not in used_titles
#     ]
#     print(f"Fresh unique articles: {len(fresh)}")

#     if fresh:
#         save_stack(fresh)
#         save_timestamp()
#         print(f"[STACK] Built with {len(fresh)} articles!")
#     else:
#         print("[STACK] No fresh articles found!")

#     print("="*50 + "\n")
#     return fresh


# # ══════════════════════════════════════════════════════════════
# # Stack empty hone ke baad timestamp ke baad fetch karo
# # ══════════════════════════════════════════════════════════════

# def _fetch_after_timestamp(selected_country, category, saved_ts):
#     print(f"\n[STACK EMPTY] Fetching new articles after: {saved_ts}")

#     TOP_N    = 6
#     all_data = []

#     all_data.extend(fetch_zerodha()[:TOP_N])
#     all_data.extend(fetch_cnbc()[:TOP_N])
#     all_data.extend(fetch_5paisa()[:TOP_N])
#     all_data.extend(fetch_livemint()[:TOP_N])
#     all_data.extend(fetch_nse_corporate()[:TOP_N])

#     filtered_data, source = filter_by_country_and_category(
#         all_data, selected_country, category
#     )
#     print(f"After country+category filter: {len(filtered_data)} (source={source})")

#     used_titles = load_used_titles()
#     fresh = [
#         item for item in filtered_data
#         if normalize_title(item.get("Blog_Title", "")) not in used_titles
#     ]

#     if fresh:
#         save_stack(fresh)
#         save_timestamp()
#         print(f"[STACK] Refilled with {len(fresh)} new articles")
#     else:
#         print("[STACK] Abhi koi naya article nahi — 5 min baad retry karega")

#     return fresh


# # ── Normalize Title ───────────────────────────────────────────
# def normalize_title(title):
#     title = title.strip().lower()
#     title = re.sub(r'\s+', ' ', title)
#     return title


# # ── Load used titles ──────────────────────────────────────────
# def load_used_titles(filepath="output/output.json"):
#     if not os.path.exists(filepath):
#         return set()
#     with open(filepath, "r", encoding="utf-8") as f:
#         try:
#             data = json.load(f)
#             return {
#                 normalize_title(item.get("Blog_Title", ""))
#                 for item in data
#             }
#         except:
#             return set()


# # ── Utility ───────────────────────────────────────────────────
# def clean_filename(text):
#     text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
#     text = re.sub(r'[\\/*?:"<>|]', '', text)
#     text = text.replace(" ", "_")
#     text = re.sub(r'_+', '_', text)
#     return text[:60]


# # ── Timed wrappers ────────────────────────────────────────────
# @timed
# def _generate_blog(item):
#     return generate_blog(item)

# @timed
# def _generate_notification(item):
#     return generate_notification(item)

# @timed
# def _generate_instagram(item):
#     return generate_instagram_caption(item)

# @timed
# def _extract_image_text(title, content, category):
#     return extract_image_text(title, content, category)

# @timed
# def _select_template_pair(category, title):
#     return select_template_pair(category, title)

# @timed
# def _compose_image(template, image_text, jpg_path, webp_path, image_type):
#     return compose_image(template, image_text, jpg_path, webp_path, image_type=image_type)

# @timed
# def _save_output(item):
#     return save_output(item)

# @timed
# def _filter_combined(data, country, category):
#     return filter_by_country_and_category(data, country, category)


# # ── Main pipeline ─────────────────────────────────────────────
# def run_pipeline(selected_country="India", category="finance"):

#     reset_timings()
#     os.makedirs(OUTPUT_IMG_DIR,      exist_ok=True)
#     os.makedirs(OUTPUT_IMG_JPG_DIR,  exist_ok=True)
#     os.makedirs(OUTPUT_IMG_WEBP_DIR, exist_ok=True)
#     results = []

#     # ── Stack load karo ──────────────────────────────────────
#     stack = load_stack()
#     print(f"[STACK] {len(stack)} articles remaining in stack")

#     # ── Stack empty hai → decide karo kya karna hai ──────────
#     if not stack:
#         saved_ts = load_timestamp()

#         if saved_ts is None:
#             print("[STACK] Pehli baar start — full fetch karo...")
#             stack = _full_fetch_and_build_stack(selected_country, category)
#         else:
#             print(f"[STACK] Empty — timestamp ke baad fetch karo: {saved_ts}")
#             stack = _fetch_after_timestamp(selected_country, category, saved_ts)

#         # ── Fallback Zerodha ──────────────────────────────────
#         if not stack:
#             print("[WAITING] Koi naya article nahi mila — fallback Zerodha...")

#             zerodha_data = fetch_zerodha()
#             if not zerodha_data:
#                 return []

#             final_item = random.choice(zerodha_data)

#             final_item["blog"]             = generate_blog(final_item)
#             final_item["notify"]           = generate_notification(final_item)
#             final_item["instagram_notify"] = generate_instagram_caption(final_item)
#             final_item["Run_Timestamp"]    = get_run_timestamp()

#             save_output(final_item)
#             return [final_item]

#     # ── Stack se ek random article pop karo ──────────────────
#     final_item, stack = pop_from_stack(stack)
#     save_stack(stack)
#     print(f"[POPPED]  {final_item.get('Blog_Title', '')[:60]}")
#     print(f"[STACK]   {len(stack)} articles remaining")

#     final_category = category

#     # ── Used titles check karo ────────────────────────────────
#     used_titles = load_used_titles()

#     if normalize_title(final_item.get("Blog_Title", "")) in used_titles:
#         print("[SKIPPED] Title already used — next cycle me try karega")
#         return []

#     print(f"[SELECTED] Fresh blog: {final_item.get('Blog_Title', '')[:50]}")

#     try:
#         # ── AI Content Generation ─────────────────────────────
#         final_item["blog"]             = _generate_blog(final_item)
#         final_item["notify"]           = _generate_notification(final_item)
#         final_item["instagram_notify"] = _generate_instagram(final_item)

#         # ── Extract image text ────────────────────────────────
#         final_item["image_text"] = _extract_image_text(
#             final_item["Blog_Title"],
#             final_item.get("Blog_Content", ""),
#             final_category.upper()
#         )

#         # ── Select template pair (outer + inner) ──────────────
#         # outer/ → 640×480 templates  (blog + instagram)
#         # inner/ → 1920×490 templates (blog_inner only)
#         template_pair  = _select_template_pair(
#             final_category,
#             final_item["Blog_Title"]
#         )
#         outer_template = template_pair["outer"]
#         inner_template = template_pair["inner"]

#         # validate_template(outer_template)
#         # validate_template(inner_template)

#         # ── File paths ────────────────────────────────────────
#         safe_title = clean_filename(final_item["Blog_Title"])

#         blog_jpg_path        = os.path.join(OUTPUT_IMG_JPG_DIR,  f"blog_{safe_title}.jpg")
#         blog_webp_path       = os.path.join(OUTPUT_IMG_WEBP_DIR, f"blog_{safe_title}.webp")
#         blog_inner_jpg_path  = os.path.join(OUTPUT_IMG_JPG_DIR,  f"blog_inner_{safe_title}.jpg")
#         blog_inner_webp_path = os.path.join(OUTPUT_IMG_WEBP_DIR, f"blog_inner_{safe_title}.webp")
#         insta_jpg_path       = os.path.join(OUTPUT_IMG_JPG_DIR,  f"insta_{safe_title}.jpg")
#         insta_webp_path      = os.path.join(OUTPUT_IMG_WEBP_DIR, f"insta_{safe_title}.webp")

#         # ── Blog Outer (640×480) — outer template + text ──────
#         print(f"[IMAGE] Blog outer → {os.path.basename(outer_template)}")
#         final_item["blog_image"] = _compose_image(
#             outer_template,
#             final_item["image_text"],
#             blog_jpg_path,
#             blog_webp_path,
#             "blog"
#         )

#         # ── Blog Inner (1920×490) — inner template + NO text ──
#         print(f"[IMAGE] Blog inner → {os.path.basename(inner_template)}")
#         final_item["blog_image_inner"] = _compose_image(
#             inner_template,
#             {},
#             blog_inner_jpg_path,
#             blog_inner_webp_path,
#             "blog_inner"
#         )

#         # ── Instagram (1080×1080) — outer template + text ─────
#         print(f"[IMAGE] Instagram → {os.path.basename(outer_template)}")
#         final_item["instagram_image"] = _compose_image(
#             outer_template,
#             final_item["image_text"],
#             insta_jpg_path,
#             insta_webp_path,
#             "instagram"
#         )

#         final_item["Run_Timestamp"] = get_run_timestamp()

#         saved = _save_output(final_item)

#         if saved:
#             results.append(final_item)
#             print(f"[DONE] {final_item['Blog_Title'][:60]}")
#         else:
#             print(f"[SKIPPED PIPELINE] Already exists: {final_item['Blog_Title'][:60]}")

#     except Exception as e:
#         print(f"[ERROR] {e}")

#     print_timing_summary()
#     return results




















# import os
# import random
# import re
# import unicodedata
# import json
# from datetime import datetime

# from RSS.zerodha import fetch_zerodha
# from RSS.cnbc import fetch_cnbc
# from RSS.paisa import fetch_5paisa
# from RSS.livemint import fetch_livemint
# from RSS.fetch_nse_corporate import fetch_nse_corporate

# from utils.combined_filter import filter_by_country_and_category
# from AI_GEN.notify_generator import generate_notification
# from AI_GEN.generate_instagram_caption import generate_instagram_caption
# from AI_GEN.get_system_timestamp import get_run_timestamp
# from AI_GEN.blog_generator import generate_blog
# from content_engine.image_module.ai_image_generator import generate_ai_image
# from content_engine.image_module.text_extractor import extract_image_text
# from content_engine.image_module.tempalte_selector import select_template
# from content_engine.image_module.compositor import compose_image
# from content_engine.image_module.validator import validate_template
# from storage.save_output import save_output
# from utils.timer import timed, Timer, print_timing_summary, reset_timings


# # ── Base directory ────────────────────────────────────────────
# BASE_DIR            = os.path.dirname(os.path.abspath(__file__))
# OUTPUT_IMG_DIR      = os.path.join(BASE_DIR, "output_images")
# OUTPUT_IMG_JPG_DIR  = os.path.join(BASE_DIR, "output_images", "jpg_images")
# OUTPUT_IMG_WEBP_DIR = os.path.join(BASE_DIR, "output_images", "webp_images")
# STACK_FILE          = os.path.join(BASE_DIR, "output", "article_stack.json")
# TIMESTAMP_FILE      = os.path.join(BASE_DIR, "output", "stack_timestamp.json")

# # ── Image generation mode ─────────────────────────────────────
# # True  → AI generated images (unique, costs money, slower)
# # False → Template based images (fast, free, uses local templates)
# USE_AI_IMAGES = False


# # ══════════════════════════════════════════════════════════════
# # Stack helpers
# # ══════════════════════════════════════════════════════════════

# def save_stack(stack):
#     os.makedirs(os.path.dirname(STACK_FILE), exist_ok=True)
#     with open(STACK_FILE, "w", encoding="utf-8") as f:
#         json.dump(stack, f, ensure_ascii=False, indent=2)
#     print(f"[STACK] {len(stack)} articles saved to disk")


# def load_stack():
#     if not os.path.exists(STACK_FILE):
#         return []
#     with open(STACK_FILE, "r", encoding="utf-8") as f:
#         try:
#             return json.load(f)
#         except:
#             return []


# def pop_from_stack(stack):
#     if not stack:
#         return None, stack
#     item = random.choice(stack)
#     stack.remove(item)
#     return item, stack


# def save_timestamp():
#     os.makedirs(os.path.dirname(TIMESTAMP_FILE), exist_ok=True)
#     ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#     with open(TIMESTAMP_FILE, "w") as f:
#         json.dump({"stack_built_at": ts}, f)
#     print(f"[TIMESTAMP] Stack built at: {ts}")
#     return ts


# def load_timestamp():
#     if not os.path.exists(TIMESTAMP_FILE):
#         return None
#     with open(TIMESTAMP_FILE, "r") as f:
#         try:
#             data = json.load(f)
#             return data.get("stack_built_at")
#         except:
#             return None


# # ══════════════════════════════════════════════════════════════
# # Pehli baar full fetch karke stack banao
# # ══════════════════════════════════════════════════════════════

# def _full_fetch_and_build_stack(selected_country, category):
#     print("\n" + "="*50)
#     print("  PHASE 1 — BUILDING FRESH STACK")
#     print("="*50)

#     TOP_N    = 20
#     all_data = []

#     with Timer("fetch_zerodha"):       all_data.extend(fetch_zerodha()[:TOP_N])
#     with Timer("fetch_cnbc"):          all_data.extend(fetch_cnbc()[:TOP_N])
#     with Timer("fetch_5paisa"):        all_data.extend(fetch_5paisa()[:TOP_N])
#     with Timer("fetch_livemint"):      all_data.extend(fetch_livemint()[:TOP_N])
#     with Timer("fetch_nse_corporate"): all_data.extend(fetch_nse_corporate()[:TOP_N])

#     print(f"Total collected: {len(all_data)}")

#     filtered_data, source = filter_by_country_and_category(
#         all_data, selected_country, category
#     )
#     print(f"After country+category filter: {len(filtered_data)} (source={source})")

#     used_titles = load_used_titles()
#     fresh = [
#         item for item in filtered_data
#         if normalize_title(item.get("Blog_Title", "")) not in used_titles
#     ]
#     print(f"Fresh unique articles: {len(fresh)}")

#     if fresh:
#         save_stack(fresh)
#         save_timestamp()
#         print(f"[STACK] Built with {len(fresh)} articles!")
#     else:
#         print("[STACK] No fresh articles found!")

#     print("="*50 + "\n")
#     return fresh


# # ══════════════════════════════════════════════════════════════
# # Stack empty hone ke baad timestamp ke baad fetch karo
# # ══════════════════════════════════════════════════════════════

# def _fetch_after_timestamp(selected_country, category, saved_ts):
#     print(f"\n[STACK EMPTY] Fetching new articles after: {saved_ts}")

#     TOP_N    = 6
#     all_data = []

#     all_data.extend(fetch_zerodha()[:TOP_N])
#     all_data.extend(fetch_cnbc()[:TOP_N])
#     all_data.extend(fetch_5paisa()[:TOP_N])
#     all_data.extend(fetch_livemint()[:TOP_N])
#     all_data.extend(fetch_nse_corporate()[:TOP_N])

#     filtered_data, source = filter_by_country_and_category(
#         all_data, selected_country, category
#     )
#     print(f"After country+category filter: {len(filtered_data)} (source={source})")

#     used_titles = load_used_titles()
#     fresh = [
#         item for item in filtered_data
#         if normalize_title(item.get("Blog_Title", "")) not in used_titles
#     ]

#     if fresh:
#         save_stack(fresh)
#         save_timestamp()
#         print(f"[STACK] Refilled with {len(fresh)} new articles")
#     else:
#         print("[STACK] Abhi koi naya article nahi — 5 min baad retry karega")

#     return fresh


# # ── Normalize Title ───────────────────────────────────────────
# def normalize_title(title):
#     title = title.strip().lower()
#     title = re.sub(r'\s+', ' ', title)
#     return title


# # ── Load used titles ──────────────────────────────────────────
# def load_used_titles(filepath="output/testing_webp_output.json"):
#     if not os.path.exists(filepath):
#         return set()
#     with open(filepath, "r", encoding="utf-8") as f:
#         try:
#             data = json.load(f)
#             return {
#                 normalize_title(item.get("Blog_Title", ""))
#                 for item in data
#             }
#         except:
#             return set()


# # ── Utility ───────────────────────────────────────────────────
# def clean_filename(text):
#     text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
#     text = re.sub(r'[\\/*?:"<>|]', '', text)
#     text = text.replace(" ", "_")
#     text = re.sub(r'_+', '_', text)
#     return text[:60]


# # ── Timed wrappers ────────────────────────────────────────────
# @timed
# def _generate_blog(item):
#     return generate_blog(item)

# @timed
# def _generate_notification(item):
#     return generate_notification(item)

# @timed
# def _generate_instagram(item):
#     return generate_instagram_caption(item)

# @timed
# def _generate_ai_image(blog_title, blog_content, blog_outer_paths, blog_inner_paths, instagram_paths, quality="medium"):
#     return generate_ai_image(blog_title, blog_content, blog_outer_paths, blog_inner_paths, instagram_paths, quality)

# @timed
# def _extract_image_text(title, content, category):
#     return extract_image_text(title, content, category)

# @timed
# def _select_template(category, title):
#     return select_template(category, title)

# @timed
# def _compose_image(template, image_text, jpg_path, webp_path, image_type):
#     return compose_image(template, image_text, jpg_path, webp_path, image_type=image_type)

# @timed
# def _save_output(item):
#     return save_output(item)

# @timed
# def _filter_combined(data, country, category):
#     return filter_by_country_and_category(data, country, category)


# # ── Main pipeline ─────────────────────────────────────────────
# def run_pipeline(selected_country="India", category="finance"):

#     reset_timings()
#     os.makedirs(OUTPUT_IMG_DIR,      exist_ok=True)
#     os.makedirs(OUTPUT_IMG_JPG_DIR,  exist_ok=True)
#     os.makedirs(OUTPUT_IMG_WEBP_DIR, exist_ok=True)
#     results = []

#     # ── Stack load karo ──────────────────────────────────────
#     stack = load_stack()
#     print(f"[STACK] {len(stack)} articles remaining in stack")

#     # ── Stack empty hai → decide karo kya karna hai ──────────
#     if not stack:
#         saved_ts = load_timestamp()

#         if saved_ts is None:
#             print("[STACK] Pehli baar start — full fetch karo...")
#             stack = _full_fetch_and_build_stack(selected_country, category)
#         else:
#             print(f"[STACK] Empty — timestamp ke baad fetch karo: {saved_ts}")
#             stack = _fetch_after_timestamp(selected_country, category, saved_ts)

#         # ── Fallback Zerodha ──────────────────────────────────
#         if not stack:
#             print("[WAITING] Koi naya article nahi mila — fallback Zerodha...")

#             zerodha_data = fetch_zerodha()
#             if not zerodha_data:
#                 return []

#             final_item = random.choice(zerodha_data)

#             final_item["blog"]             = generate_blog(final_item)
#             final_item["notify"]           = generate_notification(final_item)
#             final_item["instagram_notify"] = generate_instagram_caption(final_item)
#             final_item["Run_Timestamp"]    = get_run_timestamp()

#             save_output(final_item)
#             return [final_item]

#     # ── Stack se ek random article pop karo ──────────────────
#     final_item, stack = pop_from_stack(stack)
#     save_stack(stack)
#     print(f"[POPPED]  {final_item.get('Blog_Title', '')[:60]}")
#     print(f"[STACK]   {len(stack)} articles remaining")

#     final_category = category

#     # ── Used titles check karo ────────────────────────────────
#     used_titles = load_used_titles()

#     if normalize_title(final_item.get("Blog_Title", "")) in used_titles:
#         print("[SKIPPED] Title already used — next cycle me try karega")
#         return []

#     print(f"[SELECTED] Fresh blog: {final_item.get('Blog_Title', '')[:50]}")

#     try:
#         # ── AI Content Generation ─────────────────────────────
#         final_item["blog"]             = _generate_blog(final_item)
#         final_item["notify"]           = _generate_notification(final_item)
#         final_item["instagram_notify"] = _generate_instagram(final_item)

#         # ── File paths ────────────────────────────────────────
#         safe_title = clean_filename(final_item["Blog_Title"])

#         if USE_AI_IMAGES:
#             # ── AI Image Generation ───────────────────────────
#             print(f"[IMAGE MODE] AI generated images")

#             blog_outer_jpg  = os.path.join(OUTPUT_IMG_JPG_DIR,  f"blog_outer_{safe_title}.jpg")
#             blog_outer_webp = os.path.join(OUTPUT_IMG_WEBP_DIR, f"blog_outer_{safe_title}.webp")
#             blog_inner_jpg  = os.path.join(OUTPUT_IMG_JPG_DIR,  f"blog_inner_{safe_title}.jpg")
#             blog_inner_webp = os.path.join(OUTPUT_IMG_WEBP_DIR, f"blog_inner_{safe_title}.webp")
#             insta_jpg       = os.path.join(OUTPUT_IMG_JPG_DIR,  f"insta_{safe_title}.jpg")
#             insta_webp      = os.path.join(OUTPUT_IMG_WEBP_DIR, f"insta_{safe_title}.webp")

#             images = _generate_ai_image(
#                 final_item["Blog_Title"],
#                 final_item.get("Blog_Content", ""),
#                 blog_outer_paths = {"jpg": blog_outer_jpg,  "webp": blog_outer_webp},
#                 blog_inner_paths = {"jpg": blog_inner_jpg,  "webp": blog_inner_webp},
#                 instagram_paths  = {"jpg": insta_jpg,       "webp": insta_webp},
#                 quality          = "medium"
#             )

#             final_item["blog_image_outer"] = images["blog_outer"]
#             final_item["blog_image_inner"] = images["blog_inner"]
#             final_item["instagram_image"]  = images["instagram"]

#         else:
#             # ── Template Image Generation ─────────────────────
#             print(f"[IMAGE MODE] Template based images")

#             final_item["image_text"] = _extract_image_text(
#                 final_item["Blog_Title"],
#                 final_item.get("Blog_Content", ""),
#                 final_category.upper()
#             )

#             final_item["template_path"] = _select_template(
#                 final_category,
#                 final_item["Blog_Title"]
#             )

#             validate_template(final_item["template_path"])

#             blog_jpg_path   = os.path.join(OUTPUT_IMG_JPG_DIR,  f"blog_{safe_title}.jpg")
#             insta_jpg_path  = os.path.join(OUTPUT_IMG_JPG_DIR,  f"insta_{safe_title}.jpg")
#             blog_webp_path  = os.path.join(OUTPUT_IMG_WEBP_DIR, f"blog_{safe_title}.webp")
#             insta_webp_path = os.path.join(OUTPUT_IMG_WEBP_DIR, f"insta_{safe_title}.webp")

#             final_item["blog_image"] = _compose_image(
#                 final_item["template_path"],
#                 final_item["image_text"],
#                 blog_jpg_path,
#                 blog_webp_path,
#                 "blog"
#             )

#             final_item["instagram_image"] = _compose_image(
#                 final_item["template_path"],
#                 final_item["image_text"],
#                 insta_jpg_path,
#                 insta_webp_path,
#                 "instagram"
#             )

#         final_item["Run_Timestamp"] = get_run_timestamp()

#         saved = _save_output(final_item)

#         if saved:
#             results.append(final_item)
#             print(f"[DONE] {final_item['Blog_Title'][:60]}")
#         else:
#             print(f"[SKIPPED PIPELINE] Already exists: {final_item['Blog_Title'][:60]}")

#     except Exception as e:
#         print(f"[ERROR] {e}")

#     print_timing_summary()
#     return results












































































































































































































# import os
# import random
# import re
# import unicodedata
# import json
# import copy
# from datetime import datetime

# from RSS.zerodha import fetch_zerodha
# from RSS.cnbc import fetch_cnbc
# from RSS.paisa import fetch_5paisa
# from RSS.livemint import fetch_livemint
# from RSS.fetch_nse_corporate import fetch_nse_corporate

# from content_engine.image_module.text_extractor import extract_image_text
# from content_engine.image_module.tempalte_selector import select_template
# from content_engine.image_module.compositor import compose_image
# from content_engine.image_module.validator import validate_template

# from utils.combined_filter import filter_by_country_and_category  # ✅ one combined filter
# from AI_GEN.notify_generator import generate_notification
# from AI_GEN.generate_instagram_caption import generate_instagram_caption
# from AI_GEN.get_system_timestamp import get_run_timestamp
# from AI_GEN.blog_generator import generate_blog
# from storage.save_output import save_output
# from utils.timer import timed, Timer, print_timing_summary, reset_timings


# # ── Base directory ────────────────────────────────────────────
# BASE_DIR       = os.path.dirname(os.path.abspath(__file__))
# OUTPUT_IMG_DIR = os.path.join(BASE_DIR, "output_images")
# OUTPUT_IMG_JPG_DIR  = os.path.join(BASE_DIR, "output_images", "jpg_images")
# OUTPUT_IMG_WEBP_DIR = os.path.join(BASE_DIR, "output_images", "webp_images")
# STACK_FILE     = os.path.join(BASE_DIR, "output", "article_stack.json")
# TIMESTAMP_FILE = os.path.join(BASE_DIR, "output", "stack_timestamp.json")


# # ══════════════════════════════════════════════════════════════
# # Stack helpers
# # ══════════════════════════════════════════════════════════════

# def save_stack(stack):
#     os.makedirs(os.path.dirname(STACK_FILE), exist_ok=True)
#     with open(STACK_FILE, "w", encoding="utf-8") as f:
#         json.dump(stack, f, ensure_ascii=False, indent=2)
#     print(f"[STACK] {len(stack)} articles saved to disk")


# def load_stack():
#     if not os.path.exists(STACK_FILE):
#         return []
#     with open(STACK_FILE, "r", encoding="utf-8") as f:
#         try:
#             return json.load(f)
#         except:
#             return []


# def pop_from_stack(stack):
#     if not stack:
#         return None, stack
#     item = random.choice(stack)
#     stack.remove(item)
#     return item, stack


# def save_timestamp():
#     os.makedirs(os.path.dirname(TIMESTAMP_FILE), exist_ok=True)
#     ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#     with open(TIMESTAMP_FILE, "w") as f:
#         json.dump({"stack_built_at": ts}, f)
#     print(f"[TIMESTAMP] Stack built at: {ts}")
#     return ts


# def load_timestamp():
#     if not os.path.exists(TIMESTAMP_FILE):
#         return None
#     with open(TIMESTAMP_FILE, "r") as f:
#         try:
#             data = json.load(f)
#             return data.get("stack_built_at")
#         except:
#             return None


# # ══════════════════════════════════════════════════════════════
# # Pehli baar full fetch karke stack banao
# # ══════════════════════════════════════════════════════════════

# def _full_fetch_and_build_stack(selected_country, category):
#     print("\n" + "="*50)
#     print("  PHASE 1 — BUILDING FRESH STACK")
#     print("="*50)

#     TOP_N    = 20
#     all_data = []

#     with Timer("fetch_zerodha"):       all_data.extend(fetch_zerodha()[:TOP_N])
#     with Timer("fetch_cnbc"):          all_data.extend(fetch_cnbc()[:TOP_N])
#     with Timer("fetch_5paisa"):        all_data.extend(fetch_5paisa()[:TOP_N])
#     with Timer("fetch_livemint"):      all_data.extend(fetch_livemint()[:TOP_N])
#     with Timer("fetch_nse_corporate"): all_data.extend(fetch_nse_corporate()[:TOP_N])

#     print(f"Total collected: {len(all_data)}")

#     # ✅ Ek combined API call — country + category dono
#     filtered_data, source = filter_by_country_and_category(
#         all_data, selected_country, category
#     )
#     print(f"After country+category filter: {len(filtered_data)} (source={source})")

#     # Remove used titles
#     used_titles = load_used_titles()
#     fresh = [
#         item for item in filtered_data           # ✅ filtered_data use karo
#         if normalize_title(item.get("Blog_Title", "")) not in used_titles
#     ]
#     print(f"Fresh unique articles: {len(fresh)}")

#     if fresh:
#         save_stack(fresh)
#         save_timestamp()
#         print(f"[STACK] Built with {len(fresh)} articles!")
#     else:
#         print("[STACK] No fresh articles found!")

#     print("="*50 + "\n")
#     return fresh


# # ══════════════════════════════════════════════════════════════
# # Stack empty hone ke baad timestamp ke baad fetch karo
# # ══════════════════════════════════════════════════════════════

# def _fetch_after_timestamp(selected_country, category, saved_ts):
#     print(f"\n[STACK EMPTY] Fetching new articles after: {saved_ts}")

#     TOP_N    = 6
#     all_data = []

#     all_data.extend(fetch_zerodha()[:TOP_N])
#     all_data.extend(fetch_cnbc()[:TOP_N])
#     all_data.extend(fetch_5paisa()[:TOP_N])
#     all_data.extend(fetch_livemint()[:TOP_N])
#     all_data.extend(fetch_nse_corporate()[:TOP_N])

#     # ✅ Ek combined API call — country + category dono
#     filtered_data, source = filter_by_country_and_category(
#         all_data, selected_country, category
#     )
#     print(f"After country+category filter: {len(filtered_data)} (source={source})")

#     # Sirf naye unused articles
#     used_titles = load_used_titles()
#     fresh = [
#         item for item in filtered_data           # ✅ filtered_data use karo
#         if normalize_title(item.get("Blog_Title", "")) not in used_titles
#     ]

#     if fresh:
#         save_stack(fresh)
#         save_timestamp()
#         print(f"[STACK] Refilled with {len(fresh)} new articles")
#     else:
#         print("[STACK] Abhi koi naya article nahi — 5 min baad retry karega")

#     return fresh


# # ── Normalize Title ───────────────────────────────────────────
# def normalize_title(title):
#     title = title.strip().lower()
#     title = re.sub(r'\s+', ' ', title)
#     return title


# # ── Load used titles ──────────────────────────────────────────
# def load_used_titles(filepath="output/output.json"):
#     if not os.path.exists(filepath):
#         return set()
#     with open(filepath, "r", encoding="utf-8") as f:
#         try:
#             data = json.load(f)
#             return {
#                 normalize_title(item.get("Blog_Title", ""))
#                 for item in data
#             }
#         except:
#             return set()


# # ── Utility ───────────────────────────────────────────────────
# def clean_filename(text):
#     text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
#     text = re.sub(r'[\\/*?:"<>|]', '', text)
#     text = text.replace(" ", "_")
#     text = re.sub(r'_+', '_', text)
#     return text[:60]


# # ── Timed wrappers ────────────────────────────────────────────
# @timed
# def _generate_blog(item):
#     return generate_blog(item)

# @timed
# def _generate_notification(item):
#     return generate_notification(item)

# @timed
# def _generate_instagram(item):
#     return generate_instagram_caption(item)

# @timed
# def _extract_image_text(title, content, category):
#     return extract_image_text(title, content, category)

# @timed
# def _select_template(category, title):
#     return select_template(category, title)

# # @timed
# # def _compose_image(template, image_text, path, image_type):
# #     return compose_image(template, image_text, path, image_type=image_type)
# @timed
# def _compose_image(template, image_text, jpg_path, webp_path, image_type):
#     return compose_image(template, image_text, jpg_path, webp_path, image_type=image_type)

# @timed
# def _save_output(item):
#     return save_output(item)

# # ✅ Ek combined timed wrapper — dono filter ek saath
# @timed
# def _filter_combined(data, country, category):
#     return filter_by_country_and_category(data, country, category)


# # ── Main pipeline (har 5 min chalta hai) ─────────────────────
# def run_pipeline(selected_country="India", category="finance"):

#     reset_timings()
#     os.makedirs(OUTPUT_IMG_DIR, exist_ok=True)
#     os.makedirs(OUTPUT_IMG_JPG_DIR,  exist_ok=True)  # ← add this
#     os.makedirs(OUTPUT_IMG_WEBP_DIR, exist_ok=True)  # ← add this
#     results = []

#     # ── Stack load karo ──────────────────────────────────────
#     stack = load_stack()
#     print(f"[STACK] {len(stack)} articles remaining in stack")

#     # ── Stack empty hai → decide karo kya karna hai ──────────
#     if not stack:
#         saved_ts = load_timestamp()

#         if saved_ts is None:
#             print("[STACK] Pehli baar start — full fetch karo...")
#             stack = _full_fetch_and_build_stack(selected_country, category)
#         else:
#             print(f"[STACK] Empty — timestamp ke baad fetch karo: {saved_ts}")
#             stack = _fetch_after_timestamp(selected_country, category, saved_ts)

#         # ── Fallback Zerodha ──────────────────────────────────
#         if not stack:
#             print("[WAITING] Koi naya article nahi mila — fallback Zerodha...")

#             zerodha_data = fetch_zerodha()
#             if not zerodha_data:
#                 return []

#             final_item = random.choice(zerodha_data)

#             final_item["blog"]             = generate_blog(final_item)
#             final_item["notify"]           = generate_notification(final_item)
#             final_item["instagram_notify"] = generate_instagram_caption(final_item)
#             final_item["Run_Timestamp"]    = get_run_timestamp()

#             save_output(final_item)
#             return [final_item]

#     # ── Stack se ek random article pop karo ──────────────────
#     final_item, stack = pop_from_stack(stack)
#     save_stack(stack)
#     print(f"[POPPED]  {final_item.get('Blog_Title', '')[:60]}")
#     print(f"[STACK]   {len(stack)} articles remaining")

#     final_category = category

#     # ── Used titles check karo ────────────────────────────────
#     used_titles = load_used_titles()

#     if normalize_title(final_item.get("Blog_Title", "")) in used_titles:
#         print("[SKIPPED] Title already used — next cycle me try karega")
#         return []

#     print(f"[SELECTED] Fresh blog: {final_item.get('Blog_Title', '')[:50]}")

#     try:
#         final_item["blog"]             = _generate_blog(final_item)
#         final_item["notify"]           = _generate_notification(final_item)
#         final_item["instagram_notify"] = _generate_instagram(final_item)

#         final_item["image_text"] = _extract_image_text(
#             final_item["Blog_Title"],
#             final_item.get("Blog_Content", ""),
#             final_category.upper()
#         )

#         final_item["template_path"] = _select_template(
#             final_category,
#             final_item["Blog_Title"]
#         )

#         validate_template(final_item["template_path"])

#         safe_title = clean_filename(final_item["Blog_Title"])

#         # JPG paths → jpg_images folder
#         blog_jpg_path  = os.path.join(OUTPUT_IMG_JPG_DIR,  f"blog_{safe_title}.jpg")
#         insta_jpg_path = os.path.join(OUTPUT_IMG_JPG_DIR,  f"insta_{safe_title}.jpg")


#         # WebP paths → webp_images folder
#         blog_webp_path  = os.path.join(OUTPUT_IMG_WEBP_DIR, f"blog_{safe_title}.webp")
#         insta_webp_path = os.path.join(OUTPUT_IMG_WEBP_DIR, f"insta_{safe_title}.webp")

#         # Blog — saves JPG + WebP in one call
#         final_item["blog_image"] = _compose_image(
#             final_item["template_path"],
#             final_item["image_text"],
#             blog_jpg_path,
#             blog_webp_path,
#             "blog"
#             )
#         # Instagram — saves JPG + WebP in one call
#         final_item["instagram_image"] = _compose_image(
#             final_item["template_path"],
#             final_item["image_text"],
#             insta_jpg_path,
#             insta_webp_path,
#             "instagram"
#             )
        

#         final_item["Run_Timestamp"] = get_run_timestamp()

#         saved = _save_output(final_item)

#         if saved:
#             results.append(final_item)
#             print(f"[DONE] {final_item['Blog_Title'][:60]}")
#         else:
#             print(f"[SKIPPED PIPELINE] Already exists: {final_item['Blog_Title'][:60]}")

#     except Exception as e:
#         print(f"[ERROR] {e}")

#     print_timing_summary()
#     return results












































































# note it is latest changes code____________________________________________________
# import os
# import random
# import re
# import unicodedata
# import json
# from datetime import datetime

# from RSS.zerodha import fetch_zerodha
# from RSS.cnbc import fetch_cnbc
# from RSS.paisa import fetch_5paisa
# from RSS.livemint import fetch_livemint
# from RSS.fetch_nse_corporate import fetch_nse_corporate

# from utils.combined_filter import filter_by_country_and_category
# from AI_GEN.notify_generator import generate_notification
# from AI_GEN.generate_instagram_caption import generate_instagram_caption
# from AI_GEN.get_system_timestamp import get_run_timestamp
# from AI_GEN.blog_generator import generate_blog
# from content_engine.image_module.ai_image_generator import generate_ai_image
# from storage.save_output import save_output
# from utils.timer import timed, Timer, print_timing_summary, reset_timings


# # ── Base directory ────────────────────────────────────────────
# BASE_DIR            = os.path.dirname(os.path.abspath(__file__))
# OUTPUT_IMG_DIR      = os.path.join(BASE_DIR, "output_images")
# OUTPUT_IMG_JPG_DIR  = os.path.join(BASE_DIR, "output_images", "jpg_images")
# OUTPUT_IMG_WEBP_DIR = os.path.join(BASE_DIR, "output_images", "webp_images")
# STACK_FILE          = os.path.join(BASE_DIR, "output", "article_stack.json")
# TIMESTAMP_FILE      = os.path.join(BASE_DIR, "output", "stack_timestamp.json")


# # ══════════════════════════════════════════════════════════════
# # Stack helpers
# # ══════════════════════════════════════════════════════════════

# def save_stack(stack):
#     os.makedirs(os.path.dirname(STACK_FILE), exist_ok=True)
#     with open(STACK_FILE, "w", encoding="utf-8") as f:
#         json.dump(stack, f, ensure_ascii=False, indent=2)
#     print(f"[STACK] {len(stack)} articles saved to disk")


# def load_stack():
#     if not os.path.exists(STACK_FILE):
#         return []
#     with open(STACK_FILE, "r", encoding="utf-8") as f:
#         try:
#             return json.load(f)
#         except:
#             return []


# def pop_from_stack(stack):
#     if not stack:
#         return None, stack
#     item = random.choice(stack)
#     stack.remove(item)
#     return item, stack


# def save_timestamp():
#     os.makedirs(os.path.dirname(TIMESTAMP_FILE), exist_ok=True)
#     ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#     with open(TIMESTAMP_FILE, "w") as f:
#         json.dump({"stack_built_at": ts}, f)
#     print(f"[TIMESTAMP] Stack built at: {ts}")
#     return ts


# def load_timestamp():
#     if not os.path.exists(TIMESTAMP_FILE):
#         return None
#     with open(TIMESTAMP_FILE, "r") as f:
#         try:
#             data = json.load(f)
#             return data.get("stack_built_at")
#         except:
#             return None


# # ══════════════════════════════════════════════════════════════
# # Pehli baar full fetch karke stack banao
# # ══════════════════════════════════════════════════════════════

# def _full_fetch_and_build_stack(selected_country, category):
#     print("\n" + "="*50)
#     print("  PHASE 1 — BUILDING FRESH STACK")
#     print("="*50)

#     TOP_N    = 20
#     all_data = []

#     with Timer("fetch_zerodha"):       all_data.extend(fetch_zerodha()[:TOP_N])
#     with Timer("fetch_cnbc"):          all_data.extend(fetch_cnbc()[:TOP_N])
#     with Timer("fetch_5paisa"):        all_data.extend(fetch_5paisa()[:TOP_N])
#     with Timer("fetch_livemint"):      all_data.extend(fetch_livemint()[:TOP_N])
#     with Timer("fetch_nse_corporate"): all_data.extend(fetch_nse_corporate()[:TOP_N])

#     print(f"Total collected: {len(all_data)}")

#     filtered_data, source = filter_by_country_and_category(
#         all_data, selected_country, category
#     )
#     print(f"After country+category filter: {len(filtered_data)} (source={source})")

#     used_titles = load_used_titles()
#     fresh = [
#         item for item in filtered_data
#         if normalize_title(item.get("Blog_Title", "")) not in used_titles
#     ]
#     print(f"Fresh unique articles: {len(fresh)}")

#     if fresh:
#         save_stack(fresh)
#         save_timestamp()
#         print(f"[STACK] Built with {len(fresh)} articles!")
#     else:
#         print("[STACK] No fresh articles found!")

#     print("="*50 + "\n")
#     return fresh


# # ══════════════════════════════════════════════════════════════
# # Stack empty hone ke baad timestamp ke baad fetch karo
# # ══════════════════════════════════════════════════════════════

# def _fetch_after_timestamp(selected_country, category, saved_ts):
#     print(f"\n[STACK EMPTY] Fetching new articles after: {saved_ts}")

#     TOP_N    = 6
#     all_data = []

#     all_data.extend(fetch_zerodha()[:TOP_N])
#     all_data.extend(fetch_cnbc()[:TOP_N])
#     all_data.extend(fetch_5paisa()[:TOP_N])
#     all_data.extend(fetch_livemint()[:TOP_N])
#     all_data.extend(fetch_nse_corporate()[:TOP_N])

#     filtered_data, source = filter_by_country_and_category(
#         all_data, selected_country, category
#     )
#     print(f"After country+category filter: {len(filtered_data)} (source={source})")

#     used_titles = load_used_titles()
#     fresh = [
#         item for item in filtered_data
#         if normalize_title(item.get("Blog_Title", "")) not in used_titles
#     ]

#     if fresh:
#         save_stack(fresh)
#         save_timestamp()
#         print(f"[STACK] Refilled with {len(fresh)} new articles")
#     else:
#         print("[STACK] Abhi koi naya article nahi — 5 min baad retry karega")

#     return fresh


# # ── Normalize Title ───────────────────────────────────────────
# def normalize_title(title):
#     title = title.strip().lower()
#     title = re.sub(r'\s+', ' ', title)
#     return title


# # ── Load used titles ──────────────────────────────────────────
# def load_used_titles(filepath="output/testing_webp_output.json"):
#     if not os.path.exists(filepath):
#         return set()
#     with open(filepath, "r", encoding="utf-8") as f:
#         try:
#             data = json.load(f)
#             return {
#                 normalize_title(item.get("Blog_Title", ""))
#                 for item in data
#             }
#         except:
#             return set()


# # ── Utility ───────────────────────────────────────────────────
# def clean_filename(text):
#     text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
#     text = re.sub(r'[\\/*?:"<>|]', '', text)
#     text = text.replace(" ", "_")
#     text = re.sub(r'_+', '_', text)
#     return text[:60]


# # ── Timed wrappers ────────────────────────────────────────────
# @timed
# def _generate_blog(item):
#     return generate_blog(item)

# @timed
# def _generate_notification(item):
#     return generate_notification(item)

# @timed
# def _generate_instagram(item):
#     return generate_instagram_caption(item)

# @timed
# def _generate_ai_image(blog_title, blog_content, blog_outer_paths, blog_inner_paths, instagram_paths, quality="medium"):
#     return generate_ai_image(blog_title, blog_content, blog_outer_paths, blog_inner_paths, instagram_paths, quality)
# @timed
# def _save_output(item):
#     return save_output(item)

# @timed
# def _filter_combined(data, country, category):
#     return filter_by_country_and_category(data, country, category)


# # ── Main pipeline (har 15 min chalta hai) ────────────────────
# def run_pipeline(selected_country="India", category="finance"):

#     reset_timings()
#     os.makedirs(OUTPUT_IMG_DIR,      exist_ok=True)
#     os.makedirs(OUTPUT_IMG_JPG_DIR,  exist_ok=True)
#     os.makedirs(OUTPUT_IMG_WEBP_DIR, exist_ok=True)
#     results = []

#     # ── Stack load karo ──────────────────────────────────────
#     stack = load_stack()
#     print(f"[STACK] {len(stack)} articles remaining in stack")

#     # ── Stack empty hai → decide karo kya karna hai ──────────
#     if not stack:
#         saved_ts = load_timestamp()

#         if saved_ts is None:
#             print("[STACK] Pehli baar start — full fetch karo...")
#             stack = _full_fetch_and_build_stack(selected_country, category)
#         else:
#             print(f"[STACK] Empty — timestamp ke baad fetch karo: {saved_ts}")
#             stack = _fetch_after_timestamp(selected_country, category, saved_ts)

#         # ── Fallback Zerodha ──────────────────────────────────
#         if not stack:
#             print("[WAITING] Koi naya article nahi mila — fallback Zerodha...")

#             zerodha_data = fetch_zerodha()
#             if not zerodha_data:
#                 return []

#             final_item = random.choice(zerodha_data)

#             final_item["blog"]             = generate_blog(final_item)
#             final_item["notify"]           = generate_notification(final_item)
#             final_item["instagram_notify"] = generate_instagram_caption(final_item)
#             final_item["Run_Timestamp"]    = get_run_timestamp()

#             save_output(final_item)
#             return [final_item]

#     # ── Stack se ek random article pop karo ──────────────────
#     final_item, stack = pop_from_stack(stack)
#     save_stack(stack)
#     print(f"[POPPED]  {final_item.get('Blog_Title', '')[:60]}")
#     print(f"[STACK]   {len(stack)} articles remaining")

#     final_category = category

#     # ── Used titles check karo ────────────────────────────────
#     used_titles = load_used_titles()

#     if normalize_title(final_item.get("Blog_Title", "")) in used_titles:
#         print("[SKIPPED] Title already used — next cycle me try karega")
#         return []

#     print(f"[SELECTED] Fresh blog: {final_item.get('Blog_Title', '')[:50]}")

#     try:
#         # ── AI Content Generation ─────────────────────────────
#         final_item["blog"]             = _generate_blog(final_item)
#         final_item["notify"]           = _generate_notification(final_item)
#         final_item["instagram_notify"] = _generate_instagram(final_item)

#         # ── File paths ────────────────────────────────────────
#         safe_title = clean_filename(final_item["Blog_Title"])


#         blog_outer_jpg  = os.path.join(OUTPUT_IMG_JPG_DIR,  f"blog_outer_{safe_title}.jpg")
#         blog_outer_webp = os.path.join(OUTPUT_IMG_WEBP_DIR, f"blog_outer_{safe_title}.webp")


#         blog_inner_jpg  = os.path.join(OUTPUT_IMG_JPG_DIR,  f"blog_inner_{safe_title}.jpg")
#         blog_inner_webp = os.path.join(OUTPUT_IMG_WEBP_DIR, f"blog_inner_{safe_title}.webp")



#         insta_jpg  = os.path.join(OUTPUT_IMG_JPG_DIR,  f"insta_{safe_title}.jpg")
#         insta_webp = os.path.join(OUTPUT_IMG_WEBP_DIR, f"insta_{safe_title}.webp")


#         images = _generate_ai_image(
#         final_item["Blog_Title"],
#         final_item.get("Blog_Content", ""),
#         blog_outer_paths = {"jpg": blog_outer_jpg, "webp": blog_outer_webp},
#         blog_inner_paths = {"jpg": blog_inner_jpg, "webp": blog_inner_webp},
#         instagram_paths  = {"jpg": insta_jpg,      "webp": insta_webp},
#         quality          = "medium"
#         )

#         final_item["blog_image_outer"] = images["blog_outer"]
#         final_item["blog_image_inner"] = images["blog_inner"]
#         final_item["instagram_image"]  = images["instagram"]




        

        
#         final_item["Run_Timestamp"] = get_run_timestamp()

#         saved = _save_output(final_item)

#         if saved:
#             results.append(final_item)
#             print(f"[DONE] {final_item['Blog_Title'][:60]}")
#         else:
#             print(f"[SKIPPED PIPELINE] Already exists: {final_item['Blog_Title'][:60]}")

#     except Exception as e:
#         print(f"[ERROR] {e}")

#     print_timing_summary()
#     return results































# import os
# import random
# import re
# import unicodedata
# import json
# import copy
# from datetime import datetime

# from RSS.zerodha import fetch_zerodha
# from RSS.cnbc import fetch_cnbc
# from RSS.paisa import fetch_5paisa
# from RSS.livemint import fetch_livemint
# from RSS.fetch_nse_corporate import fetch_nse_corporate

# from content_engine.image_module.text_extractor import extract_image_text
# from content_engine.image_module.tempalte_selector import select_template
# from content_engine.image_module.compositor import compose_image
# from content_engine.image_module.validator import validate_template

# from utils.combined_filter import filter_by_country_and_category  # ✅ one combined filter
# from AI_GEN.notify_generator import generate_notification
# from AI_GEN.generate_instagram_caption import generate_instagram_caption
# from AI_GEN.get_system_timestamp import get_run_timestamp
# from AI_GEN.blog_generator import generate_blog
# from storage.save_output import save_output
# from utils.timer import timed, Timer, print_timing_summary, reset_timings


# # ── Base directory ────────────────────────────────────────────
# BASE_DIR       = os.path.dirname(os.path.abspath(__file__))
# OUTPUT_IMG_DIR = os.path.join(BASE_DIR, "output_images")
# OUTPUT_IMG_JPG_DIR  = os.path.join(BASE_DIR, "output_images", "jpg_images")
# OUTPUT_IMG_WEBP_DIR = os.path.join(BASE_DIR, "output_images", "webp_images")
# STACK_FILE     = os.path.join(BASE_DIR, "output", "article_stack.json")
# TIMESTAMP_FILE = os.path.join(BASE_DIR, "output", "stack_timestamp.json")


# # ══════════════════════════════════════════════════════════════
# # Stack helpers
# # ══════════════════════════════════════════════════════════════

# def save_stack(stack):
#     os.makedirs(os.path.dirname(STACK_FILE), exist_ok=True)
#     with open(STACK_FILE, "w", encoding="utf-8") as f:
#         json.dump(stack, f, ensure_ascii=False, indent=2)
#     print(f"[STACK] {len(stack)} articles saved to disk")


# def load_stack():
#     if not os.path.exists(STACK_FILE):
#         return []
#     with open(STACK_FILE, "r", encoding="utf-8") as f:
#         try:
#             return json.load(f)
#         except:
#             return []


# def pop_from_stack(stack):
#     if not stack:
#         return None, stack
#     item = random.choice(stack)
#     stack.remove(item)
#     return item, stack


# def save_timestamp():
#     os.makedirs(os.path.dirname(TIMESTAMP_FILE), exist_ok=True)
#     ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#     with open(TIMESTAMP_FILE, "w") as f:
#         json.dump({"stack_built_at": ts}, f)
#     print(f"[TIMESTAMP] Stack built at: {ts}")
#     return ts


# def load_timestamp():
#     if not os.path.exists(TIMESTAMP_FILE):
#         return None
#     with open(TIMESTAMP_FILE, "r") as f:
#         try:
#             data = json.load(f)
#             return data.get("stack_built_at")
#         except:
#             return None


# # ══════════════════════════════════════════════════════════════
# # Pehli baar full fetch karke stack banao
# # ══════════════════════════════════════════════════════════════

# def _full_fetch_and_build_stack(selected_country, category):
#     print("\n" + "="*50)
#     print("  PHASE 1 — BUILDING FRESH STACK")
#     print("="*50)

#     TOP_N    = 20
#     all_data = []

#     with Timer("fetch_zerodha"):       all_data.extend(fetch_zerodha()[:TOP_N])
#     with Timer("fetch_cnbc"):          all_data.extend(fetch_cnbc()[:TOP_N])
#     with Timer("fetch_5paisa"):        all_data.extend(fetch_5paisa()[:TOP_N])
#     with Timer("fetch_livemint"):      all_data.extend(fetch_livemint()[:TOP_N])
#     with Timer("fetch_nse_corporate"): all_data.extend(fetch_nse_corporate()[:TOP_N])

#     print(f"Total collected: {len(all_data)}")

#     # ✅ Ek combined API call — country + category dono
#     filtered_data, source = filter_by_country_and_category(
#         all_data, selected_country, category
#     )
#     print(f"After country+category filter: {len(filtered_data)} (source={source})")

#     # Remove used titles
#     used_titles = load_used_titles()
#     fresh = [
#         item for item in filtered_data           # ✅ filtered_data use karo
#         if normalize_title(item.get("Blog_Title", "")) not in used_titles
#     ]
#     print(f"Fresh unique articles: {len(fresh)}")

#     if fresh:
#         save_stack(fresh)
#         save_timestamp()
#         print(f"[STACK] Built with {len(fresh)} articles!")
#     else:
#         print("[STACK] No fresh articles found!")

#     print("="*50 + "\n")
#     return fresh


# # ══════════════════════════════════════════════════════════════
# # Stack empty hone ke baad timestamp ke baad fetch karo
# # ══════════════════════════════════════════════════════════════

# def _fetch_after_timestamp(selected_country, category, saved_ts):
#     print(f"\n[STACK EMPTY] Fetching new articles after: {saved_ts}")

#     TOP_N    = 6
#     all_data = []

#     all_data.extend(fetch_zerodha()[:TOP_N])
#     all_data.extend(fetch_cnbc()[:TOP_N])
#     all_data.extend(fetch_5paisa()[:TOP_N])
#     all_data.extend(fetch_livemint()[:TOP_N])
#     all_data.extend(fetch_nse_corporate()[:TOP_N])

#     # ✅ Ek combined API call — country + category dono
#     filtered_data, source = filter_by_country_and_category(
#         all_data, selected_country, category
#     )
#     print(f"After country+category filter: {len(filtered_data)} (source={source})")

#     # Sirf naye unused articles
#     used_titles = load_used_titles()
#     fresh = [
#         item for item in filtered_data           # ✅ filtered_data use karo
#         if normalize_title(item.get("Blog_Title", "")) not in used_titles
#     ]

#     if fresh:
#         save_stack(fresh)
#         save_timestamp()
#         print(f"[STACK] Refilled with {len(fresh)} new articles")
#     else:
#         print("[STACK] Abhi koi naya article nahi — 5 min baad retry karega")

#     return fresh


# # ── Normalize Title ───────────────────────────────────────────
# def normalize_title(title):
#     title = title.strip().lower()
#     title = re.sub(r'\s+', ' ', title)
#     return title


# # ── Load used titles ──────────────────────────────────────────
# def load_used_titles(filepath="output/output.json"):
#     if not os.path.exists(filepath):
#         return set()
#     with open(filepath, "r", encoding="utf-8") as f:
#         try:
#             data = json.load(f)
#             return {
#                 normalize_title(item.get("Blog_Title", ""))
#                 for item in data
#             }
#         except:
#             return set()


# # ── Utility ───────────────────────────────────────────────────
# def clean_filename(text):
#     text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
#     text = re.sub(r'[\\/*?:"<>|]', '', text)
#     text = text.replace(" ", "_")
#     text = re.sub(r'_+', '_', text)
#     return text[:60]


# # ── Timed wrappers ────────────────────────────────────────────
# @timed
# def _generate_blog(item):
#     return generate_blog(item)

# @timed
# def _generate_notification(item):
#     return generate_notification(item)

# @timed
# def _generate_instagram(item):
#     return generate_instagram_caption(item)

# @timed
# def _extract_image_text(title, content, category):
#     return extract_image_text(title, content, category)

# @timed
# def _select_template(category, title):
#     return select_template(category, title)

# # @timed
# # def _compose_image(template, image_text, path, image_type):
# #     return compose_image(template, image_text, path, image_type=image_type)
# @timed
# def _compose_image(template, image_text, jpg_path, webp_path, image_type):
#     return compose_image(template, image_text, jpg_path, webp_path, image_type=image_type)

# @timed
# def _save_output(item):
#     return save_output(item)

# # ✅ Ek combined timed wrapper — dono filter ek saath
# @timed
# def _filter_combined(data, country, category):
#     return filter_by_country_and_category(data, country, category)


# # ── Main pipeline (har 5 min chalta hai) ─────────────────────
# def run_pipeline(selected_country="India", category="finance"):

#     reset_timings()
#     os.makedirs(OUTPUT_IMG_DIR, exist_ok=True)
#     os.makedirs(OUTPUT_IMG_JPG_DIR,  exist_ok=True)  # ← add this
#     os.makedirs(OUTPUT_IMG_WEBP_DIR, exist_ok=True)  # ← add this
#     results = []

#     # ── Stack load karo ──────────────────────────────────────
#     stack = load_stack()
#     print(f"[STACK] {len(stack)} articles remaining in stack")

#     # ── Stack empty hai → decide karo kya karna hai ──────────
#     if not stack:
#         saved_ts = load_timestamp()

#         if saved_ts is None:
#             print("[STACK] Pehli baar start — full fetch karo...")
#             stack = _full_fetch_and_build_stack(selected_country, category)
#         else:
#             print(f"[STACK] Empty — timestamp ke baad fetch karo: {saved_ts}")
#             stack = _fetch_after_timestamp(selected_country, category, saved_ts)

#         # ── Fallback Zerodha ──────────────────────────────────
#         if not stack:
#             print("[WAITING] Koi naya article nahi mila — fallback Zerodha...")

#             zerodha_data = fetch_zerodha()
#             if not zerodha_data:
#                 return []

#             final_item = random.choice(zerodha_data)

#             final_item["blog"]             = generate_blog(final_item)
#             final_item["notify"]           = generate_notification(final_item)
#             final_item["instagram_notify"] = generate_instagram_caption(final_item)
#             final_item["Run_Timestamp"]    = get_run_timestamp()

#             save_output(final_item)
#             return [final_item]

#     # ── Stack se ek random article pop karo ──────────────────
#     final_item, stack = pop_from_stack(stack)
#     save_stack(stack)
#     print(f"[POPPED]  {final_item.get('Blog_Title', '')[:60]}")
#     print(f"[STACK]   {len(stack)} articles remaining")

#     final_category = category

#     # ── Used titles check karo ────────────────────────────────
#     used_titles = load_used_titles()

#     if normalize_title(final_item.get("Blog_Title", "")) in used_titles:
#         print("[SKIPPED] Title already used — next cycle me try karega")
#         return []

#     print(f"[SELECTED] Fresh blog: {final_item.get('Blog_Title', '')[:50]}")

#     try:
#         final_item["blog"]             = _generate_blog(final_item)
#         final_item["notify"]           = _generate_notification(final_item)
#         final_item["instagram_notify"] = _generate_instagram(final_item)

#         final_item["image_text"] = _extract_image_text(
#             final_item["Blog_Title"],
#             final_item.get("Blog_Content", ""),
#             final_category.upper()
#         )

#         final_item["template_path"] = _select_template(
#             final_category,
#             final_item["Blog_Title"]
#         )

#         validate_template(final_item["template_path"])

#         safe_title = clean_filename(final_item["Blog_Title"])

#         # JPG paths → jpg_images folder
#         blog_jpg_path  = os.path.join(OUTPUT_IMG_JPG_DIR,  f"blog_{safe_title}.jpg")
#         insta_jpg_path = os.path.join(OUTPUT_IMG_JPG_DIR,  f"insta_{safe_title}.jpg")


#         # WebP paths → webp_images folder
#         blog_webp_path  = os.path.join(OUTPUT_IMG_WEBP_DIR, f"blog_{safe_title}.webp")
#         insta_webp_path = os.path.join(OUTPUT_IMG_WEBP_DIR, f"insta_{safe_title}.webp")

#         # Blog — saves JPG + WebP in one call
#         final_item["blog_image"] = _compose_image(
#             final_item["template_path"],
#             final_item["image_text"],
#             blog_jpg_path,
#             blog_webp_path,
#             "blog"
#             )
#         # Instagram — saves JPG + WebP in one call
#         final_item["instagram_image"] = _compose_image(
#             final_item["template_path"],
#             final_item["image_text"],
#             insta_jpg_path,
#             insta_webp_path,
#             "instagram"
#             )
        

#         final_item["Run_Timestamp"] = get_run_timestamp()

#         saved = _save_output(final_item)

#         if saved:
#             results.append(final_item)
#             print(f"[DONE] {final_item['Blog_Title'][:60]}")
#         else:
#             print(f"[SKIPPED PIPELINE] Already exists: {final_item['Blog_Title'][:60]}")

#     except Exception as e:
#         print(f"[ERROR] {e}")

#     print_timing_summary()
#     return results












































































# import os
# import random
# import re
# import unicodedata
# import json
# import copy
# from datetime import datetime                          # ✅ NEW

# from RSS.zerodha import fetch_zerodha
# from RSS.cnbc import fetch_cnbc
# from RSS.paisa import fetch_5paisa
# from RSS.livemint import fetch_livemint
# from RSS.fetch_nse_corporate import fetch_nse_corporate

# from content_engine.image_module.text_extractor import extract_image_text
# from content_engine.image_module.tempalte_selector import select_template
# from content_engine.image_module.compositor import compose_image
# from content_engine.image_module.validator import validate_template

# from utils.combined_filter import filter_by_country_and_category
# from AI_GEN.notify_generator import generate_notification
# from AI_GEN.generate_instagram_caption import generate_instagram_caption
# from AI_GEN.get_system_timestamp import get_run_timestamp


# from AI_GEN.blog_generator import generate_blog
# from storage.save_output import save_output
# from utils.timer import timed, Timer, print_timing_summary, reset_timings


# # ── Base directory ────────────────────────────────────────────
# BASE_DIR       = os.path.dirname(os.path.abspath(__file__))
# OUTPUT_IMG_DIR = os.path.join(BASE_DIR, "output_images")
# STACK_FILE     = os.path.join(BASE_DIR, "output", "article_stack.json")   # ✅ NEW
# TIMESTAMP_FILE = os.path.join(BASE_DIR, "output", "stack_timestamp.json") # ✅ NEW


# # ══════════════════════════════════════════════════════════════
# # ✅ NEW — Stack helpers
# # ══════════════════════════════════════════════════════════════

# def save_stack(stack):
#     """Stack ko disk pe save karo"""
#     os.makedirs(os.path.dirname(STACK_FILE), exist_ok=True)
#     with open(STACK_FILE, "w", encoding="utf-8") as f:
#         json.dump(stack, f, ensure_ascii=False, indent=2)
#     print(f"[STACK] {len(stack)} articles saved to disk")


# def load_stack():
#     """Stack ko disk se load karo"""
#     if not os.path.exists(STACK_FILE):
#         return []
#     with open(STACK_FILE, "r", encoding="utf-8") as f:
#         try:
#             return json.load(f)
#         except:
#             return []


# def pop_from_stack(stack):
#     """Stack se ek random article nikalo"""
#     if not stack:
#         return None, stack
#     item = random.choice(stack)
#     stack.remove(item)
#     return item, stack


# def save_timestamp():
#     """Jab stack bana tab ka time save karo"""
#     os.makedirs(os.path.dirname(TIMESTAMP_FILE), exist_ok=True)
#     ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#     with open(TIMESTAMP_FILE, "w") as f:
#         json.dump({"stack_built_at": ts}, f)
#     print(f"[TIMESTAMP] Stack built at: {ts}")
#     return ts


# def load_timestamp():
#     """Saved timestamp wapas lo"""
#     if not os.path.exists(TIMESTAMP_FILE):
#         return None
#     with open(TIMESTAMP_FILE, "r") as f:
#         try:
#             data = json.load(f)
#             return data.get("stack_built_at")
#         except:
#             return None


# # ══════════════════════════════════════════════════════════════
# # ✅ NEW — Pehli baar full fetch karke stack banao
# # ══════════════════════════════════════════════════════════════

# def _full_fetch_and_build_stack(selected_country, category):
#     """Pehli baar ya fresh start — sab RSS fetch karo"""
#     print("\n" + "="*50)
#     print("  PHASE 1 — BUILDING FRESH STACK")
#     print("="*50)

#     TOP_N    = 20
#     all_data = []

#     with Timer("fetch_zerodha"):       all_data.extend(fetch_zerodha()[:TOP_N])
#     with Timer("fetch_cnbc"):          all_data.extend(fetch_cnbc()[:TOP_N])
#     with Timer("fetch_5paisa"):        all_data.extend(fetch_5paisa()[:TOP_N])
#     with Timer("fetch_livemint"):      all_data.extend(fetch_livemint()[:TOP_N])
#     with Timer("fetch_nse_corporate"): all_data.extend(fetch_nse_corporate()[:TOP_N])

#     print(f"Total collected: {len(all_data)}")

#     # Country filter
#     filtered_data, source = filter_by_country_and_category(
#         all_data, selected_country, category
#     )
#     print(f"After category filter: {len(category_filtered)}")

#     # Remove used titles
#     used_titles = load_used_titles()
#     fresh = [
#         item for item in category_filtered
#         if normalize_title(item.get("Blog_Title", "")) not in used_titles
#     ]
#     print(f"Fresh unique articles: {len(fresh)}")

#     if fresh:
#         save_stack(fresh)
#         save_timestamp()  # ✅ Timestamp save karo
#         print(f"[STACK] Built with {len(fresh)} articles!")
#     else:
#         print("[STACK] No fresh articles found!")

#     print("="*50 + "\n")
#     return fresh


# # ══════════════════════════════════════════════════════════════
# # ✅ NEW — Stack empty hone ke baad timestamp ke baad fetch karo
# # ══════════════════════════════════════════════════════════════

# def _fetch_after_timestamp(selected_country, category, saved_ts):
#     """Stack empty ho jaye tab — timestamp ke baad ke naye articles lo"""
#     print(f"\n[STACK EMPTY] Fetching new articles after: {saved_ts}")

#     TOP_N    = 6
#     all_data = []

#     all_data.extend(fetch_zerodha()[:TOP_N])
#     all_data.extend(fetch_cnbc()[:TOP_N])
#     all_data.extend(fetch_5paisa()[:TOP_N])
#     all_data.extend(fetch_livemint()[:TOP_N])
#     all_data.extend(fetch_nse_corporate()[:TOP_N])

#     # Country + category filter
#     filtered_data, source = filter_by_country_and_category(
#         all_data, selected_country, category
#     )
#     # Sirf naye unused articles
#     used_titles = load_used_titles()
#     fresh = [
#         item for item in category_filtered
#         if normalize_title(item.get("Blog_Title", "")) not in used_titles
#     ]

#     if fresh:
#         save_stack(fresh)
#         save_timestamp()  # ✅ Naya timestamp update karo
#         print(f"[STACK] Refilled with {len(fresh)} new articles")
#     else:
#         print("[STACK] Abhi koi naya article nahi — 5 min baad retry karega")

#     return fresh


# # ── Normalize Title ───────────────────────────────────────────
# def normalize_title(title):
#     title = title.strip().lower()
#     title = re.sub(r'\s+', ' ', title)
#     return title


# # ── Load used titles ──────────────────────────────────────────
# def load_used_titles(filepath="output/output.json"):
#     if not os.path.exists(filepath):
#         return set()
#     with open(filepath, "r", encoding="utf-8") as f:
#         try:
#             data = json.load(f)
#             return {
#                 normalize_title(item.get("Blog_Title", ""))
#                 for item in data
#             }
#         except:
#             return set()


# # ── Utility ───────────────────────────────────────────────────
# def clean_filename(text):
#     text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
#     text = re.sub(r'[\\/*?:"<>|]', '', text)
#     text = text.replace(" ", "_")
#     text = re.sub(r'_+', '_', text)
#     return text[:60]


# # ── Timed wrappers ────────────────────────────────────────────
# @timed
# def _generate_blog(item):
#     return generate_blog(item)

# @timed
# def _generate_notification(item):
#     return generate_notification(item)

# @timed
# def _generate_instagram(item):
#     return generate_instagram_caption(item)

# @timed
# def _extract_image_text(title, content, category):
#     return extract_image_text(title, content, category)

# @timed
# def _select_template(category, title):
#     return select_template(category, title)

# @timed
# def _compose_image(template, image_text, path, image_type):
#     return compose_image(template, image_text, path, image_type=image_type)

# @timed
# def _save_output(item):
#     return save_output(item)

# @timed
# def _filter_by_country(data, country):
#     return filter_by_country_model(data, country)

# @timed
# def _filter_by_category(data, category):
#     return filter_by_category_model(data, category)


# # ── Main pipeline (har 5 min chalta hai) ─────────────────────
# def run_pipeline(selected_country="India", category="finance"):

#     reset_timings()
#     TOP_N = 6
#     os.makedirs(OUTPUT_IMG_DIR, exist_ok=True)
#     results = []

#     # ══════════════════════════════════════════════════════════
#     # ✅ Stack load karo
#     # ══════════════════════════════════════════════════════════
#     stack = load_stack()
#     print(f"[STACK] {len(stack)} articles remaining in stack")

#     # ══════════════════════════════════════════════════════════
#     # ✅ Stack empty hai → decide karo kya karna hai
#     # ══════════════════════════════════════════════════════════
#     if not stack:
#         saved_ts = load_timestamp()

#         if saved_ts is None:
#             print("[STACK] Pehli baar start — full fetch karo...")
#             stack = _full_fetch_and_build_stack(selected_country, category)
#         else:
#             print(f"[STACK] Empty — timestamp ke baad fetch karo: {saved_ts}")
#             stack = _fetch_after_timestamp(selected_country, category, saved_ts)

#         # ── STEP 5: Fallback Zerodha ─────────────────────────
#         if not stack:
#             print("[WAITING] Koi naya article nahi mila — fallback Zerodha...")

#             zerodha_data = fetch_zerodha()
#             if not zerodha_data:
#                 return []

#             final_item = random.choice(zerodha_data)

#             final_item["blog"]             = generate_blog(final_item)
#             final_item["notify"]           = generate_notification(final_item)
#             final_item["instagram_notify"] = generate_instagram_caption(final_item)
#             final_item["Run_Timestamp"]    = get_run_timestamp()

#             save_output(final_item)
#             return [final_item]

#     # ══════════════════════════════════════════════════════════
#     # ✅ Stack se ek random article pop karo
#     # ══════════════════════════════════════════════════════════
#     final_item, stack = pop_from_stack(stack)
#     save_stack(stack)
#     print(f"[POPPED]  {final_item.get('Blog_Title', '')[:60]}")
#     print(f"[STACK]   {len(stack)} articles remaining")

#     final_category = category

#     # ── STEP 4: Smart Selection ──────────────────────────────
#     used_titles = load_used_titles()

#     if normalize_title(final_item.get("Blog_Title", "")) in used_titles:
#         print("[SKIPPED] Title already used — next cycle me try karega")
#         return []

#     print(f"[SELECTED] Fresh blog: {final_item.get('Blog_Title', '')[:50]}")

#     try:
#         final_item["blog"]             = _generate_blog(final_item)
#         final_item["notify"]           = _generate_notification(final_item)
#         final_item["instagram_notify"] = _generate_instagram(final_item)

#         final_item["image_text"] = _extract_image_text(
#             final_item["Blog_Title"],
#             final_item.get("Blog_Content", ""),
#             final_category.upper()
#         )

#         final_item["template_path"] = _select_template(
#             final_category,
#             final_item["Blog_Title"]
#         )

#         validate_template(final_item["template_path"])

#         safe_title = clean_filename(final_item["Blog_Title"])

#         blog_path  = os.path.join(OUTPUT_IMG_DIR, f"blog_{safe_title}.jpg")
#         insta_path = os.path.join(OUTPUT_IMG_DIR, f"insta_{safe_title}.jpg")

#         final_item["blog_image"] = _compose_image(
#             final_item["template_path"],
#             final_item["image_text"],
#             blog_path,
#             "blog"
#         )

#         final_item["instagram_image"] = _compose_image(
#             final_item["template_path"],
#             final_item["image_text"],
#             insta_path,
#             "instagram"
#         )

#         final_item["Run_Timestamp"] = get_run_timestamp()

#         saved = _save_output(final_item)

#         if saved:
#             results.append(final_item)
#             print(f"[DONE] {final_item['Blog_Title'][:60]}")
#         else:
#             print(f"[SKIPPED PIPELINE] Already exists: {final_item['Blog_Title'][:60]}")

#     except Exception as e:
#         print(f"[ERROR] {e}")

#     print_timing_summary()
#     return results
# def run_pipeline(selected_country="India", category="finance"):


#     reset_timings()
#     TOP_N = 20
#     os.makedirs(OUTPUT_IMG_DIR, exist_ok=True)
#     results = []

#     # ══════════════════════════════════════════════════════════
#     # ✅ NEW — Stack load karo
#     # ══════════════════════════════════════════════════════════
#     stack = load_stack()
#     print(f"[STACK] {len(stack)} articles remaining in stack")

#     # ══════════════════════════════════════════════════════════
#     # ✅ NEW — Stack empty hai → decide karo kya karna hai
#     # ══════════════════════════════════════════════════════════
#     if not stack:
#         saved_ts = load_timestamp()

#         if saved_ts is None:
#             # Pehli baar chal raha hai — full fetch karo
#             print("[STACK] Pehli baar start — full fetch karo...")
#             stack = _full_fetch_and_build_stack(selected_country, category)
#         else:
#             # Stack pehle bana tha — timestamp ke baad ke articles lo
#             print(f"[STACK] Empty — timestamp ke baad fetch karo: {saved_ts}")
#             stack = _fetch_after_timestamp(selected_country, category, saved_ts)

#         if not stack:
#             print("[WAITING] Koi naya article nahi mila. 5 min baad retry karega.")
#             return []

#     # ══════════════════════════════════════════════════════════
#     # ✅ NEW — Stack se ek random article pop karo
#     # ══════════════════════════════════════════════════════════
#     final_item, stack = pop_from_stack(stack)
#     save_stack(stack)  # ✅ Updated stack turant disk pe save karo
#     print(f"[POPPED]  {final_item.get('Blog_Title', '')[:60]}")
#     print(f"[STACK]   {len(stack)} articles remaining")

#     final_category = category

#     # ══════════════════════════════════════════════════════════
#     # YOUR EXISTING CODE — bilkul nahi badla ↓
#     # ══════════════════════════════════════════════════════════

#     # ── STEP 4: Smart Selection ──────────────────────────────
#     used_titles = load_used_titles()

#     if normalize_title(final_item.get("Blog_Title", "")) in used_titles:
#         print("[SKIPPED] Title already used — next cycle me try karega")
#         return []

#     print(f"[SELECTED] Fresh blog: {final_item.get('Blog_Title', '')[:50]}")

#     try:
#         final_item["blog"]             = _generate_blog(final_item)
#         final_item["notify"]           = _generate_notification(final_item)
#         final_item["instagram_notify"] = _generate_instagram(final_item)

#         final_item["image_text"] = _extract_image_text(
#             final_item["Blog_Title"],
#             final_item.get("Blog_Content", ""),
#             final_category.upper()
#         )

#         final_item["template_path"] = _select_template(
#             final_category,
#             final_item["Blog_Title"]
#         )

#         validate_template(final_item["template_path"])

#         safe_title = clean_filename(final_item["Blog_Title"])

#         blog_path  = os.path.join(OUTPUT_IMG_DIR, f"blog_{safe_title}.jpg")
#         insta_path = os.path.join(OUTPUT_IMG_DIR, f"insta_{safe_title}.jpg")

#         final_item["blog_image"] = _compose_image(
#             final_item["template_path"],
#             final_item["image_text"],
#             blog_path,
#             "blog"
#         )

#         final_item["instagram_image"] = _compose_image(
#             final_item["template_path"],
#             final_item["image_text"],
#             insta_path,
#             "instagram"
#         )

#         final_item["Run_Timestamp"] = get_run_timestamp()

#         # ✅ Save with check
#         saved = _save_output(final_item)

#         if saved:
#             results.append(final_item)
#             print(f"[DONE] {final_item['Blog_Title'][:60]}")
#         else:
#             print(f"[SKIPPED PIPELINE] Already exists: {final_item['Blog_Title'][:60]}")

#     except Exception as e:
#         print(f"[ERROR] {e}")

#     print_timing_summary()
#     return results


#     # ── STEP 5: Fallback ─────────────────────────────────────
#     else:
    
    
#     print("No data → fallback Zerodha")
    

    
        

#         zerodha_data = fetch_zerodha()
#         if not zerodha_data:
#             return []

#         final_item = random.choice(zerodha_data)

#         final_item["blog"]             = generate_blog(final_item)
#         final_item["notify"]           = generate_notification(final_item)
#         final_item["instagram_notify"] = generate_instagram_caption(final_item)
#         final_item["Run_Timestamp"]    = get_run_timestamp()

#         save_output(final_item)
#         return [final_item]




# import os
# import random
# import re
# import unicodedata
# import json
# import copy

# from RSS.zerodha import fetch_zerodha
# from RSS.cnbc import fetch_cnbc
# from RSS.paisa import fetch_5paisa
# from RSS.livemint import fetch_livemint
# from RSS.fetch_nse_corporate import fetch_nse_corporate

# from content_engine.image_module.text_extractor import extract_image_text
# from content_engine.image_module.tempalte_selector import select_template
# from content_engine.image_module.compositor import compose_image
# from content_engine.image_module.validator import validate_template

# from AI_GEN.filter_by_category_model import filter_by_category_model
# from AI_GEN.notify_generator import generate_notification
# from AI_GEN.generate_instagram_caption import generate_instagram_caption
# from AI_GEN.get_system_timestamp import get_run_timestamp

# from utils.normalize_country import filter_by_country_model
# from AI_GEN.blog_generator import generate_blog
# from storage.save_output import save_output
# from utils.timer import timed, Timer, print_timing_summary, reset_timings


# # ── Base directory ────────────────────────────────────────────
# BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# OUTPUT_IMG_DIR = os.path.join(BASE_DIR, "output_images")


# # ── Normalize Title (IMPORTANT) ───────────────────────────────
# def normalize_title(title):
#     title = title.strip().lower()
#     title = re.sub(r'\s+', ' ', title)
#     return title


# # ── Load used titles ─────────────────────────────────────────
# def load_used_titles(filepath="output/output.json"):
#     if not os.path.exists(filepath):
#         return set()

#     with open(filepath, "r", encoding="utf-8") as f:
#         try:
#             data = json.load(f)
#             return {
#                 normalize_title(item.get("Blog_Title", ""))
#                 for item in data
#             }
#         except:
#             return set()


# # ── Utility ───────────────────────────────────────────────────
# def clean_filename(text):
#     text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
#     text = re.sub(r'[\\/*?:"<>|]', '', text)
#     text = text.replace(" ", "_")
#     text = re.sub(r'_+', '_', text)
#     return text[:60]


# # ── Timed wrappers ───────────────────────────────────────────
# @timed
# def _generate_blog(item):
#     return generate_blog(item)

# @timed
# def _generate_notification(item):
#     return generate_notification(item)

# @timed
# def _generate_instagram(item):
#     return generate_instagram_caption(item)

# @timed
# def _extract_image_text(title, content, category):
#     return extract_image_text(title, content, category)

# @timed
# def _select_template(category, title):
#     return select_template(category, title)

# @timed
# def _compose_image(template, image_text, path, image_type):
#     return compose_image(template, image_text, path, image_type=image_type)

# @timed
# def _save_output(item):
#     return save_output(item)

# @timed
# def _filter_by_country(data, country):
#     return filter_by_country_model(data, country)

# @timed
# def _filter_by_category(data, category):
#     return filter_by_category_model(data, category)


# # ── Main pipeline ─────────────────────────────────────────────
# def run_pipeline(selected_country="India", category="finance"):

#     reset_timings()
#     TOP_N = 20
#     os.makedirs(OUTPUT_IMG_DIR, exist_ok=True)

#     # ── STEP 1: Fetch Data ───────────────────────────────────
#     all_data = []

#     with Timer("fetch_zerodha"):
#         all_data.extend(fetch_zerodha()[:TOP_N])

#     with Timer("fetch_cnbc"):
#         all_data.extend(fetch_cnbc()[:TOP_N])

#     with Timer("fetch_5paisa"):
#         all_data.extend(fetch_5paisa()[:TOP_N])

#     with Timer("fetch_livemint"):
#         all_data.extend(fetch_livemint()[:TOP_N])

#     with Timer("fetch_nse_corporate"):
#         all_data.extend(fetch_nse_corporate()[:TOP_N])

#     print(f"Total collected: {len(all_data)}")

#     # ── STEP 2: Country Filter ───────────────────────────────
#     filtered_data = _filter_by_country(all_data, selected_country)

#     if not filtered_data:
#         print("[WARNING] No country match → using ALL data")
#         filtered_data = all_data

#     print(f"After country filter: {len(filtered_data)}")

#     # ── STEP 3: Category Filter ──────────────────────────────
#     category_filtered_data, source = _filter_by_category(filtered_data, category)
#     working_data = category_filtered_data

#     print(f"After category filter: {len(working_data)}")

#     results = []

#     # ── STEP 4: Smart Selection ──────────────────────────────
#     if working_data:

#         final_category = category if source == "user" else "finance" if source == "finance" else "general"
#         print(f"Using category: {final_category}")

#         # ✅ Load used titles
#         used_titles = load_used_titles()

#         # ✅ Filter unused
#         available_data = [
#             item for item in working_data
#             if normalize_title(item.get("Blog_Title", "")) not in used_titles
#         ]

#         if available_data:
#             print(f"[INFO] Available unique blogs: {len(available_data)}")

#             sampled = random.sample(available_data, min(5, len(available_data)))
#             final_item = random.choice(sampled)

#             print(f"[SELECTED] Fresh blog: {final_item.get('Blog_Title', '')[:50]}")

#         else:
#             print("[INFO] No fresh content — fetching NSE Corporate directly")
#             fresh_nse = fetch_nse_corporate()  # ← fetch live NSE data
#             # Filter unused NSE items
#             unused_nse = [
#             item for item in fresh_nse
#             if normalize_title(item.get("Blog_Title", "")) not in used_titles
#             ]
#             if unused_nse:
#                 final_item = random.choice(unused_nse)
#                 print(f"[SELECTED] Fresh NSE blog: {final_item.get('Blog_Title', '')[:50]}")
#             else:
#                 print("All articles are up to date. Waiting for fresh content from RSS & NSE.")
#                 return results  # ← exit cleanly


#         try:
#             final_item["blog"] = _generate_blog(final_item)
#             final_item["notify"] = _generate_notification(final_item)
#             final_item["instagram_notify"] = _generate_instagram(final_item)

#             final_item["image_text"] = _extract_image_text(
#                 final_item["Blog_Title"],
#                 final_item.get("Blog_Content", ""),
#                 final_category.upper()
#             )

#             final_item["template_path"] = _select_template(
#                 final_category,
#                 final_item["Blog_Title"]
#             )

#             validate_template(final_item["template_path"])

#             safe_title = clean_filename(final_item["Blog_Title"])

#             blog_path = os.path.join(OUTPUT_IMG_DIR, f"blog_{safe_title}.jpg")
#             insta_path = os.path.join(OUTPUT_IMG_DIR, f"insta_{safe_title}.jpg")

#             final_item["blog_image"] = _compose_image(
#                 final_item["template_path"],
#                 final_item["image_text"],
#                 blog_path,
#                 "blog"
#             )

#             final_item["instagram_image"] = _compose_image(
#                 final_item["template_path"],
#                 final_item["image_text"],
#                 insta_path,
#                 "instagram"
#             )

#             final_item["Run_Timestamp"] = get_run_timestamp()

#             # ✅ Save with check
#             saved = _save_output(final_item)

#             if saved:
#                 results.append(final_item)
#                 print(f"[DONE] {final_item['Blog_Title'][:60]}")
#             else:
#                 print(f"[SKIPPED PIPELINE] Already exists: {final_item['Blog_Title'][:60]}")
                
#         except Exception as e:
#             print(f"[ERROR] {e}")

#         print_timing_summary()
#         return results

#     # ── STEP 5: Fallback ─────────────────────────────────────
#     else:
#         print("No data → fallback Zerodha")

#         zerodha_data = fetch_zerodha()
#         if not zerodha_data:
#             return []
        
#         final_item = random.choice(zerodha_data)

#         final_item["blog"] = generate_blog(final_item)
#         final_item["notify"] = generate_notification(final_item)
#         final_item["instagram_notify"] = generate_instagram_caption(final_item)
#         final_item["Run_Timestamp"] = get_run_timestamp()

#         save_output(final_item)

#         return [final_item]



















