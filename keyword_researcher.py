# """
# keyword_researcher.py
# ═════════════════════
# Fetches real Google search volume data for any article topic
# and injects it into the blog generation prompt.

# PIPELINE INTEGRATION — ONE LINE CHANGE
# ────────────────────────────────────────
# In mergeall_engine.py:

#     from keyword_researcher import enrich_with_keywords

#     # BEFORE:
#     data = generate_blog(item)

#     # AFTER:
#     item = enrich_with_keywords(item)   ← add this line
#     data = generate_blog(item)

# THAT'S IT. Everything else stays the same.
# """

# import logging
# from google.ads.googleads.client import GoogleAdsClient

# log = logging.getLogger(__name__)

# # ─────────────────────────────────────────────────────────────────────────────
# # CONFIG
# # ─────────────────────────────────────────────────────────────────────────────

# CUSTOMER_ID  = "2948017527"   # your Google Ads customer ID
# INDIA_GEO    = "2356"         # India location ID
# ENGLISH_LANG = "1000"         # English language ID
# TOP_N        = 8              # how many keywords to return


# # ─────────────────────────────────────────────────────────────────────────────
# # STEP 1 — Extract seed keywords from article item
# # ─────────────────────────────────────────────────────────────────────────────

# def extract_seeds(item: dict) -> list[str]:
#     """
#     Builds seed keywords from the article item.
#     These seeds are sent to Google Keyword Planner.

#     Examples:
#         # Google Trends article
#         item = {"Blog_Title": "ifci share price"}
#         → ["ifci share price"]

#         # NSE Corporate Action
#         item = {"company_name": "GHCL Limited", "action_type": "dividend", "amount": "₹12 per share"}
#         → ["GHCL Limited", "GHCL Limited dividend", "GHCL Limited dividend ₹12 per share"]

#         # News article
#         item = {"Blog_Title": "Sensex rises 250 points", "source": "economic_times"}
#         → ["Sensex rises 250 points"]
#     """
#     seeds = []

#     # Source 1: company name (corporate actions) or blog title (news/trends)
#     title = (
#         item.get("company_name") or
#         item.get("Blog_Title")   or
#         item.get("title", "")
#     ).strip()

#     if title:
#         seeds.append(title)

#     # Source 2: action type for corporate blogs
#     # e.g. "GHCL Limited" + "dividend" → "GHCL Limited dividend"
#     action = item.get("action_type", "")
#     if action and title:
#         seeds.append(f"{title} {action}")

#     # Source 3: amount for corporate blogs
#     # e.g. "GHCL Limited" + "₹12 per share" → "GHCL Limited ₹12 per share"
#     amount = item.get("amount", "")
#     if amount and title:
#         seeds.append(f"{title} {amount}")

#     # Source 4: ex-date for corporate blogs
#     # e.g. "GHCL Limited dividend" + "ex date" → "GHCL Limited dividend ex date"
#     ex_date = item.get("ex_date", "")
#     if ex_date and action and title:
#         seeds.append(f"{title} {action} ex date")

#     # Remove duplicates, limit to 5
#     seen  = set()
#     clean = []
#     for s in seeds:
#         if s.lower() not in seen and s.strip():
#             seen.add(s.lower())
#             clean.append(s.strip())

#     return clean[:5]


# # ─────────────────────────────────────────────────────────────────────────────
# # STEP 2 — Call Google Keyword Planner
# # ─────────────────────────────────────────────────────────────────────────────

# def get_keyword_volumes(seeds: list[str], top_n: int = TOP_N) -> list[dict]:
#     """
#     Sends seed keywords to Google Keyword Planner.
#     Returns top N keywords sorted by monthly search volume.

#     Args:
#         seeds : list of seed keyword strings
#         top_n : how many results to return

#     Returns:
#         [
#             {"keyword": "ifci share price today",   "volume": 18100, "competition": "LOW"},
#             {"keyword": "ifci share price nse",     "volume":  9900, "competition": "LOW"},
#             ...
#         ]

#     Returns empty list on any error — blog generation continues without keywords.
#     """
#     if not seeds:
#         return []

#     try:
#         client  = GoogleAdsClient.load_from_storage(version="v24")
#         service = client.get_service("KeywordPlanIdeaService")

#         request = client.get_type("GenerateKeywordIdeasRequest")
#         request.customer_id = CUSTOMER_ID
#         request.language    = client.get_service("GoogleAdsService")\
#                                     .language_constant_path(ENGLISH_LANG)
#         request.geo_target_constants = [
#             client.get_service("GeoTargetConstantService")\
#                   .geo_target_constant_path(INDIA_GEO)
#         ]
#         request.include_adult_keywords = False
#         request.keyword_plan_network   = (
#             client.enums.KeywordPlanNetworkEnum.GOOGLE_SEARCH_AND_PARTNERS
#         )
#         request.keyword_seed.keywords.extend(seeds)

#         ideas   = service.generate_keyword_ideas(request=request)
#         results = []

#         for idea in ideas:
#             volume = idea.keyword_idea_metrics.avg_monthly_searches
#             if volume > 0:
#                 results.append({
#                     "keyword"    : idea.text,
#                     "volume"     : volume,
#                     "competition": idea.keyword_idea_metrics.competition.name,
#                 })

#         # Sort by volume — highest first
#         results.sort(key=lambda x: x["volume"], reverse=True)

#         log.info(f"[KEYWORDS] {len(results)} ideas returned for seeds: {seeds}")
#         return results[:top_n]

#     except Exception as e:
#         log.warning(f"[KEYWORDS] API call failed: {e}")
#         print(f"[KEYWORDS] Failed — continuing without keyword data: {e}")
#         return []


# # ─────────────────────────────────────────────────────────────────────────────
# # STEP 3 — Enrich item dict with keyword data
# # ─────────────────────────────────────────────────────────────────────────────

# def enrich_with_keywords(item: dict) -> dict:
#     """
#     Main function — call this BEFORE generate_blog() or generate_corporate_blog().

#     Adds two keys to the item dict:
#         item["top_keywords"] = ["ifci share price today", "ifci share price nse", ...]
#         item["kw_data"]      = [{"keyword": ..., "volume": ..., "competition": ...}, ...]

#     Always returns the item dict — even if keyword fetch fails.
#     Blog generation is never blocked by keyword lookup failure.

#     Example:
#         BEFORE enrichment:
#             item = {"Blog_Title": "ifci share price", "source": "google_trends"}

#         AFTER enrichment:
#             item = {
#                 "Blog_Title"   : "ifci share price",
#                 "source"       : "google_trends",
#                 "top_keywords" : [
#                     "ifci share price today",
#                     "ifci share price nse",
#                     "ifci share price target 2025",
#                     "ifci limited share price",
#                     "ifci share latest news",
#                 ],
#                 "kw_data": [
#                     {"keyword": "ifci share price today",   "volume": 18100, "competition": "LOW"},
#                     {"keyword": "ifci share price nse",     "volume":  9900, "competition": "LOW"},
#                     {"keyword": "ifci share price target",  "volume":  3600, "competition": "LOW"},
#                     ...
#                 ]
#             }
#     """
#     seeds   = extract_seeds(item)
#     kw_data = get_keyword_volumes(seeds, top_n=TOP_N)

#     item["top_keywords"] = [k["keyword"] for k in kw_data]
#     item["kw_data"]      = kw_data

#     if kw_data:
#         top = kw_data[0]
#         print(
#             f"[KEYWORDS] Top: '{top['keyword']}' "
#             f"({top['volume']:,}/mo | {top['competition']})"
#         )
#     else:
#         print("[KEYWORDS] No data — blog will generate without keyword guidance")

#     return item


# # ─────────────────────────────────────────────────────────────────────────────
# # STEP 4 — Build keyword block for prompt injection
# # ─────────────────────────────────────────────────────────────────────────────

# def build_keyword_block(item: dict) -> str:
#     """
#     Builds the keyword intelligence section that gets injected into the prompt.

#     Called inside generate_blog() and generate_ipo_blog()
#     when building the prompt string.

#     Returns empty string if no keyword data — prompt works fine without it.

#     Example output injected into prompt:

#         ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#         KEYWORD INTELLIGENCE  (real Google search volume — India)
#         ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#         PRIMARY KEYWORD (highest volume — MUST appear in Blog_Title and Meta_Title):
#           ifci share price today                    18,100 searches/month  LOW

#         SECONDARY KEYWORDS (use naturally in H2 headings):
#           ifci share price nse                       9,900 searches/month  LOW
#           ifci share price target 2025               1,300 searches/month  LOW
#           ifci limited share price                  90,500 searches/month  LOW
#           ifci share latest news                     8,100 searches/month  LOW

#         RULES:
#           - Primary keyword must appear in Blog_Title, Meta_Title, and first 80 words
#           - Use 2-3 secondary keywords as exact H2 phrases
#           - Do not force keywords that don't fit the content naturally
#     """
#     kw_data = item.get("kw_data", [])

#     if not kw_data:
#         return ""

#     primary    = kw_data[0]
#     secondaries = kw_data[1:]

#     primary_line = (
#         f"  {primary['keyword']:<45} "
#         f"{primary['volume']:>8,} searches/month  "
#         f"{primary['competition']}"
#     )

#     secondary_lines = "\n".join(
#         f"  {k['keyword']:<45} "
#         f"{k['volume']:>8,} searches/month  "
#         f"{k['competition']}"
#         for k in secondaries
#     )

#     return f"""
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# KEYWORD INTELLIGENCE  (real Google Keyword Planner data — India)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PRIMARY KEYWORD — MUST appear in Blog_Title, Meta_Title, and first 80 words:
# {primary_line}

# SECONDARY KEYWORDS — use 2-3 of these naturally as exact H2 heading phrases:
# {secondary_lines}

# KEYWORD RULES:
#   1. Primary keyword must appear EXACTLY as written in Blog_Title and Meta_Title
#   2. Use secondary keywords as H2 headings only where they genuinely fit
#   3. Do not repeat the same keyword in multiple H2s
#   4. Do not force a keyword that doesn't match the article content
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""


# # ─────────────────────────────────────────────────────────────────────────────
# # TEST — run directly to verify everything works
# # ─────────────────────────────────────────────────────────────────────────────

# if __name__ == "__main__":

#     print("=" * 60)
#     print("TEST 1 — Google Trends article (IFCI)")
#     print("=" * 60)

#     item1 = {
#         "Blog_Title": "IC Electricals Company Limited-Issue postponed IPO",
#         "source"    : "nse",
#     }

#     # Show seeds
#     seeds1 = extract_seeds(item1)
#     print(f"Seeds extracted : {seeds1}")

#     # Enrich
#     item1 = enrich_with_keywords(item1)
#     print(f"Top keywords    : {item1['top_keywords'][:3]}")

#     # Show prompt block
#     block1 = build_keyword_block(item1)
#     print(block1)

#     print()
#     print("=" * 60)
#     print("TEST 2 — NSE Corporate Action (GHCL dividend)")
#     print("=" * 60)

#     item2 = {
#         "company_name": "GHCL Limited",
#         "action_type" : "dividend",
#         "amount"      : "₹12 per share",
#         "ex_date"     : "18 Jun 2026",
#         "source"      : "nse_corporate",
#     }

#     seeds2 = extract_seeds(item2)
#     print(f"Seeds extracted : {seeds2}")

#     item2 = enrich_with_keywords(item2)
#     print(f"Top keywords    : {item2['top_keywords'][:3]}")

#     block2 = build_keyword_block(item2)
#     print(block2)


"""
keyword_volume.py
=================
Takes primary + secondary keywords -> queries Google Keyword Planner
-> returns JSON with original, best Google match, volume, competition.

USAGE:
    from keyword_volume import get_keyword_volumes

    result = get_keyword_volumes(
        primary   = "aviation stocks",
        secondary = ["IndiGo share price", "SpiceJet stock NSE"]
    )
    print(result)
"""

import json
from google.ads.googleads.client import GoogleAdsClient

CUSTOMER_ID = "2948017527"
INDIA_GEO   = "2356"
LANGUAGE_ID = "1000"


def _best_match(original: str, volume_map: dict) -> dict:
    """
    Finds the best Google keyword for the original input.

    Logic: from all Google keywords that contain ALL words of the original,
    pick the one with the HIGHEST monthly search volume.

    Example:
        original   = "aviation stocks"
        candidates = ["aviation stocks", "aviation stocks india", "aviation stocks nse"]
        volumes    = [8100, 9900, 1200]
        winner     = "aviation stocks india"  (highest volume)
    """
    original_lower = original.lower().strip()
    original_words = set(original_lower.split())

    # Find all Google keywords where every word of original is present
    candidates = [
        (gkw, data)
        for gkw, data in volume_map.items()
        if original_words.issubset(set(gkw.split()))
    ]

    if candidates:
        # Pick highest volume among all candidates
        best = max(candidates, key=lambda x: x[1]["monthly_searches"])
        return {
            "original"      : original,
            "google_keyword": best[0],
            "volume"        : best[1]["monthly_searches"],
            "competition"   : best[1]["competition"],
        }

    # Fallback: exact match
    if original_lower in volume_map:
        data = volume_map[original_lower]
        return {
            "original"      : original,
            "google_keyword": original_lower,
            "volume"        : data["monthly_searches"],
            "competition"   : data["competition"],
        }

    # Final fallback: no match found
    return {
        "original"      : original,
        "google_keyword": original_lower,
        "volume"        : 0,
        "competition"   : "UNSPECIFIED",
    }


def get_keyword_volumes(primary: str, secondary: list) -> dict:
    """
    Fetches volumes from Google Keyword Planner for primary + secondary keywords.

    Args:
        primary   : primary keyword string
        secondary : list of secondary keyword strings

    Returns:
        {
            "primary_keyword": {
                "original"      : "aviation stocks",
                "google_keyword": "aviation stocks india",
                "volume"        : 9900,
                "competition"   : "MEDIUM"
            },
            "secondary_keywords": [
                {
                    "original"      : "IndiGo share price",
                    "google_keyword": "indigo share price",
                    "volume"        : 40500,
                    "competition"   : "HIGH"
                },
                ...
            ]
        }
    """

    # Combine all into one list for a single API call
    all_keywords = []
    if primary:
        all_keywords.append(primary.strip())
    for kw in secondary:
        kw = kw.strip()
        if kw and kw not in all_keywords:
            all_keywords.append(kw)

    if not all_keywords:
        return {"primary_keyword": {}, "secondary_keywords": []}

    # ── Single API call ───────────────────────────────────────────────────
    client  = GoogleAdsClient.load_from_storage(version="v24")
    service = client.get_service("KeywordPlanIdeaService")

    request = client.get_type("GenerateKeywordIdeasRequest")
    request.customer_id = CUSTOMER_ID
    request.language    = (
        client.get_service("GoogleAdsService")
        .language_constant_path(LANGUAGE_ID)
    )
    request.geo_target_constants = [
        client.get_service("GeoTargetConstantService")
        .geo_target_constant_path(INDIA_GEO)
    ]
    request.include_adult_keywords = False
    request.keyword_plan_network   = (
        client.enums.KeywordPlanNetworkEnum.GOOGLE_SEARCH_AND_PARTNERS
    )
    request.keyword_seed.keywords.extend(all_keywords)

    ideas = service.generate_keyword_ideas(request=request)

    # ── Build volume map from all returned ideas ──────────────────────────
    volume_map = {}
    for idea in ideas:
        volume_map[idea.text.lower()] = {
            "monthly_searches": idea.keyword_idea_metrics.avg_monthly_searches,
            "competition"     : idea.keyword_idea_metrics.competition.name,
        }

    # ── Match primary keyword ─────────────────────────────────────────────
    primary_entry = _best_match(primary, volume_map)

    # ── Match secondary keywords ──────────────────────────────────────────
    secondary_entries = [
        _best_match(kw.strip(), volume_map)
        for kw in secondary
    ]

    # Sort secondary by volume descending
    secondary_entries.sort(key=lambda x: x["volume"], reverse=True)

    return {
        "primary_keyword"   : primary_entry,
        "secondary_keywords": secondary_entries,
    }


if __name__ == "__main__":
    result = get_keyword_volumes(
        primary   = "fifa world cup",
        secondary = [
            "IndiGo share price",
            "SpiceJet stock NSE",
            "aviation sector India",
        ]
    )
    print(json.dumps(result, indent=2))