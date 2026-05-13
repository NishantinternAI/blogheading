import json
from add_cached import cached_model_call


def generate_instagram_caption(item):


    prompt = f"""

You are a fintech Instagram content creator for a trading platform.

Create an engaging Instagram caption for a market update.

Blog Title: {item['Blog_Title']}
Blog Content: {item['Blog_Content']}

------------------------------------

STRICT DOMAIN RULES (VERY IMPORTANT):
- DO NOT mention or suggest deposits, fixed deposits (FD), savings accounts, bank deposits, interest rates on savings
- ONLY focus on trading & investment ecosystem.

ALLOWED finacial product on swastika apps CONTEXT ONLY:
- Stocks
- F&O (Futures & Options)
- MCX trading
- SLBM
- Pledging
- Mutual Funds (MF)
- ETFs
- Bonds
- IPOs
- Market research (stocks, F&O, commodities)
- Trading strategies 
- algo trading
- AI-based insights (Sarthi)
- Human advisory / assistance

------------------------------------

CAPTION RULES:
- 4–6 lines (Instagram friendly)
- Start with a strong hook (market move / news impact)
- Explain in simple or easy English
- Add user perspective (why it matters)
- Add a soft CTA mentioning Swastika app naturally
- CTA should relate to trading/investing only .
- Use 1–2 emojis max

------------------------------------



------------------------------------

HASHTAGS:
- 5–8 relevant hashtags
- Focus on trading/investing only

------------------------------------

OUTPUT:
Return ONLY valid JSON:

{{
  "instagram_caption": ""
}}


Example style:
Hook line
Explanation
User insight
CTA
#hashtags
"""

    result = cached_model_call(prompt)
      # Convert string → JSON
    data = json.loads(result)
    return data