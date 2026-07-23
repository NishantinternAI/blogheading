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
    WEEKLY_TEMPLATE_COUNT,
    build_weekly_assignments,
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

if failures:
    print(f"\n{len(failures)} FAILURE(S)")
    raise SystemExit(1)
print("\nAll cases passed.")
