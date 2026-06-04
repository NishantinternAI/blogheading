import json
import re
from add_cached import cached_model_call


# ══════════════════════════════════════════════════════════════
#  POST-PROCESSORS — guaranteed fixes regardless of AI output
# ══════════════════════════════════════════════════════════════

def fix_em_dash(text: str) -> str:
    text = text.replace('\u2014', '\u2013')
    text = text.replace('&mdash;', '\u2013')
    text = text.replace('&#8212;', '\u2013')
    return text


def fix_tldr_h2(html: str) -> str:
    html = re.sub(r'<h2[^>]*>\s*TLDR\s*</h2>', '', html, flags=re.IGNORECASE)
    return html


def fix_faq_tags(html: str) -> str:
    faq_pattern = re.compile(
        r'(<h2[^>]*>.*?(?:frequently asked questions|faq).*?</h2>)',
        re.IGNORECASE | re.DOTALL
    )
    match = faq_pattern.search(html)
    if not match:
        return html
    before_faq  = html[:match.end()]
    faq_section = html[match.end():]
    faq_section = re.sub(r'<h3([^>]*)>', r'<h4\1>', faq_section)
    faq_section = re.sub(r'</h3>', '</h4>', faq_section)
    return before_faq + faq_section


def fix_faq_h2_keyword(html: str, blog_title: str) -> str:
    STOP = {
        'should','you','buy','sell','now','is','are','was','were',
        'the','a','an','in','on','for','your','this','that','these',
        'it','how','what','why','will','can','could','would','do',
        'does','did','has','have','had','be','been','at','by',
        'from','with','or','and','but','if','so','as','not','no',
        'its','also','just','after','before','today','act','rebalance',
        'improve','check','test','watch','rise','fall','may','june',
        'july','august','september','october','november','december'
    }
    clean = re.sub(r'[\u2013\u2014\-\?!\|]', ' ', blog_title)
    words = [w for w in clean.split() if w.lower() not in STOP and len(w) > 2]
    keyword = ' '.join(words[:4]) if words else 'Finance'

    bare_faq = re.compile(
        r'(<h2[^>]*>)\s*((?:frequently asked questions|faq))\s*(</h2>)',
        re.IGNORECASE
    )
    match = bare_faq.search(html)
    if match:
        replacement = (
            f'{match.group(1)}'
            f'Frequently Asked Questions \u2013 {keyword} For Investors'
            f'{match.group(3)}'
        )
        html = html[:match.start()] + replacement + html[match.end():]
    return html


def fix_placeholder_h3(html: str) -> str:
    """
    Remove generic placeholder H3 text the AI writes
    when it cannot think of a specific heading.
    CHANGE 5+6: Added 2 new patterns + removed '...' truncation.
    """
    PLACEHOLDER_PATTERNS = [
        r'<h3[^>]*>\s*How this affects sector allocations in your portfolio\s*</h3>',
        r'<h3[^>]*>\s*Which sectors could be affected the most\s*</h3>',
        r'<h3[^>]*>\s*Which specific stocks[^<]*are affected[^<]*</h3>',
        r'<h3[^>]*>\s*HOW does this specific event affect YOUR holdings[^<]*</h3>',
        r'<h3[^>]*>\s*How does this event affect YOUR holdings[^<]*</h3>',  # ← NEW
        r'<h3[^>]*>\s*Which stocks[/]sectors are affected[^<]*</h3>',        # ← NEW
        r'<h3[^>]*>\s*WHICH specific stocks[^<]*</h3>',
        r'<h3[^>]*>\s*What caused it[^<]*deeper context[^<]*</h3>',
        r'<h3[^>]*>\s*What this means for your portfolio\s*</h3>',
        r'<h3[^>]*>\s*Why this matters for investors\s*</h3>',
        r'<h3[^>]*>\s*What happened[^<]*simple explanation[^<]*</h3>',
        r'<h3[^>]*>\s*Sectors to watch[^<]*priority order[^<]*</h3>',
    ]

    for pattern in PLACEHOLDER_PATTERNS:
        h3_match = re.search(pattern, html, re.IGNORECASE)
        if h3_match:
            after = html[h3_match.end():]

            if after.lstrip().startswith('<ul'):
                html = html[:h3_match.start()] + html[h3_match.end():]

            elif after.lstrip().startswith('<p'):
                p_match = re.match(r'\s*<p[^>]*>(.*?)</p>', after,
                                   re.IGNORECASE | re.DOTALL)
                if p_match:
                    p_text = re.sub(r'<[^>]+>', '', p_match.group(1))
                    words  = p_text.split()[:10]
                    text   = ' '.join(words)
                    # CHANGE 5: no "..." truncation — clean heading only
                    if len(text) > 65:
                        text = text[:62]
                    new_h3 = '<h3>' + text + '</h3>'
                    html = html[:h3_match.start()] + new_h3 + html[h3_match.end():]
                else:
                    html = html[:h3_match.start()] + html[h3_match.end():]
            else:
                html = html[:h3_match.start()] + html[h3_match.end():]

    return html


# def fix_duplicate_links(html: str) -> str:
#     links_pattern = re.compile(
#         r'<p>\s*<strong>Also read:</strong>.*?</p>',
#         re.IGNORECASE | re.DOTALL
#     )
#     matches = list(links_pattern.finditer(html))
#     if len(matches) > 1:
#         for match in reversed(matches[:-1]):
#             html = html[:match.start()] + html[match.end():]
#     return html


# def fix_links_before_faq(html: str) -> str:
#     """Move internal links block immediately before FAQ section."""
#     links_pattern = re.compile(
#         r'<p>\s*<strong>Also read:</strong>.*?</p>',
#         re.IGNORECASE | re.DOTALL
#     )
#     match = links_pattern.search(html)
#     if not match:
#         return html

#     links_block = match.group(0)
#     html = html[:match.start()] + html[match.end():]

#     faq_pattern = re.compile(
#         r'<h2[^>]*>.*?(?:frequently asked questions|faq).*?</h2>',
#         re.IGNORECASE | re.DOTALL
#     )
#     faq_match = faq_pattern.search(html)
#     if not faq_match:
#         return html + '\n' + links_block

#     insert_pos = faq_match.start()
#     html = html[:insert_pos] + links_block + '\n' + html[insert_pos:]
#     return html


def fix_duplicate_swastika(html: str) -> str:
    swastika_pattern = re.compile(
        r'<p>[^<]*Swastika Investmart[^<]*(?:<[^/][^>]*>[^<]*</[^>]+>[^<]*)*</p>',
        re.IGNORECASE | re.DOTALL
    )
    matches = list(swastika_pattern.finditer(html))
    if len(matches) > 1:
        for match in reversed(matches[1:]):
            html = html[:match.start()] + html[match.end():]
    return html


def fix_table_na(html: str) -> str:
    html = re.sub(
        r'<td>\s*(?:N/A|n/a|NA|na|None|-|--)\s*</td>',
        '<td>To be announced</td>', html
    )
    html = re.sub(r'<td>\s*</td>', '<td>To be announced</td>', html)
    return html


def fix_remove_non_ipo_table(html: str, source: str) -> str:
    if source == "nse_ipo":
        return html
    html = re.sub(r'<table.*?</table>', '', html,
                  flags=re.IGNORECASE | re.DOTALL)
    return html


def fix_extra_ipo_h2(html: str, source: str) -> str:
    if source != "nse_ipo":
        return html
    ALLOWED = [
        r'key details', r'gmp', r'should you apply',
        r'risks of investing', r'frequently asked questions', r'faq',
    ]
    h2_pattern = re.compile(r'<h2[^>]*>(.*?)</h2>', re.IGNORECASE | re.DOTALL)
    for match in reversed(list(h2_pattern.finditer(html))):
        h2_text = re.sub(r'<[^>]+>', '', match.group(1)).lower()
        if not any(re.search(p, h2_text) for p in ALLOWED):
            html = html[:match.start()] + html[match.end():]
    return html


def fix_garbage_characters(text: str) -> str:
    cleaned = ''
    for char in text:
        code = ord(char)
        if (code < 128 or char in '\u20b9\u2013\u2014\xb0\u201c\u201d\u2018\u2019\u2026'):
            cleaned += char
        else:
            cleaned += ' '
    cleaned = re.sub(r'  +', ' ', cleaned)
    return cleaned


def fix_all_fields(data: dict, source: str = "") -> dict:
    blog_title = data.get('Blog_Title', '')
    for key, value in data.items():
        if isinstance(value, str):
            value = fix_em_dash(value)
            if key in ('Blog_Title', 'Meta_Title', 'Meta_Description', 'Conclusion'):
                value = fix_garbage_characters(value)
            if key == 'Blog_Content':
                value = fix_tldr_h2(value)
                value = fix_faq_tags(value)
                value = fix_faq_h2_keyword(value, blog_title)
                value = fix_placeholder_h3(value)
                # value = fix_duplicate_links(value)
                # value = fix_links_before_faq(value)
                value = fix_duplicate_swastika(value)
                value = fix_table_na(value)
                value = fix_remove_non_ipo_table(value, source)
                value = fix_extra_ipo_h2(value, source)
            data[key] = value
        elif isinstance(value, list):
            data[key] = [
                fix_em_dash(fix_garbage_characters(v)) if isinstance(v, str) else v
                for v in value
            ]
        elif isinstance(value, dict):
            data[key] = fix_all_fields(value, source)
    return data


# ══════════════════════════════════════════════════════════════
#  MAIN FUNCTION
# ══════════════════════════════════════════════════════════════

def generate_blog(item):
    prompt = f"""
You are a senior financial analyst and blog writer for Swastika Investmart,
writing for RETAIL INVESTORS in India.

NEWS:
Title: {item['Blog_Title']}
Content: {item['Blog_Content']}

Return ONLY valid JSON in this format:

{{
  "Meta_Title": "SEO title 50-60 chars strictly - keyword first - number + you + question",
  "Meta_Description": "Under 160 chars with keyword + action",
  "TLDR": [
    "Complete sentence - what happened - with specific number/date. No labels.",
    "Complete sentence - direct effect on investor money - specific sector named.",
    "Complete sentence - which specific sector or stock to watch and why.",
    "Complete sentence - one clear action investor takes today - not generic."
  ],
  "Blog_Title": "50-70 chars - keyword first - number + you/your + question mark",
  "Blog_Content": "HTML blog as per structure below",
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
  "Conclusion": "2-3 sentence investor-focused summary with clear next step",
  "CTA": "https://trade.swastika.co.in/"
}}


=====================================
!! STEP 1 — DETECT ARTICLE TYPE FIRST !!
=====================================

TYPE A — IPO article
  signals: "ipo", "lot size", "allotment", "price band",
           "subscribed", "prosp", "rhp", "listing date"

TYPE B — Gold / Silver article
  signals: "gold", "silver", "bullion", "mcx", "precious metal"

TYPE C — Stock / Company article
  signals: company name + "shares", "stock", "results",
           "profit", "revenue", "target", "dividend"

TYPE D — RBI / Interest Rate article
  signals: "rbi", "repo rate", "monetary policy",
           "interest rate", "inflation", "cpi"

TYPE E — Market / Index article
  signals: "sensex", "nifty", "market", "rally",
           "crash", "bulls", "bears", "points"

TYPE F — General Finance (if none above match)


=====================================
!! STEP 2 — TITLE RULES !!
=====================================

Every Blog_Title and Meta_Title MUST contain ALL 3 elements
inside ONE single natural flowing sentence:
  1. ONE NUMERIC VALUE  (₹ amount, %, crore, points, or date)
  2. ONE PERSONA WORD   (You, Your, Are You, Should You)
  3. ONE QUESTION MARK  (must end the title)

LENGTH — STRICT SEO BOUNDARIES:
  Meta_Title : 50 to 60 characters STRICTLY (shown on Google)
  Blog_Title : 50 to 70 characters MAXIMUM  (shown on website)
  Every space, letter, punctuation = 1 character.
  Under 50 = too weak for SEO.
  Over 60 chars on Meta_Title = Google truncates with "..."

CRITICAL GRAMMAR RULE:
  All 3 elements must form ONE single flowing thought.
  Never split into two ideas using colon (:) or em-dash.
  The number, persona word, and question must interact
  naturally within the same phrase — not as separate fragments.

NUMERIC NOUN CONSTRAINT:
  Every number must be immediately followed by a descriptive noun.
  ✅ "5 reasons"  ✅ "3 stocks"  ✅ "7 risks"  ✅ "₹500 crore"
  ❌ "5 You"      ❌ "3 Investors"              ❌ "7 Should"

SINGLE NUMBER RULE:
  Use only ONE numeric value per title.
  Two numbers = two competing hooks = confused reader.
  ❌ "₹576 Cr Revenue Signpost India Expands to 100 Cities — Are You Ready?"
  ✅ "Signpost India Posts ₹576 Cr Revenue — Should You Invest Now?"
  Pick the number that matters most to the investor. Drop the rest.

NATURAL LANGUAGE TEST:
  Read the title aloud as if speaking to a friend.
  Ask: would a human financial journalist write this sentence?

  FAIL signals — if ANY appear, rebuild the title completely:
  ❌ Title sounds like 3 separate fragments joined together
  ❌ "Are You Ready?" or "Should You Know?" floats disconnected
     from the rest of the sentence
  ❌ Two numbers appear competing for attention
  ❌ No verb appears in the first half of the title
  ❌ Title starts with ₹ or number instead of brand/keyword
  ❌ Colon or em-dash splitting two different ideas
  ❌ "You" appears twice in the same title
  ❌ Title ends with ", You?" or "Today, You?" as a tag-on

WRONG EXAMPLES — never produce these patterns:
  ❌ "5 You Should Consider: Is Groww AMC set for a governance upgrade?"
     (number has no noun, colon splits two ideas)
  ❌ "23,000 Level: Should You Brace for Nifty's Next Support Breach?"
     (colon splits, "support breach" is jargon, number has no noun)
  ❌ "₹576 crore revenue Signpost India to 100 cities Are You Ready?"
     (two numbers, no verb, "Are You Ready" disconnected)
  ❌ "3 Things to Know: Will Nifty Fall Below 23,000?"
     (colon splits two ideas)

RIGHT EXAMPLES — Meta_Title (50-60 chars):
  ✅ "Should You Buy Groww AMC Before Its ₹2,000 Cr IPO?"  (52 chars)
  ✅ "Is Your Portfolio Safe After Sensex Falls 800 Pts?"    (51 chars)
  ✅ "Does RBI Rate Cut Lower Your Home Loan EMI Today?"     (50 chars)
  ✅ "Suzlon Shares Fall 8% — Should You Exit or Hold?"      (50 chars)
  ✅ "Is Signpost India's ₹576 Cr Growth a Buy Signal?"     (50 chars)
  ✅ "Nifty at 23,000 — Is It Time to Protect Your Money?"  (52 chars)

RIGHT EXAMPLES — Blog_Title (50-70 chars):
  ✅ "Is a ₹2,000 Crore Groww AMC Listing Worth Your Money?"      (54 chars)
  ✅ "5 Reasons Groww AMC's New Management Could Grow Your Returns" (61 chars)
  ✅ "Will the 500 Point Nifty Drop Damage Your Portfolio Today?"   (58 chars)
  ✅ "Does RBI Rate Cut Mean Your Monthly Home Loan EMI Falls?"     (56 chars)
  ✅ "Signpost India Posts ₹576 Cr Revenue — Should You Invest?"    (58 chars)
  ✅ "Is Nifty's Fall to 23,000 Points a Risk for Your Portfolio?"  (60 chars)

RIGHT EXAMPLES BY ARTICLE TYPE:

  TYPE A — IPO:
    Meta: "Should You Apply for Groww AMC IPO at ₹450 Price Band?"  (55 chars)
    Blog: "Is Groww AMC's ₹2,000 Cr IPO Worth Your Hard Earned Money?" (59 chars)

  TYPE B — Gold/Silver:
    Meta: "Gold Rises 2% This Week — Should You Buy More Now?"      (51 chars)
    Blog: "Is MCX Gold at ₹72,000 Still a Good Buy for Your Portfolio?" (60 chars)

  TYPE C — Stock/Company:
    Meta: "Suzlon Shares Fall 8% — Should You Exit or Hold Now?"    (53 chars)
    Blog: "Colgate Declares ₹24 Dividend — Is It Worth Buying Now?"  (55 chars)
    Dividend specific:
    Meta: "Nelco Declares ₹1 Dividend — Should You Buy or Hold?"   (53 chars)
    Blog: "Is Nelco's ₹1 Dividend Worth Buying Before the Ex-Date?"  (55 chars)

  TYPE D — RBI/Rates:
    Meta: "Does RBI Rate Cut Lower Your Home Loan EMI Today?"       (50 chars)
    Blog: "RBI Cuts Repo Rate 0.25% — Will Your FD Returns Drop Now?" (57 chars)

  TYPE E — Market/Index:
    Meta: "Sensex Falls 800 Points — Is Your Portfolio Safe Now?"   (53 chars)
    Blog: "Nifty Drops 500 Points — Should You Buy the Dip Today?"   (55 chars)

BANNED WORDS IN TITLE — replace instantly with plain English:
  Ex-Date          → Buy Before [date]
  PAT / Net Profit → Profit / Net Earnings
  YoY / QoQ        → vs Last Year / vs Last Quarter
  Basis Points/bps → % / Interest Rate Change
  Volatile         → Up and Down
  Correction       → Market Fall
  Geopolitical     → War / Global Tensions
  Macroeconomic    → Economy / Market Conditions
  Governance       → Fund Management / Board Control
  AUM              → Total Fund Size
  Corporate Action → Dividend / Bonus / Stock Split
  Valuation        → Stock Price / What You Pay
  Support Breach   → Falls Below [level]
  Brace            → Prepare / Watch Out / Be Careful

DASH RULE CLARIFICATION:
  Em-dash and colon → BANNED inside Blog_Title and Meta_Title
  En-dash (-)       → ALLOWED inside H2/H3 headings and body text

TITLE SAFETY CHECKLIST — run before every title output:
  □ Meta_Title strictly between 50 and 60 characters?
  □ Blog_Title between 50 and 70 characters?
  □ Title reads naturally aloud as ONE single flowing thought?
  □ Numeric value has a meaningful noun immediately after it?
  □ Only ONE number used in the entire title?
  □ No colon or em-dash separating two different ideas?
  □ Core brand or keyword appears within first 4 words?
  □ All banned words replaced with plain English?
  □ No verb missing from first half of title?
  □ Does "You" or "Your" appear MORE than once? YES → remove the extra one
  □ Does the title end with ", You?" or "for You?" disconnected? YES → rewrite
  If ANY box fails → scrap and rebuild title completely from scratch.
  Never patch a broken title — always rebuild.


=====================================
!! STEP 3 — HEADING HIERARCHY RULES !!
=====================================

CRITICAL: Google's NLP reads H1 to understand the page topic.
Once H1 defines the subject, H2 and H3 do NOT need to repeat
the company name or keyword every time.
Keyword stuffing in headings = over-optimisation penalty.

RULE:
  H1 → full keyword (company + event + question)
  H2 → natural, readable section headings
       May include keyword ONCE or TWICE maximum
       Should not repeat keyword in every H2
  H3 → specific sub-topics, natural language

WRONG — keyword repeated in every heading:
  <h1>Suzlon Energy Shares Slump After SEBI Fines Rs 29 Crore</h1>
  <h2>Key Takeaways-Suzlon Energy Shares Slump</h2>     ← repeat
  <h2>Suzlon Energy Shares Today - Key Data</h2>        ← repeat
  <h2>Suzlon Energy Shares Impact on Your Money</h2>    ← repeat
  <h2>Suzlon Energy Shares - Key Risks</h2>             ← repeat
  <h2>FAQ-Suzlon Energy Shares Slump For Investors</h2> ← repeat

RIGHT — H1 sets topic, H2/H3 flow naturally:
  <h1>Suzlon Energy Shares Slump After SEBI Fines Rs 29 Crore - Should You Exit?</h1>
  <h2>Key Takeaways from the SEBI Order</h2>
  <h2>Understanding the Rs 29 Crore Penalty</h2>
    <h3>Why the Stock is Falling Today</h3>
    <h3>SEBI Findings - Inflated Profits and Subsidiary Transactions</h3>
  <h2>Impact on Investors - What Should You Do?</h2>
    <h3>How This Affects Your Portfolio</h3>
    <h3>Which Sectors Face Spillovers?</h3>
    <h3>What SIP, Lumpsum and Traders Should Do Now</h3>
  <h2>Key Risks of Holding or Buying the Stock</h2>
  <h2>Frequently Asked Questions</h2>

H2 STRUCTURE BY ARTICLE TYPE (natural language, not keyword-stuffed):

TYPE A — IPO (consistent - investors ask same questions every time):
  <h2>[Company] IPO - Key Details and Dates</h2>
  <h2>[Company] IPO GMP and Market Sentiment</h2>
  <h2>Should You Apply For [Company] IPO?</h2>
  <h2>Risks of Investing in [Company] IPO</h2>

TYPE B — Gold/Silver:
  <h2>Gold Price Today - Key Data</h2>
  <h2>Impact on Your Portfolio</h2>
  <h2>Key Risks for Investors</h2>

TYPE C — Stock/Company:
  <h2>[Company] Share Price - Key Data</h2>
  <h2>What This Means for Investors</h2>
  <h2>Key Risks of Holding or Buying</h2>

TYPE D — RBI/Rates:
  <h2>RBI Decision - What Changed</h2>
  <h2>Impact on Your Money</h2>
  <h2>Key Risks After This Decision</h2>

TYPE E — Market/Index:
  <h2>Market Overview - Key Data</h2>
  <h2>Impact on Your Portfolio</h2>
  <h2>Key Risks to Watch</h2>


=====================================
!! STEP 4 — SEMANTIC KEYWORD RULES !!
=====================================

Modern Google uses NLP — it understands topic from context.
Do NOT repeat the exact same keyword phrase over and over.
Use SEMANTIC VARIATIONS (LSI keywords) throughout the article.

For a STOCK article about Suzlon + SEBI penalty:
  Primary keyword: "Suzlon Energy shares"
  Use these variations instead of repeating primary:
    "SUZLON stock" (NSE ticker — major SEO entity)
    "Suzlon regulatory risk"
    "wind energy stock governance"
    "SEBI penalty on renewable company"
    "Suzlon corporate governance"
    "renewable energy mid-cap"
    "wind energy sector India"

  Rule: use primary keyword 2-3 times maximum.
  Fill rest of article with semantic variations.

For a GOLD article:
  Primary: "gold price India"
  Variations: "MCX gold", "gold ETF", "gold futures",
              "precious metal rally", "yellow metal", "bullion"

For an IPO article:
  Primary: "[Company] IPO"
  Variations: "[Company] SME listing", "BSE SME IPO",
              "[Company] subscription", "[Company] GMP",
              "grey market premium [Company]"

For RBI article:
  Primary: "RBI rate cut"
  Variations: "repo rate decision", "monetary policy",
              "home loan EMI", "RBI MPC", "interest rate India"


=====================================
!! STEP 5 — H3 DYNAMIC RULE !!
=====================================

H3 must be specific to this article — no placeholders.
Only ONE H3 stays consistent:
  "What SIP, Lumpsum and Traders Should Do Now"

ALL OTHER H3 must contain real details.

BANNED GENERIC H3:
  X <h3>How does this event affect YOUR holdings?</h3>
  X <h3>Which stocks/sectors are affected?</h3>
  X <h3>What This Means For Your Portfolio</h3>
  X <h3>Sectors To Watch - Priority Order</h3>
  X <h3>What Happened - Simple Explanation</h3>

RIGHT — specific with company/event/number:
  OK <h3>Why Suzlon Shares Fell After Rs 29 Crore SEBI Fine</h3>
  OK <h3>How SEBI Penalty Affects Renewable Energy Stocks</h3>
  OK <h3>Why Gold Fell 1% - US-Iran Tensions Explained</h3>


=====================================
!! STEP 6 — DATA TABLE !!
=====================================

ONLY TYPE A IPO articles get a data table.
ALL OTHER types — NO table anywhere.

IPO table format (after first H2 only):
  <table>
    <thead><tr><th>Detail</th><th>Information</th></tr></thead>
    <tbody>
      <tr><td>IPO Open Date</td>      <td>[date or To be announced]</td></tr>
      <tr><td>IPO Close Date</td>     <td>[date or To be announced]</td></tr>
      <tr><td>Price / Price Band</td> <td>[₹X or To be announced]</td></tr>
      <tr><td>Lot Size</td>           <td>[N shares or To be announced]</td></tr>
      <tr><td>Minimum Investment</td> <td>[₹amount or To be announced]</td></tr>
      <tr><td>Issue Size</td>         <td>[₹X Crore or To be announced]</td></tr>
      <tr><td>Listing Exchange</td>   <td>[BSE SME / NSE / BSE]</td></tr>
      <tr><td>Listing Date</td>       <td>[date or To be announced]</td></tr>
    </tbody>
  </table>
  Never write N/A. Table appears once only.


=====================================
!! TLDR RULES — READ BEFORE WRITING !!
=====================================

TLDR = 4 bullet points. Each bullet MUST be:
  1. A COMPLETE SENTENCE - not a label or template fragment
  2. SPECIFIC - contains real company name, number, date, or action
  3. USEFUL - investor can act on it or understand it immediately
  4. NATURAL - reads like a human financial analyst wrote it

RULES:
  Each bullet has the keyword naturally — NOT forced at the start.
  No dashes used as label separators (keyword - label - context).
  No template words: "what happened", "portfolio effects", "sector", "action".
  No repeating the full company name in every bullet.
  No generic statements: "market may be volatile", "watch the sector".

WRONG — template labels visible, keyword stuffed, dashes as separators:
  ❌ "RBI rate cut - June 5 policy decision - what happened"
  ❌ "RBI rate cut impact - yields, loan costs - portfolio effects"
  ❌ "RBI rate cut sector - banks and financials to watch"
  ❌ "RBI rate cut action - review EMIs and rebalance today"

WRONG — company name repeated in every bullet:
  ❌ "Colgate Palmolive (India) shares - interim Rs 24 dividend"
  ❌ "Colgate Palmolive (India) shares - near-term returns may improve"
  ❌ "Colgate Palmolive (India) shares - watch FMCG sector"
  ❌ "Colgate Palmolive (India) shares - action: Hold now"

RIGHT — complete sentences, specific, natural, keyword once or twice:
  RBI article:
  ✅ "RBI cuts repo rate by 25 basis points to 6% on June 5, 2026"
  ✅ "Home loan EMIs may drop Rs 500-800 per month if banks pass on the cut"
  ✅ "Bank stocks and housing finance companies stand to benefit most"
  ✅ "Lock your FD rates today before banks reduce deposit rates"

  Colgate dividend:
  ✅ "Colgate India announces Rs 24 interim dividend with record date June 1, 2026"
  ✅ "Buying before the ex-date qualifies you for the payout but price adjusts after"
  ✅ "FMCG and consumer staples sector may see mild movement around record date"
  ✅ "Hold if you already own it - avoid buying purely for the dividend"

  IPO article:
  ✅ "Aureate Tradde IPO opens May 29 at Rs 70 per share on BSE SME"
  ✅ "No GMP data yet makes listing gains uncertain for retail investors"
  ✅ "Watch subscription demand and GMP signals closely before applying"
  ✅ "Apply only with a small allocation if your risk tolerance allows SME exposure"

  Sensex fall:
  ✅ "Sensex fell 500 points today on FPI outflows and global risk-off mood"
  ✅ "Equity portfolios may see 1-2% drawdown with financials and IT hit hardest"
  ✅ "Defensive sectors like FMCG and pharma could hold better than cyclicals"
  ✅ "SIP investors should stay invested - avoid stopping SIPs on market dips"

SELF CHECK before writing TLDR:
  Does each bullet read like a sentence a financial analyst would say? YES/NO
  Does any bullet contain a template label like "what happened"? If YES → rewrite
  Does any bullet repeat the full company name 4 times? If YES → use variation
  Is each bullet specific with a number, date, or named action? YES/NO


=====================================
MANDATORY BLOG STRUCTURE (Blog_Content):
=====================================


<h1>[Title - number + you + ?]</h1>

<h2>[Natural section heading - key details]</h2>
[IPO ONLY: data table here]
<h3>[SPECIFIC: WHY + company/number/event]</h3>
<p>[2-3 lines. First sentence has main keyword.]</p>
<h3>[SPECIFIC: deeper context with real details]</h3>
<p>[market context specific to this article]</p>

<h2>[Natural section heading - impact on investors]</h2>
<h3>[SPECIFIC: HOW this affects specific holdings]</h3>
<p>[direct investor impact]</p>
<h3>[SPECIFIC: WHICH sectors/stocks by name]</h3>
<ul>
  <li><strong>1st Priority:</strong> [sector] - [reason]</li>
  <li><strong>2nd Priority:</strong> [sector] - [reason]</li>
  <li><strong>Avoid Now:</strong> [sector] - [reason]</li>
</ul>
<h3>What SIP, Lumpsum and Traders Should Do Now</h3>
<ul>
  <li><strong>SIP investors:</strong> [advice]</li>
  <li><strong>Lumpsum investors:</strong> [advice]</li>
  <li><strong>Traders:</strong> [advice]</li>
</ul>

!! SWASTIKA PARAGRAPH GOES HERE — READ RULES BELOW !!
<p>[Swastika Investmart view on THIS specific article]</p>

<h2>[Natural section heading - key risks]</h2>
!! ONE h3 + ONE ul only. No extra sections. !!
<ul>
  <li>[Risk 1]</li>
  <li>[Risk 2]</li>
  <li>[Risk 3]</li>
</ul>

<h2>Frequently Asked Questions</h2>
<h4>[Q1]?</h4><p>[A1]</p>
<h4>[Q2]?</h4><p>[A2]</p>
<h4>[Q3]?</h4><p>[A3]</p>
<h4>[Q4]?</h4><p>[A4]</p>

!! STOP — no Conclusion or CTA inside Blog_Content !!



=====================================
HTML FORMATTING RULES
=====================================

1. Lists use <ul><li> - never plain dashes or 1) 2) 3)
2. FAQ questions use <h4> - never <h3>
3. NEVER <h2>TLDR</h2> or <h2>Conclusion</h2> inside Blog_Content
4. NEVER use em dash  use en dash - only
5. English only - no foreign characters
6. No CTA URL inside Blog_Content
7. Keyword in H1 is enough - do NOT repeat in every H2
8. Use semantic keyword variations in body text
9. NO internal links anywhere - no <a href> tags in Blog_Content


=====================================
SWASTIKA PARAGRAPH — STRICT RULES
=====================================

POSITION  : After SIP/Lumpsum list, before the next <h2>
TAG       : Plain <p> only — never <h1> <h2> <h3> <h4>
LENGTH    : 2 to 3 sentences maximum
APPEARS   : EXACTLY ONCE in the entire Blog_Content
LABEL     : Never write "Swastika paragraph:" before the text
START     : Always begin with "Swastika Investmart..."

TONE RULE — MOST IMPORTANT:
  This paragraph must read like EXPERT ADVICE from a trusted
  financial partner — NOT like a product advertisement.

  The reader must feel: "These experts understand my situation"
  NOT feel: "They are trying to sell me something"

  FORBIDDEN ADVERTISING PATTERNS:
  ❌ Never list services like a menu
     ("We offer stocks, F&O, MCX, MF, ETF, Bonds, IPO...")
  ❌ Never use promotional CTAs inside the paragraph
     ("Open your account today", "Start investing now")
  ❌ Never mention service names without a contextual reason
     ("Use our F&O desk" with no connection to the article)
  ❌ Never sound like a banner ad or marketing copy

  CORRECT EXPERT ADVICE PATTERNS:
  ✅ Mention ONE relevant service as a natural solution
     to the specific problem raised in this article
  ✅ The service mention must follow logically from the news
  ✅ Advice first — service reference second
  ✅ The investor should feel guided, not sold to

HOW TO WRITE IT — 5 STEP PROCESS:

  Step 1 — Extract PRIMARY FACT from the article
    (company name, event, specific number, date)

  Step 2 — Extract PRIMARY RISK or OPPORTUNITY for investor
    (what should they be worried about or excited about?)

  Step 3 — Identify ONE Swastika service that naturally
    helps with THIS specific situation:

    Article about IPO          → IPO / Research
    Article about gold/MCX     → MCX Trading / Gold ETF
    Article about stock fall   → F&O hedge / Research / SLBM
    Article about dividend     → Stocks / Investment Trading
    Article about RBI rates    → Bonds / MF / ETF
    Article about market fall  → F&O / AI assistance / Research
    Article about market rally → Stocks / MF / Investment Trading
    Article about FX/Rupee     → MCX / F&O hedge / Research

  Step 4 — Write advice sentence first using extracted facts
  Step 5 — Add ONE natural service reference as the solution

DYNAMIC PARAGRAPH EXAMPLES BY ARTICLE TYPE:

  TYPE A — IPO (Aureate Tradde IPO, ₹70 price band):
    ❌ "Swastika Investmart offers IPO applications and research."
    ✅ <p>Swastika Investmart's research desk notes that the
       Aureate Tradde IPO's lack of GMP data makes listing
       gains uncertain — apply only with a small SME allocation
       if your risk profile allows, and track subscription
       figures on day 2 and 3 before committing further capital
       through our IPO platform.</p>

  TYPE B — Gold (MCX gold at ₹72,000):
    ❌ "Swastika Investmart offers MCX Trading and Gold ETF."
    ✅ <p>Swastika Investmart notes that MCX gold's rally above
       ₹72,000 is driven by US-Iran tensions rather than domestic
       demand — MCX traders should use defined stop-losses near
       ₹71,200 and gold ETF investors can hold existing positions
       while avoiding fresh lumpsum buys at these elevated levels.</p>

  TYPE C — Stock fall (Suzlon after SEBI fine):
    ❌ "Swastika Investmart offers stocks and F&O trading."
    ✅ <p>Swastika Investmart's equity research desk flags that
       the Rs 29 crore SEBI penalty on Suzlon introduces
       regulatory overhang that typically pressures mid-cap
       renewable stocks for 2 to 4 weeks — existing holders
       can use F&O protective puts to hedge downside while
       waiting for management's official response.</p>

  TYPE C — Dividend (Reliance ₹6 dividend):
    ❌ "Swastika Investmart offers investment trading and stocks."
    ✅ <p>Swastika Investmart believes the ₹6 per share Reliance
       dividend is a sign of balance-sheet strength but not a
       buying trigger on its own — investors already holding
       RIL through our investment platform should stay put,
       while new buyers should wait for the post-ex-date price
       adjustment before entering at better levels.</p>

  TYPE D — RBI rates (repo rate cut to 6%):
    ❌ "Swastika Investmart offers bonds, MF and ETF products."
    ✅ <p>Swastika Investmart advises that RBI's 6% repo rate
       creates a narrow window to lock into higher-yield bonds
       and long-duration debt funds before banks reduce deposit
       rates — investors on our platform can explore bond and
       debt MF options that benefit from falling rate cycles
       before this window closes in the next 4 to 6 weeks.</p>

  TYPE E — Market fall (Sensex 500 points, FPI outflows):
    ❌ "Swastika Investmart offers F&O and AI assistance."
    ✅ <p>Swastika Investmart notes that the 500-point Sensex
       fall driven by ₹7.3 lakh crore in FPI outflows signals
       a risk-off phase that typically lasts 2 to 3 weeks —
       index traders can use Nifty F&O hedges to protect
       existing positions while our AI tools track FPI flow
       data and key support levels for the next confirmed
       re-entry signal.</p>

  TYPE E — Market rally:
    ✅ <p>Swastika Investmart believes the Sensex recovery above
       74,000 points is supported by improving FPI inflows but
       warrants caution on momentum chasing — SIP investors
       on our platform should maintain their allocation and
       avoid switching to sectoral funds until the rally shows
       3 consecutive sessions of FPI buying confirmation.</p>

SWASTIKA PARAGRAPH SELF CHECK:
  □ Does it read like expert advice not a sales pitch?
  □ Does it mention ONE specific fact from the article?
     (number, company, event, date)
  □ Does it reference ONE relevant service naturally?
     (not a list of all services)
  □ Does it start with "Swastika Investmart..."?
  □ Is it inside a plain <p> tag only?
  □ Does it appear exactly once?
  □ Is the service mention a logical solution to the article problem?
     (not a random product mention)
  □ Would a reader feel advised rather than advertised to?
  If ANY box fails → rewrite using the 5-step process above.

=====================================
ANTI-DUPLICATION RULES
=====================================

1. Sector priority list — EXACTLY ONCE
3. SIP/Lumpsum section — EXACTLY ONCE
4. Risk section — EXACTLY ONCE
5. Table — IPO articles only


=====================================
QUALITY RULES
=====================================

- Blog length: 900-1200 words
- Blog_Title: 50 to 70 characters
- Meta_Title: 50 to 60 characters strictly
- TLDR: exactly 4 complete sentences
- FAQ: exactly 4 h4 questions
- FAQ_Schema: same 4 questions as FAQ
- Primary keyword: 2-3 times maximum in body text
- Semantic variations: fill rest of article
- No markdown — JSON only
- No text outside JSON
- NEVER em dash — ALWAYS en dash
- English only throughout


=====================================
!! FINAL SELF-CHECK BEFORE OUTPUT !!
=====================================

CHECK 0 — Title quality (run first):
  □ Blog_Title between 50-70 chars? NO → rewrite
  □ Meta_Title between 50-60 chars? NO → rewrite
  □ Title reads as ONE complete natural sentence aloud? NO → rewrite
  □ Number has a noun after it? NO → rewrite
  □ Only ONE number in the title? NO → remove the weaker one
  □ No colon or em-dash splitting two ideas? NO → rewrite
  □ Keyword or brand name in first 4 words? NO → rewrite
  □ All banned jargon words removed? NO → replace
  □ No fail signals from Natural Language Test? NO → rebuild

CHECK 1 — Heading repetition:
  Count how many H2s contain the main company name.
  More than 2 ? → rewrite them to be natural, topic-relevant.

CHECK 2 — Keyword density:
  Count how many times the exact primary phrase appears.
  More than 2? → replace some with semantic variations.

CHECK 3 — TLDR has no H2 above it.

CHECK 4 — FAQ uses h4 not h3.

CHECK 5 — No placeholder H3 text.

CHECK 6 — Risk section has only one h3 + one ul.

CHECK 7 — No repeated Swastika, SIP, or sector priority sections.

CHECK 8 — Table only if IPO article.

CHECK 9 — Swastika paragraph format:
  Is it wrapped in a heading tag? YES → move to plain <p> only
  Does it start with "Swastika paragraph:" label? YES → remove label
  Does it appear exactly once in H2-2 section? NO → fix placement

"""

    result = cached_model_call(prompt)
    data   = json.loads(result)

    source = item.get("source", "")
    data   = fix_all_fields(data, source=source)

    return data

# import json
# import re
# from add_cached import cached_model_call


# # ══════════════════════════════════════════════════════════════
# #  POST-PROCESSORS — fix AI output regardless of prompt
# # ══════════════════════════════════════════════════════════════

# def fix_em_dash(text: str) -> str:
#     text = text.replace('\u2014', '\u2013')
#     text = text.replace('&mdash;', '–')
#     text = text.replace('&#8212;', '–')
#     return text


# def fix_tldr_h2(html: str) -> str:
#     html = re.sub(r'<h2[^>]*>\s*TLDR\s*</h2>', '', html, flags=re.IGNORECASE)
#     return html


# def fix_faq_tags(html: str) -> str:
#     """
#     FIX 1 — Inside FAQ section: replace ALL h3 with h4.
#     Only affects FAQ section — h3 tags outside FAQ untouched.
#     """
#     faq_pattern = re.compile(
#         r'(<h2[^>]*>.*?(?:frequently asked questions|faq).*?</h2>)',
#         re.IGNORECASE | re.DOTALL
#     )
#     match = faq_pattern.search(html)
#     if not match:
#         return html
#     before_faq  = html[:match.end()]
#     faq_section = html[match.end():]
#     faq_section = re.sub(r'<h3([^>]*)>', r'<h4\1>', faq_section)
#     faq_section = re.sub(r'</h3>', '</h4>', faq_section)
#     return before_faq + faq_section
 
 
# def fix_faq_h2_keyword(html: str, blog_title: str) -> str:
#     """
#     FIX 2 — Add keyword to FAQ h2 if it has no keyword.
#     Converts:
#       <h2>Frequently Asked Questions</h2>
#     To:
#       <h2>Frequently Asked Questions – FPI Outflow For Investors</h2>
 
#     Keyword = first 3 meaningful words from Blog_Title.
#     """
#     # Words to skip when extracting keyword
#     STOP = {
#         'should','you','buy','sell','now','is','are','was','were',
#         'the','a','an','in','on','for','your','this','that','these',
#         'it','how','what','why','will','can','could','would','do',
#         'does','did','has','have','had','be','been','being','at',
#         'by','from','with','about','into','after','before','than',
#         'or','and','but','if','so','as','not','no','its','our',
#         'their','which','who','when','where','while','also','just'
#     }
 
#     # Extract keyword from blog title
#     # Remove dashes and special chars, split into words
#     clean_title = re.sub(r'[–—\-\?!\|]', ' ', blog_title)
#     title_words = clean_title.split()
#     keyword_words = [
#         w for w in title_words
#         if w.lower() not in STOP and len(w) > 2 and w.isascii()
#     ]
#     # Take first 3-4 meaningful words
#     keyword = ' '.join(keyword_words[:4]) if keyword_words else 'Finance'
 
#     # Find FAQ h2 that is bare (no extra text after FAQ/Frequently)
#     bare_faq = re.compile(
#         r'(<h2[^>]*>)\s*((?:frequently asked questions|faq))\s*(</h2>)',
#         re.IGNORECASE
#     )
#     match = bare_faq.search(html)
#     if match:
#         replacement = (
#             f'{match.group(1)}'
#             f'Frequently Asked Questions – {keyword} For Investors'
#             f'{match.group(3)}'
#         )
#         html = html[:match.start()] + replacement + html[match.end():]
 
#     return html
 
 
# def fix_placeholder_h3(html: str) -> str:
#     """
#     FIX 3 — Remove generic placeholder H3 text.
#     These exact strings are placeholder text the AI writes
#     when it cannot think of a specific heading.
 
#     Strategy: find these h3 tags and replace with the
#     paragraph text that follows as the new (more specific) heading,
#     or simply remove the h3 and let the paragraph stand.
#     """
#     PLACEHOLDER_PATTERNS = [
#         r'<h3[^>]*>\s*How this affects sector allocations in your portfolio\s*</h3>',
#         r'<h3[^>]*>\s*Which sectors could be affected the most\s*</h3>',
#         r'<h3[^>]*>\s*Which specific stocks[^<]*are affected[^<]*</h3>',
#         r'<h3[^>]*>\s*HOW does this specific event affect YOUR holdings[^<]*</h3>',
#         r'<h3[^>]*>\s*WHICH specific stocks[^<]*</h3>',
#         r'<h3[^>]*>\s*What caused it[^<]*deeper context[^<]*</h3>',
#         r'<h3[^>]*>\s*What this means for your portfolio\s*</h3>',
#         r'<h3[^>]*>\s*Why this matters for investors\s*</h3>',
#         r'<h3[^>]*>\s*What happened[^<]*simple explanation[^<]*</h3>',
#         r'<h3[^>]*>\s*Sectors to watch[^<]*priority order[^<]*</h3>',
#     ]
 
#     for pattern in PLACEHOLDER_PATTERNS:
#         # Find the placeholder h3 and the next <ul> or <p>
#         h3_match = re.search(pattern, html, re.IGNORECASE)
#         if h3_match:
#             # Look at what comes after the h3
#             after = html[h3_match.end():]
 
#             # If next tag is <ul> — the h3 is a list heading
#             # Keep the ul, remove the vague h3
#             if after.lstrip().startswith('<ul'):
#                 html = html[:h3_match.start()] + html[h3_match.end():]
 
#             # If next tag is <p> — use first 8 words of p as new h3
#             elif after.lstrip().startswith('<p'):
#                 p_match = re.match(r'\s*<p[^>]*>(.*?)</p>', after,
#                                    re.IGNORECASE | re.DOTALL)
#                 if p_match:
#                     p_text = re.sub(r'<[^>]+>', '', p_match.group(1))
#                     words  = p_text.split()[:8]
#                     new_h3 = '<h3>' + ' '.join(words) + '...</h3>'
#                     html = html[:h3_match.start()] + new_h3 + html[h3_match.end():]
#                 else:
#                     html = html[:h3_match.start()] + html[h3_match.end():]
#             else:
#                 html = html[:h3_match.start()] + html[h3_match.end():]
 
#     return html
 
 


# def fix_duplicate_links(html: str) -> str:
#     links_pattern = re.compile(
#         r'<p>\s*<strong>Also read:</strong>.*?</p>',
#         re.IGNORECASE | re.DOTALL
#     )
#     matches = list(links_pattern.finditer(html))
#     if len(matches) > 1:
#         for match in reversed(matches[:-1]):
#             html = html[:match.start()] + html[match.end():]
#     return html


# def fix_duplicate_swastika(html: str) -> str:
#     swastika_pattern = re.compile(
#         r'<p>[^<]*Swastika Investmart[^<]*(?:<[^/][^>]*>[^<]*</[^>]+>[^<]*)*</p>',
#         re.IGNORECASE | re.DOTALL
#     )
#     matches = list(swastika_pattern.finditer(html))
#     if len(matches) > 1:
#         for match in reversed(matches[1:]):
#             html = html[:match.start()] + html[match.end():]
#     return html


# def fix_table_na(html: str) -> str:
#     html = re.sub(
#         r'<td>\s*(?:N/A|n/a|NA|na|None|-|--)\s*</td>',
#         '<td>To be announced</td>',
#         html
#     )
#     html = re.sub(r'<td>\s*</td>', '<td>To be announced</td>', html)
#     return html


# def fix_remove_non_ipo_table(html: str, source: str) -> str:
#     """
#     IPO articles (source=nse_ipo) keep their table.
#     All other article types have table removed.
#     """
#     if source == "nse_ipo":
#         return html
#     html = re.sub(
#         r'<table.*?</table>',
#         '',
#         html,
#         flags=re.IGNORECASE | re.DOTALL
#     )
#     return html


# def fix_garbage_characters(text: str) -> str:
#     cleaned = ''
#     for char in text:
#         code = ord(char)
#         if (code < 128 or char in '₹–\u2013°""''…'):
#             cleaned += char
#         else:
#             cleaned += ' '
#     cleaned = re.sub(r'  +', ' ', cleaned)
#     return cleaned


# def fix_tldr_list(tldr_list: list) -> list:
#     return [fix_garbage_characters(item) for item in tldr_list]


# def fix_all_fields(data: dict, source: str = "") -> dict:
#     blog_title = data.get('Blog_Title', '')
#     for key, value in data.items():
#         if isinstance(value, str):
#             value = fix_em_dash(value)
#             if key in ('Blog_Title', 'Meta_Title', 'Meta_Description', 'Conclusion'):
#                 value = fix_garbage_characters(value)
#             if key == 'Blog_Content':
#                 value = fix_tldr_h2(value)
#                 value = fix_faq_tags(value)
#                 value = fix_faq_h2_keyword(value, blog_title)
#                 value = fix_placeholder_h3(value) 
#                 value = fix_duplicate_links(value)
#                 value = fix_duplicate_swastika(value)
#                 value = fix_table_na(value)
#                 value = fix_remove_non_ipo_table(value, source)
#             data[key] = value
#         elif isinstance(value, list):
#             fixed = []
#             for item in value:
#                 if isinstance(item, str):
#                     item = fix_em_dash(item)
#                     item = fix_garbage_characters(item)
#                 fixed.append(item)
#             data[key] = fixed
#         elif isinstance(value, dict):
#             data[key] = fix_all_fields(value, source)
#     return data


# # ══════════════════════════════════════════════════════════════
# #  MAIN FUNCTION
# # ══════════════════════════════════════════════════════════════

# def generate_blog(item):
#     prompt = f"""
# You are a financial blog writer for Swastika Investmart, writing for RETAIL INVESTORS in India.

# NEWS:
# Title: {item['Blog_Title']}
# Content: {item['Blog_Content']}

# Return ONLY valid JSON in this format:

# {{
#   "Meta_Title": "SEO friendly title under 60 characters",
#   "Meta_Description": "Short description under 160 characters",
#   "TLDR": [
#     "PRIMARY KEYWORD first — what happened — with specific number or date",
#     "PRIMARY KEYWORD impact — direct effect on investor portfolio — name the sector",
#     "PRIMARY KEYWORD sector — specific sector or stock name to watch",
#     "PRIMARY KEYWORD action — one specific action investor should take today"
#   ],
#   "Blog_Title": "Catchy investor-focused blog title",
#   "Blog_Content": "HTML blog using H1, H2, H3, H4 tags (900-1200 words) - structure below",
#   "Investor_Impact": {{
#     "primary_sector": "Most important sector affected",
#     "secondary_sector": "Second most important sector",
#     "avoid_sector": "Sector to avoid right now",
#     "action": "Buy / Hold / Wait / Avoid",
#     "reason": "One line reason for the action"
#   }},
#   "Action_Points": [
#     "Specific action investor can take TODAY",
#     "What to watch this week",
#     "Risk to keep in mind"
#   ],
#   "FAQ_Schema": {{
#     "@context": "https://schema.org",
#     "@type": "FAQPage",
#     "mainEntity": [
#       {{
#         "@type": "Question",
#         "name": "Investor focused question",
#         "acceptedAnswer": {{
#           "@type": "Answer",
#           "text": "Clear actionable answer for investor"
#         }}
#       }}
#     ]
#   }},
#   "Conclusion": "Short investor-focused summary with clear next step",
#   "CTA": "https://trade.swastika.co.in/"
# }}


# =====================================
# !! STEP 1 — DETECT ARTICLE TYPE FIRST !!
# =====================================

# Read Blog_Title and Blog_Content carefully.
# Identify which type this article is.
# This determines your H2, H3 and TABLE structure below.

# TYPE A — IPO article
#   signals: "ipo", "lot size", "allotment", "price band",
#            "subscribed", "prosp", "rhp", "listing date"

# TYPE B — Gold / Silver / Bullion article
#   signals: "gold", "silver", "bullion", "mcx", "precious metal"

# TYPE C — Stock / Company article
#   signals: company name + "shares", "stock", "results",
#            "profit", "revenue", "target", "dividend"

# TYPE D — RBI / Interest Rate article
#   signals: "rbi", "repo rate", "monetary policy",
#            "interest rate", "inflation", "cpi"

# TYPE E — Market / Index article
#   signals: "sensex", "nifty", "market", "rally",
#            "crash", "bulls", "bears", "points"

# TYPE F — General Finance (if none above match)


# =====================================
# !! MOST CRITICAL - READ BEFORE WRITING TITLE !!
# =====================================

# EVERY Blog_Title and Meta_Title MUST have ALL 3 of these.
# If ANY one is missing - title is WRONG. Rewrite it.

# MANDATORY 3:
# 1. ONE NUMBER    -> Rs amount, %, crore, points, times, date
# 2. ONE "YOU"     -> "You", "Your", "Are You", "Should You"
# 3. ONE QUESTION  -> ends with "?" OR ends with clear benefit

# SELF CHECK BEFORE WRITING:
# Ask: Does my title have a number? YES/NO
# Ask: Does my title have "You" or "Your"? YES/NO
# Ask: Does my title end with question or benefit? YES/NO
# -> All 3 must be YES. If any NO -> rewrite.

# THESE TITLES ARE WRONG - missing mandatory 3:
# X "Sugar Stocks Slide After Centre Tightens Export Rules"
#    Missing: number, "you", question

# THESE ARE CORRECT - have all mandatory 3:
# OK "Sugar Stocks Fall 5% on Export Rules - Should You Sell Now?"
#    Has: 5% (number), "You" (personal), "?" (question)

# OK "Block Deals Surge Today - Which Stocks Should You Watch Now?"
#    Has: "Today" (time ref), "You" (personal), "?" (question)


# =====================================
# BANNED WORDS - NEVER USE IN TITLE OR META
# =====================================

# BANNED            -> REPLACE WITH
# Ex-Date           -> Last Date to Buy / Buy Before [date-1]
# Record Date       -> Remove it or say Eligibility Date
# PAT               -> Profit
# EBITDA            -> Operating Profit
# YoY               -> vs Last Year
# QoQ               -> vs Last Quarter
# Consolidated      -> Total Company
# Standalone        -> India Business
# Basis Points      -> Interest Rate
# Monetary Policy   -> RBI Decision
# Geopolitical      -> War / Conflict
# Macroeconomic     -> Economy
# Liquidity         -> Cash
# Headwinds         -> Challenges
# Tailwinds         -> Benefits
# Volatile          -> Up and Down
# Correction        -> Market Fall
# Sequential        -> Quarter on Quarter


# =====================================
# TITLE FORMULA - FOLLOW THIS STRUCTURE
# =====================================

# [Company/Topic + Number] - [Simple Fact] - [Your Question]

# STEP 1 -> Company name + Rs amount or %     <- SEO keyword first
# STEP 2 -> Simple fact what happened         <- User understands instantly
# STEP 3 -> End with "Your" question "?"      <- Personal + clickable

# EXAMPLES BY NEWS TYPE:

# DIVIDEND NEWS:
# Input:  "SBI - Ex-Date: 15-May-2026, Dividend Rs 17"
# Output: "SBI Gives Rs 17 Dividend - Buy Before May 14, Are You Eligible?"

# PROFIT/LOSS NEWS:
# Input:  "Dr Reddy Q4 PAT falls 86% YoY"
# Output: "Dr Reddy Profit Falls 86% - Should You Buy or Exit Now?"

# MARKET FALL:
# Input:  "Sensex down 3400 points in 4 sessions"
# Output: "Sensex Falls 3,400 Points in 4 Days - Is Your Money Safe?"

# POLICY NEWS:
# Input:  "RBI cuts repo rate by 25 basis points"
# Output: "RBI Cuts Rate - Will Your Home Loan EMI Drop This Month?"

# EXPORT/RULE NEWS:
# Input:  "Centre tightens sugar export rules"
# Output: "Sugar Export Rules Tighten - Should You Sell Sugar Stocks Now?"

# IPO NEWS:
# Input:  "Simca Advertising IPO subscribed 80x"
# Output: "This IPO Got 80x Demand - Should You Apply Before Deadline?"

# GOLD/SILVER NEWS:
# Input:  "Gold price hits Rs 16789 today"
# Output: "Gold Hits Rs 16,789 Today - Good Time to Buy or Wait?"


# =====================================
# GOOD TITLES - ALL PASS MANDATORY 3 CHECK:
# =====================================
# OK "SBI Gives Rs 17 Dividend - Are You Eligible Before May 15?"
# OK "Sensex Falls 3,400 Points - Is Your Money Safe?"
# OK "HDFC Life Rs 2.10 Dividend - Buy Before June 18, Are You Eligible?"
# OK "Nifty IT Crashes 3% - Is Your Portfolio at Risk Today?"
# OK "Gold Hits Rs 16,789 - Should You Buy Now or Wait?"
# OK "RBI Cuts Rate - Will Your Home Loan EMI Drop This Month?"
# OK "Dr Reddy Profit Falls 86% - Should You Buy or Exit Now?"
# OK "Sugar Stocks Fall 5% on Export Rules - Should You Sell Now?"

# BAD TITLES - FAIL MANDATORY 3 CHECK:
# =====================================
# X "Sugar Stocks Slide After Centre Tightens Export Rules Till S"
# X "Block deal rush sparks revival hopes in Indian stock market"
# X "SBI Q4 Consolidated PAT Falls 86% YoY on Lower Revenue"
# X "Macroeconomic Headwinds Impact Nifty Trajectory Today"


# =====================================
# STRICT HTML FORMATTING RULES - NEVER BREAK THESE
# =====================================

# 1. NEVER put multiple points on the same line
# 2. NEVER use plain dashes (-) for bullet points always use <ul><li>
# 3. NEVER use 1) 2) 3) numbered format - always use <ul><li>
# 4. NEVER output \\n or \\n\\n - use HTML tags only
# 5. Sectors To Watch MUST use <ul><li> - one <li> per priority
# 6. Action Points MUST use <ul><li> - one <li> per investor type
# 7. Key Risks MUST use <ul><li> - one <li> per risk
# 8. Key Takeaways MUST use <ul><li> - exactly 4 <li> items
# 9. FAQ questions MUST use <h4> - one <h4> per question
# 10. NEVER add <h2>Conclusion</h2> inside Blog_Content
# 11. NEVER add CTA URL inside Blog_Content
# 12. NEVER use em dash — anywhere in the blogs
#     ALWAYS use en dash – instead.
# 13. Write ONLY in English — no foreign language characters

# WRONG FORMAT - NEVER DO THIS:
# X <p>1st Priority: FMCG - reason. 2nd Priority: IT - reason.</p>
# X <p>- SIP investors: advice - Lumpsum investors: advice</p>
# X <p>1) Risk one 2) Risk two 3) Risk three</p>
# X <h2>What is EGR?</h2>   <- FAQ must be H4, not H2

# CORRECT FORMAT - ALWAYS DO THIS:
# OK <ul>
#      <li><strong>1st Priority:</strong> FMCG - reason</li>
#      <li><strong>2nd Priority:</strong> IT - reason</li>
#      <li><strong>Avoid Now:</strong> Real Estate - reason</li>
#    </ul>

# OK <h4>What is NSE EGR and how does it work?</h4>
#    <p>Answer here...</p>


# =====================================
# !! STEP 2 — SEO H2 RULES (CRITICAL) !!
# =====================================

# RULE: Every H2 MUST contain the PRIMARY KEYWORD.

# THESE GENERIC H2 TAGS ARE BANNED — NEVER USE:
#   X <h2>News Context and Market Impact</h2>
#   X <h2>Portfolio and Strategy Focus</h2>
#   X <h2>Risks and Cautions</h2>
#   X <h2>Key Takeaways</h2>

# REPLACE with keyword-specific versions based on detected TYPE:

# ─────────────────────────────────────────────
# TYPE A — IPO article H2 structure:
# ─────────────────────────────────────────────
#   <h2>[Company] IPO - Key Details and Dates</h2>
#   [DATA TABLE here - ONLY IPO gets a table - see STEP 3]
#     <h3>What is [Company] IPO?</h3>
#     <h3>Why This IPO Matters For Investors</h3>

#   <h2>[Company] IPO GMP and Market Sentiment</h2>
#     <h3>Current GMP Analysis - What The Numbers Show</h3>
#     <h3>What [X]% GMP Signals About The Listing</h3>

#   <h2>Should You Apply For [Company] IPO?</h2>
#     <h3>Reasons to Apply - Pros</h3>
#     <ul><li>...</li></ul>
#     <h3>Reasons to Avoid - Risks</h3>
#     <ul><li>...</li></ul>

#   <h2>Risks of Investing in [Company] IPO</h2>
#     <h3>Key Risks To Watch</h3>
#     <ul><li>...</li></ul>

# NOTE: IPO H3 tags stay consistent across all IPO articles
# because investors ask the same questions for every IPO.

# ─────────────────────────────────────────────
# TYPE B - Gold / Silver article H2 structure:
# ─────────────────────────────────────────────
#   <h2>Gold Price in India [Today/This Week] - Live Data</h2>
#   [NO TABLE — go directly to h3]
#   H3 tags - DYNAMIC based on what happened:

#   IF gold fell:
#     <h3>Why Gold Price Fell [X]% Today - Key Reasons</h3>
#     <h3>Which Factor Hit Gold Hardest - [US data/Oil/Dollar]</h3>

#   IF gold rose / hit record:
#     <h3>Why Gold Surged to ₹[X] Today - Key Drivers</h3>
#     <h3>What Is Fuelling This Gold Rally in India</h3>

#   IF gold sideways / uncertain:
#     <h3>Why Gold Is Stuck at ₹[X] - What to Expect</h3>
#     <h3>Key Triggers That Could Move Gold Either Way</h3>

#   <h2>Impact of Gold Price [Fall/Rise] on Your Portfolio</h2>
#   H3 tags - DYNAMIC based on direction:

#   IF gold fell:
#     <h3>What Gold Price Fall Means For Your Holdings</h3>
#     <h3>Should You Add Gold ETF Now or Wait for Lower Levels?</h3>
#     <h3>What SIP, Lumpsum and Traders Should Do Now</h3>

#   IF gold rose:
#     <h3>What Record Gold Price Means For Your Portfolio</h3>
#     <h3>Is This the Right Time to Book Profits on Gold?</h3>
#     <h3>What SIP, Lumpsum and Traders Should Do Now</h3>

#   <h2>Key Risks of [Buying/Holding] Gold Right Now</h2>
#   H3 tags - DYNAMIC:
#     <h3>Risks of [Buying/Holding] Gold at ₹[X] Level</h3>
#     <ul><li>...</li></ul>

# ─────────────────────────────────────────────
# TYPE C — Stock / Company article H2 structure:
# ─────────────────────────────────────────────
#   <h2>[Company] Share Price Today - Key Data</h2>
#   [NO TABLE — go directly to h3]
#   H3 tags - DYNAMIC based on what happened:

#   IF stock rose:
#     <h3>Why [Company] Shares Rose [X]% Today</h3>
#     <h3>Is This [Company] Rally Sustainable?</h3>

#   IF stock fell:
#     <h3>Why [Company] Shares Fell [X]% Today</h3>
#     <h3>Is This [Company] Fall Temporary or Serious?</h3>

#   IF results / earnings:
#     <h3>[Company] Q[X] Results - Revenue and Profit Numbers</h3>
#     <h3>Why [Company] Numbers [Beat/Missed] Expectations</h3>

#   IF dividend:
#     <h3>[Company] Announces ₹[X] Dividend - Who Gets It?</h3>
#     <h3>How to Be Eligible For [Company] Dividend</h3>

#   <h2>Impact of [Company] News on Your Portfolio</h2>
#   H3 tags - DYNAMIC based on direction:

#   IF stock rose:
#     <h3>How [Company] Rise Affects Your [Sector] Holdings</h3>
#     <h3>Which [Sector] Stocks Gain From [Company] Rally?</h3>
#     <h3>What SIP, Lumpsum and Traders Should Do Now</h3>

#   IF stock fell:
#     <h3>How [Company] Fall Hits Your Portfolio</h3>
#     <h3>Should You Buy the Dip in [Company]?</h3>
#     <h3>What SIP, Lumpsum and Traders Should Do Now</h3>

#   IF results:
#     <h3>How [Company] Results Impact Your [Sector] Funds</h3>
#     <h3>Which Stocks Move With [Company] Results?</h3>
#     <h3>What SIP, Lumpsum and Traders Should Do Now</h3>

#   <h2>Key Risks of [Buying/Holding] [Company] Shares Now</h2>
#   H3 tags - DYNAMIC:
#     <h3>Risks of [Specific Action] in [Company] Now</h3>
#     <ul><li>...</li></ul>

# ─────────────────────────────────────────────
# TYPE D — RBI / Interest Rate H2 structure:
# ─────────────────────────────────────────────
#   <h2>RBI Rate Decision Today - What Changed</h2>
#   [NO TABLE — go directly to h3]
#   H3 tags - DYNAMIC based on decision:

#   IF rate cut:
#     <h3>RBI Cuts Repo Rate by [X] Points - Full Breakdown</h3>
#     <h3>Why RBI Chose to Cut Rates Now</h3>

#   IF rate hold:
#     <h3>RBI Holds Repo Rate at [X]% - What It Means</h3>
#     <h3>Why RBI Did Not Cut Despite Pressure</h3>

#   IF rate hike:
#     <h3>RBI Hikes Repo Rate by [X] Points - Full Breakdown</h3>
#     <h3>Why RBI Raised Rates - Inflation Concerns Explained</h3>

#   <h2>Impact of RBI [Cut/Hold/Hike] on Your Money</h2>
#   H3 tags - DYNAMIC based on decision:

#   IF rate cut:
#     <h3>How Much Will Your Home Loan EMI Fall After Rate Cut?</h3>
#     <h3>Which Bank and NBFC Stocks Gain From Rate Cut?</h3>
#     <h3>What SIP, Lumpsum and Traders Should Do Now</h3>

#   IF rate hold:
#     <h3>Why Your Home Loan EMI Stays Same After RBI Hold</h3>
#     <h3>Which Sectors Benefit When RBI Holds Rates?</h3>
#     <h3>What SIP, Lumpsum and Traders Should Do Now</h3>

#   IF rate hike:
#     <h3>How Much Will Your Home Loan EMI Rise After Hike?</h3>
#     <h3>Which Sectors Are Hit Hardest by Rate Hike?</h3>
#     <h3>What SIP, Lumpsum and Traders Should Do Now</h3>

#   <h2>Key Risks After RBI [Cut/Hold/Hike] Decision</h2>
#   H3 tags - DYNAMIC:
#     <h3>Risks For Investors After RBI [Decision Type]</h3>
#     <ul><li>...</li></ul>

# ─────────────────────────────────────────────
# TYPE E - Market / Index article H2 structure:
# ─────────────────────────────────────────────
#   <h2>Sensex Nifty [Today/This Week] - Market Data</h2>
#   [NO TABLE — go directly to h3]
#   H3 tags - DYNAMIC based on direction:

#   IF market fell:
#     <h3>Why Sensex Fell [X] Points Today - [X] Key Reasons</h3>
#     <h3>Which Global and Domestic Factors Triggered the Fall</h3>

#   IF market rose:
#     <h3>Why Sensex Rallied [X] Points Today - Key Drivers</h3>
#     <h3>Which Sectors Led the Market Rally Today</h3>

#   IF market sideways:
#     <h3>Why Sensex is Stuck in a Range - What to Watch</h3>
#     <h3>Key Triggers That Could Break This Market Consolidation</h3>

#   <h2>Impact of [Market Fall/Rally] on Your Portfolio</h2>
#   H3 tags - DYNAMIC based on direction:

#   IF market fell:
#     <h3>How Bad Can This Market Fall Get - Key Levels</h3>
#     <h3>Is This a Buying Opportunity or More Pain Ahead?</h3>
#     <h3>What SIP, Lumpsum and Traders Should Do Now</h3>

#   IF market rose:
#     <h3>Should You Ride This Rally or Book Profits?</h3>
#     <h3>Which Sectors Can Still Give Returns in This Rally?</h3>
#     <h3>What SIP, Lumpsum and Traders Should Do Now</h3>

#   <h2>Key Risks in the Market Right Now</h2>
#   H3 tags - DYNAMIC:
#     <h3>Risks That Could [Deepen the Fall / End the Rally]</h3>
#     <ul><li>...</li></ul>


# =====================================
# !! STEP 2B — DYNAMIC H3 MASTER RULE !!
# =====================================

# H3 tags must reflect WHAT ACTUALLY HAPPENED in the article.
# NEVER copy-paste the same H3 across different articles.

# ONLY ONE H3 stays consistent across ALL article types:
#   "What SIP, Lumpsum and Traders Should Do Now"
#   ← this appears in the second H2 of every non-IPO article

# ALL OTHER H3 tags must be unique to the specific news.
# Use the actual number, company name, or direction in the H3.

# WRONG — generic, repeated across articles:
#   X <h3>What This Means For Your Portfolio</h3>
#   X <h3>Sectors To Watch - Priority Order</h3>
#   X <h3>What Happened</h3>
#   X <h3>Why This Matters</h3>

# CORRECT - specific to the actual news:
#   OK <h3>Why Gold Fell 1% - US-Iran Tensions Explained</h3>
#   OK <h3>Should You Add Gold ETF or Wait for ₹72,000?</h3>
#   OK <h3>Why TCS Profit Fell 86% - Full Breakdown</h3>
#   OK <h3>Should You Buy TCS on This 8% Dip?</h3>
#   OK <h3>How RBI Rate Cut Affects Your ₹50L Home Loan EMI</h3>
#   OK <h3>Why Sensex Fell 500 Points - 3 Key Reasons</h3>


# =====================================
# !! STEP 3 — DATA TABLE !!
# =====================================

# ╔══════════════════════════════════════════════════════╗
# ║  TABLE RULE — READ CAREFULLY                        ║
# ║                                                      ║
# ║  ONLY TYPE A (IPO articles) get a data table.        ║
# ║  ALL OTHER types — NO TABLE at all.                  ║
# ║                                                      ║
# ║  TYPE A IPO   → WRITE table after first H2           ║
# ║  TYPE B Gold  → NO table anywhere                    ║
# ║  TYPE C Stock → NO table anywhere                    ║
# ║  TYPE D RBI   → NO table anywhere                    ║
# ║  TYPE E Market→ NO table anywhere                    ║
# ║  TYPE F Other → NO table anywhere                    ║
# ╚══════════════════════════════════════════════════════╝

# WHY IPO GETS A TABLE — WHY OTHERS DO NOT:
#   IPO data (price, dates, lot size) is FIXED after announcement.
#   It stays accurate for the entire 5-7 day IPO window.
#   Table = perfect for fixed structured data.

#   Gold/Stock/Market prices change every minute.
#   Writing a table with ₹74,000 gold price makes it stale next day.
#   These articles use paragraphs instead — they age better.

# TYPE A — IPO TABLE FORMAT:

#   Write this table immediately after first H2.
#   Use only values from Blog_Content — never invent numbers.
#   If a value is unknown, write "To be announced" — never N/A.

#   <table>
#     <thead>
#       <tr>
#         <th>Detail</th>
#         <th>Information</th>
#       </tr>
#     </thead>
#     <tbody>
#       <tr><td>IPO Open Date</td>      <td>[date or "To be announced"]</td></tr>
#       <tr><td>IPO Close Date</td>     <td>[date or "To be announced"]</td></tr>
#       <tr><td>Price / Price Band</td> <td>[₹X per share or "To be announced"]</td></tr>
#       <tr><td>Lot Size</td>           <td>[N shares or "To be announced"]</td></tr>
#       <tr><td>Minimum Investment</td> <td>[₹amount or "To be announced"]</td></tr>
#       <tr><td>Issue Size</td>         <td>[₹X Crore or "To be announced"]</td></tr>
#       <tr><td>Listing Exchange</td>   <td>[BSE SME / NSE / BSE]</td></tr>
#       <tr><td>Listing Date</td>       <td>[date or "To be announced"]</td></tr>
#     </tbody>
#   </table>

#   IPO TABLE RULES:
#     Never write N/A → use "To be announced"
#     Never write empty cell → use "To be announced"
#     Only use values from Blog_Content — never invent
#     Write table once only — do NOT repeat in other H2 sections


# =====================================
# !! STEP 4 — INTERNAL LINKS (MANDATORY) !!
# =====================================

# Just BEFORE the FAQ section in Blog_Content,
# add exactly 3 internal links.
# Use EXACTLY this format:

#   <p>
#     <strong>Also read:</strong><br>
#     <a href="/[link-1]/">[Anchor text 1 with keyword]</a><br>
#     <a href="/[link-2]/">[Anchor text 2 with keyword]</a><br>
#     <a href="/[link-3]/">[Anchor text 3 with keyword]</a>
#   </p>

# Links by article type:

#   TYPE A IPO:
#     /ipo-calendar-2026/ → View all upcoming IPOs in 2026
#     /how-to-apply-ipo-upi/ → How to apply for IPO via UPI — step by step
#     /ipo-allotment-status/ → How to check IPO allotment status

#   TYPE B Gold:
#     /gold-price-india/ → Gold price in India today — live rates
#     /how-to-invest-gold-etf/ → How to invest in Gold ETF in India
#     /gold-vs-fixed-deposit/ → Gold vs Fixed Deposit — which is better?

#   TYPE C Stock:
#     /stock-analysis-india/ → How to analyse stocks before buying
#     /fundamental-analysis-guide/ → Fundamental analysis guide for beginners
#     /how-to-buy-stocks-india/ → How to buy stocks in India — complete guide

#   TYPE D RBI:
#     /rbi-monetary-policy-2026/ → RBI monetary policy 2026 — all decisions
#     /home-loan-emi-calculator/ → Home loan EMI calculator — check impact
#     /best-fd-rates-india-2026/ → Best FD rates in India 2026

#   TYPE E Market:
#     /sensex-nifty-today/ → Sensex Nifty live — today's market update
#     /top-stocks-to-buy-india/ → Top stocks to buy in India this week
#     /how-to-invest-stock-market/ → How to start investing in stock market


# =====================================
# SEO HEADING HIERARCHY - FOLLOW EXACTLY
# =====================================

# RULE:
# - H1  -> Blog title only (once at top)
# - H2  -> Longtail keyword-rich GROUP heading (must contain main keyword)
# - H3  -> Dynamic sub-sections - specific to the actual news
# - H4  -> FAQ questions only

# WRONG - generic H3 repeated on every page:
# X <h3>What This Means For Your Portfolio</h3>
# X <h3>Sectors To Watch - Priority Order</h3>
# X <h3>What Happened</h3>
# X <h3>Why This Matters</h3>

# CORRECT - dynamic H3 specific to this article:
# OK <h3>Why Gold Fell 1% - US-Iran Tensions Explained</h3>
# OK <h3>Should You Add Gold ETF or Wait for ₹72,000?</h3>
# OK <h3>Why Sensex Fell 500 Points - 3 Key Reasons</h3>
# OK <h3>How RBI Cut Affects Your ₹50L Home Loan EMI</h3>


# =====================================
# MANDATORY BLOG STRUCTURE (Blog_Content):
# =====================================

# ╔══════════════════════════════════════════════════════╗
# ║  IPO ARTICLES (TYPE A) — use this structure         ║
# ╚══════════════════════════════════════════════════════╝

# <h1>[Blog Title - with number + you + question]</h1>

# <h2>[Company] IPO - Key Details and Dates</h2>
# [IPO DATA TABLE — 8 rows — mandatory for IPO only]
#   <h3>What is [Company] IPO?</h3>
#   <p>...</p>
#   <h3>Why This IPO Matters For Investors</h3>
#   <p>...</p>

# <h2>[Company] IPO GMP and Market Sentiment</h2>
#   <h3>Current GMP Analysis - What The Numbers Show</h3>
#   <p>...</p>
#   <h3>What GMP Signals About The Listing</h3>
#   <p>...</p>

# <h2>Should You Apply For [Company] IPO?</h2>
#   <h3>Reasons to Apply - Pros</h3>
#   <ul><li>...</li><li>...</li><li>...</li></ul>
#   <h3>Reasons to Avoid - Risks</h3>
#   <ul><li>...</li><li>...</li><li>...</li></ul>
#   <h3>What SIP, Lumpsum and Traders Should Do Now</h3>
#   <ul>
#     <li><strong>SIP investors:</strong> [advice]</li>
#     <li><strong>Lumpsum investors:</strong> [advice]</li>
#     <li><strong>Traders:</strong> [advice]</li>
#   </ul>
#   <p>[Swastika paragraph — once only here]</p>

# <h2>Risks of Investing in [Company] IPO</h2>
#   <h3>Key Risks To Watch</h3>
#   <ul>
#     <li>[Risk 1]</li>
#     <li>[Risk 2]</li>
#     <li>[Risk 3]</li>
#   </ul>

# <p>
#   <strong>Also read:</strong><br>
#   <a href="/ipo-calendar-2026/">View all upcoming IPOs in 2026</a><br>
#   <a href="/how-to-apply-ipo-upi/">How to apply for IPO via UPI</a><br>
#   <a href="/ipo-allotment-status/">How to check IPO allotment status</a>
# </p>

# <h2>FAQ - [Company] IPO For Retail Investors</h2>
#   <h4>[Q1]?</h4><p>[A1]</p>
#   <h4>[Q2]?</h4><p>[A2]</p>
#   <h4>[Q3]?</h4><p>[A3]</p>
#   <h4>[Q4]?</h4><p>[A4]</p>


# ╔══════════════════════════════════════════════════════╗
# ║  ALL OTHER ARTICLES (TYPE B/C/D/E/F) — use this    ║
# ╚══════════════════════════════════════════════════════╝

# <h1>[Blog Title - with number + you + question]</h1>

# <h2>[TYPE-SPECIFIC H2 with main keyword - Key Details]</h2>
# [NO TABLE — start directly with h3]
#   <h3>[DYNAMIC - WHY did specific thing happen?]</h3>
#   <p>2-3 lines. First sentence MUST contain main keyword.</p>
#   <h3>[DYNAMIC - WHAT caused it / deeper context?]</h3>
#   <p>Market context - specific to this article.</p>

# <h2>[TYPE-SPECIFIC H2 with main keyword - Impact on Your Money]</h2>
#   <h3>[DYNAMIC - HOW does THIS specific event affect YOUR holdings?]</h3>
#   <p>Direct investor impact specific to this news.</p>
#   <h3>[DYNAMIC - WHICH specific stocks/sectors are affected?]</h3>
#   <ul>
#     <li><strong>1st Priority:</strong> [sector] - [one line why]</li>
#     <li><strong>2nd Priority:</strong> [sector] - [one line why]</li>
#     <li><strong>Avoid Now:</strong> [sector] - [one line why]</li>
#   </ul>
#   <h3>What SIP, Lumpsum and Traders Should Do Now</h3>
#   <ul>
#     <li><strong>SIP investors:</strong> [specific advice]</li>
#     <li><strong>Lumpsum investors:</strong> [specific advice]</li>
#     <li><strong>Traders:</strong> [specific advice]</li>
#   </ul>
#   <p>[Swastika paragraph - once only here]</p>

# <h2>[TYPE-SPECIFIC H2 with main keyword - Key Risks]</h2>
# !! THIS H2 = one h3 + one ul only. No extra sections. !!
#   <h3>[DYNAMIC - Risks of SPECIFIC ACTION related to this news]</h3>
#   <ul>
#     <li>[Risk 1 - specific]</li>
#     <li>[Risk 2 - specific]</li>
#     <li>[Risk 3 - specific]</li>
#   </ul>

# <p>
#   <strong>Also read:</strong><br>
#   <a href="/[link-1]/">[anchor text 1]</a><br>
#   <a href="/[link-2]/">[anchor text 2]</a><br>
#   <a href="/[link-3]/">[anchor text 3]</a>
# </p>

# <h2>FAQ - [Main Keyword] For Retail Investors</h2>
#   <h4>[FAQ Q1 - specific to this news]?</h4>
#   <p>[Answer]</p>
#   <h4>[FAQ Q2 - specific to this news]?</h4>
#   <p>[Answer]</p>
#   <h4>[FAQ Q3 - specific to this news]?</h4>
#   <p>[Answer]</p>
#   <h4>[FAQ Q4 - specific to this news]?</h4>
#   <p>[Answer]</p>

# !! STOP HERE - Blog_Content ends after FAQ section !!
# - DO NOT add Conclusion section inside Blog_Content
# - DO NOT add CTA link or URL inside Blog_Content
# - Conclusion goes ONLY in the "Conclusion" JSON field
# - CTA goes ONLY in the "CTA" JSON field


# =====================================
# INVESTOR TONE RULES:
# =====================================
# - Always talk directly to investor ("your portfolio", "you should")
# - Every section must end with investor implication
# - Give CLEAR priority — not everything is equally important
# - Avoid vague: "markets may move" — be specific
# - If bullish: say "consider buying X"
# - If bearish: say "avoid or reduce exposure to X"
# - Keep beginner-friendly — no complex jargon

# SWASTIKA RULE:
# - Include Swastika Investmart in ONLY ONE paragraph inside Blog_Content
# - That paragraph must be 2-5 sentences maximum
# - Naturally blended - not a separate section
# - Do NOT sound like promotion or advertisement
# - Keep it informational and relevant to topic

# QUALITY RULES:
# - Blog length: 900-1200 words
# - Use H1, H2, H3, H4 tags as per hierarchy above
# - TLDR must have exactly 4 points
# - Generate exactly 4 FAQs inside Blog_Content using H4
# - FAQ_Schema JSON field must also have same 4 questions
# - No markdown - only JSON output
# - No extra text outside JSON.

# TLDR KEYWORD RULES — MANDATORY
# Each TLDR point MUST start with or contain
# the PRIMARY KEYWORD of the article.

# PRIMARY KEYWORD by article type:
#   IPO article    → company name + "IPO"
#   Gold article   → "Gold price" or "Gold"
#   Stock article  → company name + "shares" or "stock"
#   RBI article    → "RBI" or "RBI rate"
#   Market article → "Sensex" or "Nifty"
#   Fuel article   → "Fuel prices" or "Petrol diesel"

# WRONG — generic TLDR (no keyword):
#   X "What happened - prices moved today"
#   X "Direct impact on investor portfolio"
#   X "Top priority sector to watch"
#   X "Action - review your exposure"

# CORRECT — keyword in every point:
#   OK "Gold price fell 1% today on MCX to ₹74,000"
#   OK "Gold price fall reduces portfolio hedge value"
#   OK "Watch Gold ETFs and MCX gold futures this week"
#   OK "Add gold ETF gradually — avoid lumpsum now"

#   OK "Aureate Tradde IPO opens May 29 at ₹70 per share"
#   OK "Aureate Tradde IPO carries SME liquidity risk"
#   OK "SME IPO space — watch subscription demand closely"
#   OK "Apply Aureate Tradde IPO only with small allocation"

# RULES:
#   Point 1 → keyword + what happened + number/date
#   Point 2 → keyword + portfolio impact + specific sector
#   Point 3 → keyword + specific sector or stock to watch
#   Point 4 → keyword + specific action (not "review exposure")

# =====================================
# STRICT ANTI-DUPLICATION RULES
# =====================================

# Before generating Blog_Content, check for duplicate sections.

# 1. Internal links block must appear EXACTLY ONCE.
#    Place it only immediately before the FAQ section.

# 2. Swastika Investmart paragraph must appear EXACTLY ONCE.
#    Use only one paragraph mentioning Swastika Investmart.

# 3. Never repeat sector recommendations.
#    If sectors are listed once, do not create another sector list.

# 4. Never create a second risk or opportunity section.
#    Only one dedicated risk section is allowed.

# 5. Every H2 must introduce NEW information.
#    No H2 may repeat information covered by a previous H2.

# 6. Before returning output, verify:
#    - Internal links count = 1
#    - Swastika paragraph count = 1
#    - Risk section count = 1
#    - Sector recommendation section count = 1
#    - Table appears only if article is TYPE A (IPO)
#    - No repeated H2 topics


# =====================================
# !! FINAL SELF-CHECK BEFORE OUTPUT !!
# READ THIS BEFORE GENERATING JSON
# =====================================

# CHECK 1 — Table rule:
#   Is this a TYPE A IPO article?
#   YES → table must be present after first H2
#   NO  → no table anywhere in Blog_Content
#         If you wrote a table → DELETE it

# CHECK 2 — H2 TLDR:
#   Is there a <h2>TLDR</h2> in my output?
#   YES → DELETE the h2 tag, keep the ul list

# CHECK 3 — FAQ heading:
#   Does FAQ h2 contain main keyword?
#   NO → Add keyword: <h2>FAQ — [Topic] For Investors</h2>

# CHECK 4 — FAQ tag format:
#   Are FAQ questions using <h4> tags?
#   NO → Change <h3> or bold text to <h4>

# CHECK 5 — Lists format:
#   Are sectors and action points in <ul><li>?
#   NO → Wrap in proper <ul><li><strong> format

# CHECK 6 — H3 placeholders:
#   Do any H3 contain placeholder words like
#   "What caused it" or "deeper context"?
#   YES → Rewrite with specific company/event name

# CHECK 7 — THIRD H2 IS RISKS ONLY:
#   Does my third H2 contain "Opportunities" or
#   a second priority/sectors list?
#   YES → Remove it. Third H2 = risks ul list only.
#   WRONG: <h2>Key Risks and Opportunities</h2>
#   RIGHT: <h2>Key Risks in the Market Right Now</h2>

# CHECK 8 — NO REPETITIONS:
#   Count how many times these appear in Blog_Content:
#   Swastika paragraph     → must be exactly 1
#   SIP/Lumpsum section    → must be exactly 1
#   Internal links block   → must be exactly 1
#   Priority/sectors ul    → must be exactly 1
#   If any appear more than once → delete the extra ones
# """

#     result = cached_model_call(prompt)
#     data   = json.loads(result)

#     # Post-processors: fix issues regardless of AI output
#     source = item.get("source", "")
#     data   = fix_all_fields(data, source=source)

#     return data











































































































































































































































