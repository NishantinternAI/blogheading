




# """
# build_keyword_graph.py
# ------------------------
# Builds a pillar / cluster / sibling graph across all blogs in
# blogs_missing_keywords.json, based on primary/secondary keyword
# relationships (the hierarchy model discussed earlier).

# Handles both keyword formats found in the real data:
#     - enriched:  {"original": ..., "google_keyword": ..., "volume": N, ...}
#     - raw:       "plain keyword string" (no volume yet)

# Relationship rules:
#     1. PILLAR-CHILD: blog A's secondary keyword == blog B's primary keyword
#        → B is the pillar, A is B's child.
#     2. SIBLING: two blogs share a secondary keyword, with no pillar
#        relationship between them.
#     3. If multiple blogs share the exact same primary keyword (a data
#        collision), the one with the highest volume is treated as the
#        canonical pillar for that keyword; the rest are flagged for review.

# Output: keyword_graph.json — an adjacency structure like:
#     {
#       "<webflow_url>": {
#           "title": "...",
#           "primary_kw": "...",
#           "pillar": "<webflow_url of pillar, or null>",
#           "children": ["<webflow_url>", ...],
#           "siblings": ["<webflow_url>", ...]
#       },
#       ...
#     }

# This file is what get_related_links() reads from at generation-time,
# and what a one-time internal_linker.py pass can use to inject related
# links into ALL 143 already-published blogs retroactively.

# Usage:
#     python build_keyword_graph.py --path "D:\\Blogheading\\output\\blogs_missing_keywords.json"
# """

# import os
# import json
# import argparse
# from collections import defaultdict


# TOPIC_TAGS = {
#     "gold_price": ["gold price", "gold rate", "mcx gold"],
#     "bank_share_price": ["bank share price", "bank stock price", "bank stock"],
#     "usd_inr": ["usd to inr", "usd/inr", "rupee", "dollar"],
#     "sensex_nifty": ["sensex", "nifty", "gift nifty"],
#     "ipo": [" ipo", "ipo "],
# }


# def get_topic_tags(primary_kw_text: str) -> set:
#     """
#     Returns the set of broad topic tags this keyword belongs to, based on
#     substring matching. Lets us group e.g. 'mcx gold price' and 'current
#     gold price in kerala' as related even though the exact text differs —
#     catches cases pillar/sibling exact-matching structurally can't.
#     """
#     tags = set()
#     text = f" {primary_kw_text} "  # padding so " ipo " boundary check works
#     for tag, triggers in TOPIC_TAGS.items():
#         if any(trigger in text for trigger in triggers):
#             tags.add(tag)
#     return tags


# def get_blog_topic_tags(primary_kw_text: str, secondary_kws: list = None) -> set:
#     """
#     Same as get_topic_tags but also checks secondary keywords — a blog
#     whose PRIMARY keyword doesn't mention gold but whose SECONDARY
#     keywords do should still be tagged as gold-related.
#     """
#     tags = get_topic_tags(primary_kw_text)
#     for sec in (secondary_kws or []):
#         tags |= get_topic_tags(sec)
#     return tags


# def add_topic_group_siblings(records, graph):
#     """
#     Groups records by topic tag and links every pair within a group as
#     siblings, UNLESS they're already connected via pillar/child. This is
#     a looser, broader connection than exact keyword matching — it's meant
#     to catch same-subject blogs that pillar/child rules structurally miss.
#     """
#     by_topic = defaultdict(list)
#     for r in records:
#         for tag in get_blog_topic_tags(r["primary_kw"], r["secondary_kws"]):
#             by_topic[tag].append(r["id"])

#     for tag, ids in by_topic.items():
#         if len(ids) < 2:
#             continue
#         for i in range(len(ids)):
#             for j in range(i + 1, len(ids)):
#                 a, b = ids[i], ids[j]
#                 if graph[a]["pillar"] == b or graph[b]["pillar"] == a:
#                     continue  # already connected via a stronger relationship
#                 if b not in graph[a]["siblings"]:
#                     graph[a]["siblings"].append(b)
#                 if a not in graph[b]["siblings"]:
#                     graph[b]["siblings"].append(a)


# def normalize_keyword(kw):
#     """
#     Handles both enriched (dict, has real volume) and raw (string, no
#     volume data yet) keyword formats.

#     Returns (text, volume, has_volume) — has_volume distinguishes
#     "genuinely zero search volume" from "we simply don't know yet",
#     so downstream ranking never treats missing data as if it were a
#     real zero.
#     """
#     if isinstance(kw, dict):
#         text = (kw.get("google_keyword") or kw.get("original") or "").strip().lower()
#         volume = kw.get("volume", 0) or 0
#         has_volume = "volume" in kw
#     else:
#         text = str(kw).strip().lower()
#         volume = 0
#         has_volume = False
#     return text, volume, has_volume


# def load_records(blogs):
#     """Flatten each blog into a normalized record keyed by its webflow_url."""
#     records = []
#     for b in blogs:
#         url = b.get("webflow_url")
#         if not url:
#             continue  # should already be filtered out, but skip defensively

#         primary_text, primary_vol, primary_has_vol = normalize_keyword(b.get("primary_keyword", ""))
#         secondaries = [normalize_keyword(s) for s in b.get("secondary_keywords", [])]

#         records.append({
#             "id": url,
#             "title": b.get("blog", {}).get("Blog_Title") or b.get("Blog_Title", ""),
#             "primary_kw": primary_text,
#             "primary_vol": primary_vol,
#             "primary_has_vol": primary_has_vol,
#             "secondary_kws": [s[0] for s in secondaries if s[0]],
#             "secondary_vols": {s[0]: s[1] for s in secondaries if s[0]},
#         })
#     return records


# def elect_pillars(records):
#     """
#     If multiple records share the same primary keyword, pick a canonical
#     pillar. Priority order:
#         1. Enriched (has real volume) beats non-enriched — never let a
#            missing-data default of 0 lose to an actual number, or vice versa.
#         2. Among enriched records, highest volume wins.
#         3. Among non-enriched records (no volume data at all on either
#            side), fall back to richer content (_content_quality) as a
#            weak tiebreaker — first one wins otherwise, and it's flagged
#            for manual review either way.

#     Returns {primary_kw: record_id}.
#     """
#     by_primary = defaultdict(list)
#     for r in records:
#         if r["primary_kw"]:
#             by_primary[r["primary_kw"]].append(r)

#     canonical = {}
#     for kw, group in by_primary.items():
#         if len(group) > 1:
#             group.sort(key=lambda r: (r["primary_has_vol"], r["primary_vol"]), reverse=True)
#             has_mixed_enrichment = len({r["primary_has_vol"] for r in group}) > 1
#             flag = " [MIXED ENRICHMENT — verify]" if has_mixed_enrichment else ""
#             print(f"[GRAPH] Collision on primary keyword '{kw}' — {len(group)} blogs share it,"
#                   f"{flag} using: {group[0]['title'][:60]}")
#         canonical[kw] = group[0]["id"]

#     return canonical


# def build_graph(records):
#     by_id = {r["id"]: r for r in records}
#     pillar_by_kw = elect_pillars(records)

#     graph = {
#         r["id"]: {
#             "title": r["title"],
#             "primary_kw": r["primary_kw"],
#             "primary_vol": r["primary_vol"],
#             "secondary_kws": r["secondary_kws"],
#             "pillar": None,
#             "children": [],
#             "siblings": [],
#         }
#         for r in records
#     }

#     # ── Rule 1a: same-primary-keyword edges ──────────────────────────────
#     # If multiple blogs share the exact same primary keyword (a recurring
#     # topic — e.g. the same stock covered across several news events),
#     # link the non-canonical ones to the canonical pillar directly. Without
#     # this, blogs that never cross-reference each other via a secondary
#     # keyword stay disconnected even though they're obviously about the
#     # same thing.
#     for r in records:
#         if not r["primary_kw"]:
#             continue
#         pillar_id = pillar_by_kw.get(r["primary_kw"])
#         if pillar_id and pillar_id != r["id"]:
#             graph[r["id"]]["pillar"] = pillar_id
#             graph[pillar_id]["children"].append(r["id"])

#     # ── Rule 1b: secondary-to-primary pillar-child edges ─────────────────
#     for r in records:
#         if graph[r["id"]]["pillar"]:
#             continue  # already assigned a pillar via Rule 1a
#         for sec_kw in r["secondary_kws"]:
#             pillar_id = pillar_by_kw.get(sec_kw)
#             if pillar_id and pillar_id != r["id"]:
#                 graph[r["id"]]["pillar"] = pillar_id
#                 graph[pillar_id]["children"].append(r["id"])
#                 break  # one primary pillar per blog is enough

#     # ── Rule 2: sibling edges (shared secondary keyword, no pillar link) ─
#     secondary_index = defaultdict(list)
#     for r in records:
#         for sec_kw in r["secondary_kws"]:
#             secondary_index[sec_kw].append(r["id"])

#     for kw, ids in secondary_index.items():
#         if len(ids) < 2:
#             continue
#         for i in range(len(ids)):
#             for j in range(i + 1, len(ids)):
#                 a, b = ids[i], ids[j]
#                 # skip if they're already in a pillar-child relationship
#                 if graph[a]["pillar"] == b or graph[b]["pillar"] == a:
#                     continue
#                 if b not in graph[a]["siblings"]:
#                     graph[a]["siblings"].append(b)
#                 if a not in graph[b]["siblings"]:
#                     graph[b]["siblings"].append(a)

#     # ── Rule 3: topic-tag siblings (catches wording differences) ────────
#     add_topic_group_siblings(records, graph)

#     return graph


# def summarize(graph):
#     pillars = sum(1 for v in graph.values() if v["children"])
#     orphans = sum(1 for v in graph.values() if not v["pillar"] and not v["children"] and not v["siblings"])
#     with_pillar = sum(1 for v in graph.values() if v["pillar"])
#     with_siblings_only = sum(1 for v in graph.values() if v["siblings"] and not v["pillar"] and not v["children"])

#     print("\n[GRAPH] ── Summary ──────────────────────────")
#     print(f"  Total blogs:              {len(graph)}")
#     print(f"  Pillars (have children):  {pillars}")
#     print(f"  Have a pillar (children): {with_pillar}")
#     print(f"  Sibling-only connections: {with_siblings_only}")
#     print(f"  Fully isolated (orphans): {orphans}")


# def main():
#     parser = argparse.ArgumentParser()
#     parser.add_argument("--path", required=True, help="Path to blogs_missing_keywords.json")
#     parser.add_argument("--out", default=None, help="Output path for keyword_graph.json (defaults to same folder)")
#     args = parser.parse_args()

#     with open(args.path, "r", encoding="utf-8") as f:
#         blogs = json.load(f)

#     records = load_records(blogs)
#     print(f"[GRAPH] Loaded {len(records)} blogs with confirmed webflow_url")

#     graph = build_graph(records)

#     out_path = args.out or args.path.replace("blogs_missing_keywords.json", "keyword_graph.json")

#     # ── MERGE, don't overwrite — preserve any nodes added live by
#     # add_blog_to_graph() since the last rebuild (e.g. blogs published
#     # after this historical file was last exported). Only rebuild-sourced
#     # nodes get replaced; anything the rebuild doesn't know about survives.
#     if os.path.exists(out_path):
#         with open(out_path, "r", encoding="utf-8") as f:
#             existing_graph = json.load(f)
#         rebuild_urls = set(graph.keys())
#         preserved = {url: node for url, node in existing_graph.items() if url not in rebuild_urls}
#         if preserved:
#             print(f"[GRAPH] Preserving {len(preserved)} node(s) not in the historical file "
#                   f"(likely published after last export):")
#             for url, node in preserved.items():
#                 print(f"  - {node.get('title', url)[:60]}")
#         graph.update(preserved)

#     summarize(graph)

#     with open(out_path, "w", encoding="utf-8") as f:
#         json.dump(graph, f, ensure_ascii=False, indent=2)

#     print(f"\n[GRAPH] Saved to: {out_path}")


# if __name__ == "__main__":
#     main()




"""
build_keyword_graph.py
------------------------
Full-graph builder using the SAME schema and matching rules as
related_links.py -- primary-keyword-indexed groups, exact-match fast
path with a containment-based fuzzy fallback (imported directly from
related_links.py so both files can never drift out of sync).

Safe to re-run at any time:
    - Starts from whatever keyword_graph.json already exists (so any
      blogs added live by add_blog_to_graph() since the last rebuild
      are automatically preserved, never overwritten).
    - Skips any blog whose URL is already present anywhere in the graph
      (dedup by URL), so re-running never creates duplicates.
    - Only adds blogs from blogs_missing_keywords.json that aren't
      already in the graph yet.

Usage:
    python build_keyword_graph.py --path "D:\\Blogheading\\output\\blogs_missing_keywords.json"
"""

import json
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # repo root, for related_links
from related_links import _normalize_keyword_field, _find_group_key, load_graph, save_graph


def load_records(blogs):
    """Flatten each blog into a normalized record ready for grouping."""
    records = []
    for b in blogs:
        url = b.get("webflow_url")
        if not url:
            continue  # skip anything without a confirmed published URL

        primary_text, primary_vol = _normalize_keyword_field(b.get("primary_keyword", ""))
        secondary_texts = [_normalize_keyword_field(s)[0] for s in b.get("secondary_keywords", [])]
        secondary_texts = [t for t in secondary_texts if t]
        title = b.get("blog", {}).get("Blog_Title") or b.get("Blog_Title", "")

        records.append({
            "url": url,
            "title": title,
            "primary_kw": primary_text,
            "volume": primary_vol,
            "secondary_kws": secondary_texts,
        })
    return records


def existing_urls(graph: dict) -> set:
    """Every blog URL already present anywhere in the graph, across all groups."""
    urls = set()
    for group in graph.values():
        for blog in group:
            urls.add(blog["url"])
    return urls


def add_record_to_graph(record: dict, graph: dict):
    """Same exact-match-then-fuzzy-fallback logic as add_blog_to_graph() in related_links.py."""
    group_key = _find_group_key(record["primary_kw"], graph)
    entry = {
        "url": record["url"],
        "title": record["title"],
        "volume": record["volume"],
        "secondary_kws": record["secondary_kws"],
    }
    if group_key:
        graph[group_key].append(entry)
    else:
        graph[record["primary_kw"]] = [entry]


def summarize(graph: dict):
    total_blogs = sum(len(g) for g in graph.values())
    total_groups = len(graph)
    grouped = sum(1 for g in graph.values() if len(g) > 1)
    isolated = sum(1 for g in graph.values() if len(g) == 1)
    largest = max((len(g) for g in graph.values()), default=0)

    print("\n[GRAPH] --- Summary --------------------------")
    print(f"  Total blogs:           {total_blogs}")
    print(f"  Total groups:          {total_groups}")
    print(f"  Groups with >1 blog:   {grouped}")
    print(f"  Isolated (singleton):  {isolated}")
    print(f"  Largest group size:    {largest}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", required=True, help="Path to blogs_missing_keywords.json")
    parser.add_argument("--out", default=None, help="Output path for keyword_graph.json (defaults to same folder)")
    args = parser.parse_args()

    with open(args.path, "r", encoding="utf-8") as f:
        blogs = json.load(f)

    out_path = args.out or args.path.replace("blogs_missing_keywords.json", "keyword_graph.json")

    # Start from whatever graph already exists -- this is what preserves
    # any blogs added live by add_blog_to_graph() since the last rebuild.
    graph = load_graph(out_path)
    already_present = existing_urls(graph)

    records = load_records(blogs)
    added = 0
    skipped = 0
    for r in records:
        if r["url"] in already_present:
            skipped += 1
            continue
        add_record_to_graph(r, graph)
        added += 1

    print(f"[GRAPH] Loaded {len(records)} blogs from historical file")
    print(f"[GRAPH] Added {added} new blog(s), skipped {skipped} already present in the graph")

    summarize(graph)

    save_graph(graph, out_path)
    print(f"\n[GRAPH] Saved to: {out_path}")


if __name__ == "__main__":
    main()