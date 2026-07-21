"""
generate_corporate_blog.py
══════════════════════════
Generates a full SEO/GEO-optimised blog article for NSE Corporate Action items.

PIPELINE INTEGRATION
────────────────────
In mergeall_engine.py:

    from generate_corporate_blog import generate_corporate_blog

    if source == "nse_corporate":
        data = generate_corporate_blog(item)

INPUT
─────
    item dict from nse_corporate_fetcher.parse_nse_rss_item()
    All required keys are documented in nse_corporate_fetcher.py

OUTPUT
──────
    dict with keys:
        Blog_Title, Meta_Title, Meta_Description,
        TLDR (list of 4),
        Blog_Content (HTML string),
        Conclusion   (HTML string),
        FAQ_Schema   (schema.org FAQPage object)

    Passed through fix_all_fields() before returning.
"""

import json
import logging
from typing import Optional

import requests
from bs4 import BeautifulSoup

log = logging.getLogger(__name__)

# ── your existing pipeline modules ────────────────────────────────────────────
from add_cached import cached_model_call, fix_all_fields, _strip_page_furniture


# ─────────────────────────────────────────────────────────────────────────────
# ARTICLE FETCHER  (tries to get real article body if URL is not generic NSE)
# ─────────────────────────────────────────────────────────────────────────────

_NSE_GENERIC_URL = "https://www.nseindia.com/companies-listing/corporate-filings-actions"

_FETCH_HEADERS = {
    "User-Agent"     : (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-IN,en;q=0.9",
    "Accept"         : "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

def _fetch_article(url: str) -> dict:
    """
    Tries to fetch the article body from a news URL.
    Returns {"title": str, "body": str, "fetched": bool, "error": str}
    Never raises — always returns gracefully.
    """
    out = {"title": "", "body": "", "fetched": False, "error": ""}

    # Skip the generic NSE corporate actions page — nothing useful to scrape
    if not url or url.strip().rstrip("/") == _NSE_GENERIC_URL.rstrip("/"):
        out["error"] = "nse_generic_url"
        return out

    if not url.startswith("http"):
        out["error"] = "not_a_url"
        return out

    try:
        r = requests.get(url, headers=_FETCH_HEADERS, timeout=15)
        r.raise_for_status()
    except Exception as e:
        out["error"] = str(e)
        return out

    soup = BeautifulSoup(r.text, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer",
                     "aside", "form", "noscript", "iframe"]):
        tag.decompose()

    og = soup.find("meta", property="og:title")
    out["title"] = og["content"].strip() if og else (soup.title.string or "").strip()

    body = ""
    for sel in [
        {"itemprop": "articleBody"},
        {"class"   : "article-body"},
        {"class"   : "story-content"},
        {"class"   : "article__body"},
        "article",
    ]:
        tag = (soup.find(["div", "section", "article"], sel)
               if isinstance(sel, dict) else soup.find(sel))
        if tag:
            body = tag.get_text(separator="\n", strip=True)
            break

    if not body:
        paras = soup.find_all("p")
        body  = "\n".join(
            p.get_text(strip=True) for p in paras
            if len(p.get_text(strip=True)) > 40
        )

    out["body"]    = _strip_page_furniture(body).strip()[:6000]
    out["fetched"] = bool(body)
    return out


# ─────────────────────────────────────────────────────────────────────────────
# STRUCTURED DATA BLOCK  (what the LLM reads as ground truth)
# ─────────────────────────────────────────────────────────────────────────────

def _build_data_block(item: dict) -> str:
    def f(key):
        v = item.get(key)
        return str(v) if v is not None else "N/A"

    return f"""COMPANY          : {f('company_name')}
SYMBOL / ISIN    : {f('symbol')} / {f('isin')}
ACTION TYPE      : {f('action_type').upper()}
NSE PURPOSE LINE : {f('purpose')}
EX-DATE          : {f('ex_date')}
RECORD DATE      : {f('record_date')}
PAYMENT DATE     : {f('payment_date')}
AMOUNT / RATIO   : {f('amount')}
FACE VALUE       : {f('face_value')}
DIVIDEND SUBTYPE : {f('subtype')}"""


# ─────────────────────────────────────────────────────────────────────────────
# SOURCE SECTION  (switches between full article and structured-data-only mode)
# ─────────────────────────────────────────────────────────────────────────────

def _build_source_section(item: dict, article: dict) -> str:
    data_block = _build_data_block(item)
    url        = item.get("Blog_Links", "")

    if article.get("fetched") and article.get("body"):
        return f"""THE SOURCE MATERIAL  (read every word before writing anything)

Article title   : {article['title']}
Source URL      : {url}

--- ARTICLE TEXT START ---
{article['body']}
--- ARTICLE TEXT END ---

NSE STRUCTURED DATA  (ground truth — these fields override any ambiguity in the article):
{data_block}

CRITICAL RULE: Every rupee figure, date, company name, ratio, and percentage
in the structured data AND the article MUST appear in the blog if relevant.
Never paraphrase ₹ figures. Write ₹12 per share, not "a significant dividend".
Never approximate dates. Write "18 Jun 2026", not "mid-June 2026"."""

    # No article body — structured data only
    return f"""THE SOURCE MATERIAL

The NSE corporate actions RSS item provides all available data.
There is no additional article to fetch.
Use ONLY the fields below. If a field shows N/A, do not invent a value.
Write "as per NSE disclosure" and omit the unknown field.

NSE STRUCTURED DATA:
{data_block}

Source URL (do not publish): {url}"""


# ─────────────────────────────────────────────────────────────────────────────
# ACTION-SPECIFIC WRITING RULES  (one block per action type)
# ─────────────────────────────────────────────────────────────────────────────

def _action_rules(action_type: str, item: dict) -> str:
    company = item.get("company_name", "[Company]")
    isin    = item.get("isin") or "ISIN"
    ex_date = item.get("ex_date") or "[ex-date]"
    amount  = item.get("amount") or "[amount]"
    rec     = item.get("record_date") or "[record-date]"
    subtype = item.get("subtype") or "Dividend"

    rules = {

"dividend": f"""
ACTION: DIVIDEND

KEY DATA — extract all present values, use every one that exists:
  - Dividend amount        : exact ₹ per share — never paraphrase
  - Interim or Final       : {subtype}
  - Ex-date                : {ex_date}  — MOST IMPORTANT DATE (investor must hold BEFORE this)
  - Record date            : {rec}
  - Payment date           : if available
  - Dividend yield %       : calculate as (amount / CMP × 100) only if CMP is in source

INVESTOR ANGLE:
  The reader's one question: "Do I qualify, and should I buy before ex-date?"
  Lead with the ₹ amount and ex-date in the first sentence.
  Explain eligibility in plain terms (hold shares before ex-date, not on ex-date).
  Distinguish between ex-date and record date — most retail investors confuse them.
  Cover whether the dividend is sustainable if history data is available.

GEO ANCHOR SENTENCES — place both in the first half of Blog_Content:
  Anchor 1: "{company} ({isin}) declared a {subtype} dividend of {amount}
  with ex-date {ex_date}, as per BSE/NSE quarterly corporate action disclosure."
  Anchor 2 (if yield calculable): "At the current market price, this implies
  a dividend yield of [Y.YY]%, making it one of the [higher/lower]-yielding
  stocks in the [sector] space."

URGENCY FRAMING: High — investor must act before {ex_date}.
""",

"bonus": f"""
ACTION: BONUS ISSUE

KEY DATA — extract all present values:
  - Bonus ratio             : e.g. 1:1 = 1 free share per 1 held
  - Ex-date / Record date   : {ex_date}
  - Board approval date     : if available
  - Post-bonus share count  : calculate if total shares available

INVESTOR ANGLE:
  Retail investors often confuse bonus shares with wealth creation.
  Clarify explicitly: bonus increases your share count but the price adjusts
  proportionally on ex-date — net portfolio value is unchanged on that day.
  The real signal is: promoter confidence in the stock's future, improved
  liquidity for retail buyers, and potential for post-split re-rating.
  Cover: how many shares for every X held, price adjustment, eligibility cutoff.

GEO ANCHOR SENTENCES:
  Anchor 1: "{company} ({isin}) announced a bonus share issue in the ratio
  {amount}, effective ex-date {ex_date}, entitling eligible shareholders
  to additional shares for every share held on record date, per NSE filing."
  Anchor 2: "The bonus issue will proportionally reduce the share price
  on ex-date while increasing the total share count, leaving investor
  portfolio value unchanged at the time of issue."

URGENCY FRAMING: High — eligibility tied to holding before {ex_date}.
""",

"split": f"""
ACTION: STOCK SPLIT

KEY DATA — extract all present values:
  - Split ratio             : e.g. 10:1
  - Old face value          : ₹[X] per share
  - New face value          : ₹[Y] per share
  - Ex-date                 : {ex_date}
  - Adjusted share price    : approx = CMP ÷ split ratio (if CMP available)
  - F&O lot size change     : note if the stock has active derivatives

INVESTOR ANGLE:
  Stock splits make high-priced shares affordable for retail investors.
  Address the two most common misconceptions:
    1. Your investment value does not change — you hold more shares at a lower price.
    2. A split is NOT a bonus — there is no wealth creation on ex-date.
  Cover: what changes (price, share count, lot size), what does not change (total value).

GEO ANCHOR SENTENCES:
  Anchor 1: "{company} ({isin}) approved a stock split of {amount},
  effective ex-date {ex_date}, which will proportionally reduce the
  market price while increasing the share count per investor, per NSE disclosure."
  Anchor 2: "Existing shareholders' portfolio value remains unchanged on
  ex-date as the price adjustment mirrors the split ratio exactly."

URGENCY FRAMING: Medium — investors should understand impact before ex-date.
""",

"rights": f"""
ACTION: RIGHTS ISSUE

KEY DATA — extract all present values:
  - Rights ratio            : e.g. 1 share per 5 held
  - Issue price             : exact ₹ per share
  - Issue open date         : when subscription window opens
  - Issue close date        : deadline — most important date
  - Record date             : eligibility cutoff
  - Discount to CMP         : calculate if both prices available
  - Renouncement option     : can the investor sell their entitlement?

INVESTOR ANGLE:
  Rights issue is a HIGH-STAKES decision with two competing outcomes:
    - Subscribe: get shares at a discount (if issue price < CMP)
    - Skip: face dilution as your ownership percentage falls
  Explain both clearly. State plainly: what happens if the investor does nothing.
  Also cover: can you sell your rights entitlement if you don't want to subscribe?

GEO ANCHOR SENTENCES:
  Anchor 1: "{company} ({isin}) announced a rights issue at {amount}
  in a [N:M] ratio, opening [date] and closing [date], per SEBI-mandated
  NSE corporate action filing."
  Anchor 2: "Shareholders who do not subscribe will face dilution of their
  ownership stake, while those who subscribe receive shares at [a discount
  to / at parity with] the current market price."

URGENCY FRAMING: Very High — hard subscription deadline, financial decision required.
""",

"buyback": f"""
ACTION: BUYBACK

KEY DATA — extract all present values:
  - Buyback price           : exact ₹ per share
  - Buyback size            : total ₹ crore outlay
  - Method                  : tender offer or open market
  - Record date             : {rec}
  - % of paid-up capital targeted
  - Premium over CMP        : calculate (buyback price - CMP) / CMP × 100
  - Estimated acceptance ratio : total eligible shares ÷ shares company will buy

INVESTOR ANGLE:
  The central question: "Is the buyback price above current market price,
  and what is my realistic acceptance ratio?"
  Lead with the buyback price vs CMP premium.
  Explain acceptance ratio in plain terms — company will NOT accept 100% of
  tendered shares; you only get a fraction of your tendered shares bought back.
  Cover whether buyback signals undervaluation or is just a cash return mechanism.

GEO ANCHOR SENTENCES:
  Anchor 1: "{company} ({isin}) announced a share buyback at {amount},
  aggregating ₹[W] crore via the [tender/open market] route, with record
  date {rec}, per NSE regulatory disclosure."
  Anchor 2: "The buyback price represents a [Z]% [premium/discount] to the
  last traded price, and the estimated acceptance ratio is approximately
  [X]% of each investor's eligible shares."

URGENCY FRAMING: Medium-High — tender deadline for eligible shareholders.
""",

"agm": f"""
ACTION: AGM / EGM

KEY DATA — extract all present values:
  - Meeting date and type   : AGM or EGM
  - Key agenda items        : list ALL — dividend, capital raise, director change, etc.
  - Record date for voting  : {rec}
  - Special resolutions     : any proposed
  - Final dividend proposed : amount if known
  - Capital raise proposed  : rights issue, QIP, preferential allotment

INVESTOR ANGLE:
  Not all AGMs are equal. The angle depends entirely on the agenda.
  If dividend approval is on the agenda: cover expected amount and payout.
  If capital raise is proposed: explain dilution risk clearly.
  If director change is proposed: note any governance implications.
  Always cover: how retail shareholders can participate or vote (e-voting via CDSL/NSDL).

GEO ANCHOR SENTENCES:
  Anchor 1: "{company} ({isin}) scheduled its [AGM/EGM] on [meeting date]
  to consider key agenda items including [top 2 items], per NSE corporate
  filing dated {item.get('pub_date', '[date]')}."
  Anchor 2: "Shareholders with holdings as of record date {rec} are
  eligible to vote, including via the CDSL/NSDL e-voting facility."

URGENCY FRAMING: Low-Medium — higher if capital raise or dividend approval is on agenda.
""",

"general": f"""
ACTION: CORPORATE ACTION (GENERAL)

The specific action type could not be auto-classified. Identify it from the source data.
State the corporate action type clearly in the opening paragraph.

KEY DATA to extract:
  - Company name and corporate action description
  - Effective date or ex-date
  - Financial impact on shareholders
  - Eligibility conditions

GEO ANCHOR SENTENCE:
  "{company} ({isin}) announced [action description] effective [date],
  impacting shareholders as [key financial impact], per NSE regulatory
  disclosure."

URGENCY FRAMING: Derive from the nature of the action.
""",

    }

    return rules.get(action_type, rules["general"]).strip()


# ─────────────────────────────────────────────────────────────────────────────
# FULL PROMPT BUILDER
# ─────────────────────────────────────────────────────────────────────────────

def _build_prompt(item: dict, article: dict) -> str:
    action_type    = item.get("action_type", "general")
    source_section = _build_source_section(item, article)
    action_section = _action_rules(action_type, item)
    company        = item.get("company_name", "[Company]")

    return f"""You are a senior financial content strategist for Swastika Investmart, a SEBI-registered
Indian stockbroker serving retail investors across India. You write long-form blogs that rank
on Google and get cited by AI search engines: Perplexity, ChatGPT Search, Gemini, and Claude.

Your standard: E-E-A-T (Experience, Expertise, Authoritativeness, Trustworthiness).
Every factual claim must be grounded in the source data below. Do not invent numbers,
dates, or facts not present in the source.


{source_section}
{action_section}

DATA EXTRACTION — do this mentally before writing a single word

From the source, identify:
  1. Company name and stock symbol/ISIN
  2. Corporate action type (confirmed above)
  3. The KEY FINANCIAL FIGURE (₹ amount, ratio, or price)
  4. The MOST CRITICAL DATE (ex-date, record date, or subscription close)
  5. Investor eligibility condition
  6. One risk or caveat for the investor

Items 3 and 4 MUST appear in the opening sentence.

---

BLOG TITLE

Write a blog title that does three things at once:
- Contains the primary long-tail keyword naturally
- Should rank higher in GEO and SEO

The title is the most important SEO signal in the entire blog.
---

OPENING

Start with the sharpest hook, most interesting thing 
about this story — a tension, a number, a consequence, a question worth answering.

---
BODY STRUCTURE

Let the story decide the structure.

Instead:
- Each H2 must be a long-tail keyword phrase a real investor would search
- Each H2 must make a specific claim or raise a specific question
- Each section must add something the previous one didn't

    



    ---

TLDR

Write exactly 4 short, punchy sentences. No bullet formatting beyond the list structure. Each sentence must stand alone and deliver real information.

---

TABLES

If the source material contains 3 or more timestamped price points, or any
series of numeric data meant to be compared side by side (intraday price
ticks, SMA/EMA levels, daily/weekly/monthly returns, volume figures,
valuation ratios), you MUST present that data as an HTML <table> —
never as a prose paragraph listing timestamps and figures one after another.

Example — intraday price ticks become:
<table><tr><th>Time (IST)</th><th>Price (Rs)</th><th>Change</th></tr>
<tr><td>03:35 PM</td><td>186.46</td><td>+0.31%</td></tr>
<tr><td>03:30 PM</td><td>186.35</td><td>+0.25%</td></tr></table>

Example — moving averages / returns become:
<table><tr><th>Metric</th><th>Value</th></tr>
<tr><td>5-Day SMA</td><td>Rs 186.40</td></tr>
<tr><td>7-Day SMA</td><td>Rs 187.30</td></tr>
<tr><td>1-Year Return</td><td>15.11%</td></tr></table>

For any other content, add a table only when it genuinely helps the reader
compare structured data — do not force one into narrative-only sections.

---

CONCLUSION

The conclusion is the last thing the investor reads. Make it the most useful paragraph in the blog.

Write 2 paragraphs under <h2>Conclusion</h2>:
Summarize what this story means for the retail investor right now - not a recap of facts, but the so-what.
Give the investor one clear next step or mental model they can apply.


----

FAQ

Write 4–6 FAQ questions and Answers that would rank in Google Search. 
Answers must be specific, factual, and grounded in the source article.



---

SWASTIKA CONTEXT

Swastika offers: stocks, F&O, mutual funds, IPOs, ETFs, bonds, MCX, SLBM, pledging, 
research reports, and Sarthi — an AI stock assistant that gives institutional-level 
research on any stock or index to retail investors.

Place one implicit CTA in the body where it genuinely fits the article context. A natural bridge between what the investor 
just learned and what they might do next.
---

SEO OUTPUT REQUIREMENTS

Meta Title: Under 60 characters. Must contain the primary keyword. Must create click 
intent. Count the characters.

Meta Description: Under 155 characters. One sentence. Tell the reader exactly what 
insight they'll get from clicking. Count the characters.

---
HTML RULES

These are allowed tags which you can use: <h1> <h2> <h3> <h4> <p> <ul> <li> <strong> <u> <a href=""> 
<table> <tr> <th> <td>

TLDR points go in <li> tags with no paragraph following them.
FAQ questions use <h4>. Answers use <p>.
Every major section needs an <h2>. Use <h3> only for genuine subsections.
-------

output
Return only valid JSON. No markdown. No explanation. No code fences.

{{
  "Blog_Title"      : "",
  "Meta_Title"      : "",
  "Meta_Description": "",
  "TLDR"            : ["", "", "", ""],
  "Blog_Content"    : "",
  "Conclusion"      : "",
  "FAQ_Schema"      : {{
    "@context"  : "https://schema.org",
    "@type"     : "FAQPage",
    "mainEntity": [
      {{
        "@type": "Question",
        "name" : "",
        "acceptedAnswer": {{ "@type": "Answer", "text": "" }}
      }},
      {{
        "@type": "Question",
        "name" : "",
        "acceptedAnswer": {{ "@type": "Answer", "text": "" }}
      }},
      {{
        "@type": "Question",
        "name" : "",
        "acceptedAnswer": {{ "@type": "Answer", "text": "" }}
      }},
      {{
        "@type": "Question",
        "name" : "",
        "acceptedAnswer": {{ "@type": "Answer", "text": "" }}
      }}
    ]
  }}
}}

"""


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def generate_corporate_blog(item: dict) -> dict:
    """
    Full pipeline call for one NSE Corporate Action item.

    Args:
        item : structured dict from nse_corporate_fetcher.parse_nse_rss_item()

    Returns:
        post-processed blog dict ready for Webflow publish

    Raises:
        ValueError if the LLM returns invalid JSON (with raw output for debugging)
    """
    source  = item.get("source", "nse_corporate")
    url     = item.get("Blog_Links", "")
    company = item.get("company_name", "unknown")
    action  = item.get("action_type", "general")

    log.info(f"[CORPORATE BLOG] {company} | action={action} | url={url[:60]}")

    # Step 1: try to fetch a real article (skips generic NSE URL automatically)
    article = _fetch_article(url)
    if article["fetched"]:
        log.info(f"[CORPORATE BLOG] Article fetched ({len(article['body'])} chars)")
    else:
        log.info(f"[CORPORATE BLOG] No article — structured data only ({article['error']})")

    # Step 2: build prompt
    prompt = _build_prompt(item, article)

    # Step 3: call LLM
    result = cached_model_call(prompt)

    # Step 4: parse JSON
    try:
        data = json.loads(result)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"[CORPORATE BLOG] JSON parse failed\n"
            f"Company : {company}\n"
            f"Action  : {action}\n"
            f"Error   : {e}\n"
            f"Raw output (first 800 chars):\n{result}"
        ) from e

    # Step 5: post-process with your existing fix_all_fields
    data = fix_all_fields(data, source=source)

    log.info(f"[CORPORATE BLOG] Done — {company} | {action}")
    return data