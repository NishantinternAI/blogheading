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
import base64
import json
import os
import tempfile
from datetime import datetime, timezone, timedelta

from openai import OpenAI
from PIL import Image

from content_engine.image_module.template_selector import TEMPLATE_CATEGORIES

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

BATCH_STATE_PATH = os.path.abspath(
    os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "..", "output",
        "template_batch_state.json",
    )
)

TARGET_SIZES = {
    "outer": (640, 480),
    "inner": (1920, 490),
}

MASTER_SIZE = "1536x1024"

TEMPLATE_BASE = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "templates")
)

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


def build_batch_input_lines(assignments: list) -> list:
    """
    Returns a list of JSON-serializable dicts, one per OpenAI Batch API
    request line, for POST /v1/images/generations via gpt-image-1.5.
    `custom_id` encodes "<category>__<idx>" so fetch_completed_batch() can
    map each output image back to its assignment.
    """
    lines = []
    for a in assignments:
        custom_id = f"{a['category']}__{a['idx']}"
        lines.append({
            "custom_id": custom_id,
            "method": "POST",
            "url": "/v1/images/generations",
            "body": {
                "model": "gpt-image-1.5",
                "prompt": build_category_prompt(a["category"]),
                "size": MASTER_SIZE,
                "quality": "medium",
                "n": 1,
            },
        })
    return lines


def append_template_description(category: str, filename: str) -> None:
    """
    Append a description entry for a newly generated outer template into
    content_engine/templates/<category>/image_descriptions.json, creating
    the category folder and/or file if missing. Schema matches the existing
    image_descriptions.json files (visual/mood/best_for/avoid_for), read by
    template_selector.select_template_pair_smart().
    """
    info = CATEGORY_PROMPTS[category]
    category_dir = os.path.join(TEMPLATE_BASE, category)
    os.makedirs(category_dir, exist_ok=True)
    desc_path = os.path.join(category_dir, "image_descriptions.json")

    if os.path.exists(desc_path):
        with open(desc_path, "r", encoding="utf-8") as f:
            descriptions = json.load(f)
    else:
        descriptions = {}

    descriptions[f"outer/{filename}"] = {
        "visual": info["visual_scene"],
        "mood": info["color_mood"],
        "best_for": info["best_for"],
        "avoid_for": info["avoid_for"],
    }

    with open(desc_path, "w", encoding="utf-8") as f:
        json.dump(descriptions, f, ensure_ascii=False, indent=2)


def _load_state() -> dict:
    if not os.path.exists(BATCH_STATE_PATH):
        return {}
    with open(BATCH_STATE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_state(state: dict) -> None:
    dir_name = os.path.dirname(BATCH_STATE_PATH)
    os.makedirs(dir_name, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", dir=dir_name, delete=False, suffix=".tmp", encoding="utf-8"
    ) as tmp:
        json.dump(state, tmp, ensure_ascii=False, indent=2)
        tmp_path = tmp.name
    os.replace(tmp_path, BATCH_STATE_PATH)


def submit_weekly_batch(openai_client=None) -> dict:
    """
    Builds this week's category assignments, writes a Batch API .jsonl
    input file, uploads it, creates the batch job, and records it in
    BATCH_STATE_PATH with status "submitted".

    Skips (returns {"skipped": "..."}) if a previous batch is still
    "submitted" (not yet resolved by fetch_completed_batch()) -- avoids
    overlapping batches. `openai_client` is injectable for tests; defaults
    to the module-level `client`.
    """
    oc = openai_client or client
    state = _load_state()
    if state.get("status") == "submitted":
        msg = f"Batch {state.get('batch_id')} still submitted — skipping this week"
        print(f"[TEMPLATE BATCH] {msg}")
        return {"skipped": msg}

    ist = timezone(timedelta(hours=5, minutes=30))
    iso_week = datetime.now(ist).isocalendar()[1]
    assignments = build_weekly_assignments(iso_week)
    lines = build_batch_input_lines(assignments)

    batch_dir = os.path.dirname(BATCH_STATE_PATH)
    os.makedirs(batch_dir, exist_ok=True)
    input_path = os.path.join(batch_dir, "template_batch_input.jsonl")
    with open(input_path, "w", encoding="utf-8") as f:
        for line in lines:
            f.write(json.dumps(line, ensure_ascii=False) + "\n")

    with open(input_path, "rb") as f:
        uploaded = oc.files.create(file=f, purpose="batch")
    batch = oc.batches.create(
        input_file_id=uploaded.id,
        endpoint="/v1/images/generations",
        completion_window="24h",
    )

    new_state = {
        "batch_id": batch.id,
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        "category_assignments": assignments,
        "status": "submitted",
    }
    _save_state(new_state)
    print(f"[TEMPLATE BATCH] Submitted batch {batch.id} for {len(assignments)} templates")
    return new_state


def _decode_and_store_image(b64_json: str, category: str, idx: int, batchdate: str) -> str:
    """
    Decodes one generated master image, pad-resizes it into outer
    (640x480) and inner (1920x490) crops using that category's pad color,
    saves both under content_engine/templates/<category>/{outer,inner}/,
    appends a description entry, and returns the filename written (same
    filename used for both the outer and inner file).
    """
    import io

    info = CATEGORY_PROMPTS[category]
    master_bytes = base64.b64decode(b64_json)
    master = Image.open(io.BytesIO(master_bytes)).convert("RGB")

    outer_dir = os.path.join(TEMPLATE_BASE, category, "outer")
    inner_dir = os.path.join(TEMPLATE_BASE, category, "inner")
    os.makedirs(outer_dir, exist_ok=True)
    os.makedirs(inner_dir, exist_ok=True)

    filename = f"ai_{category}_{batchdate}_{idx}.png"
    outer_img = contain_fit_and_pad(master, TARGET_SIZES["outer"], info["pad_color"])
    inner_img = contain_fit_and_pad(master, TARGET_SIZES["inner"], info["pad_color"])
    outer_img.save(os.path.join(outer_dir, filename))
    inner_img.save(os.path.join(inner_dir, filename))

    append_template_description(category, filename)
    return filename


def fetch_completed_batch(openai_client=None) -> dict:
    """
    Checks the currently-tracked batch's status:
      - "completed"                    -> downloads output, decodes+pads+
                                           saves each image, marks state
                                           "fetched".
      - in-progress/validating         -> leaves state as "submitted",
                                           returns {"in_progress": status}.
      - failed/expired/cancelled       -> falls back to synchronous
                                           generation for the same
                                           assignments, marks state
                                           "fetched_via_fallback".
    Returns {"noop": "..."} if there's no active ("submitted") batch.
    """
    oc = openai_client or client
    state = _load_state()
    if state.get("status") != "submitted":
        msg = "No active batch to fetch"
        print(f"[TEMPLATE BATCH] {msg}")
        return {"noop": msg}

    batch = oc.batches.retrieve(state["batch_id"])
    batchdate = state["submitted_at"][:10].replace("-", "")

    if batch.status == "completed":
        output_file = oc.files.content(batch.output_file_id)
        saved = []
        for line in output_file.text.splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            category, idx_str = record["custom_id"].split("__")
            idx = int(idx_str)
            b64_json = record["response"]["body"]["data"][0]["b64_json"]
            filename = _decode_and_store_image(b64_json, category, idx, batchdate)
            saved.append(filename)
        state["status"] = "fetched"
        _save_state(state)
        print(f"[TEMPLATE BATCH] Fetched and saved {len(saved)} templates")
        return {"fetched": saved}

    if batch.status in ("failed", "expired", "cancelled"):
        print(f"[TEMPLATE BATCH] Batch {batch.status} — falling back to synchronous generation")
        saved = []
        for a in state["category_assignments"]:
            response = oc.images.generate(
                model="gpt-image-1.5",
                prompt=build_category_prompt(a["category"]),
                size=MASTER_SIZE,
                quality="medium",
                n=1,
            )
            filename = _decode_and_store_image(
                response.data[0].b64_json, a["category"], a["idx"], batchdate
            )
            saved.append(filename)
        state["status"] = "fetched_via_fallback"
        _save_state(state)
        print(f"[TEMPLATE BATCH] Fallback-generated {len(saved)} templates")
        return {"fetched_via_fallback": saved}

    print(f"[TEMPLATE BATCH] Batch still {batch.status} — checking again next run")
    return {"in_progress": batch.status}
