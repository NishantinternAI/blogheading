import streamlit as st
from bs4 import BeautifulSoup
import os
from urllib.parse import urlparse
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


def render_blog_in_box(html_content: str):
    st.markdown(
        f"""
        <div style="
            height: 400px;
            overflow-y: auto;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            padding: 16px 20px;
            background-color: #fafafa;
            font-size: 15px;
            line-height: 1.8;
            color: #333;
        ">{html_content}</div>
        """,
        unsafe_allow_html=True
    )


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


@st.cache_data(show_spinner="Loading blogs...", ttl=60)
def load_data():
    path = "output/testing_webp_output1.json"
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except:
            return []


output  = load_data()
results = output.get("results", []) if isinstance(output, dict) else output

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
        or q in r.get("Blog_Content", "").lower()
    ]
    st.session_state.page = 1

if sort == "Newest first":
    filtered = sorted(filtered, key=lambda x: x.get("Publish_Date") or x.get("Blog_PublishDate") or x.get("Run_Timestamp", ""), reverse=True)
elif sort == "Oldest first":
    filtered = sorted(filtered, key=lambda x: x.get("Publish_Date") or x.get("Blog_PublishDate") or x.get("Run_Timestamp", ""))
else:
    filtered = sorted(filtered, key=lambda x: x.get("Blog_Title", ""))

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
        title    = item.get("Blog_Title", "—")
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

    copy_row("Blog title", item.get("Blog_Title", ""), key=f"cp_title_{idx}")
    st.divider()

    meta_title = blog.get("Meta_Title", "")
    meta_desc  = blog.get("Meta_Description", "")

    if meta_title or meta_desc:
        with st.expander("SEO fields — Meta Title & Meta Description"):
            if meta_title:
                char_count = len(meta_title)
                color = "green" if char_count <= 60 else "red"
                st.markdown(
                    f"**Meta Title** &nbsp; <span style='color:{color};font-size:12px'>{char_count}/60 chars</span>",
                    unsafe_allow_html=True
                )
                st.code(meta_title, language=None)
            if meta_desc:
                char_count = len(meta_desc)
                color = "green" if char_count <= 160 else "red"
                st.markdown(
                    f"**Meta Description** &nbsp; <span style='color:{color};font-size:12px'>{char_count}/160 chars</span>",
                    unsafe_allow_html=True
                )
                st.code(meta_desc, language=None)
    st.divider()

    tldr = blog.get("TLDR", [])
    if tldr:
        copy_row("Key takeaways", "\n".join(f"• {t}" for t in tldr), key=f"cp_tldr_{idx}")
    st.divider()

    blog_html     = blog.get("Blog_Content", "")
    plain_content = BeautifulSoup(blog_html, "html.parser").get_text(separator="\n", strip=True) if blog_html else ""

    st.markdown("**Blog content**")
    if blog_html:
        render_blog_in_box(blog_html)
        st.divider()
        st.markdown("**Copy full blog content**")
        st.text_area(
            label            = "Copy full blog content",
            value            = blog_html,
            height           = 150,
            key              = f"cp_fullcontent_{idx}",
            label_visibility = "collapsed"
        )
    else:
        st.info("No blog content available.")
    st.divider()

    conclusion = blog.get("Conclusion", "")
    if conclusion:
        copy_row("Conclusion", conclusion, key=f"cp_conclusion_{idx}")
        st.divider()

    internal_links = blog.get("Internal_Links", [])
    if internal_links:
        st.markdown("**Internal Links**")
        for lnk in internal_links:
            anchor    = lnk.get("anchor_text", "")
            url       = lnk.get("url", "")
            placement = lnk.get("placement", "")
            st.markdown(
                f"- [{anchor}]({url})"
                + (f" &nbsp; <span style='color:#999;font-size:12px'>({placement})</span>" if placement else ""),
                unsafe_allow_html=True
            )
        st.divider()

    # ── FAQs — JSON-LD Schema ─────────────────────────────────
    faq_schema = blog.get("FAQ_Schema", {})
    faqs       = faq_schema.get("mainEntity", [])

    if faqs:
        # ── CHANGE — Copy all shows JSON-LD format ────────────
        faq_jsonld = json.dumps(faq_schema, indent=2, ensure_ascii=False)
        st.markdown("**FAQs — copy all (JSON-LD Schema)**")
        st.text_area(
            label            = "FAQs JSON-LD",
            value            = faq_jsonld,
            height           = 200,
            key              = f"cp_allfaqs_{idx}",
            label_visibility = "collapsed"
        )
        st.divider()

        # ── FAQ details — still shows Q&A for reading ─────────
        st.markdown("**FAQ details**")
        for fi, faq in enumerate(faqs):
            with st.expander(faq.get("name", "")):
                st.code(faq.get("acceptedAnswer", {}).get("text", ""), language=None)
        st.divider()

    notify_text = item.get("notify", {}).get("blog_notify", "")
    if notify_text:
        copy_row("Blog notification", notify_text, key=f"cp_notify_{idx}")
        st.divider()

    # ── Blog Images ───────────────────────────────────────────
    show_image_section(
        label         = "Blog Thumbnail Outer (640×480)",
        image_field   = item.get("blog_image_outer"),
        display_width = 640,
        idx           = idx,
        key_prefix    = "blog_outer"
    )
    st.divider()

    show_image_section(
        label         = "Blog Thumbnail Inner (1920×490)",
        image_field   = item.get("blog_image_inner"),
        display_width = 700,
        idx           = idx,
        key_prefix    = "blog_inner"
    )
    st.divider()

    cta = blog.get("CTA")
    if cta:
        if isinstance(cta, dict):
            cta_text = cta.get("text", "Trade on Swastika ↗")
            cta_url  = cta.get("url",  "https://trade.swastika.co.in/")
        else:
            cta_text = "Trade on Swastika ↗"
            cta_url  = cta if str(cta).startswith("http") else "https://trade.swastika.co.in/"
        st.link_button(cta_text, cta_url)


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
#     path = "output/testing_webp_output1.json"
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


# def get_image_path(image_field, prefer: str = "webp") -> str:
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
#     st.session_state.page = 1  # reset to page 1 on search

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

#     # ── Blog image ────────────────────────────────────────────
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

#     # ── Instagram image ───────────────────────────────────────
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
#         label     = label,
#         value     = text,
#         height    = min(100, 35 + text.count('\n') * 20),
#         key       = key,
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
