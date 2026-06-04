import json
from add_cached import cached_model_call


def filter_by_country_and_category(data, user_country, user_category):
    """
    Filters articles by BOTH country AND category.
    Sends title + content snippet for better accuracy.
    Returns only articles matching both — no fallback permissiveness.
    """
    if not data:
        return [], "none"

    # ── Build text with title + content snippet ───────────────
    # Sending first 200 chars of content gives AI much better
    # context without increasing token cost significantly
    text = ""
    for i, item in enumerate(data):
        title   = item.get("Blog_Title", "").strip()
        content = item.get("Blog_Content", "").strip()

        # Take first 200 chars of content as context
        snippet = content[:200].replace("\n", " ").strip() if content else ""

        text += f"{i}. Title  : {title}\n"
        if snippet:
            text += f"   Content: {snippet}\n"
        text += "\n"

    prompt = f"""You are a strict news filter for a financial blog platform.

COUNTRY  : "{user_country}"
CATEGORY : "{user_category}"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STRICT RULE — BOTH must match:
  Article MUST be about {user_country} AND {user_category}
  If only country matches but NOT finance → REJECT
  If only finance matches but not India → REJECT
  When in doubt → REJECT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

FINANCE signals — include if title OR content has:
  stock, share, IPO, market, nifty, sensex, bse, nse,
  rbi, sebi, epfo, pf, provident fund, upi withdrawal,
  dividend, bonus, split, mutual fund, etf, sip,
  gold price, crude oil, rupee, interest rate, inflation,
  gdp, budget, tax, revenue, profit, earnings, quarterly,
  tcs, infosys, reliance, hdfc, icici, sbi, bank results,
  ipo gmp, listing, trading, invest, portfolio, economy,
  tariff, trade, export, import, fiscal, monetary policy,
  pension, gratuity, salary, income tax, itr, tds, gst

NOT FINANCE — reject these even if India-related:
  politics, election, party, minister, yojana, scheme,
  cricket, football, sports, match, tournament,
  bollywood, movie, actor, celebrity,
  weather, rain, flood, disaster,
  crime, arrest, court, murder,
  horoscope, astrology, religion,
  lifestyle, food, travel, fashion,
  lottery, result, exam, education

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HOW TO USE CONTENT:
  Title alone may be vague — use content to confirm.
  Example:
    Title: "dl55"  → unclear
    Content: "Kerala Lottery result Rs 1 crore winner" → REJECT (lottery)

    Title: "epfo 3.0 new features" → finance signal
    Content: "EPFO UPI access PF withdrawal funds" → ACCEPT ✅

    Title: "trump tariffs" → unclear
    Content: "India IT exports impacted by US trade tariffs" → ACCEPT ✅
    Content: "Canada Mexico EU forced labour tariffs" → REJECT (not India)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Blog Articles (0-indexed):
{text}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Return ONLY this JSON — no text before or after:
{{
    "matched": [0, 2, 5],
    "source": "user"
}}

source values:
  "user" → matched both India + finance strictly
  "none" → nothing matched

IMPORTANT: If no articles match, return empty list.
Do NOT return politics, sports, lottery, astrology articles.
{{
    "matched": [],
    "source": "none"
}}
"""

    raw = cached_model_call(prompt)

    try:
        parsed  = json.loads(raw)
        indices = parsed.get("matched", [])
        source  = parsed.get("source", "none")

        valid_indices = [
            i for i in indices
            if isinstance(i, int) and 0 <= i < len(data)
        ]

        filtered = [data[i] for i in valid_indices]

        if not filtered:
            print(f"[FILTER] No India+finance match found — returning empty")
            return [], "none"

        print(f"[FILTER] {len(filtered)} articles matched "
              f"(country={user_country}, category={user_category}, source={source})")

        return filtered, source

    except Exception as e:
        print(f"[FILTER] Parsing failed: {e}")
        print(f"RAW: {raw}")
        return [], "none"