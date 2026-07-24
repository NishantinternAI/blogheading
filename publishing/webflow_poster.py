"""
webflow_poster.py
-----------------
Sync Webflow CMS poster -- called by scheduler.py after each pipeline run.
Uses only `requests` (already in requirements.txt), no extra deps.

Also imported by blog_post_mcp.py so the MCP server and the scheduler
share the same logic.
"""

import os
import tempfile
import re
import json
import hashlib
import base64
from datetime import datetime, timezone, timedelta
from pathlib import Path, PureWindowsPath

import requests

from keywords.related_links import (
    get_related_links,
    build_related_links_html,
    load_graph,
    add_blog_to_graph,
    _inject_related_links_before_conclusion,
)

TOKEN         = os.environ.get("WEBFLOW_API_TOKEN", "")
SITE_ID       = os.environ.get("SITE_ID", "649a7bd9d30be4bdd61239e5")
COLLECTION_ID = os.environ.get("COLLECTION_ID", "64d4a2b7bcb8f41bb4083979")
BASE          = "https://api.webflow.com/v2"

IMAGE_JPG_DIR = os.environ.get(
    "IMAGE_JPG_DIR",
    "/app/output_images/jpg_images",
)

IMAGE_WEBP_DIR = os.environ.get(
    "IMAGE_WEBP_DIR",
    "/app/output_images/webp_images",
)

OUTPUT_JSON_PATH = os.environ.get(
    "OUTPUT_JSON_PATH",
    "/app/output/output.json",
)
SITE_DOMAIN = os.environ.get("SITE_DOMAIN", "www.swastika.co.in")

# -- Default category -- "All Blog" item ID from Blog Post Categories ------
ALL_BLOG_CATEGORY_ID = "64e47c1a14f5229268062b69"

# -- Author details (hardcoded -- same for every blog post) ----------------
AUTHOR_USERNAME   = "Nidhi Thakur"
AUTHOR_EMAIL      = "nidhi.thakur@swastika.co.in"
AUTHOR_FIRST_NAME = "Nidhi"
AUTHOR_LAST_NAME  = "Thakur"

# -- IST timezone (UTC+5:30) -------------------------------------------------
IST = timezone(timedelta(hours=5, minutes=30))


# -- Helpers ------------------------------------------------------------------

def save_webflow_url(blog_links, webflow_url, output_path=OUTPUT_JSON_PATH,
                     generated_title=None):
    """Find the blog record just published and attach its live Webflow URL.

    Matching by `Blog_Links` alone is unsafe: corporate/IPO articles frequently
    share a source URL (e.g. the generic NSE corporate-actions page) or have an
    empty `Blog_Links`, so a first-match-by-link would write the URL onto the
    wrong (older) record. When `generated_title` is supplied (the generated
    blog["Blog_Title"] that was actually published), it is used as an additional
    discriminator: the match requires BOTH the link and the generated title, and
    if no link+title match is found we fall back to a title-only match before
    finally trying link-only. This keeps shared/empty links from mis-attaching.
    """
    with open(output_path, "r", encoding="utf-8") as f:
        blogs = json.load(f)

    def _gen_title(b):
        gt = b.get("blog")
        return gt.get("Blog_Title") if isinstance(gt, dict) else None

    match = None
    if generated_title:
        # Strongest: same source link AND same generated title
        match = next((b for b in blogs
                      if b.get("Blog_Links") == blog_links
                      and _gen_title(b) == generated_title), None)
        # Next: generated title alone (unique enough; handles empty/shared links)
        if match is None:
            match = next((b for b in blogs if _gen_title(b) == generated_title), None)
    # Last resort: legacy link-only match (safe only when the link is unique)
    if match is None:
        match = next((b for b in blogs if b.get("Blog_Links") == blog_links), None)

    if match is None:
        print(f"[WARN] No matching blog found (link={blog_links!r}, "
              f"title={generated_title!r}); URL not saved.")
        return False
    match["webflow_url"] = webflow_url

    dir_name = os.path.dirname(os.path.abspath(output_path))
    with tempfile.NamedTemporaryFile("w", dir=dir_name, delete=False, suffix=".tmp", encoding="utf-8") as tmp:
        json.dump(blogs, tmp, ensure_ascii=False, indent=2)
        tmp_path = tmp.name

    os.replace(tmp_path, output_path)
    print(f"[WEBFLOW] webflow_url saved to output.json: {webflow_url}")
    return True


def _now_ist_iso() -> str:
    """Return the current time in IST as an ISO 8601 string with +05:30 offset."""
    return datetime.now(IST).strftime("%Y-%m-%dT%H:%M:%S+05:30")


def _headers():
    """Build the standard Bearer-auth JSON headers used for every Webflow API request."""
    return {
        "Authorization": f"Bearer {TOKEN}",
        "Accept":        "application/json",
        "Content-Type":  "application/json",
    }


def _make_slug(title: str) -> str:
    """Derive a URL-safe slug from a blog title: lowercase, strip non-alphanumerics,
    collapse whitespace/dashes, and truncate to 80 chars."""
    s = title.lower()
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"\s+", "-", s.strip())
    s = re.sub(r"-+", "-", s)
    return s[:80]


def _faq_script(faq_schema: dict) -> str:
    """FAQ JSON-LD script tag -- for SEO, hidden from visitors."""
    return (
        '<script type="application/ld+json">'
        + json.dumps(faq_schema, ensure_ascii=False)
        + "</script>"
    )


def _md5_b64(path: Path) -> str:
    """Return the base64-encoded MD5 digest of a file's bytes (Webflow asset upload requires this as fileHash)."""
    return base64.b64encode(hashlib.md5(path.read_bytes()).digest()).decode()


def _local_path(img_dir: str, server_path: str) -> Path:
    """
    Resolve a stored image path (which may be a path from a different machine/OS,
    e.g. a Windows path recorded on another host) to a real local file.

    Returns `server_path` unchanged as a Path if it already exists on disk;
    otherwise re-joins just the filename onto `img_dir`.
    """
    original = Path(server_path)
    if original.exists():
        return original
    filename = PureWindowsPath(server_path).name
    if not filename:
        filename = Path(server_path).name
    return Path(img_dir) / filename


def _strip_h1(html: str) -> str:
    """Remove <h1>...</h1> from Blog_Content -- title already posted as item name."""
    return re.sub(r"<h1[^>]*>.*?</h1>", "", html, flags=re.IGNORECASE | re.DOTALL).strip()


# -- Title Case enforcement ---------------------------------------------------

_SMALL_WORDS = {
    "a", "an", "the", "and", "but", "or", "for", "nor",
    "on", "at", "to", "by", "in", "of", "up", "as", "is",
    "it", "vs", "via",
}


def _apply_title_case(text: str) -> str:
    """
    Capitalize the first letter of every major word.
    Uses negative lookbehind so letters following an apostrophe are NOT
    capitalized. Japan's stays Japan's, not Japan'S.
    """
    words = text.split()
    result = []
    for i, word in enumerate(words):
        clean = re.sub(r"[^a-zA-Z]", "", word).lower()
        if i == 0 or clean not in _SMALL_WORDS:
            titled = re.sub(
                r"(?<!['\u2019])(?:^|(?<=-))[a-z]",
                lambda m: m.group(0).upper(),
                word
            )
            result.append(titled)
        else:
            result.append(word)
    return " ".join(result)


def _title_case_name(title: str) -> str:
    """Apply Title Case to a blog's display name (thin wrapper around `_apply_title_case`)."""
    return _apply_title_case(title)


def _title_case_headings(html: str) -> str:
    """Force Title Case onto the visible text of every <h2> heading in `html`, leaving other tags untouched."""
    def _capitalize_heading(m):
        """Regex callback: title-case the captured <h2> text while preserving the surrounding tags."""
        tag_open  = m.group(1)
        text      = m.group(2)
        tag_close = m.group(3)
        titled = re.sub(
            r"(?<!['\u2019])\b([a-z])",
            lambda w: w.group(1).upper(),
            text
        )
        return f"{tag_open}{titled}{tag_close}"

    return re.sub(
        r"(<h2[^>]*>)(.*?)(</h2>)",
        _capitalize_heading,
        html,
        flags=re.IGNORECASE | re.DOTALL
    )


APP_DOWNLOAD_AD_HTML = (
    '<div class="w-embed"><div style="'
    'background: linear-gradient(to right, #39C3E6, #0B616D);'
    'border-radius: 8px; '
    'padding: 32px 24px; '
    'margin: 35px 0; '
    'width: 100%;'
    'box-sizing: border-box;'
    'text-align: center;'
    'box-shadow: 0 4px 15px rgba(11, 97, 109, 0.2);'
    'font-family: sans-serif;">'
    '<div style="'
    'font-size: 22px; '
    'font-weight: 700; '
    'color: #ffffff; '
    'margin-bottom: 20px; '
    'line-height: 1.3;'
    'letter-spacing: -0.01em;'
    'text-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);">'
    'Download App Now'
    '</div>'
    '<div class="appsblock ccenter" style="'
    'display: flex; '
    'justify-content: center; '
    'gap: 16px; '
    'flex-wrap: wrap;">'
    '<a rel="noopener noreferrer" href="https://play.google.com/store/apps/details?id=swastika.tradingo.justrade" target="_blank" class="w-inline-block" style="display: inline-block;">'
    '<img src="https://cdn.prod.website-files.com/649a7bd9d30be4bdd61239e5/659f97377f92a9d5b2572d85_google_play.webp" loading="lazy" alt="google play" class="app-img" style="height: 42px; width: auto; display: block;">'
    '</a>'
    '<a rel="noopener noreferrer" href="https://apps.apple.com/in/app/justrade2-0-stocks-investmart/id1627649963" target="_blank" class="w-inline-block" style="display: inline-block;">'
    '<img src="https://cdn.prod.website-files.com/649a7bd9d30be4bdd61239e5/659f97615e983f345bd9d60f_app_store.webp" loading="lazy" alt="app store" class="app-img" style="height: 42px; width: auto; display: block;">'
    '</a>'
    '</div></div></div>'
)


def _inject_app_download_ads(content: str) -> str:
    """
    Insert the app-download promo banner between body <h2> sections, mirroring
    the placement pattern used on the live site: roughly 2 banners spaced
    through the body, never inside TLDR/FAQ/Conclusion.

    Must run on `content` while it holds ONLY the generated body sections plus
    the (already-generated) Conclusion heading -- i.e. before TLDR is
    prepended and before FAQ is (re)injected -- so every <h2> found here
    except "Conclusion" counts as a body section boundary.
    """
    h2_pattern = re.compile(r"<h2[^>]*>.*?</h2>", re.IGNORECASE | re.DOTALL)
    body_h2s = [m for m in h2_pattern.finditer(content)
                if "conclusion" not in m.group(0).lower()]
    n = len(body_h2s)
    if n < 2:
        return content

    # Evenly-spaced boundaries, e.g. n=3 -> after section 0 and section 1.
    slots = sorted({s for s in (n // 3, (2 * n) // 3) if 0 < s < n})
    if not slots:
        return content

    result = content
    for slot in sorted(slots, reverse=True):
        pos = body_h2s[slot].start()
        result = result[:pos] + APP_DOWNLOAD_AD_HTML + result[pos:]
    return result


def _build_tldr_html(tldr: list) -> str:
    """Convert TLDR list into a visible Key Takeaways HTML block."""
    if not tldr:
        return ""
    items = "".join(f"<li>{point}</li>" for point in tldr)
    return (
        "<h2>Key Takeaways</h2>"
        f"<ul>{items}</ul>"
    )


def _build_faq_html(faq_schema: dict) -> str:
    """Render a FAQ JSON-LD schema's `mainEntity` Q&A pairs into visible <h2>/<h4>/<p> HTML. Returns "" if no questions."""
    if not faq_schema:
        return ""
    questions = faq_schema.get("mainEntity", [])
    if not questions:
        return ""
    html = "<h2>Frequently Asked Questions</h2>"
    for item in questions:
        question = item.get("name", "")
        answer   = item.get("acceptedAnswer", {}).get("text", "")
        if question and answer:
            html += f"<h4>{question}</h4><p>{answer}</p>"
    return html


def _inject_faq_before_conclusion(content: str, faq_html: str) -> str:
    """Insert `faq_html` immediately before the <h2>Conclusion</h2> heading, or append it at the end if no Conclusion section exists."""
    if not faq_html:
        return content
    conclusion_match = re.search(r"<h2[^>]*>\s*Conclusion\s*</h2>", content, re.IGNORECASE)
    if conclusion_match:
        insert_pos = conclusion_match.start()
        return content[:insert_pos] + faq_html + content[insert_pos:]
    return content + faq_html


def _build_cta_html(blog_title: str) -> str:
    """Build the hardcoded "open a trading/demat account" CTA link HTML. `blog_title` is currently unused."""
    url = "https://trade.swastika.co.in/?utm_source=Blog&utm_campaign=Tax+planning+plays+an+important+role+in+maximizing+investment+returns"
    return (
        f'<p><a href="{url}" rel="noopener" target="_blank">'
        f"Open your trading and demat account here</a></p>"
    )


def _inject_cta_after_conclusion(content: str, cta_html: str) -> str:
    """Insert `cta_html` after the last </p> inside the Conclusion section; falls back to appending at the end of `content` if there's no Conclusion or no paragraph to anchor to."""
    if not cta_html:
        return content
    conclusion_match = re.search(r"<h2[^>]*>\s*Conclusion\s*</h2>", content, re.IGNORECASE)
    if conclusion_match:
        after_conclusion = content[conclusion_match.start():]
        last_p = after_conclusion.rfind("</p>")
        if last_p != -1:
            insert_pos = conclusion_match.start() + last_p + len("</p>")
            return content[:insert_pos] + cta_html + content[insert_pos:]
    return content + cta_html


def _remove_empty_sections(html: str) -> str:
    """
    Drop any <h2> section that has no substantive following content (no
    <p>/<ul>/<ol>/<table>/<div> with text before the next <h2>). Uses
    BeautifulSoup to walk siblings; mutates and re-serializes the parsed tree.
    """
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    h2_tags = soup.find_all("h2")

    for h2 in h2_tags:
        siblings = []
        sibling = h2.next_sibling
        while sibling:
            if hasattr(sibling, "name") and sibling.name == "h2":
                break
            siblings.append(sibling)
            sibling = sibling.next_sibling

        has_content = any(
            hasattr(s, "name") and s.name in ("p", "ul", "ol", "table", "div")
            and s.get_text(strip=True)
            for s in siblings
        )

        if not has_content:
            print(f"[WEBFLOW] Removing empty H2 section: '{h2.get_text(strip=True)[:60]}'")
            h2.decompose()

    return str(soup)


# Competitor brokerages -- their name/domain must never appear inside the
# HREF of a reference/external link (source citation, related links, or any
# link the AI slips into Blog_Content). The name itself is still allowed to
# appear in visible text -- only the link target is blocked.
COMPETITOR_BROKERS = [
    "sahi", "groww", "upstox", "angel one", "angelone", "zerodha",
    "motilal oswal", "anand rathi", "5paisa", "arihant capital",
    "aditya birla money",
]


def _mentions_competitor(text: str) -> bool:
    """True if any competitor brokerage name appears in `text` (case-insensitive)."""
    if not text:
        return False
    lowered = text.lower()
    return any(name in lowered for name in COMPETITOR_BROKERS)


def _strip_competitor_links(html: str) -> str:
    """
    Unwraps any <a href="...">text</a> whose HREF names a competitor
    brokerage, keeping the visible text (the company name may still be
    mentioned in content, just not linked to their site).
    """
    if not html:
        return html

    def _unwrap_if_competitor(match: "re.Match") -> str:
        """Regex callback: return just the inner text (dropping the <a> tag) if the matched link's href names a competitor, else return the match unchanged."""
        href, inner_text = match.group(1), match.group(2)
        if _mentions_competitor(href):
            print(f"[WEBFLOW] Stripped competitor link: {href}")
            return inner_text
        return match.group(0)

    return re.sub(
        r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
        _unwrap_if_competitor,
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )


def _get_source_display_name(source_url: str) -> str:
    """
    Dynamically derives a human-readable source name directly from
    the Blog_Links URL -- no hardcoded map needed.

    Examples:
        https://economictimes.indiatimes.com/...  -> "Economic Times"
        https://www.ndtvprofit.com/...            -> "Ndtvprofit"
        https://www.business-standard.com/...    -> "Business Standard"
        https://www.5paisa.com/...               -> "5paisa"
        https://pulse.zerodha.com/...            -> "Zerodha"
    """
    if not source_url:
        return ""
    try:
        from urllib.parse import urlparse
        netloc = urlparse(source_url).netloc.lower()
        netloc = re.sub(r"^(www\.|pulse\.|m\.|news\.)", "", netloc)
        domain_part = netloc.split(".")[0]
        display = domain_part.replace("-", " ").replace("_", " ").title()
        return display
    except Exception:
        return ""


# def _build_source_reference_html(source_url: str, source_name: str) -> str:
#     """
#     Builds a single clickable "Reference:" attribution line.
#     Label is always "Reference" -- consistent for both blockquote and
#     conclusion placements. Source name is derived from the actual URL domain.
#     """
#     if not source_url:
#         return ""

#     display_name = source_name if source_name else "Source"

#     return (
#         f'<p><em>Reference 1: '
#         f'<a href="{source_url}" rel="noopener" target="_blank">{display_name}</a>'
#         f'</em></p>'
#     )


def _build_source_reference_html(source_url: str, source_name: str) -> str:
    """
    Builds source attribution in two-line format:
 
    Reference :
    1 : Business Standard   ← clickable
    """
    if not source_url:
        return ""
 
    display_name = source_name if source_name else "Source"
 
    return (
        f'<p><em>Reference :</em></p>'
        f'<p><em>1 : <a href="{source_url}" rel="noopener" target="_blank">{display_name}</a></em></p>'
    )


def _inject_source_reference(html: str, source_url: str, source_name: str) -> str:
    """
    Injects a single clickable "Reference:" attribution into Blog_Content.

    Rules:
    - Derive display name from URL domain (not from entry["source"])
    - If <blockquote> exists -> inject after FIRST </blockquote>
    - If no <blockquote>    -> inject at end of Conclusion (before CTA)
    - Never inject if reference already present (prevents duplicates)
    """
    if not source_url:
        return html

    if _mentions_competitor(source_url) or _mentions_competitor(source_name):
        print(f"[WEBFLOW] Source is a competitor brokerage -- skipping reference link: {source_url}")
        return html

    display_name = _get_source_display_name(source_url) or source_name or "Source"

    if "Reference :" in html and source_url in html:
        print(f"[WEBFLOW] Source reference already present -- skipping duplicate")
        return html

    ref_html = _build_source_reference_html(source_url, display_name)

    blockquote_match = re.search(r"</blockquote>", html, flags=re.IGNORECASE)
    if blockquote_match:
        insert_pos = blockquote_match.start()
        print(f"[WEBFLOW] Reference injected after blockquote: {display_name}")
        return html[:insert_pos] + ref_html + html[insert_pos:]

    conclusion_match = re.search(
        r"<h2[^>]*>\s*Conclusion\s*</h2>",
        html,
        flags=re.IGNORECASE
    )
    if conclusion_match:
        after_conclusion = html[conclusion_match.start():]
        last_p           = after_conclusion.rfind("</p>")
        if last_p != -1:
            insert_pos = conclusion_match.start() + last_p + len("</p>")
            print(f"[WEBFLOW] Reference injected at end of Conclusion: {display_name}")
            return html[:insert_pos] + ref_html + html[insert_pos:]

    return html + ref_html


def _enhance_blockquotes(html: str) -> str:
    """Add inline CSS (red left border, light-red background) to every <blockquote> that doesn't already have `border-left` styling, for expert-opinion callouts."""
    BLOCKQUOTE_STYLE = (
        "border-left:4px solid #D8312F;"
        "background:#FEF2F2;"
        "padding:16px 20px;"
        "margin:20px 0;"
        "border-radius:4px;"
    )

    def _style_quote(m):
        """Regex callback: inject the blockquote style attribute unless one is already present."""
        bq = m.group(0)
        if "border-left" in bq:
            return bq
        return re.sub(
            r"<blockquote[^>]*>",
            f'<blockquote style="{BLOCKQUOTE_STYLE}">',
            bq,
            flags=re.IGNORECASE
        )

    return re.sub(
        r"<blockquote[^>]*>.*?</blockquote>",
        _style_quote,
        html,
        flags=re.IGNORECASE | re.DOTALL
    )


def _enhance_tables(html: str) -> str:
    """
    Style every <table> in `html` with inline CSS (borders, padding, fixed
    layout), skipping tables that already have `border-collapse` set.
    Also wraps a bare leading row in <thead> and the remaining rows in
    <tbody> if those wrapper tags are missing.
    """
    import re as _re

    TABLE_STYLE = "width:100%;border-collapse:collapse;table-layout:fixed;margin:16px 0;"
    TH_STYLE    = "border:1px solid #ddd;padding:10px;text-align:left;font-weight:600;background:#f9f9f9;word-wrap:break-word;"
    TD_STYLE    = "border:1px solid #ddd;padding:10px;text-align:left;vertical-align:top;word-wrap:break-word;"

    def _upgrade_table(m):
        """Regex callback: add thead/tbody wrappers (if absent) and inline styles to one matched <table>...</table> block."""
        t = m.group(0)
        if "border-collapse" in t:
            return t
        if "<thead>" not in t.lower():
            t = _re.sub(
                r"(<table[^>]*>)\s*(<tr[^>]*>(?:(?!</tr>).)*?</tr>)",
                lambda m2: m2.group(1) + "<thead>" + m2.group(2) + "</thead>",
                t, count=1, flags=_re.IGNORECASE | _re.DOTALL
            )
        if "<tbody>" not in t.lower():
            thead_end = t.lower().rfind("</thead>")
            if thead_end != -1:
                after     = t[thead_end + len("</thead>"):]
                close_tag = after.rfind("</table>")
                rows      = after[:close_tag].strip()
                end       = after[close_tag:]
                if rows:
                    t = t[:thead_end + len("</thead>")] + "<tbody>" + rows + "</tbody>" + end
        t = _re.sub(r"<table([^>]*)>",
                    lambda m2: f'<table{m2.group(1)} style="{TABLE_STYLE}">',
                    t, flags=_re.IGNORECASE)
        t = _re.sub(r"<th([^>]*)>",
                    lambda m2: f'<th{m2.group(1)} style="{TH_STYLE}">',
                    t, flags=_re.IGNORECASE)
        t = _re.sub(r"<td([^>]*)>",
                    lambda m2: f'<td{m2.group(1)} style="{TD_STYLE}">',
                    t, flags=_re.IGNORECASE)
        return t

    return _re.sub(
        r"<table[^>]*>.*?</table>",
        _upgrade_table,
        html,
        flags=_re.IGNORECASE | _re.DOTALL
    )


def _validate_content(html: str, name: str) -> list:
    """
    Check final `html` (for blog `name`) for publish-blocking problems: empty
    H2 sections, a missing/placeholder Conclusion, and content that's too
    short (<300 plain-text chars). Returns a list of human-readable issue
    strings (empty list = no issues). Used by post_entry_as_draft() to decide
    whether to publish live or leave the item as a draft.
    """
    import re as _re
    issues = []

    empty_h2 = _re.findall(
        r"<h2[^>]*>(.*?)</h2>\s*(?:<h2|$)",
        html,
        flags=_re.IGNORECASE | _re.DOTALL
    )
    for heading in empty_h2:
        clean = _re.sub(r"<[^>]+>", "", heading).strip()
        issues.append(f"Empty H2 section: '{clean[:60]}'")

    PLACEHOLDER_PHRASES = (
        "published without a generated conclusion",
        "please review and add a conclusion",
        "this article was published without",
    )

    conclusion_match = _re.search(
        r"<h2[^>]*>\s*Conclusion\s*</h2>(.*?)(?=<h2|$)",
        html,
        flags=_re.IGNORECASE | _re.DOTALL
    )
    if conclusion_match:
        conclusion_body = conclusion_match.group(1).strip()
        conclusion_text = _re.sub(r"<[^>]+>", "", conclusion_body).strip().lower()
        if not _re.search(r"<p[^>]*>.+?</p>", conclusion_body, _re.IGNORECASE | _re.DOTALL):
            issues.append("Conclusion section has no paragraph content")
        elif any(phrase in conclusion_text for phrase in PLACEHOLDER_PHRASES):
            issues.append("Conclusion is a placeholder -- LLM never generated real content")
    else:
        issues.append("Conclusion section is missing entirely")

    plain_text = _re.sub(r"<[^>]+>", "", html).strip()
    if len(plain_text) < 300:
        issues.append(f"Content too short: only {len(plain_text)} characters")

    return issues


def _clean_conclusion(html: str) -> str:
    """
    Strip stray FAQ leftovers from inside the Conclusion section: <h4> sub-
    headings, "Q:" style paragraphs, a literal "Frequently Asked Questions"
    string, and a "Conclusion Paragraph N:" label prefix, then collapse
    repeated whitespace. No-op if there's no Conclusion heading.
    """
    import re as _re

    conclusion_match = _re.search(
        r"(<h2[^>]*>\s*Conclusion\s*</h2>)(.*?)$",
        html,
        flags=_re.IGNORECASE | _re.DOTALL
    )
    if not conclusion_match:
        return html

    before_conclusion = html[:conclusion_match.start()]
    conclusion_tag    = conclusion_match.group(1)
    conclusion_body   = conclusion_match.group(2)

    conclusion_body = _re.sub(r"<h4[^>]*>.*?</h4>", "", conclusion_body,
                               flags=_re.IGNORECASE | _re.DOTALL)
    conclusion_body = _re.sub(r"<p[^>]*>\s*(?:\d+\)?\s*)?Q[:\.].*?</p>", "", conclusion_body,
                               flags=_re.IGNORECASE | _re.DOTALL)
    conclusion_body = _re.sub(r"Frequently Asked Questions", "", conclusion_body,
                               flags=_re.IGNORECASE)

    conclusion_body = _re.sub(
        r"(<p[^>]*>)\s*Conclusion\s*(?:Paragraph\s*)?\d*\s*:\s*",
        r"\1",
        conclusion_body,
        flags=_re.IGNORECASE
    )

    conclusion_body = _re.sub(r"\s{2,}", " ", conclusion_body).strip()

    return before_conclusion + conclusion_tag + conclusion_body


def _strip_existing_faq(html: str) -> str:
    """Remove any LLM-generated FAQ block (an "FAQ"/"Frequently Asked Questions" <h2> section, plus any leftover <h4> Q/A pairs elsewhere) so the schema-derived FAQ can be injected cleanly instead."""
    import re as _re

    html = _re.compile(
        r"<h2[^>]*>\s*(?:FAQ|Frequently Asked Questions)[^<]*</h2>.*?(?=<h2|$)",
        flags=_re.IGNORECASE | _re.DOTALL
    ).sub("", html)

    html = _re.compile(
        r"<h4[^>]*>.*?</h4>\s*(?:<p[^>]*>.*?</p>)?",
        flags=_re.IGNORECASE | _re.DOTALL
    ).sub("", html)

    return html


# -- Image upload ---------------------------------------------------------------

def upload_image(file_path: Path) -> str | None:
    """
    Upload a local image file to Webflow's asset storage: pre-sign via the
    Webflow API, then POST the file bytes directly to the returned S3
    bucket. Returns the hosted asset URL, or None if the token/file is
    missing or any step of the upload fails (logged, not raised).
    """
    if not TOKEN:
        print("[WEBFLOW] Skipping image upload -- WEBFLOW_API_TOKEN not set")
        return None
    if not file_path.exists():
        print(f"[WEBFLOW] Image file not found: {file_path}")
        return None
    try:
        r = requests.post(
            f"{BASE}/sites/{SITE_ID}/assets",
            headers=_headers(),
            json={"fileName": file_path.name, "fileHash": _md5_b64(file_path)},
            timeout=30,
        )
        if r.status_code >= 400:
            print(f"[WEBFLOW] Asset pre-sign failed ({r.status_code}): {r.text[:150]}")
            return None

        data       = r.json()
        details    = data.get("uploadDetails", {})
        hosted_url = data.get("hostedUrl", "")
        bucket     = details.pop("bucket", "webflow-prod-assets")

        print(f"[WEBFLOW] Asset hostedUrl: {hosted_url[:80] if hosted_url else 'NOT FOUND'}")

        file_bytes = file_path.read_bytes()
        fields = {k: (None, v) for k, v in details.items()}
        fields["file"] = (file_path.name, file_bytes, "image/webp")

        s3 = requests.post(
            f"https://{bucket}.s3.amazonaws.com/",
            files=fields,
            timeout=60,
        )
        if s3.status_code not in (200, 201, 204):
            print(f"[WEBFLOW] S3 upload failed ({s3.status_code}): {s3.text[:100]}")
            return None

        if hosted_url:
            return hosted_url
        s3_key = details.get("key", "")
        return f"https://uploads-ssl.webflow.com/{s3_key}"

    except Exception as e:
        print(f"[WEBFLOW] Image upload error: {e}")
        return None


# -- Publish item -----------------------------------------------------------

def _publish_item(item_id: str) -> bool:
    """Publish a previously-created Webflow CMS item live via the collection publish endpoint. Returns True on success, False on any HTTP error or exception."""
    try:
        r = requests.post(
            f"{BASE}/collections/{COLLECTION_ID}/items/publish",
            headers=_headers(),
            json={"itemIds": [item_id]},
            timeout=30,
        )
        if r.status_code in (200, 201, 202, 204):
            print(f"[WEBFLOW] Published live: item_id={item_id}")
            return True
        else:
            print(f"[WEBFLOW] Publish failed ({r.status_code}): {r.text[:150]}")
            return False
    except Exception as e:
        print(f"[WEBFLOW] Publish error: {e}")
        return False


# -- Draft creation + publish -------------------------------------------------

def post_entry_as_draft(entry: dict, image_dir: str = "") -> dict:
    """
    Post one pipeline output entry to Webflow CMS and publish it live.

    Content build order:
        1.  _strip_h1()                     -- remove duplicate H1
        2.  _title_case_headings()          -- force Title Case on H2s
        3.  _remove_empty_sections()        -- auto-fix empty H2s
        3b. _inject_app_download_ads()      -- insert app-download promo banners
                                                between body sections
        4.  _build_tldr_html()              -- prepend Key Takeaways
        4b. related links injected here     -- pillar/cluster links
        5.  _strip_existing_faq()           -- remove LLM FAQ
        6.  _inject_faq_before_conclusion() -- inject clean FAQ from schema
        7.  _clean_conclusion()             -- strip misplaced FAQ from Conclusion
        8.  _inject_cta_after_conclusion()  -- add CTA link
        9.  _inject_source_reference()      -- add clickable source attribution
                                                (skipped if source is a competitor brokerage)
        10. _enhance_blockquotes()          -- style expert opinion callouts
        11. _enhance_tables()               -- style tables with inline CSS
        12. _strip_competitor_links()       -- unwrap any remaining link to a
                                                competitor brokerage (name may
                                                still appear in visible text)

    After successful publish:
        - save_webflow_url()   -- captures the real live URL
        - add_blog_to_graph()  -- registers this blog into keyword_graph.json
    """
    if not TOKEN:
        return {"error": "WEBFLOW_API_TOKEN not set"}

    blog       = entry.get("blog", {})
    name       = blog.get("Blog_Title", entry.get("Blog_Title", "Untitled"))

    name = _title_case_name(name)

    slug       = _make_slug(name)
    meta_title = blog.get("Meta_Title", name)
    meta_desc  = blog.get("Meta_Description", "")
    faq_schema = blog.get("FAQ_Schema", {})
    tldr       = blog.get("TLDR", [])

    now_ist = _now_ist_iso()
    print(f"[WEBFLOW] Post datetime (IST): {now_ist}")

    # -- Build full content -----------------------------------------------------
    raw_content = blog.get("Blog_Content", "")
    raw_content = _strip_h1(raw_content)
    raw_content = _title_case_headings(raw_content)
    raw_content = _remove_empty_sections(raw_content)
    raw_content = _inject_app_download_ads(raw_content)
    raw_content = _build_tldr_html(tldr) + raw_content

    # -- Related links -- matched against keyword_graph.json --------------------
    try:
        graph = load_graph()
        related_links = get_related_links(
            entry.get("primary_keyword"),
            entry.get("secondary_keywords"),
            graph,
        )
        related_html = build_related_links_html(related_links)
        raw_content = _inject_related_links_before_conclusion(raw_content, related_html)
        if related_links:
            print(f"[GRAPH] Injected {len(related_links)} related link(s) into: {name[:60]}")
    except Exception as e:
        print(f"[GRAPH] WARN: related links step failed, continuing without them: {e}")
    # ---------------------------------------------------------------------------

    raw_content = _strip_existing_faq(raw_content)
    raw_content = _inject_faq_before_conclusion(raw_content, _build_faq_html(faq_schema))
    raw_content = _clean_conclusion(raw_content)
    raw_content = _inject_cta_after_conclusion(raw_content, _build_cta_html(name))

    # -- Source reference -- clickable attribution to original article ----------
    source_url  = entry.get("Blog_Links", "")
    source_name = entry.get("source_name", "")
    raw_content = _inject_source_reference(raw_content, source_url, source_name)
    # ---------------------------------------------------------------------------

    raw_content = _enhance_blockquotes(raw_content)
    raw_content = _enhance_tables(raw_content)
    content     = _strip_competitor_links(raw_content)
    faq_script_html = _faq_script(faq_schema) if faq_schema else ""

    # -- Resolve WebP image paths -------------------------------------------------
    webp_dir     = IMAGE_WEBP_DIR
    thumb_server = entry.get("blog_image", {}).get("webp", "")
    cover_server = entry.get("blog_image_inner", {}).get("webp", "")

    thumb_url = cover_url = None

    if webp_dir and thumb_server:
        thumb_path = _local_path(webp_dir, thumb_server)
        print(f"[WEBFLOW] Thumbnail path resolved: {thumb_path}")
        thumb_url = upload_image(thumb_path)
        if thumb_url:
            print(f"[WEBFLOW] Thumbnail uploaded (WebP): {thumb_path.name}")
        else:
            print(f"[WEBFLOW] Thumbnail upload failed or file missing: {thumb_path}")

    if webp_dir and cover_server:
        cover_path = _local_path(webp_dir, cover_server)
        print(f"[WEBFLOW] Cover path resolved:     {cover_path}")
        cover_url = upload_image(cover_path)
        if cover_url:
            print(f"[WEBFLOW] Cover uploaded (WebP):     {cover_path.name}")
        else:
            print(f"[WEBFLOW] Cover upload failed or file missing: {cover_path}")

    # -- Build Webflow field payload ----------------------------------------------
    field_data: dict = {
        "name":                 name,
        "slug":                 slug,
        "content":              content,
        "title-tag-seo":        meta_title,
        "meta-description-seo": meta_desc,
        "posted-date":          now_ist,
        "post-modified-date":   now_ist,
        "categories":           ALL_BLOG_CATEGORY_ID,
        "author-username":      AUTHOR_USERNAME,
        "author-email":         AUTHOR_EMAIL,
        "author-first-name":    AUTHOR_FIRST_NAME,
        "author-last-name":     AUTHOR_LAST_NAME,
    }
    if faq_script_html:
        field_data["faq-schema-script-2"] = faq_script_html
    if thumb_url:
        field_data["blog-thumbnail-image"] = {"url": thumb_url, "alt": name}
    if cover_url:
        field_data["blog-cover-image"] = {"url": cover_url, "alt": name}

    payload = {
        "isArchived": False,
        "isDraft":    False,
        "fieldData":  field_data,
    }

    # -- POST to Webflow CMS --------------------------------------------------------
    try:
        r = requests.post(
            f"{BASE}/collections/{COLLECTION_ID}/items",
            headers=_headers(),
            json=payload,
            timeout=30,
        )
        data = r.json()
        if r.status_code >= 400:
            return {"error": True, "status": r.status_code, "detail": data}

        item_id = data.get("id")

        issues = _validate_content(content, name)

        if issues:
            print(f"[WEBFLOW] Content issues found -- saved as DRAFT (not published):")
            for issue in issues:
                print(f"[WEBFLOW]    - {issue}")
            return {
                "item_id":    item_id,
                "name":       data.get("fieldData", {}).get("name", name),
                "slug":       data.get("fieldData", {}).get("slug", slug),
                "isDraft":    True,
                "published":  False,
                "issues":     issues,
                "posted_date": now_ist,
                "thumb":      thumb_url or "not uploaded",
                "cover":      cover_url or "not uploaded",
                "author":     AUTHOR_USERNAME,
            }

        published = _publish_item(item_id)
        if published:
            actual_slug = data.get("fieldData", {}).get("slug", slug)
            webflow_url = f"https://{SITE_DOMAIN}/blog/{actual_slug}"
            try:
                save_webflow_url(
                    blog_links=entry.get("Blog_Links"),
                    webflow_url=webflow_url,
                    generated_title=entry.get("blog", {}).get("Blog_Title"),
                )
            except Exception as e:
                print(f"[WEBFLOW] WARN: could not save webflow_url to output.json: {e}")

            try:
                add_blog_to_graph(
                    webflow_url=webflow_url,
                    title=name,
                    primary_keyword=entry.get("primary_keyword"),
                    secondary_keywords=entry.get("secondary_keywords"),
                )
            except Exception as e:
                print(f"[GRAPH] WARN: could not add blog to keyword_graph.json: {e}")

        return {
            "item_id":   item_id,
            "name":      data.get("fieldData", {}).get("name", name),
            "slug":      data.get("fieldData", {}).get("slug", slug),
            "isDraft":   False,
            "published": published,
            "issues":    [],
            "posted_date": now_ist,
            "thumb":     thumb_url or "not uploaded",
            "cover":     cover_url or "not uploaded",
            "author":    AUTHOR_USERNAME,
        }
    except Exception as e:
        return {"error": str(e)}


def post_results_as_drafts(results: list, image_dir: str = "") -> list:
    """
    Post and publish a list of pipeline result entries to Webflow.
    Called by scheduler.py after run_pipeline() returns.
    """
    posted = []
    for entry in results:
        name = entry.get("blog", {}).get("Blog_Title", entry.get("Blog_Title", "?"))
        print(f"[WEBFLOW] Posting & publishing: {name[:60]}")
        result = post_entry_as_draft(entry, image_dir)
        if result.get("error"):
            print(f"[WEBFLOW] FAILED: {result}")
        else:
            print(
                f"[WEBFLOW] Live -- item_id={result.get('item_id')} | "
                f"published={result.get('published')} | "
                f"posted_date={result.get('posted_date')} | "
                f"author={result.get('author')} | "
                f"thumb={result.get('thumb')} | "
                f"cover={result.get('cover')}"
            )
        posted.append(result)
    return posted