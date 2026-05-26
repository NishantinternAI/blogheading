# utils/combined_filter.py
import json
from add_cached import cached_model_call


def filter_by_country_and_category(data, user_country, user_category):
    """
    Ek AI call me country + category dono filter karo
    """

    # Sirf titles bhejo — kam tokens = kam cost
    text = ""
    for i, item in enumerate(data):
        title = item.get("Blog_Title", "")
        text += f"{i}. {title}\n"

    prompt = f"""You are a smart news filter. Your job is to filter blog titles by BOTH country and category.

COUNTRY  : "{user_country}"
CATEGORY : "{user_category}"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
COUNTRY RULES:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INCLUDE if title is primarily about:
- The country name itself
- Its institutions (central banks, stock exchanges, government bodies)
- Its major cities or leaders
- Its economy, finance, or domestic policy

EXCLUDE if:
- Title is global/generic with no country-specific focus
- Country is mentioned only secondarily
- Multiple countries mentioned with no clear primary focus
- You are unsure → omit

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CATEGORY RULES:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Categories and their keywords:
- finance  → stock, IPO, banking, market, dividend, ex-date, record date,
             corporate action, bonus, split, demerger, NSE, BSE, RBI, SEBI
- tech     → AI, startups, software, gadgets, digital
- health   → medical, fitness, pharma, hospital
- politics → government, policy, elections, parliament
- sports   → cricket, football, matches, tournament
- lifestyle→ travel, fashion, food, entertainment
- general  → everything else

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MATCHING LOGIC:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
A blog is SELECTED only if it matches BOTH:
✅ Country = "{user_country}"  AND  Category = "{user_category}"

If no match for "{user_category}" → try "finance" as fallback category
If still no match → return all country-matched indices

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Blog Titles (0-indexed):
{text}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Return ONLY this JSON — no text before or after:
{{
    "matched": [0, 2, 5],
    "source": "user"
}}

source values:
- "user"     → matched both country + user category
- "finance"  → matched country + finance (fallback)
- "fallback" → only country matched, no category match
- "none"     → nothing matched at all

If nothing matched at all:
{{
    "matched": [],
    "source": "none"
}}
"""

    # ✅ API Call — sirf ek
    raw = cached_model_call(prompt)

    # ✅ Parse result
    try:
        parsed  = json.loads(raw)
        indices = parsed.get("matched", [])
        source  = parsed.get("source", "fallback")

        # Safety check — valid indices only
        valid_indices = [
            i for i in indices
            if isinstance(i, int) and 0 <= i < len(data)
        ]

        filtered = [data[i] for i in valid_indices]

        # ── Fallback logic ────────────────────────────────
        if not filtered:
            print(f"[FILTER] No match → returning all data")
            return data, "fallback"

        print(f"[FILTER] {len(filtered)} articles matched "
              f"(country={user_country}, category={user_category}, source={source})")

        return filtered, source

    except Exception as e:
        print(f"[FILTER] Parsing failed — returning all data")
        print(f"RAW: {raw}")
        return data, "fallback"