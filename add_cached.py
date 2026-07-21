"""
add_cached.py -- Model-call layer shared by the blog generators.

Two OpenAI call paths live here:
  - cached_model_call() -- the main JSON-mode blog-writing call
    (@lru_cache'd on the prompt text). No web_search tool attached; it
    only writes from whatever context the caller already assembled.
  - fetch_via_websearch() / fetch_ipo_live_data_via_ai() -- the two
    call paths that DO use OpenAI's built-in web_search tool, for
    fetching source-article content and live IPO GMP/subscription data
    respectively. Both scrub/validate the model's output before
    returning it (see _strip_page_furniture, _looks-like-valid-GMP
    style validation in fetch_ipo_live_data_via_ai) so page furniture
    or unparseable answers never reach a published blog as fact.

Also home to fix_all_fields() and friends -- the post-processing pass
applied to every generated blog's fields (garbage-character stripping,
placeholder cleanup, FAQ/conclusion ordering fixes) before it's handed
to webflow_poster.py.

Prompt/response pairs are logged to logs/prompts/<date>.txt via
_log_prompt()/_log_response() for later audit (see reports/*.md).
"""

import os
import re
import json
from datetime import datetime
from functools import lru_cache
from urllib.parse import urlparse
from config import client, MODEL

# ─────────────────────────────────────────────────────────────
# PROMPT LOGGING — one file per day
# logs/prompts/2026-06-20.txt  ← all calls from that day
# logs/prompts/2026-06-21.txt  ← next day, new file
# ─────────────────────────────────────────────────────────────

LOG_DIR     = "logs/prompts"
ENABLE_LOGS = True


def _get_daily_log_path() -> str:
    """Returns today's log file path e.g. logs/prompts/2026-06-20.txt"""
    os.makedirs(LOG_DIR, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    return os.path.join(LOG_DIR, f"{today}.txt")


def _log_prompt(call_num: int, prompt: str, metadata: dict = None):
    """Append prompt to today's log file."""
    if not ENABLE_LOGS:
        return
    try:
        filepath = _get_daily_log_path()
        ts       = datetime.now().strftime("%H:%M:%S")

        with open(filepath, "a", encoding="utf-8") as f:
            f.write("\n" + "=" * 70 + "\n")
            f.write(f"  CALL #{call_num}  |  {datetime.now().strftime('%Y-%m-%d')}  {ts}\n")
            f.write("=" * 70 + "\n")

            if metadata:
                f.write("\nMETADATA:\n")
                for k, v in metadata.items():
                    f.write(f"  {k}: {v}\n")

            f.write("\nPROMPT:\n")
            f.write("-" * 70 + "\n")
            f.write(prompt)
            f.write("\n")

        print(f"   [LOG] → {filepath}  (Call #{call_num})")
    except Exception as e:
        print(f"   [LOG] Failed: {e}")


def _log_response(call_num: int, response_text: str,
                  input_tokens: int, output_tokens: int, cost: float):
    """Append LLM response to today's log file."""
    if not ENABLE_LOGS:
        return
    try:
        filepath = _get_daily_log_path()

        with open(filepath, "a", encoding="utf-8") as f:
            f.write("\nRESPONSE:\n")
            f.write("-" * 70 + "\n")
            f.write(f"  Input Tokens  : {input_tokens}\n")
            f.write(f"  Output Tokens : {output_tokens}\n")
            f.write(f"  Cost          : ${cost:.6f}\n")
            f.write("-" * 70 + "\n")
            try:
                parsed = json.loads(response_text)
                f.write(json.dumps(parsed, indent=2, ensure_ascii=False))
            except Exception:
                f.write(response_text)
            f.write("\n" + "=" * 70 + "\n")
    except Exception as e:
        print(f"   [LOG] Failed to save response: {e}")


# ─────────────────────────────────────────────────────────────
# TRACKERS
# ─────────────────────────────────────────────────────────────

total_cost     = 0.0
api_call_count = 0

def reset_cost_tracker():
    """Zeroes the module-level total_cost and api_call_count globals.
    Call this at the start of a pipeline run so cost/call totals don't
    accumulate across unrelated runs sharing the same process."""
    global total_cost, api_call_count
    total_cost     = 0.0
    api_call_count = 0

def get_total_cost():
    """Returns the running total_cost (USD, float) accumulated so far by
    cached_model_call() across all calls since the last reset_cost_tracker()."""
    return total_cost

def get_api_call_count():
    """Returns the running api_call_count (int) — every call to
    cached_model_call(), fetch_via_websearch(), and fetch_ipo_live_data_via_ai()
    increments this shared global counter, since it doubles as the log call-number."""
    return api_call_count


# ─────────────────────────────────────────────────────────────
# WEB SEARCH CONFIG
#
# allowed_domains — restricts web_search to these sources only.
# Add any domain here that is WAF-blocked by your scraper cascade.
#
# INCLUDE_LIST — asks OpenAI to return reasoning trace + source URLs
# alongside the response for debugging and audit purposes.
# ─────────────────────────────────────────────────────────────

WEB_SEARCH_TOOL = {
    "type": "web_search",
    "search_context_size": "high",
    "user_location": {"type": "approximate"}
    # "filters": {
    #     "allowed_domains": [
    #         # PRIORITY_SOURCES
    #         "www.nseindia.com",
    #         "trends.google.com",
    #         # NEWS_SOURCES
    #         "zerodha.com",
    #         "www.cnbctv18.com",
    #         "www.5paisa.com",
    #         "www.livemint.com",
    #         "news.google.com",
    #         "economictimes.indiatimes.com",
    #         "www.ndtvprofit.com",
    #         "www.business-standard.com",
    #     ]
    # }
}

INCLUDE_LIST = [
    "reasoning.encrypted_content",
    "web_search_call.action.sources",
]

# Page-furniture patterns that live-blog/ticker pages surface alongside real
# data (update counters, comment-section markers, nav labels) but that are
# NOT facts about the story — must never reach the writing prompt or a
# published blog.
_PAGE_FURNITURE_PATTERNS = [
    r"\b\d+\s+New\s+Updates?\b",
    r"\bComments?\s+section\b",
    r"\b(?:Live\s+)?Blog\s+(?:continues|updated)\b",
    r"\bFollow\s+us\s+on\b.*",
    r"\bShare\s+this\s+article\b.*",
    r"\bClick\s+here\s+to\b.*",
    r"\bRead\s+More\b\s*$",
]


def _strip_page_furniture(text: str) -> str:
    """Removes scraped webpage UI furniture (update counters, comment-section
    markers, nav prompts) that isn't part of the article's actual content."""
    if not text:
        return text
    cleaned = text
    for pattern in _PAGE_FURNITURE_PATTERNS:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
    return cleaned


_GMP_LINE_RE = re.compile(r'^GMP:\s*₹\s*(-?[\d,]+(?:\.\d+)?)\s*\(([\d.]+)%\)', re.IGNORECASE)
_SUB_LINE_RE = re.compile(r'^(RETAIL|NII|QIB|OVERALL):\s*([\d.]+)x', re.IGNORECASE)


def fetch_ipo_live_data_via_ai(company_name: str) -> dict:
    """
    Fetches GMP + live subscription status for an IPO via OpenAI's web_search
    tool instead of raw scraping — this data lives on JS-rendered pages
    (InvestorGain's subscription tables, live GMP widgets) that plain
    requests+BeautifulSoup can't see, but the model's own search/browse tool
    can. Every field is strictly format-validated before being trusted; any
    line that doesn't match the required format is dropped rather than
    passed through as free text, so a confused/hallucinated answer can never
    reach the blog as a fabricated number.

    Returns a dict with only the keys it was confident about, e.g.
    {"gmp": "₹15 (4.76%)", "retail_sub": "0.08x", "nii_sub": "0.15x",
     "qib_sub": "0.00x", "overall_sub": "0.10x"} — missing/unparseable
    fields are simply absent, never guessed.
    """
    global api_call_count
    api_call_count += 1
    ws_call_num = api_call_count

    request_text = (
        f"Search for the current Grey Market Premium (GMP) and live Day-1/Day-2 "
        f"subscription status for the {company_name} IPO in India — check sources "
        f"like InvestorGain, Chittorgarh, or IPO Watch. "
        f"Reply with ONLY these lines, in exactly this format, nothing else — "
        f"no explanation, no markdown, no extra text:\n"
        f"GMP: ₹<amount> (<percent>%)\n"
        f"RETAIL: <number>x\n"
        f"NII: <number>x\n"
        f"QIB: <number>x\n"
        f"OVERALL: <number>x\n"
        f"If a value is not currently available, write NOT AVAILABLE on that "
        f"line instead (e.g. \"GMP: NOT AVAILABLE\"). Never estimate or guess "
        f"a number — only report it if a source states it directly."
    )

    try:
        response = client.responses.create(
            model=MODEL,
            input=[{"role": "user", "content": request_text}],
            tools   = [WEB_SEARCH_TOOL],
            include = INCLUDE_LIST,
            store   = False,
        )
        content = response.output_text or ""
    except Exception as e:
        print(f"   [IPO LIVE DATA] Failed for {company_name}: {e}")
        return {}

    usage = getattr(response, "usage", None)
    _log_prompt(
        call_num = ws_call_num,
        prompt   = request_text,
        metadata = {"type": "IPO_LIVE_DATA", "company": company_name},
    )
    _log_response(
        call_num      = ws_call_num,
        response_text = content,
        input_tokens  = getattr(usage, "input_tokens", 0) if usage else 0,
        output_tokens = getattr(usage, "output_tokens", 0) if usage else 0,
        cost          = 0.0,
    )

    result = {}
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        m = _GMP_LINE_RE.match(line)
        if m:
            result["gmp"] = f"₹{m.group(1)} ({m.group(2)}%)"
            continue
        m = _SUB_LINE_RE.match(line)
        if m:
            field = {"RETAIL": "retail_sub", "NII": "nii_sub",
                      "QIB": "qib_sub", "OVERALL": "overall_sub"}[m.group(1).upper()]
            result[field] = f"{m.group(2)}x"

    print(f"   [IPO LIVE DATA] {company_name} → parsed fields: {list(result.keys())}")
    return result


def fetch_via_websearch(url: str) -> str:
    """
    Fetches article content using OpenAI's built-in web_search tool.
    No domain restriction — works for any URL including Google Trends sources.
    """
    global api_call_count
    api_call_count += 1
    ws_call_num = api_call_count

    # ── This is the actual REQUEST sent to the model ────────────────────
    request_text = (
        f"Search for this article and extract all key information from it: "
        f"every statistic, number, date, company name, expert quote, "
        f"financial figure, and important fact mentioned. "
        f"Present ONLY as bullet-point notes — do not summarise or paraphrase numbers. "
        f"Do NOT include inline citation links or markdown links like ([source](url)) "
        f"after each bullet point — return plain text bullet points only, no hyperlinks. "
        f"Keep all rupee figures, percentages, and named sources exactly as stated. "
        f"Do NOT extract page furniture or site UI text — this includes update "
        f"counters (e.g. '1 New Update'), comment-section markers, 'follow us' / "
        f"'share this' / 'click here' prompts, navigation labels, or anything "
        f"describing the webpage itself rather than the story. Only extract facts "
        f"that are actually about the news story. "
        f"If the source contains a timestamped price series (e.g. intraday stock "
        f"ticks), extract each timestamp with its paired price/value as one bullet "
        f"per data point, not prose. "
        f"Do NOT ask follow-up questions. "
        f"Do NOT offer further options. "
        f"Just return the extracted data and stop.\n\n"
        f"URL: {url}"
    )

    try:
        response = client.responses.create(
            model=MODEL,
            input=[
                {
                    "role": "user",
                    "content": request_text,
                }
            ],
            tools   = [WEB_SEARCH_TOOL],
            include = INCLUDE_LIST,
            store   = False,
        )

        content    = _strip_page_furniture(response.output_text or "")
        word_count = len(content.split())
        domain     = urlparse(url).netloc
        print(f"   [WEB_SEARCH] {domain} → {word_count} words fetched")

        # ── Extract which URLs were actually used ──────────────────
        sources_log = []

        for output_item in response.output:
            if output_item.type == "web_search_call":
                action  = getattr(output_item, "action", None)
                sources = getattr(action, "sources", []) if action else []

                if sources:
                    print(f"   [WEB_SEARCH] Sources used:")
                    for s in sources:
                        if isinstance(s, dict):
                            src_url   = s.get("url",   "unknown")
                            src_title = s.get("title", "")
                        else:
                            src_url   = getattr(s, "url",   "unknown")
                            src_title = getattr(s, "title", "")

                        sources_log.append(src_url)
                        print(f"      → {src_url}")
                        print(f"         {src_title}")
        # ───────────────────────────────────────────────────────────

        # ── FIX: log the REQUEST under PROMPT, and the RESPONSE under RESPONSE ──
        # Previously `content` (the model's output) was passed into _log_prompt(),
        # which wrote it under a "PROMPT:" header — making the response look like
        # the prompt in the log file. This corrects that by logging each piece
        # under its correct, accurately labelled section.
        _log_prompt(
            call_num = ws_call_num,
            prompt   = request_text,
            metadata = {
                "type"          : "WEB_SEARCH",
                "original_url"  : url,
                "words_fetched" : word_count,
                "sources_used"  : sources_log,
            }
        )

        usage = getattr(response, "usage", None)
        _log_response(
            call_num      = ws_call_num,
            response_text = content,
            input_tokens  = getattr(usage, "input_tokens", 0) if usage else 0,
            output_tokens = getattr(usage, "output_tokens", 0) if usage else 0,
            cost          = 0.0,
        )
        # ──────────────────────────────────────────────────────────────────────

        return content

    except Exception as e:
        print(f"   [WEB_SEARCH] Failed for {url}: {e}")
        return ""


# ─────────────────────────────────────────────────────────────
# CACHED MODEL CALL — Step 2 (json mode, no tools)
# ─────────────────────────────────────────────────────────────

@lru_cache(maxsize=200)
def cached_model_call(prompt: str) -> str:
    """
    Main JSON-mode blog-writing call — no web_search tool attached, so it
    writes only from context the caller already assembled into `prompt`.

    Gotcha: @lru_cache'd on the exact `prompt` string (maxsize=200) — an
    identical prompt returns the cached response and does NOT increment
    api_call_count/total_cost or write a new log entry, so retrying with
    the same prompt text after a downstream failure will silently reuse
    the old result instead of calling the API again.

    Side effects: increments the global api_call_count, adds this call's
    cost to the global total_cost (priced at $3/M input + $15/M output
    tokens), and writes the prompt/response pair to logs/prompts/<date>.txt
    via _log_prompt()/_log_response().

    Returns the raw JSON string from response.output_text (the caller is
    responsible for json.loads-ing it).
    """
    global total_cost, api_call_count
    api_call_count += 1
    print(f"Calling API... (Call #{api_call_count})")

    _log_prompt(
        call_num=api_call_count,
        prompt=prompt,
        metadata={
            "model":        MODEL,
            "prompt_words": len(prompt.split()),
            "prompt_chars": len(prompt),
        }
    )

    response = client.responses.create(
        model=MODEL,
        input=[
            {"role": "system", "content": "You must return a valid JSON response only."},
            {"role": "user",   "content": prompt},
        ],
        text={
            "format":    {"type": "json_object"},
            "verbosity": "high",
        },
        reasoning={
            "effort":  "high",
            "summary": "auto",
        },
        store=True,
    )

    input_tokens  = response.usage.input_tokens
    output_tokens = response.usage.output_tokens
    cost          = (input_tokens / 1_000_000) * 3 + (output_tokens / 1_000_000) * 15
    total_cost   += cost

    print(f"   Input Tokens  : {input_tokens}")
    print(f"   Output Tokens : {output_tokens}")
    print(f"   💰 Call Cost   : ${cost:.6f}")

    _log_response(
        call_num=api_call_count,
        response_text=response.output_text,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost=cost,
    )

    return response.output_text