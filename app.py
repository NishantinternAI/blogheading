# import streamlit as st
# from bs4 import BeautifulSoup
# import os
# from urllib.parse import urlparse
# import json

# st.set_page_config(layout="wide", page_title="Swastika Blog Dashboard")

# DEFAULT_COUNTRY  = "India"
# DEFAULT_CATEGORY = "finance"


# def copy_row(label: str, text: str, key: str = ""):
#     st.markdown(f"**{label}**")
#     st.text_area(
#         label            = label,
#         value            = text,
#         height           = min(150, 35 + text.count('\n') * 20),
#         key              = key,
#         label_visibility = "collapsed"
#     )


# def download_image_btn(image_path: str, filename: str, label: str = "Download", unique_key: str = ""):
#     if image_path and os.path.exists(image_path):
#         ext  = os.path.splitext(filename)[1].lower()
#         mime = "image/webp" if ext == ".webp" else "image/jpeg"
#         with open(image_path, "rb") as f:
#             img_bytes = f.read()
#         st.download_button(
#             label     = label,
#             data      = img_bytes,
#             file_name = filename,
#             mime      = mime,
#             key       = f"dl_{unique_key}_{filename}"
#         )
#     else:
#         st.caption("Image not available for download.")


# def get_image_path(image_field, prefer: str = "webp") -> str:
#     if isinstance(image_field, dict):
#         if prefer == "webp" and image_field.get("webp"):
#             return image_field["webp"]
#         return image_field.get("jpg", "")
#     return image_field or ""


# def render_blog_in_box(html_content: str):
#     st.markdown(
#         f"""
#         <div style="
#             height: 400px;
#             overflow-y: auto;
#             border: 1px solid #e0e0e0;
#             border-radius: 8px;
#             padding: 16px 20px;
#             background-color: #fafafa;
#             font-size: 15px;
#             line-height: 1.8;
#             color: #333;
#         ">{html_content}</div>
#         """,
#         unsafe_allow_html=True
#     )


# def show_image_section(label: str, image_field, display_width: int, idx: int, key_prefix: str):
#     st.markdown(f"**{label}**")
#     webp_path = get_image_path(image_field, prefer="webp")
#     jpg_path  = get_image_path(image_field, prefer="jpg")

#     if webp_path and os.path.exists(webp_path):
#         st.image(webp_path, width=display_width)
#         col1, col2 = st.columns(2)
#         with col1:
#             download_image_btn(
#                 webp_path,
#                 os.path.basename(webp_path),
#                 "⬇ Download WebP",
#                 unique_key=f"{key_prefix}_webp_{idx}"
#             )
#         with col2:
#             download_image_btn(
#                 jpg_path,
#                 os.path.basename(jpg_path),
#                 "⬇ Download JPG",
#                 unique_key=f"{key_prefix}_jpg_{idx}"
#             )
#     elif jpg_path and os.path.exists(jpg_path):
#         st.image(jpg_path, width=display_width)
#         download_image_btn(
#             jpg_path,
#             os.path.basename(jpg_path),
#             "⬇ Download JPG",
#             unique_key=f"{key_prefix}_jpg_only_{idx}"
#         )
#     else:
#         st.warning(f"{label} not available.")


# st.title("Blog Dashboard")
# st.caption(f"Country: {DEFAULT_COUNTRY}  ·  Category: {DEFAULT_CATEGORY.capitalize()}")

# USE_AI_IMAGES   = False
# OUTPUT_FILENAME = "testing_webp_output.json" if USE_AI_IMAGES else "output.json"
# @st.cache_data(show_spinner="Loading blogs...", ttl=60)
# def load_data():
#     path = f"output/{OUTPUT_FILENAME}"
#     if not os.path.exists(path):
#         return []
#     with open(path, "r", encoding="utf-8") as f:
#         try:
#             return json.load(f)
#         except:
#             return []


# output  = load_data()
# results = output.get("results", []) if isinstance(output, dict) else output

# if st.button("Refresh data"):
#     st.cache_data.clear()
#     st.rerun()

# for key in ["selected_blog", "selected_insta", "page"]:
#     if key not in st.session_state:
#         st.session_state[key] = None if key != "page" else 1

# if not results:
#     st.warning("No blogs returned.")
#     st.stop()

# m1, m2, m3, m4 = st.columns(4)
# m1.metric("Total blogs",  len(results))
# m2.metric("Country",      DEFAULT_COUNTRY)
# m3.metric("Category",     DEFAULT_CATEGORY.capitalize())
# m4.metric("Sources", len(set(
#     urlparse(r.get("Blog_Link") or r.get("Blog_Links", "")).netloc
#     for r in results
# )))

# st.divider()

# sc, ss = st.columns([4, 1])
# search = sc.text_input("Search", placeholder="Search title or content...", label_visibility="collapsed")
# sort   = ss.selectbox("Sort", ["Newest first", "Oldest first", "A to Z"], label_visibility="collapsed")

# filtered = results
# if search:
#     q = search.lower()
#     filtered = [
#         r for r in results
#         if q in r.get("Blog_Title", "").lower()
#         or q in r.get("blog", {}).get("Blog_Title", "").lower()
#         or q in r.get("Blog_Content", "").lower()
#     ]
#     st.session_state.page = 1

# if sort == "Newest first":
#     filtered = sorted(filtered, key=lambda x: x.get("Publish_Date") or x.get("Blog_PublishDate") or x.get("Run_Timestamp", ""), reverse=True)
# elif sort == "Oldest first":
#     filtered = sorted(filtered, key=lambda x: x.get("Publish_Date") or x.get("Blog_PublishDate") or x.get("Run_Timestamp", ""))
# else:
#     filtered = sorted(filtered, key=lambda x: x.get("blog", {}).get("Blog_Title", "") or x.get("Blog_Title", ""))

# if not filtered:
#     st.info("No blogs match your search.")
#     st.stop()

# # ── Pagination ────────────────────────────────────────────────
# PAGE_SIZE = 20
# total     = len(filtered)
# max_page  = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)

# if st.session_state.page > max_page:
#     st.session_state.page = 1

# p1, p2, p3 = st.columns([1, 2, 1])
# with p1:
#     if st.button("← Prev") and st.session_state.page > 1:
#         st.session_state.page -= 1
#         st.rerun()
# with p2:
#     st.caption(f"Page {st.session_state.page} of {max_page}  ·  {total} blogs")
# with p3:
#     if st.button("Next →") and st.session_state.page < max_page:
#         st.session_state.page += 1
#         st.rerun()

# start      = (st.session_state.page - 1) * PAGE_SIZE
# end        = start + PAGE_SIZE
# page_items = filtered[start:end]

# # ── Header ───────────────────────────────────────────────────
# h1, h2, h3, h4, h5, h6 = st.columns([2, 4, 1, 1.5, 1.5, 2])
# h1.caption("Publish date")
# h2.caption("Blog title")
# h3.caption("Blog")
# h4.caption("Instagram")
# h5.caption("Tag")
# h6.caption("Source")
# st.divider()

# # ── Scrollable blog list ──────────────────────────────────────
# with st.container(height=500):
#     for i, item in enumerate(page_items):
#         real_idx = results.index(item)
#         publish  = item.get("Publish_Date") or item.get("Blog_PublishDate") or item.get("Run_Timestamp", "—")
#         title    = item.get("blog", {}).get("Blog_Title", "") or item.get("Blog_Title", "—")
#         tag      = item.get("image_text", {}).get("tag", "GENERAL")
#         link     = item.get("Blog_Link") or item.get("Blog_Links", "—")

#         try:
#             domain = urlparse(link).netloc.replace("www.", "")
#         except:
#             domain = link[:30] if link else "—"

#         c1, c2, c3, c4, c5, c6 = st.columns([2, 4, 1, 1.5, 1.5, 2])
#         c1.caption(publish[:16] if publish else "—")
#         c2.write(f"**{title[:80]}**" if len(title) > 80 else f"**{title}**")

#         if c3.button("Read", key=f"blog_{real_idx}"):
#             st.session_state.selected_blog  = real_idx
#             st.session_state.selected_insta = None

#         if c4.button("📸 Insta", key=f"insta_{real_idx}"):
#             st.session_state.selected_insta = real_idx
#             st.session_state.selected_blog  = None

#         c5.write(f"`{tag}`")
#         c6.markdown(f"[{domain}]({link})")
#         st.divider()


# # ── Blog Detail ───────────────────────────────────────────────
# if st.session_state.selected_blog is not None:
#     idx  = st.session_state.selected_blog
#     item = results[idx]
#     blog = item.get("blog", {})

#     st.subheader("Blog detail")
#     m1, m2, m3 = st.columns(3)
#     m1.markdown(f"**Tag:** `{item.get('image_text', {}).get('tag', 'GENERAL')}`")
#     m2.markdown(f"**Country:** `{DEFAULT_COUNTRY}`")
#     m3.markdown(f"**Generated:** `{item.get('Run_Timestamp', '—')}`")

#     link = item.get("Blog_Link") or item.get("Blog_Links", "")
#     if link:
#         st.markdown(f"[Read original source ↗]({link})")
#     st.divider()

#     ai_title = blog.get("Blog_Title", "") or item.get("Blog_Title", "")
#     copy_row("Blog title", ai_title, key=f"cp_title_{idx}")
#     st.divider()

#     meta_title = blog.get("Meta_Title", "")
#     meta_desc  = blog.get("Meta_Description", "")

#     if meta_title or meta_desc:
#         with st.expander("SEO fields — Meta Title & Meta Description"):
#             if meta_title:
#                 char_count = len(meta_title)
#                 color = "green" if char_count <= 60 else "red"
#                 st.markdown(
#                     f"**Meta Title** &nbsp; <span style='color:{color};font-size:12px'>{char_count}/60 chars</span>",
#                     unsafe_allow_html=True
#                 )
#                 st.code(meta_title, language=None)
#             if meta_desc:
#                 char_count = len(meta_desc)
#                 color = "green" if char_count <= 160 else "red"
#                 st.markdown(
#                     f"**Meta Description** &nbsp; <span style='color:{color};font-size:12px'>{char_count}/160 chars</span>",
#                     unsafe_allow_html=True
#                 )
#                 st.code(meta_desc, language=None)
#     st.divider()

#     tldr = blog.get("TLDR", [])
#     if tldr:
#         copy_row("Key takeaways", "\n".join(f"• {t}" for t in tldr), key=f"cp_tldr_{idx}")
#     st.divider()

#     blog_html     = blog.get("Blog_Content", "")
#     plain_content = BeautifulSoup(blog_html, "html.parser").get_text(separator="\n", strip=True) if blog_html else ""

#     st.markdown("**Blog content**")
#     if blog_html:
#         render_blog_in_box(blog_html)
#         st.divider()
#         st.markdown("**Copy full blog content**")
#         st.text_area(
#             label            = "Copy full blog content",
#             value            = blog_html,
#             height           = 150,
#             key              = f"cp_fullcontent_{idx}",
#             label_visibility = "collapsed"
#         )
#     else:
#         st.info("No blog content available.")
#     st.divider()

#     conclusion = blog.get("Conclusion", "")
#     if conclusion:
#         copy_row("Conclusion", conclusion, key=f"cp_conclusion_{idx}")
#         st.divider()

#     internal_links = blog.get("Internal_Links", [])
#     if internal_links:
#         st.markdown("**Internal Links**")
#         for lnk in internal_links:
#             anchor    = lnk.get("anchor_text", "")
#             url       = lnk.get("url", "")
#             placement = lnk.get("placement", "")
#             st.markdown(
#                 f"- [{anchor}]({url})"
#                 + (f" &nbsp; <span style='color:#999;font-size:12px'>({placement})</span>" if placement else ""),
#                 unsafe_allow_html=True
#             )
#         st.divider()

#     faq_schema = blog.get("FAQ_Schema", {})
#     faqs       = faq_schema.get("mainEntity", [])
#     if faqs:
#         faq_jsonld = json.dumps(faq_schema, indent=2, ensure_ascii=False)
#         st.markdown("**FAQs — copy all (JSON-LD Schema)**")
#         st.text_area(
#             label            = "FAQs JSON-LD",
#             value            = faq_jsonld,
#             height           = 200,
#             key              = f"cp_allfaqs_{idx}",
#             label_visibility = "collapsed"
#         )
#         st.divider()
#         st.markdown("**FAQ details**")
#         for fi, faq in enumerate(faqs):
#             with st.expander(faq.get("name", "")):
#                 st.code(faq.get("acceptedAnswer", {}).get("text", ""), language=None)
#         st.divider()

#     notify_text = item.get("notify", {}).get("blog_notify", "")
#     if notify_text:
#         copy_row("Blog notification", notify_text, key=f"cp_notify_{idx}")
#         st.divider()

#     # ── CHANGE — Blog image handles both template and AI mode ─
#     show_image_section(
#         label         = "Blog Thumbnail Outer (640×480)",
#         image_field   = item.get("blog_image_outer") or item.get("blog_image"),
#         display_width = 640,
#         idx           = idx,
#         key_prefix    = "blog_outer"
#     )
#     st.divider()

#     show_image_section(
#         label         = "Blog Thumbnail Inner (1920×490)",
#         image_field   = item.get("blog_image_inner"),
#         display_width = 700,
#         idx           = idx,
#         key_prefix    = "blog_inner"
#     )
#     st.divider()

#     cta = blog.get("CTA")
#     if cta:
#         if isinstance(cta, dict):
#             cta_text = cta.get("text", "Trade on Swastika ↗")
#             cta_url  = cta.get("url",  "https://trade.swastika.co.in/")
#         else:
#             cta_text = "Trade on Swastika ↗"
#             cta_url  = cta if str(cta).startswith("http") else "https://trade.swastika.co.in/"
#         st.link_button(cta_text, cta_url)


# # ── Instagram Detail ──────────────────────────────────────────
# if st.session_state.selected_insta is not None:
#     idx  = st.session_state.selected_insta
#     item = results[idx]

#     st.subheader("Instagram detail")

#     insta_data = item.get("instagram_notify", {})
#     caption    = insta_data.get("instagram_caption", "No caption found.")
#     hashtags   = insta_data.get("hashtags", "")

#     copy_row("Caption", caption, key=f"cp_insta_caption_{idx}")

#     if hashtags:
#         st.divider()
#         copy_row("Hashtags", hashtags, key=f"cp_insta_hashtags_{idx}")

#     st.divider()

#     show_image_section(
#         label         = "Instagram Image (1080×1080)",
#         image_field   = item.get("instagram_image"),
#         display_width = 540,
#         idx           = idx,
#         key_prefix    = "insta"
#     )

# import streamlit as st
# from bs4 import BeautifulSoup
# import os
# from urllib.parse import urlparse
# import json

# st.set_page_config(layout="wide", page_title="Swastika Blog Dashboard")

# DEFAULT_COUNTRY  = "India"
# DEFAULT_CATEGORY = "finance"


# def copy_row(label: str, text: str, key: str = ""):
#     st.markdown(f"**{label}**")
#     st.text_area(
#         label            = label,
#         value            = text,
#         height           = min(150, 35 + text.count('\n') * 20),
#         key              = key,
#         label_visibility = "collapsed"
#     )


# def download_image_btn(image_path: str, filename: str, label: str = "Download", unique_key: str = ""):
#     if image_path and os.path.exists(image_path):
#         ext  = os.path.splitext(filename)[1].lower()
#         mime = "image/webp" if ext == ".webp" else "image/jpeg"
#         with open(image_path, "rb") as f:
#             img_bytes = f.read()
#         st.download_button(
#             label     = label,
#             data      = img_bytes,
#             file_name = filename,
#             mime      = mime,
#             key       = f"dl_{unique_key}_{filename}"
#         )
#     else:
#         st.caption("Image not available for download.")


# def get_image_path(image_field, prefer: str = "webp") -> str:
#     if isinstance(image_field, dict):
#         if prefer == "webp" and image_field.get("webp"):
#             return image_field["webp"]
#         return image_field.get("jpg", "")
#     return image_field or ""


# def render_blog_in_box(html_content: str):
#     st.markdown(
#         f"""
#         <div style="
#             height: 400px;
#             overflow-y: auto;
#             border: 1px solid #e0e0e0;
#             border-radius: 8px;
#             padding: 16px 20px;
#             background-color: #fafafa;
#             font-size: 15px;
#             line-height: 1.8;
#             color: #333;
#         ">{html_content}</div>
#         """,
#         unsafe_allow_html=True
#     )


# def show_image_section(label: str, image_field, display_width: int, idx: int, key_prefix: str):
#     st.markdown(f"**{label}**")
#     webp_path = get_image_path(image_field, prefer="webp")
#     jpg_path  = get_image_path(image_field, prefer="jpg")

#     if webp_path and os.path.exists(webp_path):
#         st.image(webp_path, width=display_width)
#         col1, col2 = st.columns(2)
#         with col1:
#             download_image_btn(
#                 webp_path,
#                 os.path.basename(webp_path),
#                 "⬇ Download WebP",
#                 unique_key=f"{key_prefix}_webp_{idx}"
#             )
#         with col2:
#             download_image_btn(
#                 jpg_path,
#                 os.path.basename(jpg_path),
#                 "⬇ Download JPG",
#                 unique_key=f"{key_prefix}_jpg_{idx}"
#             )
#     elif jpg_path and os.path.exists(jpg_path):
#         st.image(jpg_path, width=display_width)
#         download_image_btn(
#             jpg_path,
#             os.path.basename(jpg_path),
#             "⬇ Download JPG",
#             unique_key=f"{key_prefix}_jpg_only_{idx}"
#         )
#     else:
#         st.warning(f"{label} not available.")


# st.title("Blog Dashboard")
# st.caption(f"Country: {DEFAULT_COUNTRY}  ·  Category: {DEFAULT_CATEGORY.capitalize()}")


# @st.cache_data(show_spinner="Loading blogs...", ttl=60)
# def load_data():
#     """Auto-detects which output file to load based on most recently modified."""
#     candidates = [
#         "output/testing_webp_output.json",
#         "output/output.json",
#     ]
#     existing = [f for f in candidates if os.path.exists(f)]
#     if not existing:
#         return []
#     latest_file = max(existing, key=os.path.getmtime)
#     st.session_state["loaded_file"] = latest_file
#     with open(latest_file, "r", encoding="utf-8") as f:
#         try:
#             data = json.load(f)
#             return data.get("results", []) if isinstance(data, dict) else data
#         except:
#             return []


# output  = load_data()
# results = output if isinstance(output, list) else output.get("results", [])

# if st.button("Refresh data"):
#     st.cache_data.clear()
#     st.rerun()

# for key in ["selected_blog", "selected_insta", "page"]:
#     if key not in st.session_state:
#         st.session_state[key] = None if key != "page" else 1

# if not results:
#     st.warning("No blogs returned.")
#     st.stop()

# m1, m2, m3, m4 = st.columns(4)
# m1.metric("Total blogs",  len(results))
# m2.metric("Country",      DEFAULT_COUNTRY)
# m3.metric("Category",     DEFAULT_CATEGORY.capitalize())
# m4.metric("Sources", len(set(
#     urlparse(r.get("Blog_Link") or r.get("Blog_Links", "")).netloc
#     for r in results
# )))

# st.divider()

# sc, ss = st.columns([4, 1])
# search = sc.text_input("Search", placeholder="Search title or content...", label_visibility="collapsed")
# sort   = ss.selectbox("Sort", ["Newest first", "Oldest first", "A to Z"], label_visibility="collapsed")

# filtered = results
# if search:
#     q = search.lower()
#     filtered = [
#         r for r in results
#         if q in r.get("Blog_Title", "").lower()
#         or q in r.get("blog", {}).get("Blog_Title", "").lower()
#         or q in r.get("Blog_Content", "").lower()
#     ]
#     st.session_state.page = 1

# if sort == "Newest first":
#     filtered = sorted(filtered, key=lambda x: x.get("Publish_Date") or x.get("Blog_PublishDate") or x.get("Run_Timestamp", ""), reverse=True)
# elif sort == "Oldest first":
#     filtered = sorted(filtered, key=lambda x: x.get("Publish_Date") or x.get("Blog_PublishDate") or x.get("Run_Timestamp", ""))
# else:
#     filtered = sorted(filtered, key=lambda x: x.get("blog", {}).get("Blog_Title", "") or x.get("Blog_Title", ""))

# if not filtered:
#     st.info("No blogs match your search.")
#     st.stop()

# # ── Pagination ────────────────────────────────────────────────
# PAGE_SIZE = 20
# total     = len(filtered)
# max_page  = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)

# if st.session_state.page > max_page:
#     st.session_state.page = 1

# p1, p2, p3 = st.columns([1, 2, 1])
# with p1:
#     if st.button("← Prev") and st.session_state.page > 1:
#         st.session_state.page -= 1
#         st.rerun()
# with p2:
#     st.caption(f"Page {st.session_state.page} of {max_page}  ·  {total} blogs")
# with p3:
#     if st.button("Next →") and st.session_state.page < max_page:
#         st.session_state.page += 1
#         st.rerun()

# start      = (st.session_state.page - 1) * PAGE_SIZE
# end        = start + PAGE_SIZE
# page_items = filtered[start:end]

# # ── Header ───────────────────────────────────────────────────
# h1, h2, h3, h4, h5, h6 = st.columns([2, 4, 1, 1.5, 1.5, 2])
# h1.caption("Publish date")
# h2.caption("Blog title")
# h3.caption("Blog")
# h4.caption("Instagram")
# h5.caption("Tag")
# h6.caption("Source")
# st.divider()

# # ── Scrollable blog list ──────────────────────────────────────
# with st.container(height=500):
#     for i, item in enumerate(page_items):
#         real_idx = results.index(item)
#         publish  = item.get("Publish_Date") or item.get("Blog_PublishDate") or item.get("Run_Timestamp", "—")
#         title    = item.get("blog", {}).get("Blog_Title", "") or item.get("Blog_Title", "—")
#         tag      = item.get("image_text", {}).get("tag", "GENERAL")
#         link     = item.get("Blog_Link") or item.get("Blog_Links", "—")

#         try:
#             domain = urlparse(link).netloc.replace("www.", "")
#         except:
#             domain = link[:30] if link else "—"

#         c1, c2, c3, c4, c5, c6 = st.columns([2, 4, 1, 1.5, 1.5, 2])
#         c1.caption(publish[:16] if publish else "—")
#         c2.write(f"**{title[:80]}**" if len(title) > 80 else f"**{title}**")

#         if c3.button("Read", key=f"blog_{real_idx}"):
#             st.session_state.selected_blog  = real_idx
#             st.session_state.selected_insta = None

#         if c4.button("📸 Insta", key=f"insta_{real_idx}"):
#             st.session_state.selected_insta = real_idx
#             st.session_state.selected_blog  = None

#         c5.write(f"`{tag}`")
#         c6.markdown(f"[{domain}]({link})")
#         st.divider()


# # ── Blog Detail ───────────────────────────────────────────────
# if st.session_state.selected_blog is not None:
#     idx  = st.session_state.selected_blog
#     item = results[idx]
#     blog = item.get("blog", {})

#     st.subheader("Blog detail")
#     m1, m2, m3 = st.columns(3)
#     m1.markdown(f"**Tag:** `{item.get('image_text', {}).get('tag', 'GENERAL')}`")
#     m2.markdown(f"**Country:** `{DEFAULT_COUNTRY}`")
#     m3.markdown(f"**Generated:** `{item.get('Run_Timestamp', '—')}`")

#     link = item.get("Blog_Link") or item.get("Blog_Links", "")
#     if link:
#         st.markdown(f"[Read original source ↗]({link})")
#     st.divider()

#     # ══════════════════════════════════════════════════════════
#     # SECTION 1 — BLOG TITLE
#     # ══════════════════════════════════════════════════════════
#     ai_title = blog.get("Blog_Title", "") or item.get("Blog_Title", "")
#     copy_row("1. Blog Title", ai_title, key=f"cp_title_{idx}")
#     st.divider()

#     # ══════════════════════════════════════════════════════════
#     # SECTION 2 — SEO BOX (Meta Title + Meta Desc + JSON-LD FAQ)
#     # All in one copyable text area
#     # ══════════════════════════════════════════════════════════
#     meta_title = blog.get("Meta_Title", "")
#     meta_desc  = blog.get("Meta_Description", "")
#     faq_schema = blog.get("FAQ_Schema", {})
#     faqs       = faq_schema.get("mainEntity", [])
#     faq_jsonld = json.dumps(faq_schema, indent=2, ensure_ascii=False) if faq_schema else ""

#     st.markdown("**2. SEO Data**")
#     st.markdown(
#         """
#         <div style="
#             border: 1.5px solid #1A56DB;
#             border-radius: 8px;
#             padding: 12px 16px 4px 16px;
#             background: #f0f4ff;
#             margin-bottom: 8px;
#         ">
#             <span style="font-size:12px;color:#1A56DB;font-weight:600;">
#                 SEO — Meta Title · Meta Description · JSON-LD FAQ Schema
#             </span>
#         </div>
#         """,
#         unsafe_allow_html=True
#     )

#     # Show char counts separately for readability
#     if meta_title:
#         char_count = len(meta_title)
#         color = "green" if char_count <= 60 else "red"
#         st.markdown(
#             f"Meta Title &nbsp; <span style='color:{color};font-size:12px'>{char_count}/60 chars</span>",
#             unsafe_allow_html=True
#         )
#     if meta_desc:
#         char_count = len(meta_desc)
#         color = "green" if char_count <= 160 else "red"
#         st.markdown(
#             f"Meta Description &nbsp; <span style='color:{color};font-size:12px'>{char_count}/160 chars</span>",
#             unsafe_allow_html=True
#         )

#     # ── Single copyable box with ALL SEO data ─────────────────
#     seo_combined = ""
#     if meta_title:
#         seo_combined += f"META TITLE:\n{meta_title}\n\n"
#     if meta_desc:
#         seo_combined += f"META DESCRIPTION:\n{meta_desc}\n\n"
#     if faq_jsonld:
#         seo_combined += f"JSON-LD FAQ SCHEMA:\n{faq_jsonld}"

#     if seo_combined:
#         st.text_area(
#             label            = "SEO combined",
#             value            = seo_combined,
#             height           = 300,
#             key              = f"cp_seo_combined_{idx}",
#             label_visibility = "collapsed"
#         )
#     st.divider()

#     # ══════════════════════════════════════════════════════════
#     # SECTION 3 — BLOG CONTENT BOX
#     # Key takeaways + Blog content (rendered + HTML) + Conclusion + FAQ details
#     # All in one copyable text area
#     # ══════════════════════════════════════════════════════════
#     st.markdown("**3. Blog Content**")
#     st.markdown(
#         """
#         <div style="
#             border: 1.5px solid #10B981;
#             border-radius: 8px;
#             padding: 12px 16px 4px 16px;
#             background: #f0fff8;
#             margin-bottom: 8px;
#         ">
#             <span style="font-size:12px;color:#10B981;font-weight:600;">
#                 Key Takeaways · Blog Content · Conclusion · FAQ Details
#             </span>
#         </div>
#         """,
#         unsafe_allow_html=True
#     )

#     tldr      = blog.get("TLDR", [])
#     blog_html = blog.get("Blog_Content", "")
#     conclusion = blog.get("Conclusion", "")

#     # ── Rendered blog preview ─────────────────────────────────
#     if blog_html:
#         render_blog_in_box(blog_html)

#     # ── Build single copyable text with all blog content ──────
#     # ── Build single copyable box with ALL blog content ───────
#     blog_combined = ""

#     if tldr:
#         blog_combined += "KEY TAKEAWAYS:\n"
#         blog_combined += "\n".join(f"• {t}" for t in tldr)
#         blog_combined += "\n\n"

#     if blog_html:
#         blog_combined += "BLOG CONTENT (HTML):\n"
#         blog_combined += blog_html
#         blog_combined += "\n\n"

#     if conclusion:
#         blog_combined += "CONCLUSION:\n"
#         blog_combined += conclusion
#         blog_combined += "\n\n"

#     if faqs:
#         blog_combined += "FAQ DETAILS:\n"
#         for faq in faqs:
#             q = faq.get("name", "")
#             a = faq.get("acceptedAnswer", {}).get("text", "")
#             blog_combined += f"Q: {q}\nA: {a}\n\n"

#     if blog_combined:
#         st.text_area(
#             label            = "Blog content combined",
#             value            = blog_combined,
#             height           = 400,
#             key              = f"cp_blog_combined_{idx}",
#             label_visibility = "collapsed"
#         )
#     st.divider()

#     # ══════════════════════════════════════════════════════════
#     # SECTION 4 — BLOG NOTIFICATION (separate)
#     # ══════════════════════════════════════════════════════════
#     notify_text = item.get("notify", {}).get("blog_notify", "")
#     if notify_text:
#         copy_row("4. Blog Notification", notify_text, key=f"cp_notify_{idx}")
#         st.divider()

#     # ══════════════════════════════════════════════════════════
#     # SECTION 5 — IMAGES (separate)
#     # ══════════════════════════════════════════════════════════
#     st.markdown("**5. Images**")

#     show_image_section(
#         label         = "Blog Thumbnail Outer (640×480)",
#         image_field   = item.get("blog_image_outer") or item.get("blog_image"),
#         display_width = 640,
#         idx           = idx,
#         key_prefix    = "blog_outer"
#     )
#     st.divider()

#     if item.get("blog_image_inner"):
#         show_image_section(
#             label         = "Blog Thumbnail Inner (1920×490)",
#             image_field   = item.get("blog_image_inner"),
#             display_width = 700,
#             idx           = idx,
#             key_prefix    = "blog_inner"
#         )
#         st.divider()

#     cta = blog.get("CTA")
#     if cta:
#         if isinstance(cta, dict):
#             cta_text = cta.get("text", "Trade on Swastika ↗")
#             cta_url  = cta.get("url",  "https://trade.swastika.co.in/")
#         else:
#             cta_text = "Trade on Swastika ↗"
#             cta_url  = cta if str(cta).startswith("http") else "https://trade.swastika.co.in/"
#         st.link_button(cta_text, cta_url)


# # ── Instagram Detail ──────────────────────────────────────────
# if st.session_state.selected_insta is not None:
#     idx  = st.session_state.selected_insta
#     item = results[idx]

#     st.subheader("Instagram detail")

#     insta_data = item.get("instagram_notify", {})
#     caption    = insta_data.get("instagram_caption", "No caption found.")
#     hashtags   = insta_data.get("hashtags", "")

#     copy_row("Caption", caption, key=f"cp_insta_caption_{idx}")

#     if hashtags:
#         st.divider()
#         copy_row("Hashtags", hashtags, key=f"cp_insta_hashtags_{idx}")

#     st.divider()

#     show_image_section(
#         label         = "Instagram Image (1080×1080)",
#         image_field   = item.get("instagram_image"),
#         display_width = 540,
#         idx           = idx,
#         key_prefix    = "insta"
#     )

# import streamlit as st
# from bs4 import BeautifulSoup
# import os
# import re
# from urllib.parse import urlparse
# import json

# st.set_page_config(layout="wide", page_title="Swastika Blog Dashboard")

# DEFAULT_COUNTRY  = "India"
# DEFAULT_CATEGORY = "finance"


# def copy_row(label: str, text: str, key: str = ""):
#     st.markdown(f"**{label}**")
#     st.text_area(
#         label            = label,
#         value            = text,
#         height           = min(150, 35 + text.count('\n') * 20),
#         key              = key,
#         label_visibility = "collapsed"
#     )


# def download_image_btn(image_path: str, filename: str, label: str = "Download", unique_key: str = ""):
#     if image_path and os.path.exists(image_path):
#         ext  = os.path.splitext(filename)[1].lower()
#         mime = "image/webp" if ext == ".webp" else "image/jpeg"
#         with open(image_path, "rb") as f:
#             img_bytes = f.read()
#         st.download_button(
#             label     = label,
#             data      = img_bytes,
#             file_name = filename,
#             mime      = mime,
#             key       = f"dl_{unique_key}_{filename}"
#         )
#     else:
#         st.caption("Image not available for download.")


# def get_image_path(image_field, prefer: str = "webp") -> str:
#     if isinstance(image_field, dict):
#         if prefer == "webp" and image_field.get("webp"):
#             return image_field["webp"]
#         return image_field.get("jpg", "")
#     return image_field or ""


# # def clean_blog_html(blog_html: str) -> str:
# #     """
# #     Cleans blog HTML:
# #     - Removes first <h1> (duplicate title)
# #     - Removes ALL div/section/article tags including stray closing tags
# #     - Keeps only allowed tags: h1-h4, p, ul, ol, li, strong, em, br, a, span
# #     """
# #     if not blog_html:
# #         return ""

# #     allowed_tags = ["h1", "h2", "h3", "h4", "p", "ul", "ol",
# #                     "li", "strong", "em", "br", "a", "span"]

# #     soup = BeautifulSoup(blog_html, "html.parser")

# #     # ── Remove first h1 (duplicate title) ────────────────────
# #     first_h1 = soup.find("h1")
# #     if first_h1:
# #         first_h1.decompose()

# #     # ── Unwrap all tags not in allowed list ───────────────────
# #     for tag in soup.find_all(True):
# #         if tag.name not in allowed_tags:
# #             tag.unwrap()

# #     cleaned = str(soup)

# #     # ── Remove stray div tags (opening + closing) ─────────────
# #     cleaned = re.sub(r'<div[^>]*>', '', cleaned)
# #     cleaned = re.sub(r'</div>',     '', cleaned)

# #     # ── Remove stray section/article tags ─────────────────────
# #     cleaned = re.sub(r'<section[^>]*>', '', cleaned)
# #     cleaned = re.sub(r'</section>',     '', cleaned)
# #     cleaned = re.sub(r'<article[^>]*>', '', cleaned)
# #     cleaned = re.sub(r'</article>',     '', cleaned)

# #     # ── Clean up extra blank lines ────────────────────────────
# #     cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)

# #     return cleaned.strip()
# def clean_blog_html(blog_html: str) -> str:
#     if not blog_html:
#         return ""

#     allowed_tags = ["h1", "h2", "h3", "h4", "p", "ul", "ol",
#                     "li", "strong", "em", "br", "a", "span"]

#     soup = BeautifulSoup(blog_html, "html.parser")

#     # ── Remove first h1 (duplicate title) ────────────────────
#     first_h1 = soup.find("h1")
#     if first_h1:
#         first_h1.decompose()

#     # ── Remove FAQ and Conclusion h2 blocks ──────────────────
#     for h2 in soup.find_all("h2"):
#         heading_text = h2.get_text(strip=True).lower()
#         if heading_text in ("faq", "conclusion"):
#             # Remove the h2 and all siblings until next h2
#             current = h2.next_sibling
#             while current:
#                 next_node = current.next_sibling
#                 if hasattr(current, 'name') and current.name == "h2":
#                     break
#                 if hasattr(current, 'decompose'):
#                     current.decompose()
#                 current = next_node
#             h2.decompose()

#     # ── Unwrap all tags not in allowed list ───────────────────
#     for tag in soup.find_all(True):
#         if tag.name not in allowed_tags:
#             tag.unwrap()

#     cleaned = str(soup)

#     # ── Remove stray div/section/article tags ─────────────────
#     cleaned = re.sub(r'<div[^>]*>',    '', cleaned)
#     cleaned = re.sub(r'</div>',         '', cleaned)
#     cleaned = re.sub(r'<section[^>]*>', '', cleaned)
#     cleaned = re.sub(r'</section>',     '', cleaned)
#     cleaned = re.sub(r'<article[^>]*>', '', cleaned)
#     cleaned = re.sub(r'</article>',     '', cleaned)

#     # ── Clean up extra blank lines ────────────────────────────
#     cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)

#     return cleaned.strip()

# def show_image_section(label: str, image_field, display_width: int, idx: int, key_prefix: str):
#     st.markdown(f"**{label}**")
#     webp_path = get_image_path(image_field, prefer="webp")
#     jpg_path  = get_image_path(image_field, prefer="jpg")

#     if webp_path and os.path.exists(webp_path):
#         st.image(webp_path, width=display_width)
#         col1, col2 = st.columns(2)
#         with col1:
#             download_image_btn(
#                 webp_path,
#                 os.path.basename(webp_path),
#                 "⬇ Download WebP",
#                 unique_key=f"{key_prefix}_webp_{idx}"
#             )
#         with col2:
#             download_image_btn(
#                 jpg_path,
#                 os.path.basename(jpg_path),
#                 "⬇ Download JPG",
#                 unique_key=f"{key_prefix}_jpg_{idx}"
#             )
#     elif jpg_path and os.path.exists(jpg_path):
#         st.image(jpg_path, width=display_width)
#         download_image_btn(
#             jpg_path,
#             os.path.basename(jpg_path),
#             "⬇ Download JPG",
#             unique_key=f"{key_prefix}_jpg_only_{idx}"
#         )
#     else:
#         st.warning(f"{label} not available.")


# st.title("Blog Dashboard")
# st.caption(f"Country: {DEFAULT_COUNTRY}  ·  Category: {DEFAULT_CATEGORY.capitalize()}")

# # ── Set same as mergeall_engine.py ───────────────────────────
# USE_AI_IMAGES = False
# OUTPUT_FILE   = "testing_webp_output.json" if USE_AI_IMAGES else "output.json"


# @st.cache_data(show_spinner="Loading blogs...", ttl=60)
# def load_data():
#     path = f"output/{OUTPUT_FILE}"
#     if not os.path.exists(path):
#         return []
#     with open(path, "r", encoding="utf-8") as f:
#         try:
#             return json.load(f)
#         except:
#             return []


# output  = load_data()
# results = output if isinstance(output, list) else output.get("results", [])

# if st.button("Refresh data"):
#     st.cache_data.clear()
#     st.rerun()

# for key in ["selected_blog", "selected_insta", "page"]:
#     if key not in st.session_state:
#         st.session_state[key] = None if key != "page" else 1

# if not results:
#     st.warning("No blogs returned.")
#     st.stop()

# m1, m2, m3, m4 = st.columns(4)
# m1.metric("Total blogs",  len(results))
# m2.metric("Country",      DEFAULT_COUNTRY)
# m3.metric("Category",     DEFAULT_CATEGORY.capitalize())
# m4.metric("Sources", len(set(
#     urlparse(r.get("Blog_Link") or r.get("Blog_Links", "")).netloc
#     for r in results
# )))

# st.divider()

# sc, ss = st.columns([4, 1])
# search = sc.text_input("Search", placeholder="Search title or content...", label_visibility="collapsed")
# sort   = ss.selectbox("Sort", ["Newest first", "Oldest first", "A to Z"], label_visibility="collapsed")

# filtered = results
# if search:
#     q = search.lower()
#     filtered = [
#         r for r in results
#         if q in r.get("Blog_Title", "").lower()
#         or q in r.get("blog", {}).get("Blog_Title", "").lower()
#         or q in r.get("Blog_Content", "").lower()
#     ]
#     st.session_state.page = 1

# if sort == "Newest first":
#     filtered = sorted(filtered, key=lambda x: x.get("Publish_Date") or x.get("Blog_PublishDate") or x.get("Run_Timestamp", ""), reverse=True)
# elif sort == "Oldest first":
#     filtered = sorted(filtered, key=lambda x: x.get("Publish_Date") or x.get("Blog_PublishDate") or x.get("Run_Timestamp", ""))
# else:
#     filtered = sorted(filtered, key=lambda x: x.get("blog", {}).get("Blog_Title", "") or x.get("Blog_Title", ""))

# if not filtered:
#     st.info("No blogs match your search.")
#     st.stop()

# # ── Pagination ────────────────────────────────────────────────
# PAGE_SIZE = 20
# total     = len(filtered)
# max_page  = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)

# if st.session_state.page > max_page:
#     st.session_state.page = 1

# p1, p2, p3 = st.columns([1, 2, 1])
# with p1:
#     if st.button("← Prev") and st.session_state.page > 1:
#         st.session_state.page -= 1
#         st.rerun()
# with p2:
#     st.caption(f"Page {st.session_state.page} of {max_page}  ·  {total} blogs")
# with p3:
#     if st.button("Next →") and st.session_state.page < max_page:
#         st.session_state.page += 1
#         st.rerun()

# start      = (st.session_state.page - 1) * PAGE_SIZE
# end        = start + PAGE_SIZE
# page_items = filtered[start:end]

# # ── Header ───────────────────────────────────────────────────
# h1, h2, h3, h4, h5, h6 = st.columns([2, 4, 1, 1.5, 1.5, 2])
# h1.caption("Publish date")
# h2.caption("Blog title")
# h3.caption("Blog")
# h4.caption("Instagram")
# h5.caption("Tag")
# h6.caption("Source")
# st.divider()

# # ── Scrollable blog list ──────────────────────────────────────
# with st.container(height=500):
#     for i, item in enumerate(page_items):
#         real_idx = results.index(item)
#         publish  = item.get("Publish_Date") or item.get("Blog_PublishDate") or item.get("Run_Timestamp", "—")
#         title    = item.get("blog", {}).get("Blog_Title", "") or item.get("Blog_Title", "—")
#         tag      = item.get("image_text", {}).get("tag", "GENERAL")
#         link     = item.get("Blog_Link") or item.get("Blog_Links", "—")

#         try:
#             domain = urlparse(link).netloc.replace("www.", "")
#         except:
#             domain = link[:30] if link else "—"

#         c1, c2, c3, c4, c5, c6 = st.columns([2, 4, 1, 1.5, 1.5, 2])
#         c1.caption(publish[:16] if publish else "—")
#         c2.write(f"**{title[:80]}**" if len(title) > 80 else f"**{title}**")

#         if c3.button("Read", key=f"blog_{real_idx}"):
#             st.session_state.selected_blog  = real_idx
#             st.session_state.selected_insta = None

#         if c4.button("📸 Insta", key=f"insta_{real_idx}"):
#             st.session_state.selected_insta = real_idx
#             st.session_state.selected_blog  = None

#         c5.write(f"`{tag}`")
#         c6.markdown(f"[{domain}]({link})")
#         st.divider()


# # ── Blog Detail ───────────────────────────────────────────────
# if st.session_state.selected_blog is not None:
#     idx  = st.session_state.selected_blog
#     item = results[idx]
#     blog = item.get("blog", {})

#     st.subheader("Blog detail")
#     m1, m2, m3 = st.columns(3)
#     m1.markdown(f"**Tag:** `{item.get('image_text', {}).get('tag', 'GENERAL')}`")
#     m2.markdown(f"**Country:** `{DEFAULT_COUNTRY}`")
#     m3.markdown(f"**Generated:** `{item.get('Run_Timestamp', '—')}`")

#     link = item.get("Blog_Link") or item.get("Blog_Links", "")
#     if link:
#         st.markdown(f"[Read original source ↗]({link})")
#     st.divider()

#     # ── Extract all blog fields ───────────────────────────────
#     ai_title   = blog.get("Blog_Title", "") or item.get("Blog_Title", "")
#     meta_title = blog.get("Meta_Title", "")
#     meta_desc  = blog.get("Meta_Description", "")
#     faq_schema = blog.get("FAQ_Schema", {})
#     faqs       = faq_schema.get("mainEntity", [])
#     faq_jsonld = json.dumps(faq_schema, indent=2, ensure_ascii=False) if faq_schema else ""
#     tldr       = blog.get("TLDR", [])
#     blog_html  = blog.get("Blog_Content", "")
#     conclusion = blog.get("Conclusion", "")

#     # ── Clean blog HTML ───────────────────────────────────────
#     blog_html_clean = clean_blog_html(blog_html)

#     # ══════════════════════════════════════════════════════════
#     # SECTION 1 — BLOG TITLE (separate copyable)
#     # ══════════════════════════════════════════════════════════
#     copy_row("1. Blog Title", ai_title, key=f"cp_title_{idx}")
#     st.divider()

#     # ══════════════════════════════════════════════════════════
#     # SECTION 2 — SEO DATA (single copyable box)
#     # Meta Title + Meta Description + JSON-LD FAQ Schema
#     # ══════════════════════════════════════════════════════════
#     st.markdown("**2. SEO Data**")
#     st.markdown(
#         """
#         <div style="
#             border: 1.5px solid #1A56DB;
#             border-radius: 8px;
#             padding: 12px 16px 4px 16px;
#             background: #f0f4ff;
#             margin-bottom: 8px;
#         ">
#             <span style="font-size:12px;color:#1A56DB;font-weight:600;">
#                 SEO — Meta Title · Meta Description · JSON-LD FAQ Schema
#             </span>
#         </div>
#         """,
#         unsafe_allow_html=True
#     )

#     if meta_title:
#         char_count = len(meta_title)
#         color = "green" if char_count <= 60 else "red"
#         st.markdown(
#             f"Meta Title &nbsp; <span style='color:{color};font-size:12px'>{char_count}/60 chars</span>",
#             unsafe_allow_html=True
#         )
#     if meta_desc:
#         char_count = len(meta_desc)
#         color = "green" if char_count <= 160 else "red"
#         st.markdown(
#             f"Meta Description &nbsp; <span style='color:{color};font-size:12px'>{char_count}/160 chars</span>",
#             unsafe_allow_html=True
#         )

#     seo_combined = ""
#     if meta_title:
#         seo_combined += f"META TITLE:\n{meta_title}\n\n"
#     if meta_desc:
#         seo_combined += f"META DESCRIPTION:\n{meta_desc}\n\n"
#     if faq_jsonld:
#         seo_combined += f"JSON-LD FAQ SCHEMA:\n{faq_jsonld}"

#     if seo_combined:
#         st.text_area(
#             label            = "SEO combined",
#             value            = seo_combined,
#             height           = 300,
#             key              = f"cp_seo_combined_{idx}",
#             label_visibility = "collapsed"
#         )
#     st.divider()

#     # ══════════════════════════════════════════════════════════
#     # SECTION 3 — BLOG CONTENT BOX
#     # Format:
#     #   <h1> Blog Title (once only)
#     #   <h2> Key Takeaways + <ul><li>
#     #   Blog Content HTML (h1 stripped, stray tags removed)
#     #   <h2> FAQ Details + <h3>Q + <p>A
#     #   <h2> Conclusion + <p>
#     # Two boxes: copyable text + rendered HTML preview
#     # ══════════════════════════════════════════════════════════
#     st.markdown("**3. Blog Content**")
#     st.markdown(
#         """
#         <div style="
#             border: 1.5px solid #10B981;
#             border-radius: 8px;
#             padding: 12px 16px 4px 16px;
#             background: #f0fff8;
#             margin-bottom: 8px;
#         ">
#             <span style="font-size:12px;color:#10B981;font-weight:600;">
#                 Blog Title · Key Takeaways · Blog Content · FAQ Details · Conclusion — HTML Format
#             </span>
#         </div>
#         """,
#         unsafe_allow_html=True
#     )

#     blog_combined = ""

#     # ── 1. Blog Title — once only ─────────────────────────────
#     if ai_title:
#         blog_combined += f"<h1>{ai_title}</h1>\n\n"

#     # ── 2. Key Takeaways ──────────────────────────────────────
#     if tldr:
#         blog_combined += "<h2>Key Takeaways</h2>\n<ul>\n"
#         blog_combined += "\n".join(f"<li>{t}</li>" for t in tldr)
#         blog_combined += "\n</ul>\n\n"

#     # ── 3. Blog Content HTML (cleaned) ───────────────────────
#     if blog_html_clean:
#         blog_combined += blog_html_clean
#         blog_combined += "\n\n"

#     # ── 4. FAQ Details ────────────────────────────────────────
#     if faqs:
#         blog_combined += "<h2>FAQ</h2>\n"
#         for faq in faqs:
#             q = faq.get("name", "")
#             a = faq.get("acceptedAnswer", {}).get("text", "")
#             blog_combined += f"<h3>{q}</h3>\n<p>{a}</p>\n\n"

#     # ── 5. Conclusion ─────────────────────────────────────────
#     if conclusion:
#         blog_combined += "<h2>Conclusion</h2>\n"
#         blog_combined += f"<p>{conclusion}</p>\n\n"

#     if blog_combined:
#         blog_combined = re.sub(r'<div[^>]*>',  '', blog_combined)
#         blog_combined = re.sub(r'</div>',       '', blog_combined)
#         blog_combined = re.sub(r'<section[^>]*>', '', blog_combined)
#         blog_combined = re.sub(r'</section>',   '', blog_combined)
#         blog_combined = re.sub(r'<article[^>]*>', '', blog_combined)
#         blog_combined = re.sub(r'</article>',   '', blog_combined)
#         blog_combined = re.sub(r'\n{3,}', '\n\n', blog_combined)
#         blog_combined = blog_combined.strip()

#         # ── Copyable text area ────────────────────────────────
#         st.text_area(
#             label            = "Blog content combined",
#             value            = blog_combined,
#             height           = 400,
#             key              = f"cp_blog_combined_{idx}",
#             label_visibility = "collapsed"
#         )

#         # ── Rendered HTML preview ─────────────────────────────
#         st.markdown("**Preview**")
#         st.markdown(
#             f"""
#             <div style="
#                 height: 500px;
#                 overflow-y: auto;
#                 border: 1px solid #e0e0e0;
#                 border-radius: 8px;
#                 padding: 24px 28px;
#                 background-color: #ffffff;
#                 font-size: 15px;
#                 line-height: 1.8;
#                 color: #1a1a1a;
#                 font-family: Arial, sans-serif;
#             ">
#                 {blog_combined}
#             </div>
#             """,
#             unsafe_allow_html=True
#         )

#     st.divider()

#     # ══════════════════════════════════════════════════════════
#     # SECTION 4 — BLOG NOTIFICATION (separate copyable)
#     # ══════════════════════════════════════════════════════════
#     notify_text = item.get("notify", {}).get("blog_notify", "")
#     if notify_text:
#         copy_row("4. Blog Notification", notify_text, key=f"cp_notify_{idx}")
#         st.divider()

#     # ══════════════════════════════════════════════════════════
#     # SECTION 5 — IMAGES
#     # ══════════════════════════════════════════════════════════
#     st.markdown("**5. Images**")

#     show_image_section(
#         label         = "Blog Thumbnail Outer (640×480)",
#         image_field   = item.get("blog_image_outer") or item.get("blog_image"),
#         display_width = 640,
#         idx           = idx,
#         key_prefix    = "blog_outer"
#     )
#     st.divider()

#     if item.get("blog_image_inner"):
#         show_image_section(
#             label         = "Blog Thumbnail Inner (1920×490)",
#             image_field   = item.get("blog_image_inner"),
#             display_width = 700,
#             idx           = idx,
#             key_prefix    = "blog_inner"
#         )
#         st.divider()

#     cta = blog.get("CTA")
#     if cta:
#         if isinstance(cta, dict):
#             cta_text = cta.get("text", "Trade on Swastika ↗")
#             cta_url  = cta.get("url",  "https://trade.swastika.co.in/")
#         else:
#             cta_text = "Trade on Swastika ↗"
#             cta_url  = cta if str(cta).startswith("http") else "https://trade.swastika.co.in/"
#         st.link_button(cta_text, cta_url)


# # ── Instagram Detail ──────────────────────────────────────────
# if st.session_state.selected_insta is not None:
#     idx  = st.session_state.selected_insta
#     item = results[idx]

#     st.subheader("Instagram detail")

#     insta_data = item.get("instagram_notify", {})
#     caption    = insta_data.get("instagram_caption", "No caption found.")
#     hashtags   = insta_data.get("hashtags", "")

#     copy_row("Caption", caption, key=f"cp_insta_caption_{idx}")

#     if hashtags:
#         st.divider()
#         copy_row("Hashtags", hashtags, key=f"cp_insta_hashtags_{idx}")

#     st.divider()

#     show_image_section(
#         label         = "Instagram Image (1080×1080)",
#         image_field   = item.get("instagram_image"),
#         display_width = 540,
#         idx           = idx,
#         key_prefix    = "insta"
#     )
import streamlit as st
from bs4 import BeautifulSoup
import os
import re
from urllib.parse import urlparse
from email.utils import parsedate_to_datetime
from datetime import datetime
import json

st.set_page_config(layout="wide", page_title="Swastika Blog Dashboard")

DEFAULT_COUNTRY  = "India"
DEFAULT_CATEGORY = "finance"


def copy_row(label: str, text: str, key: str = ""):
    st.markdown(f"**{label}**")
    st.text_area(
        label            = label,
        value            = text,
        height           = min(150, 35 + text.count('\n') * 20),
        key              = key,
        label_visibility = "collapsed"
    )


def download_image_btn(image_path: str, filename: str, label: str = "Download", unique_key: str = ""):
    if image_path and os.path.exists(image_path):
        ext  = os.path.splitext(filename)[1].lower()
        mime = "image/webp" if ext == ".webp" else "image/jpeg"
        with open(image_path, "rb") as f:
            img_bytes = f.read()
        st.download_button(
            label     = label,
            data      = img_bytes,
            file_name = filename,
            mime      = mime,
            key       = f"dl_{unique_key}_{filename}"
        )
    else:
        st.caption("Image not available for download.")


def get_image_path(image_field, prefer: str = "webp") -> str:
    if isinstance(image_field, dict):
        if prefer == "webp" and image_field.get("webp"):
            return image_field["webp"]
        return image_field.get("jpg", "")
    return image_field or ""


def parse_date(item) -> datetime:
    """Parse any date format from JSON into a naive datetime for correct sorting."""
    raw = (
        item.get("Publish_Date")
        or item.get("Blog_PublishDate")
        or item.get("Run_Timestamp", "")
    )
    if not raw:
        return datetime.min

    raw = raw.strip()

    # Try RFC 2822: "Tue, 19 May 2026 08:30:45 +0530"
    try:
        dt = parsedate_to_datetime(raw)
        return dt.replace(tzinfo=None)
    except Exception:
        pass

    # Try ISO formats: "2026-05-19 04:16:25", "2026-05-19T04:16:25", "2026-05-19"
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw[:19], fmt)
        except Exception:
            pass

    # Try "15-May-2026 03:0" or "15-May-2026 03:00" style (NSE format)
    try:
        # Normalize short time like "03:0" → "03:00"
        parts = raw.split(" ")
        date_part = parts[0]                          # "15-May-2026"
        time_part = parts[1] if len(parts) > 1 else "00:00"
        if len(time_part.split(":")[1]) < 2:          # fix "3:0" → "03:00"
            time_part = time_part + "0"
        normalized = f"{date_part} {time_part}"
        return datetime.strptime(normalized, "%d-%b-%Y %H:%M")
    except Exception:
        pass

    # Try "15-May-2026" date only
    try:
        return datetime.strptime(raw[:11], "%d-%b-%Y")
    except Exception:
        pass

    return datetime.min
def clean_blog_html(blog_html: str) -> str:
    """
    Cleans blog HTML:
    - Removes first <h1> (duplicate title)
    - Removes duplicate sections: key takeaways, frequently asked questions,
      faq, faq details, conclusion, cta (these are appended separately by the app)
    - Removes all <h4> tags and their following <p> (FAQ questions/answers inside Blog_Content)
    - Removes CTA anchor links pointing to swastika.co.in
    - Removes ALL div/section/article tags including stray closing tags
    - Keeps only allowed tags: h1-h4, p, ul, ol, li, strong, em, br, a, span
    """
    if not blog_html:
        return ""

    allowed_tags = ["h1", "h2", "h3", "h4", "p", "ul", "ol",
                    "li", "strong", "em", "br", "a", "span"]

    # Headings the app appends separately — strip from Blog_Content to avoid duplicates
    REMOVE_PREFIXES = (
        "key takeaways",
        "frequently asked questions",
        "faq",
        "conclusion",
        "cta",
    )

    soup = BeautifulSoup(blog_html, "html.parser")

    # ── Remove first h1 (duplicate title) ────────────────────
    first_h1 = soup.find("h1")
    if first_h1:
        first_h1.decompose()

    # ── Remove duplicate section blocks (h2 + all content until next h2) ──
    for h2 in soup.find_all("h2"):
        heading_text = h2.get_text(strip=True).lower()
        if any(heading_text.startswith(p) for p in REMOVE_PREFIXES):
            current = h2.next_sibling
            while current:
                next_node = current.next_sibling
                if hasattr(current, 'name') and current.name == "h2":
                    break
                if hasattr(current, 'decompose'):
                    current.decompose()
                current = next_node
            h2.decompose()

    # ── Remove all h4 tags and their answer <p> (FAQ Q&A inside Blog_Content) ──
    for h4 in soup.find_all("h4"):
        next_p = h4.find_next_sibling("p")
        if next_p:
            next_p.decompose()
        h4.decompose()

    # ── Remove CTA anchor links (swastika.co.in) ─────────────
    for a_tag in soup.find_all("a", href=True):
        if "swastika.co.in" in a_tag.get("href", ""):
            a_tag.decompose()

    # ── Unwrap all tags not in allowed list ───────────────────
    for tag in soup.find_all(True):
        if tag.name not in allowed_tags:
            tag.unwrap()

    cleaned = str(soup)

    # ── Remove stray div/section/article tags ─────────────────
    cleaned = re.sub(r'<div[^>]*>',    '', cleaned)
    cleaned = re.sub(r'</div>',         '', cleaned)
    cleaned = re.sub(r'<section[^>]*>', '', cleaned)
    cleaned = re.sub(r'</section>',     '', cleaned)
    cleaned = re.sub(r'<article[^>]*>', '', cleaned)
    cleaned = re.sub(r'</article>',     '', cleaned)

    # ── Clean up extra blank lines ────────────────────────────
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)

    return cleaned.strip()


def show_image_section(label: str, image_field, display_width: int, idx: int, key_prefix: str):
    st.markdown(f"**{label}**")
    webp_path = get_image_path(image_field, prefer="webp")
    jpg_path  = get_image_path(image_field, prefer="jpg")

    if webp_path and os.path.exists(webp_path):
        st.image(webp_path, width=display_width)
        col1, col2 = st.columns(2)
        with col1:
            download_image_btn(
                webp_path,
                os.path.basename(webp_path),
                "⬇ Download WebP",
                unique_key=f"{key_prefix}_webp_{idx}"
            )
        with col2:
            download_image_btn(
                jpg_path,
                os.path.basename(jpg_path),
                "⬇ Download JPG",
                unique_key=f"{key_prefix}_jpg_{idx}"
            )
    elif jpg_path and os.path.exists(jpg_path):
        st.image(jpg_path, width=display_width)
        download_image_btn(
            jpg_path,
            os.path.basename(jpg_path),
            "⬇ Download JPG",
            unique_key=f"{key_prefix}_jpg_only_{idx}"
        )
    else:
        st.warning(f"{label} not available.")


st.title("Blog Dashboard")
st.caption(f"Country: {DEFAULT_COUNTRY}  ·  Category: {DEFAULT_CATEGORY.capitalize()}")

# ── Set same as mergeall_engine.py ───────────────────────────
USE_AI_IMAGES = False
OUTPUT_FILE   = "testing_webp_output.json" if USE_AI_IMAGES else "output.json"


@st.cache_data(show_spinner="Loading blogs...", ttl=60)
def load_data():
    path = f"output/{OUTPUT_FILE}"
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except:
            return []


output  = load_data()
results = output if isinstance(output, list) else output.get("results", [])

if st.button("Refresh data"):
    st.cache_data.clear()
    st.rerun()

for key in ["selected_blog", "selected_insta", "page"]:
    if key not in st.session_state:
        st.session_state[key] = None if key != "page" else 1

if not results:
    st.warning("No blogs returned.")
    st.stop()

m1, m2, m3, m4 = st.columns(4)
m1.metric("Total blogs",  len(results))
m2.metric("Country",      DEFAULT_COUNTRY)
m3.metric("Category",     DEFAULT_CATEGORY.capitalize())
m4.metric("Sources", len(set(
    urlparse(r.get("Blog_Link") or r.get("Blog_Links", "")).netloc
    for r in results
)))

st.divider()

sc, ss = st.columns([4, 1])
search = sc.text_input("Search", placeholder="Search title or content...", label_visibility="collapsed")
sort   = ss.selectbox("Sort", ["Newest first", "Oldest first", "A to Z"], label_visibility="collapsed")

filtered = results
if search:
    q = search.lower()
    filtered = [
        r for r in results
        if q in r.get("Blog_Title", "").lower()
        or q in r.get("blog", {}).get("Blog_Title", "").lower()
        or q in r.get("Blog_Content", "").lower()
    ]
    st.session_state.page = 1

# ── Sort with proper date parsing ────────────────────────────
if sort == "Newest first":
    filtered = sorted(filtered, key=parse_date, reverse=True)
elif sort == "Oldest first":
    filtered = sorted(filtered, key=parse_date)
else:
    filtered = sorted(
        filtered,
        key=lambda x: x.get("blog", {}).get("Blog_Title", "") or x.get("Blog_Title", "")
    )

if not filtered:
    st.info("No blogs match your search.")
    st.stop()

# ── Pagination ────────────────────────────────────────────────
PAGE_SIZE = 20
total     = len(filtered)
max_page  = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)

if st.session_state.page > max_page:
    st.session_state.page = 1

p1, p2, p3 = st.columns([1, 2, 1])
with p1:
    if st.button("← Prev") and st.session_state.page > 1:
        st.session_state.page -= 1
        st.rerun()
with p2:
    st.caption(f"Page {st.session_state.page} of {max_page}  ·  {total} blogs")
with p3:
    if st.button("Next →") and st.session_state.page < max_page:
        st.session_state.page += 1
        st.rerun()

start      = (st.session_state.page - 1) * PAGE_SIZE
end        = start + PAGE_SIZE
page_items = filtered[start:end]

# ── Header ───────────────────────────────────────────────────
h1, h2, h3, h4, h5, h6 = st.columns([2, 4, 1, 1.5, 1.5, 2])
h1.caption("Publish date")
h2.caption("Blog title")
h3.caption("Blog")
h4.caption("Instagram")
h5.caption("Tag")
h6.caption("Source")
st.divider()

# ── Scrollable blog list ──────────────────────────────────────
with st.container(height=500):
    for i, item in enumerate(page_items):
        real_idx = results.index(item)
        publish  = item.get("Publish_Date") or item.get("Blog_PublishDate") or item.get("Run_Timestamp", "—")
        title    = item.get("blog", {}).get("Blog_Title", "") or item.get("Blog_Title", "—")
        tag      = item.get("image_text", {}).get("tag", "GENERAL")
        link     = item.get("Blog_Link") or item.get("Blog_Links", "—")

        try:
            domain = urlparse(link).netloc.replace("www.", "")
        except:
            domain = link[:30] if link else "—"

        c1, c2, c3, c4, c5, c6 = st.columns([2, 4, 1, 1.5, 1.5, 2])
        c1.caption(publish[:16] if publish else "—")
        c2.write(f"**{title[:80]}**" if len(title) > 80 else f"**{title}**")

        if c3.button("Read", key=f"blog_{real_idx}"):
            st.session_state.selected_blog  = real_idx
            st.session_state.selected_insta = None

        if c4.button("📸 Insta", key=f"insta_{real_idx}"):
            st.session_state.selected_insta = real_idx
            st.session_state.selected_blog  = None

        c5.write(f"`{tag}`")
        c6.markdown(f"[{domain}]({link})")
        st.divider()


# ── Blog Detail ───────────────────────────────────────────────
if st.session_state.selected_blog is not None:
    idx  = st.session_state.selected_blog
    item = results[idx]
    blog = item.get("blog", {})

    st.subheader("Blog detail")
    m1, m2, m3 = st.columns(3)
    m1.markdown(f"**Tag:** `{item.get('image_text', {}).get('tag', 'GENERAL')}`")
    m2.markdown(f"**Country:** `{DEFAULT_COUNTRY}`")
    m3.markdown(f"**Generated:** `{item.get('Run_Timestamp', '—')}`")

    link = item.get("Blog_Link") or item.get("Blog_Links", "")
    if link:
        st.markdown(f"[Read original source ↗]({link})")
    st.divider()

    # ── Extract all blog fields ───────────────────────────────
    ai_title   = blog.get("Blog_Title", "") or item.get("Blog_Title", "")
    meta_title = blog.get("Meta_Title", "")
    meta_desc  = blog.get("Meta_Description", "")
    faq_schema = blog.get("FAQ_Schema", {})
    faqs       = faq_schema.get("mainEntity", [])
    faq_jsonld = json.dumps(faq_schema, indent=2, ensure_ascii=False) if faq_schema else ""
    tldr       = blog.get("TLDR", [])
    blog_html  = blog.get("Blog_Content", "")
    conclusion = blog.get("Conclusion", "")

    # ── Clean blog HTML (strips FAQ from Blog_Content) ────────
    blog_html_clean = clean_blog_html(blog_html)

    # ══════════════════════════════════════════════════════════
    # SECTION 1 — BLOG TITLE (separate copyable)
    # ══════════════════════════════════════════════════════════
    copy_row("1. Blog Title", ai_title, key=f"cp_title_{idx}")
    st.divider()

    # ══════════════════════════════════════════════════════════
    # SECTION 2 — SEO DATA (single copyable box)
    # Meta Title + Meta Description + JSON-LD FAQ Schema
    # ══════════════════════════════════════════════════════════
    st.markdown("**2. SEO Data**")
    st.markdown(
        """
        <div style="
            border: 1.5px solid #1A56DB;
            border-radius: 8px;
            padding: 12px 16px 4px 16px;
            background: #f0f4ff;
            margin-bottom: 8px;
        ">
            <span style="font-size:12px;color:#1A56DB;font-weight:600;">
                SEO — Meta Title · Meta Description · JSON-LD FAQ Schema
            </span>
        </div>
        """,
        unsafe_allow_html=True
    )

    if meta_title:
        char_count = len(meta_title)
        color = "green" if char_count <= 60 else "red"
        st.markdown(
            f"Meta Title &nbsp; <span style='color:{color};font-size:12px'>{char_count}/60 chars</span>",
            unsafe_allow_html=True
        )
    if meta_desc:
        char_count = len(meta_desc)
        color = "green" if char_count <= 160 else "red"
        st.markdown(
            f"Meta Description &nbsp; <span style='color:{color};font-size:12px'>{char_count}/160 chars</span>",
            unsafe_allow_html=True
        )

    seo_combined = ""
    if meta_title:
        seo_combined += f"META TITLE:\n{meta_title}\n\n"
    if meta_desc:
        seo_combined += f"META DESCRIPTION:\n{meta_desc}\n\n"
    if faq_jsonld:
        seo_combined += f"JSON-LD FAQ SCHEMA:\n{faq_jsonld}"

    if seo_combined:
        st.text_area(
            label            = "SEO combined",
            value            = seo_combined,
            height           = 300,
            key              = f"cp_seo_combined_{idx}",
            label_visibility = "collapsed"
        )
    st.divider()

    # ══════════════════════════════════════════════════════════
    # SECTION 3 — BLOG CONTENT BOX
    # Format:
    #   <h1> Blog Title (once only)
    #   <h2> TLDR + <ul><li>           ← from blog.TLDR
    #   Blog Content HTML               ← cleaned (no title, no key takeaways,
    #                                      no faq h2/h4/p, no conclusion, no cta)
    #   <h2> FAQ + <h3>Q <p>A          ← from blog.FAQ_Schema.mainEntity (clean source)
    #   <h2> Conclusion + <p>           ← from blog.Conclusion
    # Two boxes: copyable text + rendered HTML preview
    # ══════════════════════════════════════════════════════════
    st.markdown("**3. Blog Content**")
    st.markdown(
        """
        <div style="
            border: 1.5px solid #10B981;
            border-radius: 8px;
            padding: 12px 16px 4px 16px;
            background: #f0fff8;
            margin-bottom: 8px;
        ">
            <span style="font-size:12px;color:#10B981;font-weight:600;">
                Blog Title · TLDR · Blog Content · FAQ · Conclusion — HTML Format
            </span>
        </div>
        """,
        unsafe_allow_html=True
    )

    blog_combined = ""

    # ── 1. Blog Title — once only ─────────────────────────────
    if ai_title:
        blog_combined += f"<h1>{ai_title}</h1>\n\n"

    # ── 2. TLDR ───────────────────────────────────────────────
    if tldr:
        blog_combined += "<h2>TLDR</h2>\n<ul>\n"
        blog_combined += "\n".join(f"<li>{t}</li>" for t in tldr)
        blog_combined += "\n</ul>\n\n"

    # ── 3. Blog Content HTML (cleaned — no FAQ/Conclusion inside) ──
    if blog_html_clean:
        blog_combined += blog_html_clean
        blog_combined += "\n\n"

    # ── 4. FAQ — appended from FAQ_Schema.mainEntity only ─────
    if faqs:
        blog_combined += "<h2>Frequently Asked Questions</h2>\n"
        for faq in faqs:
            q = faq.get("name", "")
            a = faq.get("acceptedAnswer", {}).get("text", "")
            blog_combined += f"<h3>{q}</h3>\n<p>{a}</p>\n\n"

    # ── 5. Conclusion ─────────────────────────────────────────
    if conclusion:
        blog_combined += "<h2>Conclusion</h2>\n"
        blog_combined += f"<p>{conclusion}</p>\n\n"

    if blog_combined:
        blog_combined = re.sub(r'<div[^>]*>',    '', blog_combined)
        blog_combined = re.sub(r'</div>',          '', blog_combined)
        blog_combined = re.sub(r'<section[^>]*>', '', blog_combined)
        blog_combined = re.sub(r'</section>',      '', blog_combined)
        blog_combined = re.sub(r'<article[^>]*>', '', blog_combined)
        blog_combined = re.sub(r'</article>',      '', blog_combined)
        blog_combined = re.sub(r'\n{3,}', '\n\n', blog_combined)
        blog_combined = blog_combined.strip()

        # ── Copyable text area ────────────────────────────────
        st.text_area(
            label            = "Blog content combined",
            value            = blog_combined,
            height           = 400,
            key              = f"cp_blog_combined_{idx}",
            label_visibility = "collapsed"
        )

        # ── Rendered HTML preview ─────────────────────────────
        st.markdown("**Preview**")
        st.markdown(
            f"""
            <div style="
                height: 500px;
                overflow-y: auto;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 24px 28px;
                background-color: #ffffff;
                font-size: 15px;
                line-height: 1.8;
                color: #1a1a1a;
                font-family: Arial, sans-serif;
            ">
                {blog_combined}
            </div>
            """,
            unsafe_allow_html=True
        )

    st.divider()

    # ══════════════════════════════════════════════════════════
    # SECTION 4 — BLOG NOTIFICATION (separate copyable)
    # ══════════════════════════════════════════════════════════
    notify_text = item.get("notify", {}).get("blog_notify", "")
    if notify_text:
        copy_row("4. Blog Notification", notify_text, key=f"cp_notify_{idx}")
        st.divider()

    # ══════════════════════════════════════════════════════════
    # SECTION 5 — IMAGES
    # ══════════════════════════════════════════════════════════
    st.markdown("**5. Images**")

    show_image_section(
        label         = "Blog Thumbnail Outer (640×480)",
        image_field   = item.get("blog_image_outer") or item.get("blog_image"),
        display_width = 640,
        idx           = idx,
        key_prefix    = "blog_outer"
    )
    st.divider()

    if item.get("blog_image_inner"):
        show_image_section(
            label         = "Blog Thumbnail Inner (1920×490)",
            image_field   = item.get("blog_image_inner"),
            display_width = 700,
            idx           = idx,
            key_prefix    = "blog_inner"
        )
        st.divider()

    # ── CTA — show URL link only, no label ───────────────────
    cta = blog.get("CTA")
    if cta:
        cta_url = (
            cta.get("url", "https://trade.swastika.co.in/")
            if isinstance(cta, dict)
            else (cta if str(cta).startswith("http") else "https://trade.swastika.co.in/")
        )
        st.markdown(f"[{cta_url}]({cta_url})")


# ── Instagram Detail ──────────────────────────────────────────
if st.session_state.selected_insta is not None:
    idx  = st.session_state.selected_insta
    item = results[idx]

    st.subheader("Instagram detail")

    insta_data = item.get("instagram_notify", {})
    caption    = insta_data.get("instagram_caption", "No caption found.")
    hashtags   = insta_data.get("hashtags", "")

    copy_row("Caption", caption, key=f"cp_insta_caption_{idx}")

    if hashtags:
        st.divider()
        copy_row("Hashtags", hashtags, key=f"cp_insta_hashtags_{idx}")

    st.divider()

    show_image_section(
        label         = "Instagram Image (1080×1080)",
        image_field   = item.get("instagram_image"),
        display_width = 540,
        idx           = idx,
        key_prefix    = "insta"
    )
# import streamlit as st
# from bs4 import BeautifulSoup
# import os
# import re
# from urllib.parse import urlparse
# import json

# st.set_page_config(layout="wide", page_title="Swastika Blog Dashboard")

# DEFAULT_COUNTRY  = "India"
# DEFAULT_CATEGORY = "finance"


# def copy_row(label: str, text: str, key: str = ""):
#     st.markdown(f"**{label}**")
#     st.text_area(
#         label            = label,
#         value            = text,
#         height           = min(150, 35 + text.count('\n') * 20),
#         key              = key,
#         label_visibility = "collapsed"
#     )


# def download_image_btn(image_path: str, filename: str, label: str = "Download", unique_key: str = ""):
#     if image_path and os.path.exists(image_path):
#         ext  = os.path.splitext(filename)[1].lower()
#         mime = "image/webp" if ext == ".webp" else "image/jpeg"
#         with open(image_path, "rb") as f:
#             img_bytes = f.read()
#         st.download_button(
#             label     = label,
#             data      = img_bytes,
#             file_name = filename,
#             mime      = mime,
#             key       = f"dl_{unique_key}_{filename}"
#         )
#     else:
#         st.caption("Image not available for download.")


# def get_image_path(image_field, prefer: str = "webp") -> str:
#     if isinstance(image_field, dict):
#         if prefer == "webp" and image_field.get("webp"):
#             return image_field["webp"]
#         return image_field.get("jpg", "")
#     return image_field or ""


# # def clean_blog_html(blog_html: str) -> str:
# #     """
# #     Cleans blog HTML:
# #     - Removes first <h1> (duplicate title)
# #     - Removes ALL div/section/article tags including stray closing tags
# #     - Keeps only allowed tags: h1-h4, p, ul, ol, li, strong, em, br, a, span
# #     """
# #     if not blog_html:
# #         return ""

# #     allowed_tags = ["h1", "h2", "h3", "h4", "p", "ul", "ol",
# #                     "li", "strong", "em", "br", "a", "span"]

# #     soup = BeautifulSoup(blog_html, "html.parser")

# #     # ── Remove first h1 (duplicate title) ────────────────────
# #     first_h1 = soup.find("h1")
# #     if first_h1:
# #         first_h1.decompose()

# #     # ── Unwrap all tags not in allowed list ───────────────────
# #     for tag in soup.find_all(True):
# #         if tag.name not in allowed_tags:
# #             tag.unwrap()

# #     cleaned = str(soup)

# #     # ── Remove stray div tags (opening + closing) ─────────────
# #     cleaned = re.sub(r'<div[^>]*>', '', cleaned)
# #     cleaned = re.sub(r'</div>',     '', cleaned)

# #     # ── Remove stray section/article tags ─────────────────────
# #     cleaned = re.sub(r'<section[^>]*>', '', cleaned)
# #     cleaned = re.sub(r'</section>',     '', cleaned)
# #     cleaned = re.sub(r'<article[^>]*>', '', cleaned)
# #     cleaned = re.sub(r'</article>',     '', cleaned)

# #     # ── Clean up extra blank lines ────────────────────────────
# #     cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)

# #     return cleaned.strip()
# def clean_blog_html(blog_html: str) -> str:
#     """
#     Cleans blog HTML:
#     - Removes first <h1> (duplicate title)
#     - Removes Conclusion section (added separately at end)
#     - Removes FAQ section (added separately at end)
#     - Removes ALL div/section/article stray tags
#     - Keeps only allowed tags: h1-h4, p, ul, ol, li, strong, em, br, a, span
#     """
#     if not blog_html:
#         return ""

#     allowed_tags = ["h1", "h2", "h3", "h4", "p", "ul", "ol",
#                     "li", "strong", "em", "br", "a", "span"]

#     soup = BeautifulSoup(blog_html, "html.parser")

#     # ── Remove first h1 (duplicate title) ────────────────────
#     first_h1 = soup.find("h1")
#     if first_h1:
#         first_h1.decompose()

#     # ── Remove Conclusion + FAQ h2 sections ──────────────────
#     # These are added separately at end — remove from blog_html
#     for h2 in soup.find_all("h2"):
#         h2_text = h2.get_text().strip().lower()
#         if any(keyword in h2_text for keyword in [
#             "conclusion", "faq", "frequently asked", "faq details"
#         ]):
#             # Remove all sibling nodes until next h2
#             current = h2.next_sibling
#             while current and not (
#                 hasattr(current, 'name') and current.name == 'h2'
#             ):
#                 next_node = current.next_sibling
#                 if hasattr(current, 'decompose'):
#                     current.decompose()
#                 current = next_node
#             h2.decompose()

#     # ── Unwrap all tags not in allowed list ───────────────────
#     for tag in soup.find_all(True):
#         if tag.name not in allowed_tags:
#             tag.unwrap()

#     cleaned = str(soup)

#     # ── Remove stray div tags (opening + closing) ─────────────
#     cleaned = re.sub(r'<div[^>]*>',    '', cleaned)
#     cleaned = re.sub(r'</div>',         '', cleaned)
#     cleaned = re.sub(r'<section[^>]*>', '', cleaned)
#     cleaned = re.sub(r'</section>',     '', cleaned)
#     cleaned = re.sub(r'<article[^>]*>', '', cleaned)
#     cleaned = re.sub(r'</article>',     '', cleaned)

#     # ── Clean up extra blank lines ────────────────────────────
#     cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)

#     return cleaned.strip()

# def show_image_section(label: str, image_field, display_width: int, idx: int, key_prefix: str):
#     st.markdown(f"**{label}**")
#     webp_path = get_image_path(image_field, prefer="webp")
#     jpg_path  = get_image_path(image_field, prefer="jpg")

#     if webp_path and os.path.exists(webp_path):
#         st.image(webp_path, width=display_width)
#         col1, col2 = st.columns(2)
#         with col1:
#             download_image_btn(
#                 webp_path,
#                 os.path.basename(webp_path),
#                 "⬇ Download WebP",
#                 unique_key=f"{key_prefix}_webp_{idx}"
#             )
#         with col2:
#             download_image_btn(
#                 jpg_path,
#                 os.path.basename(jpg_path),
#                 "⬇ Download JPG",
#                 unique_key=f"{key_prefix}_jpg_{idx}"
#             )
#     elif jpg_path and os.path.exists(jpg_path):
#         st.image(jpg_path, width=display_width)
#         download_image_btn(
#             jpg_path,
#             os.path.basename(jpg_path),
#             "⬇ Download JPG",
#             unique_key=f"{key_prefix}_jpg_only_{idx}"
#         )
#     else:
#         st.warning(f"{label} not available.")


# st.title("Blog Dashboard")
# st.caption(f"Country: {DEFAULT_COUNTRY}  ·  Category: {DEFAULT_CATEGORY.capitalize()}")

# # ── Set same as mergeall_engine.py ───────────────────────────
# USE_AI_IMAGES = False
# OUTPUT_FILE   = "testing_webp_output.json" if USE_AI_IMAGES else "output.json"


# @st.cache_data(show_spinner="Loading blogs...", ttl=60)
# def load_data():
#     path = f"output/{OUTPUT_FILE}"
#     if not os.path.exists(path):
#         return []
#     with open(path, "r", encoding="utf-8") as f:
#         try:
#             return json.load(f)
#         except:
#             return []


# output  = load_data()
# results = output if isinstance(output, list) else output.get("results", [])

# if st.button("Refresh data"):
#     st.cache_data.clear()
#     st.rerun()

# for key in ["selected_blog", "selected_insta", "page"]:
#     if key not in st.session_state:
#         st.session_state[key] = None if key != "page" else 1

# if not results:
#     st.warning("No blogs returned.")
#     st.stop()

# m1, m2, m3, m4 = st.columns(4)
# m1.metric("Total blogs",  len(results))
# m2.metric("Country",      DEFAULT_COUNTRY)
# m3.metric("Category",     DEFAULT_CATEGORY.capitalize())
# m4.metric("Sources", len(set(
#     urlparse(r.get("Blog_Link") or r.get("Blog_Links", "")).netloc
#     for r in results
# )))

# st.divider()

# sc, ss = st.columns([4, 1])
# search = sc.text_input("Search", placeholder="Search title or content...", label_visibility="collapsed")
# sort   = ss.selectbox("Sort", ["Newest first", "Oldest first", "A to Z"], label_visibility="collapsed")

# filtered = results
# if search:
#     q = search.lower()
#     filtered = [
#         r for r in results
#         if q in r.get("Blog_Title", "").lower()
#         or q in r.get("blog", {}).get("Blog_Title", "").lower()
#         or q in r.get("Blog_Content", "").lower()
#     ]
#     st.session_state.page = 1

# if sort == "Newest first":
#     filtered = sorted(filtered, key=lambda x: x.get("Publish_Date") or x.get("Blog_PublishDate") or x.get("Run_Timestamp", ""), reverse=True)
# elif sort == "Oldest first":
#     filtered = sorted(filtered, key=lambda x: x.get("Publish_Date") or x.get("Blog_PublishDate") or x.get("Run_Timestamp", ""))
# else:
#     filtered = sorted(filtered, key=lambda x: x.get("blog", {}).get("Blog_Title", "") or x.get("Blog_Title", ""))

# if not filtered:
#     st.info("No blogs match your search.")
#     st.stop()

# # ── Pagination ────────────────────────────────────────────────
# PAGE_SIZE = 20
# total     = len(filtered)
# max_page  = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)

# if st.session_state.page > max_page:
#     st.session_state.page = 1

# p1, p2, p3 = st.columns([1, 2, 1])
# with p1:
#     if st.button("← Prev") and st.session_state.page > 1:
#         st.session_state.page -= 1
#         st.rerun()
# with p2:
#     st.caption(f"Page {st.session_state.page} of {max_page}  ·  {total} blogs")
# with p3:
#     if st.button("Next →") and st.session_state.page < max_page:
#         st.session_state.page += 1
#         st.rerun()

# start      = (st.session_state.page - 1) * PAGE_SIZE
# end        = start + PAGE_SIZE
# page_items = filtered[start:end]

# # ── Header ───────────────────────────────────────────────────
# h1, h2, h3, h4, h5, h6 = st.columns([2, 4, 1, 1.5, 1.5, 2])
# h1.caption("Publish date")
# h2.caption("Blog title")
# h3.caption("Blog")
# h4.caption("Instagram")
# h5.caption("Tag")
# h6.caption("Source")
# st.divider()

# # ── Scrollable blog list ──────────────────────────────────────
# with st.container(height=500):
#     for i, item in enumerate(page_items):
#         real_idx = results.index(item)
#         publish  = item.get("Publish_Date") or item.get("Blog_PublishDate") or item.get("Run_Timestamp", "—")
#         title    = item.get("blog", {}).get("Blog_Title", "") or item.get("Blog_Title", "—")
#         tag      = item.get("image_text", {}).get("tag", "GENERAL")
#         link     = item.get("Blog_Link") or item.get("Blog_Links", "—")

#         try:
#             domain = urlparse(link).netloc.replace("www.", "")
#         except:
#             domain = link[:30] if link else "—"

#         c1, c2, c3, c4, c5, c6 = st.columns([2, 4, 1, 1.5, 1.5, 2])
#         c1.caption(publish[:16] if publish else "—")
#         c2.write(f"**{title[:80]}**" if len(title) > 80 else f"**{title}**")

#         if c3.button("Read", key=f"blog_{real_idx}"):
#             st.session_state.selected_blog  = real_idx
#             st.session_state.selected_insta = None

#         if c4.button("📸 Insta", key=f"insta_{real_idx}"):
#             st.session_state.selected_insta = real_idx
#             st.session_state.selected_blog  = None

#         c5.write(f"`{tag}`")
#         c6.markdown(f"[{domain}]({link})")
#         st.divider()


# # ── Blog Detail ───────────────────────────────────────────────
# if st.session_state.selected_blog is not None:
#     idx  = st.session_state.selected_blog
#     item = results[idx]
#     blog = item.get("blog", {})

#     st.subheader("Blog detail")
#     m1, m2, m3 = st.columns(3)
#     m1.markdown(f"**Tag:** `{item.get('image_text', {}).get('tag', 'GENERAL')}`")
#     m2.markdown(f"**Country:** `{DEFAULT_COUNTRY}`")
#     m3.markdown(f"**Generated:** `{item.get('Run_Timestamp', '—')}`")

#     link = item.get("Blog_Link") or item.get("Blog_Links", "")
#     if link:
#         st.markdown(f"[Read original source ↗]({link})")
#     st.divider()

#     # ── Extract all blog fields ───────────────────────────────
#     ai_title   = blog.get("Blog_Title", "") or item.get("Blog_Title", "")
#     meta_title = blog.get("Meta_Title", "")
#     meta_desc  = blog.get("Meta_Description", "")
#     faq_schema = blog.get("FAQ_Schema", {})
#     faqs       = faq_schema.get("mainEntity", [])
#     faq_jsonld = json.dumps(faq_schema, indent=2, ensure_ascii=False) if faq_schema else ""
#     tldr       = blog.get("TLDR", [])
#     blog_html  = blog.get("Blog_Content", "")
#     conclusion = blog.get("Conclusion", "")

#     # ── Clean blog HTML ───────────────────────────────────────
#     blog_html_clean = clean_blog_html(blog_html)

#     # ══════════════════════════════════════════════════════════
#     # SECTION 1 — BLOG TITLE (separate copyable)
#     # ══════════════════════════════════════════════════════════
#     copy_row("1. Blog Title", ai_title, key=f"cp_title_{idx}")
#     st.divider()

#     # ══════════════════════════════════════════════════════════
#     # SECTION 2 — SEO DATA (single copyable box)
#     # Meta Title + Meta Description + JSON-LD FAQ Schema
#     # ══════════════════════════════════════════════════════════
#     st.markdown("**2. SEO Data**")
#     st.markdown(
#         """
#         <div style="
#             border: 1.5px solid #1A56DB;
#             border-radius: 8px;
#             padding: 12px 16px 4px 16px;
#             background: #f0f4ff;
#             margin-bottom: 8px;
#         ">
#             <span style="font-size:12px;color:#1A56DB;font-weight:600;">
#                 SEO — Meta Title · Meta Description · JSON-LD FAQ Schema
#             </span>
#         </div>
#         """,
#         unsafe_allow_html=True
#     )

#     if meta_title:
#         char_count = len(meta_title)
#         color = "green" if char_count <= 60 else "red"
#         st.markdown(
#             f"Meta Title &nbsp; <span style='color:{color};font-size:12px'>{char_count}/60 chars</span>",
#             unsafe_allow_html=True
#         )
#     if meta_desc:
#         char_count = len(meta_desc)
#         color = "green" if char_count <= 160 else "red"
#         st.markdown(
#             f"Meta Description &nbsp; <span style='color:{color};font-size:12px'>{char_count}/160 chars</span>",
#             unsafe_allow_html=True
#         )

#     seo_combined = ""
#     if meta_title:
#         seo_combined += f"META TITLE:\n{meta_title}\n\n"
#     if meta_desc:
#         seo_combined += f"META DESCRIPTION:\n{meta_desc}\n\n"
#     if faq_jsonld:
#         seo_combined += f"JSON-LD FAQ SCHEMA:\n{faq_jsonld}"

#     if seo_combined:
#         st.text_area(
#             label            = "SEO combined",
#             value            = seo_combined,
#             height           = 300,
#             key              = f"cp_seo_combined_{idx}",
#             label_visibility = "collapsed"
#         )
#     st.divider()

#     # ══════════════════════════════════════════════════════════
#     # SECTION 3 — BLOG CONTENT BOX
#     # Format:
#     #   <h1> Blog Title (once only)
#     #   <h2> Key Takeaways + <ul><li>
#     #   Blog Content HTML (h1 stripped, stray tags removed)
#     #   <h2> FAQ Details + <h3>Q + <p>A
#     #   <h2> Conclusion + <p>
#     # Two boxes: copyable text + rendered HTML preview
#     # ══════════════════════════════════════════════════════════
#     st.markdown("**3. Blog Content**")
#     st.markdown(
#         """
#         <div style="
#             border: 1.5px solid #10B981;
#             border-radius: 8px;
#             padding: 12px 16px 4px 16px;
#             background: #f0fff8;
#             margin-bottom: 8px;
#         ">
#             <span style="font-size:12px;color:#10B981;font-weight:600;">
#                 Blog Title · Key Takeaways · Blog Content · FAQ Details · Conclusion — HTML Format
#             </span>
#         </div>
#         """,
#         unsafe_allow_html=True
#     )

#     blog_combined = ""

#     # ── 1. Blog Title — once only ─────────────────────────────
#     if ai_title:
#         blog_combined += f"<h1>{ai_title}</h1>\n\n"

#     # ── 2. Key Takeaways ──────────────────────────────────────
#     if tldr:
#         blog_combined += "<h2>Key Takeaways</h2>\n<ul>\n"
#         blog_combined += "\n".join(f"<li>{t}</li>" for t in tldr)
#         blog_combined += "\n</ul>\n\n"

#     # ── 3. Blog Content HTML (cleaned) ───────────────────────
#     if blog_html_clean:
#         blog_combined += blog_html_clean
#         blog_combined += "\n\n"

#     # ── 4. FAQ Details ────────────────────────────────────────
#     if faqs:
#         blog_combined += "<h2>FAQ Details</h2>\n"
#         for faq in faqs:
#             q = faq.get("name", "")
#             a = faq.get("acceptedAnswer", {}).get("text", "")
#             blog_combined += f"<h3>{q}</h3>\n<p>{a}</p>\n\n"

#     # ── 5. Conclusion ─────────────────────────────────────────
#     if conclusion:
#         blog_combined += "<h2>Conclusion</h2>\n"
#         blog_combined += f"<p>{conclusion}</p>\n\n"

#     if blog_combined:
#         blog_combined = re.sub(r'<div[^>]*>',  '', blog_combined)
#         blog_combined = re.sub(r'</div>',       '', blog_combined)
#         blog_combined = re.sub(r'<section[^>]*>', '', blog_combined)
#         blog_combined = re.sub(r'</section>',   '', blog_combined)
#         blog_combined = re.sub(r'<article[^>]*>', '', blog_combined)
#         blog_combined = re.sub(r'</article>',   '', blog_combined)
#         blog_combined = re.sub(r'\n{3,}', '\n\n', blog_combined)
#         blog_combined = blog_combined.strip()

#         # ── Copyable text area ────────────────────────────────
#         st.text_area(
#             label            = "Blog content combined",
#             value            = blog_combined,
#             height           = 400,
#             key              = f"cp_blog_combined_{idx}",
#             label_visibility = "collapsed"
#         )

#         # ── Rendered HTML preview ─────────────────────────────
#         st.markdown("**Preview**")
#         st.markdown(
#             f"""
#             <div style="
#                 height: 500px;
#                 overflow-y: auto;
#                 border: 1px solid #e0e0e0;
#                 border-radius: 8px;
#                 padding: 24px 28px;
#                 background-color: #ffffff;
#                 font-size: 15px;
#                 line-height: 1.8;
#                 color: #1a1a1a;
#                 font-family: Arial, sans-serif;
#             ">
#                 {blog_combined}
#             </div>
#             """,
#             unsafe_allow_html=True
#         )

#     st.divider()

#     # ══════════════════════════════════════════════════════════
#     # SECTION 4 — BLOG NOTIFICATION (separate copyable)
#     # ══════════════════════════════════════════════════════════
#     notify_text = item.get("notify", {}).get("blog_notify", "")
#     if notify_text:
#         copy_row("4. Blog Notification", notify_text, key=f"cp_notify_{idx}")
#         st.divider()

#     # ══════════════════════════════════════════════════════════
#     # SECTION 5 — IMAGES
#     # ══════════════════════════════════════════════════════════
#     st.markdown("**5. Images**")

#     show_image_section(
#         label         = "Blog Thumbnail Outer (640×480)",
#         image_field   = item.get("blog_image_outer") or item.get("blog_image"),
#         display_width = 640,
#         idx           = idx,
#         key_prefix    = "blog_outer"
#     )
#     st.divider()

#     if item.get("blog_image_inner"):
#         show_image_section(
#             label         = "Blog Thumbnail Inner (1920×490)",
#             image_field   = item.get("blog_image_inner"),
#             display_width = 700,
#             idx           = idx,
#             key_prefix    = "blog_inner"
#         )
#         st.divider()

#     cta = blog.get("CTA")
#     if cta:
#         if isinstance(cta, dict):
#             cta_text = cta.get("text", "Trade on Swastika ↗")
#             cta_url  = cta.get("url",  "https://trade.swastika.co.in/")
#         else:
#             cta_text = "Trade on Swastika ↗"
#             cta_url  = cta if str(cta).startswith("http") else "https://trade.swastika.co.in/"
#         st.link_button(cta_text, cta_url)


# # ── Instagram Detail ──────────────────────────────────────────
# if st.session_state.selected_insta is not None:
#     idx  = st.session_state.selected_insta
#     item = results[idx]

#     st.subheader("Instagram detail")

#     insta_data = item.get("instagram_notify", {})
#     caption    = insta_data.get("instagram_caption", "No caption found.")
#     hashtags   = insta_data.get("hashtags", "")

#     copy_row("Caption", caption, key=f"cp_insta_caption_{idx}")

#     if hashtags:
#         st.divider()
#         copy_row("Hashtags", hashtags, key=f"cp_insta_hashtags_{idx}")

#     st.divider()

#     show_image_section(
#         label         = "Instagram Image (1080×1080)",
#         image_field   = item.get("instagram_image"),
#         display_width = 540,
#         idx           = idx,
#         key_prefix    = "insta"
#     )




















# note this is latest code changes___________________
# import streamlit as st
# from bs4 import BeautifulSoup
# import os
# from urllib.parse import urlparse
# import json

# st.set_page_config(layout="wide", page_title="Swastika Blog Dashboard")

# DEFAULT_COUNTRY  = "India"
# DEFAULT_CATEGORY = "finance"


# def copy_row(label: str, text: str, key: str = ""):
#     st.markdown(f"**{label}**")
#     st.text_area(
#         label            = label,
#         value            = text,
#         height           = min(150, 35 + text.count('\n') * 20),
#         key              = key,
#         label_visibility = "collapsed"
#     )


# def download_image_btn(image_path: str, filename: str, label: str = "Download", unique_key: str = ""):
#     if image_path and os.path.exists(image_path):
#         ext  = os.path.splitext(filename)[1].lower()
#         mime = "image/webp" if ext == ".webp" else "image/jpeg"
#         with open(image_path, "rb") as f:
#             img_bytes = f.read()
#         st.download_button(
#             label     = label,
#             data      = img_bytes,
#             file_name = filename,
#             mime      = mime,
#             key       = f"dl_{unique_key}_{filename}"
#         )
#     else:
#         st.caption("Image not available for download.")


# def get_image_path(image_field, prefer: str = "webp") -> str:
#     if isinstance(image_field, dict):
#         if prefer == "webp" and image_field.get("webp"):
#             return image_field["webp"]
#         return image_field.get("jpg", "")
#     return image_field or ""


# def render_blog_in_box(html_content: str):
#     st.markdown(
#         f"""
#         <div style="
#             height: 400px;
#             overflow-y: auto;
#             border: 1px solid #e0e0e0;
#             border-radius: 8px;
#             padding: 16px 20px;
#             background-color: #fafafa;
#             font-size: 15px;
#             line-height: 1.8;
#             color: #333;
#         ">{html_content}</div>
#         """,
#         unsafe_allow_html=True
#     )


# def show_image_section(label: str, image_field, display_width: int, idx: int, key_prefix: str):
#     st.markdown(f"**{label}**")
#     webp_path = get_image_path(image_field, prefer="webp")
#     jpg_path  = get_image_path(image_field, prefer="jpg")

#     if webp_path and os.path.exists(webp_path):
#         st.image(webp_path, width=display_width)
#         col1, col2 = st.columns(2)
#         with col1:
#             download_image_btn(
#                 webp_path,
#                 os.path.basename(webp_path),
#                 "⬇ Download WebP",
#                 unique_key=f"{key_prefix}_webp_{idx}"
#             )
#         with col2:
#             download_image_btn(
#                 jpg_path,
#                 os.path.basename(jpg_path),
#                 "⬇ Download JPG",
#                 unique_key=f"{key_prefix}_jpg_{idx}"
#             )
#     elif jpg_path and os.path.exists(jpg_path):
#         st.image(jpg_path, width=display_width)
#         download_image_btn(
#             jpg_path,
#             os.path.basename(jpg_path),
#             "⬇ Download JPG",
#             unique_key=f"{key_prefix}_jpg_only_{idx}"
#         )
#     else:
#         st.warning(f"{label} not available.")


# st.title("Blog Dashboard")
# st.caption(f"Country: {DEFAULT_COUNTRY}  ·  Category: {DEFAULT_CATEGORY.capitalize()}")


# @st.cache_data(show_spinner="Loading blogs...", ttl=60)
# def load_data():
#     path = "output/testing_webp_output.json"
#     if not os.path.exists(path):
#         return []
#     with open(path, "r", encoding="utf-8") as f:
#         try:
#             return json.load(f)
#         except:
#             return []


# output  = load_data()
# results = output.get("results", []) if isinstance(output, dict) else output

# if st.button("Refresh data"):
#     st.cache_data.clear()
#     st.rerun()

# for key in ["selected_blog", "selected_insta", "page"]:
#     if key not in st.session_state:
#         st.session_state[key] = None if key != "page" else 1

# if not results:
#     st.warning("No blogs returned.")
#     st.stop()

# m1, m2, m3, m4 = st.columns(4)
# m1.metric("Total blogs",  len(results))
# m2.metric("Country",      DEFAULT_COUNTRY)
# m3.metric("Category",     DEFAULT_CATEGORY.capitalize())
# m4.metric("Sources", len(set(
#     urlparse(r.get("Blog_Link") or r.get("Blog_Links", "")).netloc
#     for r in results
# )))

# st.divider()

# sc, ss = st.columns([4, 1])
# search = sc.text_input("Search", placeholder="Search title or content...", label_visibility="collapsed")
# sort   = ss.selectbox("Sort", ["Newest first", "Oldest first", "A to Z"], label_visibility="collapsed")

# filtered = results
# if search:
#     q = search.lower()
#     filtered = [
#         r for r in results
#         if q in r.get("Blog_Title", "").lower()
#         or q in r.get("blog", {}).get("Blog_Title", "").lower()
#         or q in r.get("Blog_Content", "").lower()
#     ]
#     st.session_state.page = 1

# if sort == "Newest first":
#     filtered = sorted(filtered, key=lambda x: x.get("Publish_Date") or x.get("Blog_PublishDate") or x.get("Run_Timestamp", ""), reverse=True)
# elif sort == "Oldest first":
#     filtered = sorted(filtered, key=lambda x: x.get("Publish_Date") or x.get("Blog_PublishDate") or x.get("Run_Timestamp", ""))
# else:
#     filtered = sorted(filtered, key=lambda x: x.get("blog", {}).get("Blog_Title", "") or x.get("Blog_Title", ""))

# if not filtered:
#     st.info("No blogs match your search.")
#     st.stop()

# # ── Pagination ────────────────────────────────────────────────
# PAGE_SIZE = 20
# total     = len(filtered)
# max_page  = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)

# if st.session_state.page > max_page:
#     st.session_state.page = 1

# p1, p2, p3 = st.columns([1, 2, 1])
# with p1:
#     if st.button("← Prev") and st.session_state.page > 1:
#         st.session_state.page -= 1
#         st.rerun()
# with p2:
#     st.caption(f"Page {st.session_state.page} of {max_page}  ·  {total} blogs")
# with p3:
#     if st.button("Next →") and st.session_state.page < max_page:
#         st.session_state.page += 1
#         st.rerun()

# start      = (st.session_state.page - 1) * PAGE_SIZE
# end        = start + PAGE_SIZE
# page_items = filtered[start:end]

# # ── Header ───────────────────────────────────────────────────
# h1, h2, h3, h4, h5, h6 = st.columns([2, 4, 1, 1.5, 1.5, 2])
# h1.caption("Publish date")
# h2.caption("Blog title")
# h3.caption("Blog")
# h4.caption("Instagram")
# h5.caption("Tag")
# h6.caption("Source")
# st.divider()

# # ── Scrollable blog list ──────────────────────────────────────
# with st.container(height=500):
#     for i, item in enumerate(page_items):
#         real_idx = results.index(item)
#         publish  = item.get("Publish_Date") or item.get("Blog_PublishDate") or item.get("Run_Timestamp", "—")

#         # ── CHANGE 1 — show AI generated title in list ────────
#         title = item.get("blog", {}).get("Blog_Title", "") or item.get("Blog_Title", "—")

#         tag   = item.get("image_text", {}).get("tag", "GENERAL")
#         link  = item.get("Blog_Link") or item.get("Blog_Links", "—")

#         try:
#             domain = urlparse(link).netloc.replace("www.", "")
#         except:
#             domain = link[:30] if link else "—"

#         c1, c2, c3, c4, c5, c6 = st.columns([2, 4, 1, 1.5, 1.5, 2])
#         c1.caption(publish[:16] if publish else "—")
#         c2.write(f"**{title[:80]}**" if len(title) > 80 else f"**{title}**")

#         if c3.button("Read", key=f"blog_{real_idx}"):
#             st.session_state.selected_blog  = real_idx
#             st.session_state.selected_insta = None

#         if c4.button("📸 Insta", key=f"insta_{real_idx}"):
#             st.session_state.selected_insta = real_idx
#             st.session_state.selected_blog  = None

#         c5.write(f"`{tag}`")
#         c6.markdown(f"[{domain}]({link})")
#         st.divider()


# # ── Blog Detail ───────────────────────────────────────────────
# if st.session_state.selected_blog is not None:
#     idx  = st.session_state.selected_blog
#     item = results[idx]
#     blog = item.get("blog", {})

#     st.subheader("Blog detail")
#     m1, m2, m3 = st.columns(3)
#     m1.markdown(f"**Tag:** `{item.get('image_text', {}).get('tag', 'GENERAL')}`")
#     m2.markdown(f"**Country:** `{DEFAULT_COUNTRY}`")
#     m3.markdown(f"**Generated:** `{item.get('Run_Timestamp', '—')}`")

#     link = item.get("Blog_Link") or item.get("Blog_Links", "")
#     if link:
#         st.markdown(f"[Read original source ↗]({link})")
#     st.divider()

#     # ── CHANGE 2 — show AI generated title in detail ──────────
#     ai_title = blog.get("Blog_Title", "") or item.get("Blog_Title", "")
#     copy_row("Blog title", ai_title, key=f"cp_title_{idx}")
#     st.divider()

#     meta_title = blog.get("Meta_Title", "")
#     meta_desc  = blog.get("Meta_Description", "")

#     if meta_title or meta_desc:
#         with st.expander("SEO fields — Meta Title & Meta Description"):
#             if meta_title:
#                 char_count = len(meta_title)
#                 color = "green" if char_count <= 60 else "red"
#                 st.markdown(
#                     f"**Meta Title** &nbsp; <span style='color:{color};font-size:12px'>{char_count}/60 chars</span>",
#                     unsafe_allow_html=True
#                 )
#                 st.code(meta_title, language=None)
#             if meta_desc:
#                 char_count = len(meta_desc)
#                 color = "green" if char_count <= 160 else "red"
#                 st.markdown(
#                     f"**Meta Description** &nbsp; <span style='color:{color};font-size:12px'>{char_count}/160 chars</span>",
#                     unsafe_allow_html=True
#                 )
#                 st.code(meta_desc, language=None)
#     st.divider()

#     tldr = blog.get("TLDR", [])
#     if tldr:
#         copy_row("Key takeaways", "\n".join(f"• {t}" for t in tldr), key=f"cp_tldr_{idx}")
#     st.divider()

#     blog_html     = blog.get("Blog_Content", "")
#     plain_content = BeautifulSoup(blog_html, "html.parser").get_text(separator="\n", strip=True) if blog_html else ""

#     st.markdown("**Blog content**")
#     if blog_html:
#         render_blog_in_box(blog_html)
#         st.divider()
#         st.markdown("**Copy full blog content**")
#         st.text_area(
#             label            = "Copy full blog content",
#             value            = blog_html,
#             height           = 150,
#             key              = f"cp_fullcontent_{idx}",
#             label_visibility = "collapsed"
#         )
#     else:
#         st.info("No blog content available.")
#     st.divider()

#     conclusion = blog.get("Conclusion", "")
#     if conclusion:
#         copy_row("Conclusion", conclusion, key=f"cp_conclusion_{idx}")
#         st.divider()

#     internal_links = blog.get("Internal_Links", [])
#     if internal_links:
#         st.markdown("**Internal Links**")
#         for lnk in internal_links:
#             anchor    = lnk.get("anchor_text", "")
#             url       = lnk.get("url", "")
#             placement = lnk.get("placement", "")
#             st.markdown(
#                 f"- [{anchor}]({url})"
#                 + (f" &nbsp; <span style='color:#999;font-size:12px'>({placement})</span>" if placement else ""),
#                 unsafe_allow_html=True
#             )
#         st.divider()

#     faq_schema = blog.get("FAQ_Schema", {})
#     faqs       = faq_schema.get("mainEntity", [])
#     if faqs:
#         faq_jsonld = json.dumps(faq_schema, indent=2, ensure_ascii=False)
#         st.markdown("**FAQs — copy all (JSON-LD Schema)**")
#         st.text_area(
#             label            = "FAQs JSON-LD",
#             value            = faq_jsonld,
#             height           = 200,
#             key              = f"cp_allfaqs_{idx}",
#             label_visibility = "collapsed"
#         )
#         st.divider()
#         st.markdown("**FAQ details**")
#         for fi, faq in enumerate(faqs):
#             with st.expander(faq.get("name", "")):
#                 st.code(faq.get("acceptedAnswer", {}).get("text", ""), language=None)
#         st.divider()

#     notify_text = item.get("notify", {}).get("blog_notify", "")
#     if notify_text:
#         copy_row("Blog notification", notify_text, key=f"cp_notify_{idx}")
#         st.divider()

#     show_image_section(
#         label         = "Blog Thumbnail Outer (640×480)",
#         image_field   = item.get("blog_image_outer"),
#         display_width = 640,
#         idx           = idx,
#         key_prefix    = "blog_outer"
#     )
#     st.divider()

#     show_image_section(
#         label         = "Blog Thumbnail Inner (1920×490)",
#         image_field   = item.get("blog_image_inner"),
#         display_width = 700,
#         idx           = idx,
#         key_prefix    = "blog_inner"
#     )
#     st.divider()

#     cta = blog.get("CTA")
#     if cta:
#         if isinstance(cta, dict):
#             cta_text = cta.get("text", "Trade on Swastika ↗")
#             cta_url  = cta.get("url",  "https://trade.swastika.co.in/")
#         else:
#             cta_text = "Trade on Swastika ↗"
#             cta_url  = cta if str(cta).startswith("http") else "https://trade.swastika.co.in/"
#         st.link_button(cta_text, cta_url)


# # ── Instagram Detail ──────────────────────────────────────────
# if st.session_state.selected_insta is not None:
#     idx  = st.session_state.selected_insta
#     item = results[idx]

#     st.subheader("Instagram detail")

#     insta_data = item.get("instagram_notify", {})
#     caption    = insta_data.get("instagram_caption", "No caption found.")
#     hashtags   = insta_data.get("hashtags", "")

#     copy_row("Caption", caption, key=f"cp_insta_caption_{idx}")

#     if hashtags:
#         st.divider()
#         copy_row("Hashtags", hashtags, key=f"cp_insta_hashtags_{idx}")

#     st.divider()

#     show_image_section(
#         label         = "Instagram Image (1080×1080)",
#         image_field   = item.get("instagram_image"),
#         display_width = 540,
#         idx           = idx,
#         key_prefix    = "insta"
#     )


# import streamlit as st
# from bs4 import BeautifulSoup
# import os
# from urllib.parse import urlparse
# import json

# st.set_page_config(layout="wide", page_title="Swastika Blog Dashboard")

# DEFAULT_COUNTRY  = "India"
# DEFAULT_CATEGORY = "finance"


# def copy_row(label: str, text: str, key: str = ""):
#     st.markdown(f"**{label}**")
#     st.text_area(
#         label            = label,
#         value            = text,
#         height           = min(150, 35 + text.count('\n') * 20),
#         key              = key,
#         label_visibility = "collapsed"
#     )


# def download_image_btn(image_path: str, filename: str, label: str = "Download", unique_key: str = ""):
#     if image_path and os.path.exists(image_path):
#         ext  = os.path.splitext(filename)[1].lower()
#         mime = "image/webp" if ext == ".webp" else "image/jpeg"
#         with open(image_path, "rb") as f:
#             img_bytes = f.read()
#         st.download_button(
#             label     = label,
#             data      = img_bytes,
#             file_name = filename,
#             mime      = mime,
#             key       = f"dl_{unique_key}_{filename}"
#         )
#     else:
#         st.caption("Image not available for download.")


# def get_image_path(image_field, prefer: str = "webp") -> str:
#     if isinstance(image_field, dict):
#         if prefer == "webp" and image_field.get("webp"):
#             return image_field["webp"]
#         return image_field.get("jpg", "")
#     return image_field or ""


# def render_blog_in_box(html_content: str):
#     st.markdown(
#         f"""
#         <div style="
#             height: 400px;
#             overflow-y: auto;
#             border: 1px solid #e0e0e0;
#             border-radius: 8px;
#             padding: 16px 20px;
#             background-color: #fafafa;
#             font-size: 15px;
#             line-height: 1.8;
#             color: #333;
#         ">{html_content}</div>
#         """,
#         unsafe_allow_html=True
#     )


# # ── Image section helper ──────────────────────────────────────
# def show_image_section(label: str, image_field, display_width: int, idx: int, key_prefix: str):
#     """
#     Shows image with WebP display + download buttons for both JPG and WebP.
#     Handles both old string format and new dict format.
#     """
#     st.markdown(f"**{label}**")
#     webp_path = get_image_path(image_field, prefer="webp")
#     jpg_path  = get_image_path(image_field, prefer="jpg")

#     if webp_path and os.path.exists(webp_path):
#         st.image(webp_path, width=display_width)
#         col1, col2 = st.columns(2)
#         with col1:
#             download_image_btn(
#                 webp_path,
#                 os.path.basename(webp_path),
#                 "⬇ Download WebP",
#                 unique_key=f"{key_prefix}_webp_{idx}"
#             )
#         with col2:
#             download_image_btn(
#                 jpg_path,
#                 os.path.basename(jpg_path),
#                 "⬇ Download JPG",
#                 unique_key=f"{key_prefix}_jpg_{idx}"
#             )
#     elif jpg_path and os.path.exists(jpg_path):
#         st.image(jpg_path, width=display_width)
#         download_image_btn(
#             jpg_path,
#             os.path.basename(jpg_path),
#             "⬇ Download JPG",
#             unique_key=f"{key_prefix}_jpg_only_{idx}"
#         )
#     else:
#         st.warning(f"{label} not available.")


# st.title("Blog Dashboard")
# st.caption(f"Country: {DEFAULT_COUNTRY}  ·  Category: {DEFAULT_CATEGORY.capitalize()}")


# @st.cache_data(show_spinner="Loading blogs...", ttl=60)
# def load_data():
#     path = "output/testing_webp_output.json"
#     if not os.path.exists(path):
#         return []
#     with open(path, "r", encoding="utf-8") as f:
#         try:
#             return json.load(f)
#         except:
#             return []


# output  = load_data()
# results = output.get("results", []) if isinstance(output, dict) else output

# if st.button("Refresh data"):
#     st.cache_data.clear()
#     st.rerun()

# for key in ["selected_blog", "selected_insta", "page"]:
#     if key not in st.session_state:
#         st.session_state[key] = None if key != "page" else 1

# if not results:
#     st.warning("No blogs returned.")
#     st.stop()

# m1, m2, m3, m4 = st.columns(4)
# m1.metric("Total blogs",  len(results))
# m2.metric("Country",      DEFAULT_COUNTRY)
# m3.metric("Category",     DEFAULT_CATEGORY.capitalize())
# m4.metric("Sources", len(set(
#     urlparse(r.get("Blog_Link") or r.get("Blog_Links", "")).netloc
#     for r in results
# )))

# st.divider()

# sc, ss = st.columns([4, 1])
# search = sc.text_input("Search", placeholder="Search title or content...", label_visibility="collapsed")
# sort   = ss.selectbox("Sort", ["Newest first", "Oldest first", "A to Z"], label_visibility="collapsed")

# filtered = results
# if search:
#     q = search.lower()
#     filtered = [
#         r for r in results
#         if q in r.get("Blog_Title", "").lower()
#         or q in r.get("Blog_Content", "").lower()
#     ]
#     st.session_state.page = 1

# if sort == "Newest first":
#     filtered = sorted(filtered, key=lambda x: x.get("Publish_Date") or x.get("Blog_PublishDate") or x.get("Run_Timestamp", ""), reverse=True)
# elif sort == "Oldest first":
#     filtered = sorted(filtered, key=lambda x: x.get("Publish_Date") or x.get("Blog_PublishDate") or x.get("Run_Timestamp", ""))
# else:
#     filtered = sorted(filtered, key=lambda x: x.get("Blog_Title", ""))

# if not filtered:
#     st.info("No blogs match your search.")
#     st.stop()

# # ── Pagination ────────────────────────────────────────────────
# PAGE_SIZE = 20
# total     = len(filtered)
# max_page  = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)

# if st.session_state.page > max_page:
#     st.session_state.page = 1

# p1, p2, p3 = st.columns([1, 2, 1])
# with p1:
#     if st.button("← Prev") and st.session_state.page > 1:
#         st.session_state.page -= 1
#         st.rerun()
# with p2:
#     st.caption(f"Page {st.session_state.page} of {max_page}  ·  {total} blogs")
# with p3:
#     if st.button("Next →") and st.session_state.page < max_page:
#         st.session_state.page += 1
#         st.rerun()

# start      = (st.session_state.page - 1) * PAGE_SIZE
# end        = start + PAGE_SIZE
# page_items = filtered[start:end]

# # ── Header ───────────────────────────────────────────────────
# # h1, h2, h3, h4, h5, h6, h7 = st.columns([2, 4, 2, 1, 1.5, 1.5, 2])
# h1, h2, h3, h4, h5, h6 = st.columns([2, 4, 1, 1.5, 1.5, 2])
# h1.caption("Publish date")
# h2.caption("Blog title")
# h3.caption("Blog")
# h4.caption("Instagram")
# h5.caption("Tag")
# h6.caption("Source")
# st.divider()

# # ── Scrollable blog list ──────────────────────────────────────
# with st.container(height=500):
#     for i, item in enumerate(page_items):
#         real_idx = results.index(item)
#         publish  = item.get("Publish_Date") or item.get("Blog_PublishDate") or item.get("Run_Timestamp", "—")
#         title    = item.get("Blog_Title", "—")
#         headline = item.get("image_text", {}).get("headline", "—")
#         tag      = item.get("image_text", {}).get("tag", "GENERAL")
#         link     = item.get("Blog_Link") or item.get("Blog_Links", "—")

#         try:
#             domain = urlparse(link).netloc.replace("www.", "")
#         except:
#             domain = link[:30] if link else "—"

#         c1, c2, c3, c4, c5, c6 = st.columns([2, 4, 1, 1.5, 1.5, 2])
#         c1.caption(publish[:16] if publish else "—")
#         c2.write(f"**{title[:80]}**" if len(title) > 80 else f"**{title}**")
        

#         if c3.button("Read", key=f"blog_{real_idx}"):
#             st.session_state.selected_blog  = real_idx
#             st.session_state.selected_insta = None

#         if c4.button("📸 Insta", key=f"insta_{real_idx}"):
#             st.session_state.selected_insta = real_idx
#             st.session_state.selected_blog  = None

#         c5.write(f"`{tag}`")
#         c6.markdown(f"[{domain}]({link})")
#         st.divider()


# # ── Blog Detail ───────────────────────────────────────────────
# if st.session_state.selected_blog is not None:
#     idx  = st.session_state.selected_blog
#     item = results[idx]
#     blog = item.get("blog", {})

#     st.subheader("Blog detail")
#     m1, m2, m3 = st.columns(3)
#     m1.markdown(f"**Tag:** `{item.get('image_text', {}).get('tag', 'GENERAL')}`")
#     m2.markdown(f"**Country:** `{DEFAULT_COUNTRY}`")
#     m3.markdown(f"**Generated:** `{item.get('Run_Timestamp', '—')}`")

#     link = item.get("Blog_Link") or item.get("Blog_Links", "")
#     if link:
#         st.markdown(f"[Read original source ↗]({link})")
#     st.divider()

#     copy_row("Blog title", item.get("Blog_Title", ""), key=f"cp_title_{idx}")
#     st.divider()

#     meta_title = blog.get("Meta_Title", "")
#     meta_desc  = blog.get("Meta_Description", "")

#     if meta_title or meta_desc:
#         with st.expander("SEO fields — Meta Title & Meta Description"):
#             if meta_title:
#                 char_count = len(meta_title)
#                 color = "green" if char_count <= 60 else "red"
#                 st.markdown(
#                     f"**Meta Title** &nbsp; <span style='color:{color};font-size:12px'>{char_count}/60 chars</span>",
#                     unsafe_allow_html=True
#                 )
#                 st.code(meta_title, language=None)
#             if meta_desc:
#                 char_count = len(meta_desc)
#                 color = "green" if char_count <= 160 else "red"
#                 st.markdown(
#                     f"**Meta Description** &nbsp; <span style='color:{color};font-size:12px'>{char_count}/160 chars</span>",
#                     unsafe_allow_html=True
#                 )
#                 st.code(meta_desc, language=None)
#     st.divider()

#     tldr = blog.get("TLDR", [])
#     if tldr:
#         copy_row("Key takeaways", "\n".join(f"• {t}" for t in tldr), key=f"cp_tldr_{idx}")
#     st.divider()

#     blog_html     = blog.get("Blog_Content", "")
#     plain_content = BeautifulSoup(blog_html, "html.parser").get_text(separator="\n", strip=True) if blog_html else ""

#     # st.markdown("**Blog content**")
#     # if blog_html:
#     #     render_blog_in_box(blog_html)
#     #     st.divider()
#     #     copy_row("Copy full blog content", plain_content, key=f"cp_fullcontent_{idx}")
#     # else:
#     #     st.info("No blog content available.")
#     # st.divider()
#     st.markdown("**Blog content**")
#     if blog_html:
#         render_blog_in_box(blog_html)
#         st.divider()

#         # ── Copy full blog content — same rendered view + copyable HTML ──
#         st.markdown("**Copy full blog content**")
#         # render_blog_in_box(blog_html)          # same styled preview
#         st.text_area(                           # raw HTML for clipboard
#             label            = "Copy full blog content",
#             value            = blog_html,
#             height           = 150,
#             key              = f"cp_fullcontent_{idx}",
#             label_visibility = "collapsed"
#         )
#     else:
#         st.info("No blog content available.")
#     st.divider()

#     conclusion = blog.get("Conclusion", "")
#     if conclusion:
#         copy_row("Conclusion", conclusion, key=f"cp_conclusion_{idx}")
#         st.divider()

#     internal_links = blog.get("Internal_Links", [])
#     if internal_links:
#         st.markdown("**Internal Links**")
#         for lnk in internal_links:
#             anchor    = lnk.get("anchor_text", "")
#             url       = lnk.get("url", "")
#             placement = lnk.get("placement", "")
#             st.markdown(
#                 f"- [{anchor}]({url})"
#                 + (f" &nbsp; <span style='color:#999;font-size:12px'>({placement})</span>" if placement else ""),
#                 unsafe_allow_html=True
#             )
#         st.divider()

#     faq_schema = blog.get("FAQ_Schema", {})
#     faqs       = faq_schema.get("mainEntity", [])
#     if faqs:
#         faq_jsonld = json.dumps(faq_schema, indent=2, ensure_ascii=False)
#         st.markdown("**FAQs — copy all (JSON-LD Schema)**")
#         st.text_area(
#             label            = "FAQs JSON-LD",
#             value            = faq_jsonld,
#             height           = 200,
#             key              = f"cp_allfaqs_{idx}",
#             label_visibility = "collapsed"
#         )
#         st.divider()
#         st.markdown("**FAQ details**")
#         for fi, faq in enumerate(faqs):
#             with st.expander(faq.get("name", "")):
#                 st.code(faq.get("acceptedAnswer", {}).get("text", ""), language=None)
#         st.divider()

#     notify_text = item.get("notify", {}).get("blog_notify", "")
#     if notify_text:
#         copy_row("Blog notification", notify_text, key=f"cp_notify_{idx}")
#         st.divider()

#     # ── Blog Images — Thumbnail Outer (640x480) ───────────────
#     show_image_section(
#         label         = "Blog Thumbnail Outer (640×480)",
#         image_field   = item.get("blog_image_outer"),
#         display_width = 640,
#         idx           = idx,
#         key_prefix    = "blog_outer"
#     )
#     st.divider()

#     # ── Blog Images — Thumbnail Inner (1920x490) ──────────────
#     show_image_section(
#         label         = "Blog Thumbnail Inner (1920×490)",
#         image_field   = item.get("blog_image_inner"),
#         display_width = 700,
#         idx           = idx,
#         key_prefix    = "blog_inner"
#     )
#     st.divider()

#     cta = blog.get("CTA")
#     if cta:
#         if isinstance(cta, dict):
#             cta_text = cta.get("text", "Trade on Swastika ↗")
#             cta_url  = cta.get("url",  "https://trade.swastika.co.in/")
#         else:
#             cta_text = "Trade on Swastika ↗"
#             cta_url  = cta if str(cta).startswith("http") else "https://trade.swastika.co.in/"
#         st.link_button(cta_text, cta_url)


# # ── Instagram Detail ──────────────────────────────────────────
# if st.session_state.selected_insta is not None:
#     idx  = st.session_state.selected_insta
#     item = results[idx]

#     st.subheader("Instagram detail")

#     insta_data = item.get("instagram_notify", {})
#     caption    = insta_data.get("instagram_caption", "No caption found.")
#     hashtags   = insta_data.get("hashtags", "")

#     copy_row("Caption", caption, key=f"cp_insta_caption_{idx}")

#     if hashtags:
#         st.divider()
#         copy_row("Hashtags", hashtags, key=f"cp_insta_hashtags_{idx}")

#     st.divider()

#     # ── Instagram Image (1080x1080) ───────────────────────────
#     show_image_section(
#         label         = "Instagram Image (1080×1080)",
#         image_field   = item.get("instagram_image"),
#         display_width = 540,
#         idx           = idx,
#         key_prefix    = "insta"
#     )









# import streamlit as st
# from bs4 import BeautifulSoup
# import os
# from urllib.parse import urlparse
# import json

# st.set_page_config(layout="wide", page_title="Swastika Blog Dashboard")

# DEFAULT_COUNTRY  = "India"
# DEFAULT_CATEGORY = "finance"


# def copy_row(label: str, text: str, key: str = ""):
#     st.markdown(f"**{label}**")
#     st.text_area(
#         label            = label,
#         value            = text,
#         height           = min(150, 35 + text.count('\n') * 20),
#         key              = key,
#         label_visibility = "collapsed"
#     )


# # ── CHANGE 1 — download_image_btn supports both jpg and webp ──
# def download_image_btn(image_path: str, filename: str, label: str = "Download"):
#     if image_path and os.path.exists(image_path):
#         ext  = os.path.splitext(filename)[1].lower()
#         mime = "image/webp" if ext == ".webp" else "image/jpeg"
#         with open(image_path, "rb") as f:
#             img_bytes = f.read()
#         st.download_button(
#             label     = label,
#             data      = img_bytes,
#             file_name = filename,
#             mime      = mime,
#             key       = f"dl_{filename}"
#         )
#     else:
#         st.caption("Image not available for download.")


# # ── CHANGE 2 — helper to extract webp path from blog_image dict
# def get_image_path(image_field, prefer: str = "webp") -> str:
#     """
#     blog_image / instagram_image can be:
#       - dict: {"jpg": "...", "webp": "..."}  ← new format
#       - str:  "path/to/image.jpg"            ← old format fallback
#     Returns the preferred format path if available, else fallback.
#     """
#     if isinstance(image_field, dict):
#         if prefer == "webp" and image_field.get("webp"):
#             return image_field["webp"]
#         return image_field.get("jpg", "")
#     return image_field or ""


# def render_blog_in_box(html_content: str):
#     plain_text = BeautifulSoup(html_content, "html.parser").get_text(separator="\n", strip=True)
#     st.markdown(
#         f"""
#         <div style="
#             height: 400px;
#             overflow-y: auto;
#             border: 1px solid #e0e0e0;
#             border-radius: 8px;
#             padding: 16px 20px;
#             background-color: #fafafa;
#             font-size: 15px;
#             line-height: 1.8;
#             color: #333;
#             white-space: pre-wrap;
#         ">{plain_text}</div>
#         """,
#         unsafe_allow_html=True
#     )


# st.title("Blog Dashboard")
# st.caption(f"Country: {DEFAULT_COUNTRY}  ·  Category: {DEFAULT_CATEGORY.capitalize()}")


# @st.cache_data(show_spinner="Loading blogs...", ttl=60)
# def load_data():
#     path = "output/output.json"
#     if not os.path.exists(path):
#         return []
#     with open(path, "r", encoding="utf-8") as f:
#         try:
#             return json.load(f)
#         except:
#             return []


# output  = load_data()
# results = output.get("results", []) if isinstance(output, dict) else output

# if st.button("Refresh data"):
#     st.cache_data.clear()
#     st.rerun()

# for key in ["selected_blog", "selected_insta"]:
#     if key not in st.session_state:
#         st.session_state[key] = None

# if not results:
#     st.warning("No blogs returned.")
#     st.stop()

# m1, m2, m3, m4 = st.columns(4)
# m1.metric("Total blogs",  len(results))
# m2.metric("Country",      DEFAULT_COUNTRY)
# m3.metric("Category",     DEFAULT_CATEGORY.capitalize())
# m4.metric("Sources", len(set(
#     urlparse(r.get("Blog_Link") or r.get("Blog_Links", "")).netloc
#     for r in results
# )))

# st.divider()

# sc, ss = st.columns([4, 1])
# search = sc.text_input("Search", placeholder="Search title or content...", label_visibility="collapsed")
# sort   = ss.selectbox("Sort", ["Newest first", "Oldest first", "A to Z"], label_visibility="collapsed")

# filtered = results
# if search:
#     q = search.lower()
#     filtered = [
#         r for r in results
#         if q in r.get("Blog_Title", "").lower()
#         or q in r.get("Blog_Content", "").lower()
#     ]

# if sort == "Newest first":
#     filtered = sorted(filtered, key=lambda x: x.get("Publish_Date") or x.get("Blog_PublishDate") or x.get("Run_Timestamp", ""), reverse=True)
# elif sort == "Oldest first":
#     filtered = sorted(filtered, key=lambda x: x.get("Publish_Date") or x.get("Blog_PublishDate") or x.get("Run_Timestamp", ""))
# else:
#     filtered = sorted(filtered, key=lambda x: x.get("Blog_Title", ""))

# if not filtered:
#     st.info("No blogs match your search.")
#     st.stop()

# # ── Header ───────────────────────────────────────────────────
# h1, h2, h3, h4, h5, h6, h7 = st.columns([2, 4, 2, 1, 1.5, 1.5, 2])
# h1.caption("Publish date")
# h2.caption("Blog title")
# h3.caption("Headline")
# h4.caption("Blog")
# h5.caption("Instagram")
# h6.caption("Tag")
# h7.caption("Source")
# st.divider()

# # ── Scrollable blog list ──────────────────────────────────────
# with st.container(height=500):
#     for i, item in enumerate(filtered):
#         real_idx = results.index(item)
#         publish  = item.get("Publish_Date") or item.get("Blog_PublishDate") or item.get("Run_Timestamp", "—")
#         title    = item.get("Blog_Title", "—")
#         headline = item.get("image_text", {}).get("headline", "—")
#         tag      = item.get("image_text", {}).get("tag", "GENERAL")
#         link     = item.get("Blog_Link") or item.get("Blog_Links", "—")

#         try:
#             domain = urlparse(link).netloc.replace("www.", "")
#         except:
#             domain = link[:30] if link else "—"

#         c1, c2, c3, c4, c5, c6, c7 = st.columns([2, 4, 2, 1, 1.5, 1.5, 2])
#         c1.caption(publish[:16] if publish else "—")
#         c2.write(f"**{title[:80]}**" if len(title) > 80 else f"**{title}**")
#         c3.caption(headline[:50] + "..." if len(headline) > 50 else headline)

#         if c4.button("Read", key=f"blog_{real_idx}"):
#             st.session_state.selected_blog  = real_idx
#             st.session_state.selected_insta = None

#         if c5.button("📸 Insta", key=f"insta_{real_idx}"):
#             st.session_state.selected_insta = real_idx
#             st.session_state.selected_blog  = None

#         c6.write(f"`{tag}`")
#         c7.markdown(f"[{domain}]({link})")
#         st.divider()


# # ── Blog Detail ───────────────────────────────────────────────
# if st.session_state.selected_blog is not None:
#     idx  = st.session_state.selected_blog
#     item = results[idx]
#     blog = item.get("blog", {})

#     st.subheader("Blog detail")
#     m1, m2, m3 = st.columns(3)
#     m1.markdown(f"**Tag:** `{item.get('image_text', {}).get('tag', 'GENERAL')}`")
#     m2.markdown(f"**Country:** `{DEFAULT_COUNTRY}`")
#     m3.markdown(f"**Generated:** `{item.get('Run_Timestamp', '—')}`")

#     link = item.get("Blog_Link") or item.get("Blog_Links", "")
#     if link:
#         st.markdown(f"[Read original source ↗]({link})")
#     st.divider()

#     copy_row("Blog title", item.get("Blog_Title", ""), key=f"cp_title_{idx}")
#     st.divider()

#     meta_title = blog.get("Meta_Title", "")
#     meta_desc  = blog.get("Meta_Description", "")

#     if meta_title or meta_desc:
#         with st.expander("SEO fields — Meta Title & Meta Description"):
#             if meta_title:
#                 char_count = len(meta_title)
#                 color = "green" if char_count <= 60 else "red"
#                 st.markdown(
#                     f"**Meta Title** &nbsp; <span style='color:{color};font-size:12px'>{char_count}/60 chars</span>",
#                     unsafe_allow_html=True
#                 )
#                 st.code(meta_title, language=None)
#             if meta_desc:
#                 char_count = len(meta_desc)
#                 color = "green" if char_count <= 160 else "red"
#                 st.markdown(
#                     f"**Meta Description** &nbsp; <span style='color:{color};font-size:12px'>{char_count}/160 chars</span>",
#                     unsafe_allow_html=True
#                 )
#                 st.code(meta_desc, language=None)
#     st.divider()

#     tldr = blog.get("TLDR", [])
#     if tldr:
#         copy_row("Key takeaways", "\n".join(f"• {t}" for t in tldr), key=f"cp_tldr_{idx}")
#     st.divider()

#     blog_html     = blog.get("Blog_Content", "")
#     plain_content = BeautifulSoup(blog_html, "html.parser").get_text(separator="\n", strip=True) if blog_html else ""

#     st.markdown("**Blog content**")
#     if blog_html:
#         render_blog_in_box(blog_html)
#         st.divider()
#         copy_row("Copy full blog content", plain_content, key=f"cp_fullcontent_{idx}")
#     else:
#         st.info("No blog content available.")
#     st.divider()

#     conclusion = blog.get("Conclusion", "")
#     if conclusion:
#         copy_row("Conclusion", conclusion, key=f"cp_conclusion_{idx}")
#         st.divider()

#     internal_links = blog.get("Internal_Links", [])
#     if internal_links:
#         st.markdown("**Internal Links**")
#         for lnk in internal_links:
#             anchor    = lnk.get("anchor_text", "")
#             url       = lnk.get("url", "")
#             placement = lnk.get("placement", "")
#             st.markdown(
#                 f"- [{anchor}]({url})"
#                 + (f" &nbsp; <span style='color:#999;font-size:12px'>({placement})</span>" if placement else ""),
#                 unsafe_allow_html=True
#             )
#         st.divider()

#     faqs = blog.get("FAQ_Schema", {}).get("mainEntity", [])
#     if faqs:
#         copy_row("FAQs — copy all", "\n\n".join(
#             f"Q: {f.get('name', '')}\nA: {f.get('acceptedAnswer', {}).get('text', '')}"
#             for f in faqs
#         ), key=f"cp_allfaqs_{idx}")
#         st.markdown("**FAQ details**")
#         for fi, faq in enumerate(faqs):
#             with st.expander(faq.get("name", "")):
#                 st.code(faq.get("acceptedAnswer", {}).get("text", ""), language=None)
#         st.divider()

#     notify_text = item.get("notify", {}).get("blog_notify", "")
#     if notify_text:
#         copy_row("Blog notification", notify_text, key=f"cp_notify_{idx}")
#         st.divider()

#     # ── CHANGE 3 — Blog image shown in WebP, download both ───
#     st.markdown("**Blog image**")
#     blog_webp = get_image_path(item.get("blog_image"), prefer="webp")
#     blog_jpg  = get_image_path(item.get("blog_image"), prefer="jpg")

#     if blog_webp and os.path.exists(blog_webp):
#         st.image(blog_webp, width=700)
#         col1, col2 = st.columns(2)
#         with col1:
#             download_image_btn(blog_webp, os.path.basename(blog_webp), "⬇ Download WebP")
#         with col2:
#             download_image_btn(blog_jpg,  os.path.basename(blog_jpg),  "⬇ Download JPG")
#     elif blog_jpg and os.path.exists(blog_jpg):
#         st.image(blog_jpg, width=700)
#         download_image_btn(blog_jpg, os.path.basename(blog_jpg), "⬇ Download JPG")
#     else:
#         st.warning("Blog image not available.")

#     cta = blog.get("CTA")
#     if cta:
#         if isinstance(cta, dict):
#             cta_text = cta.get("text", "Trade on Swastika ↗")
#             cta_url  = cta.get("url",  "https://trade.swastika.co.in/")
#         else:
#             cta_text = "Trade on Swastika ↗"
#             cta_url  = cta if str(cta).startswith("http") else "https://trade.swastika.co.in/"
#         st.link_button(cta_text, cta_url)


# # ── Instagram Detail ──────────────────────────────────────────
# if st.session_state.selected_insta is not None:
#     idx  = st.session_state.selected_insta
#     item = results[idx]

#     st.subheader("Instagram detail")

#     insta_data = item.get("instagram_notify", {})
#     caption    = insta_data.get("instagram_caption", "No caption found.")
#     hashtags   = insta_data.get("hashtags", "")

#     copy_row("Caption", caption, key=f"cp_insta_caption_{idx}")

#     if hashtags:
#         st.divider()
#         copy_row("Hashtags", hashtags, key=f"cp_insta_hashtags_{idx}")

#     st.divider()

#     # ── CHANGE 4 — Instagram image shown in WebP, download both
#     st.markdown("**Instagram image**")
#     insta_webp = get_image_path(item.get("instagram_image"), prefer="webp")
#     insta_jpg  = get_image_path(item.get("instagram_image"), prefer="jpg")

#     if insta_webp and os.path.exists(insta_webp):
#         st.image(insta_webp, width=540)
#         col1, col2 = st.columns(2)
#         with col1:
#             download_image_btn(insta_webp, os.path.basename(insta_webp), "⬇ Download WebP")
#         with col2:
#             download_image_btn(insta_jpg,  os.path.basename(insta_jpg),  "⬇ Download JPG")
#     elif insta_jpg and os.path.exists(insta_jpg):
#         st.image(insta_jpg, width=540)
#         download_image_btn(insta_jpg, os.path.basename(insta_jpg), "⬇ Download JPG")
#     else:
#         st.warning("No Instagram image generated yet.")



# import streamlit as st
# from bs4 import BeautifulSoup
# import os
# from urllib.parse import urlparse
# import json

# st.set_page_config(layout="wide", page_title="Swastika Blog Dashboard")

# DEFAULT_COUNTRY  = "India"
# DEFAULT_CATEGORY = "finance"


# def copy_row(label: str, text: str, key: str = ""):
#     st.markdown(f"**{label}**")
#     st.text_area(
#         label            = label,
#         value            = text,
#         height           = min(150, 35 + text.count('\n') * 20),
#         key              = key,
#         label_visibility = "collapsed"
#     )


# def download_image_btn(image_path: str, filename: str, label: str = "Download"):
#     if image_path and os.path.exists(image_path):
#         with open(image_path, "rb") as f:
#             img_bytes = f.read()
#         st.download_button(
#             label=label,
#             data=img_bytes,
#             file_name=filename,
#             mime="image/jpeg",
#             key=f"dl_{filename}"
#         )
#     else:
#         st.caption("Image not available for download.")


# def render_blog_in_box(html_content: str):
#     plain_text = BeautifulSoup(html_content, "html.parser").get_text(separator="\n", strip=True)
#     st.markdown(
#         f"""
#         <div style="
#             height: 400px;
#             overflow-y: auto;
#             border: 1px solid #e0e0e0;
#             border-radius: 8px;
#             padding: 16px 20px;
#             background-color: #fafafa;
#             font-size: 15px;
#             line-height: 1.8;
#             color: #333;
#             white-space: pre-wrap;
#         ">{plain_text}</div>
#         """,
#         unsafe_allow_html=True
#     )


# st.title("Blog Dashboard")
# st.caption(f"Country: {DEFAULT_COUNTRY}  ·  Category: {DEFAULT_CATEGORY.capitalize()}")


# @st.cache_data(show_spinner="Loading blogs...", ttl=60)
# def load_data():
#     path = "output/output.json"
#     if not os.path.exists(path):
#         return []
#     with open(path, "r", encoding="utf-8") as f:
#         try:
#             return json.load(f)
#         except:
#             return []


# output  = load_data()
# results = output.get("results", []) if isinstance(output, dict) else output

# if st.button("Refresh data"):
#     st.cache_data.clear()
#     st.rerun()

# for key in ["selected_blog", "selected_insta"]:
#     if key not in st.session_state:
#         st.session_state[key] = None

# if not results:
#     st.warning("No blogs returned.")
#     st.stop()

# m1, m2, m3, m4 = st.columns(4)
# m1.metric("Total blogs",  len(results))
# m2.metric("Country",      DEFAULT_COUNTRY)
# m3.metric("Category",     DEFAULT_CATEGORY.capitalize())
# m4.metric("Sources", len(set(
#     urlparse(r.get("Blog_Link") or r.get("Blog_Links", "")).netloc
#     for r in results
# )))

# st.divider()

# sc, ss = st.columns([4, 1])
# search = sc.text_input("Search", placeholder="Search title or content...", label_visibility="collapsed")
# sort   = ss.selectbox("Sort", ["Newest first", "Oldest first", "A to Z"], label_visibility="collapsed")

# filtered = results
# if search:
#     q = search.lower()
#     filtered = [
#         r for r in results
#         if q in r.get("Blog_Title", "").lower()
#         or q in r.get("Blog_Content", "").lower()
#     ]

# if sort == "Newest first":
#     filtered = sorted(filtered, key=lambda x: x.get("Publish_Date") or x.get("Blog_PublishDate") or x.get("Run_Timestamp", ""), reverse=True)
# elif sort == "Oldest first":
#     filtered = sorted(filtered, key=lambda x: x.get("Publish_Date") or x.get("Blog_PublishDate") or x.get("Run_Timestamp", ""))
# else:
#     filtered = sorted(filtered, key=lambda x: x.get("Blog_Title", ""))

# if not filtered:
#     st.info("No blogs match your search.")
#     st.stop()

# # ── Header ───────────────────────────────────────────────────
# h1, h2, h3, h4, h5, h6, h7 = st.columns([2, 4, 2, 1, 1.5, 1.5, 2])
# h1.caption("Publish date")
# h2.caption("Blog title")
# h3.caption("Headline")
# h4.caption("Blog")
# h5.caption("Instagram")
# h6.caption("Tag")
# h7.caption("Source")
# st.divider()

# # ── Scrollable blog list ──────────────────────────────────────
# with st.container(height=500):
#     for i, item in enumerate(filtered):
#         real_idx = results.index(item)
#         publish  = item.get("Publish_Date") or item.get("Blog_PublishDate") or item.get("Run_Timestamp", "—")
#         title    = item.get("Blog_Title", "—")
#         headline = item.get("image_text", {}).get("headline", "—")
#         tag      = item.get("image_text", {}).get("tag", "GENERAL")
#         link     = item.get("Blog_Link") or item.get("Blog_Links", "—")

#         try:
#             domain = urlparse(link).netloc.replace("www.", "")
#         except:
#             domain = link[:30] if link else "—"

#         c1, c2, c3, c4, c5, c6, c7 = st.columns([2, 4, 2, 1, 1.5, 1.5, 2])
#         c1.caption(publish[:16] if publish else "—")
#         c2.write(f"**{title[:80]}**" if len(title) > 80 else f"**{title}**")
#         c3.caption(headline[:50] + "..." if len(headline) > 50 else headline)

#         if c4.button("Read", key=f"blog_{real_idx}"):
#             st.session_state.selected_blog  = real_idx
#             st.session_state.selected_insta = None

#         if c5.button("📸 Insta", key=f"insta_{real_idx}"):
#             st.session_state.selected_insta = real_idx
#             st.session_state.selected_blog  = None

#         c6.write(f"`{tag}`")
#         c7.markdown(f"[{domain}]({link})")
#         st.divider()


# # ── Blog Detail ───────────────────────────────────────────────
# if st.session_state.selected_blog is not None:
#     idx  = st.session_state.selected_blog
#     item = results[idx]
#     blog = item.get("blog", {})

#     st.subheader("Blog detail")
#     m1, m2, m3 = st.columns(3)
#     m1.markdown(f"**Tag:** `{item.get('image_text', {}).get('tag', 'GENERAL')}`")
#     m2.markdown(f"**Country:** `{DEFAULT_COUNTRY}`")
#     m3.markdown(f"**Generated:** `{item.get('Run_Timestamp', '—')}`")

#     link = item.get("Blog_Link") or item.get("Blog_Links", "")
#     if link:
#         st.markdown(f"[Read original source ↗]({link})")
#     st.divider()

#     # ── Blog Title ────────────────────────────────────────────
#     copy_row("Blog title", item.get("Blog_Title", ""), key=f"cp_title_{idx}")
#     st.divider()

#     # ── CHANGE 1: SEO Meta fields with character counters ─────
#     meta_title = blog.get("Meta_Title", "")
#     meta_desc  = blog.get("Meta_Description", "")

#     if meta_title or meta_desc:
#         with st.expander("SEO fields — Meta Title & Meta Description"):
#             if meta_title:
#                 char_count = len(meta_title)
#                 color = "green" if char_count <= 60 else "red"
#                 st.markdown(
#                     f"**Meta Title** &nbsp; <span style='color:{color};font-size:12px'>{char_count}/60 chars</span>",
#                     unsafe_allow_html=True
#                 )
#                 st.code(meta_title, language=None)
#             if meta_desc:
#                 char_count = len(meta_desc)
#                 color = "green" if char_count <= 160 else "red"
#                 st.markdown(
#                     f"**Meta Description** &nbsp; <span style='color:{color};font-size:12px'>{char_count}/160 chars</span>",
#                     unsafe_allow_html=True
#                 )
#                 st.code(meta_desc, language=None)
#     st.divider()

#     # ── TLDR ──────────────────────────────────────────────────
#     tldr = blog.get("TLDR", [])
#     if tldr:
#         copy_row("Key takeaways", "\n".join(f"• {t}" for t in tldr), key=f"cp_tldr_{idx}")
#     st.divider()

#     # ── Blog Content ──────────────────────────────────────────
#     blog_html     = blog.get("Blog_Content", "")
#     plain_content = BeautifulSoup(blog_html, "html.parser").get_text(separator="\n", strip=True) if blog_html else ""

#     st.markdown("**Blog content**")
#     if blog_html:
#         render_blog_in_box(blog_html)
#         st.divider()
#         copy_row("Copy full blog content", plain_content, key=f"cp_fullcontent_{idx}")
#     else:
#         st.info("No blog content available.")
#     st.divider()

#     # ── Conclusion ────────────────────────────────────────────
#     conclusion = blog.get("Conclusion", "")
#     if conclusion:
#         copy_row("Conclusion", conclusion, key=f"cp_conclusion_{idx}")
#         st.divider()

#     # ── CHANGE 2: Internal Links section ──────────────────────
#     internal_links = blog.get("Internal_Links", [])
#     if internal_links:
#         st.markdown("**Internal Links**")
#         for lnk in internal_links:
#             anchor    = lnk.get("anchor_text", "")
#             url       = lnk.get("url", "")
#             placement = lnk.get("placement", "")
#             st.markdown(
#                 f"- [{anchor}]({url})"
#                 + (f" &nbsp; <span style='color:#999;font-size:12px'>({placement})</span>" if placement else ""),
#                 unsafe_allow_html=True
#             )
#         st.divider()

#     # ── FAQs ──────────────────────────────────────────────────
#     faqs = blog.get("FAQ_Schema", {}).get("mainEntity", [])
#     if faqs:
#         copy_row("FAQs — copy all", "\n\n".join(
#             f"Q: {f.get('name', '')}\nA: {f.get('acceptedAnswer', {}).get('text', '')}"
#             for f in faqs
#         ), key=f"cp_allfaqs_{idx}")
#         st.markdown("**FAQ details**")
#         for fi, faq in enumerate(faqs):
#             with st.expander(faq.get("name", "")):
#                 st.code(faq.get("acceptedAnswer", {}).get("text", ""), language=None)
#         st.divider()

#     # ── Blog notification ─────────────────────────────────────
#     notify_text = item.get("notify", {}).get("blog_notify", "")
#     if notify_text:
#         copy_row("Blog notification", notify_text, key=f"cp_notify_{idx}")
#         st.divider()

#     # ── Blog image ────────────────────────────────────────────
#     blog_img = item.get("blog_image", "")
#     if blog_img and os.path.exists(blog_img):
#         st.markdown("**Blog image**")
#         st.image(blog_img, width=700)
#         download_image_btn(blog_img, os.path.basename(blog_img), "Download blog image")

#     # ── CHANGE 3: Contextual CTA ──────────────────────────────
#     cta = blog.get("CTA")
#     if cta:
#         # Support both old string format and new dict format
#         if isinstance(cta, dict):
#             cta_text = cta.get("text", "Trade on Swastika ↗")
#             cta_url  = cta.get("url",  "https://trade.swastika.co.in/")
#         else:
#             # Old format: CTA is just a URL string
#             cta_text = "Trade on Swastika ↗"
#             cta_url  = cta if str(cta).startswith("http") else "https://trade.swastika.co.in/"
#         st.link_button(cta_text, cta_url)


# # ── Instagram Detail ──────────────────────────────────────────
# if st.session_state.selected_insta is not None:
#     idx  = st.session_state.selected_insta
#     item = results[idx]

#     st.subheader("Instagram detail")

#     insta_data = item.get("instagram_notify", {})

#     caption  = insta_data.get("instagram_caption", "No caption found.")
#     hashtags = insta_data.get("hashtags", "")

#     copy_row("Caption", caption, key=f"cp_insta_caption_{idx}")

#     if hashtags:
#         st.divider()
#         copy_row("Hashtags", hashtags, key=f"cp_insta_hashtags_{idx}")

#     st.divider()

#     insta_img = item.get("instagram_image", "")
#     if insta_img and os.path.exists(insta_img):
#         st.markdown("**Instagram image**")
#         st.image(insta_img, width=540)
#         download_image_btn(insta_img, os.path.basename(insta_img), "Download Instagram image")
#     else:
#         st.warning("No Instagram image generated yet.")

# import streamlit as st
# from bs4 import BeautifulSoup
# import os
# from urllib.parse import urlparse
# import json

# st.set_page_config(layout="wide", page_title="Swastika Blog Dashboard")

# DEFAULT_COUNTRY  = "India"
# DEFAULT_CATEGORY = "finance"


# def copy_row(label: str, text: str, key: str = ""):
#     st.markdown(f"**{label}**")
#     st.text_area(
#         label            = label,
#         value            = text,
#         height           = min(150, 35 + text.count('\n') * 20),
#         key              = key,
#         label_visibility = "collapsed"
#     )


# def download_image_btn(image_path: str, filename: str, label: str = "Download"):
#     if image_path and os.path.exists(image_path):
#         with open(image_path, "rb") as f:
#             img_bytes = f.read()
#         st.download_button(
#             label=label,
#             data=img_bytes,
#             file_name=filename,
#             mime="image/jpeg",
#             key=f"dl_{filename}"
#         )
#     else:
#         st.caption("Image not available for download.")


# def render_blog_in_box(html_content: str):
#     plain_text = BeautifulSoup(html_content, "html.parser").get_text(separator="\n", strip=True)
#     st.markdown(
#         f"""
#         <div style="
#             height: 400px;
#             overflow-y: auto;
#             border: 1px solid #e0e0e0;
#             border-radius: 8px;
#             padding: 16px 20px;
#             background-color: #fafafa;
#             font-size: 15px;
#             line-height: 1.8;
#             color: #333;
#             white-space: pre-wrap;
#         ">{plain_text}</div>
#         """,
#         unsafe_allow_html=True
#     )


# st.title("Blog Dashboard")
# st.caption(f"Country: {DEFAULT_COUNTRY}  ·  Category: {DEFAULT_CATEGORY.capitalize()}")


# @st.cache_data(show_spinner="Loading blogs...", ttl=60)
# def load_data():
#     path = "output/output.json"
#     if not os.path.exists(path):
#         return []
#     with open(path, "r", encoding="utf-8") as f:
#         try:
#             return json.load(f)
#         except:
#             return []


# output  = load_data()
# results = output.get("results", []) if isinstance(output, dict) else output

# if st.button("Refresh data"):
#     st.cache_data.clear()
#     st.rerun()

# for key in ["selected_blog", "selected_insta"]:
#     if key not in st.session_state:
#         st.session_state[key] = None

# if not results:
#     st.warning("No blogs returned.")
#     st.stop()

# m1, m2, m3, m4 = st.columns(4)
# m1.metric("Total blogs",  len(results))
# m2.metric("Country",      DEFAULT_COUNTRY)
# m3.metric("Category",     DEFAULT_CATEGORY.capitalize())
# m4.metric("Sources", len(set(
#     urlparse(r.get("Blog_Link") or r.get("Blog_Links", "")).netloc
#     for r in results
# )))

# st.divider()

# sc, ss = st.columns([4, 1])
# search = sc.text_input("Search", placeholder="Search title or content...", label_visibility="collapsed")
# sort   = ss.selectbox("Sort", ["Newest first", "Oldest first", "A to Z"], label_visibility="collapsed")

# filtered = results
# if search:
#     q = search.lower()
#     filtered = [
#         r for r in results
#         if q in r.get("Blog_Title", "").lower()
#         or q in r.get("Blog_Content", "").lower()
#     ]

# if sort == "Newest first":
#     filtered = sorted(filtered, key=lambda x: x.get("Publish_Date") or x.get("Blog_PublishDate") or x.get("Run_Timestamp", ""), reverse=True)
# elif sort == "Oldest first":
#     filtered = sorted(filtered, key=lambda x: x.get("Publish_Date") or x.get("Blog_PublishDate") or x.get("Run_Timestamp", ""))
# else:
#     filtered = sorted(filtered, key=lambda x: x.get("Blog_Title", ""))

# if not filtered:
#     st.info("No blogs match your search.")
#     st.stop()

# # ── Header ───────────────────────────────────────────────────
# h1, h2, h3, h4, h5, h6, h7 = st.columns([2, 4, 2, 1, 1.5, 1.5, 2])
# h1.caption("Publish date")
# h2.caption("Blog title")
# h3.caption("Headline")
# h4.caption("Blog")
# h5.caption("Instagram")
# h6.caption("Tag")
# h7.caption("Source")
# st.divider()

# # ✅ NEW — Scrollable container — max 500px height
# with st.container(height=500):
#     for i, item in enumerate(filtered):
#         real_idx = results.index(item)
#         publish  = item.get("Publish_Date") or item.get("Blog_PublishDate") or item.get("Run_Timestamp", "—")
#         title    = item.get("Blog_Title", "—")
#         headline = item.get("image_text", {}).get("headline", "—")
#         tag      = item.get("image_text", {}).get("tag", "GENERAL")
#         link     = item.get("Blog_Link") or item.get("Blog_Links", "—")

#         try:
#             domain = urlparse(link).netloc.replace("www.", "")
#         except:
#             domain = link[:30] if link else "—"

#         c1, c2, c3, c4, c5, c6, c7 = st.columns([2, 4, 2, 1, 1.5, 1.5, 2])
#         c1.caption(publish[:16] if publish else "—")
#         c2.write(f"**{title[:80]}**" if len(title) > 80 else f"**{title}**")
#         c3.caption(headline[:50] + "..." if len(headline) > 50 else headline)

#         if c4.button("Read", key=f"blog_{real_idx}"):
#             st.session_state.selected_blog  = real_idx
#             st.session_state.selected_insta = None

#         if c5.button("📸 Insta", key=f"insta_{real_idx}"):
#             st.session_state.selected_insta = real_idx
#             st.session_state.selected_blog  = None

#         c6.write(f"`{tag}`")
#         c7.markdown(f"[{domain}]({link})")
#         st.divider()

# # ── Blog Detail ───────────────────────────────────────────────
# if st.session_state.selected_blog is not None:
#     idx  = st.session_state.selected_blog
#     item = results[idx]
#     blog = item.get("blog", {})

#     st.subheader("Blog detail")
#     m1, m2, m3 = st.columns(3)
#     m1.markdown(f"**Tag:** `{item.get('image_text', {}).get('tag', 'GENERAL')}`")
#     m2.markdown(f"**Country:** `{DEFAULT_COUNTRY}`")
#     m3.markdown(f"**Generated:** `{item.get('Run_Timestamp', '—')}`")

#     link = item.get("Blog_Link") or item.get("Blog_Links", "")
#     if link:
#         st.markdown(f"[Read original source ↗]({link})")
#     st.divider()

#     copy_row("Blog title", item.get("Blog_Title", ""), key=f"cp_title_{idx}")
#     st.divider()

#     tldr = blog.get("TLDR", [])
#     if tldr:
#         copy_row("Key takeaways", "\n".join(f"• {t}" for t in tldr), key=f"cp_tldr_{idx}")
#     st.divider()

#     blog_html     = blog.get("Blog_Content", "")
#     plain_content = BeautifulSoup(blog_html, "html.parser").get_text(separator="\n", strip=True) if blog_html else ""

#     st.markdown("**Blog content**")
#     if blog_html:
#         render_blog_in_box(blog_html)
#         st.divider()
#         copy_row("Copy full blog content", plain_content, key=f"cp_fullcontent_{idx}")
#     else:
#         st.info("No blog content available.")
#     st.divider()

#     conclusion = blog.get("Conclusion", "")
#     if conclusion:
#         copy_row("Conclusion", conclusion, key=f"cp_conclusion_{idx}")
#         st.divider()

#     faqs = blog.get("FAQ_Schema", {}).get("mainEntity", [])
#     if faqs:
#         copy_row("FAQs — copy all", "\n\n".join(
#             f"Q: {f.get('name', '')}\nA: {f.get('acceptedAnswer', {}).get('text', '')}"
#             for f in faqs
#         ), key=f"cp_allfaqs_{idx}")
#         st.markdown("**FAQ details**")
#         for fi, faq in enumerate(faqs):
#             with st.expander(faq.get("name", "")):
#                 st.code(faq.get("acceptedAnswer", {}).get("text", ""), language=None)
#         st.divider()

#     notify_text = item.get("notify", {}).get("blog_notify", "")
#     if notify_text:
#         copy_row("Blog notification", notify_text, key=f"cp_notify_{idx}")
#         st.divider()

#     blog_img = item.get("blog_image", "")
#     if blog_img and os.path.exists(blog_img):
#         st.markdown("**Blog image**")
#         st.image(blog_img, width=700)
#         download_image_btn(blog_img, os.path.basename(blog_img), "Download blog image")

#     # if blog.get("CTA"):
#     #     st.link_button("Trade on Swastika app ↗", blog["CTA"])
#     if blog.get("CTA"):
#         cta_text = blog.get("CTA_Text", "Trade on Swastika ↗")  # contextual text
#         cta_url  = blog.get("CTA") if blog["CTA"].startswith("http") else "https://trade.swastika.co.in/"
#         st.link_button(cta_text, cta_url)


# # ── Instagram Detail ──────────────────────────────────────────
# if st.session_state.selected_insta is not None:
#     idx  = st.session_state.selected_insta
#     item = results[idx]

#     st.subheader("Instagram detail")

#     insta_data = item.get("instagram_notify", {})

#     # ✅ Caption aur hashtags alag dikhao
#     caption  = insta_data.get("instagram_caption", "No caption found.")
#     hashtags = insta_data.get("hashtags", "")

#     copy_row("Caption", caption, key=f"cp_insta_caption_{idx}")

#     if hashtags:
#         st.divider()
#         copy_row("Hashtags", hashtags, key=f"cp_insta_hashtags_{idx}")

#     st.divider()

#     insta_img = item.get("instagram_image", "")
#     if insta_img and os.path.exists(insta_img):
#         st.markdown("**Instagram image**")
#         st.image(insta_img, width=540)
#         download_image_btn(insta_img, os.path.basename(insta_img), "Download Instagram image")
#     else:
#         st.warning("No Instagram image generated yet.")
# if st.session_state.selected_insta is not None:
#     idx  = st.session_state.selected_insta
#     item = results[idx]

#     st.subheader("Instagram detail")
#     copy_row(
#         "Caption",
#         item.get("instagram_notify", {}).get("instagram_caption", "No caption found."),
#         key=f"cp_insta_caption_{idx}"
#     )
#     st.divider()

#     insta_img = item.get("instagram_image", "")
#     if insta_img and os.path.exists(insta_img):
#         st.markdown("**Instagram image**")
#         st.image(insta_img, width=540)
#         download_image_btn(insta_img, os.path.basename(insta_img), "Download Instagram image")
#     else:
#         st.warning("No Instagram image generated yet.")
# import streamlit as st
# from bs4 import BeautifulSoup
# import os
# from urllib.parse import urlparse

# import json

# st.set_page_config(layout="wide", page_title="Swastika Blog Dashboard")

# DEFAULT_COUNTRY  = "India"
# DEFAULT_CATEGORY = "finance"

# # ✅ FIXED copy_row — st.html use karo
# def copy_row(label: str, text: str, key: str = ""):
#     st.markdown(f"**{label}**")
#     st.code(text, language=None)  # 
# def download_image_btn(image_path: str, filename: str, label: str = "Download"):
#     if image_path and os.path.exists(image_path):
#         with open(image_path, "rb") as f:
#             img_bytes = f.read()
#         st.download_button(
#             label=label,
#             data=img_bytes,
#             file_name=filename,
#             mime="image/jpeg",
#             key=f"dl_{filename}"
#         )
#     else:
#         st.caption("Image not available for download.")

# st.title("Blog Dashboard")
# st.caption(f"Country: {DEFAULT_COUNTRY}  ·  Category: {DEFAULT_CATEGORY.capitalize()}")

# @st.cache_data(show_spinner="Loading blogs...", ttl=60)
# def load_data():
#     path = "output/output.json"
#     if not os.path.exists(path):
#         return []
#     with open(path, "r", encoding="utf-8") as f:
#         try:
#             return json.load(f)
#         except:
#             return []

# output  = load_data()
# results = output.get("results", []) if isinstance(output, dict) else output

# if st.button("Refresh data"):
#     st.cache_data.clear()
#     st.rerun()

# for key in ["selected_blog", "selected_insta"]:
#     if key not in st.session_state:
#         st.session_state[key] = None

# if not results:
#     st.warning("No blogs returned.")
#     st.stop()

# m1, m2, m3, m4 = st.columns(4)
# m1.metric("Total blogs",  len(results))
# m2.metric("Country",      DEFAULT_COUNTRY)
# m3.metric("Category",     DEFAULT_CATEGORY.capitalize())
# m4.metric("Sources", len(set(
#     urlparse(r.get("Blog_Link") or r.get("Blog_Links","")).netloc
#     for r in results
# )))

# st.divider()

# sc, ss = st.columns([4, 1])
# search = sc.text_input("Search", placeholder="Search title or content...", label_visibility="collapsed")
# sort   = ss.selectbox("Sort", ["Newest first", "Oldest first", "A to Z"], label_visibility="collapsed")

# filtered = results
# if search:
#     q = search.lower()
#     filtered = [
#         r for r in results
#         if q in r.get("Blog_Title","").lower()
#         or q in r.get("Blog_Content","").lower()
#     ]

# if sort == "Newest first":
#     filtered = sorted(filtered, key=lambda x: x.get("Publish_Date") or x.get("Blog_PublishDate") or x.get("Run_Timestamp",""), reverse=True)
# elif sort == "Oldest first":
#     filtered = sorted(filtered, key=lambda x: x.get("Publish_Date") or x.get("Blog_PublishDate") or x.get("Run_Timestamp",""))
# else:
#     filtered = sorted(filtered, key=lambda x: x.get("Blog_Title",""))

# if not filtered:
#     st.info("No blogs match your search.")
#     st.stop()

# h1, h2, h3, h4, h5, h6, h7 = st.columns([2, 4, 2, 1, 1.5, 1.5, 2])
# h1.caption("Publish date")
# h2.caption("Blog title")
# h3.caption("Headline")
# h4.caption("Blog")
# h5.caption("Instagram")
# h6.caption("Tag")
# h7.caption("Source")
# st.divider()

# for i, item in enumerate(filtered):
#     real_idx = results.index(item)
#     publish  = item.get("Publish_Date") or item.get("Blog_PublishDate") or item.get("Run_Timestamp","—")
#     title    = item.get("Blog_Title","—")
#     headline = item.get("image_text",{}).get("headline","—")
#     tag      = item.get("image_text",{}).get("tag","GENERAL")
#     link     = item.get("Blog_Link") or item.get("Blog_Links","—")

#     try:
#         domain = urlparse(link).netloc.replace("www.","")
#     except:
#         domain = link[:30] if link else "—"

#     c1, c2, c3, c4, c5, c6, c7 = st.columns([2, 4, 2, 1, 1.5, 1.5, 2])
#     c1.caption(publish[:16] if publish else "—")
#     c2.write(f"**{title[:80]}**" if len(title) > 80 else f"**{title}**")
#     c3.caption(headline[:50] + "..." if len(headline) > 50 else headline)

#     if c4.button("Read", key=f"blog_{real_idx}"):
#         st.session_state.selected_blog  = real_idx
#         st.session_state.selected_insta = None

#     if c5.button("📸 Insta", key=f"insta_{real_idx}"):
#         st.session_state.selected_insta = real_idx
#         st.session_state.selected_blog  = None

#     c6.write(f"`{tag}`")
#     c7.markdown(f"[{domain}]({link})")

# st.divider()

# def render_blog_content(html_content: str):
#     html_content = html_content.replace("\\n", " ").replace("\n", " ")
#     soup = BeautifulSoup(html_content, "html.parser")
#     for element in soup.descendants:
#         if element.parent != soup:
#             continue
#         tag_name  = getattr(element, 'name', None)
#         full_text = element.get_text(strip=True) if hasattr(element, 'get_text') else str(element).strip()
#         if not full_text:
#             continue
#         if tag_name == "h1":
#             parts = full_text.split(":", 1)
#             st.markdown(f"## {parts[0].strip()}")
#             if len(parts) > 1:
#                 st.caption(parts[1].strip())
#         elif tag_name in ["h2", "h3"]:
#             lines   = full_text.split(".")
#             heading = lines[0].strip()
#             body    = ". ".join(lines[1:]).strip() if len(lines) > 1 else ""
#             if tag_name == "h2":
#                 st.markdown(f"### {heading}")
#             else:
#                 st.markdown(
#                     f"<div style='border-left:3px solid #e6f1fb;padding-left:10px;margin:8px 0'>"
#                     f"<span style='font-size:14px;font-weight:500'>{heading}</span>"
#                     f"</div>", unsafe_allow_html=True
#                 )
#             if body:
#                 st.write(body)
#         elif tag_name == "p":
#             st.write(full_text)
#         elif tag_name is None:
#             if full_text:
#                 st.write(full_text)

# if st.session_state.selected_blog is not None:
#     idx  = st.session_state.selected_blog
#     item = results[idx]
#     blog = item.get("blog", {})
#     st.subheader("Blog detail")
#     m1, m2, m3 = st.columns(3)
#     m1.markdown(f"**Tag:** `{item.get('image_text',{}).get('tag','GENERAL')}`")
#     m2.markdown(f"**Country:** `{DEFAULT_COUNTRY}`")
#     m3.markdown(f"**Generated:** `{item.get('Run_Timestamp','—')}`")
#     link = item.get("Blog_Link") or item.get("Blog_Links","")
#     if link:
#         st.markdown(f"[Read original source ↗]({link})")
#     st.divider()
#     copy_row("Blog title", item.get("Blog_Title",""), key=f"cp_title_{idx}")
#     st.divider()
#     tldr = blog.get("TLDR", [])
#     if tldr:
#         copy_row("Key takeaways", "\n".join(f"• {t}" for t in tldr), key=f"cp_tldr_{idx}")
#     st.divider()
#     blog_html     = blog.get("Blog_Content", "")
#     plain_content = BeautifulSoup(blog_html, "html.parser").get_text(separator="\n", strip=True) if blog_html else ""
#     st.markdown("**Blog content**")
#     if blog_html:
#         render_blog_content(blog_html)
#         st.divider()
#         copy_row("Copy full blog content", plain_content, key=f"cp_fullcontent_{idx}")
#     else:
#         st.info("No blog content available.")
#     st.divider()
#     conclusion = blog.get("Conclusion","")
#     if conclusion:
#         copy_row("Conclusion", conclusion, key=f"cp_conclusion_{idx}")
#         st.divider()
#     faqs = blog.get("FAQ_Schema",{}).get("mainEntity",[])
#     if faqs:
#         copy_row("FAQs — copy all", "\n\n".join(
#             f"Q: {f.get('name','')}\nA: {f.get('acceptedAnswer',{}).get('text','')}"
#             for f in faqs
#         ), key=f"cp_allfaqs_{idx}")
#         st.markdown("**FAQ details**")
#         for fi, faq in enumerate(faqs):
#             with st.expander(faq.get("name","")):
#                 st.code(faq.get("acceptedAnswer",{}).get("text",""), language=None)
#         st.divider()
#     notify_text = item.get("notify",{}).get("blog_notify","")
#     if notify_text:
#         copy_row("Blog notification", notify_text, key=f"cp_notify_{idx}")
#         st.divider()
#     blog_img = item.get("blog_image","")
#     if blog_img and os.path.exists(blog_img):
#         st.markdown("**Blog image**")
#         st.image(blog_img, width=700)
#         download_image_btn(blog_img, os.path.basename(blog_img), "Download blog image")
#     if blog.get("CTA"):
#         st.link_button("Trade on Swastika app ↗", blog["CTA"])

# if st.session_state.selected_insta is not None:
#     idx  = st.session_state.selected_insta
#     item = results[idx]
#     st.subheader("Instagram detail")
#     copy_row("Caption", item.get("instagram_notify",{}).get("instagram_caption","No caption found."), key=f"cp_insta_caption_{idx}")
#     st.divider()
#     insta_img = item.get("instagram_image","")
#     if insta_img and os.path.exists(insta_img):
#         st.markdown("**Instagram image**")
#         st.image(insta_img, width=540)
#         download_image_btn(insta_img, os.path.basename(insta_img), "Download Instagram image")
#     else:
#         st.warning("No Instagram image generated yet.")
# import streamlit as st
# import threading
# from scheduler import run_job
# from apscheduler.schedulers.background import BackgroundScheduler
# from apscheduler.triggers.cron import CronTrigger
# # from mergeall_engine import run_pipeline
# from bs4 import BeautifulSoup
# import os
# from urllib.parse import urlparse
# import json
# # Start scheduler in background thread
# if "scheduler_started" not in st.session_state:
#     st.session_state.scheduler_started = True
#     def start_scheduler():
#         scheduler = BackgroundScheduler()  # ✅ doesn't block
#         scheduler.add_job(
#         func    = run_job,
#         trigger = CronTrigger(minute="*/5"),
#         id      = "blog_pipeline_job",
#         max_instances    = 1
#         )

    
        
#         run_job()
#         scheduler.start()
#     thread = threading.Thread(target=start_scheduler, daemon=True)   
#     thread.start()    

#     # run immediately
    

# # Start in background so Streamlit still loads



# st.set_page_config(layout="wide", page_title="Swastika Blog Dashboard")

# # ── Constants ─────────────────────────────────────────────────
# DEFAULT_COUNTRY  = "India"
# DEFAULT_CATEGORY = "finance"

# # ── Copy helper — uses st.code (native Streamlit copy icon) ──
# def copy_row(label: str, text: str, key: str = ""):
#     clean_text = text.replace("\\n", " ").replace("\n", " ").strip()
#     st.markdown(f"**{label}**")
#     st.code(text, language=None)

# # ── Download helper ───────────────────────────────────────────
# def download_image_btn(image_path: str, filename: str, label: str = "Download"):
#     if image_path and os.path.exists(image_path):
#         with open(image_path, "rb") as f:
#             img_bytes = f.read()
#         st.download_button(
#             label=label,
#             data=img_bytes,
#             file_name=filename,
#             mime="image/jpeg",
#             key=f"dl_{filename}"
#         )
#     else:
#         st.caption("Image not available for download.")

# # ── Page header ───────────────────────────────────────────────
# st.title("Blog Dashboard")
# st.caption(f"Country: {DEFAULT_COUNTRY}  ·  Category: {DEFAULT_CATEGORY.capitalize()}")

# # ── Load data ─────────────────────────────────────────────────
# # @st.cache_data(show_spinner="Fetching and generating blogs...")
# @st.cache_data(show_spinner="Loading blogs...", ttl=60)
# def load_data():
#     path = "output/output.json"
#     if not os.path.exists(path):
#         return []
#     with open(path, "r", encoding="utf-8") as f:
#         try:
#             return json.load(f)
#         except:
#             return []
#     # return run_pipeline(DEFAULT_COUNTRY, DEFAULT_CATEGORY)

# output  = load_data()
# results = output.get("results", []) if isinstance(output, dict) else output

# if st.button("Refresh data"):
#     st.cache_data.clear()
#     st.rerun()

# # ── Session state ─────────────────────────────────────────────
# for key in ["selected_blog", "selected_insta"]:
#     if key not in st.session_state:
#         st.session_state[key] = None

# # ── No data state ─────────────────────────────────────────────
# if not results:
#     st.warning("No blogs returned.")
#     st.stop()

# # ── Stats row ─────────────────────────────────────────────────
# m1, m2, m3, m4 = st.columns(4)
# m1.metric("Total blogs",  len(results))
# m2.metric("Country",      DEFAULT_COUNTRY)
# m3.metric("Category",     DEFAULT_CATEGORY.capitalize())
# m4.metric("Sources",      len(set(
#     urlparse(r.get("Blog_Link") or r.get("Blog_Links","")).netloc
#     for r in results
# )))

# st.divider()

# # ── Search + sort ─────────────────────────────────────────────
# sc, ss = st.columns([4, 1])
# search = sc.text_input("Search", placeholder="Search title or content...", label_visibility="collapsed")
# sort   = ss.selectbox("Sort", ["Newest first", "Oldest first", "A to Z"], label_visibility="collapsed")

# filtered = results
# if search:
#     q = search.lower()
#     filtered = [
#         r for r in results
#         if q in r.get("Blog_Title","").lower()
#         or q in r.get("Blog_Content","").lower()
#     ]

# if sort == "Newest first":
#     filtered = sorted(filtered, key=lambda x: x.get("Publish_Date") or x.get("Blog_PublishDate") or x.get("Run_Timestamp",""), reverse=True)
# elif sort == "Oldest first":
#     filtered = sorted(filtered, key=lambda x: x.get("Publish_Date") or x.get("Blog_PublishDate") or x.get("Run_Timestamp",""))
# else:
#     filtered = sorted(filtered, key=lambda x: x.get("Blog_Title",""))

# if not filtered:
#     st.info("No blogs match your search.")
#     st.stop()

# # ── Table header ──────────────────────────────────────────────
# h1, h2, h3, h4, h5, h6, h7 = st.columns([2, 4, 2, 1, 1.5, 1.5, 2])
# h1.caption("Publish date")
# h2.caption("Blog title")
# h3.caption("Headline")
# h4.caption("Blog")
# h5.caption("Instagram")
# h6.caption("Tag")
# h7.caption("Source")
# st.divider()

# # ── Table rows ────────────────────────────────────────────────
# for i, item in enumerate(filtered):
#     real_idx = results.index(item)

#     publish  = item.get("Publish_Date") or item.get("Blog_PublishDate") or item.get("Run_Timestamp","—")
#     title    = item.get("Blog_Title","—")
#     headline = item.get("image_text",{}).get("headline","—")
#     tag      = item.get("image_text",{}).get("tag","GENERAL")
#     link     = item.get("Blog_Link") or item.get("Blog_Links","—")

#     try:
#         domain = urlparse(link).netloc.replace("www.","")
#     except:
#         domain = link[:30] if link else "—"

#     c1, c2, c3, c4, c5, c6, c7 = st.columns([2, 4, 2, 1, 1.5, 1.5, 2])

#     c1.caption(publish[:16] if publish else "—")
#     c2.write(f"**{title[:80]}**" if len(title) > 80 else f"**{title}**")
#     c3.caption(headline[:50] + "..." if len(headline) > 50 else headline)

#     if c4.button("Read", key=f"blog_{real_idx}"):
#         st.session_state.selected_blog  = real_idx
#         st.session_state.selected_insta = None

#     if c5.button("📸 Insta", key=f"insta_{real_idx}"):
#         st.session_state.selected_insta = real_idx
#         st.session_state.selected_blog  = None

#     c6.write(f"`{tag}`")
#     c7.markdown(f"[{domain}]({link})")

# st.divider()

# # ── HTML content renderer ─────────────────────────────────────

# def render_blog_content(html_content: str):
#     """
#     Cleans and renders blog HTML content.
#     Handles literal \\n strings and malformed HTML from LLM output.
#     """
#     # ── Clean literal \n strings before parsing ───────────────
#     html_content = html_content.replace("\\n", " ").replace("\n", " ")

#     soup = BeautifulSoup(html_content, "html.parser")

#     for element in soup.descendants:
#         if element.parent != soup:
#             continue

#         tag_name  = getattr(element, 'name', None)
#         full_text = element.get_text(strip=True) if hasattr(element, 'get_text') else str(element).strip()

#         if not full_text:
#             continue

#         if tag_name == "h1":
#             parts = full_text.split(":", 1)
#             st.markdown(f"## {parts[0].strip()}")
#             if len(parts) > 1:
#                 st.caption(parts[1].strip())

#         elif tag_name in ["h2", "h3"]:
#             lines   = full_text.split(".")
#             heading = lines[0].strip()
#             body    = ". ".join(lines[1:]).strip() if len(lines) > 1 else ""

#             if tag_name == "h2":
#                 st.markdown(f"### {heading}")
#             else:
#                 st.markdown(
#                     f"<div style='border-left:3px solid #e6f1fb;padding-left:10px;margin:8px 0'>"
#                     f"<span style='font-size:14px;font-weight:500'>{heading}</span>"
#                     f"</div>",
#                     unsafe_allow_html=True
#                 )
#             if body:
#                 st.write(body)

#         elif tag_name == "p":
#             st.write(full_text)

#         elif tag_name is None:
#             if full_text:
#                 st.write(full_text)


# # ── Blog detail panel ─────────────────────────────────────────
# if st.session_state.selected_blog is not None:
#     idx  = st.session_state.selected_blog
#     item = results[idx]
#     blog = item.get("blog", {})

#     st.subheader("Blog detail")

#     # ── Meta ──────────────────────────────────────────────────
#     m1, m2, m3 = st.columns(3)
#     m1.markdown(f"**Tag:** `{item.get('image_text',{}).get('tag','GENERAL')}`")
#     m2.markdown(f"**Country:** `{DEFAULT_COUNTRY}`")
#     m3.markdown(f"**Generated:** `{item.get('Run_Timestamp','—')}`")

#     link = item.get("Blog_Link") or item.get("Blog_Links","")
#     if link:
#         st.markdown(f"[Read original source ↗]({link})")

#     st.divider()

#     # ── Blog title ────────────────────────────────────────────
#     copy_row("Blog title", item.get("Blog_Title",""), key=f"cp_title_{idx}")

#     st.divider()

#     # ── TLDR ──────────────────────────────────────────────────
#     tldr = blog.get("TLDR", [])
#     if tldr:
#         tldr_text = "\n".join(f"• {t}" for t in tldr)
#         copy_row("Key takeaways", tldr_text, key=f"cp_tldr_{idx}")

#     st.divider()

#     # ── Blog content — label + copy full content in same row ──
#     blog_html     = blog.get("Blog_Content", "")
#     plain_content = BeautifulSoup(blog_html, "html.parser").get_text(separator="\n", strip=True) if blog_html else ""

#     st.markdown("**Blog content**")
#     if blog_html:
#         render_blog_content(blog_html)
#         st.divider()
#         copy_row("Copy full blog content", plain_content, key=f"cp_fullcontent_{idx}")
#     else:
#         st.info("No blog content available.")

#     st.divider()

#     # ── Conclusion ────────────────────────────────────────────
#     conclusion = blog.get("Conclusion","")
#     if conclusion:
#         copy_row("Conclusion", conclusion, key=f"cp_conclusion_{idx}")
#         st.divider()

#     # ── FAQs ──────────────────────────────────────────────────
#     faqs = blog.get("FAQ_Schema",{}).get("mainEntity",[])
#     if faqs:
#         all_faqs_text = "\n\n".join(
#             f"Q: {f.get('name','')}\nA: {f.get('acceptedAnswer',{}).get('text','')}"
#             for f in faqs
#         )
#         copy_row("FAQs — copy all", all_faqs_text, key=f"cp_allfaqs_{idx}")

#         st.markdown("**FAQ details**")
#         for fi, faq in enumerate(faqs):
#             q   = faq.get("name","")
#             ans = faq.get("acceptedAnswer",{}).get("text","")
#             with st.expander(q):
#                 st.code(ans, language=None)

#         st.divider()

#     # ── Blog notification ─────────────────────────────────────
#     notify_text = item.get("notify",{}).get("blog_notify","")
#     if notify_text:
#         copy_row("Blog notification", notify_text, key=f"cp_notify_{idx}")
#         st.divider()

#     # ── Blog image with download ──────────────────────────────
#     blog_img = item.get("blog_image","")
#     if blog_img and os.path.exists(blog_img):
#         st.markdown("**Blog image**")
#         st.image(blog_img, width=700)
#         download_image_btn(
#             blog_img,
#             filename=os.path.basename(blog_img),
#             label="Download blog image"
#         )

#     # ── CTA ───────────────────────────────────────────────────
#     if blog.get("CTA"):
#         st.link_button("Trade on Swastika app ↗", blog["CTA"])

# # ── Instagram detail panel ────────────────────────────────────
# if st.session_state.selected_insta is not None:
#     idx  = st.session_state.selected_insta
#     item = results[idx]

#     st.subheader("Instagram detail")

#     caption = item.get("instagram_notify",{}).get("instagram_caption","No caption found.")
#     copy_row("Caption", caption, key=f"cp_insta_caption_{idx}")

#     st.divider()

#     insta_img = item.get("instagram_image","")
#     if insta_img and os.path.exists(insta_img):
#         st.markdown("**Instagram image**")
#         st.image(insta_img, width=540)
#         download_image_btn(
#             insta_img,
#             filename=os.path.basename(insta_img),
#             label="Download Instagram image"
#         )
#     else:
#         st.warning("No Instagram image generated yet.")
