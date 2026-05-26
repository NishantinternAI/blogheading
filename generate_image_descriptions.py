# generate_image_descriptions.py
# Run ONCE to generate descriptions for all templates

# import os
# import json
# import base64
# from config import client


# TEMPLATES_BASE = "content_engine/templates"

# # ── Generate for these categories ────────────────────────────
# CATEGORIES = ["finance", "general"]


# def image_to_base64(image_path: str) -> str:
#     with open(image_path, "rb") as f:
#         return base64.b64encode(f.read()).decode("utf-8")


# def describe_image(image_path: str) -> str:
#     """Send image to GPT-4o vision and get description."""
#     base64_image = image_to_base64(image_path)
#     ext          = os.path.splitext(image_path)[1].lower().replace(".", "")
#     mime         = "image/png" if ext == "png" else "image/jpeg"

#     response = client.chat.completions.create(
#         model="gpt-4o",
#         messages=[
#             {
#                 "role": "user",
#                 "content": [
#                     {
#                         "type": "image_url",
#                         "image_url": {
#                             "url": f"data:{mime};base64,{base64_image}"
#                         }
#                     },
#                     {
#                         "type": "text",
#                         "text": """You are describing a financial blog background image for an AI template matching system.

# Analyze this image carefully and return ONLY in this EXACT format (no extra text):

# Visual: [describe exactly what you see - objects, people, charts, symbols, flags, buildings]
# Mood: [choose one: dark-dramatic / bright-optimistic / neutral-professional]
# Best for: [10-12 VERY SPECIFIC blog topics this image perfectly matches, comma separated]
# Avoid for: [8-10 blog topics this image should NEVER be used for, comma separated]

# STRICT RULES:
# - Coal mining image → Best for ONLY coal/mining topics, NOT general energy
# - Oil barrels image → Best for ONLY oil/crude/Iran topics, NOT banking or pharma
# - Stock market bull/bear → Best for general stocks, earnings, dividends, Nifty
# - Stressed person chart → Best for market crash, bad news, losses ONLY
# - Geopolitics/war image → Best for war/conflict/sanctions ONLY
# - Technology/globe image → Best for IT stocks, digital, fintech, global markets
# - Handshake/partnership → Best for deals, mergers, investments, positive news

# EXAMPLES:

# Coal mining image:
# Visual: large coal excavator with coal heap, dark dramatic sky
# Mood: dark-dramatic
# Best for: coal stocks, Coal India news, coal sector decline, mining company results, coal prices fall, commodity sector bearish, coal production update, mining sector news
# Avoid for: general stock market, earnings season, dividend announcement, pharma stocks, banking news, RBI policy, IT sector, IPO news, rupee movement, oil prices

# Oil barrels image:
# Visual: oil barrels, pumpjack, US and Iran flags, globe, stock charts
# Mood: dark-dramatic
# Best for: crude oil prices, OPEC news, oil sector stocks, Iran sanctions, US-Iran tensions, energy geopolitics, Brent crude, oil marketing companies, petrol diesel prices
# Avoid for: banking regulation, dividend news, pharma results, IT stocks, general earnings, RBI policy, mutual funds, IPO, gold prices, rupee news

# Stock market bull bear image:
# Visual: bull and bear symbols, stock charts rising, financial district buildings
# Mood: neutral-professional
# Best for: general stock market news, Nifty Sensex update, earnings results, dividend announcement, stock picks, market rally, bull run, investment strategy, portfolio advice, quarterly results
# Avoid for: coal mining, oil prices, war conflict, natural disasters, geopolitics only

# Provide ONLY the 4 fields above. No extra sentences."""
#                     }
#                 ]
#             }
#         ],
        
#     )

#     return response.choices[0].message.content.strip()


# def generate_for_category(category: str):
#     """Generate descriptions for outer/ folder of a category."""

#     outer_folder  = os.path.join(TEMPLATES_BASE, category, "outer")
#     output_file   = os.path.join(TEMPLATES_BASE, category, "image_descriptions.json")

#     if not os.path.exists(outer_folder):
#         print(f"[SKIP] {category}/outer/ not found — skipping")
#         return

#     templates = sorted([
#         f for f in os.listdir(outer_folder)
#         if f.lower().endswith(('.png', '.jpg', '.jpeg'))
#     ])

#     if not templates:
#         print(f"[SKIP] No templates in {category}/outer/")
#         return

#     print(f"\n[{category.upper()}] Processing {len(templates)} templates...")

#     descriptions = {}

#     for template in templates:
#         path = os.path.join(outer_folder, template)
#         key  = f"outer/{template}"

#         print(f"  Describing {key}...")

#         try:
#             desc = describe_image(path)
#             descriptions[key] = desc
#             print(f"  ✅ {desc[:80]}...")
#         except Exception as e:
#             print(f"  ❌ Error: {e}")
#             descriptions[key] = "General financial markets image"

#     # ── Save descriptions JSON inside category folder ─────────
#     with open(output_file, "w", encoding="utf-8") as f:
#         json.dump(descriptions, f, indent=2, ensure_ascii=False)

#     print(f"  ✅ Saved → {output_file}")
#     print(f"  Total: {len(descriptions)} images described")


# def main():
#     for category in CATEGORIES:
#         generate_for_category(category)

#     print("\n✅ All descriptions generated!")


# if __name__ == "__main__":
#     main()

# generate_image_descriptions.py
# Run ONCE to generate descriptions for all templates

import os
import json
import base64
from functools import lru_cache
from config import client, MODEL

TEMPLATES_BASE = "content_engine/templates"
CATEGORIES = ["finance", "general"]

# ── Cost & Call Trackers (mirrors cached_model_call pattern) ─────────────────
total_cost = 0.0
api_call_count = 0


def reset_cost_tracker():
    global total_cost, api_call_count
    total_cost = 0.0
    api_call_count = 0


def get_total_cost():
    return total_cost


def get_api_call_count():
    return api_call_count


# ── Vision Cache (uses image_path as cache key) ───────────────────────────────
@lru_cache(maxsize=200)
def cached_vision_call(image_path: str) -> str:
    """
    Mirrors cached_model_call but for GPT-4o Vision.
    Cache key = image_path (since same image always gives same description).
    Returns a JSON string.
    """
    global total_cost, api_call_count

    api_call_count += 1
    print(f"  Calling Vision API... (Call #{api_call_count})")

    # ── Read & encode image ───────────────────────────────────────────────────
    with open(image_path, "rb") as f:
        base64_image = base64.b64encode(f.read()).decode("utf-8")

    ext  = os.path.splitext(image_path)[1].lower().replace(".", "")
    mime = "image/png" if ext == "png" else "image/jpeg"

    # ── Prompt (JSON format to match cached_model_call convention) ────────────
    prompt_text = """You are describing a financial blog background image for an AI template matching system.

Analyze this image carefully and return a valid JSON object in EXACTLY this format:

{
  "visual": "describe exactly what you see - objects, people, charts, symbols, flags, buildings",
  "mood": "one of: dark-dramatic / bright-optimistic / neutral-professional",
  "best_for": ["10-12 VERY SPECIFIC blog topics this image perfectly matches"],
  "avoid_for": ["8-10 blog topics this image should NEVER be used for"]
}

STRICT RULES:
- Coal mining image → best_for ONLY coal/mining topics, NOT general energy
- Oil barrels image → best_for ONLY oil/crude/Iran topics, NOT banking or pharma
- Stock market bull/bear → best_for general stocks, earnings, dividends, Nifty
- Stressed person chart → best_for market crash, bad news, losses ONLY
- Geopolitics/war image → best_for war/conflict/sanctions ONLY
- Technology/globe image → best_for IT stocks, digital, fintech, global markets
- Handshake/partnership → best_for deals, mergers, investments, positive news

Return ONLY the JSON object. No extra text, no markdown, no explanation."""

    response = client.chat.completions.create(
        model="gpt-4o",              # Vision requires gpt-4o specifically
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime};base64,{base64_image}"}
                    },
                    {
                        "type": "text",
                        "text": prompt_text
                    }
                ]
            }
        ],
        response_format={"type": "json_object"}   # Force JSON like cached_model_call
    )

    # ── Cost tracking (mirrors cached_model_call) ─────────────────────────────
    input_tokens  = response.usage.prompt_tokens
    output_tokens = response.usage.completion_tokens
    cost          = (input_tokens / 1_000_000) * 5 + (output_tokens / 1_000_000) * 15
    total_cost   += cost

    print(f"     Input Tokens  : {input_tokens}")
    print(f"     Output Tokens : {output_tokens}")
    print(f"     💰 Call Cost   : ${cost:.6f}")

    return response.choices[0].message.content.strip()


def describe_image(image_path: str) -> dict:
    """
    Calls cached_vision_call and returns parsed JSON dict.
    Cached — same image path won't hit the API twice.
    """
    raw_json = cached_vision_call(image_path)  # ← uses cache
    try:
        return json.loads(raw_json)
    except json.JSONDecodeError:
        print(f"  ⚠️  JSON parse failed for {image_path}, using fallback")
        return {
            "visual": "General financial markets image",
            "mood":   "neutral-professional",
            "best_for":  ["general market news"],
            "avoid_for": []
        }


def generate_for_category(category: str):
    """Generate descriptions for outer/ folder of a category."""

    outer_folder = os.path.join(TEMPLATES_BASE, category, "outer")
    output_file  = os.path.join(TEMPLATES_BASE, category, "image_descriptions.json")

    if not os.path.exists(outer_folder):
        print(f"[SKIP] {category}/outer/ not found — skipping")
        return

    templates = sorted([
        f for f in os.listdir(outer_folder)
        if f.lower().endswith(('.png', '.jpg', '.jpeg'))
    ])

    if not templates:
        print(f"[SKIP] No templates in {category}/outer/")
        return

    print(f"\n[{category.upper()}] Processing {len(templates)} templates...")

    # ── Load existing descriptions (skip already processed images) ────────────
    if os.path.exists(output_file):
        with open(output_file, "r", encoding="utf-8") as f:
            descriptions = json.load(f)
        print(f"  📂 Loaded {len(descriptions)} existing descriptions")
    else:
        descriptions = {}

    for template in templates:
        path = os.path.join(outer_folder, template)
        key  = f"outer/{template}"

        # ── Skip if already described (no re-processing) ──────────────────────
        if key in descriptions:
            print(f"  ⏭️  Skipping {key} (already described)")
            continue

        print(f"  Describing {key}...")

        try:
            desc = describe_image(path)          # ← calls cached_vision_call
            descriptions[key] = desc
            print(f"  ✅ Mood: {desc.get('mood')} | Best for: {', '.join(desc.get('best_for', [])[:3])}...")
        except Exception as e:
            print(f"  ❌ Error: {e}")
            descriptions[key] = {
                "visual":    "General financial markets image",
                "mood":      "neutral-professional",
                "best_for":  ["general market news"],
                "avoid_for": []
            }

    # ── Save descriptions JSON ─────────────────────────────────────────────────
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(descriptions, f, indent=2, ensure_ascii=False)

    print(f"  ✅ Saved → {output_file}")
    print(f"  Total: {len(descriptions)} images described")


def main():
    reset_cost_tracker()

    for category in CATEGORIES:
        generate_for_category(category)

    # ── Final cost summary (mirrors cached_model_call pattern) ────────────────
    print("\n" + "=" * 45)
    print(f"✅  All descriptions generated!")
    print(f"📞  Total API Calls : {get_api_call_count()}")
    print(f"💰  Total Cost      : ${get_total_cost():.6f}")
    print("=" * 45)


if __name__ == "__main__":
    main()