
import json
from add_cached import cached_model_call

def generate_blog(item):
    prompt = f"""
You are a financial blog writer for Swastika Investmart, writing for RETAIL INVESTORS in India.

NEWS:
Title: {item['Blog_Title']}
Content: {item['Blog_Content']}

Return ONLY valid JSON in this format:

{{
  "Meta_Title": "SEO friendly title under 60 characters",
  "Meta_Description": "Short description under 160 characters",
  "TLDR": [
    "What happened - one line simple summary",
    "Direct impact on investor portfolio",
    "Top priority sector to watch",
    "One clear action investor should take today"
  ],
  "Blog_Title": "Catchy investor-focused blog title",
  "Blog_Content": "HTML blog using H1, H2, H3, H4 tags (600-800 words) - structure below",
  "Investor_Impact": {{
    "primary_sector": "Most important sector affected",
    "secondary_sector": "Second most important sector",
    "avoid_sector": "Sector to avoid right now",
    "action": "Buy / Hold / Wait / Avoid",
    "reason": "One line reason for the action"
  }},
  "Action_Points": [
    "Specific action investor can take TODAY",
    "What to watch this week",
    "Risk to keep in mind"
  ],
  "FAQ_Schema": {{
    "@context": "https://schema.org",
    "@type": "FAQPage",
    "mainEntity": [
      {{
        "@type": "Question",
        "name": "Investor focused question",
        "acceptedAnswer": {{
          "@type": "Answer",
          "text": "Clear actionable answer for investor"
        }}
      }}
    ]
  }},
  "Conclusion": "Short investor-focused summary with clear next step",
  "CTA": "https://trade.swastika.co.in/"
}}

=====================================
!! MOST CRITICAL - READ BEFORE WRITING TITLE !!
=====================================

EVERY Blog_Title and Meta_Title MUST have ALL 3 of these.
If ANY one is missing - title is WRONG. Rewrite it.

MANDATORY 3:
1. ONE NUMBER    -> Rs amount, %, crore, points, times, date
2. ONE "YOU"     -> "You", "Your", "Are You", "Should You"
3. ONE QUESTION  -> ends with "?" OR ends with clear benefit

SELF CHECK BEFORE WRITING:
Ask: Does my title have a number? YES/NO
Ask: Does my title have "You" or "Your"? YES/NO
Ask: Does my title end with question or benefit? YES/NO
-> All 3 must be YES. If any NO -> rewrite.

THESE TITLES ARE WRONG - missing mandatory 3:
X "Sugar Stocks Slide After Centre Tightens Export Rules"
   Missing: number, "you", question


THESE ARE CORRECT - have all mandatory 3:
OK "Sugar Stocks Fall 5% on Export Rules - Should You Sell Now?"
   Has: 5% (number), "You" (personal), "?" (question)

OK "Block Deals Surge Today - Which Stocks Should You Watch Now?"
   Has: "Today" (time ref), "You" (personal), "?" (question)

=====================================
BANNED WORDS - NEVER USE IN TITLE OR META
=====================================

BANNED            -> REPLACE WITH
Ex-Date           -> Last Date to Buy / Buy Before [date-1]
Record Date       -> Remove it or say Eligibility Date
PAT               -> Profit
EBITDA            -> Operating Profit
YoY               -> vs Last Year
QoQ               -> vs Last Quarter
Consolidated      -> Total Company
Standalone        -> India Business
Basis Points      -> Interest Rate
Monetary Policy   -> RBI Decision
Geopolitical      -> War / Conflict
Macroeconomic     -> Economy
Liquidity         -> Cash
Headwinds         -> Challenges
Tailwinds         -> Benefits
Volatile          -> Up and Down
Correction        -> Market Fall
Sequential        -> Quarter on Quarter

=====================================
TITLE FORMULA - FOLLOW THIS STRUCTURE
=====================================

[Company/Topic + Number] - [Simple Fact] - [Your Question]

STEP 1 -> Company name + Rs amount or %     <- SEO keyword first
STEP 2 -> Simple fact what happened         <- User understands instantly
STEP 3 -> End with "Your" question "?"      <- Personal + clickable

EXAMPLES BY NEWS TYPE:

DIVIDEND NEWS:
Input:  "SBI - Ex-Date: 15-May-2026, Dividend Rs 17"
Output: "SBI Gives Rs 17 Dividend - Buy Before May 14, Are You Eligible?"

PROFIT/LOSS NEWS:
Input:  "Dr Reddy Q4 PAT falls 86% YoY"
Output: "Dr Reddy Profit Falls 86% - Should You Buy or Exit Now?"

MARKET FALL:
Input:  "Sensex down 3400 points in 4 sessions"
Output: "Sensex Falls 3,400 Points in 4 Days - Is Your Money Safe?"

POLICY NEWS:
Input:  "RBI cuts repo rate by 25 basis points"
Output: "RBI Cuts Rate - Will Your Home Loan EMI Drop This Month?"

EXPORT/RULE NEWS:
Input:  "Centre tightens sugar export rules"
Output: "Sugar Export Rules Tighten - Should You Sell Sugar Stocks Now?"

BLOCK DEAL NEWS:
Input:  "Block deal rush in Indian stock market"
Output: "Block Deals Surge Today - Which Stocks Should You Watch Now?"

IPO NEWS:
Input:  "Simca Advertising IPO subscribed 80x"
Output: "This IPO Got 80x Demand - Should You Apply Before Deadline?"

GOLD/SILVER NEWS:
Input:  "Gold price hits Rs 16789 today"
Output: "Gold Hits Rs 16,789 Today - Good Time to Buy or Wait?"

=====================================
GOOD TITLES - ALL PASS MANDATORY 3 CHECK:
=====================================
OK "SBI Gives Rs 17 Dividend - Are You Eligible Before May 15?"
OK "Sensex Falls 3,400 Points - Is Your Money Safe?"
OK "HDFC Life Rs 2.10 Dividend - Buy Before June 18, Are You Eligible?"
OK "Nifty IT Crashes 3% - Is Your Portfolio at Risk Today?"
OK "Gold Hits Rs 16,789 - Should You Buy Now or Wait?"
OK "Royal Enfield Rs 2,200 Cr Plan - Which Stocks Will Gain?"
OK "RBI Cuts Rate - Will Your Home Loan EMI Drop This Month?"
OK "Dr Reddy Profit Falls 86% - Should You Buy or Exit Now?"
OK "Sugar Stocks Fall 5% on Export Rules - Should You Sell Now?"
OK "Block Deals Surge Today - Which Stocks Should You Watch?"

BAD TITLES - FAIL MANDATORY 3 CHECK:
=====================================
X "Sugar Stocks Slide After Centre Tightens Export Rules Till S"
X "Block deal rush sparks revival hopes in Indian stock market"
X "SBI Q4 Consolidated PAT Falls 86% YoY on Lower Revenue"
X "Macroeconomic Headwinds Impact Nifty Trajectory Today"
X "JSW Energy Limited - Ex-Date: 05-Jun-2026"
X "One MobiKwik Systems Q4 Results Co Swings to Black"

=====================================
STRICT HTML FORMATTING RULES - NEVER BREAK THESE
=====================================

1. NEVER put multiple points on the same line
2. NEVER use plain dashes (-) for bullet points always use <ul><li>
3. NEVER use 1) 2) 3) numbered format - always use <ul><li>
4. NEVER output \\n or \\n\\n - use HTML tags only
5. Sectors To Watch MUST use <ul><li> - one <li> per priority
6. Action Points MUST use <ul><li> - one <li> per investor type
7. Key Risks MUST use <ul><li> - one <li> per risk
8. Key Takeaways MUST use <ul><li> - exactly 4 <li> items
9. FAQ questions MUST use <h4> - one <h4> per question
10. NEVER add <h2>Conclusion</h2> inside Blog_Content
11. NEVER add CTA URL inside Blog_Content

WRONG FORMAT - NEVER DO THIS:
X <p>1st Priority: FMCG - reason. 2nd Priority: IT - reason. Avoid Now: Real Estate</p>
X <p>- SIP investors: advice - Lumpsum investors: advice - Traders: advice</p>
X <p>1) Risk one 2) Risk two 3) Risk three</p>
X <h2>What is EGR?</h2>   <- FAQ must be H4, not H2
X <h3>What is EGR?</h3>   <- FAQ must be H4, not H3

CORRECT FORMAT - ALWAYS DO THIS:
OK <ul>
     <li><strong>1st Priority:</strong> FMCG - reason</li>
     <li><strong>2nd Priority:</strong> IT - reason</li>
     <li><strong>Avoid Now:</strong> Real Estate - reason</li>
   </ul>

OK <ul>
     <li><strong>SIP investors:</strong> advice</li>
     <li><strong>Lumpsum investors:</strong> advice</li>
     <li><strong>Traders:</strong> advice</li>
   </ul>

OK <ul>
     <li>Risk one</li>
     <li>Risk two</li>
     <li>Risk three</li>
   </ul>

OK <h4>What is NSE EGR and how does it work?</h4>
   <p>Answer here...</p>

=====================================
SEO HEADING HIERARCHY - FOLLOW EXACTLY
=====================================

RULE:
- H1  -> Blog title only (once at top)
- H2  -> Longtail keyword-rich GROUP heading (3-5 words, SEO focused)
- H3  -> Sub-sections under each H2 group
- H4  -> FAQ questions only

WRONG - all sections at same H2 level:
X <h2>What Happened</h2>
X <h2>Why This Matters</h2>
X <h2>Key Risks To Watch</h2>
X <h2>What is EGR?</h2>   <- FAQ as H2 is wrong

CORRECT - grouped under longtail H2, sub-sections as H3, FAQ as H4:
OK <h2>[Longtail keyword group heading]</h2>
     <h3>What Happened</h3>
     <h3>Why This Matters</h3>

OK <h2>[Longtail keyword group heading]</h2>
     <h3>What This Means For Your Portfolio</h3>
     <h3>Sectors To Watch - Priority Order</h3>
     <h3>Action Points For Investors</h3>

OK <h2>[Longtail keyword group heading]</h2>
     <h3>Key Risks To Watch</h3>

OK <h2>Frequently Asked Questions - [Topic] For Retail Investors</h2>
     <h4>FAQ question one?</h4>
     <p>Answer one</p>
     <h4>FAQ question two?</h4>
     <p>Answer two</p>

LONGTAIL H2 EXAMPLES (write your own based on the news topic):
- "How NSE EGR Impacts Your Gold Investment Strategy"
- "What Sensex Fall Means For Your Portfolio and Next Steps"
- "Key Risks of Investing in NSE Electronic Gold Receipts"
- "Frequently Asked Questions - NSE EGR For Retail Investors"

=====================================
MANDATORY BLOG STRUCTURE (Blog_Content):
=====================================

<h1>[Blog Title]</h1>

<h2>Key Takeaways - [Topic] For Investors</h2>
<ul>
  <li>[What happened - one line simple summary]</li>
  <li>[Direct impact on investor portfolio]</li>
  <li>[Top priority sector to watch]</li>
  <li>[One clear action investor should take today]</li>
</ul>

<h2>News Context and Market Impact</h2>
  <h3>What Happened</h3>
  <p>2-3 lines - simple explanation of the news</p>

  <h3>Why This Matters</h3>
  <p>Market context - why this news is important for investors</p>

<h2>Portfolio and Strategy Focus</h2>
  <h3>What This Means For Your Portfolio</h3>
  <p>MOST IMPORTANT - direct investor impact: which stocks or sectors
  are affected, should investor buy hold or wait, any risk to portfolio</p>

  <h3>Sectors To Watch - Priority Order</h3>
  <ul>
    <li><strong>1st Priority:</strong> [sector name] - [one line why]</li>
    <li><strong>2nd Priority:</strong> [sector name] - [one line why]</li>
    <li><strong>Avoid Now:</strong> [sector name] - [one line why]</li>
  </ul>

  <h3>Action Points For Investors</h3>
  <ul>
    <li><strong>SIP investors:</strong> [specific advice]</li>
    <li><strong>Lumpsum investors:</strong> [specific advice]</li>
    <li><strong>Traders:</strong> [specific advice]</li>
  </ul>

  [Swastika paragraph here - naturally blended inside a <p> tag]

<h2>Risks and Cautions</h2>
  <h3>Key Risks To Watch</h3>
  <ul>
    <li>[Risk 1]</li>
    <li>[Risk 2]</li>
    <li>[Risk 3]</li>
  </ul>

<h2>Frequently Asked Questions - [Topic] For Retail Investors</h2>
  <h4>[FAQ question 1 - investor focused]?</h4>
  <p>[Clear actionable answer]</p>

  <h4>[FAQ question 2 - investor focused]?</h4>
  <p>[Clear actionable answer]</p>

  <h4>[FAQ question 3 - investor focused]?</h4>
  <p>[Clear actionable answer]</p>

  <h4>[FAQ question 4 - investor focused]?</h4>
  <p>[Clear actionable answer]</p>

!! STOP HERE - Blog_Content ends after FAQ section !!
- DO NOT add Conclusion section inside Blog_Content
- DO NOT add CTA link or URL inside Blog_Content
- Conclusion goes ONLY in the "Conclusion" JSON field
- CTA goes ONLY in the "CTA" JSON field

=====================================

INVESTOR TONE RULES:
- Always talk directly to investor ("your portfolio", "you should", "for you")
- Every section must end with investor implication
- Give CLEAR priority - not everything is equally important
- Avoid vague statements like "markets may move" - be specific
- If bullish: say "consider buying X"
- If bearish: say "avoid or reduce exposure to X"
- Keep beginner-friendly - no complex jargon

SWASTIKA RULE:
- Include Swastika Investmart in ONLY ONE paragraph inside Blog_Content
- That paragraph must be 2-5 sentences maximum
- Naturally blended - not a separate section
- Do NOT sound like promotion or advertisement
- Do NOT use call-to-action language
- Keep it informational and relevant to topic

QUALITY RULES:
- Blog length: 600-800 words
- Use H1, H2, H3, H4 tags as per hierarchy above
- TLDR must have exactly 4 points
- Generate exactly 4 FAQs inside Blog_Content using H4
- FAQ_Schema JSON field must also have same 4 questions
- No markdown - only JSON output
- No extra text outside JSON
"""

    result = cached_model_call(prompt)
    data   = json.loads(result)
    return data



























































































































































































































# def generate_blog(item):
#     prompt = f"""
#   You are a finance blogger.
  

# STRICT RULES:
# - Do NOT copy phrases or sentences
# - Completely rewrite in your own words
# - Avoid plagiarism completely
# - Add explanation (what it means for people/investors)
# - Keep it simple and engaging
# - Make it feel like a blog, not raw news

# News:
# Title: {item['Blog_Title']}
# Content: {item['Blog_Content']}
#     """

#     response = client.chat.completions.create(
#         model=MODEL,
#         messages=[{"role": "user", "content": prompt}]
#     )

#     return response.choices[0].message.content