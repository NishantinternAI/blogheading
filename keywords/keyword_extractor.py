from core.model_client import cached_model_call
import json

def extract_keywords(article_content: str) -> dict:
    prompt = f"""
You are an SEO keyword researcher for an Indian stock market blog.

Analyze the article below and extract keywords that real investors
actually type into Google Search — not news headlines.

RULES FOR PRIMARY KEYWORD:
- Maximum 4 words
- Must be a real search query, not an article title
- Format: [Company Name] + [action]  e.g. "IRFC share price"
- Pick the SINGLE most searched company or topic in the article
- No dates, no percentages, no rupee amounts

RULES FOR SECONDARY KEYWORDS:
- Maximum 6 keywords total
- Each keyword: 2 to 5 words only
- No dates  (not "June 2026", not "Q1 FY26")
- No percentages  (not "2% stake", not "58% acquisition")
- No rupee amounts  (not "₹91 floor price")
- Format: [Company] + [generic action]  e.g. "IRFC OFS", "Infosys stock"
- Think: what would an investor search BEFORE reading this news

GOOD EXAMPLES:
  primary_keyword    : "IRFC share price"
  secondary_keywords : ["IRFC OFS", "Infosys stock NSE",
                        "City Union Bank dividend",
                        "Honasa Consumer stock",
                        "Rashi Peripherals acquisition"]

BAD EXAMPLES — never return these:
  "Stocks In Focus Today: Infosys, IRFC..."   ← article title, not a search query
  "IRFC divestment 2% stake June 24 25 2026"  ← too specific, zero search volume
  "IRFC OFS floor price ₹91"                  ← has rupee amount

Return ONLY valid JSON. No markdown. No explanation.

{{
  "primary_keyword": "",
  "secondary_keywords": []
}}

ARTICLE:
{article_content}
"""

    try:
        result = cached_model_call(prompt)
        return json.loads(result)

    except Exception:
        return {{
            "primary_keyword": "",
            "secondary_keywords": []
        }}