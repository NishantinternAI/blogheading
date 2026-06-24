# import json
# from functools import lru_cache
# from config import client, MODEL
# from utils.mcp_tools import fetch_and_clean

# # ─────────────────────────────────────────────────────────────
# # INTERNAL TOOL DEFINITION
# # Tells the LLM what function it can call and what args to pass.
# # Your Python code executes it — no external server needed.
# # ─────────────────────────────────────────────────────────────

# FETCH_ARTICLE_TOOL = {
#     "type": "function",
#     "name": "fetch_article_content",
#     "description": (
#         "Scrape and clean a news article from a URL. "
#         "Always call this first before writing any blog. "
#         "Returns the full article text to base the blog on."
#     ),
#     "parameters": {
#         "type": "object",
#         "properties": {
#             "url": {
#                 "type": "string",
#                 "description": "Full article URL to scrape"
#             },
#             "title": {
#                 "type": "string",
#                 "description": "Article headline — helps remove duplicate title from body"
#             },
#             "fallback_text": {
#                 "type": "string",
#                 "description": "RSS summary — used if scraping fails on server"
#             }
#         },
#         "required": ["url"]
#     }
# }


# # ─────────────────────────────────────────────────────────────
# # TOOL EXECUTOR — runs locally in your Python process
# # ─────────────────────────────────────────────────────────────

# def _execute_tool(tool_name: str, arguments: str) -> str:
#     """Execute the function the LLM requested. Returns result as JSON string."""
#     args = json.loads(arguments)

#     if tool_name == "fetch_article_content":
#         result = fetch_and_clean(
#             url=args.get("url", ""),
#             title=args.get("title", ""),
#             fallback_text=args.get("fallback_text", "")
#         )
#         print(f"   [TOOL] fetch_article_content → {result['quality']} ({result['word_count']} words) via {result['method']}")
#         return json.dumps(result, ensure_ascii=False)

#     return json.dumps({"error": f"Unknown tool: {tool_name}"})


# # ─────────────────────────────────────────────────────────────
# # TRACKERS
# # ─────────────────────────────────────────────────────────────

# total_cost     = 0.0
# api_call_count = 0

# def reset_cost_tracker():
#     global total_cost, api_call_count
#     total_cost     = 0.0
#     api_call_count = 0

# def get_total_cost():     return total_cost
# def get_api_call_count(): return api_call_count


# # ─────────────────────────────────────────────────────────────
# # CACHED MODEL CALL
# # use_tools=True  → LLM can call fetch_article_content locally
# # use_tools=False → plain LLM call, no tools (default)
# # ─────────────────────────────────────────────────────────────

# @lru_cache(maxsize=200)
# def cached_model_call(prompt: str, use_tools: bool = False) -> str:
#     global total_cost, api_call_count
#     api_call_count += 1
#     print(f"Calling API... (Call #{api_call_count})"
#           + (" [tools enabled]" if use_tools else ""))

#     tools = [FETCH_ARTICLE_TOOL] if use_tools else []

#     # ── First LLM call ───────────────────────────────────────
#     response = client.responses.create(
#         model=MODEL,
#         tools=tools,
#         input=[
#             {"role": "system", "content": "You must return a valid JSON response only."},
#             {"role": "user",   "content": prompt},
#         ],
#         text={
#             "format":    {"type": "json_object"},
#             "verbosity": "high",
#         },
#         reasoning={
#             "effort":  "high",
#             "summary": "auto",
#         },
#         store=True,
#     )

#     # ── Tool call loop ────────────────────────────────────────
#     # LLM may request one or more tool calls before giving final answer
#     while use_tools:
#         tool_calls = [
#             item for item in response.output
#             if getattr(item, "type", None) == "function_call"
#         ]
#         if not tool_calls:
#             break  # no tool calls — LLM gave final answer

#         # Build next input: original messages + LLM output + tool results
#         # Must include system message so 'json' word is present for json_object format
#         next_input = [
#             {"role": "system", "content": "You must return a valid JSON response only."},
#             {"role": "user",   "content": prompt},
#             *response.output,
#         ]
#         for tc in tool_calls:
#             tool_result = _execute_tool(tc.name, tc.arguments)
#             next_input.append({
#                 "type":    "function_call_output",
#                 "call_id": tc.call_id,
#                 "output":  tool_result,
#             })

#         api_call_count += 1
#         print(f"Calling API... (Call #{api_call_count}) [tool result → final answer]")

#         response = client.responses.create(
#             model=MODEL,
#             tools=tools,
#             input=next_input,
#             text={
#                 "format":    {"type": "json_object"},
#                 "verbosity": "high",
#             },
#             reasoning={
#                 "effort":  "high",
#                 "summary": "auto",
#             },
#             store=True,
#         )

#     # ── Cost tracking ─────────────────────────────────────────
#     input_tokens  = response.usage.input_tokens
#     output_tokens = response.usage.output_tokens
#     cost          = (input_tokens / 1_000_000) * 3 + (output_tokens / 1_000_000) * 15
#     total_cost   += cost

#     print(f"   Input Tokens  : {input_tokens}")
#     print(f"   Output Tokens : {output_tokens}")
#     print(f"   💰 Call Cost   : ${cost:.6f}")

#     return response.output_text



# from functools import lru_cache
# from config import client, MODEL

# # ─────────────────────────────────────────────────────────────
# # TRACKERS
# # ─────────────────────────────────────────────────────────────

# total_cost     = 0.0
# api_call_count = 0

# def reset_cost_tracker():
#     global total_cost, api_call_count
#     total_cost     = 0.0
#     api_call_count = 0

# def get_total_cost():     return total_cost
# def get_api_call_count(): return api_call_count


# # ─────────────────────────────────────────────────────────────
# # CACHED MODEL CALL — single API call, no tools
# # ─────────────────────────────────────────────────────────────

# @lru_cache(maxsize=200)
# def cached_model_call(prompt: str) -> str:
#     global total_cost, api_call_count
#     api_call_count += 1
#     print(f"Calling API... (Call #{api_call_count})")

#     response = client.responses.create(
#         model=MODEL,
#         input=[
#             {"role": "system", "content": "You must return a valid JSON response only."},
#             {"role": "user",   "content": prompt},
#         ],
#         text={
#             "format":    {"type": "json_object"},
#             "verbosity": "high",
#         },
#         reasoning={
#             "effort":  "high",
#             "summary": "auto",
#         },
#         store=True,
#     )

#     input_tokens  = response.usage.input_tokens
#     output_tokens = response.usage.output_tokens
#     cost          = (input_tokens / 1_000_000) * 3 + (output_tokens / 1_000_000) * 15
#     total_cost   += cost

#     print(f"   Input Tokens  : {input_tokens}")
#     print(f"   Output Tokens : {output_tokens}")
#     print(f"   💰 Call Cost   : ${cost:.6f}")

#     return response.output_text







import os
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
    global total_cost, api_call_count
    total_cost     = 0.0
    api_call_count = 0

def get_total_cost():     return total_cost
def get_api_call_count(): return api_call_count


# ─────────────────────────────────────────────────────────────
# WEB SEARCH CONFIG
#
# allowed_domains — restricts web_search to these sources only.
# Add any domain here that is WAF-blocked by your scraper cascade.
#
# INCLUDE_LIST — asks OpenAI to return reasoning trace + source URLs
# alongside the response for debugging and audit purposes.
# ─────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────
# WEB SEARCH CONFIG
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

# Must mirror WEB_SEARCH_TOOL allowed_domains (with + without www)
# WS_TRIGGER_DOMAINS = {
#     # PRIORITY_SOURCES
#     "www.nseindia.com",
#     "nseindia.com",
#     "trends.google.com",
#     # NEWS_SOURCES
#     "zerodha.com",
#     "www.zerodha.com",
#     "www.cnbctv18.com",
#     "cnbctv18.com",
#     "www.5paisa.com",
#     "5paisa.com",
#     "www.livemint.com",
#     "livemint.com",
#     "news.google.com",
#     "www.economictimes.indiatimes.com",
#     "economictimes.indiatimes.com",
#     "www.ndtvprofit.com",
#     "ndtvprofit.com",
#     "www.business-standard.com",
#     "business-standard.com",
# }

# ─────────────────────────────────────────────────────────────
# WEB SEARCH FETCH — Step 1 (text mode, no JSON)
#
# OpenAI does NOT allow web_search + json_object in one call.
# Solution: two-step approach
#   Step 1 → fetch_via_websearch()  — web_search, text mode, gets article
#   Step 2 → cached_model_call()    — json mode, no tools, writes blog
#
# Only fires for domains listed in WS_TRIGGER_DOMAINS.
# For all other domains returns "" so blog_generator falls back
# to the existing RSS content in item["Blog_Content"].
# ─────────────────────────────────────────────────────────────

# def fetch_via_websearch(url: str) -> str:
#     """
#     Fetches article content using OpenAI's built-in web_search tool.
#     No domain restriction — works for any URL including Google Trends sources.
#     """
#     try:
#         response = client.responses.create(
#             model=MODEL,
#             input=[
#                 {
#                     "role": "user",
#                     "content": (
#                         f"Search for this article and extract all key information from it: "
#                         f"every statistic, number, date, company name, expert quote, "
#                         f"financial figure, and important fact mentioned. "
#                         f"Present them as detailed notes — do not summarise or paraphrase numbers. "
#                         f"Keep all rupee figures, percentages, and named sources exactly as stated."
#                         f"Do NOT ask follow-up questions. "        # ← add this
#                         f"Do NOT offer further options. "          # ← add this
#                         f"Just return the extracted data and stop.\n\n"
#                         f"URL: {url}"
#                     )
#                 }
#             ],
#             tools   = [WEB_SEARCH_TOOL],
#             include = INCLUDE_LIST,
#             store   = False,
#         )

#         content    = response.output_text or ""
#         word_count = len(content.split())
#         domain     = urlparse(url).netloc
#         print(f"   [WEB_SEARCH] {domain} → {word_count} words fetched")

#         # ── Extract which URLs were actually used ──────────────────
#         sources_log = []

#         for item in response.output:
#             if item.type == "web_search_call":
#                 sources = getattr(item, "sources", []) or []
#                 if sources:
#                     print(f"   [WEB_SEARCH] Sources used:")
#                     for s in sources:
#                         print(f"      → {s.get('url', 'unknown')}")
#                         print(f"         {s.get('title', '')}")
        
#         _log_prompt(
#             call_num  = api_call_count,
#             prompt    = content,
#             metadata  = {
#                 "original_url"  : url,
#                 "words_fetched" : word_count,
#                 "sources_used"  : sources_log,
#             }
#         )
#         return content

#     except Exception as e:
#         print(f"   [WEB_SEARCH] Failed for {url}: {e}")
#         return ""


def fetch_via_websearch(url: str) -> str:
    """
    Fetches article content using OpenAI's built-in web_search tool.
    No domain restriction — works for any URL including Google Trends sources.
    """
    global api_call_count
    api_call_count += 1
    ws_call_num = api_call_count

    try:
        response = client.responses.create(
            model=MODEL,
            input=[
                {
                    "role": "user",
                    "content": (
                        f"Search for this article and extract all key information from it: "
                        f"every statistic, number, date, company name, expert quote, "
                        f"financial figure, and important fact mentioned. "
                        f"Present ONLY as bullet-point notes — do not summarise or paraphrase numbers. "
                        f"Keep all rupee figures, percentages, and named sources exactly as stated. "
                        f"Do NOT ask follow-up questions. "
                        f"Do NOT offer further options. "
                        f"Just return the extracted data and stop.\n\n"
                        f"URL: {url}"
                    )
                }
            ],
            tools   = [WEB_SEARCH_TOOL],
            include = INCLUDE_LIST,
            store   = False,
        )

        content    = response.output_text or ""
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

        _log_prompt(
            call_num = ws_call_num,
            prompt   = content,
            metadata = {
                "type"          : "WEB_SEARCH",
                "original_url"  : url,
                "words_fetched" : word_count,
                "sources_used"  : sources_log,
            }
        )

        return content

    except Exception as e:
        print(f"   [WEB_SEARCH] Failed for {url}: {e}")
        return ""
# ─────────────────────────────────────────────────────────────
# CACHED MODEL CALL — Step 2 (json mode, no tools)
# ─────────────────────────────────────────────────────────────

@lru_cache(maxsize=200)
def cached_model_call(prompt: str) -> str:
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