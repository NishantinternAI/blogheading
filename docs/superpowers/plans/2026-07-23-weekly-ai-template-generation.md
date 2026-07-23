# Weekly AI Template Generation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Automatically generate a small weekly batch of AI background templates (via OpenAI's Batch API), expand the template pool into topic-specific categories, and route each blog to the right category by classifying its title/content — so the stale 2-category, 17-image pool stops being reused for every single blog regardless of topic.

**Architecture:** Three independent, individually-shippable pieces: (1) a pure `classify_template_category()` function wired into the 3 existing image-selection call sites in `core/pipeline.py`, safe to ship alone because `select_template_pair_smart()` already falls back to `general` for any category folder that doesn't exist yet; (2) a new `template_batch_generator.py` module holding category prompts/pad-colors, round-robin assignment, Batch API request building, and pad-resize-without-cropping logic; (3) two APScheduler cron jobs in `scheduler.py` (Saturday submit, Monday fetch-or-fallback) that drive (2).

**Tech Stack:** Python, `openai` SDK (`gpt-image-1.5`, Batch API), Pillow (`PIL.Image`) for resize/pad, APScheduler (already used by `scheduler.py`), stdlib `json`/`tempfile`/`datetime`.

## Global Constraints

- `ipo_compositor.py` and the IPO fixed-template path are never touched — IPO stays a separate, always-fixed-template flow due to its traffic priority.
- `USE_AI_IMAGES` / per-blog `ai_image_generator.py` generation is never touched — stays gated off in production.
- The news-fetch `category` parameter (`filter_by_country_and_category`, decides which articles get fetched) is never repurposed — only the image/template-selection call sites change.
- Template pool only grows — no deletion of existing or newly generated templates.
- Model is `gpt-image-1.5`, not `gpt-image-1` (`gpt-image-1` deprecates 2026-10-23; 1.5 is also cheaper at the same resolutions and is Batch-API-supported).
- `WEEKLY_TEMPLATE_COUNT = 10` (hard cap 15 if ever changed).
- Categories: `finance, general, dividend, rbi_policy, gold_oil, tech, banking` (7 total — `ipo` is deliberately excluded).
- Outer templates are exactly 640×480 px, inner templates are exactly 1920×490 px (compositor.py uses templates as-is, no resize at composite time) — every generated file must match these dimensions exactly.
- Atomic writes for any shared JSON state file (`tempfile.NamedTemporaryFile` + `os.replace`), matching the pattern already used in `publishing/webflow_poster.py::save_webflow_url` — never the non-atomic pattern flagged as a known gotcha for `storage/save_output.py`.

---

### Task 1: `classify_template_category()` in `template_selector.py`

**Files:**
- Modify: `content_engine/image_module/template_selector.py`
- Test: `tools/test_classify_template_category.py`

**Interfaces:**
- Produces: `classify_template_category(title: str, content: str = "") -> str`, returning one of `"dividend" | "rbi_policy" | "gold_oil" | "tech" | "banking" | "finance" | "general"`.
- Produces: `TEMPLATE_CATEGORIES` — the ordered list `["finance", "general", "dividend", "rbi_policy", "gold_oil", "tech", "banking"]`, importable by Task 4's round-robin logic.

- [ ] **Step 1: Write the failing test**

Create `tools/test_classify_template_category.py`:

```python
"""
Ad-hoc verification script for classify_template_category() -- run directly
with `python tools/test_classify_template_category.py`, matching this repo's
existing convention of no pytest/unittest runner.
"""
from content_engine.image_module.template_selector import classify_template_category

CASES = [
    ("Company announces dividend payout and record date", "", "dividend"),
    ("RBI hikes repo rate to curb inflation", "", "rbi_policy"),
    ("Gold prices surge to record high", "", "gold_oil"),
    ("Crude oil prices tumble on demand worries", "", "gold_oil"),
    ("TCS Q1 results beat estimates", "", "tech"),
    ("HDFC Bank posts record profit", "", "banking"),
    ("Sensex surges 500 points on strong buying", "", "finance"),
    ("Rupee weakens against dollar amid forex outflows", "", "finance"),
    ("Local temple festival draws record crowds", "", "general"),
]

failures = []
for title, content, expected in CASES:
    actual = classify_template_category(title, content)
    status = "OK" if actual == expected else "FAIL"
    if actual != expected:
        failures.append((title, expected, actual))
    print(f"[{status}] {title!r} -> {actual} (expected {expected})")

if failures:
    print(f"\n{len(failures)} FAILURE(S)")
    raise SystemExit(1)
print("\nAll cases passed.")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python tools/test_classify_template_category.py`
Expected: `ImportError: cannot import name 'classify_template_category'` (function doesn't exist yet).

- [ ] **Step 3: Write minimal implementation**

In `content_engine/image_module/template_selector.py`, add after the existing `FALLBACK_CATEGORY = 'general'` line (do not remove any existing code):

```python
TEMPLATE_CATEGORIES = [
    "finance", "general", "dividend", "rbi_policy", "gold_oil", "tech", "banking",
]

# Priority order matters: checked top to bottom, first match wins. A story
# mentioning both "RBI" and "bank" should land on the more specific
# rbi_policy bucket rather than the broader banking one.
_CATEGORY_KEYWORD_ORDER = ["dividend", "rbi_policy", "gold_oil", "tech", "banking", "finance"]

_CATEGORY_KEYWORDS = {
    "dividend": ["dividend", "ex-date", "record date", "payout", "buyback"],
    "rbi_policy": ["rbi", "reserve bank", "monetary", "inflation", "cpi", "repo"],
    "gold_oil": [
        "gold", "silver", "bullion", "precious metal",
        "oil", "crude", "petroleum", "fuel", "ongc", "bpcl", "hpcl",
    ],
    "tech": ["infosys", "tcs", "wipro", "it sector", "tech", "software"],
    "banking": [
        "psu bank", "private bank", "npa", "credit growth", "sbi",
        "hdfc bank", "icici bank", "axis bank", "kotak", "bank", "banking",
    ],
    "finance": [
        "surge", "rally", "jump", "rise", "gain", "profit", "high", "record",
        "soar", "climb", "positive", "boost",
        "fall", "crash", "drop", "decline", "loss", "slump", "plunge", "sink",
        "dip", "weak", "negative",
        "rupee", "dollar", "forex", "currency", "usd",
    ],
}


def classify_template_category(title: str, content: str = "") -> str:
    """
    Classify a blog's title/content into one of TEMPLATE_CATEGORIES using
    the same keyword bins as ai_image_generator.build_image_prompt(). Falls
    back to "general" if nothing matches.
    """
    combined = f"{title or ''} {content or ''}".lower()
    for category in _CATEGORY_KEYWORD_ORDER:
        if any(keyword in combined for keyword in _CATEGORY_KEYWORDS[category]):
            return category
    return "general"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python tools/test_classify_template_category.py`
Expected: `All cases passed.` (exit code 0)

- [ ] **Step 5: Commit**

```bash
git add content_engine/image_module/template_selector.py tools/test_classify_template_category.py
git commit -m "feat: add classify_template_category() for per-blog template category routing"
```

---

### Task 2: Wire the classifier into `core/pipeline.py`

**Files:**
- Modify: `core/pipeline.py:1373-1384` (Zerodha fallback branch), `core/pipeline.py:1552-1556` (IPO-template-missing fallback branch), `core/pipeline.py:1603-1613` (main non-IPO branch)

**Interfaces:**
- Consumes: `classify_template_category(title, content=None) -> str` from Task 1.

- [ ] **Step 1: Import the classifier**

At the top of `core/pipeline.py`, find the existing import block:

```python
from content_engine.image_module.template_selector import (
    select_template_pair,
    select_template_pair_smart
)
```

Change it to:

```python
from content_engine.image_module.template_selector import (
    select_template_pair,
    select_template_pair_smart,
    classify_template_category,
)
```

- [ ] **Step 2: Wire call site 1 — Zerodha fallback branch (lines ~1373-1384)**

Find:

```python
            image_text = extract_image_text(
                img_title,
                img_content,
                category.upper()
            )
            final_item["image_text"] = image_text

            template_pair  = select_template_pair_smart(
                category,
                img_title,
                img_content
            )
```

Replace with:

```python
            template_category = classify_template_category(img_title, img_content)
            image_text = extract_image_text(
                img_title,
                img_content,
                template_category.upper()
            )
            final_item["image_text"] = image_text

            template_pair  = select_template_pair_smart(
                template_category,
                img_title,
                img_content
            )
```

- [ ] **Step 3: Wire call site 2 — IPO-template-missing fallback (lines ~1550-1556)**

Find:

```python
                ipo_text      = _extract_ipo_image_text(final_item)
                _ipo_img_title, _ipo_img_content = _imaging_text_source(final_item)
                template_pair = _select_template_pair_smart(
                    final_category,   # was "priority" — no templates/priority/ folder, so it fell to random MD5 every time
                    _ipo_img_title,
                    _ipo_img_content
                )
```

Replace with:

```python
                ipo_text      = _extract_ipo_image_text(final_item)
                _ipo_img_title, _ipo_img_content = _imaging_text_source(final_item)
                _ipo_template_category = classify_template_category(_ipo_img_title, _ipo_img_content)
                template_pair = _select_template_pair_smart(
                    _ipo_template_category,
                    _ipo_img_title,
                    _ipo_img_content
                )
```

- [ ] **Step 4: Wire call site 3 — main non-IPO branch (lines ~1601-1613)**

Find:

```python
            img_title, img_content = _imaging_text_source(final_item)

            final_item["image_text"] = _extract_image_text(
                img_title,
                img_content,
                final_category.upper()
            )

            template_pair  = _select_template_pair_smart(
                final_category,
                img_title,
                img_content
            )
```

Replace with:

```python
            img_title, img_content = _imaging_text_source(final_item)
            template_category = classify_template_category(img_title, img_content)

            final_item["image_text"] = _extract_image_text(
                img_title,
                img_content,
                template_category.upper()
            )

            template_pair  = _select_template_pair_smart(
                template_category,
                img_title,
                img_content
            )
```

- [ ] **Step 5: Verify with a syntax + smoke check**

Run: `python -c "import ast; ast.parse(open('core/pipeline.py', encoding='utf-8').read())" && echo OK`
Expected: `OK`

Run: `python -c "from core.pipeline import run_pipeline; print('import OK')"`
Expected: `import OK` (confirms the edited file still imports cleanly with `config.py` present; this does not execute the pipeline).

- [ ] **Step 6: Commit**

```bash
git add core/pipeline.py
git commit -m "feat: route template selection through classify_template_category() instead of the news-fetch category"
```

---

### Task 3: Category prompts, pad-colors, and no-crop resize helper

**Files:**
- Create: `content_engine/image_module/template_batch_generator.py`
- Test: `tools/test_template_batch_generator.py`

**Interfaces:**
- Consumes: `TEMPLATE_CATEGORIES` from Task 1 (`content_engine.image_module.template_selector`).
- Produces: `CATEGORY_PROMPTS: dict` (category -> `{emotion, visual_scene, color_mood, pad_color, best_for, avoid_for}`), `TARGET_SIZES = {"outer": (640, 480), "inner": (1920, 490)}`, `contain_fit_and_pad(master: PIL.Image.Image, target_size: tuple, pad_color: tuple) -> PIL.Image.Image`, `build_category_prompt(category: str) -> str`.

- [ ] **Step 1: Write the failing test**

Create `tools/test_template_batch_generator.py`:

```python
"""
Ad-hoc verification script for template_batch_generator.py -- run directly
with `python tools/test_template_batch_generator.py`. No network calls are
made anywhere in this script.
"""
from PIL import Image
from content_engine.image_module.template_batch_generator import (
    CATEGORY_PROMPTS,
    TARGET_SIZES,
    contain_fit_and_pad,
    build_category_prompt,
)
from content_engine.image_module.template_selector import TEMPLATE_CATEGORIES

failures = []


def check(label, condition):
    status = "OK" if condition else "FAIL"
    print(f"[{status}] {label}")
    if not condition:
        failures.append(label)


# -- CATEGORY_PROMPTS covers every category, with the required keys --------
for category in TEMPLATE_CATEGORIES:
    check(f"CATEGORY_PROMPTS has '{category}'", category in CATEGORY_PROMPTS)
    info = CATEGORY_PROMPTS.get(category, {})
    for key in ("emotion", "visual_scene", "color_mood", "pad_color", "best_for", "avoid_for"):
        check(f"'{category}' has key '{key}'", key in info)
    pad = info.get("pad_color")
    check(
        f"'{category}' pad_color is a valid RGB tuple",
        isinstance(pad, tuple) and len(pad) == 3 and all(0 <= c <= 255 for c in pad),
    )

# -- build_category_prompt() produces non-empty, category-specific text ----
prompt = build_category_prompt("dividend")
check("build_category_prompt('dividend') is non-empty", bool(prompt.strip()))
check("dividend prompt mentions dividend visual scene", "dividend" in prompt.lower() or "cheque" in prompt.lower())

# -- contain_fit_and_pad(): output is exactly the target size, no crop -----
master = Image.new("RGB", (1536, 1024), (200, 50, 50))

outer = contain_fit_and_pad(master, TARGET_SIZES["outer"], (0, 0, 0))
check("outer output size == (640, 480)", outer.size == (640, 480))

inner = contain_fit_and_pad(master, TARGET_SIZES["inner"], (0, 0, 0))
check("inner output size == (1920, 490)", inner.size == (1920, 490))

# A very wide inner target vs a ~3:2 master means most of the canvas is
# padding -- confirm the corner pixels are the pad color (i.e. padded, not
# stretched/cropped over).
check("inner top-left corner is pad color", inner.getpixel((0, 0)) == (0, 0, 0))

if failures:
    print(f"\n{len(failures)} FAILURE(S)")
    raise SystemExit(1)
print("\nAll cases passed.")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python tools/test_template_batch_generator.py`
Expected: `ModuleNotFoundError: No module named 'content_engine.image_module.template_batch_generator'`

- [ ] **Step 3: Write minimal implementation**

Create `content_engine/image_module/template_batch_generator.py`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python tools/test_template_batch_generator.py`
Expected: `All cases passed.` (exit code 0)

- [ ] **Step 5: Commit**

```bash
git add content_engine/image_module/template_batch_generator.py tools/test_template_batch_generator.py
git commit -m "feat: add category prompts and no-crop pad-resize helper for weekly template generation"
```

---

### Task 4: Round-robin weekly category assignment

**Files:**
- Modify: `content_engine/image_module/template_batch_generator.py`
- Modify: `tools/test_template_batch_generator.py`

**Interfaces:**
- Produces: `WEEKLY_TEMPLATE_COUNT = 10`, `build_weekly_assignments(iso_week: int, count: int = WEEKLY_TEMPLATE_COUNT) -> list[dict]`, each dict `{"category": str, "idx": int}`.

- [ ] **Step 1: Write the failing test**

Append to `tools/test_template_batch_generator.py` (before the `if failures:` block at the end -- move that block down, or just insert above it):

```python
from content_engine.image_module.template_batch_generator import (
    WEEKLY_TEMPLATE_COUNT,
    build_weekly_assignments,
)

# -- build_weekly_assignments(): correct count, valid categories, rotates --
week0 = build_weekly_assignments(iso_week=0)
check("week0 has WEEKLY_TEMPLATE_COUNT assignments", len(week0) == WEEKLY_TEMPLATE_COUNT)
check(
    "every week0 assignment has a valid category",
    all(a["category"] in TEMPLATE_CATEGORIES for a in week0),
)
check(
    "week0 per-category idx values start at 0 and are contiguous",
    all(
        sorted(a["idx"] for a in week0 if a["category"] == cat) == list(range(count))
        for cat, count in (
            (c, sum(1 for a in week0 if a["category"] == c)) for c in TEMPLATE_CATEGORIES
        )
    ),
)

week1 = build_weekly_assignments(iso_week=1)
check(
    "week0 and week1 start on a different category (rotation)",
    week0[0]["category"] != week1[0]["category"],
)

week7 = build_weekly_assignments(iso_week=7)  # 7 categories -> full cycle
check(
    "a full 7-week cycle returns to the same starting category",
    week0[0]["category"] == week7[0]["category"],
)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python tools/test_template_batch_generator.py`
Expected: `ImportError: cannot import name 'build_weekly_assignments'`

- [ ] **Step 3: Write minimal implementation**

Append to `content_engine/image_module/template_batch_generator.py`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python tools/test_template_batch_generator.py`
Expected: `All cases passed.` (exit code 0)

- [ ] **Step 5: Commit**

```bash
git add content_engine/image_module/template_batch_generator.py tools/test_template_batch_generator.py
git commit -m "feat: add round-robin weekly category assignment for template batches"
```

---

### Task 5: Batch API request lines + `image_descriptions.json` writer

**Files:**
- Modify: `content_engine/image_module/template_batch_generator.py`
- Modify: `tools/test_template_batch_generator.py`

**Interfaces:**
- Consumes: `CATEGORY_PROMPTS`, `build_category_prompt()` from Task 3; `TEMPLATE_BASE` (new module-level constant, `content_engine/templates/`, same path `template_selector.TEMPLATE_BASE` resolves to).
- Produces: `build_batch_input_lines(assignments: list) -> list[dict]`, `append_template_description(category: str, filename: str) -> None`.

- [ ] **Step 1: Write the failing test**

Append to `tools/test_template_batch_generator.py` (before the closing `if failures:` block):

```python
import json
import os
import tempfile

from content_engine.image_module.template_batch_generator import (
    build_batch_input_lines,
    append_template_description,
)
import content_engine.image_module.template_batch_generator as tbg

# -- build_batch_input_lines(): one line per assignment, correct shape -----
assignments = build_weekly_assignments(iso_week=0, count=3)
lines = build_batch_input_lines(assignments)
check("build_batch_input_lines returns one line per assignment", len(lines) == 3)
first = lines[0]
check("line has custom_id encoding category+idx", first["custom_id"] == f"{assignments[0]['category']}__{assignments[0]['idx']}")
check("line targets the images endpoint", first["url"] == "/v1/images/generations")
check("line body uses gpt-image-1.5", first["body"]["model"] == "gpt-image-1.5")
check("line body size is the master size", first["body"]["size"] == "1536x1024")
check("every line is JSON-serializable", all(json.dumps(l) for l in lines))

# -- append_template_description(): writes/creates image_descriptions.json -
with tempfile.TemporaryDirectory() as tmp_base:
    original_base = tbg.TEMPLATE_BASE
    tbg.TEMPLATE_BASE = tmp_base
    try:
        append_template_description("dividend", "ai_dividend_20260801_0.png")
        desc_path = os.path.join(tmp_base, "dividend", "image_descriptions.json")
        check("image_descriptions.json created", os.path.exists(desc_path))
        with open(desc_path, encoding="utf-8") as f:
            data = json.load(f)
        key = "outer/ai_dividend_20260801_0.png"
        check("new entry present under outer/<filename>", key in data)
        check("entry has visual/mood/best_for/avoid_for keys", all(
            k in data[key] for k in ("visual", "mood", "best_for", "avoid_for")
        ))
    finally:
        tbg.TEMPLATE_BASE = original_base
```

This adds a second `import os` to the test file -- harmless (Python no-ops a
repeated import), and keeps this snippet copy-pasteable on its own without
having to cross-reference Task 3's version of the file.

- [ ] **Step 2: Run test to verify it fails**

Run: `python tools/test_template_batch_generator.py`
Expected: `ImportError: cannot import name 'build_batch_input_lines'`

- [ ] **Step 3: Write minimal implementation**

Append to `content_engine/image_module/template_batch_generator.py` (near the top, after the `MASTER_SIZE` constant, add `TEMPLATE_BASE`; then add the two functions at the end of the file):

```python
TEMPLATE_BASE = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "templates")
)
```

```python
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
```

Add `import json` at the top of `content_engine/image_module/template_batch_generator.py` alongside the existing `import os`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python tools/test_template_batch_generator.py`
Expected: `All cases passed.` (exit code 0)

- [ ] **Step 5: Commit**

```bash
git add content_engine/image_module/template_batch_generator.py tools/test_template_batch_generator.py
git commit -m "feat: add Batch API request builder and image_descriptions.json writer"
```

---

### Task 6: `submit_weekly_batch()` with tracking file + overlap guard

**Files:**
- Modify: `content_engine/image_module/template_batch_generator.py`
- Test: `tools/test_submit_weekly_batch.py`

**Interfaces:**
- Consumes: `build_weekly_assignments()`, `build_batch_input_lines()` from Tasks 4-5.
- Produces: `BATCH_STATE_PATH` (module constant, `output/template_batch_state.json`), `_load_state() -> dict`, `_save_state(state: dict) -> None`, `submit_weekly_batch(openai_client=None) -> dict`.

- [ ] **Step 1: Write the failing test**

Create `tools/test_submit_weekly_batch.py`:

```python
"""
Ad-hoc verification script for submit_weekly_batch() -- run directly with
`python tools/test_submit_weekly_batch.py`. Uses a stub OpenAI client so no
real network calls or costs occur.
"""
import json
import os
import tempfile

import content_engine.image_module.template_batch_generator as tbg

failures = []


def check(label, condition):
    status = "OK" if condition else "FAIL"
    print(f"[{status}] {label}")
    if not condition:
        failures.append(label)


class _FakeFiles:
    def create(self, file, purpose):
        return type("Obj", (), {"id": "file_abc123"})()


class _FakeBatches:
    def __init__(self):
        self.create_calls = []

    def create(self, input_file_id, endpoint, completion_window):
        self.create_calls.append((input_file_id, endpoint, completion_window))
        return type("Obj", (), {"id": "batch_xyz789"})()


class _FakeClient:
    def __init__(self):
        self.files = _FakeFiles()
        self.batches = _FakeBatches()


with tempfile.TemporaryDirectory() as tmp_dir:
    original_state_path = tbg.BATCH_STATE_PATH
    tbg.BATCH_STATE_PATH = os.path.join(tmp_dir, "template_batch_state.json")
    try:
        # -- First submit: should go through and write state -------------
        fake_client = _FakeClient()
        result = tbg.submit_weekly_batch(openai_client=fake_client)
        check("first submit is not skipped", "skipped" not in result)
        check("batch_id recorded", result.get("batch_id") == "batch_xyz789")
        check("status is 'submitted'", result.get("status") == "submitted")
        check(
            "category_assignments has WEEKLY_TEMPLATE_COUNT entries",
            len(result.get("category_assignments", [])) == tbg.WEEKLY_TEMPLATE_COUNT,
        )
        check("exactly one batches.create call made", len(fake_client.batches.create_calls) == 1)
        check("state file was written", os.path.exists(tbg.BATCH_STATE_PATH))
        with open(tbg.BATCH_STATE_PATH, encoding="utf-8") as f:
            on_disk = json.load(f)
        check("on-disk state matches returned state", on_disk == result)

        # -- Second submit while still 'submitted': should be skipped -----
        fake_client_2 = _FakeClient()
        result_2 = tbg.submit_weekly_batch(openai_client=fake_client_2)
        check("second submit is skipped", "skipped" in result_2)
        check(
            "second submit made no batches.create call",
            len(fake_client_2.batches.create_calls) == 0,
        )
    finally:
        tbg.BATCH_STATE_PATH = original_state_path

if failures:
    print(f"\n{len(failures)} FAILURE(S)")
    raise SystemExit(1)
print("\nAll cases passed.")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python tools/test_submit_weekly_batch.py`
Expected: `AttributeError: module 'content_engine.image_module.template_batch_generator' has no attribute 'BATCH_STATE_PATH'`

- [ ] **Step 3: Write minimal implementation**

Add to the top of `content_engine/image_module/template_batch_generator.py`, alongside the existing `import os`/`import json`:

```python
import tempfile
from datetime import datetime, timezone, timedelta

from openai import OpenAI

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

BATCH_STATE_PATH = os.path.abspath(
    os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "..", "output",
        "template_batch_state.json",
    )
)
```

Append to the end of the file:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python tools/test_submit_weekly_batch.py`
Expected: `All cases passed.` (exit code 0)

- [ ] **Step 5: Commit**

```bash
git add content_engine/image_module/template_batch_generator.py tools/test_submit_weekly_batch.py
git commit -m "feat: add submit_weekly_batch() with tracking file and overlap guard"
```

---

### Task 7: `fetch_completed_batch()` — completed / in-progress / failed-with-fallback

**Files:**
- Modify: `content_engine/image_module/template_batch_generator.py`
- Test: `tools/test_fetch_completed_batch.py`

**Interfaces:**
- Consumes: `_load_state()`, `_save_state()`, `CATEGORY_PROMPTS`, `contain_fit_and_pad()`, `TARGET_SIZES`, `append_template_description()`, `build_category_prompt()` from earlier tasks.
- Produces: `fetch_completed_batch(openai_client=None) -> dict`.

- [ ] **Step 1: Write the failing test**

Create `tools/test_fetch_completed_batch.py`:

```python
"""
Ad-hoc verification script for fetch_completed_batch() -- run directly with
`python tools/test_fetch_completed_batch.py`. Uses a stub OpenAI client and
a locally-generated PNG (no network calls) for both the batch-output and
synchronous-fallback code paths.
"""
import base64
import io
import json
import os
import tempfile

from PIL import Image

import content_engine.image_module.template_batch_generator as tbg

failures = []


def check(label, condition):
    status = "OK" if condition else "FAIL"
    print(f"[{status}] {label}")
    if not condition:
        failures.append(label)


def _fake_b64_image():
    buf = io.BytesIO()
    Image.new("RGB", (1536, 1024), (10, 100, 200)).save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


ASSIGNMENTS = [
    {"category": "dividend", "idx": 0},
    {"category": "tech", "idx": 0},
]


def _seed_state(tmp_base):
    state = {
        "batch_id": "batch_xyz789",
        "submitted_at": "2026-07-25T02:00:00+00:00",
        "category_assignments": ASSIGNMENTS,
        "status": "submitted",
    }
    tbg._save_state(state)


class _FakeOutputFile:
    def __init__(self, text):
        self.text = text


class _FakeFiles:
    def __init__(self, output_text):
        self._output_text = output_text

    def content(self, file_id):
        return _FakeOutputFile(self._output_text)


class _FakeBatches:
    def __init__(self, status):
        self.status_to_report = status

    def retrieve(self, batch_id):
        return type("Obj", (), {
            "id": batch_id,
            "status": self.status_to_report,
            "output_file_id": "outfile_1",
        })()


class _FakeImages:
    def __init__(self):
        self.generate_calls = 0

    def generate(self, model, prompt, size, quality, n):
        self.generate_calls += 1
        return type("Obj", (), {
            "data": [type("D", (), {"b64_json": _fake_b64_image()})()]
        })()


class _FakeClient:
    def __init__(self, status, output_lines=None):
        self.batches = _FakeBatches(status)
        self.files = _FakeFiles(output_lines or "")
        self.images = _FakeImages()


with tempfile.TemporaryDirectory() as tmp_dir:
    original_state_path = tbg.BATCH_STATE_PATH
    original_template_base = tbg.TEMPLATE_BASE
    tbg.BATCH_STATE_PATH = os.path.join(tmp_dir, "state", "template_batch_state.json")
    tbg.TEMPLATE_BASE = os.path.join(tmp_dir, "templates")
    try:
        # -- No active batch: no-op ---------------------------------------
        result = tbg.fetch_completed_batch(openai_client=_FakeClient("completed"))
        check("no-op when no active batch", "noop" in result)

        # -- Completed: downloads, pads, saves, marks 'fetched' ------------
        _seed_state(tmp_dir)
        b64 = _fake_b64_image()
        output_lines = "\n".join(
            json.dumps({
                "custom_id": f"{a['category']}__{a['idx']}",
                "response": {"status_code": 200, "body": {"data": [{"b64_json": b64}]}},
            })
            for a in ASSIGNMENTS
        )
        fake_client = _FakeClient("completed", output_lines)
        result = tbg.fetch_completed_batch(openai_client=fake_client)
        check("completed batch reports fetched", "fetched" in result)
        check("2 files saved", len(result["fetched"]) == 2)
        for a in ASSIGNMENTS:
            outer_dir = os.path.join(tbg.TEMPLATE_BASE, a["category"], "outer")
            inner_dir = os.path.join(tbg.TEMPLATE_BASE, a["category"], "inner")
            check(f"{a['category']} outer dir has 1 file", len(os.listdir(outer_dir)) == 1)
            check(f"{a['category']} inner dir has 1 file", len(os.listdir(inner_dir)) == 1)
            outer_file = os.path.join(outer_dir, os.listdir(outer_dir)[0])
            check(f"{a['category']} outer image is 640x480", Image.open(outer_file).size == (640, 480))
        state_after = tbg._load_state()
        check("state marked 'fetched'", state_after["status"] == "fetched")

        # -- In progress: leaves state as 'submitted' ----------------------
        _seed_state(tmp_dir)
        result = tbg.fetch_completed_batch(openai_client=_FakeClient("in_progress"))
        check("in-progress batch reports in_progress", "in_progress" in result)
        check("state remains 'submitted'", tbg._load_state()["status"] == "submitted")

        # -- Failed: falls back to synchronous generation ------------------
        _seed_state(tmp_dir)
        fallback_client = _FakeClient("failed")
        result = tbg.fetch_completed_batch(openai_client=fallback_client)
        check("failed batch reports fetched_via_fallback", "fetched_via_fallback" in result)
        check(
            "images.generate called once per assignment",
            fallback_client.images.generate_calls == len(ASSIGNMENTS),
        )
        check("state marked 'fetched_via_fallback'", tbg._load_state()["status"] == "fetched_via_fallback")
    finally:
        tbg.BATCH_STATE_PATH = original_state_path
        tbg.TEMPLATE_BASE = original_template_base

if failures:
    print(f"\n{len(failures)} FAILURE(S)")
    raise SystemExit(1)
print("\nAll cases passed.")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python tools/test_fetch_completed_batch.py`
Expected: `AttributeError: module 'content_engine.image_module.template_batch_generator' has no attribute 'fetch_completed_batch'`

- [ ] **Step 3: Write minimal implementation**

Append to `content_engine/image_module/template_batch_generator.py`:

```python
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
```

Add `import base64` at the top of `content_engine/image_module/template_batch_generator.py` alongside the existing imports.

- [ ] **Step 4: Run test to verify it passes**

Run: `python tools/test_fetch_completed_batch.py`
Expected: `All cases passed.` (exit code 0)

- [ ] **Step 5: Commit**

```bash
git add content_engine/image_module/template_batch_generator.py tools/test_fetch_completed_batch.py
git commit -m "feat: add fetch_completed_batch() with completed/in-progress/failed-fallback handling"
```

---

### Task 8: Wire Saturday-submit / Monday-fetch cron jobs into `scheduler.py`

**Files:**
- Modify: `scheduler.py`

**Interfaces:**
- Consumes: `submit_weekly_batch()`, `fetch_completed_batch()` from Tasks 6-7.

- [ ] **Step 1: Add the import**

In `scheduler.py`, add alongside the existing imports:

```python
from content_engine.image_module.template_batch_generator import (
    submit_weekly_batch,
    fetch_completed_batch,
)
```

- [ ] **Step 2: Add the two cron jobs**

After the existing `pipeline_job()` function definition (before the `if __name__ == "__main__":` block), add:

```python
@scheduler.scheduled_job('cron', day_of_week='sat', hour=2, minute=0, timezone='Asia/Kolkata')
def weekly_template_submit_job():
    """Saturday 02:00 IST -- submits this week's AI template-pool batch."""
    print("\n[TEMPLATE BATCH] Submitting weekly template batch...")
    submit_weekly_batch()


@scheduler.scheduled_job('cron', day_of_week='mon', hour=9, minute=0, timezone='Asia/Kolkata')
def weekly_template_fetch_job():
    """Monday 09:00 IST -- fetches (or falls back on) this week's batch."""
    print("\n[TEMPLATE BATCH] Checking weekly template batch...")
    fetch_completed_batch()
```

- [ ] **Step 3: Verify**

Run: `python -c "import ast; ast.parse(open('scheduler.py', encoding='utf-8').read())" && echo OK`
Expected: `OK`

Run (requires `config.py`/`.env` present, per this repo's standing requirement for anything that imports `core.pipeline`):

```bash
python -c "
import scheduler
job_ids = sorted(j.id for j in scheduler.scheduler.get_jobs())
assert 'weekly_template_submit_job' in job_ids, job_ids
assert 'weekly_template_fetch_job' in job_ids, job_ids
print('Registered jobs:', job_ids)
"
```

Expected: prints a list of job ids including `weekly_template_submit_job` and `weekly_template_fetch_job`, no assertion error.

- [ ] **Step 4: Commit**

```bash
git add scheduler.py
git commit -m "feat: schedule Saturday template-batch submit and Monday fetch-or-fallback jobs"
```

---

## Manual follow-up (not part of automated tests, costs real API usage)

Before relying on this in production, run one real end-to-end submit against
the actual OpenAI API (`python -c "from content_engine.image_module.template_batch_generator import submit_weekly_batch; print(submit_weekly_batch())"`)
to confirm the installed `openai` SDK version (`2.40.0` at plan-writing time)
actually accepts `endpoint="/v1/images/generations"` on `client.batches.create()`
— this Batch API surface for image models was only announced 2026-02-21, and the
plan's automated tests stub the client entirely, so this is the one thing they
cannot verify. Then either wait ~24h or manually poll
`fetch_completed_batch()` to confirm the completed-batch download/pad/save
path against real output data (the exact JSON shape used above for the
completed-branch test — `response.body.data[0].b64_json` — is inferred from
OpenAI's Batch API pattern for other endpoints and should be confirmed
against a real output file).
