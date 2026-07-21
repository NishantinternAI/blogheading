import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__))) # ← adds generators/ to path
import json
import re
from bs4 import BeautifulSoup
from add_cached import cached_model_call
from utils.mcp_tools import fetch_and_clean
from add_cached import cached_model_call, fetch_via_websearch
from priAndsec_keywords import extract_keywords
from keyword_researcher import get_keyword_volumes 
from json_repair import repair_json


# ══════════════════════════════════════════════════════════════
#  POST-PROCESSORS
# ══════════════════════════════════════════════════════════════

def fix_em_dash(text: str) -> str:
    """Replace em-dashes (raw char, &mdash;, &#8212;) with en-dashes. Returns the fixed string."""
    text = text.replace('\u2014', '\u2013')
    text = text.replace('&mdash;', '\u2013')
    text = text.replace('&#8212;', '\u2013')
    return text


def fix_tldr_h2(html: str) -> str:
    """Remove a stray bare '<h2>TLDR</h2>' heading from Blog_Content (the TLDR list itself is kept)."""
    html = re.sub(r'<h2[^>]*>\s*TLDR\s*</h2>', '', html, flags=re.IGNORECASE)
    return html


def fix_faq_tags(html: str) -> str:
    """Downgrade <h3> question tags to <h4> everywhere after the FAQ/'Frequently Asked Questions' <h2>, since FAQ questions must be <h4>."""
    faq_pattern = re.compile(
        r'(<h2[^>]*>.*?(?:frequently asked questions|faq).*?</h2>)',
        re.IGNORECASE | re.DOTALL
    )
    match = faq_pattern.search(html)
    if not match:
        return html
    before_faq  = html[:match.end()]
    faq_section = html[match.end():]
    faq_section = re.sub(r'<h3([^>]*)>', r'<h4\1>', faq_section)
    faq_section = re.sub(r'</h3>', '</h4>', faq_section)
    return before_faq + faq_section


def fix_faq_h2_keyword(html: str, blog_title: str) -> str:
    """
    Rewrite a bare '<h2>FAQ</h2>' / '<h2>Frequently Asked Questions</h2>' heading into
    'Frequently Asked Questions – <keyword> For Investors', deriving the keyword from the
    first few non-stopword tokens of blog_title. Leaves the heading untouched if it already
    has extra text (not a bare match) or blog_title yields no usable words (falls back to "Finance").
    """
    STOP = {
        'should','you','buy','sell','now','is','are','was','were',
        'the','a','an','in','on','for','your','this','that','these',
        'it','how','what','why','will','can','could','would','do',
        'does','did','has','have','had','be','been','at','by',
        'from','with','or','and','but','if','so','as','not','no',
        'its','also','just','after','before','today','act','rebalance',
        'improve','check','test','watch','rise','fall','may','june',
        'july','august','september','october','november','december'
    }
    clean = re.sub(r'[\u2013\u2014\-\?!\|]', ' ', blog_title)
    words = [w for w in clean.split() if w.lower() not in STOP and len(w) > 2]
    keyword = ' '.join(words[:4]) if words else 'Finance'

    bare_faq = re.compile(
        r'(<h2[^>]*>)\s*((?:frequently asked questions|faq))\s*(</h2>)',
        re.IGNORECASE
    )
    match = bare_faq.search(html)
    if match:
        replacement = (
            f'{match.group(1)}'
            f'Frequently Asked Questions \u2013 {keyword} For Investors'
            f'{match.group(3)}'
        )
        html = html[:match.start()] + replacement + html[match.end():]
    return html


def fix_placeholder_h3(html: str) -> str:
    """
    Remove known generic/template <h3> subheadings (e.g. "What this means for your
    portfolio") that the model sometimes leaves in verbatim instead of a real subheading.
    If the placeholder is followed by a <ul>, the heading is dropped entirely; if followed
    by a <p>, the heading is replaced with a short (<=65 char) heading derived from that
    paragraph's first ~10 words; otherwise the heading is just removed.
    """
    PLACEHOLDER_PATTERNS = [
        r'<h3[^>]*>\s*How this affects sector allocations in your portfolio\s*</h3>',
        r'<h3[^>]*>\s*Which sectors could be affected the most\s*</h3>',
        r'<h3[^>]*>\s*Which specific stocks[^<]*are affected[^<]*</h3>',
        r'<h3[^>]*>\s*HOW does this specific event affect YOUR holdings[^<]*</h3>',
        r'<h3[^>]*>\s*How does this event affect YOUR holdings[^<]*</h3>',
        r'<h3[^>]*>\s*Which stocks[/]sectors are affected[^<]*</h3>',
        r'<h3[^>]*>\s*WHICH specific stocks[^<]*</h3>',
        r'<h3[^>]*>\s*What caused it[^<]*deeper context[^<]*</h3>',
        r'<h3[^>]*>\s*What this means for your portfolio\s*</h3>',
        r'<h3[^>]*>\s*Why this matters for investors\s*</h3>',
        r'<h3[^>]*>\s*What happened[^<]*simple explanation[^<]*</h3>',
        r'<h3[^>]*>\s*Sectors to watch[^<]*priority order[^<]*</h3>',
    ]
    for pattern in PLACEHOLDER_PATTERNS:
        h3_match = re.search(pattern, html, re.IGNORECASE)
        if h3_match:
            after = html[h3_match.end():]
            if after.lstrip().startswith('<ul'):
                html = html[:h3_match.start()] + html[h3_match.end():]
            elif after.lstrip().startswith('<p'):
                p_match = re.match(r'\s*<p[^>]*>(.*?)</p>', after,
                                   re.IGNORECASE | re.DOTALL)
                if p_match:
                    p_text = re.sub(r'<[^>]+>', '', p_match.group(1))
                    words  = p_text.split()[:10]
                    text   = ' '.join(words)
                    if len(text) > 65:
                        text = text[:62]
                    new_h3 = '<h3>' + text + '</h3>'
                    html = html[:h3_match.start()] + new_h3 + html[h3_match.end():]
                else:
                    html = html[:h3_match.start()] + html[h3_match.end():]
            else:
                html = html[:h3_match.start()] + html[h3_match.end():]
    return html


def fix_duplicate_swastika(html: str) -> str:
    """
    Keep only the first Swastika reference in Blog_Content.
    Matches any <p> containing 'Swastika' — with or without 'Investmart',
    covering 'Swastika's Sarthi', 'Swastika's platform', etc.
    """
    swastika_pattern = re.compile(
        r'<p>[^<]*[Ss]wastika[^<]*(?:<[^/][^>]*>[^<]*</[^>]+>[^<]*)*</p>',
        re.IGNORECASE | re.DOTALL
    )
    matches = list(swastika_pattern.finditer(html))
    if len(matches) > 1:
        for match in reversed(matches[1:]):
            html = html[:match.start()] + html[match.end():]
    return html


def fix_table_na(html: str) -> str:
    """Replace empty/placeholder table cells (N/A, NA, None, -, --, or blank) with 'To be announced'."""
    html = re.sub(
        r'<td>\s*(?:N/A|n/a|NA|na|None|-|--)\s*</td>',
        '<td>To be announced</td>', html
    )
    html = re.sub(r'<td>\s*</td>', '<td>To be announced</td>', html)
    return html


# def fix_remove_non_ipo_table(html: str, source: str) -> str:
#     """Remove tables from non-IPO articles only."""
#     if source == "nse_ipo":
#         return html
#     html = re.sub(r'<table.*?</table>', '', html,
#                   flags=re.IGNORECASE | re.DOTALL)
#     return html


def fix_garbage_characters(text: str) -> str:
    """Strip non-ASCII characters the model sometimes emits (mojibake, stray symbols) down to spaces, keeping only ASCII plus a small allowlist (rupee sign, dashes, degree, curly quotes, ellipsis); also collapses resulting double spaces."""
    cleaned = ''
    for char in text:
        code = ord(char)
        if (code < 128 or char in '\u20b9\u2013\u2014\xb0\u201c\u201d\u2018\u2019\u2026'):
            cleaned += char
        else:
            cleaned += ' '
    cleaned = re.sub(r'  +', ' ', cleaned)
    return cleaned


def fix_nested_p_tags(html: str) -> str:
    """Remove nested <p> tags: <p><p>text</p></p> → <p>text</p>"""
    html = re.sub(r'<p>\s*<p>', '<p>', html)
    html = re.sub(r'</p>\s*</p>', '</p>', html)
    return html


def fix_meta_length(data: dict) -> dict:
    """Hard-truncate Meta_Title (60 chars) and Meta_Description (155 chars)."""
    if data.get("Meta_Title") and len(data["Meta_Title"]) > 60:
        data["Meta_Title"] = data["Meta_Title"][:57].rstrip() + "..."
    if data.get("Meta_Description") and len(data["Meta_Description"]) > 155:
        data["Meta_Description"] = data["Meta_Description"][:152].rstrip() + "..."
    return data


def fix_faq_schema_answers(data: dict) -> dict:
    """Strip HTML tags from FAQ_Schema acceptedAnswer text fields."""
    entities = data.get("FAQ_Schema", {}).get("mainEntity", [])
    for entity in entities:
        answer_obj = entity.get("acceptedAnswer", {})
        raw_text   = answer_obj.get("text", "")
        if raw_text:
            answer_obj["text"] = BeautifulSoup(
                raw_text, "html.parser"
            ).get_text(strip=True)
    return data


def fix_strip_tldr_from_content(html: str) -> str:
    """
    Removes TLDR / Key Takeaways block from Blog_Content.
    Case A — wrapped in <h2>TLDR</h2> or <h2>Key Takeaways</h2>
    Case B — bare <ul>/<ol> dumped directly after <h1> with no wrapper
    """
    soup = BeautifulSoup(html, "html.parser")

    TLDR_PREFIXES = ("tldr", "key takeaways")
    for h2 in soup.find_all("h2"):
        if h2.get_text(strip=True).lower().startswith(TLDR_PREFIXES):
            current = h2.next_sibling
            while current:
                next_node = current.next_sibling
                if hasattr(current, "name") and current.name == "h2":
                    break
                if hasattr(current, "decompose"):
                    current.decompose()
                current = next_node
            h2.decompose()

    first_h2 = soup.find("h2")
    if first_h2:
        for tag in first_h2.find_all_previous(["ul", "ol"]):
            tag.decompose()

    return str(soup).strip()


def fix_conclusion_labels(html: str) -> str:
    """
    Removes inline label prefixes that the model writes inside conclusion
    paragraphs — e.g. 'Conclusion:', 'Takeaway:', 'Key takeaway:',
    'In summary:', 'Summary:' — leaving only the clean prose that follows.

    Also removes duplicate conclusion paragraphs that just restate the
    heading (e.g. a <p> that starts with 'Conclusion:' when <h2>Conclusion
    </h2> already exists).
    """
    LABEL_PATTERN = re.compile(
    r'^\s*(?:conclusion|takeaway|key takeaway|in summary|summary'
    r'|final thought|final recommendation|bottom line)'
    r'(?:\s+paragraph\s*\d+|\s*\d+)?\s*:\s*',
    re.IGNORECASE
    )

    soup = BeautifulSoup(html, "html.parser")

    conclusion_h2 = None
    for h2 in soup.find_all("h2"):
        if h2.get_text(strip=True).lower().startswith("conclusion"):
            conclusion_h2 = h2
            break

    if not conclusion_h2:
        return html

    # Walk paragraphs inside the conclusion section
    current = conclusion_h2.next_sibling
    while current:
        next_node = current.next_sibling
        if hasattr(current, "name"):
            if current.name == "h2":
                break
            if current.name == "p":
                raw = current.decode_contents()
                # Strip the label prefix from the paragraph text
                cleaned = LABEL_PATTERN.sub("", raw).strip()
                if cleaned:
                    current.clear()
                    current.append(BeautifulSoup(cleaned, "html.parser"))
                else:
                    # Paragraph was only the label — remove it entirely
                    current.decompose()
        current = next_node

    return str(soup).strip()


def fix_swastika_paragraph_start(html: str) -> str:
    """Prevent <p> tags that open with 'Swastika' as the first word."""
    return re.sub(
        r'(<p>)(Swastika)',
        r'\1For stock-level analysis, \2',
        html,
        flags=re.IGNORECASE,
    )


def fix_swastika_heading(html: str) -> str:
    """
    Removes any H2/H3/H4 that contains 'Swastika' in its text.
    The model occasionally creates a branded section header like:
    <h2>Swastika's insights: how to gauge entry levels</h2>
    which is never valid — Swastika references must appear in <p> only.

    The heading is removed along with any empty content that follows
    before the next heading.
    """
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup.find_all(["h2", "h3", "h4"]):
        if "swastika" in tag.get_text(strip=True).lower():
            # Remove any immediately following empty or Swastika-only paragraphs
            current = tag.next_sibling
            while current:
                next_node = current.next_sibling
                if hasattr(current, "name"):
                    if current.name in ("h2", "h3", "h4"):
                        break
                    if current.name == "p":
                        text = current.get_text(strip=True)
                        # Only remove if the paragraph is empty or also Swastika-branded
                        if not text or "swastika" in text.lower():
                            current.decompose()
                        else:
                            break
                current = next_node
            tag.decompose()

    return str(soup).strip()


def fix_faq_before_conclusion(html: str) -> str:
    """
    If FAQ appears after Conclusion in Blog_Content, swap them
    so stored JSON always follows: body → FAQ → Conclusion.
    The dashboard re-appends both sections in correct order,
    but fixing it in stored JSON keeps the data canonical.
    """
    soup = BeautifulSoup(html, "html.parser")

    conclusion_h2 = None
    faq_h2        = None

    for h2 in soup.find_all("h2"):
        text = h2.get_text(strip=True).lower()
        if text.startswith("conclusion") and conclusion_h2 is None:
            conclusion_h2 = h2
        if (text.startswith("faq") or text.startswith("frequently")) and faq_h2 is None:
            faq_h2 = h2

    if not conclusion_h2 or not faq_h2:
        return html

    all_h2s       = soup.find_all("h2")
    conclusion_pos = all_h2s.index(conclusion_h2)
    faq_pos        = all_h2s.index(faq_h2)

    # Already in correct order
    if faq_pos < conclusion_pos:
        return html

    # Extract entire FAQ block (h2 + all siblings until next h2)
    faq_block = [faq_h2]
    current   = faq_h2.next_sibling
    while current:
        next_node = current.next_sibling
        if hasattr(current, "name") and current.name == "h2":
            break
        faq_block.append(current.extract())
        current = next_node

    # Insert FAQ block before the Conclusion h2
    for node in reversed(faq_block):
        conclusion_h2.insert_before(node)
    faq_h2.extract()

    return str(soup).strip()


def fix_ensure_conclusion(html: str) -> str:
    """
    Ensures Blog_Content has a properly tagged <h2>Conclusion</h2>
    with real content after it.

    Case A — properly tagged, real content follows             → do nothing
    Case E — conclusion h2 exists but nothing follows it       → look backwards
             (model stopped writing after the heading)           for real paragraphs,
                                                                 then fall to Case D
    Case B — tag exists, placeholder follows, real paragraphs  → move real paragraphs
             sit BEFORE the tag                                   from before to after
    Case C — conclusion-like paragraph exists after FAQ        → insert <h2> above it
             but has no heading
    Case D — no conclusion at all                              → append placeholder
    """
    PLACEHOLDER = "this article was published without a generated conclusion"
    CONCLUSION_SIGNALS = (
        "next step", "in summary", "to summarise", "to summarize",
        "the bottom line", "the key takeaway", "for retail investors",
        "approach with", "worth applying", "wait for listing",
        "the single most", "what to do next", "going forward",
        "overall,", "ultimately,", "in conclusion",
        "the takeaway", "to conclude", "presents a", "mental model",
        "watch the listing", "treat this as", "wait for more",
        "monitor the official", "optimal move",
    )

    soup = BeautifulSoup(html, "html.parser")

    conclusion_h2 = None
    for h2 in soup.find_all("h2"):
        if h2.get_text(strip=True).lower().startswith("conclusion"):
            conclusion_h2 = h2
            break

    if conclusion_h2:
        next_p      = conclusion_h2.find_next_sibling("p")
        next_p_text = next_p.get_text(strip=True).lower() if next_p else ""

        # Case A: real content already follows the tag
        if next_p and PLACEHOLDER not in next_p_text:
            return str(soup).strip()

        # Case E: nothing follows the conclusion h2 at all (model stopped early)
        # OR only a placeholder follows — look backwards for real paragraphs
        real_paragraphs = []
        prev = conclusion_h2.find_previous_sibling()
        while prev and prev.name == "p":
            text = prev.get_text(strip=True).lower()
            if any(signal in text for signal in CONCLUSION_SIGNALS):
                real_paragraphs.insert(0, prev.extract())
                prev = conclusion_h2.find_previous_sibling()
            else:
                break

        if real_paragraphs:
            # Remove placeholder if present
            if next_p and PLACEHOLDER in next_p_text:
                next_p.decompose()
            for p in reversed(real_paragraphs):
                conclusion_h2.insert_after(p)
            return str(soup).strip()

        # No real paragraphs found before the tag either —
        # remove the empty heading and fall through to Case C/D
        # so the function can try to detect a conclusion-like paragraph elsewhere
        conclusion_h2.decompose()
        conclusion_h2 = None

    # Case C: no conclusion h2 — find conclusion-like paragraph after FAQ
    faq_h2 = None
    for h2 in soup.find_all("h2"):
        if h2.get_text(strip=True).lower().startswith(("faq", "frequently")):
            faq_h2 = h2
            break

    if faq_h2:
        current = faq_h2.next_sibling
        while current:
            if hasattr(current, "name"):
                if current.name == "p":
                    p_text = current.get_text(strip=True).lower()
                    if any(signal in p_text for signal in CONCLUSION_SIGNALS):
                        conclusion_tag = BeautifulSoup(
                            "<h2>Conclusion</h2>", "html.parser"
                        ).find("h2")
                        current.insert_before(conclusion_tag)
                        return str(soup).strip()
                elif current.name == "h2":
                    break
            current = current.next_sibling

    # Case D: nothing found anywhere — append placeholder
    if not conclusion_h2:
        fallback = (
            "\n<h2>Conclusion</h2>\n"
            "<p>This article was published without a generated conclusion. "
            "Please review and add a conclusion before publishing.</p>\n"
        )
        faq_match = re.search(
            r"(<h2[^>]*>\s*(?:faq|frequently).*?</h2>.*?)(<h2|$)",
            str(soup), re.IGNORECASE | re.DOTALL,
        )
        if faq_match:
            rebuilt = str(soup)
            insert_pos = faq_match.end(1)
            return rebuilt[:insert_pos] + fallback + rebuilt[insert_pos:]
        return str(soup).strip() + fallback

    return str(soup).strip()



def fix_tldr_list(data: dict) -> dict:
    """
    Strips any HTML tags the LLM accidentally wrote inside TLDR list items.

    The TLDR field is a JSON array of plain strings — e.g.:
        ["238 companies plan ₹4.72 trillion...", "174 SEBI-approved..."]

    But the LLM sometimes wraps them in <li> tags:
        ["<li>238 companies plan ₹4.72 trillion...</li>", ...]

    This causes double <li><li>...</li></li> when _build_tldr_html()
    wraps each item in another <li> tag.
    """
    import re as _re

    tldr = data.get("TLDR", [])
    if not tldr or not isinstance(tldr, list):
        return data

    cleaned = []
    for item in tldr:
        if isinstance(item, str):
            # Strip any HTML tags from inside TLDR strings
            clean = _re.sub(r"<[^>]+>", "", item).strip()
            if clean:
                cleaned.append(clean)
        else:
            cleaned.append(item)

    data["TLDR"] = cleaned
    return data


def fix_html_tags(content: str) -> str:
    """
    Fixes common HTML formatting issues that LLMs produce.
 
    Fixes:
      1. Double <li> tags      : <li><li>text</li></li> → <li>text</li>
      2. Double <p> tags       : <p><p>text</p></p>     → <p>text</p>
      3. Conclusion label      : "Conclusion – Paragraph 1:" → removed
      4. Empty tags            : <p></p>, <li></li>     → removed
      5. Nested same tags      : <h2><h2>text</h2></h2> → <h2>text</h2>
    """
    if not content:
        return content
 
    # 1. Fix double <li> tags — <li><li>text</li></li> → <li>text</li>
    content = re.sub(r'<li>\s*<li>', '<li>', content)
    content = re.sub(r'</li>\s*</li>', '</li>', content)
 
    # 2. Fix double <p> tags — <p><p>text</p></p> → <p>text</p>
    content = re.sub(r'<p>\s*<p>', '<p>', content)
    content = re.sub(r'</p>\s*</p>', '</p>', content)
 
    # 3. Fix nested same heading tags — <h2><h2>text</h2></h2>
    for tag in ['h1', 'h2', 'h3', 'h4']:
        content = re.sub(
            rf'<{tag}>\s*<{tag}>', f'<{tag}>', content
        )
        content = re.sub(
            rf'</{tag}>\s*</{tag}>', f'</{tag}>', content
        )
 
    # 4. Remove conclusion paragraph labels
    # "Conclusion – Paragraph 1:" / "Conclusion - Paragraph 2:"
    content = re.sub(
        r'Conclusion\s*[–\-]\s*Paragraph\s*\d+\s*:?\s*',
        '',
        content,
        flags=re.IGNORECASE
    )
 
    # 5. Remove empty tags
    content = re.sub(r'<(p|li|h[1-4])>\s*</(p|li|h[1-4])>', '', content)
 
    # 6. Fix missing space between closing and opening tags
    content = re.sub(r'</(\w+)><(\w+)', r'</\1> <\2', content)
 
    # 7. Remove H2/H3 headings that have no paragraph content after them
    # Pattern: <h2>title</h2> immediately followed by another <h2> or end of string
    content = re.sub(
        r'<h2>[^<]+</h2>\s*(?=<h2>|<h3>|$)',
        '',
        content
    )
    content = re.sub(
        r'<h3>[^<]+</h3>\s*(?=<h2>|<h3>|$)',
        '',
        content
    )
 
    return content.strip()

# ══════════════════════════════════════════════════════════════
#  fix_all_fields — main pipeline entry point
# ══════════════════════════════════════════════════════════════

def fix_all_fields(data: dict, source: str = "") -> dict:
    """
    Post-processes raw LLM JSON output before storage.

    Pipeline order:
      1.  Meta length enforcement
      2.  FAQ schema answer cleanup
      3.  String-level fixes on all keys (em-dash, garbage chars)
      4.  Blog_Content transformations:
            a. Strip TLDR from content
            b. Nested <p> cleanup
            c. TLDR h2 removal
            d. FAQ tag normalisation (h3→h4 inside FAQ)
            e. FAQ heading keyword enrichment
            f. Placeholder h3 removal
            g. Duplicate Swastika fix        (now matches all Swastika refs)
            h. Swastika paragraph-start fix
            i. Table N/A cleanup
            k. FAQ before Conclusion swap    (new — corrects reversed order)
            l. Ensure conclusion             (tag + real content)
    """
    blog_title = data.get("Blog_Title", "")

    # ── 1. Meta length ────────────────────────────────────────
    data = fix_meta_length(data)

    # ── 2. FAQ schema answer cleanup ─────────────────────────
    data = fix_faq_schema_answers(data)

    data = fix_tldr_list(data)

    # ── 3. String-level fixes ─────────────────────────────────
    for key, value in list(data.items()):

        if isinstance(value, str):
            value = fix_em_dash(value)

            if key in ("Blog_Title", "Meta_Title", "Meta_Description", "Conclusion"):
                value = fix_garbage_characters(value)

            if key == "Blog_Content":
                value = value.replace('\\n', ' ').replace('\n', ' ')  # ← FIRST
                value = fix_strip_tldr_from_content(value)      # a
                value = fix_nested_p_tags(value)                 # b
                value = fix_html_tags(value)
                value = fix_tldr_h2(value)                       # c
                value = fix_faq_tags(value)                      # d
                value = fix_faq_h2_keyword(value, blog_title)    # e
                value = fix_placeholder_h3(value)                # f
                value = fix_duplicate_swastika(value)
                value = fix_swastika_heading(value)            # g
                value = fix_swastika_paragraph_start(value)      # h
                value = fix_table_na(value)                      # i
                # value = fix_remove_non_ipo_table(value, source)  # j
                value = fix_faq_before_conclusion(value)         # k
                value = fix_ensure_conclusion(value)  
                value = fix_conclusion_labels(value)           # l

            data[key] = value

        elif isinstance(value, list):
            data[key] = [
                fix_em_dash(fix_garbage_characters(v))
                if isinstance(v, str) else v
                for v in value
            ]

        elif isinstance(value, dict):
            data[key] = fix_all_fields(value, source="")

    return data


# ══════════════════════════════════════════════════════════════
#  BLOG GENERATORS
# ══════════════════════════════════════════════════════════════




def generate_blog(item: dict) -> dict:
    """
    Generate a full SEO/GEO-optimised blog for a general news item.

    Fetches the source article via fetch_via_websearch(), extracts primary/secondary
    keywords, and looks up their Google search volumes. If every keyword has 0 search
    volume, generation is skipped entirely and {} is returned (no LLM call made).
    Otherwise builds a large prompt (source content + keyword usage rules + structure/SEO
    instructions) and calls cached_model_call(). The raw JSON response is parsed, with a
    json_repair fallback if parsing fails (writing repaired_blog_response.json or, on
    total failure, failed_blog_response.json for debugging); {} is returned if recovery
    fails. On success the dict is passed through fix_all_fields() and annotated with
    primary_keyword / secondary_keywords before being returned.

    Args:
        item: dict expected to contain "Blog_Links" (source URL) and "source".

    Returns:
        Post-processed blog dict, or {} if skipped/unrecoverable.
    """
    url =item["Blog_Links"]
    article_content = fetch_via_websearch(url)
    print(article_content)
    keyword_data = extract_keywords(article_content)
    print("Keywords:", keyword_data)
    volume_data = get_keyword_volumes(
        primary   = keyword_data.get("primary_keyword", ""),
        secondary = keyword_data.get("secondary_keywords", [])
    )
    print("Volumes:", volume_data)
    pk  = volume_data.get("primary_keyword", {})
    sks = volume_data.get("secondary_keywords", [])
    # Only include secondary keywords that have real volume
    valid_secondary = [s for s in sks if s.get("volume", 0) > 0]
    primary_volume = pk.get("volume", 0)
    has_any_volume = primary_volume > 0 or len(valid_secondary) > 0
    if not has_any_volume:
        print(
            f"[BLOG] ⚠️  Skipping — all keywords have 0 search volume.\n"
            f"[BLOG]    Primary  : '{pk.get('original', '')}' → {primary_volume}/mo\n"
            f"[BLOG]    Secondary: all 0 volume — no SEO value in generating this blog."
        )
        return {}

    secondary_lines = "\n".join([
        f'  {i+1}. replace "{s["original"]}" → "{s["google_keyword"]}"  ({s["volume"]:,}/mo)'
        for i, s in enumerate(valid_secondary)
    ])
    keyword_block = f"""

Keyword Usage Rules

Use the provided Google keywords only when they fit naturally and preserve the original meaning.

* Do NOT force keyword replacements.
* If a replacement changes the meaning or makes the sentence unnatural, keep the original wording.
* Do NOT create new sentences solely to insert keywords.
* Avoid repeating the same keyword in consecutive sentences.

Primary Keyword (Mandatory)

Original: "{pk.get('original', '')}"
Preferred: "{pk.get('google_keyword', '')}"
Volume: {pk.get('volume', 0):,}/month
- Must appear in:
  - Blog Title
  - Meta Title
  - First 100 words
  - One H2 heading
- Use naturally 2-3 times throughout the article.

Secondary Keywords:

- Try to use each keyword at least once.
- Place them naturally across:
  - H2/H3/H4 headings
  - Paragraphs
  - Tables
  - FAQs
- Do not force insertion.
- Skip any keyword that does not fit the context.

Keyword distribution should feel natural and improve readability.

{secondary_lines if secondary_lines else "No secondary keywords available."}
"""

    prompt = f"""
You are a SEO & GEO Blog strategist writing for Swastika Investmart — 
a SEBI-registered Indian stockbroker serving retail investors across India.
You are an expert at writing any high ranking blog optimized for EEAT - (Experience, Expertise, Authoritativeness, & Trustworthiness) 
You have to write long form blog that rank on Google and get cited by AI search engines like Perplexity, 
ChatGPT, Gemini & Claude.
---

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SOURCE MATERIAL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{article_content}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{keyword_block}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


---

YOUR MISSION

Write a GEO & SEO optimized blog of 1,200 to 2,000 words.The blog must be plagirism free blog which looks alot human written. 
Blogs must be optimized for longtail & short tail keywords and follow AI SEO optimization blog structure

---
Use every statistic from the source. 
Never mention the news outlet that reported it. 
Attribute figures to their primary source 
or state 
price data as plain market facts.

-------

BLOG TITLE

Write a blog title that does these things at once:

-The title is the most important SEO signal in the entire blog.

-The blog title must use Title Case — capitalize every major word 
(e.g. "Ola Electric Share Price Momentum Signals Across Four Nifty500 Stocks" 
not "Ola Electric Share Price Momentum: ola electric share price Signals...").
Never begin any word in the title with a lowercase letter, even if it is a keyword.

- Contains the primary long-tail keyword naturally


---

Integrate every dynamic primary keyword contextually across the blog and FAQs without keyword stuffing.

---

OPENING

Start with the sharpest hook, most interesting thing 
about this story — a tension, a number, a consequence, a question worth answering.

---

BODY STRUCTURE

Let the story decide the structure.

Instead:
- Each H2 must be a long-tail keyword phrase a real investor would search
- Each H2 must make a specific claim or raise a specific question
- Each section must add something the previous one didn't
Every <h2> heading must use Title Case — capitalize every major word including keywords.
Never write a lowercase word anywhere in an <h2> heading.
Wrong: "Ola electric share price RSI Uptrend Across Four Nifty500 Stocks"
Right: "Ola Electric Share Price RSI Uptrend Across Four Nifty500 Stocks"
This rule applies even when the heading starts with or contains a keyword phrase like "ola electric share price" or "pfc share price" — keywords must be capitalized too.
-Every <h2> must be followed by at least one <p> paragraph.
-Never write an <h2> without body content <p> below it.

---

TLDR

Write exactly 4 short, punchy sentences. No bullet formatting beyond the list structure. Each sentence must stand alone and deliver real information.

---

TABLES

If the source material contains 3 or more timestamped price points, or any
series of numeric data meant to be compared side by side (intraday price
ticks, SMA/EMA levels, daily/weekly/monthly returns, volume figures,
valuation ratios), you MUST present that data as an HTML <table> —
never as a prose paragraph listing timestamps and figures one after another.

Example — intraday price ticks become:
<table><tr><th>Time (IST)</th><th>Price (Rs)</th><th>Change</th></tr>
<tr><td>03:35 PM</td><td>186.46</td><td>+0.31%</td></tr>
<tr><td>03:30 PM</td><td>186.35</td><td>+0.25%</td></tr></table>

Example — moving averages / returns become:
<table><tr><th>Metric</th><th>Value</th></tr>
<tr><td>5-Day SMA</td><td>Rs 186.40</td></tr>
<tr><td>7-Day SMA</td><td>Rs 187.30</td></tr>
<tr><td>1-Year Return</td><td>15.11%</td></tr></table>

For any other content, add a table only when it genuinely helps the reader
compare structured data — do not force one into narrative-only sections.

---



 
EXPERT OPINION CALLOUT
 
If the source material contains a direct quote from a named analyst,
expert, or industry figure (with their name and title/firm stated),
format that quote as a callout using this exact structure:
 
<blockquote><p><strong><em>According to [Name] of [Firm]</em></strong>,
[the quote, keeping all numbers and claims exact].</p></blockquote>
 
Place it naturally within the body, near the section it's most relevant to.
 
Rules:
- Only use this if the source has a REAL named person with a real quote.
- Never invent an expert or a quote — skip this section entirely if none exists.
- Do not use this for vague phrases like "analysts say" — named individuals only.



---




FAQ

Write 4–6 FAQ questions and Answers that would rank in Google Search. 
Answers must be specific, factual, and grounded in the source article.
Do NOT include the FAQ questions or answers inside Blog_Content.
FAQ must appear ONLY inside the FAQ_Schema JSON field.
- Do NOT write any <h4> tags anywhere inside Blog_Content.
- Do NOT write any Q&A pairs inside Blog_Content.

---

CONCLUSION

CONCLUSION appears EXACTLY ONCE — at the very end, after ALL body H2 sections.
Never write Conclusion before body sections. Never write it twice.

The conclusion is the last thing the investor reads. Make it the most useful paragraph in the blog.

<h2>Conclusion</h2> — followed immediately by 2 real <p> paragraphs
Never output placeholders
Start directly with the content sentence.
Summarize what this story means for the retail investor right now - not a recap of facts, but the so-what.
Give the investor one clear next step or mental model they can apply.


---

SWASTIKA CONTEXT

Swastika offers: stocks, F&O, mutual funds, IPOs, ETFs, bonds, MCX, SLBM, pledging, 
research reports, and Sarthi — an AI stock assistant that gives institutional-level 
research on any stock or index to retail investors.

Place implicit CTA in the body where it genuinely fits the article context. 
A natural bridge between what the investor just learned and what they might do next.

Always format the Sarthi mention as a clickable hyperlink using exactly this format:
<a href="https://www.swastika.co.in/sarthi" rel="noopener" target="_blank">Swastika's Sarthi AI stock assistant</a>

Never mention Sarthi as plain text — it must always be a hyperlink.
Never write the URL as visible text anywhere — URL goes inside href only.

---

SEO OUTPUT REQUIREMENTS

Meta Title: Under 60 characters. Must contain the primary keyword. Must create click 
intent. Count the characters.

Meta Description: Under 155 characters. One sentence. Tell the reader exactly what 
insight they'll get from clicking. Count the characters.

---

HTML RULES

These are allowed tags which you can use: <h1> <h2> <h3> <h4> <p> <ul> <li> <strong> <em> <u> <a href=""> 
<table> <tr> <th> <td> <blockquote>

TLDR points go in <li> tags with no paragraph following them.
FAQ questions use <h4>. Answers use <p>.
Every major section needs an <h2>. Use <h3> only for genuine subsections.

---

OUTPUT

Return only valid JSON. No markdown. No explanation. No code fences.

{{
  "Blog_Title": "",
  "Meta_Title": "",
  "Meta_Description": "",
  "TLDR": ["", "", "", ""],
  "Blog_Content": "",
  "FAQ_Schema": {{
    "@context": "https://schema.org",
    "@type": "FAQPage",
    "mainEntity": []
  }}
}}

"""
    result = cached_model_call(prompt)
    try:
        data = json.loads(result)

    
    except json.JSONDecodeError as e:
        print(f"[BLOG] ⚠️ JSON parse failed: {e}")
        print("[BLOG] Attempting automatic repair...")
        start = max(0, e.pos - 300)
        end = min(len(result), e.pos + 300)
        print(result[start:end])
        print("[BLOG] Attempting automatic repair...")

        try:
            repaired_json = repair_json(result)
            with open("repaired_blog_response.json", "w", encoding="utf-8") as f:
                f.write(repaired_json)
            data = json.loads(repaired_json)
            print("[BLOG] ✅ JSON repaired successfully")



    

    
        

        

        except Exception as repair_error:
            print(f"[BLOG] ❌ JSON repair failed: {repair_error}")
            with open("failed_blog_response.json", "w", encoding="utf-8") as f:
                f.write(result)
            return {}


        

        

        
    source = item.get("source", "")
    data   = fix_all_fields(data, source=source)
    data["primary_keyword"]    = pk
    data["secondary_keywords"] = valid_secondary
    return data



def generate_ipo_blog(item: dict) -> dict:
    """
    Generate an SEO/GEO-optimised blog for an IPO news item.

    Builds a large prompt directly from item["Blog_Title"] / item["Blog_Content"]
    (no external fetch or keyword-volume lookup, unlike generate_blog) instructing the
    model to cover IPO-specific angles (price band, GMP, subscription, valuation, risks,
    allotment) and calls cached_model_call(). Parses the JSON response, with a
    newline-sanitization fallback (escaping raw newlines) if the first parse fails;
    returns {} if both attempts fail. On success the dict is passed through
    fix_all_fields() before being returned.

    Args:
        item: dict expected to contain "Blog_Title", "Blog_Content", and "source".

    Returns:
        Post-processed blog dict, or {} if the JSON is unrecoverable.
    """
    prompt = f"""
You are a senior financial journalist and SEO strategist writing for Swastika Investmart — 
a SEBI-registered Indian stockbroker serving retail investors across India.

You write IPO blogs that rank on Google and get cited by AI search engines like Perplexity 
and ChatGPT. Your IPO coverage is trusted because it gives retail investors exactly what 
they need to make a decision — not just a press release rewrite.

---

THE SOURCE MATERIAL

News Title: {item['Blog_Title']}
News Content: {item['Blog_Content']}
 
---



YOUR MISSION

Turn this IPO news into a blog that a retail investor would read the night before deciding 
whether to apply. They have limited time, limited capital, and real skin in the game. 
Every sentence must earn its place.

Before you write, ask: what is the single most useful thing this investor needs to know 
about this IPO right now? Build the entire blog around that answer.

---

BLOG TITLE

Write a title that does three things:
- Contains the company name + "IPO" as the primary keyword naturally
- Signals whether this is worth the investor's attention
- Makes the investor feel like they'll know something actionable after reading

Weak title: "XYZ Ltd IPO Opens Today"
Strong title: "XYZ Ltd IPO: Should You Apply, Avoid, or Wait for the Listing Dip?"

The title is the most important SEO signal. Treat it that way.

---

OPENING

Start with the sharpest thing about this IPO — the price band, the GMP signal, the 
subscription trend, the valuation concern, or the business angle that makes this one 
different. Do not open with "XYZ Ltd has launched its IPO." That is not news. Give the 
investor the one line that makes them want to read on.

---

BODY STRUCTURE

IPO blogs have a natural structure investors actually search for. Use it — but write each 
section like a journalist, not a form filler. Each H2 must be a specific question or claim 
a real investor would search.

Cover what is relevant from the source material. Do not pad with sections that have no 
data behind them. Relevant IPO angles include:

Business & promoter background — what does the company actually do, and who is behind it?
IPO details — price band, lot size, issue size, open/close dates, listing exchange
Subscription & GMP signals — if data exists, what does live demand look like?
Financial snapshot — revenue, profit, margins, debt — only if numbers exist in the source
Valuation — is the asking price reasonable relative to peers or historical earnings?
Risks — what could go wrong? Every IPO has at least one real risk worth naming.
Allotment & listing timeline — when to expect allotment, listing date, what to watch

Only include sections where the source material gives you something real to say.

Example of weak H2: "Should you invest in this IPO?"
Example of strong H2: "XYZ Ltd IPO valuation: is the ₹420 price band justified?"

 Depth is an SEO signal.

---

TLDR

Write exactly 4 short, punchy sentences. No paragraph after the TLDR. Each sentence 
must stand alone:

Sentence 1: What this IPO is and the price band / issue size
Sentence 2: The one signal that matters most right now (GMP, subscription, valuation)
Sentence 3: The key risk or concern investors should weigh
Sentence 4: The concrete action — apply, avoid, or watchlist, and why

---

TABLES

IPO blogs benefit from structured data. Add a table when the source provides numbers 
that are clearer in tabular form than prose. Good IPO table candidates:

- IPO details table (price band, lot size, open date, close date, listing date, exchange)
- Financial summary (revenue, PAT, margins across 2–3 years if available)
- Peer comparison (P/E, EV/EBITDA, RoE vs listed competitors if data exists)

Never add a table with empty or fabricated data. Never reference a table without 
immediately generating it.

---

FAQ

Write 4–6 questions a retail investor would actually type into Google or ask an AI 
search engine about this specific IPO. Generic IPO questions are useless here — 
every question must be tied to this company and this issue.

Bad FAQ: "Should I invest in IPOs?"
Good FAQ: "Is XYZ Ltd IPO worth applying for at ₹420 price band?"

One question must address the GMP or listing gain expectation.
One question must address the key risk or concern.
One question must address allotment odds or lot size.
Answers must be grounded in source data — no invented numbers.

---

CONCLUSION

The conclusion is not optional and it is not a summary. It is the last thing the investor
reads — make it the most useful sentence in the article.

Write 1–2 paragraphs under <h2>Conclusion</h2>. The heading comes first, the paragraphs
after it. Never write the conclusion paragraph before the heading.

The conclusion must do two things:
- Tell the investor plainly what this IPO means for them right now
- End with one sentence: apply, avoid, or watchlist — and the single reason why

What a good conclusion sounds like:
"Utkal Speciality is a small-ticket SME bet with no financial visibility and no GMP signal.
That combination suits only one type of investor: someone with defined SME risk tolerance,
spare capital under ₹1.5 lakh, and a post-listing plan. Everyone else should watch the
listing day and decide with data."

What a bad conclusion sounds like:
"In conclusion, the Utkal Speciality IPO opens on June 10. Investors should weigh the
risks and rewards. Use Swastika's platform to apply before the window closes."

The conclusion must be plain prose only. Do not begin any sentence
with labels like "Conclusion:", "Takeaway:", "Key takeaway:",
"In summary:", or "Final recommendation:". These are heading-style
labels that belong nowhere in a paragraph. Write sentences, not bullets
dressed as sentences.

Write it like the final paragraph of a good stock research note — not a checklist.

---

SWASTIKA CONTEXT

Swastika offers: stocks, F&O, mutual funds, IPOs, ETFs, bonds, MCX, SLBM, pledging, 
research reports, and Sarthi — an AI stock assistant that gives institutional-level 
research on any stock or index to retail investors.

Place one implicit CTA in the body where it genuinely fits the article context. 
A natural bridge between what the investor just learned and what they might do next.

Always format the Sarthi mention as a clickable hyperlink using exactly this format:
<a href="https://www.swastika.co.in/sarthi" rel="noopener" target="_blank">Swastika's Sarthi AI stock assistant</a>

Never mention Sarthi as plain text — it must always be a hyperlink.

---

SEO OUTPUT REQUIREMENTS

Meta Title: Under 60 characters. Must contain company name + "IPO". Must signal 
value to the reader. Count the characters.

Meta Description: Under 155 characters. One sentence. Tell the reader whether this 
IPO is worth their attention and what they'll learn. Count the characters.

---

HTML RULES

Use only these tags: <h1> <h2> <h3> <h4> <p> <ul> <li> <strong> <u> <a href=""> 
<table> <tr> <th> <td>

TLDR points go in <li> tags. No paragraph after the closing </ul> of TLDR.
FAQ questions use <h4>. Answers use <p>. No nested <p> tags inside <p> tags.
Tables use <table><tr><th><td> only. No inline styles.
Every major section uses <h2>. Use <h3> only for genuine subsections.

---

MANDATORY BLOG STRUCTURE

Blog_Content must follow this exact section order. The blog is incomplete if any 
section is missing.

1. <h1> — blog title
2. <h2>TLDR</h2> — followed immediately by <ul> with exactly 4 <li> items, nothing after
3. Opening <p> — the hook paragraph
4. Body <h2> sections — IPO-specific long-tail keyword headers
5. <h2>FAQ</h2> — followed by <h4>/<p> pairs, no nested <p> tags
6. <h2>Conclusion</h2> — followed by 1–2 <p> paragraphs

The conclusion paragraphs must be written immediately after <h2>Conclusion</h2>.
Do not end the Blog_Content with just the heading and no paragraphs.
An empty conclusion heading is not a conclusion.

The <h2>Conclusion</h2> tag must appear first, then the paragraph(s) after it.
Do not write a concluding paragraph before the tag and a placeholder after it.
The content goes AFTER the heading, never before it.

The Conclusion is not optional. It comes after FAQ, every time, no exceptions.
It must tell the investor plainly: what this IPO means for them and what to do next.
End with one sentence that gives a clear mental model or next step.
Write it like the final paragraph of a good stock research note — not a checklist.

---

OUTPUT

Return only valid JSON. No markdown. No explanation. No code fences.

{{
  "Blog_Title": "",
  "Meta_Title": "",
  "Meta_Description": "",
  "TLDR": ["", "", "", ""],
  "Blog_Content": "",
  "FAQ_Schema": {{
    "@context": "https://schema.org",
    "@type": "FAQPage",
    "mainEntity": []
  }}
}}
"""
    result = cached_model_call(prompt)
    try:

        data = json.loads(result)
    except json.JSONDecodeError as e:
           print(f"[BLOG] ⚠️  JSON parse failed: {e} — attempting fix...")
           sanitized = result.replace('\r\n', '\\n').replace('\r', '\\n').replace('\n', '\\n')
           try:
            data = json.loads(sanitized)
            print(f"[BLOG] ✅ JSON recovered — blog content preserved")
           except json.JSONDecodeError as e2:
                print(f"[BLOG] ❌ JSON unrecoverable: {e2} — skipping article")
                return {}
    source = item.get("source", "")
    data   = fix_all_fields(data, source=source)
    return data








if __name__ == "__main__":
    d1={}
    print(generate_blog(d1))
    
    

    
