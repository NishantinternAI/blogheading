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

from utils.combined_filter import filter_by_country_and_category
from AI_GEN.notify_generator import generate_notification
from AI_GEN.generate_instagram_caption import generate_instagram_caption
from AI_GEN.get_system_timestamp import get_run_timestamp
from AI_GEN.blog_generator import generate_blog
from content_engine.image_module.ai_image_generator import generate_ai_image
from storage.save_output import save_output
from utils.timer import timed, Timer, print_timing_summary, reset_timings


# ── Base directory ────────────────────────────────────────────
BASE_DIR            = os.path.dirname(os.path.abspath(__file__))
OUTPUT_IMG_DIR      = os.path.join(BASE_DIR, "output_images")
OUTPUT_IMG_JPG_DIR  = os.path.join(BASE_DIR, "output_images", "jpg_images")
OUTPUT_IMG_WEBP_DIR = os.path.join(BASE_DIR, "output_images", "webp_images")
STACK_FILE          = os.path.join(BASE_DIR, "output", "article_stack.json")
TIMESTAMP_FILE      = os.path.join(BASE_DIR, "output", "stack_timestamp.json")


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

    TOP_N    = 20
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


# ── Load used titles ──────────────────────────────────────────
def load_used_titles(filepath="output/testing_webp_output.json"):
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
def _generate_ai_image(blog_title, blog_content, blog_outer_paths, blog_inner_paths, instagram_paths, quality="medium"):
    return generate_ai_image(blog_title, blog_content, blog_outer_paths, blog_inner_paths, instagram_paths, quality)
@timed
def _save_output(item):
    return save_output(item)

@timed
def _filter_combined(data, country, category):
    return filter_by_country_and_category(data, country, category)


# ── Main pipeline (har 15 min chalta hai) ────────────────────
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
        if not stack:
            print("[WAITING] Koi naya article nahi mila — fallback Zerodha...")

            zerodha_data = fetch_zerodha()
            if not zerodha_data:
                return []

            final_item = random.choice(zerodha_data)

            final_item["blog"]             = generate_blog(final_item)
            final_item["notify"]           = generate_notification(final_item)
            final_item["instagram_notify"] = generate_instagram_caption(final_item)
            final_item["Run_Timestamp"]    = get_run_timestamp()

            save_output(final_item)
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
        final_item["blog"]             = _generate_blog(final_item)
        final_item["notify"]           = _generate_notification(final_item)
        final_item["instagram_notify"] = _generate_instagram(final_item)

        # ── File paths ────────────────────────────────────────
        safe_title = clean_filename(final_item["Blog_Title"])


        blog_outer_jpg  = os.path.join(OUTPUT_IMG_JPG_DIR,  f"blog_outer_{safe_title}.jpg")
        blog_outer_webp = os.path.join(OUTPUT_IMG_WEBP_DIR, f"blog_outer_{safe_title}.webp")


        blog_inner_jpg  = os.path.join(OUTPUT_IMG_JPG_DIR,  f"blog_inner_{safe_title}.jpg")
        blog_inner_webp = os.path.join(OUTPUT_IMG_WEBP_DIR, f"blog_inner_{safe_title}.webp")



        insta_jpg  = os.path.join(OUTPUT_IMG_JPG_DIR,  f"insta_{safe_title}.jpg")
        insta_webp = os.path.join(OUTPUT_IMG_WEBP_DIR, f"insta_{safe_title}.webp")


        images = _generate_ai_image(
        final_item["Blog_Title"],
        final_item.get("Blog_Content", ""),
        blog_outer_paths = {"jpg": blog_outer_jpg, "webp": blog_outer_webp},
        blog_inner_paths = {"jpg": blog_inner_jpg, "webp": blog_inner_webp},
        instagram_paths  = {"jpg": insta_jpg,      "webp": insta_webp},
        quality          = "medium"
        )

        final_item["blog_image_outer"] = images["blog_outer"]
        final_item["blog_image_inner"] = images["blog_inner"]
        final_item["instagram_image"]  = images["instagram"]




        

        
        final_item["Run_Timestamp"] = get_run_timestamp()

        saved = _save_output(final_item)

        if saved:
            results.append(final_item)
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

# @timed
# def _compose_image(template, image_text, path, image_type):
#     return compose_image(template, image_text, path, image_type=image_type)

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

#             print("[SELECTED] Fresh unique blog")

#         else:
#             print("[FALLBACK] No unique blogs left → Using NSE Corporate")
#             nse_data = [
#             item for item in working_data
#             if "nse" in item.get("source", "").lower()
#             or "corporate" in item.get("source", "").lower()
#             ]


    
#     # ✅ Filter only NSE Corporate data
   

#             if nse_data:
#                 final_item = copy.deepcopy(random.choice(nse_data))
#                 print("[SELECTED] NSE Corporate blog")

        

#             else:
#                 print("[WARNING] No NSE data found → fallback to all")

#                 final_item = copy.deepcopy(random.choice(working_data))

#                 # Optional: mark as variation (if needed)
#             final_item["Blog_Title"] = final_item["Blog_Title"] + " (Updated)"

#         try:
#             final_item["blog"] = _generate_blog(final_item)
#             final_item["notify"] = _generate_notification(final_item)
#             final_item["instagram_notify"] = _generate_instagram(final_item)

#             final_item["image_text"] = _extract_image_text(
#                 final_item["Blog_Title"],
#                 final_item["Blog_Content"],
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
#                 print(f"[DONE] {title[:60]}")
#             else:
#                 print(f"[SKIPPED PIPELINE] Already exists: {title[:60]}")

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

#         final_item = zerodha_data[0]

#         final_item["blog"] = generate_blog(final_item)
#         final_item["notify"] = generate_notification(final_item)
#         final_item["instagram_notify"] = generate_instagram_caption(final_item)
#         final_item["Run_Timestamp"] = get_run_timestamp()

#         save_output(final_item)

#         return [final_item]



















# import os
# import random
# import re
# import unicodedata

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

#     # ── STEP 4: Smart Random Logic ───────────────────────────
#     if working_data:

#         final_category = category if source == "user" else "finance" if source == "finance" else "general"
#         print(f"Using category: {final_category}")

#         MAX_RETRY = 5
#         used_titles = set()   # 🔴 Replace with DB later

#         final_item = None

#         # ✅ Retry logic
#         for attempt in range(MAX_RETRY):

#             sampled = random.sample(working_data, min(5, len(working_data)))
#             candidate = random.choice(sampled)

#             title = candidate.get("Blog_Title", "")
#             print(f"[TRY {attempt+1}] {title[:60]}")

#             if title not in used_titles:
#                 final_item = candidate
#                 print("[SELECTED] Unique blog")
#                 break
#             else:
#                 print("[DUPLICATE] Retrying...")

#         # ✅ Fallback 1 → full list
#         if not final_item:
#             print("[FALLBACK] Searching unused in full list")

#             for item in working_data:
#                 title = item.get("Blog_Title", "")
#                 if title not in used_titles:
#                     final_item = item
#                     print("[SELECTED] From full list")
#                     break

#         # ✅ Fallback 2 → AI variation
#         if not final_item:
#             print("[FALLBACK] AI variation")

#             final_item = random.choice(working_data)
#             final_item["Blog_Title"] += " (Updated)"

#         # ✅ Final fallback
#         if not final_item:
#             print("[LAST FALLBACK] Allow duplicate")
#             final_item = random.choice(working_data)

#         # ── PROCESS ──────────────────────────────────────────
#         title = final_item.get("Blog_Title", "unknown")
#         print(f"\nProcessing: {title[:60]}")

#         try:
#             final_item["blog"] = _generate_blog(final_item)
#             final_item["notify"] = _generate_notification(final_item)
#             final_item["instagram_notify"] = _generate_instagram(final_item)

#             final_item["image_text"] = _extract_image_text(
#                 final_item["Blog_Title"],
#                 final_item["Blog_Content"],
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
#             _save_output(final_item)

#             results.append(final_item)
#             print(f"[DONE] {title[:60]}")

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

#         final_item = zerodha_data[0]

#         final_item["blog"] = generate_blog(final_item)
#         final_item["notify"] = generate_notification(final_item)
#         final_item["instagram_notify"] = generate_instagram_caption(final_item)
#         final_item["Run_Timestamp"] = get_run_timestamp()

#         save_output(final_item)

#         return [final_item]
# import os
# import random
# import re
# import unicodedata

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
# BASE_DIR       = os.path.dirname(os.path.abspath(__file__))
# OUTPUT_IMG_DIR = os.path.join(BASE_DIR, "output_images")


# # ── Utility ───────────────────────────────────────────────────
# def clean_filename(text):
#     text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
#     text = re.sub(r'[\\/*?:"<>|]', '', text)
#     text = text.replace(" ", "_")
#     text = re.sub(r'_+', '_', text)
#     return text[:60]


# # ── Timed wrappers for AI + image steps ──────────────────────
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
# # ── Main pipeline ─────────────────────────────────────────────
# def run_pipeline(selected_country="India", category="finance"):

#     reset_timings()

#     TOP_N = 20
#     os.makedirs(OUTPUT_IMG_DIR, exist_ok=True)

#     # ── STEP 1: Fetch RSS feeds ───────────────────────────────
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

#     # ── STEP 2: Country filter ────────────────────────────────
#     filtered_data = _filter_by_country(all_data, selected_country)

#     if not filtered_data:
#         print("[WARNING] No country match → using ALL data")
#         filtered_data = all_data

#     print(f"After country filter: {len(filtered_data)}")

#     # ── STEP 3: Category filter ───────────────────────────────
#     category_filtered_data, source = _filter_by_category(filtered_data, category)
#     working_data = category_filtered_data

#     print(f"After category filter: {len(working_data)}")

#     results = []

#     # ── STEP 4: Random Selection + Process ────────────────────
#     if working_data:

#         if source == "user":
#             final_category = category
#         elif source == "finance":
#             final_category = "finance"
#         else:
#             final_category = "general"

#         print(f"Using category: {final_category}")

#         # ✅ STEP 4A: Take random sample (max 5)
#         selected_data = random.sample(
#             working_data,
#             min(5, len(working_data))
#         )

#         # ✅ STEP 4B: Pick final item from sample
#         final_item = random.choice(selected_data)

#         title = final_item.get("Blog_Title", "unknown")
#         print(f"\nProcessing RANDOM: {title[:60]}")

#         try:
#             # ── AI generation ─────────────────────────────
#             final_item["blog"]             = _generate_blog(final_item)
#             final_item["notify"]           = _generate_notification(final_item)
#             final_item["instagram_notify"] = _generate_instagram(final_item)

#             # ── Image text extraction ─────────────────────
#             final_item["image_text"]       = _extract_image_text(
#                 final_item["Blog_Title"],
#                 final_item["Blog_Content"],
#                 final_category.upper()
#             )

#             # ── Template selection ────────────────────────
#             final_item["template_path"]    = _select_template(
#                 final_category,
#                 final_item["Blog_Title"]
#             )

#             validate_template(final_item["template_path"])

#             safe_title = clean_filename(final_item["Blog_Title"])

#             blog_output_path  = os.path.join(OUTPUT_IMG_DIR, f"blog_{safe_title}.jpg")
#             insta_output_path = os.path.join(OUTPUT_IMG_DIR, f"insta_{safe_title}.jpg")

#             # ── Image composition ─────────────────────────
#             final_item["blog_image"] = _compose_image(
#                 final_item["template_path"],
#                 final_item["image_text"],
#                 blog_output_path,
#                 "blog"
#             )

#             final_item["instagram_image"] = _compose_image(
#                 final_item["template_path"],
#                 final_item["image_text"],
#                 insta_output_path,
#                 "instagram"
#             )

#             # ── Timestamp + save ──────────────────────────
#             final_item["Run_Timestamp"] = get_run_timestamp()
#             _save_output(final_item)

#             results.append(final_item)
#             print(f"[DONE] {title[:60]}")

#         except Exception as e:
#             print(f"[ERROR] Skipping '{title[:50]}': {e}")

#         print_timing_summary()
#         return results

#     # ── STEP 5: Fallback ──────────────────────────────────────
#     else:
#         print("No data found → fallback to Zerodha")

#         zerodha_data = fetch_zerodha()
#         if not zerodha_data:
#             print("Zerodha also empty")
#             return []

#         final_item = zerodha_data[0]

#         with Timer("fallback_generate_blog"):
#             final_item["blog"] = generate_blog(final_item)

#         with Timer("fallback_generate_notification"):
#             final_item["notify"] = generate_notification(final_item)

#         with Timer("fallback_generate_instagram"):
#             final_item["instagram_notify"] = generate_instagram_caption(final_item)

#         final_item["Run_Timestamp"] = get_run_timestamp()

#         with Timer("fallback_save_output"):
#             save_output(final_item)

#         print_timing_summary()

#         return [final_item]








































































































# def run_pipeline(selected_country="India", category="finance"):

#     reset_timings()

#     TOP_N = 20
#     os.makedirs(OUTPUT_IMG_DIR, exist_ok=True)

#     # ── STEP 1: Fetch RSS feeds ───────────────────────────────
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

#     # ── STEP 2: Country filter ────────────────────────────────
#     filtered_data = _filter_by_country(all_data, selected_country)

#     if not filtered_data:
#         print("[WARNING] No country match → using ALL data")
#         filtered_data = all_data

#     print(f"After country filter: {len(filtered_data)}")

#     # ── STEP 3: Category filter ───────────────────────────────
#     category_filtered_data, source = _filter_by_category(filtered_data, category)
#     working_data = category_filtered_data

#     print(f"After category filter: {len(working_data)}")

#     results = []

#     # ── STEP 4: Process each item ─────────────────────────────
#     if working_data:

#         if source == "user":
#             final_category = category
#         elif source == "finance":
#             final_category = "finance"
#         else:
#             final_category = "general"

#         print(f"Using category: {final_category}")

#         for item in working_data:
#             title = item.get("Blog_Title", "unknown")
#             print(f"\nProcessing: {title[:60]}")

#             try:
#                 # ── AI generation ─────────────────────────────
#                 item["blog"]             = _generate_blog(item)
#                 item["notify"]           = _generate_notification(item)
#                 item["instagram_notify"] = _generate_instagram(item)

#                 # ── Image text extraction ─────────────────────
#                 item["image_text"]       = _extract_image_text(
#                     item["Blog_Title"],
#                     item["Blog_Content"],
#                     final_category.upper()
#                 )

#                 # ── Template selection ────────────────────────
#                 item["template_path"]    = _select_template(
#                     final_category,
#                     item["Blog_Title"]
#                 )

#                 validate_template(item["template_path"])

#                 safe_title               = clean_filename(item["Blog_Title"])
#                 blog_output_path         = os.path.join(OUTPUT_IMG_DIR, f"blog_{safe_title}.jpg")
#                 insta_output_path        = os.path.join(OUTPUT_IMG_DIR, f"insta_{safe_title}.jpg")

#                 # ── Image composition ─────────────────────────
#                 item["blog_image"]       = _compose_image(
#                     item["template_path"],
#                     item["image_text"],
#                     blog_output_path,
#                     "blog"
#                 )

#                 item["instagram_image"]  = _compose_image(
#                     item["template_path"],
#                     item["image_text"],
#                     insta_output_path,
#                     "instagram"
#                 )

#                 # ── Timestamp + save ──────────────────────────
#                 item["Run_Timestamp"]    = get_run_timestamp()
#                 _save_output(item)

#                 results.append(item)
#                 print(f"[DONE] {title[:60]}")

#             except Exception as e:
#                 print(f"[ERROR] Skipping '{title[:50]}': {e}")
#                 continue

#         # ── Print timing summary after all items ──────────────
#         print_timing_summary()

#         return results

#     # ── STEP 5: Fallback ──────────────────────────────────────
#     else:
#         print("No data found → fallback to Zerodha")

#         zerodha_data = fetch_zerodha()
#         if not zerodha_data:
#             print("Zerodha also empty")
#             return []

#         final_item = zerodha_data[0]

#         with Timer("fallback_generate_blog"):
#             final_item["blog"] = generate_blog(final_item)

#         with Timer("fallback_generate_notification"):
#             final_item["notify"] = generate_notification(final_item)

#         with Timer("fallback_generate_instagram"):
#             final_item["instagram_notify"] = generate_instagram_caption(final_item)

#         final_item["Run_Timestamp"] = get_run_timestamp()

#         with Timer("fallback_save_output"):
#             save_output(final_item)

#         print_timing_summary()

#         return [final_item]





























# import random
# import re
# import unicodedata

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


# # -------------------------------
# # Utility: Clean filename
# # -------------------------------
# def clean_filename(text):
#     text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
#     text = re.sub(r'[\\/*?:"<>|]', '', text)
#     text = text.replace(" ", "_")
#     text = re.sub(r'_+', '_', text)
#     return text[:60]


# # -------------------------------
# # MAIN PIPELINE FUNCTION
# # -------------------------------
# def run_pipeline(selected_country="India", category="finance"):

#     TOP_N = 5

#     # -------------------------------
#     # STEP 1: Collect Data
#     # -------------------------------
#     all_data = []
#     all_data.extend(fetch_zerodha()[:TOP_N])
#     all_data.extend(fetch_cnbc()[:TOP_N])
#     all_data.extend(fetch_5paisa()[:TOP_N])
#     all_data.extend(fetch_livemint()[:TOP_N])
#     all_data.extend(fetch_nse_corporate()[:TOP_N])

#     print(f"Total collected: {len(all_data)}")

#     # -------------------------------
#     # STEP 2: Country Filter
#     # -------------------------------
#     filtered_data = filter_by_country_model(all_data, selected_country)

#     if not filtered_data:
#         print("[WARNING] No country match → using ALL data")
#         filtered_data = all_data

#     print("After country filter:", len(filtered_data))

#     # -------------------------------
#     # STEP 3: Category Filter
#     # -------------------------------
#     category_filtered_data, source = filter_by_category_model(
#         filtered_data, category
#     )

#     working_data = category_filtered_data

#     print("After category filter:", len(working_data))

#     results = []

#     # -------------------------------
#     # STEP 4: Decision Logic
#     # -------------------------------
#     if working_data:

#         if source == "user":
#             final_category = category
#         elif source == "finance":
#             final_category = "finance"
#         else:
#             final_category = "general"

#         print(f"Using category: {final_category}")

#         # -------------------------------
#         # STEP 5: Process Each Item
#         # -------------------------------
#         for item in working_data:

#             # ---- AI Content ----
#             item["blog"] = generate_blog(item)
#             item["notify"] = generate_notification(item)
#             item["instagram_notify"] = generate_instagram_caption(item)

#             # ---- Image Text ----
#             item["image_text"] = extract_image_text(
#                 item["Blog_Title"],
#                 item["Blog_Content"],
#                 final_category.upper()
#             )

#             # ---- Template ----
#             item["template_path"] = select_template(
#                 final_category,
#                 item["Blog_Title"]
#             )

#             validate_template(item["template_path"])

#             # ---- Safe filename ----
#             safe_title = clean_filename(item["Blog_Title"])

#             # ---- Blog Image ----
#             blog_output_path = f"output_images/blog_{safe_title}.jpg"
#             item["blog_image"] = compose_image(
#                 item["template_path"],
#                 item["image_text"],
#                 blog_output_path,
#                 image_type="blog"
#             )

#             # ---- Instagram Image ----
#             insta_output_path = f"output_images/insta_{safe_title}.jpg"
#             item["instagram_image"] = compose_image(
#                 item["template_path"],
#                 item["image_text"],
#                 insta_output_path,
#                 image_type="instagram"
#             )

#             # ---- Timestamp ----
#             item["Run_Timestamp"] = get_run_timestamp()

#             # ---- Save ----
#             save_output(item)

#             # ---- Append to results ----
#             results.append(item)

#         return results

#     # -------------------------------
#     # STEP 6: Fallback (No Data)
#     # -------------------------------
#     else:
#         print("No data found → fallback to Zerodha")

#         zerodha_data = fetch_zerodha()

#         if not zerodha_data:
#             print("Zerodha also empty ❌")
#             return []

#         final_item = zerodha_data[0]

#         final_item["blog"] = generate_blog(final_item)
#         final_item["notify"] = generate_notification(final_item)
#         final_item["instagram_notify"] = generate_instagram_caption(final_item)
#         final_item["Run_Timestamp"] = get_run_timestamp()

#         save_output(final_item)

#         return [final_item]