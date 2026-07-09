# """
# related_links.py
# ------------------
# Called from webflow_poster.py at two points in the pipeline:

#     1. BEFORE publish — get_related_links() + build_related_links_html()
#        find candidates for the NEW blog and produce an HTML block to
#        inject into its content.

#     2. AFTER publish  — add_blog_to_graph() registers the newly published
#        blog into keyword_graph.json so future blogs can find and link to it.
# """

# import os
# import json
# import tempfile
# from collections import defaultdict

# from build_keyword_graph import get_topic_tags, get_blog_topic_tags

# KEYWORD_GRAPH_PATH = os.environ.get(
#     "KEYWORD_GRAPH_PATH",
#     r"D:\Blogheading\output\keyword_graph.json",
# )

# MAX_RELATED_LINKS = 3


# def _normalize_keyword_field(kw):
#     """Same normalization used in build_keyword_graph.py — handles enriched dicts."""
#     if isinstance(kw, dict):
#         text = (kw.get("google_keyword") or kw.get("original") or "").strip().lower()
#         volume = kw.get("volume", 0) or 0
#     else:
#         text = str(kw).strip().lower()
#         volume = 0
#     return text, volume


# def load_graph(path: str = KEYWORD_GRAPH_PATH) -> dict:
#     if not os.path.exists(path):
#         return {}
#     with open(path, "r", encoding="utf-8") as f:
#         return json.load(f)


# def save_graph(graph: dict, path: str = KEYWORD_GRAPH_PATH):
#     dir_name = os.path.dirname(os.path.abspath(path))
#     os.makedirs(dir_name, exist_ok=True)
#     with tempfile.NamedTemporaryFile("w", dir=dir_name, delete=False, suffix=".tmp", encoding="utf-8") as tmp:
#         json.dump(graph, tmp, ensure_ascii=False, indent=2)
#         tmp_path = tmp.name
#     os.replace(tmp_path, path)


# # ── Step 1: find related links for a NEW blog, before publish ──────────────

# def get_related_links(primary_keyword, secondary_keywords, graph: dict, max_links: int = MAX_RELATED_LINKS) -> list:
#     """
#     Given a new blog's primary/secondary keywords and the existing graph,
#     return a ranked list of {title, url} candidates — pillar first, then
#     children/siblings by volume, capped at max_links.
#     """
#     if not graph:
#         return []

#     new_primary_text, _ = _normalize_keyword_field(primary_keyword)
#     new_secondary_texts = [_normalize_keyword_field(s)[0] for s in (secondary_keywords or [])]
#     new_secondary_texts = [t for t in new_secondary_texts if t]

#     # Build a lookup: primary_kw text -> node url, from the existing graph
#     primary_to_url = {}
#     for url, node in graph.items():
#         pk = node.get("primary_kw", "")
#         if pk:
#             primary_to_url.setdefault(pk, url)  # first one wins if duplicated

#     pillar_url = None
#     pillar_candidates = []

#     # Case A: new blog's own primary keyword already exists (recurring topic)
#     if new_primary_text and new_primary_text in primary_to_url:
#         existing_url = primary_to_url[new_primary_text]
#         existing_node = graph[existing_url]
#         # If that existing node itself has a pillar, point to that pillar's root;
#         # otherwise the existing node IS the pillar.
#         pillar_url = existing_node.get("pillar") or existing_url

#     # Case B: new blog's secondary keyword matches an existing primary keyword
#     if not pillar_url:
#         for sec in new_secondary_texts:
#             if sec in primary_to_url:
#                 pillar_url = primary_to_url[sec]
#                 break

#     candidates = {}  # url -> node, deduped

#     if pillar_url and pillar_url in graph:
#         candidates[pillar_url] = graph[pillar_url]
#         # pull in the pillar's existing children too — same cluster
#         for child_url in graph[pillar_url].get("children", []):
#             if child_url in graph:
#                 candidates[child_url] = graph[child_url]

#     # Case C: sibling matches — any existing blog sharing a secondary keyword
#     for url, node in graph.items():
#         if url in candidates:
#             continue
#         if node.get("primary_kw") in new_secondary_texts:
#             candidates[url] = node

#     # Case D: topic-tag matches — catches same-subject blogs with different
#     # wording, checking BOTH primary and secondary keywords on both sides
#     # (e.g. new primary "gold price" vs an existing blog's secondary
#     # "kerala gold price")
#     new_tags = get_blog_topic_tags(new_primary_text, new_secondary_texts)
#     if new_tags:
#         for url, node in graph.items():
#             if url in candidates:
#                 continue
#             node_tags = get_blog_topic_tags(node.get("primary_kw", ""), node.get("secondary_kws", []))
#             if node_tags & new_tags:
#                 candidates[url] = node

#     # Case E: REVERSE match — an existing blog's secondary keyword matches
#     # THIS new blog's primary keyword. This means the new blog is about to
#     # become that existing blog's pillar (add_blog_to_graph will record
#     # this after publish) — so it should link DOWN to that blog right now,
#     # since it's effectively that blog's parent topic.
#     if new_primary_text:
#         for url, node in graph.items():
#             if url in candidates:
#                 continue
#             if new_primary_text in node.get("secondary_kws", []):
#                 candidates[url] = node

#     def rank_key(item):
#         url, node = item
#         is_pillar = 1 if url == pillar_url else 0
#         return (is_pillar, node.get("primary_vol", 0))

#     ranked = sorted(candidates.items(), key=rank_key, reverse=True)

#     return [
#         {"title": node["title"], "url": url}
#         for url, node in ranked[:max_links]
#     ]


# def build_related_links_html(related_links: list) -> str:
#     """Turns a related-links list into the HTML block injected into content."""
#     if not related_links:
#         return ""
#     items = "".join(
#         f'<li><a href="{l["url"]}">{l["title"]}</a></li>'
#         for l in related_links
#     )
#     return f"<h2>Related Reads</h2><ul>{items}</ul>"


# def _inject_related_links_before_conclusion(content: str, related_html: str) -> str:
#     """Same insertion pattern as _inject_faq_before_conclusion in webflow_poster.py."""
#     import re
#     if not related_html:
#         return content
#     conclusion_match = re.search(r"<h2[^>]*>\s*Conclusion\s*</h2>", content, re.IGNORECASE)
#     if conclusion_match:
#         insert_pos = conclusion_match.start()
#         return content[:insert_pos] + related_html + content[insert_pos:]
#     return content + related_html


# # ── Step 2: register the newly published blog into the graph ───────────────

# def add_blog_to_graph(webflow_url: str, title: str, primary_keyword, secondary_keywords,
#                        graph_path: str = KEYWORD_GRAPH_PATH):
#     """
#     Called AFTER a blog is confirmed published. Computes this one blog's
#     relationships against the existing graph and saves the updated graph.
#     """
#     graph = load_graph(graph_path)

#     primary_text, primary_vol = _normalize_keyword_field(primary_keyword)
#     secondary_texts = [_normalize_keyword_field(s)[0] for s in (secondary_keywords or [])]
#     secondary_texts = [t for t in secondary_texts if t]

#     # Add this blog as its own node first
#     graph[webflow_url] = {
#         "title": title,
#         "primary_kw": primary_text,
#         "primary_vol": primary_vol,
#         "secondary_kws": secondary_texts,
#         "pillar": None,
#         "children": [],
#         "siblings": [],
#     }

#     # ── Rule 0: REVERSE CASE — this new blog's primary keyword matches an
#     # existing blog's secondary keyword. That means this NEW blog is the
#     # pillar, and the OLD blog should become its child.
#     # Note: this only updates keyword_graph.json — it does NOT retroactively
#     # edit the old blog's already-published Webflow content. That old blog
#     # won't visibly show a link to this new one until a separate retrofit
#     # pass re-injects related links into its live content.
#     for url, node in graph.items():
#         if url == webflow_url:
#             continue
#         if primary_text and primary_text in node.get("secondary_kws", []):
#             node["pillar"] = webflow_url
#             graph[webflow_url].setdefault("children", []).append(url)
#             print(f"[GRAPH] '{title[:50]}' is now the pillar for existing blog "
#                   f"'{node['title'][:50]}' — old blog's live page not auto-updated")

#     primary_to_url = {}
#     for url, node in graph.items():
#         if url == webflow_url:
#             continue
#         pk = node.get("primary_kw", "")
#         if pk:
#             primary_to_url.setdefault(pk, url)

#     # Rule 1a: same primary keyword as an existing blog (recurring topic)
#     if primary_text and primary_text in primary_to_url:
#         pillar_url = primary_to_url[primary_text]
#         graph[webflow_url]["pillar"] = pillar_url
#         graph[pillar_url].setdefault("children", []).append(webflow_url)

#     # Rule 1b: secondary keyword matches an existing primary keyword
#     if not graph[webflow_url]["pillar"]:
#         for sec in secondary_texts:
#             if sec in primary_to_url:
#                 pillar_url = primary_to_url[sec]
#                 graph[webflow_url]["pillar"] = pillar_url
#                 graph[pillar_url].setdefault("children", []).append(webflow_url)
#                 break

#     # Rule 2: sibling edges — other blogs whose primary matches one of our secondaries,
#     # or whose secondary-derived primary overlaps (best-effort, since we don't store
#     # each node's secondary list in the graph)
#     for url, node in graph.items():
#         if url == webflow_url:
#             continue
#         if node.get("primary_kw") in secondary_texts:
#             if url not in graph[webflow_url]["siblings"]:
#                 graph[webflow_url]["siblings"].append(url)
#             if webflow_url not in node.get("siblings", []):
#                 node.setdefault("siblings", []).append(webflow_url)

#     # Rule 3: topic-tag siblings — catches same-subject blogs with different
#     # wording, checking both primary and secondary keywords on both sides
#     new_tags = get_blog_topic_tags(primary_text, secondary_texts)
#     if new_tags:
#         for url, node in graph.items():
#             if url == webflow_url:
#                 continue
#             if node["pillar"] == webflow_url or graph[webflow_url]["pillar"] == url:
#                 continue  # already connected via a stronger relationship
#             node_tags = get_blog_topic_tags(node.get("primary_kw", ""), node.get("secondary_kws", []))
#             if node_tags & new_tags:
#                 if url not in graph[webflow_url]["siblings"]:
#                     graph[webflow_url]["siblings"].append(url)
#                 if webflow_url not in node.get("siblings", []):
#                     node.setdefault("siblings", []).append(webflow_url)

#     save_graph(graph, graph_path)
#     print(f"[GRAPH] Added new blog to keyword_graph.json: {title[:60]}")








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

Rules:
    1. Primary matches + secondary overlap exists somewhere in the group
       -> rank the group by secondary-match-score, return top max_links.
    2. Primary matches + no secondary overlap at all in the group
       -> return any max_links from the group (order doesn't matter).
    3. Primary doesn't match anything -> return nothing, start a new group.
"""

import os
import json
import tempfile

KEYWORD_GRAPH_PATH = os.environ.get(
    "KEYWORD_GRAPH_PATH",
    r"D:\Blogheading\output\keyword_graph.json",
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
    """
    new_primary_text, _ = _normalize_keyword_field(primary_keyword)
    if not new_primary_text:
        return []

    group_key = _find_group_key(new_primary_text, graph)
    if not group_key:
        return []  # Rule 3: no primary match at all (exact or fuzzy)

    group = graph[group_key]

    new_secondary_set = {
        _normalize_keyword_field(s)[0] for s in (secondary_keywords or [])
    }
    new_secondary_set.discard("")

    scored = [
        (blog, len(new_secondary_set & set(blog.get("secondary_kws", []))))
        for blog in group
    ]

    any_secondary_overlap = any(score > 0 for _, score in scored)

    if any_secondary_overlap:
        scored.sort(key=lambda item: item[1], reverse=True)
    else:
        scored.sort(key=lambda item: item[0].get("volume", 0), reverse=True)

    top = [blog for blog, _ in scored[:max_links]]
    return [{"title": b["title"], "url": b["url"]} for b in top]


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