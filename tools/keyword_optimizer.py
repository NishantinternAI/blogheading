"""
keyword_optimizer.py  v5
════════════════════════
Full context-aware keyword optimization — Pass 2.

PIPELINE INTEGRATION
────────────────────
In mergeall_engine.py:

    from keyword_optimizer import optimize_keywords

    final_item["blog"] = _parse_blog_output(final_item["blog"])
    final_item["blog"] = optimize_keywords(final_item["blog"], final_item)
"""

import os
import sys
import json
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # repo root, for add_cached
from add_cached import cached_model_call

log = logging.getLogger(__name__)


def optimize_keywords(blog_data: dict, item: dict) -> dict:
    """
    Full context-aware keyword optimization.

    Targets:
        Blog_Title, Meta_Title, H1, H2, H3, H4,
        First 100 words, relevant paragraphs, FAQ answers

    Args:
        blog_data : output dict from generate_blog()
        item      : item dict with kw_data from enrich_with_keywords()

    Returns:
        same blog_data dict with keywords woven in naturally
    """

    # ── Safety checks ─────────────────────────────────────────
    kw_data = item.get("kw_data", [])
    if not kw_data:
        print("[OPTIMIZER] No keyword data — skipping")
        return blog_data

    if not blog_data.get("Blog_Content"):
        print("[OPTIMIZER] Empty Blog_Content — skipping")
        return blog_data

    # ── Build keyword reference list ──────────────────────────
    kw_lines = "\n".join(
        f"  [{i+1:02d}] {k['keyword']:<50} {k['volume']:>12,}/month"
        for i, k in enumerate(kw_data)
    )

    blog_title   = blog_data.get("Blog_Title",   "")
    meta_title   = blog_data.get("Meta_Title",   "")
    blog_content = blog_data.get("Blog_Content", "")

    # ── Prompt ────────────────────────────────────────────────
    prompt = f"""You are a senior SEO editor optimizing an already-written financial blog
using real Google Keyword Planner data for India.

Task: Improve SEO relevance without changing facts, statistics, dates,
numbers, meaning, structure, TLDR, tables, or conclusion.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CURRENT BLOG
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Blog_Title : {blog_title}
Meta_Title : {meta_title}

Blog_Content:
{blog_content}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
GOOGLE KEYWORD PLANNER DATA (India — real monthly search volumes)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{kw_lines}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OPTIMIZE THESE TARGETS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Blog_Title
- Meta_Title (under 60 characters)
- H1, H2, H3, H4 headings
- First 100 words
- FAQ questions and answers

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1.  Read the entire blog before making any changes.
2.  Insert keywords only where they genuinely match the content.
3.  Prefer replacing generic phrases with specific keyword phrases.
4.  Never force keywords into unrelated sections.
6.  Primary keyword must appear naturally in Blog_Title, H1, and first 100 words.
7.  Secondary keywords may be used only where context strongly supports them.
8.  Preserve readability and human-written flow.
9.  If a keyword does not fit naturally — skip it.
10. Do not rewrite the whole article — make only necessary SEO improvements.
11. Never change any factual information — numbers, dates, statistics are sacred.
12. Avoid keyword stuffing and repetition.
13. Meta_Title must be under 60 characters — count every character.
14. Return the complete Blog_Content — never truncate.
15. TLDR list items must not be changed.
16. Conclusion paragraphs must not be rewritten for keywords.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT — valid JSON only, no markdown, no explanation
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{{
  "Blog_Title"   : "",
  "Meta_Title"   : "",
  "Blog_Content" : "",
  "changes"      : [
    {{
      "target" : "Blog_Title / Meta_Title / H1 / H2 / H3 / H4 / paragraph / FAQ_question / FAQ_answer / first_100_words",
      "before" : "original text",
      "after"  : "optimized text",
      "keyword": "keyword used",
      "reason" : "why this keyword fits here"
    }}
  ]
}}
"""

    # ── Call LLM ──────────────────────────────────────────────
    print("[OPTIMIZER] Running keyword optimization...")

    try:
        result = cached_model_call(prompt)
    except Exception as e:
        log.error(f"[OPTIMIZER] API call failed: {e}")
        print(f"[OPTIMIZER] API failed — returning original: {e}")
        return blog_data

    # ── Parse JSON ────────────────────────────────────────────
    try:
        optimized = json.loads(result)
    except json.JSONDecodeError as e:
        log.warning(f"[OPTIMIZER] JSON parse failed: {e}")
        print("[OPTIMIZER] Parse failed — returning original blog")
        return blog_data

    # ── Apply changes ─────────────────────────────────────────
    if optimized.get("Blog_Title"):
        blog_data["Blog_Title"]   = optimized["Blog_Title"]

    if optimized.get("Meta_Title"):
        blog_data["Meta_Title"]   = optimized["Meta_Title"]

    if optimized.get("Blog_Content"):
        blog_data["Blog_Content"] = optimized["Blog_Content"]

    # ── Log changes ───────────────────────────────────────────
    changes = optimized.get("changes", [])

    if changes:
        print(f"[OPTIMIZER] {len(changes)} optimizations applied:")
        for c in changes:
            print(f"  [{c.get('target','').upper()}]")
            print(f"    Before  : {str(c.get('before',''))[:80]}")
            print(f"    After   : {str(c.get('after', ''))[:80]}")
            print(f"    Keyword : {c.get('keyword','')}")
            print(f"    Reason  : {c.get('reason', '')}")
    else:
        print("[OPTIMIZER] No changes — blog already well optimized")

    return blog_data