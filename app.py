"""
app.py -- Streamlit review dashboard.

Runs as its own container (`streamlit run app.py`), independently of
scheduler.py's pipeline loop. Reads output/output.json (or
output/testing_webp_output.json when USE_AI_IMAGES=True in this file --
must stay in sync with the same flag in mergeall_engine.py) and lets a
human review/browse generated blogs, images, and captions before or
after they're posted to Webflow.
"""

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


# ─────────────────────────────────────────────────────────────
# HTML HELPERS
# ─────────────────────────────────────────────────────────────

def extract_conclusion(blog_html: str) -> str:
    """
    Extracts conclusion paragraph(s) from raw Blog_Content HTML
    BEFORE clean_blog_html strips them.

    Returns the inner HTML of the conclusion section (without the
    <h2> tag itself). Returns empty string if not found.

    Call order in dashboard:
        conclusion      = extract_conclusion(blog_html)   ← first
        blog_html_clean = clean_blog_html(blog_html)      ← second
    """
    if not blog_html:
        return ""

    soup = BeautifulSoup(blog_html, "html.parser")

    for h2 in soup.find_all("h2"):
        if h2.get_text(strip=True).lower().startswith("conclusion"):
            parts   = []
            current = h2.next_sibling
            while current:
                if hasattr(current, "name") and current.name == "h2":
                    break
                if hasattr(current, "get_text"):
                    parts.append(str(current))
                current = current.next_sibling
            return "".join(parts).strip()

    return ""


def clean_blog_html(blog_html: str) -> str:
    """
    Cleans Blog_Content HTML for dashboard rendering.

    Operations (in order):
      1. Remove first <h1>                   — dashboard renders title separately
      2. Remove orphaned <ul>/<ol> before    — catches bare TLDR lists dumped after
         first <h2>                            <h1> with no section wrapper
      3. Remove duplicate section blocks     — strips h2 + following content for
         (TLDR, FAQ, Conclusion, CTA, etc.)    sections the dashboard re-appends
      4. Remove all <h4> + following <p>     — FAQ Q&A leaking into Blog_Content
      5. Remove Swastika CTA anchor links    — swastika.co.in hrefs
      6. Unwrap disallowed tags              — keeps only allowed_tags
      7. Strip stray div/section/article     — leftovers from BeautifulSoup unwrap
      8. Normalise excessive blank lines
    """
    if not blog_html:
        return ""

    allowed_tags = [
        "h1", "h2", "h3", "h4",
        "p", "ul", "ol", "li",
        "strong", "em", "u", "br", "a", "span",
        "table", "thead", "tbody", "tr", "th", "td",
    ]

    # Sections the dashboard re-appends — strip from Blog_Content to prevent duplication
    REMOVE_PREFIXES = (
        "tldr",
        "key takeaways",
        "frequently asked questions",
        "faq",
        "faq details",
        "conclusion",
        "cta",
    )

    soup = BeautifulSoup(blog_html, "html.parser")

    # ── 1. Remove first <h1> ──────────────────────────────────
    first_h1 = soup.find("h1")
    if first_h1:
        first_h1.decompose()

    # ── 2. Remove orphaned <ul>/<ol> before first <h2> ───────
    # Catches TLDR lists dumped directly after <h1> with no
    # <h2>TLDR</h2> wrapper (prefix stripper below can't catch them)
    first_h2 = soup.find("h2")
    if first_h2:
        for tag in first_h2.find_all_previous(["ul", "ol"]):
            tag.decompose()

    # ── 3. Remove duplicate section blocks ───────────────────
    for h2 in soup.find_all("h2"):
        heading_text = h2.get_text(strip=True).lower()
        if any(heading_text.startswith(p) for p in REMOVE_PREFIXES):
            current = h2.next_sibling
            while current:
                next_node = current.next_sibling
                if hasattr(current, "name") and current.name == "h2":
                    break
                if hasattr(current, "decompose"):
                    current.decompose()
                current = next_node
            h2.decompose()

    # ── 4. Remove all <h4> + their answer <p> ────────────────
    for h4 in soup.find_all("h4"):
        next_p = h4.find_next_sibling("p")
        if next_p:
            next_p.decompose()
        h4.decompose()

    # ── 5. Remove CTA anchor links (swastika.co.in) ──────────
    for a_tag in soup.find_all("a", href=True):
        if "swastika.co.in" in a_tag.get("href", ""):
            a_tag.decompose()

    # ── 6. Unwrap disallowed tags ─────────────────────────────
    for tag in soup.find_all(True):
        if tag.name not in allowed_tags:
            tag.unwrap()

    cleaned = str(soup)

    # ── 7. Strip stray block-level tags ──────────────────────
    for block_tag in ("div", "section", "article"):
        cleaned = re.sub(rf"<{block_tag}[^>]*>", "", cleaned)
        cleaned = re.sub(rf"</{block_tag}>",      "", cleaned)

    # ── 8. Normalise blank lines ──────────────────────────────
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

    return cleaned.strip()


# ─────────────────────────────────────────────────────────────
# DATA HELPERS
# ─────────────────────────────────────────────────────────────

def get_blog(item: dict) -> dict:
    """
    Safely returns the blog field as a dict.
    Handles: dict already, JSON string, ```json wrapped string.
    """
    blog = item.get("blog", {})

    if isinstance(blog, dict):
        return blog

    if isinstance(blog, str):
        text = blog.strip()
        if text.startswith("```"):
            lines = text.split("\n")[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines).strip()
        try:
            return json.loads(text)
        except Exception:
            return {}

    return {}


def parse_date(item) -> datetime:
    """Parse any date format from JSON into a naive datetime for sorting."""
    raw = (
        item.get("Publish_Date")
        or item.get("Blog_PublishDate")
        or item.get("Run_Timestamp", "")
    )
    if not raw:
        return datetime.min

    raw = raw.strip()

    # RFC 2822: "Tue, 19 May 2026 08:30:45 +0530"
    try:
        return parsedate_to_datetime(raw).replace(tzinfo=None)
    except Exception:
        pass

    # ISO: "2026-05-19 04:16:25" / "2026-05-19T04:16:25" / "2026-05-19"
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw[:19], fmt)
        except Exception:
            pass

    # NSE: "15-May-2026 03:0" or "15-May-2026 03:00"
    try:
        parts     = raw.split(" ")
        date_part = parts[0]
        time_part = parts[1] if len(parts) > 1 else "00:00"
        if len(time_part.split(":")[1]) < 2:
            time_part += "0"
        return datetime.strptime(f"{date_part} {time_part}", "%d-%b-%Y %H:%M")
    except Exception:
        pass

    # NSE date only: "15-May-2026"
    try:
        return datetime.strptime(raw[:11], "%d-%b-%Y")
    except Exception:
        pass

    return datetime.min


def extract_faq_keyword(blog_title: str) -> str:
    """
    Derives a short keyword phrase from a blog title for FAQ display purposes.

    Strips a fixed set of stopwords and financial punctuation (dashes, `?`,
    `!`, `|`, `₹`, `%`, `,`), then returns the first 4 remaining words
    joined by spaces. Returns "Finance" if nothing remains after stripping.
    """
    STOP = {"should", "you", "buy", "sell", "now", "is", "are"}
    clean = re.sub(r"[–—\-\?!\|₹%,]", " ", blog_title)
    words = [w for w in clean.split() if w.lower() not in STOP]
    return " ".join(words[:4]) if words else "Finance"


def get_image_path(image_field, prefer: str = "webp") -> str:
    """
    Resolves a filesystem path from an item's image field.

    image_field may be a dict with "webp"/"jpg" keys or a plain string path
    (legacy shape). When prefer="webp" and a "webp" path exists, returns it;
    otherwise falls back to "jpg". Returns "" if nothing is available.
    """
    if isinstance(image_field, dict):
        if prefer == "webp" and image_field.get("webp"):
            return image_field["webp"]
        return image_field.get("jpg", "")
    return image_field or ""


# ─────────────────────────────────────────────────────────────
# UI HELPERS
# ─────────────────────────────────────────────────────────────

def copy_row(label: str, text: str, key: str = ""):
    """
    Renders a labelled, read-only text area sized to fit its content,
    used throughout the dashboard as a copy-to-clipboard-friendly widget.

    Params: label (bold heading shown above the box and used as the
    Streamlit widget label), text (content to display), key (Streamlit
    widget key; must be unique per call site to avoid state collisions).
    Renders directly to the page; returns None.
    """
    st.markdown(f"**{label}**")
    st.text_area(
        label            = label,
        value            = text,
        height           = min(150, 35 + text.count("\n") * 20),
        key              = key,
        label_visibility = "collapsed",
    )


def download_image_btn(image_path: str, filename: str, label: str = "Download", unique_key: str = ""):
    """
    Renders a Streamlit download button for a single local image file.

    Reads image_path from disk and infers MIME type from filename's
    extension (image/webp for .webp, image/jpeg otherwise). If image_path
    is falsy or does not exist on disk, renders a "not available" caption
    instead. unique_key must be unique per call site (it's combined with
    filename to build the widget key) to avoid Streamlit key collisions
    when multiple download buttons are rendered on the same page. Renders
    directly to the page; returns None.
    """
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
            key       = f"dl_{unique_key}_{filename}",
        )
    else:
        st.caption("Image not available for download.")


def show_image_section(label: str, image_field, display_width: int, idx: int, key_prefix: str):
    """
    Renders a labelled image preview plus download button(s) for one image
    field of an item (e.g. blog thumbnail, Instagram image).

    Resolves both webp and jpg paths via get_image_path(). Preference
    order: if a webp file exists on disk, show it (at display_width) with
    side-by-side "Download WebP" / "Download JPG" buttons; else if only
    the jpg exists, show it with a single JPG download button; else
    render a warning that the image is unavailable. idx and key_prefix
    are combined into Streamlit widget keys to keep buttons unique across
    repeated calls (e.g. one per list row). Renders directly to the page;
    returns None.
    """
    st.markdown(f"**{label}**")
    webp_path = get_image_path(image_field, prefer="webp")
    jpg_path  = get_image_path(image_field, prefer="jpg")

    if webp_path and os.path.exists(webp_path):
        st.image(webp_path, width=display_width)
        col1, col2 = st.columns(2)
        with col1:
            download_image_btn(webp_path, os.path.basename(webp_path), "⬇ Download WebP", unique_key=f"{key_prefix}_webp_{idx}")
        with col2:
            download_image_btn(jpg_path,  os.path.basename(jpg_path),  "⬇ Download JPG",  unique_key=f"{key_prefix}_jpg_{idx}")
    elif jpg_path and os.path.exists(jpg_path):
        st.image(jpg_path, width=display_width)
        download_image_btn(jpg_path, os.path.basename(jpg_path), "⬇ Download JPG", unique_key=f"{key_prefix}_jpg_only_{idx}")
    else:
        st.warning(f"{label} not available.")


# ─────────────────────────────────────────────────────────────
# APP BOOTSTRAP
# ─────────────────────────────────────────────────────────────

st.title("Blog Dashboard")
st.caption(f"Country: {DEFAULT_COUNTRY}  ·  Category: {DEFAULT_CATEGORY.capitalize()}")

USE_AI_IMAGES = False
OUTPUT_FILE   = "testing_webp_output.json" if USE_AI_IMAGES else "output.json"


@st.cache_data(show_spinner="Loading blogs...", ttl=60)
def load_data():
    """
    Loads the pipeline's output JSON from disk into a Python object.

    Reads from output/{OUTPUT_FILE}, where OUTPUT_FILE is chosen by the
    module-level USE_AI_IMAGES flag defined just above this function:
    "testing_webp_output.json" when True, else "output.json". GOTCHA:
    this flag is a separate constant from the same-named USE_AI_IMAGES
    flag in mergeall_engine.py and must be kept in sync with it manually
    — there is no shared config. Returns [] if the file is missing or
    fails to parse as JSON (never raises). Cached by Streamlit for 60s
    (ttl=60); the "Refresh data" button clears this cache on demand.
    """
    path = f"output/{OUTPUT_FILE}"
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except Exception:
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

# ─────────────────────────────────────────────────────────────
# METRICS BAR
# ─────────────────────────────────────────────────────────────

m1, m2, m3, m4 = st.columns(4)
m1.metric("Total blogs", len(results))
m2.metric("Country",     DEFAULT_COUNTRY)
m3.metric("Category",    DEFAULT_CATEGORY.capitalize())
m4.metric("Sources", len(set(
    urlparse(r.get("Blog_Link") or r.get("Blog_Links", "")).netloc
    for r in results
)))

st.divider()

# ─────────────────────────────────────────────────────────────
# SEARCH + SORT
# ─────────────────────────────────────────────────────────────

sc, ss = st.columns([4, 1])
search = sc.text_input("Search", placeholder="Search title or content...", label_visibility="collapsed")
sort   = ss.selectbox("Sort", ["Newest first", "Oldest first", "A to Z"], label_visibility="collapsed")

filtered = results
if search:
    q = search.lower()
    filtered = [
        r for r in results
        if q in r.get("Blog_Title", "").lower()
        or q in get_blog(r).get("Blog_Title", "").lower()
        or q in r.get("Blog_Content", "").lower()
    ]
    st.session_state.page = 1

if sort == "Newest first":
    filtered = sorted(filtered, key=parse_date, reverse=True)
elif sort == "Oldest first":
    filtered = sorted(filtered, key=parse_date)
else:
    filtered = sorted(
        filtered,
        key=lambda x: get_blog(x).get("Blog_Title", "") or x.get("Blog_Title", ""),
    )

if not filtered:
    st.info("No blogs match your search.")
    st.stop()

# ─────────────────────────────────────────────────────────────
# PAGINATION
# ─────────────────────────────────────────────────────────────

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

# ─────────────────────────────────────────────────────────────
# BLOG LIST
# ─────────────────────────────────────────────────────────────

h1, h2, h3, h4, h5, h6 = st.columns([2, 4, 1, 1.5, 1.5, 2])
h1.caption("Publish date")
h2.caption("Blog title")
h3.caption("Blog")
h4.caption("Instagram")
h5.caption("Tag")
h6.caption("Source")
st.divider()

with st.container(height=500):
    for i, item in enumerate(page_items):
        real_idx = results.index(item)
        publish  = item.get("Publish_Date") or item.get("Blog_PublishDate") or item.get("Run_Timestamp", "—")
        title    = get_blog(item).get("Blog_Title", "") or item.get("Blog_Title", "—")
        tag      = item.get("image_text", {}).get("tag", "GENERAL")
        link     = item.get("Blog_Link") or item.get("Blog_Links", "—")

        try:
            domain = urlparse(link).netloc.replace("www.", "")
        except Exception:
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


# ─────────────────────────────────────────────────────────────
# BLOG DETAIL
# ─────────────────────────────────────────────────────────────

if st.session_state.selected_blog is not None:
    idx  = st.session_state.selected_blog
    item = results[idx]
    blog = get_blog(item)

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

    # extract_conclusion MUST run on raw blog_html, before clean_blog_html strips it
    conclusion      = extract_conclusion(blog_html)
    blog_html_clean = clean_blog_html(blog_html)

    # ══════════════════════════════════════════════════════════
    # SECTION 1 — BLOG TITLE
    # ══════════════════════════════════════════════════════════
    copy_row("1. Blog Title", ai_title, key=f"cp_title_{idx}")
    st.divider()

    # ══════════════════════════════════════════════════════════
    # SECTION 2 — SEO DATA
    # ══════════════════════════════════════════════════════════
    st.markdown("**2. SEO Data**")
    st.markdown(
        """
        <div style="border:1.5px solid #1A56DB;border-radius:8px;
                    padding:12px 16px 4px 16px;background:#f0f4ff;margin-bottom:8px;">
            <span style="font-size:12px;color:#1A56DB;font-weight:600;">
                SEO — Meta Title · Meta Description · JSON-LD FAQ Schema
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if meta_title:
        n     = len(meta_title)
        color = "green" if n <= 60 else "red"
        st.markdown(
            f"Meta Title &nbsp; <span style='color:{color};font-size:12px'>{n}/60 chars</span>",
            unsafe_allow_html=True,
        )
    if meta_desc:
        n     = len(meta_desc)
        color = "green" if n <= 160 else "red"
        st.markdown(
            f"Meta Description &nbsp; <span style='color:{color};font-size:12px'>{n}/160 chars</span>",
            unsafe_allow_html=True,
        )

    seo_combined = ""
    if meta_title:  seo_combined += f"META TITLE:\n{meta_title}\n\n"
    if meta_desc:   seo_combined += f"META DESCRIPTION:\n{meta_desc}\n\n"
    if faq_jsonld:  seo_combined += f"JSON-LD FAQ SCHEMA:\n{faq_jsonld}"

    if seo_combined:
        st.text_area(
            label            = "SEO combined",
            value            = seo_combined,
            height           = 300,
            key              = f"cp_seo_combined_{idx}",
            label_visibility = "collapsed",
        )
    st.divider()

    # ══════════════════════════════════════════════════════════
    # SECTION 3 — BLOG CONTENT
    # Assembly order:
    #   1. <h1> title
    #   2. <h2>Key Takeaways</h2> + TLDR list  ← from blog.TLDR
    #   3. Cleaned body HTML                    ← no title / TLDR / FAQ / Conclusion
    #   4. <h2>FAQ</h2>                         ← from FAQ_Schema.mainEntity
    #   5. <h2>Conclusion</h2>                  ← extracted from Blog_Content
    # ══════════════════════════════════════════════════════════
    st.markdown("**3. Blog Content**")
    st.markdown(
        """
        <div style="border:1.5px solid #10B981;border-radius:8px;
                    padding:12px 16px 4px 16px;background:#f0fff8;margin-bottom:8px;">
            <span style="font-size:12px;color:#10B981;font-weight:600;">
                Blog Title · TLDR · Blog Content · FAQ · Conclusion — HTML Format
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    blog_combined = ""

    # 1. Title
    if ai_title:
        blog_combined += f"<h1>{ai_title}</h1>\n\n"

    # 2. TLDR — sourced from structured field only, never from Blog_Content
    if tldr:
        blog_combined += "<h2>Key Takeaways</h2>\n<ul>\n"
        blog_combined += "\n".join(f"<li>{t}</li>" for t in tldr)
        blog_combined += "\n</ul>\n\n"

    # 3. Cleaned body
    if blog_html_clean:
        blog_combined += blog_html_clean + "\n\n"

    # 4. FAQ — sourced from FAQ_Schema.mainEntity only
    if faqs:
        blog_combined += "<h2>FAQ</h2>\n"
        for faq in faqs:
            q = faq.get("name", "")
            a = faq.get("acceptedAnswer", {}).get("text", "")
            # Strip any HTML tags from answer text (model sometimes wraps in <p>)
            a_clean = BeautifulSoup(a, "html.parser").get_text(strip=True)
            blog_combined += f"<h4>{q}</h4>\n<p>{a_clean}</p>\n\n"

    # 5. Conclusion — extracted from Blog_Content before cleaning
    #    conclusion already contains <p> tags — append directly, do NOT wrap in <p>
    if conclusion:
        blog_combined += f"<h2>Conclusion</h2>\n{conclusion}\n\n"

    # Final cleanup pass
    if blog_combined:
        for block_tag in ("div", "section", "article"):
            blog_combined = re.sub(rf"<{block_tag}[^>]*>", "", blog_combined)
            blog_combined = re.sub(rf"</{block_tag}>",      "", blog_combined)
        blog_combined = re.sub(r"\n{3,}", "\n\n", blog_combined).strip()

        st.text_area(
            label            = "Blog content combined",
            value            = blog_combined,
            height           = 400,
            key              = f"cp_blog_combined_{idx}",
            label_visibility = "collapsed",
        )

        st.markdown("**Preview**")
        st.markdown(
            f"""
            <div style="height:500px;overflow-y:auto;border:1px solid #e0e0e0;
                        border-radius:8px;padding:24px 28px;background-color:#ffffff;
                        font-size:15px;line-height:1.8;color:#1a1a1a;
                        font-family:Arial,sans-serif;">
                {blog_combined}
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.divider()

    # ══════════════════════════════════════════════════════════
    # SECTION 4 — BLOG NOTIFICATION
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
        key_prefix    = "blog_outer",
    )
    st.divider()

    if item.get("blog_image_inner"):
        show_image_section(
            label         = "Blog Thumbnail Inner (1920×490)",
            image_field   = item.get("blog_image_inner"),
            display_width = 700,
            idx           = idx,
            key_prefix    = "blog_inner",
        )
        st.divider()

    # CTA link
    cta = blog.get("CTA")
    if cta:
        cta_url = (
            cta.get("url", "https://trade.swastika.co.in/")
            if isinstance(cta, dict)
            else (cta if str(cta).startswith("http") else "https://trade.swastika.co.in/")
        )
        st.markdown(f"[{cta_url}]({cta_url})")


# ─────────────────────────────────────────────────────────────
# INSTAGRAM DETAIL
# ─────────────────────────────────────────────────────────────

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
        key_prefix    = "insta",
    )