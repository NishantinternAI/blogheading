# import json
# from core.model_client import cached_model_call


# def generate_instagram_caption(item):


#     prompt = f"""

# You are a fintech Instagram content creator for a trading platform.

# Create an engaging Instagram caption for a market update.

# Blog Title: {item['Blog_Title']}
# Blog Content: {item['Blog_Content']}

# ------------------------------------

# STRICT DOMAIN RULES (VERY IMPORTANT):
# - DO NOT mention or suggest deposits, fixed deposits (FD), savings accounts, bank deposits, interest rates on savings
# - ONLY focus on trading & investment ecosystem.

# ALLOWED finacial product on swastika apps CONTEXT ONLY:
# - Stocks
# - F&O (Futures & Options)
# - MCX trading
# - SLBM
# - Pledging
# - Mutual Funds (MF)
# - ETFs
# - Bonds
# - IPOs
# - Market research (stocks, F&O, commodities)
# - Trading strategies 
# - algo trading
# - AI-based insights (Sarthi)
# - Human advisory / assistance

# ------------------------------------

# CAPTION RULES:
# - 4–6 lines (Instagram friendly)
# - Start with a strong hook (market move / news impact)
# - Explain in simple or easy English
# - Add user perspective (why it matters)
# - Add a soft CTA mentioning Swastika app naturally
# - CTA should relate to trading/investing only .
# - Use 1–2 emojis max

# ------------------------------------



# ------------------------------------

# HASHTAGS:
# - 5–8 relevant hashtags
# - Focus on trading/investing only

# ------------------------------------

# OUTPUT:
# Return ONLY valid JSON:

# {{
#   "instagram_caption": ""
# }}


# Example style:
# Hook line
# Explanation
# User insight
# CTA
# #hashtags
# """

#     result = cached_model_call(prompt)
#       # Convert string → JSON
#     data = json.loads(result)
#     return data
# generators/generate_instagram_caption.py

import json
from core.model_client import cached_model_call
# ─────────────────────────────────────────
# Normalized Swastika Services Tag Line
# ─────────────────────────────────────────


def generate_instagram_caption(item):
    title   = item.get("Blog_Title", "")
    content = item.get("Blog_Content", "")
    prompt = f"""
    You are a Instagram caption writer for Swastika Investmart.

Your job is to convert stock market news into a HIGH-ENGAGEMENT Instagram caption that feels real, emotional, and relatable for Indian retail investors.

NEWS:
Title: {title}
Content: {content}


━━━━━━━━━━━━━━━
RULES:

- Tone: Informal, conversational, human-like
- Not too technical or jargon-heavy
- Avoid sounding like a news report
- Output must be strictly in English.
-Keep the flow natural and readable
- Caption should feel like a real human wrote it
DO NOT use label-style writing like: -
 "Why it matters:" 
 - "Takeaway:" - "Key point:" 
 - "Bottom line:" Instead, naturally blend insights into the caption flow.

━━━━━━━━━━━━━━━
STRUCTURE:

1. Strong emotional hook (first line must grab attention)
2. Connect news to user's money/portfolio
3. Simplify the insight
4. Add a smart takeaway or perspective
5. End with a thought-provoking line
FORMATTING RULES (STRICT):
- Write the caption as ONE continuous flowing paragraph
-DO NOT use label-style prefixes like:
    "Smart takeaway:" / "P.S." / "Key point:" / "Bottom line:" / "Note:"
- DO NOT split sentences onto separate lines
- All sentences must flow together naturally like a human wrote it in one go
- Only the final tagline should be on a new line
-Everything should read like one human naturally speaking
After the caption, write a short  message that tells the user
WHY they should come to Swastika Apps — based on the news in the caption.

RULES:
- Connect directly to the caption topic (don't write generic lines)
- Sound like a helpful friend, not a salesman
-Everything should read like one human naturally speaking
- End with a soft call-to-action (download, explore, check)


EXAMPLES based on context:
  FX / Inflation news   → mention Research, AI Assistance, Bonds, MF
  Stock rally news      → mention Stocks, F&O, Research
  Dividend news         → mention Investment Trading, ETF, MF


━━━━━━━━━━━━━━━
📦 OUTPUT FORMAT (STRICT JSON ONLY):

{{
  "instagram_caption": "<caption here>",
  "hashtags": "#Nifty #StockMarket #IndianInvestor #MarketUpdate #SwastikaInvestmart"
}}
"""

#     prompt = f"""
# # You are a Instagram caption writer for Swastika Investmart.
# # Your job is to convert stock market news into a HIGH-ENGAGEMENT Instagram caption that feels real, emotional, and relatable for Indian retail investors.

# # NEWS:
# # Title: {title}
# # Content: {content}

# # ━Write a scroll-stopping Instagram caption  with a strong hook, sharp insights, urgency, and no repetitive lines.
# # Tone:
# # - Informal, conversational, human-like
# # - Not too technical or jargon-heavy
# # - Avoid sounding like a news report.
# # - Output must be strictly in English (no Hindi, no Hinglish, no mixed language)
# # Structure:
# # 1. Start with a strong hook scroll-stopping  (emotion-driven)
# # 2. Connect news to the reader’s money/portfolio
# # 3. Simplify the insight (why it matters to them)
# # 4. Add a subtle takeaway or perspective
# # 5. End with a thought-provoking or engaging line
# # Return ONLY valid JSON:

# # {{
# #   "instagram_caption": " ",
# #   "hashtags": "#Nifty #StockMarket #IndianInvestor #MarketUpdate #SwastikaInvestmart"
# # }}
# """

    result = cached_model_call(prompt)
    data   = json.loads(result)
    return data