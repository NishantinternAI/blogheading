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
