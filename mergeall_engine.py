# import os
# import glob
# import random
# import re
# import unicodedata
# import json
# from datetime import datetime

# # ── RSS Fetchers ──────────────────────────────────────────────
# from RSS.zerodha             import fetch_zerodha
# from RSS.cnbc                import fetch_cnbc
# from RSS.paisa               import fetch_5paisa
# from RSS.livemint            import fetch_livemint
# from RSS.fetch_nse_corporate import fetch_nse_corporate
# from RSS.ipo                 import fetch_nse_ipo

# # ── Image modules ─────────────────────────────────────────────
# from content_engine.image_module.text_extractor import extract_image_text
# from content_engine.image_module.tempalte_selector import (
#     select_template,
#     select_template_pair,
#     select_template_pair_smart
# )
# from content_engine.image_module.compositor     import compose_image
# from content_engine.image_module.ipo_compositor import compose_ipo_image
# from content_engine.image_module.validator      import validate_template
# from content_engine.image_module.ai_image_generator import generate_ai_image

# # ── Utilities & AI ────────────────────────────────────────────
# from utils.combined_filter import filter_by_country_and_category
# from AI_GEN.notify_generator            import generate_notification
# from AI_GEN.generate_instagram_caption  import generate_instagram_caption
# from AI_GEN.get_system_timestamp        import get_run_timestamp
# from AI_GEN.blog_generator              import generate_blog
# from storage.save_output                import save_output
# from utils.timer import timed, Timer, print_timing_summary, reset_timings


# # ══════════════════════════════════════════════════════════════
# #  BASE DIRECTORIES
# # ══════════════════════════════════════════════════════════════

# BASE_DIR            = os.path.dirname(os.path.abspath(__file__))
# OUTPUT_IMG_DIR      = os.path.join(BASE_DIR, "output_images")
# OUTPUT_IMG_JPG_DIR  = os.path.join(BASE_DIR, "output_images", "jpg_images")
# OUTPUT_IMG_WEBP_DIR = os.path.join(BASE_DIR, "output_images", "webp_images")
# TIMESTAMP_FILE      = os.path.join(BASE_DIR, "output", "stack_timestamp.json")
# PATTERN_INDEX_FILE  = os.path.join(BASE_DIR, "output", "pattern_index.json")

# STACK_FILES = {
#     "priority":  os.path.join(BASE_DIR, "output", "stack_priority.json"),
#     "news":      os.path.join(BASE_DIR, "output", "stack_news.json"),
#     "corporate": os.path.join(BASE_DIR, "output", "stack_corporate.json"),
# }

# USE_AI_IMAGES   = True
# OUTPUT_FILENAME = "testing_webp_output.json" if USE_AI_IMAGES else "output.json"
# print(f"[MODE] USE_AI_IMAGES={USE_AI_IMAGES} → saving to output/{OUTPUT_FILENAME}")


# # ══════════════════════════════════════════════════════════════
# #  POSTING PATTERN CONFIG
# # ══════════════════════════════════════════════════════════════

# POSTING_PATTERN = [
#     "priority",
#     "news",
#     "priority",
#     "corporate",
# ]


# # ══════════════════════════════════════════════════════════════
# #  SOURCE CONFIG
# # ══════════════════════════════════════════════════════════════

# PRIORITY_SOURCES  = ["nse_ipo"]
# CORPORATE_SOURCES = ["nse_corporate"]
# NEWS_SOURCES      = ["zerodha", "cnbc", "5paisa", "livemint"]


# # ══════════════════════════════════════════════════════════════
# #  IPO TEMPLATE FINDER
# # ══════════════════════════════════════════════════════════════

# def _get_ipo_template_path() -> str:
#     """Returns IPO Alert template path (for blog outer + instagram)."""
#     ipo_template = os.path.join(
#         BASE_DIR, "content_engine", "templates", "ipo_alert.png"
#     )
#     print(f"[DEBUG] IPO template path: {ipo_template}")
#     if os.path.exists(ipo_template):
#         print(f"[IPO TEMPLATE] Found: {ipo_template}")
#         return ipo_template
#     print("[IPO TEMPLATE] File NOT found")
#     return ""

# def _get_ipo_inner_template_path() -> str:
#     """
#     Returns IPO Blog Inner template path (1920×490).
#     This is a separate pre-made image — no resize needed.
#     Falls back to ipo_alert.png if ipo_inner.png not found.
#     """
#     ipo_inner = os.path.join(
#         BASE_DIR, "content_engine", "templates", "ipo_inner.png"
#     )
#     print(f"[DEBUG] IPO inner template path: {ipo_inner}")
#     if os.path.exists(ipo_inner):
#         print(f"[IPO INNER] Found: {ipo_inner}")
#         return ipo_inner

#     # Fallback — use main template (will be resized)
#     print("[IPO INNER] ipo_inner.png not found — using ipo_alert.png fallback")
#     return _get_ipo_template_path()
# # ══════════════════════════════════════════════════════════════
# #  IPO IMAGE TEXT EXTRACTOR
# #  Fallback when IPO template not found
# # ══════════════════════════════════════════════════════════════

# def _extract_ipo_image_text(article: dict) -> dict:
#     company    = article.get("company", article.get("Blog_Title", ""))
#     open_date  = article.get("open_date",    "")
#     listing    = article.get("listing_date", "")
#     price      = article.get("price_band",   "")
#     lot        = article.get("lot_size",      "")
#     issue_size = article.get("issue_size",   "")
#     doc_type   = article.get("doc_type",     "IPO")

#     company_short = company\
#         .replace(" Limited", "").replace(" Ltd", "")\
#         .replace(" (India)", "").strip()

#     tag = "IPO"

#     if open_date:
#         headline = f"{company_short} IPO Opens {open_date}"
#     elif doc_type == "RHP":
#         headline = f"{company_short} IPO Opening Soon"
#     elif doc_type == "PROSP":
#         headline = f"{company_short} IPO Prospectus Filed"
#     else:
#         headline = f"{company_short} Files for IPO"

#     words = headline.split()
#     if len(words) > 6:
#         headline = " ".join(words[:6])

#     parts = []
#     if price:
#         parts.append(f"Price {price}")
#     if lot:
#         lot_num = lot.replace(" Shares","").replace(" shares","").strip()
#         parts.append(f"Lot {lot_num}")
#     if listing:
#         listing_short = listing\
#             .replace("Fri, ","").replace("Mon, ","").replace("Tue, ","")\
#             .replace("Wed, ","").replace("Thu, ","").replace("Sat, ","")\
#             .replace("Sun, ","").replace(", 2026","").replace(", 2025","")\
#             .strip()
#         parts.append(f"Listing {listing_short}")
#     elif issue_size:
#         parts.append(f"Size {issue_size[:10]}")

#     subtext = " · ".join(parts) if parts else f"IPO Alert — {doc_type} Filed"
#     subtext_words = subtext.split()
#     if len(subtext_words) > 10:
#         subtext = " ".join(subtext_words[:10])

#     result = {"tag": tag, "headline": headline, "subtext": subtext}
#     print(f"[IPO IMAGE TEXT] tag={result['tag']} | "
#           f"headline={result['headline']} | subtext={result['subtext']}")
#     return result


# # ══════════════════════════════════════════════════════════════
# #  SOURCE CLASSIFIER
# # ══════════════════════════════════════════════════════════════

# def classify_source(article: dict) -> str:
#     source = article.get("source", "").lower().strip()
#     if source in PRIORITY_SOURCES:
#         return "priority"
#     if source in CORPORATE_SOURCES:
#         return "corporate"
#     return "news"


# # ══════════════════════════════════════════════════════════════
# #  STACK HELPERS
# # ══════════════════════════════════════════════════════════════

# def save_stack(stack: list, source_type: str):
#     path = STACK_FILES[source_type]
#     os.makedirs(os.path.dirname(path), exist_ok=True)
#     with open(path, "w", encoding="utf-8") as f:
#         json.dump(stack, f, ensure_ascii=False, indent=2)
#     print(f"[STACK] {source_type:<10} → {len(stack)} articles saved")


# def load_stack(source_type: str) -> list:
#     path = STACK_FILES[source_type]
#     if not os.path.exists(path):
#         return []
#     with open(path, "r", encoding="utf-8") as f:
#         try:
#             return json.load(f)
#         except:
#             return []


# def load_all_stacks() -> dict:
#     stacks = {t: load_stack(t) for t in STACK_FILES}
#     print(f"[STACK] Loaded → Priority:{len(stacks['priority'])} | "
#           f"News:{len(stacks['news'])} | Corporate:{len(stacks['corporate'])}")
#     return stacks


# def total_stack_size(stacks: dict) -> int:
#     return sum(len(v) for v in stacks.values())


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
#     with open(TIMESTAMP_FILE) as f:
#         try:
#             return json.load(f).get("stack_built_at")
#         except:
#             return None


# # ══════════════════════════════════════════════════════════════
# #  PATTERN INDEX
# # ══════════════════════════════════════════════════════════════

# def load_pattern_index() -> int:
#     if not os.path.exists(PATTERN_INDEX_FILE):
#         return 0
#     with open(PATTERN_INDEX_FILE) as f:
#         try:
#             return json.load(f).get("current_index", 0)
#         except:
#             return 0


# def save_pattern_index(index: int, source_type: str):
#     os.makedirs(os.path.dirname(PATTERN_INDEX_FILE), exist_ok=True)
#     with open(PATTERN_INDEX_FILE, "w") as f:
#         json.dump({
#             "current_index": index,
#             "last_type":     source_type,
#             "at":            datetime.now().isoformat()
#         }, f)
#     print(f"[PATTERN] Saved index={index} last_type={source_type}")


# # ══════════════════════════════════════════════════════════════
# #  PATTERN-BASED POP DECISION
# # ══════════════════════════════════════════════════════════════

# def decide_pop_type(stacks: dict) -> str | None:
#     has = {
#         "priority":  len(stacks.get("priority",  [])) > 0,
#         "news":      len(stacks.get("news",      [])) > 0,
#         "corporate": len(stacks.get("corporate", [])) > 0,
#     }

#     print(f"[POP] Stack sizes → "
#           f"Priority:{len(stacks.get('priority',[]))} | "
#           f"News:{len(stacks.get('news',[]))} | "
#           f"Corporate:{len(stacks.get('corporate',[]))}")

#     if not any(has.values()):
#         print("[POP] All stacks empty")
#         return None

#     current_index = load_pattern_index()
#     pattern_len   = len(POSTING_PATTERN)
#     print(f"[PATTERN] index={current_index} | Pattern={POSTING_PATTERN}")

#     for attempt in range(pattern_len):
#         idx         = (current_index + attempt) % pattern_len
#         wanted_type = POSTING_PATTERN[idx]

#         if has[wanted_type]:
#             next_index = (idx + 1) % pattern_len
#             save_pattern_index(next_index, wanted_type)
#             print(f"[PATTERN] idx={idx} → {wanted_type} ✅ → next={next_index}")
#             return wanted_type

#         print(f"[PATTERN] idx={idx} → {wanted_type} empty, skip")

#     return None


# # ══════════════════════════════════════════════════════════════
# #  DATE PARSER — for IPO oldest-first sorting
# # ══════════════════════════════════════════════════════════════

# def _parse_published_date(pub_str: str) -> datetime:
#     """
#     Parses published date string into datetime for sorting.
#     Falls back to datetime.min if unparseable (treated as oldest).
#     """
#     if not pub_str:
#         return datetime.min

#     formats = [
#         "%d-%b-%Y",                      # "22-May-2026"
#         "%d-%B-%Y",                      # "22-May-2026" full month
#         "%Y-%m-%d",                      # "2026-05-22"
#         "%d %b, %Y",                     # "22 May, 2026"
#         "%d %B, %Y",                     # "22 May, 2026" full month
#         "%a, %d %b %Y %H:%M:%S %z",     # "Tue, 20 May 2026 00:00:00 +0530"
#         "%a, %d %b %Y",                  # "Tue, 20 May 2026"
#         "%d %b %Y",                      # "22 May 2026"
#     ]

#     for fmt in formats:
#         try:
#             return datetime.strptime(pub_str.strip(), fmt)
#         except ValueError:
#             continue

#     return datetime.min


# # ══════════════════════════════════════════════════════════════
# #  STEP 4 — ARTICLE SELECTION FROM STACK
# #
# #  IPO articles (source=nse_ipo) inside priority stack:
# #    → sort by published date (oldest first)
# #    → tiebreaker: _stack_index (order added to stack)
# #    → _stack_index is set ONLY on IPO articles in
# #      _build_stacks_from_articles()
# #
# #  Non-IPO articles inside priority stack:
# #    → random.choice()
# #
# #  News stack    → random.choice()
# #  Corporate stack → random.choice()
# # ══════════════════════════════════════════════════════════════

# def _pop_article_from_stack(stack: list, pop_type: str) -> tuple:
#     """
#     Selects and removes one article from the stack.

#     Returns:
#         (selected_article, updated_stack)
#     """
#     if not stack:
#         return None, stack

#     ipo_articles = [a for a in stack if a.get("source") == "nse_ipo"]

#     # ── Priority + has IPO articles → oldest first ────────────
#     if pop_type == "priority" and ipo_articles:

#         def sort_key(a):
#             # Primary:   published date (oldest first)
#             # Tiebreaker: _stack_index (lower = fetched earlier)
#             #             only IPO articles have _stack_index
#             #             9999 fallback for any edge case
#             published   = _parse_published_date(a.get("published", ""))
#             stack_index = a.get("_stack_index", 9999)
#             return (published, stack_index)

#         ipo_sorted = sorted(ipo_articles, key=sort_key)
#         selected   = ipo_sorted[0]

#         print(f"[POP] IPO → oldest-first (published + _stack_index)")
#         print(f"[POP] Selected   : '{selected.get('Blog_Title','')[:50]}'")
#         print(f"[POP] Published  : {selected.get('published',    'N/A')}")
#         print(f"[POP] StackIndex : {selected.get('_stack_index', 'N/A')}")

#         if len(ipo_articles) > 1:
#             print(f"[POP] Skipped {len(ipo_articles)-1} newer IPO article(s):")
#             for s in ipo_sorted[1:]:
#                 print(f"[POP]   · idx={s.get('_stack_index','?')} "
#                       f"pub={s.get('published','N/A')} "
#                       f"'{s.get('Blog_Title','')[:35]}'")

#     # ── Everything else → random.choice() ────────────────────
#     # Covers: non-IPO priority, news, corporate
#     else:
#         selected = random.choice(stack)

#         label = {
#             "priority":  "PRIORITY (non-IPO)",
#             "news":      "NEWS",
#             "corporate": "CORPORATE",
#         }.get(pop_type, pop_type.upper())

#         print(f"[POP] Random → [{label}]")
#         print(f"[POP] Selected : '{selected.get('Blog_Title','')[:50]}'")

#     updated_stack = [a for a in stack if a is not selected]
#     return selected, updated_stack


# # ══════════════════════════════════════════════════════════════
# #  FETCH ALL SOURCES
# # ══════════════════════════════════════════════════════════════

# def _fetch_all_sources(top_n: int = 6) -> list:
#     all_data = []

#     sources = [
#         (fetch_nse_ipo,       "nse_ipo"),
#         (fetch_nse_corporate, "nse_corporate"),
#         (fetch_zerodha,       "zerodha"),
#         (fetch_cnbc,          "cnbc"),
#         (fetch_5paisa,        "5paisa"),
#         (fetch_livemint,      "livemint"),
#     ]

#     for fetcher, source_name in sources:
#         try:
#             with Timer(f"fetch_{source_name}"):
#                 data = fetcher(top_n) if source_name == "nse_ipo" \
#                        else fetcher()[:top_n]
#                 for article in data:
#                     article["source"] = source_name
#                 all_data.extend(data)
#                 print(f"[FETCH] {source_name:<15} → {len(data)} articles")
#         except Exception as e:
#             print(f"[FETCH] {source_name} failed: {e}")

#     print(f"[FETCH] Total: {len(all_data)}")
#     return all_data


# # ══════════════════════════════════════════════════════════════
# #  BUILD STACKS
# #
# #  _stack_index is added ONLY to IPO articles (source=nse_ipo)
# #  It records the order each IPO article was added to the stack
# #  Used as tiebreaker when published dates are identical
# #  Non-IPO, news, corporate → NO _stack_index added
# # ══════════════════════════════════════════════════════════════

# def _build_stacks_from_articles(articles: list) -> dict:
#     seen_titles     = set()
#     unique_articles = []

#     for article in articles:
#         norm = normalize_title(article.get("Blog_Title", ""))
#         if norm not in seen_titles:
#             seen_titles.add(norm)
#             unique_articles.append(article)
#         else:
#             print(f"[DEDUP] Removed: {article['Blog_Title'][:50]}")

#     print(f"[DEDUP] {len(articles)} → {len(unique_articles)} after stack dedup")

#     used_titles = load_used_titles()
#     fresh = [
#         item for item in unique_articles
#         if normalize_title(item.get("Blog_Title", "")) not in used_titles
#     ]
#     removed = len(unique_articles) - len(fresh)
#     if removed:
#         print(f"[DEDUP] Removed {removed} already published")
#     print(f"[DEDUP] {len(unique_articles)} → {len(fresh)} fresh remain")

#     buckets     = {"priority": [], "news": [], "corporate": []}
#     ipo_counter = 0   # counts ONLY IPO articles — used for _stack_index

#     for article in fresh:
#         st = classify_source(article)
#         article["_source_type"] = st

#         # ── Add _stack_index ONLY to IPO articles ─────────────
#         # Gives each IPO article a unique position number
#         # Lower number = fetched earlier = posts first (tiebreaker)
#         # Non-IPO articles do NOT get _stack_index
#         if article.get("source") == "nse_ipo":
#             article["_stack_index"] = ipo_counter
#             ipo_counter += 1
#             print(f"[STACK IDX] IPO #{article['_stack_index']} → "
#                   f"'{article.get('Blog_Title','')[:45]}'")

#         buckets[st].append(article)

#     print(f"\n[STACK BUILD] Priority:{len(buckets['priority'])} | "
#           f"News:{len(buckets['news'])} | Corporate:{len(buckets['corporate'])}")

#     for st, stack in buckets.items():
#         save_stack(stack, st)

#     save_timestamp()
#     return buckets


# # ══════════════════════════════════════════════════════════════
# #  FULL FETCH + FETCH AFTER TIMESTAMP
# # ══════════════════════════════════════════════════════════════

# def _full_fetch_and_build_stack(selected_country: str, category: str) -> dict:
#     print("\n" + "="*50)
#     print("  PHASE 1 — BUILDING FRESH STACK")
#     print("="*50)

#     all_data = _fetch_all_sources(top_n=6)

#     # IPO articles bypass AI filter
#     ipo_articles   = [a for a in all_data if a.get("source") == "nse_ipo"]
#     other_articles = [a for a in all_data if a.get("source") != "nse_ipo"]

#     print(f"[FILTER] IPO articles (bypass filter): {len(ipo_articles)}")

#     filtered_other, source = filter_by_country_and_category(
#         other_articles, selected_country, category
#     )
#     print(f"[FILTER] Other articles after filter: {len(filtered_other)}")

#     filtered_data = ipo_articles + filtered_other
#     print(f"[FILTER] Total combined: {len(filtered_data)}")

#     if not filtered_data:
#         print("[STACK] No articles after filter!")
#         return {"priority": [], "news": [], "corporate": []}

#     stacks = _build_stacks_from_articles(filtered_data)
#     print("="*50 + "\n")
#     return stacks


# def _fetch_after_timestamp(
#     selected_country: str,
#     category: str,
#     saved_ts: str
# ) -> dict:
#     print(f"\n[STACK EMPTY] Fetching after: {saved_ts}")

#     all_data = _fetch_all_sources(top_n=6)

#     ipo_articles   = [a for a in all_data if a.get("source") == "nse_ipo"]
#     other_articles = [a for a in all_data if a.get("source") != "nse_ipo"]

#     print(f"[FILTER] IPO articles (bypass filter): {len(ipo_articles)}")

#     filtered_other, source = filter_by_country_and_category(
#         other_articles, selected_country, category
#     )
#     print(f"[FILTER] Other articles after filter: {len(filtered_other)}")

#     filtered_data = ipo_articles + filtered_other
#     print(f"[FILTER] Total combined: {len(filtered_data)}")

#     if not filtered_data:
#         print("[STACK] No new articles yet — retrying next cycle")
#         return {"priority": [], "news": [], "corporate": []}

#     return _build_stacks_from_articles(filtered_data)


# # ══════════════════════════════════════════════════════════════
# #  UTILITY
# # ══════════════════════════════════════════════════════════════

# def normalize_title(title: str) -> str:
#     return re.sub(r'\s+', ' ', title.strip().lower())


# def clean_newlines(text):
#     if not isinstance(text, str):
#         return text
#     return text.replace('\\n\\n', '').replace('\\n', '')


# def clean_filename(text: str) -> str:
#     text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
#     text = re.sub(r'[\\/*?:"<>|]', '', text)
#     text = text.replace(" ", "_")
#     text = re.sub(r'_+', '_', text)
#     return text[:60]


# def load_used_titles() -> set:
#     filepath = f"output/{OUTPUT_FILENAME}"
#     if not os.path.exists(filepath):
#         return set()
#     with open(filepath, "r", encoding="utf-8") as f:
#         try:
#             data = json.load(f)
#             return {normalize_title(item.get("Blog_Title", "")) for item in data}
#         except:
#             return set()


# # ══════════════════════════════════════════════════════════════
# #  TIMED WRAPPERS
# # ══════════════════════════════════════════════════════════════

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
# def _select_template_pair_smart(category, title, content=""):
#     return select_template_pair_smart(category, title, content)

# @timed
# def _compose_image(template, image_text, jpg_path, webp_path, image_type):
#     return compose_image(
#         template, image_text, jpg_path, webp_path,
#         image_type=image_type
#     )

# @timed
# def _compose_ipo_image(template, article, jpg_path, webp_path, image_type):
#     return compose_ipo_image(
#         template, article, jpg_path, webp_path,
#         image_type=image_type
#     )

# @timed
# def _generate_ai_image(
#     blog_title, blog_content,
#     blog_outer_paths, blog_inner_paths,
#     instagram_paths, quality="medium"
# ):
#     return generate_ai_image(
#         blog_title, blog_content,
#         blog_outer_paths, blog_inner_paths,
#         instagram_paths, quality
#     )

# @timed
# def _save_output(item, filename):
#     return save_output(item, filename=filename)


# # ══════════════════════════════════════════════════════════════
# #  MAIN PIPELINE
# # ══════════════════════════════════════════════════════════════

# def run_pipeline(selected_country="India", category="finance"):

#     reset_timings()
#     os.makedirs(OUTPUT_IMG_DIR,      exist_ok=True)
#     os.makedirs(OUTPUT_IMG_JPG_DIR,  exist_ok=True)
#     os.makedirs(OUTPUT_IMG_WEBP_DIR, exist_ok=True)
#     results = []

#     # ══════════════════════════════════════════════════════════
#     # STEP 1 — Load all 3 stacks from disk
#     # ══════════════════════════════════════════════════════════
#     stacks = load_all_stacks()

#     # ══════════════════════════════════════════════════════════
#     # STEP 2 — Rebuild stacks if all empty
#     # ══════════════════════════════════════════════════════════
#     if total_stack_size(stacks) == 0:
#         saved_ts = load_timestamp()

#         if saved_ts is None:
#             print("[STACK] First run — full fetch...")
#             stacks = _full_fetch_and_build_stack(selected_country, category)
#         else:
#             print(f"[STACK] All empty — fetching after: {saved_ts}")
#             stacks = _fetch_after_timestamp(selected_country, category, saved_ts)

#         # ── Fallback: zerodha random if still empty ───────────
#         if total_stack_size(stacks) == 0:
#             print("[WAITING] No new articles — fallback Zerodha...")

#             zerodha_data = fetch_zerodha()
#             if not zerodha_data:
#                 print("[FALLBACK] Zerodha also empty — aborting")
#                 return []

#             final_item                     = random.choice(zerodha_data)
#             final_item["source"]           = "zerodha"
#             final_item["_source_type"]     = "news"
#             final_item["source_type"]      = "news"
#             final_item["blog"]             = clean_newlines(generate_blog(final_item))
#             final_item["notify"]           = clean_newlines(generate_notification(final_item))
#             final_item["instagram_notify"] = clean_newlines(generate_instagram_caption(final_item))
#             final_item["Run_Timestamp"]    = get_run_timestamp()

#             safe_title     = clean_filename(final_item["Blog_Title"])
#             image_text     = extract_image_text(
#                 final_item["Blog_Title"],
#                 final_item.get("Blog_Content", ""),
#                 category.upper()
#             )
#             final_item["image_text"] = image_text
#             template_pair  = select_template_pair_smart(
#                 category,
#                 final_item["Blog_Title"],
#                 final_item.get("Blog_Content", "")
#             )
#             outer_template = template_pair["outer"]
#             inner_template = template_pair["inner"]

#             final_item["blog_image"] = compose_image(
#                 outer_template, image_text,
#                 os.path.join(OUTPUT_IMG_JPG_DIR,  f"blog_{safe_title}.jpg"),
#                 os.path.join(OUTPUT_IMG_WEBP_DIR, f"blog_{safe_title}.webp"),
#                 image_type="blog"
#             )
#             final_item["blog_image_inner"] = compose_image(
#                 inner_template, {},
#                 os.path.join(OUTPUT_IMG_JPG_DIR,  f"blog_inner_{safe_title}.jpg"),
#                 os.path.join(OUTPUT_IMG_WEBP_DIR, f"blog_inner_{safe_title}.webp"),
#                 image_type="blog_inner"
#             )
#             final_item["instagram_image"] = compose_image(
#                 outer_template, image_text,
#                 os.path.join(OUTPUT_IMG_JPG_DIR,  f"insta_{safe_title}.jpg"),
#                 os.path.join(OUTPUT_IMG_WEBP_DIR, f"insta_{safe_title}.webp"),
#                 image_type="instagram"
#             )
#             save_output(final_item, filename=OUTPUT_FILENAME)
#             return [final_item]

#     # ══════════════════════════════════════════════════════════
#     # STEP 3 — Decide which stack to pop (pattern-based)
#     # ══════════════════════════════════════════════════════════
#     pop_type = decide_pop_type(stacks)

#     if pop_type is None:
#         print("[STACK] All stacks empty — nothing to process")
#         return []

#     # ══════════════════════════════════════════════════════════
#     # STEP 4 — Select article from chosen stack
#     #
#     # Priority + IPO (nse_ipo) → oldest published + _stack_index
#     # Priority + non-IPO       → random.choice()
#     # News                     → random.choice()
#     # Corporate                → random.choice()
#     # ══════════════════════════════════════════════════════════
#     chosen_stack          = stacks[pop_type]
#     final_item, new_stack = _pop_article_from_stack(chosen_stack, pop_type)

#     stacks[pop_type] = new_stack
#     save_stack(new_stack, pop_type)

#     print(f"\n[POPPED]  [{pop_type.upper()}] "
#           f"{final_item.get('Blog_Title', '')[:60]}")
#     print(f"[STACK]   Priority:{len(stacks['priority'])} | "
#           f"News:{len(stacks['news'])} | "
#           f"Corporate:{len(stacks['corporate'])}")

#     final_category = category

#     # ══════════════════════════════════════════════════════════
#     # STEP 5 — Duplicate check (safety net)
#     # ══════════════════════════════════════════════════════════
#     used_titles = load_used_titles()
#     if normalize_title(final_item.get("Blog_Title", "")) in used_titles:
#         print("[SKIPPED] Already published — next cycle will retry")
#         return []

#     print(f"[SELECTED] [{pop_type.upper()}] "
#           f"{final_item.get('Blog_Title', '')[:50]}")

#     try:
#         # ══════════════════════════════════════════════════════
#         # STEP 6 — Generate blog + notification + instagram (AI)
#         # ══════════════════════════════════════════════════════
#         final_item["blog"]             = clean_newlines(_generate_blog(final_item))
#         final_item["notify"]           = clean_newlines(_generate_notification(final_item))
#         final_item["instagram_notify"] = clean_newlines(_generate_instagram(final_item))
#         final_item["Run_Timestamp"]    = get_run_timestamp()
#         final_item["source_type"]      = pop_type

#         safe_title = clean_filename(final_item["Blog_Title"])

#         # ══════════════════════════════════════════════════════
#         # STEP 7 — Generate images
#         #
#         # BRANCH A: priority + source=nse_ipo → ipo_compositor
#         # BRANCH B: everything else           → compositor
#         # ══════════════════════════════════════════════════════

#         if USE_AI_IMAGES:
#             print(f"[IMAGE MODE] AI images → {OUTPUT_FILENAME}")
#             images = _generate_ai_image(
#                 final_item["Blog_Title"],
#                 final_item.get("Blog_Content", ""),
#                 blog_outer_paths={
#                     "jpg":  os.path.join(OUTPUT_IMG_JPG_DIR,  f"blog_outer_{safe_title}.jpg"),
#                     "webp": os.path.join(OUTPUT_IMG_WEBP_DIR, f"blog_outer_{safe_title}.webp")
#                 },
#                 blog_inner_paths={
#                     "jpg":  os.path.join(OUTPUT_IMG_JPG_DIR,  f"blog_inner_{safe_title}.jpg"),
#                     "webp": os.path.join(OUTPUT_IMG_WEBP_DIR, f"blog_inner_{safe_title}.webp")
#                 },
#                 instagram_paths={
#                     "jpg":  os.path.join(OUTPUT_IMG_JPG_DIR,  f"insta_{safe_title}.jpg"),
#                     "webp": os.path.join(OUTPUT_IMG_WEBP_DIR, f"insta_{safe_title}.webp")
#                 },
#                 quality="medium"
#             )
#             final_item["blog_image_outer"] = images["blog_outer"]
#             final_item["blog_image_inner"] = images["blog_inner"]
#             final_item["instagram_image"]  = images["instagram"]

#         else:
#             print(f"[IMAGE MODE] Template images → {OUTPUT_FILENAME}")

#             blog_jpg_path        = os.path.join(OUTPUT_IMG_JPG_DIR,  f"blog_{safe_title}.jpg")
#             blog_webp_path       = os.path.join(OUTPUT_IMG_WEBP_DIR, f"blog_{safe_title}.webp")
#             blog_inner_jpg_path  = os.path.join(OUTPUT_IMG_JPG_DIR,  f"blog_inner_{safe_title}.jpg")
#             blog_inner_webp_path = os.path.join(OUTPUT_IMG_WEBP_DIR, f"blog_inner_{safe_title}.webp")
#             insta_jpg_path       = os.path.join(OUTPUT_IMG_JPG_DIR,  f"insta_{safe_title}.jpg")
#             insta_webp_path      = os.path.join(OUTPUT_IMG_WEBP_DIR, f"insta_{safe_title}.webp")

#             article_source = final_item.get("source", "")

#             # ── BRANCH A: IPO article ─────────────────────────
#             if pop_type == "priority" and article_source == "nse_ipo":
#                 print(f"[IMAGE] IPO article (nse_ipo) → ipo_compositor.py")

#                 ipo_template = _get_ipo_template_path()

#                 if ipo_template:
#                     # Blog outer (640×480) — uses ipo_alert.png
#                     print(f"[IMAGE] Blog outer (640×480) + IPO zone values")
#                     final_item["blog_image"] = _compose_ipo_image(
#                         ipo_template, final_item,
#                         blog_jpg_path, blog_webp_path, "blog"
#                     )
#                     # Blog inner (1920×490) — uses ipo_inner.png directly
#                     ipo_inner_template = _get_ipo_inner_template_path()
#                     print(f"[IMAGE] Blog inner (1920×490) — dedicated template")
#                     final_item["blog_image_inner"] = _compose_ipo_image(
#                     ipo_inner_template, final_item,     # ← separate template
#                     blog_inner_jpg_path, blog_inner_webp_path, "blog_inner"
#                     )
#                     # Instagram (1080×1080) — uses ipo_alert.png
#                     print(f"[IMAGE] Instagram (1080×1080) + IPO zone values")
#                     final_item["instagram_image"] = _compose_ipo_image(
#                         ipo_template, final_item,
#                         insta_jpg_path, insta_webp_path, "instagram"
#                     )
#                 else:
#                     print(f"[IMAGE] IPO fallback → smart template + text overlay")
#                     ipo_text      = _extract_ipo_image_text(final_item)
#                     template_pair = _select_template_pair_smart(
#                         "priority",
#                         final_item["Blog_Title"],
#                         final_item.get("Blog_Content", "")
#                     )
#                     final_item["blog_image"] = _compose_image(
#                         template_pair["outer"], ipo_text,
#                         blog_jpg_path, blog_webp_path, "blog"
#                     )
#                     final_item["blog_image_inner"] = _compose_image(
#                         template_pair["inner"], {},
#                         blog_inner_jpg_path, blog_inner_webp_path, "blog_inner"
#                     )
#                     final_item["instagram_image"] = _compose_image(
#                         template_pair["outer"], ipo_text,
#                         insta_jpg_path, insta_webp_path, "instagram"
#                     )

#                 final_item["image_text"] = _extract_ipo_image_text(final_item)

#             # ── BRANCH B: news / corporate / non-IPO priority ─
#             else:
#                 print(f"[IMAGE] {pop_type.upper()} "
#                       f"(source={article_source}) → compositor.py")

#                 final_item["image_text"] = _extract_image_text(
#                     final_item["Blog_Title"],
#                     final_item.get("Blog_Content", ""),
#                     final_category.upper()
#                 )

#                 template_pair  = _select_template_pair_smart(
#                     final_category,
#                     final_item["Blog_Title"],
#                     final_item.get("Blog_Content", "")
#                 )
#                 outer_template = template_pair["outer"]
#                 inner_template = template_pair["inner"]

#                 print(f"[IMAGE] Blog outer → {os.path.basename(outer_template)}")
#                 final_item["blog_image"] = _compose_image(
#                     outer_template, final_item["image_text"],
#                     blog_jpg_path, blog_webp_path, "blog"
#                 )
#                 print(f"[IMAGE] Blog inner → {os.path.basename(inner_template)}")
#                 final_item["blog_image_inner"] = _compose_image(
#                     inner_template, {},
#                     blog_inner_jpg_path, blog_inner_webp_path, "blog_inner"
#                 )
#                 print(f"[IMAGE] Instagram → {os.path.basename(outer_template)}")
#                 final_item["instagram_image"] = _compose_image(
#                     outer_template, final_item["image_text"],
#                     insta_jpg_path, insta_webp_path, "instagram"
#                 )

#         # ══════════════════════════════════════════════════════
#         # STEP 8 — Save to output file
#         # ══════════════════════════════════════════════════════
#         saved = _save_output(final_item, OUTPUT_FILENAME)

#         if saved:
#             results.append(final_item)
#             print(f"[DONE] [{pop_type.upper()}] Saved → output/{OUTPUT_FILENAME}")
#             print(f"[DONE] {final_item['Blog_Title'][:60]}")
#         else:
#             print(f"[SKIPPED] Already exists: {final_item['Blog_Title'][:60]}")

#     except Exception as e:
#         print(f"[ERROR] {e}")

#     print_timing_summary()
#     return results




import os
import glob
import random
import re
import unicodedata
import json
from datetime import datetime
# Change this line
from datetime import datetime

# To this
from datetime import datetime, timezone, timedelta

# ── RSS Fetchers ──────────────────────────────────────────────
from RSS.zerodha             import fetch_zerodha
from RSS.cnbc                import fetch_cnbc
from RSS.paisa               import fetch_5paisa
from RSS.livemint            import fetch_livemint
from RSS.fetch_nse_corporate import fetch_nse_corporate
from RSS.ipo                 import fetch_nse_ipo
from RSS.google_trends import fetch_google_trends
from RSS.google_news_business import fetch_google_news_business
from RSS.economic_times import fetch_economic_times
from RSS.ndtv_profit         import fetch_ndtv_profit
from RSS.Business_Standard import fetch_business_standard

# ── Image modules ─────────────────────────────────────────────
from content_engine.image_module.text_extractor import extract_image_text
from content_engine.image_module.tempalte_selector import (
    select_template,
    select_template_pair,
    select_template_pair_smart
)
from content_engine.image_module.compositor     import compose_image
from content_engine.image_module.ipo_compositor import compose_ipo_image
from content_engine.image_module.validator      import validate_template
from content_engine.image_module.ai_image_generator import generate_ai_image

# ── Utilities & AI ────────────────────────────────────────────
from utils.combined_filter import filter_by_country_and_category
from AI_GEN.notify_generator            import generate_notification
from AI_GEN.generate_instagram_caption  import generate_instagram_caption
from AI_GEN.get_system_timestamp        import get_run_timestamp
from AI_GEN.blog_generator import generate_blog, generate_ipo_blog
from storage.save_output                import save_output
from utils.timer import timed, Timer, print_timing_summary, reset_timings
from utils.date_filter import filter_fresh_articles


# ══════════════════════════════════════════════════════════════
#  BASE DIRECTORIES
# ══════════════════════════════════════════════════════════════

BASE_DIR            = os.path.dirname(os.path.abspath(__file__))
OUTPUT_IMG_DIR      = os.path.join(BASE_DIR, "output_images")
OUTPUT_IMG_JPG_DIR  = os.path.join(BASE_DIR, "output_images", "jpg_images")
OUTPUT_IMG_WEBP_DIR = os.path.join(BASE_DIR, "output_images", "webp_images")
TIMESTAMP_FILE      = os.path.join(BASE_DIR, "output", "stack_timestamp.json")
PATTERN_INDEX_FILE  = os.path.join(BASE_DIR, "output", "pattern_index.json")

STACK_FILES = {
    "priority":  os.path.join(BASE_DIR, "output", "stack_priority.json"),
    "news":      os.path.join(BASE_DIR, "output", "stack_news.json"),
    "corporate": os.path.join(BASE_DIR, "output", "stack_corporate.json"),
}

USE_AI_IMAGES   = False
OUTPUT_FILENAME = "testing_webp_output.json" if USE_AI_IMAGES else "output.json"
print(f"[MODE] USE_AI_IMAGES={USE_AI_IMAGES} → saving to output/{OUTPUT_FILENAME}")


# ══════════════════════════════════════════════════════════════
#  POSTING PATTERN CONFIG
# ══════════════════════════════════════════════════════════════

POSTING_PATTERN = [
    "priority",
    "news",
    "priority",
    "corporate",
]


# ══════════════════════════════════════════════════════════════
#  SOURCE CONFIG
# ══════════════════════════════════════════════════════════════

PRIORITY_SOURCES  = ["nse_ipo", "google_trends"]
CORPORATE_SOURCES = []
NEWS_SOURCES      = ["zerodha", "cnbc", "5paisa", "livemint","google_news_business","economic_times","ndtv_profit","business_standard"]


# ══════════════════════════════════════════════════════════════
#  IPO TEMPLATE FINDERS
# ══════════════════════════════════════════════════════════════


def _parse_blog_output(raw: str) -> dict:
    """
    Parses blog generator output into clean dict.

    Handles 3 cases:
      Case 1: Already a dict → return as-is
      Case 2: JSON string    → parse and return
      Case 3: ```json wrapped string → strip and parse

    Always returns a dict — never a string.
    """
    # Case 1 — already parsed dict
    if isinstance(raw, dict):
        return raw

    if not isinstance(raw, str):
        print(f"[BLOG PARSE] Unexpected type: {type(raw)}")
        return {}

    # Case 2 + 3 — strip ```json wrapper if present
    text = raw.strip()

    if text.startswith("```"):
        # Remove ```json or ``` at start
        lines  = text.split("\n")
        lines  = lines[1:]  # remove first line (```json)

        # Remove ``` at end
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        text = "\n".join(lines).strip()

    # Parse JSON
    try:
        data = json.loads(text)
        print(f"[BLOG PARSE] ✅ Parsed successfully")
        return data
    except json.JSONDecodeError as e:
        print(f"[BLOG PARSE] ❌ JSON parse failed: {e}")
        print(f"[BLOG PARSE] Raw (first 200 chars): {text[:200]}")
        return {"Blog_Content": raw, "parse_error": str(e)}
    


def _get_ipo_template_path() -> str:
    """Returns IPO Alert template path (for blog outer + instagram)."""
    ipo_template = os.path.join(
        BASE_DIR, "content_engine", "templates", "ipo_alert.png"
    )
    print(f"[DEBUG] IPO template path: {ipo_template}")
    if os.path.exists(ipo_template):
        print(f"[IPO TEMPLATE] Found: {ipo_template}")
        return ipo_template
    print("[IPO TEMPLATE] File NOT found")
    return ""

def _clear_stale_stacks():
    """
    Clears all stack files if they were built on a previous date.
    Ensures stack only contains today's articles.
    Called at start of every pipeline run.
    """
    saved_ts = load_timestamp()
    if not saved_ts:
        return

    try:
        IST          = timezone(timedelta(hours=5, minutes=30))
        now_ist      = datetime.now(IST)
        saved_dt     = datetime.strptime(saved_ts, "%Y-%m-%d %H:%M:%S")
        saved_dt_ist = saved_dt.replace(tzinfo=IST)

        if saved_dt_ist.date() < now_ist.date():
            print(f"[STACK] Stale stack from {saved_dt_ist.date()} "
                  f"— today is {now_ist.date()} → clearing")

            for source_type, path in STACK_FILES.items():
                if os.path.exists(path):
                    with open(path, "w") as f:
                        json.dump([], f)
                    print(f"[STACK] Cleared: {source_type}")

            if os.path.exists(TIMESTAMP_FILE):
                os.remove(TIMESTAMP_FILE)

            print(f"[STACK] All stacks cleared ✅")

    except Exception as e:
        print(f"[STACK] Clear stale check failed: {e}")


def _get_ipo_inner_template_path() -> str:
    """
    Returns IPO Blog Inner template path (1920×490).
    This is a separate pre-made image — no resize needed.
    Falls back to ipo_alert.png if ipo_inner.png not found.
    """
    ipo_inner = os.path.join(
        BASE_DIR, "content_engine", "templates", "ipo_inner.png"
    )
    print(f"[DEBUG] IPO inner template path: {ipo_inner}")
    if os.path.exists(ipo_inner):
        print(f"[IPO INNER] Found: {ipo_inner}")
        return ipo_inner
    print("[IPO INNER] ipo_inner.png not found — using ipo_alert.png fallback")
    return _get_ipo_template_path()


# ══════════════════════════════════════════════════════════════
#  IPO IMAGE TEXT EXTRACTOR
#  Fallback when IPO template not found
# ══════════════════════════════════════════════════════════════

def _extract_ipo_image_text(article: dict) -> dict:
    company    = article.get("company", article.get("Blog_Title", ""))
    open_date  = article.get("open_date",    "")
    listing    = article.get("listing_date", "")
    price      = article.get("price_band",   "")
    lot        = article.get("lot_size",      "")
    issue_size = article.get("issue_size",   "")
    doc_type   = article.get("doc_type",     "IPO")

    company_short = company\
        .replace(" Limited", "").replace(" Ltd", "")\
        .replace(" (India)", "").strip()

    tag = "IPO"

    if open_date:
        headline = f"{company_short} IPO Opens {open_date}"
    elif doc_type == "RHP":
        headline = f"{company_short} IPO Opening Soon"
    elif doc_type == "PROSP":
        headline = f"{company_short} IPO Prospectus Filed"
    else:
        headline = f"{company_short} Files for IPO"

    words = headline.split()
    if len(words) > 6:
        headline = " ".join(words[:6])

    parts = []
    if price:
        parts.append(f"Price {price}")
    if lot:
        lot_num = lot.replace(" Shares","").replace(" shares","").strip()
        parts.append(f"Lot {lot_num}")
    if listing:
        listing_short = listing\
            .replace("Fri, ","").replace("Mon, ","").replace("Tue, ","")\
            .replace("Wed, ","").replace("Thu, ","").replace("Sat, ","")\
            .replace("Sun, ","").replace(", 2026","").replace(", 2025","")\
            .strip()
        parts.append(f"Listing {listing_short}")
    elif issue_size:
        parts.append(f"Size {issue_size[:10]}")

    subtext = " · ".join(parts) if parts else f"IPO Alert — {doc_type} Filed"
    subtext_words = subtext.split()
    if len(subtext_words) > 10:
        subtext = " ".join(subtext_words[:10])

    result = {"tag": tag, "headline": headline, "subtext": subtext}
    print(f"[IPO IMAGE TEXT] tag={result['tag']} | "
          f"headline={result['headline']} | subtext={result['subtext']}")
    return result


# ══════════════════════════════════════════════════════════════
#  SOURCE CLASSIFIER
# ══════════════════════════════════════════════════════════════

def classify_source(article: dict) -> str:
    source = article.get("source", "").lower().strip()
    if source in PRIORITY_SOURCES:
        return "priority"
    if source in CORPORATE_SOURCES:
        return "corporate"
    return "news"


# ══════════════════════════════════════════════════════════════
#  STACK HELPERS
# ══════════════════════════════════════════════════════════════

def save_stack(stack: list, source_type: str):
    path = STACK_FILES[source_type]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(stack, f, ensure_ascii=False, indent=2)
    print(f"[STACK] {source_type:<10} → {len(stack)} articles saved")


def load_stack(source_type: str) -> list:
    path = STACK_FILES[source_type]
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except:
            return []


def load_all_stacks() -> dict:
    stacks = {t: load_stack(t) for t in STACK_FILES}

    # ── Remove stale articles from loaded stacks ──────────────
    total_before = sum(len(v) for v in stacks.values())

    for source_type in stacks:
        filtered = filter_fresh_articles(stacks[source_type])
        if len(filtered) != len(stacks[source_type]):
            stacks[source_type] = filtered
            save_stack(filtered, source_type)

    total_after = sum(len(v) for v in stacks.values())
    if total_before != total_after:
        print(f"[STACK] Removed {total_before - total_after} "
              f"stale articles from loaded stacks")

    print(f"[STACK] Loaded → Priority:{len(stacks['priority'])} | "
          f"News:{len(stacks['news'])} | Corporate:{len(stacks['corporate'])}")
    return stacks


def total_stack_size(stacks: dict) -> int:
    return sum(len(v) for v in stacks.values())


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
    with open(TIMESTAMP_FILE) as f:
        try:
            return json.load(f).get("stack_built_at")
        except:
            return None


# ══════════════════════════════════════════════════════════════
#  PATTERN INDEX
# ══════════════════════════════════════════════════════════════

def load_pattern_index() -> int:
    if not os.path.exists(PATTERN_INDEX_FILE):
        return 0
    with open(PATTERN_INDEX_FILE) as f:
        try:
            return json.load(f).get("current_index", 0)
        except:
            return 0


def save_pattern_index(index: int, source_type: str):
    os.makedirs(os.path.dirname(PATTERN_INDEX_FILE), exist_ok=True)
    with open(PATTERN_INDEX_FILE, "w") as f:
        json.dump({
            "current_index": index,
            "last_type":     source_type,
            "at":            datetime.now().isoformat()
        }, f)
    print(f"[PATTERN] Saved index={index} last_type={source_type}")


# ══════════════════════════════════════════════════════════════
#  PATTERN-BASED POP DECISION
# ══════════════════════════════════════════════════════════════

def decide_pop_type(stacks: dict) -> str | None:
    has = {
        "priority":  len(stacks.get("priority",  [])) > 0,
        "news":      len(stacks.get("news",      [])) > 0,
        "corporate": len(stacks.get("corporate", [])) > 0,
    }

    print(f"[POP] Stack sizes → "
          f"Priority:{len(stacks.get('priority',[]))} | "
          f"News:{len(stacks.get('news',[]))} | "
          f"Corporate:{len(stacks.get('corporate',[]))}")

    if not any(has.values()):
        print("[POP] All stacks empty")
        return None

    current_index = load_pattern_index()
    pattern_len   = len(POSTING_PATTERN)
    print(f"[PATTERN] index={current_index} | Pattern={POSTING_PATTERN}")

    for attempt in range(pattern_len):
        idx         = (current_index + attempt) % pattern_len
        wanted_type = POSTING_PATTERN[idx]

        if has[wanted_type]:
            next_index = (idx + 1) % pattern_len
            save_pattern_index(next_index, wanted_type)
            print(f"[PATTERN] idx={idx} → {wanted_type} ✅ → next={next_index}")
            return wanted_type

        print(f"[PATTERN] idx={idx} → {wanted_type} empty, skip")

    return None


# ══════════════════════════════════════════════════════════════
#  DATE PARSER — for IPO oldest-first sorting
# ══════════════════════════════════════════════════════════════

def _parse_published_date(pub_str: str) -> datetime:
    if not pub_str:
        return datetime.min

    formats = [
        "%d-%b-%Y",
        "%d-%B-%Y",
        "%Y-%m-%d",
        "%d %b, %Y",
        "%d %B, %Y",
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y",
        "%d %b %Y",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(pub_str.strip(), fmt)
        except ValueError:
            continue

    return datetime.min


# ══════════════════════════════════════════════════════════════
#  STEP 4 — ARTICLE SELECTION FROM STACK
# ══════════════════════════════════════════════════════════════

def _pop_article_from_stack(stack: list, pop_type: str) -> tuple:
    if not stack:
        return None, stack

    ipo_articles = [a for a in stack if a.get("source") == "nse_ipo"]

    if pop_type == "priority" and ipo_articles:
        def sort_key(a):
            published   = _parse_published_date(a.get("published", ""))
            stack_index = a.get("_stack_index", 9999)
            return (published, stack_index)

        ipo_sorted = sorted(ipo_articles, key=sort_key)
        selected   = ipo_sorted[0]

        print(f"[POP] IPO → oldest-first (published + _stack_index)")
        print(f"[POP] Selected   : '{selected.get('Blog_Title','')[:50]}'")
        print(f"[POP] Published  : {selected.get('published',    'N/A')}")
        print(f"[POP] StackIndex : {selected.get('_stack_index', 'N/A')}")

        if len(ipo_articles) > 1:
            print(f"[POP] Skipped {len(ipo_articles)-1} newer IPO article(s):")
            for s in ipo_sorted[1:]:
                print(f"[POP]   · idx={s.get('_stack_index','?')} "
                      f"pub={s.get('published','N/A')} "
                      f"'{s.get('Blog_Title','')[:35]}'")
    else:
        selected = random.choice(stack)
        label = {
            "priority":  "PRIORITY (non-IPO)",
            "news":      "NEWS",
            "corporate": "CORPORATE",
        }.get(pop_type, pop_type.upper())
        print(f"[POP] Random → [{label}]")
        print(f"[POP] Selected : '{selected.get('Blog_Title','')[:50]}'")

    updated_stack = [a for a in stack if a is not selected]
    return selected, updated_stack


# ══════════════════════════════════════════════════════════════
#  FETCH ALL SOURCES
# ══════════════════════════════════════════════════════════════

def _fetch_all_sources(top_n: int = 6) -> list:
    all_data = []

    sources = [
        (fetch_nse_ipo,       "nse_ipo"),
        (fetch_google_trends,  "google_trends"),
        (fetch_google_news_business, "google_news_business"),
        (fetch_economic_times,       "economic_times"),
        (fetch_ndtv_profit,        "ndtv_profit"),
        (fetch_zerodha,       "zerodha"),
        (fetch_cnbc,          "cnbc"),
        (fetch_5paisa,        "5paisa"),
        (fetch_livemint,      "livemint"),
        (fetch_business_standard, "business_standard"),
    ]

    for fetcher, source_name in sources:
        try:
            with Timer(f"fetch_{source_name}"):
                if source_name == "nse_ipo":
                    data = fetcher()        # IPO — limited to top_n
                elif source_name == "google_trends":
                    data = fetcher()   
                elif source_name == "google_news_business":
                    data = fetcher(top_n=top_n)          # Business news — pass top_n to fetcher
                else:
                    data = fetcher()[:top_n]     # Others — limited to top_n

                for article in data:
                    article["source"] = source_name
                data = filter_fresh_articles(data)
                all_data.extend(data)
                print(f"[FETCH] {source_name:<15} → {len(data)} articles")
        except Exception as e:
            print(f"[FETCH] {source_name} failed: {e}")

    print(f"[FETCH] Total: {len(all_data)}")
    return all_data

# ══════════════════════════════════════════════════════════════
#  BUILD STACKS
# ══════════════════════════════════════════════════════════════

def _build_stacks_from_articles(articles: list) -> dict:
    seen_titles     = set()
    unique_articles = []

    for article in articles:
        norm = normalize_title(article.get("Blog_Title", ""))
        if norm not in seen_titles:
            seen_titles.add(norm)
            unique_articles.append(article)
        else:
            print(f"[DEDUP] Removed: {article['Blog_Title'][:50]}")

    print(f"[DEDUP] {len(articles)} → {len(unique_articles)} after stack dedup")

    used_titles = load_used_titles()
    fresh = [
        item for item in unique_articles
        if normalize_title(item.get("Blog_Title", "")) not in used_titles
    ]
    removed = len(unique_articles) - len(fresh)
    if removed:
        print(f"[DEDUP] Removed {removed} already published")
    print(f"[DEDUP] {len(unique_articles)} → {len(fresh)} fresh remain")

    buckets     = {"priority": [], "news": [], "corporate": []}
    ipo_counter = 0

    for article in fresh:
        st = classify_source(article)
        article["_source_type"] = st

        if article.get("source") == "nse_ipo":
            article["_stack_index"] = ipo_counter
            ipo_counter += 1
            print(f"[STACK IDX] IPO #{article['_stack_index']} → "
                  f"'{article.get('Blog_Title','')[:45]}'")

        buckets[st].append(article)

    print(f"\n[STACK BUILD] Priority:{len(buckets['priority'])} | "
          f"News:{len(buckets['news'])} | Corporate:{len(buckets['corporate'])}")

    for st, stack in buckets.items():
        save_stack(stack, st)

    save_timestamp()
    return buckets


# ══════════════════════════════════════════════════════════════
#  FULL FETCH + FETCH AFTER TIMESTAMP
# ══════════════════════════════════════════════════════════════

def _full_fetch_and_build_stack(selected_country: str, category: str) -> dict:
    print("\n" + "="*50)
    print("  PHASE 1 — BUILDING FRESH STACK")
    print("="*50)

    all_data = _fetch_all_sources(top_n=6)

    # ipo_articles   = [a for a in all_data if a.get("source") == "nse_ipo"]
    # other_articles = [a for a in all_data if a.get("source") != "nse_ipo"]
    ipo_articles = [
    a for a in all_data
    if a.get("source") == "nse_ipo"
    ]

    google_trends_articles = [
    a for a in all_data
    if a.get("source") == "google_trends"
    ]
    print(
    f"[DEBUG] Finance Google Trends: "
    f"{len(google_trends_articles)}"
    )

    other_articles = [
    a for a in all_data
    if a.get("source") not in ["nse_ipo", "google_trends"]
    ]
    finance_trends, _ = filter_by_country_and_category(
    google_trends_articles,
    selected_country,
    category
    )

    if not finance_trends:
        print(f"[FILTER] No finance trends found in Google Trends today")

    print(f"[FILTER] IPO articles (bypass filter): {len(ipo_articles)}")

    filtered_other, source = filter_by_country_and_category(
        other_articles, selected_country, category
    )
    print(f"[FILTER] Other articles after filter: {len(filtered_other)}")

    filtered_data = (
    ipo_articles +
    finance_trends +
    filtered_other
    )
    print(f"[FILTER] Total combined: {len(filtered_data)}")

    if not filtered_data:
        print("[STACK] No articles after filter!")
        return {"priority": [], "news": [], "corporate": []}

    stacks = _build_stacks_from_articles(filtered_data)
    print("="*50 + "\n")
    return stacks


def _fetch_after_timestamp(
    selected_country: str,
    category: str,
    saved_ts: str
) -> dict:
    print(f"\n[STACK EMPTY] Fetching after: {saved_ts}")

    all_data = _fetch_all_sources(top_n=6)

    # ── Split into 3 groups ───────────────────────────────────
    ipo_articles = [
        a for a in all_data
        if a.get("source") == "nse_ipo"
    ]

    google_trends_articles = [
        a for a in all_data
        if a.get("source") == "google_trends"
    ]

    other_articles = [
        a for a in all_data
        if a.get("source") not in ["nse_ipo", "google_trends"]
    ]

    print(f"[FILTER] IPO articles (bypass filter)    : {len(ipo_articles)}")
    print(f"[FILTER] Google Trends articles           : {len(google_trends_articles)}")
    print(f"[FILTER] Other articles (to filter)      : {len(other_articles)}")

    # ── Filter google_trends separately ──────────────────────
    # Google Trends is already India-specific (geo=IN)
    # but we still filter for finance category only
    finance_trends, _ = filter_by_country_and_category(
        google_trends_articles, selected_country, category
    )

    if not finance_trends:
        print(f"[FILTER] No finance trends found in Google Trends today")
    print(f"[FILTER] Google Trends after filter      : {len(finance_trends)}")

    # ── Filter other sources normally ────────────────────────
    filtered_other, source = filter_by_country_and_category(
        other_articles, selected_country, category
    )
    print(f"[FILTER] Other articles after filter     : {len(filtered_other)}")

    # ── Combine all 3 groups ──────────────────────────────────
    filtered_data = ipo_articles + finance_trends + filtered_other
    print(f"[FILTER] Total combined                  : {len(filtered_data)}")

    if not filtered_data:
        print("[STACK] No new articles yet — retrying next cycle")
        return {"priority": [], "news": [], "corporate": []}

    return _build_stacks_from_articles(filtered_data)


# ══════════════════════════════════════════════════════════════
#  UTILITY
# ══════════════════════════════════════════════════════════════

def normalize_title(title: str) -> str:
    return re.sub(r'\s+', ' ', title.strip().lower())


def clean_newlines(text):
    if not isinstance(text, str):
        return text
    return text.replace('\\n\\n', '').replace('\\n', '')


def clean_filename(text: str) -> str:
    ascii_text = unicodedata.normalize("NFKD", text)\
                             .encode("ascii", "ignore")\
                             .decode()
    ascii_text = re.sub(r'[\\/*?:"<>|]', '', ascii_text)
    ascii_text = ascii_text.replace(" ", "_")
    ascii_text = re.sub(r'_+', '_', ascii_text).strip("_")

    # Fallback for regional language titles
    # that become empty after ASCII stripping
    if len(ascii_text) < 3:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        print(f"[FILENAME] Regional title → using timestamp: {timestamp}")
        return timestamp

    return ascii_text[:60]


def load_used_titles() -> set:
    filepath = f"output/{OUTPUT_FILENAME}"
    if not os.path.exists(filepath):
        return set()
    with open(filepath, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
            return {normalize_title(item.get("Blog_Title", "")) for item in data}
        except:
            return set()


# ══════════════════════════════════════════════════════════════
#  TIMED WRAPPERS
# ══════════════════════════════════════════════════════════════

@timed
def _generate_blog(item):
    return generate_blog(item)

@timed
def _generate_ipo_blog(item):          # ← add this
    return generate_ipo_blog(item)

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
    return select_template_pair_smart(category, title, content)

@timed
def _compose_image(template, image_text, jpg_path, webp_path, image_type):
    return compose_image(
        template, image_text, jpg_path, webp_path,
        image_type=image_type
    )

@timed
def _compose_ipo_image(template, article, jpg_path, webp_path, image_type):
    return compose_ipo_image(
        template, article, jpg_path, webp_path,
        image_type=image_type
    )

@timed
def _generate_ai_image(
    blog_title, blog_content,
    blog_outer_paths, blog_inner_paths,
    instagram_paths, quality="medium"
):
    return generate_ai_image(
        blog_title, blog_content,
        blog_outer_paths, blog_inner_paths,
        instagram_paths, quality
    )

@timed
def _save_output(item, filename):
    return save_output(item, filename=filename)


# ══════════════════════════════════════════════════════════════
#  MAIN PIPELINE
# ══════════════════════════════════════════════════════════════

def run_pipeline(selected_country="India", category="finance"):

    reset_timings()
    os.makedirs(OUTPUT_IMG_DIR,      exist_ok=True)
    os.makedirs(OUTPUT_IMG_JPG_DIR,  exist_ok=True)
    os.makedirs(OUTPUT_IMG_WEBP_DIR, exist_ok=True)
    results = []

    # ── Clear stale stacks from previous day ──────────────────
    _clear_stale_stacks()

    # ══════════════════════════════════════════════════════════
    # STEP 1 — Load all 3 stacks from disk
    # ══════════════════════════════════════════════════════════
    stacks = load_all_stacks()

    # ══════════════════════════════════════════════════════════
    # STEP 2 — Rebuild stacks if all empty
    # ══════════════════════════════════════════════════════════
    if total_stack_size(stacks) == 0:
        saved_ts = load_timestamp()

        if saved_ts is None:
            print("[STACK] First run — full fetch...")
            stacks = _full_fetch_and_build_stack(selected_country, category)
        else:
            print(f"[STACK] All empty — fetching after: {saved_ts}")
            stacks = _fetch_after_timestamp(selected_country, category, saved_ts)

        if total_stack_size(stacks) == 0:
            print("[WAITING] No new articles — fallback Zerodha...")

            zerodha_data = fetch_zerodha()
            if not zerodha_data:
                print("[FALLBACK] Zerodha also empty — aborting")
                return []

            used_titles   = load_used_titles()
            fresh_zerodha = [
                a for a in zerodha_data
                if normalize_title(a.get("Blog_Title", "")) not in used_titles
            ]
            if not fresh_zerodha:
                print("[FALLBACK] All Zerodha articles already published — aborting")
                return []
            print(
                f"[FALLBACK] {len(zerodha_data)} fetched → "
                f"{len(fresh_zerodha)} fresh after dedup"
            )

            final_item                 = random.choice(fresh_zerodha)
            final_item["source"]       = "zerodha"
            final_item["_source_type"] = "news"
            final_item["source_type"]  = "news"
            print(f"[FALLBACK] Selected: '{final_item.get('Blog_Title','')[:50]}'")

            # Fallback always uses standard blog generator (zerodha = news)
            print(f"[BLOG] FALLBACK news article → generate_blog")
            final_item["blog"]             = clean_newlines(generate_blog(final_item))
            final_item["notify"]           = clean_newlines(generate_notification(final_item))
            final_item["instagram_notify"] = clean_newlines(generate_instagram_caption(final_item))
            final_item["Run_Timestamp"]    = get_run_timestamp()
            final_item["blog"]             = _parse_blog_output(final_item["blog"])

            safe_title = clean_filename(final_item["Blog_Title"])
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

    # ══════════════════════════════════════════════════════════
    # STEP 3 — Decide which stack to pop (pattern-based)
    # ══════════════════════════════════════════════════════════
    pop_type = decide_pop_type(stacks)

    if pop_type is None:
        print("[STACK] All stacks empty — nothing to process")
        return []

    # ══════════════════════════════════════════════════════════
    # STEP 4 — Select article from chosen stack
    # ══════════════════════════════════════════════════════════
    chosen_stack          = stacks[pop_type]
    final_item, new_stack = _pop_article_from_stack(chosen_stack, pop_type)

    stacks[pop_type] = new_stack
    save_stack(new_stack, pop_type)

    print(f"\n[POPPED]  [{pop_type.upper()}] "
          f"{final_item.get('Blog_Title', '')[:60]}")
    print(f"[STACK]   Priority:{len(stacks['priority'])} | "
          f"News:{len(stacks['news'])} | "
          f"Corporate:{len(stacks['corporate'])}")

    final_category = category

    # ══════════════════════════════════════════════════════════
    # STEP 5 — Duplicate check (safety net)
    # ══════════════════════════════════════════════════════════
    used_titles = load_used_titles()
    if normalize_title(final_item.get("Blog_Title", "")) in used_titles:
        print("[SKIPPED] Already published — next cycle will retry")
        return []

    print(f"[SELECTED] [{pop_type.upper()}] "
          f"{final_item.get('Blog_Title', '')[:50]}")

    try:
        # ══════════════════════════════════════════════════════
        # STEP 6 — Generate blog + notification + instagram (AI)
        #
        # BLOG GENERATOR ROUTING:
        #   IPO  (priority + nse_ipo)    → generate_ipo_blog
        #   NEWS (news sources)          → generate_blog
        #   CORPORATE (nse_corporate)    → generate_blog
        #   PRIORITY non-IPO             → generate_blog
        #                                  (e.g. google_trends)
        #
        # WHY double condition for IPO:
        #   PRIORITY_SOURCES contains both nse_ipo and google_trends.
        #   google_trends priority articles must use generate_blog,
        #   not the IPO prompt. Only nse_ipo gets generate_ipo_blog.
        # ══════════════════════════════════════════════════════
        final_item["_source_type"] = pop_type
        article_source             = final_item.get("source", "")

        if pop_type == "priority" and article_source == "nse_ipo":
            print(f"[BLOG] IPO article (priority + nse_ipo) → generate_ipo_blog")
            final_item["blog"] = clean_newlines(_generate_ipo_blog(final_item))
        else:
            print(f"[BLOG] {pop_type.upper()} article "
                  f"(source={article_source}) → generate_blog")
            final_item["blog"] = clean_newlines(_generate_blog(final_item))

        final_item["notify"]           = clean_newlines(_generate_notification(final_item))
        final_item["instagram_notify"] = clean_newlines(_generate_instagram(final_item))
        final_item["Run_Timestamp"]    = get_run_timestamp()
        final_item["source_type"]      = pop_type
        final_item["blog"]             = _parse_blog_output(final_item["blog"])

        safe_title = clean_filename(final_item["Blog_Title"])

        # File paths — shared by all image branches
        blog_jpg_path        = os.path.join(OUTPUT_IMG_JPG_DIR,  f"blog_{safe_title}.jpg")
        blog_webp_path       = os.path.join(OUTPUT_IMG_WEBP_DIR, f"blog_{safe_title}.webp")
        blog_inner_jpg_path  = os.path.join(OUTPUT_IMG_JPG_DIR,  f"blog_inner_{safe_title}.jpg")
        blog_inner_webp_path = os.path.join(OUTPUT_IMG_WEBP_DIR, f"blog_inner_{safe_title}.webp")
        insta_jpg_path       = os.path.join(OUTPUT_IMG_JPG_DIR,  f"insta_{safe_title}.jpg")
        insta_webp_path      = os.path.join(OUTPUT_IMG_WEBP_DIR, f"insta_{safe_title}.webp")

        # ══════════════════════════════════════════════════════
        # STEP 7 — Generate images
        #
        # ORDER OF CHECKS (critical):
        #   1st: IPO article? → ALWAYS ipo_compositor (ignores USE_AI_IMAGES)
        #   2nd: USE_AI_IMAGES? → AI generation for non-IPO
        #   3rd: else → template compositor for non-IPO
        #
        # WHY IPO IS FIRST:
        #   USE_AI_IMAGES=True was causing IPO articles to use
        #   OpenAI image generation instead of the IPO Alert template.
        #   IPO articles MUST always use ipo_compositor regardless
        #   of the USE_AI_IMAGES flag.
        # ══════════════════════════════════════════════════════

        # ── BRANCH A: IPO article — ALWAYS template ───────────
        if pop_type == "priority" and article_source == "nse_ipo":
            print(f"[IMAGE] IPO article → ipo_compositor.py "
                  f"(always template, ignores USE_AI_IMAGES)")

            ipo_template       = _get_ipo_template_path()
            ipo_inner_template = _get_ipo_inner_template_path()

            if ipo_template:
                print(f"[IMAGE] Blog outer  (640×480)   + IPO zone values")
                final_item["blog_image"] = _compose_ipo_image(
                    ipo_template, final_item,
                    blog_jpg_path, blog_webp_path, "blog"
                )

                print(f"[IMAGE] Blog inner  (1920×490)  — dedicated template")
                final_item["blog_image_inner"] = _compose_ipo_image(
                    ipo_inner_template, final_item,
                    blog_inner_jpg_path, blog_inner_webp_path, "blog_inner"
                )

                print(f"[IMAGE] Instagram   (1080×1080) + IPO zone values")
                final_item["instagram_image"] = _compose_ipo_image(
                    ipo_template, final_item,
                    insta_jpg_path, insta_webp_path, "instagram"
                )
            else:
                # Fallback: ipo_alert.png missing
                print(f"[IMAGE] IPO fallback → smart template + text overlay")
                ipo_text      = _extract_ipo_image_text(final_item)
                template_pair = _select_template_pair_smart(
                    "priority",
                    final_item["Blog_Title"],
                    final_item.get("Blog_Content", "")
                )
                final_item["blog_image"] = _compose_image(
                    template_pair["outer"], ipo_text,
                    blog_jpg_path, blog_webp_path, "blog"
                )
                final_item["blog_image_inner"] = _compose_image(
                    template_pair["inner"], {},
                    blog_inner_jpg_path, blog_inner_webp_path, "blog_inner"
                )
                final_item["instagram_image"] = _compose_image(
                    template_pair["outer"], ipo_text,
                    insta_jpg_path, insta_webp_path, "instagram"
                )

            final_item["image_text"] = _extract_ipo_image_text(final_item)

        # ── BRANCH B: non-IPO + USE_AI_IMAGES=True ───────────
        elif USE_AI_IMAGES:
            print(f"[IMAGE MODE] AI images → {OUTPUT_FILENAME}")
            images = _generate_ai_image(
                final_item["Blog_Title"],
                final_item.get("Blog_Content", ""),
                blog_outer_paths={
                    "jpg":  os.path.join(OUTPUT_IMG_JPG_DIR,  f"blog_outer_{safe_title}.jpg"),
                    "webp": os.path.join(OUTPUT_IMG_WEBP_DIR, f"blog_outer_{safe_title}.webp"),
                },
                blog_inner_paths={
                    "jpg":  os.path.join(OUTPUT_IMG_JPG_DIR,  f"blog_inner_{safe_title}.jpg"),
                    "webp": os.path.join(OUTPUT_IMG_WEBP_DIR, f"blog_inner_{safe_title}.webp"),
                },
                instagram_paths={
                    "jpg":  os.path.join(OUTPUT_IMG_JPG_DIR,  f"insta_{safe_title}.jpg"),
                    "webp": os.path.join(OUTPUT_IMG_WEBP_DIR, f"insta_{safe_title}.webp"),
                },
                quality="medium"
            )
            final_item["blog_image_outer"] = images["blog_outer"]
            final_item["blog_image_inner"] = images["blog_inner"]
            final_item["instagram_image"]  = images["instagram"]

        # ── BRANCH C: non-IPO + USE_AI_IMAGES=False ──────────
        else:
            print(f"[IMAGE] {pop_type.upper()} "
                  f"(source={article_source}) → compositor.py")

            final_item["image_text"] = _extract_image_text(
                final_item["Blog_Title"],
                final_item.get("Blog_Content", ""),
                final_category.upper()
            )

            template_pair  = _select_template_pair_smart(
                final_category,
                final_item["Blog_Title"],
                final_item.get("Blog_Content", "")
            )
            outer_template = template_pair["outer"]
            inner_template = template_pair["inner"]

            print(f"[IMAGE] Blog outer  → {os.path.basename(outer_template)}")
            final_item["blog_image"] = _compose_image(
                outer_template, final_item["image_text"],
                blog_jpg_path, blog_webp_path, "blog"
            )
            print(f"[IMAGE] Blog inner  → {os.path.basename(inner_template)}")
            final_item["blog_image_inner"] = _compose_image(
                inner_template, {},
                blog_inner_jpg_path, blog_inner_webp_path, "blog_inner"
            )
            print(f"[IMAGE] Instagram   → {os.path.basename(outer_template)}")
            final_item["instagram_image"] = _compose_image(
                outer_template, final_item["image_text"],
                insta_jpg_path, insta_webp_path, "instagram"
            )

        # ══════════════════════════════════════════════════════
        # STEP 8 — Save to output file
        # ══════════════════════════════════════════════════════
        saved = _save_output(final_item, OUTPUT_FILENAME)

        if saved:
            results.append(final_item)
            print(f"[DONE] [{pop_type.upper()}] Saved → output/{OUTPUT_FILENAME}")
            print(f"[DONE] {final_item['Blog_Title'][:60]}")
        else:
            print(f"[SKIPPED] Already exists: {final_item['Blog_Title'][:60]}")

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
# from content_engine.image_module.tempalte_selector import (
#     select_template,
#     select_template_pair,
#     select_template_pair_smart        # ← added
# )
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
# USE_AI_IMAGES   = False
# OUTPUT_FILENAME = "testing_webp_output.json" if USE_AI_IMAGES else "output.json"

# print(f"[MODE] USE_AI_IMAGES={USE_AI_IMAGES} → saving to output/{OUTPUT_FILENAME}")

# def clean_newlines(text):
#     if not isinstance(text, str):
#         return text
#     return text.replace('\\n\\n', '').replace('\\n', '')
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
# def _select_template_pair_smart(category, title, content=""):
#     # ── Smart selection using descriptions + OpenAI ───────────
#     # Falls back to MD5 if descriptions missing or API fails
#     return select_template_pair_smart(category, title, content)

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
#         # ── Fallback Zerodha ──────────────────────────────────
#         if not stack:
#             print("[WAITING] Koi naya article nahi mila — fallback Zerodha...")

#             zerodha_data = fetch_zerodha()
#             if not zerodha_data:
#                 return []

#             final_item = random.choice(zerodha_data)

#             final_item["blog"]             = clean_newlines(generate_blog(final_item))
#             final_item["notify"]           = clean_newlines(generate_notification(final_item))
#             final_item["instagram_notify"] = clean_newlines(generate_instagram_caption(final_item))
#             final_item["Run_Timestamp"]    = get_run_timestamp()

#             safe_title = clean_filename(final_item["Blog_Title"])

#             if USE_AI_IMAGES:
#                 # ── AI Image Generation ───────────────────────
#                 blog_outer_jpg  = os.path.join(OUTPUT_IMG_JPG_DIR,  f"blog_outer_{safe_title}.jpg")
#                 blog_outer_webp = os.path.join(OUTPUT_IMG_WEBP_DIR, f"blog_outer_{safe_title}.webp")
#                 blog_inner_jpg  = os.path.join(OUTPUT_IMG_JPG_DIR,  f"blog_inner_{safe_title}.jpg")
#                 blog_inner_webp = os.path.join(OUTPUT_IMG_WEBP_DIR, f"blog_inner_{safe_title}.webp")
#                 insta_jpg       = os.path.join(OUTPUT_IMG_JPG_DIR,  f"insta_{safe_title}.jpg")
#                 insta_webp      = os.path.join(OUTPUT_IMG_WEBP_DIR, f"insta_{safe_title}.webp")

#                 images = generate_ai_image(
#                     final_item["Blog_Title"],
#                     final_item.get("Blog_Content", ""),
#                     blog_outer_paths = {"jpg": blog_outer_jpg,  "webp": blog_outer_webp},
#                     blog_inner_paths = {"jpg": blog_inner_jpg,  "webp": blog_inner_webp},
#                     instagram_paths  = {"jpg": insta_jpg,       "webp": insta_webp},
#                     quality          = "medium"
#                 )
#                 final_item["blog_image_outer"] = images["blog_outer"]
#                 final_item["blog_image_inner"] = images["blog_inner"]
#                 final_item["instagram_image"]  = images["instagram"]

#             else:
#                 # ── Template Image Generation ─────────────────
#                 image_text = extract_image_text(
#                     final_item["Blog_Title"],
#                     final_item.get("Blog_Content", ""),
#                     category.upper()
#                 )
#                 final_item["image_text"] = image_text

#                 template_pair  = select_template_pair_smart(
#                     category,
#                     final_item["Blog_Title"],
#                     final_item.get("Blog_Content", "")
#                 )
#                 outer_template = template_pair["outer"]
#                 inner_template = template_pair["inner"]

#                 final_item["blog_image"] = compose_image(
#                     outer_template, image_text,
#                     os.path.join(OUTPUT_IMG_JPG_DIR,  f"blog_{safe_title}.jpg"),
#                     os.path.join(OUTPUT_IMG_WEBP_DIR, f"blog_{safe_title}.webp"),
#                     image_type="blog"
#                 )
#                 final_item["blog_image_inner"] = compose_image(
#                     inner_template, {},
#                     os.path.join(OUTPUT_IMG_JPG_DIR,  f"blog_inner_{safe_title}.jpg"),
#                     os.path.join(OUTPUT_IMG_WEBP_DIR, f"blog_inner_{safe_title}.webp"),
#                     image_type="blog_inner"
#                 )
#                 final_item["instagram_image"] = compose_image(
#                     outer_template, image_text,
#                     os.path.join(OUTPUT_IMG_JPG_DIR,  f"insta_{safe_title}.jpg"),
#                     os.path.join(OUTPUT_IMG_WEBP_DIR, f"insta_{safe_title}.webp"),
#                     image_type="instagram"
#                 )

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
#         final_item["blog"]             = clean_newlines(_generate_blog(final_item))
#         final_item["notify"]           = clean_newlines(_generate_notification(final_item))
#         final_item["instagram_notify"] = clean_newlines(_generate_instagram(final_item))

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

#             # ── Smart template selection ──────────────────────
#             # Reads image_descriptions.json → OpenAI picks best match
#             # Falls back to MD5 if file missing or API fails
#             template_pair  = _select_template_pair_smart(
#                 final_category,
#                 final_item["Blog_Title"],
#                 final_item.get("Blog_Content", "") # ← pass content
                
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



















