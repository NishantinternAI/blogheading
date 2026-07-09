# """
# mcp_agent.py
# ------------
# AI agent that drives the blog posting flow via tool use (MCP pattern).

# After run_pipeline() saves output.json, the scheduler calls run_agent().
# The model (GPT-4o) decides which tools to call and in what order — it is
# not hardcoded to post; it reads the situation and acts accordingly.

# Tools exposed to the model mirror blog_post_mcp.py so any MCP-compatible
# AI (Claude, Gemini, GPT-4o) can drive the same flow through the same server.
# """

# import os
# import json
# import logging
# from config import client, MODEL
# from webflow_poster import post_entry_as_draft, post_results_as_drafts

# log = logging.getLogger(__name__)

# OUTPUT_JSON_PATH = os.environ.get("OUTPUT_JSON_PATH", "/app/output/output.json")
# IMAGE_JPG_DIR    = os.environ.get("IMAGE_JPG_DIR",    "/app/output_images/jpg_images")

# # ── Tool definitions (same surface as blog_post_mcp.py) ───────────────────

# TOOLS = [
#     {
#         "type": "function",
#         "function": {
#             "name": "post_single_blog",
#             "description": (
#                 "Post one blog entry as a Webflow CMS draft — with h2 spacing, "
#                 "FAQ schema, and images uploaded. Call this with the blog entry "
#                 "that was just generated."
#             ),
#             "parameters": {
#                 "type": "object",
#                 "properties": {
#                     "blog_entry_json": {
#                         "type": "string",
#                         "description": "JSON string of the single blog entry to post.",
#                     },
#                     "image_dir": {
#                         "type": "string",
#                         "description": "Absolute path to jpg_images folder.",
#                     },
#                 },
#                 "required": ["blog_entry_json"],
#             },
#         },
#     },
# ]


# # ── Tool executor ──────────────────────────────────────────────────────────

# def _execute_tool(name: str, args: dict) -> str:
#     """Run the tool the model decided to call. Returns a JSON string result."""
#     try:
#         if name == "post_blogs_from_file":
#             path      = args.get("output_json_path", OUTPUT_JSON_PATH)
#             image_dir = args.get("image_dir", IMAGE_JPG_DIR)
#             with open(path, encoding="utf-8") as f:
#                 entries = json.load(f)
#             results = post_results_as_drafts(entries, image_dir)
#             ok = sum(1 for r in results if not r.get("error"))
#             return json.dumps({
#                 "total":   len(results),
#                 "saved":   ok,
#                 "errors":  len(results) - ok,
#                 "results": results,
#             })

#         elif name == "post_single_blog":
#             entry     = json.loads(args["blog_entry_json"])
#             image_dir = args.get("image_dir", IMAGE_JPG_DIR)
#             result    = post_entry_as_draft(entry, image_dir)
#             return json.dumps(result)

#         else:
#             return json.dumps({"error": f"Unknown tool: {name}"})

#     except Exception as e:
#         return json.dumps({"error": str(e)})


# # ── Agent loop ─────────────────────────────────────────────────────────────

# def run_agent(entry: dict) -> str:
#     """
#     Run the MCP agent for a single blog entry.
#     The model decides to call post_single_blog with the entry.

#     Args:
#         entry: The single blog entry dict returned by run_pipeline().
#     Returns:
#         The model's final text response (confirmation / summary).
#     """
#     blog_title = entry.get("blog", {}).get("Blog_Title", entry.get("Blog_Title", ""))

#     messages = [
#         {
#             "role": "system",
#             "content": (
#                 "You are a blog publishing assistant for Swastika Investmart. "
#                 "You have a tool to post a single blog draft to the Webflow CMS. "
#                 "When given a blog entry, post it as a draft. "
#                 "Be concise — confirm what was posted and flag any errors."
#             ),
#         },
#         {
#             "role": "user",
#             "content": (
#                 f"A new blog has just been generated: \"{blog_title}\". "
#                 f"Post it to Webflow as a draft now. "
#                 f"The image directory is {IMAGE_JPG_DIR}. "
#                 f"Here is the full blog entry:\n{json.dumps(entry)}"
#             ),
#         },
#     ]

#     print("[AGENT] Starting MCP agent loop...")

#     # Agentic loop — model keeps calling tools until it's done
#     while True:
#         response = client.chat.completions.create(
#             model=MODEL,
#             messages=messages,
#             tools=TOOLS,
#             tool_choice="auto",
#         )

#         msg = response.choices[0].message
#         messages.append(msg)

#         # No tool calls — model is done
#         if not msg.tool_calls:
#             final = msg.content or "Done."
#             print(f"[AGENT] {final}")
#             return final

#         # Execute each tool the model called
#         for tc in msg.tool_calls:
#             name = tc.function.name
#             args = json.loads(tc.function.arguments)
#             print(f"[AGENT] Calling tool: {name}({list(args.keys())})")

#             result = _execute_tool(name, args)
#             print(f"[AGENT] Tool result: {result[:120]}...")

#             messages.append({
#                 "role":         "tool",
#                 "tool_call_id": tc.id,
#                 "content":      result,
#             })






"""
mcp_agent.py
------------
AI agent that drives the blog posting flow via tool use (MCP pattern).

After run_pipeline() saves output.json, the scheduler calls run_agent().
The model (GPT-4o) decides ONLY whether to call the tool — it never
carries the blog payload itself. The entry is stored in memory and read
directly by _execute_tool(), bypassing GPT-4o's JSON serialization entirely.
"""

import os
import json
import logging
from config import client, MODEL
from webflow_poster import post_entry_as_draft, post_results_as_drafts

log = logging.getLogger(__name__)

OUTPUT_JSON_PATH = os.environ.get("OUTPUT_JSON_PATH", "/app/output/output.json")
IMAGE_JPG_DIR    = os.environ.get("IMAGE_JPG_DIR",    "/app/output_images/jpg_images")

# ── In-memory store — entry is saved here before agent runs ───────────────
# GPT-4o never sees or carries the blog data. It only calls the tool by name.
_PENDING_ENTRY: dict = {}

_ALREADY_POSTED: bool = False


# ── Tool definitions ───────────────────────────────────────────────────────

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "post_single_blog",
            "description": (
                "Post the pending blog entry as a Webflow CMS draft — with h2 spacing, "
                "FAQ schema, and images uploaded. Call this to post the blog that was "
                "just generated. The blog data is already loaded in memory."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "image_dir": {
                        "type": "string",
                        "description": "Absolute path to jpg_images folder.",
                    },
                },
                "required": [],
            },
        },
    },
]


# ── Tool executor ──────────────────────────────────────────────────────────

def _execute_tool(name: str, args: dict) -> str:
    """
    Run the tool the model decided to call.
    Entry data is read from _PENDING_ENTRY — NOT from GPT's arguments.
    Returns a JSON string result.
    """
    global _ALREADY_POSTED
 
    try:
        if name == "post_single_blog":
            entry     = _PENDING_ENTRY
            image_dir = args.get("image_dir", IMAGE_JPG_DIR)
 
            if not entry:
                return json.dumps({"error": "No pending entry found in memory."})
 
            # ── NEW: duplicate post guard ──────────────────────────────────
            # Prevents the same blog being posted twice when GPT makes a
            # second tool call after a successful first post in the same
            # agent loop. Seen in logs as two consecutive post_single_blog
            # calls producing two separate Webflow items with the same content.
            if _ALREADY_POSTED:
                print("[AGENT] ⚠️  Duplicate post prevented — blog already posted in this session")
                return json.dumps({
                    "status":  "already_posted",
                    "message": "Blog was already posted successfully in this agent loop. No action taken."
                })
            # ──────────────────────────────────────────────────────────────
 
            result         = post_entry_as_draft(entry, image_dir)
            _ALREADY_POSTED = True   # ← mark posted so second call is blocked
            return json.dumps(result)
 
        elif name == "post_blogs_from_file":
            path      = args.get("output_json_path", OUTPUT_JSON_PATH)
            image_dir = args.get("image_dir", IMAGE_JPG_DIR)
            with open(path, encoding="utf-8") as f:
                entries = json.load(f)
            results = post_results_as_drafts(entries, image_dir)
            ok = sum(1 for r in results if not r.get("error"))
            return json.dumps({
                "total":   len(results),
                "saved":   ok,
                "errors":  len(results) - ok,
                "results": results,
            })
 
        else:
            return json.dumps({"error": f"Unknown tool: {name}"})
 
    except Exception as e:
        return json.dumps({"error": str(e)})
 

# ── Agent loop ─────────────────────────────────────────────────────────────

def run_agent(entry: dict) -> str:
    """
    Run the MCP agent for a single blog entry.

    The entry is stored in _PENDING_ENTRY memory BEFORE the agent starts.
    GPT-4o only receives the blog title — it never sees the full payload.
    This prevents JSON truncation and control character errors.

    Args:
        entry: The single blog entry dict returned by run_pipeline().
    Returns:
        The model's final text response (confirmation / summary).
    """
    global _PENDING_ENTRY, _ALREADY_POSTED
    _PENDING_ENTRY  = entry      # store full entry in memory
    _ALREADY_POSTED = False      # reset so each new blog can post once

    blog_title = entry.get("blog", {}).get("Blog_Title", entry.get("Blog_Title", ""))

    messages = [
        {
            "role": "system",
            "content": (
                "You are a blog publishing assistant for Swastika Investmart. "
                "You have a tool to post the pending blog draft to Webflow CMS. "
                "The blog data is already loaded in memory — you do not need to pass it. "
                "Call post_single_blog ONCE to post it — do not call it again after success. "
                "Be concise — confirm the title, item_id, and slug. Flag any errors."
                
            ),
        },
        {
            "role": "user",
            "content": (
                f"A new blog has just been generated: \"{blog_title}\". "
                f"Post it to Webflow as a draft now. "
                f"Use image directory: {IMAGE_JPG_DIR}"
                # NOTE: full entry JSON is NOT passed here anymore.
                # It is stored in _PENDING_ENTRY and read by _execute_tool directly.
            ),
        },
    ]

    print("[AGENT] Starting MCP agent loop...")

    while True:
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
        )

        msg = response.choices[0].message
        messages.append(msg)

        if not msg.tool_calls:
            final = msg.content or "Done."
            print(f"[AGENT] {final}")
            return final

        for tc in msg.tool_calls:
            name = tc.function.name
            args = json.loads(tc.function.arguments)
            print(f"[AGENT] Calling tool: {name}({list(args.keys())})")

            result = _execute_tool(name, args)
            print(f"[AGENT] Tool result: {result[:120]}...")

            messages.append({
                "role":         "tool",
                "tool_call_id": tc.id,
                "content":      result,
            })