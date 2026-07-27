"""
related_links.py
------------------
Graph structure: keyword_graph.json is keyed by PRIMARY KEYWORD, not URL.

    {
        "hdfc bank share price": [
            {"url": ..., "title": ..., "volume": ..., "secondary_kws": [...]},
            ...
        ],
        "gold prices today": [
            {"url": ..., "title": ..., "volume": ..., "secondary_kws": [...]}
        ]
    }

This gives O(1) lookup of "every blog sharing my primary keyword" -- no
scanning the whole graph. Secondary-keyword comparison then only runs
within that one small group (size K, typically 2-4), not across all N
blogs in the graph.

Rules (see get_related_links() for the full tier breakdown):
    1. Primary matches + secondary overlap exists somewhere in the group
       -> rank the group by secondary-match-score, return top max_links.
    2. Primary matches + no secondary overlap at all in the group
       -> return any max_links from the group (order doesn't matter).
    3. Primary doesn't match anything, or its group is smaller than
       max_links -> fill remaining slots from any OTHER group whose blogs
       share a secondary keyword with this one (cross-group fallback).
"""

import os
import json
import tempfile

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

KEYWORD_GRAPH_PATH = os.environ.get(
    "KEYWORD_GRAPH_PATH",
    os.path.join(BASE_DIR, "output", "keyword_graph.json"),
)

MAX_RELATED_LINKS = 3
FUZZY_MATCH_CUTOFF = 0.55       # length-ratio threshold for containment matching
FUZZY_MIN_LENGTH = 10           # shorter string must be at least this long --
                                 # blocks short generic words (e.g. "bank") from
                                 # matching too broadly against unrelated keywords


def _find_group_key(new_primary_text: str, graph: dict):
    """
    Exact O(1) lookup first. Only if that misses, falls back to a
    CONTAINMENT check (not plain fuzzy ratio) against existing group keys.

    Why containment, not difflib ratio: tested against real keyword pairs,
    plain fuzzy ratio scored "hdfc bank share price" vs "icici bank share
    price" (different companies, 0.837) HIGHER than "hdfc bank share" vs
    "hdfc bank share price" (same company, shorter wording, 0.833) --
    because the long shared phrase "bank share price" dominates the score
    while the short company-name difference barely registers. That makes
    plain fuzzy ratio unsafe here: any threshold either misses real
    matches or merges different companies together.

    Containment avoids this: it only matches when one keyword is (almost)
    entirely a prefix/substring of the other, which happens for genuine
    wording-length differences ("hdfc bank share" is fully contained in
    "hdfc bank share price") but essentially never for different company
    names of similar length.
    """
    if new_primary_text in graph:
        return new_primary_text  # fast path, O(1)

    if not graph or not new_primary_text:
        return None

    best_key = None
    best_ratio = 0.0
    for key in graph:
        shorter, longer = sorted([new_primary_text, key], key=len)
        if not shorter or shorter not in longer:
            continue  # not a containment case at all -- skip
        if len(shorter) < FUZZY_MIN_LENGTH:
            continue  # too short/generic to trust -- avoid broad false matches
        length_ratio = len(shorter) / len(longer)
        if length_ratio >= FUZZY_MATCH_CUTOFF and length_ratio > best_ratio:
            best_ratio = length_ratio
            best_key = key

    return best_key


def _normalize_keyword_field(kw):
    """Same normalization used in build_keyword_graph.py -- handles enriched dicts."""
    if isinstance(kw, dict):
        text = (kw.get("google_keyword") or kw.get("original") or "").strip().lower()
        volume = kw.get("volume", 0) or 0
    else:
        text = str(kw).strip().lower()
        volume = 0
    return text, volume


def load_graph(path: str = KEYWORD_GRAPH_PATH) -> dict:
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_graph(graph: dict, path: str = KEYWORD_GRAPH_PATH):
    dir_name = os.path.dirname(os.path.abspath(path))
    os.makedirs(dir_name, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", dir=dir_name, delete=False, suffix=".tmp", encoding="utf-8") as tmp:
        json.dump(graph, tmp, ensure_ascii=False, indent=2)
        tmp_path = tmp.name
    os.replace(tmp_path, path)


# -- Step 1: find related links for a NEW blog, before publish --------------

def get_related_links(primary_keyword, secondary_keywords, graph: dict, max_links: int = MAX_RELATED_LINKS) -> list:
    """
    O(1) group lookup by primary keyword, then O(K x S) secondary-overlap
    scoring within that group only (K = blogs in the group, S = secondary
    keywords per blog) -- not O(N) across the whole graph.

    Tier 1 (primary-keyword group, as before):
        1a. Primary matches + secondary overlap exists somewhere in the
            group -> rank the group by secondary-match-score.
        1b. Primary matches + no secondary overlap at all in the group
            -> rank the group by volume (order doesn't otherwise matter).
        1c. Primary doesn't match anything -> tier 1 contributes nothing.

    Tier 2 (cross-group fallback, new): when tier 1 didn't fill max_links
    -- either the primary keyword had no group at all, or its group was
    too small -- fill the rest from ANY other group whose blogs share at
    least one secondary keyword with this blog, ranked by overlap count.
    This catches topically-adjacent blogs that never shared a primary
    keyword -- e.g. a "tanishq gold price today" blog and an "ibja gold
    price" blog both carry the secondary keyword "ibja gold rate" despite
    belonging to different primary-keyword groups.
    """
    new_primary_text, _ = _normalize_keyword_field(primary_keyword)
    new_secondary_set = {
        _normalize_keyword_field(s)[0] for s in (secondary_keywords or [])
    }
    new_secondary_set.discard("")

    selected = []
    selected_urls = set()

    # -- Tier 1: same primary-keyword group --------------------------------
    group_key = _find_group_key(new_primary_text, graph) if new_primary_text else None
    if group_key:
        group = graph[group_key]
        scored = [
            (blog, len(new_secondary_set & set(blog.get("secondary_kws", []))))
            for blog in group
        ]
        any_secondary_overlap = any(score > 0 for _, score in scored)
        scored.sort(
            key=lambda item: item[1] if any_secondary_overlap else item[0].get("volume", 0),
            reverse=True,
        )
        for blog, _ in scored:
            if len(selected) >= max_links:
                break
            selected.append(blog)
            selected_urls.add(blog["url"])

    # -- Tier 2: cross-group secondary-keyword overlap fallback -----------
    if len(selected) < max_links and new_secondary_set:
        candidates = []
        for key, group in graph.items():
            if key == group_key:
                continue  # already covered by tier 1
            for blog in group:
                if blog["url"] in selected_urls:
                    continue
                overlap = len(new_secondary_set & set(blog.get("secondary_kws", [])))
                if overlap > 0:
                    candidates.append((blog, overlap))
        candidates.sort(key=lambda item: item[1], reverse=True)
        for blog, _ in candidates:
            if len(selected) >= max_links:
                break
            selected.append(blog)
            selected_urls.add(blog["url"])

    return [{"title": b["title"], "url": b["url"]} for b in selected]


def build_related_links_html(related_links: list) -> str:
    if not related_links:
        return ""
    items = "".join(
        f'<li><a href="{l["url"]}">{l["title"]}</a></li>'
        for l in related_links
    )
    return f"<h2>Related Reads</h2><ul>{items}</ul>"


def _inject_related_links_before_conclusion(content: str, related_html: str) -> str:
    import re
    if not related_html:
        return content
    conclusion_match = re.search(r"<h2[^>]*>\s*Conclusion\s*</h2>", content, re.IGNORECASE)
    if conclusion_match:
        insert_pos = conclusion_match.start()
        return content[:insert_pos] + related_html + content[insert_pos:]
    return content + related_html


# -- Step 2: register the newly published blog into the graph ---------------

def add_blog_to_graph(webflow_url: str, title: str, primary_keyword, secondary_keywords,
                       graph_path: str = KEYWORD_GRAPH_PATH):
    graph = load_graph(graph_path)

    primary_text, primary_vol = _normalize_keyword_field(primary_keyword)
    secondary_texts = [_normalize_keyword_field(s)[0] for s in (secondary_keywords or [])]
    secondary_texts = [t for t in secondary_texts if t]

    new_entry = {
        "url": webflow_url,
        "title": title,
        "volume": primary_vol,
        "secondary_kws": secondary_texts,
    }

    group_key = _find_group_key(primary_text, graph)
    existing_group = graph.get(group_key) if group_key else None

    if existing_group is not None:
        overlap_found = any(
            set(secondary_texts) & set(b.get("secondary_kws", []))
            for b in existing_group
        )
        match_type = "exact" if group_key == primary_text else f"fuzzy (joined existing group '{group_key}')"
        print(f"[GRAPH] '{title[:50]}' joins existing primary-keyword group [{match_type}] "
              f"({len(existing_group)} blog(s) already there, "
              f"secondary overlap: {'yes' if overlap_found else 'no'})")
        existing_group.append(new_entry)
    else:
        graph[primary_text] = [new_entry]
        print(f"[GRAPH] '{title[:50]}' starts a new primary-keyword group (isolated)")

    save_graph(graph, graph_path)
