"""
template_batch_generator.py
----------------------------
Weekly AI template-pool refresher. Generates a small batch of reusable
background templates via OpenAI's Batch API (gpt-image-1.5), submitted
Saturday and fetched Monday by scheduler.py's cron jobs. See
docs/superpowers/specs/2026-07-23-weekly-ai-template-generation-design.md.

Not wired into the live per-blog pipeline -- this only grows the on-disk
template pool that content_engine/image_module/template_selector.py already
reads from.
"""
import os

from PIL import Image

from content_engine.image_module.template_selector import TEMPLATE_CATEGORIES

TARGET_SIZES = {
    "outer": (640, 480),
    "inner": (1920, 490),
}

MASTER_SIZE = "1536x1024"

# Static per-category art direction + a curated pad color (a precomputed
# stand-in for "derive a color from the color_mood string" -- simpler and
# more reliable than parsing color names out of free text at runtime) and
# image_descriptions.json metadata (schema matches the existing
# content_engine/templates/*/image_descriptions.json files).
CATEGORY_PROMPTS = {
    "dividend": {
        "emotion": "wealth, reward, passive income",
        "visual_scene": (
            "golden coins and currency notes falling like rain, a happy "
            "investor holding a dividend cheque, BSE ticker showing stock "
            "gains, warm golden light"
        ),
        "color_mood": "rich gold and deep green on dark background",
        "pad_color": (11, 46, 33),
        "best_for": [
            "dividend announcements", "dividend payout news",
            "buyback announcements", "ex-date and record date coverage",
            "passive income investing stories",
        ],
        "avoid_for": [
            "IPO listing news", "RBI policy announcements",
            "IT sector earnings", "crude oil price movements",
            "banking sector regulation news",
        ],
    },
    "rbi_policy": {
        "emotion": "authority, policy power, economic control",
        "visual_scene": (
            "RBI building facade, rupee symbol ₹ large and bold, "
            "interest rate arrows, Indian currency notes, serious "
            "financial tension"
        ),
        "color_mood": "deep navy blue and gold",
        "pad_color": (10, 20, 45),
        "best_for": [
            "RBI monetary policy announcements", "repo rate changes",
            "inflation and CPI data", "interest rate outlook stories",
            "central bank commentary",
        ],
        "avoid_for": [
            "dividend payout news", "IPO listings",
            "gold and silver price stories", "IT sector earnings",
            "crude oil price movements",
        ],
    },
    "gold_oil": {
        "emotion": "value and energy, safe haven meets market power",
        "visual_scene": (
            "gleaming gold bars stacked high beside oil barrels and a "
            "crude oil price chart, refinery silhouette at sunset"
        ),
        "color_mood": "warm gold and deep orange on black",
        "pad_color": (46, 24, 6),
        "best_for": [
            "gold and silver price movements", "bullion market stories",
            "crude oil and petroleum price stories",
            "ONGC/BPCL/HPCL company news", "commodity market coverage",
        ],
        "avoid_for": [
            "RBI policy announcements", "IT sector earnings",
            "dividend payout news", "banking sector regulation news",
            "IPO listings",
        ],
    },
    "tech": {
        "emotion": "innovation, digital power, market leadership",
        "visual_scene": (
            "modern tech office, multiple trading screens showing code and "
            "charts, Indian IT professionals, digital data flowing"
        ),
        "color_mood": "electric blue and white on dark background",
        "pad_color": (6, 18, 40),
        "best_for": [
            "IT sector earnings", "Infosys/TCS/Wipro company news",
            "software industry trends", "technology sector market movements",
        ],
        "avoid_for": [
            "gold and silver price movements", "crude oil price stories",
            "RBI policy announcements", "dividend payout news",
            "banking sector regulation news",
        ],
    },
    "banking": {
        "emotion": "trust, stability, institutional strength",
        "visual_scene": (
            "grand bank building facade, secure vault door, banker's desk "
            "with ledgers and a laptop showing growth charts"
        ),
        "color_mood": "deep navy and silver on dark background",
        "pad_color": (13, 20, 32),
        "best_for": [
            "banking sector regulation news", "PSU and private bank earnings",
            "NPA and credit growth stories",
            "SBI/HDFC Bank/ICICI Bank/Axis Bank company news",
        ],
        "avoid_for": [
            "IT sector earnings", "gold and silver price movements",
            "crude oil price stories", "IPO listings",
        ],
    },
    "finance": {
        "emotion": "market intelligence, financial insight",
        "visual_scene": (
            "professional trader analyzing multiple screens, Indian stock "
            "market data, NSE/BSE trading floor, financial charts and graphs"
        ),
        "color_mood": "deep blue and gold on dark background",
        "pad_color": (9, 13, 32),
        "best_for": [
            "general market movement stories", "Sensex/Nifty coverage",
            "rupee-dollar/forex stories",
            "broad bullish or bearish market sentiment",
        ],
        "avoid_for": [
            "dividend payout news", "RBI policy announcements",
            "gold and silver price movements", "IT sector earnings",
            "banking sector regulation news",
        ],
    },
    "general": {
        "emotion": "market intelligence, general financial insight",
        "visual_scene": (
            "wide shot of a modern Indian financial district skyline at "
            "dusk with subtle stock chart overlays"
        ),
        "color_mood": "neutral navy and soft gold",
        "pad_color": (16, 21, 36),
        "best_for": [
            "general financial news",
            "stories that don't fit a specific sector",
        ],
        "avoid_for": [],
    },
}


def build_category_prompt(category: str) -> str:
    """Build a generic, reusable-background image prompt for a template
    category (no per-blog title/content -- these are not tied to one
    article)."""
    info = CATEGORY_PROMPTS[category]
    return f"""
Create a powerful, story-driven financial background image for Indian investors.

EMOTION TO CONVEY: {info['emotion']}

MAIN VISUAL SCENE:
{info['visual_scene']}

COLOR MOOD:
{info['color_mood']}

COMPOSITION RULES:
- ONE strong hero element takes 60% of frame
- Indian financial market context -- ₹ symbol, BSE/NSE, Mumbai skyline where relevant
- Dramatic depth -- sharp foreground, atmospheric background
- Cinematic lighting -- strong directional light on hero element

QUALITY:
- Photorealistic, magazine cover standard
- Ultra sharp, high detail on hero element
- NO text overlay
- NO watermarks
- NO logos
- Landscape format, reusable as a generic background (not tied to one specific news story)
""".strip()


def contain_fit_and_pad(master: "Image.Image", target_size: tuple, pad_color: tuple) -> "Image.Image":
    """
    Resize `master` to fit entirely within `target_size` preserving aspect
    ratio (no cropping, no content loss), then paste it centered onto a
    `target_size` canvas filled with `pad_color`.
    """
    target_w, target_h = target_size
    src_w, src_h = master.size
    scale = min(target_w / src_w, target_h / src_h)
    new_w = max(1, round(src_w * scale))
    new_h = max(1, round(src_h * scale))
    resized = master.resize((new_w, new_h), Image.LANCZOS)

    canvas = Image.new("RGB", target_size, pad_color)
    paste_x = (target_w - new_w) // 2
    paste_y = (target_h - new_h) // 2
    canvas.paste(resized, (paste_x, paste_y))
    return canvas


WEEKLY_TEMPLATE_COUNT = 10


def build_weekly_assignments(iso_week: int, count: int = WEEKLY_TEMPLATE_COUNT) -> list:
    """
    Returns `count` dicts of {"category": str, "idx": int} -- one per
    template to generate this week -- round-robining through
    TEMPLATE_CATEGORIES starting at an offset derived from `iso_week`, so
    the "extra" templates (count % len(TEMPLATE_CATEGORIES)) land on a
    different subset of categories each week instead of always the same
    ones. `idx` is a per-category counter *within this batch*, used to keep
    generated filenames unique when a category appears more than once.
    """
    n = len(TEMPLATE_CATEGORIES)
    offset = iso_week % n
    per_category_counter = {}
    assignments = []
    for i in range(count):
        category = TEMPLATE_CATEGORIES[(offset + i) % n]
        idx = per_category_counter.get(category, 0)
        per_category_counter[category] = idx + 1
        assignments.append({"category": category, "idx": idx})
    return assignments
