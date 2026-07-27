"""
backfill_template_descriptions.py -- One-off fix for templates generated
before describe_generated_image() existed: every template in a weekly batch
was getting the exact same category-level visual/mood text (idx was never
folded into the prompt or the description), leaving
select_template_pair_smart()'s LLM picker with no way to tell same-category
templates apart.

Re-describes every outer/ai_<category>_<date>_<idx>.png template already on
disk via vision and rewrites its image_descriptions.json entry in place.
Run manually: python tools/backfill_template_descriptions.py [date_prefix]
date_prefix defaults to today's IST date (YYYYMMDD); pass e.g. 20260727 to
target a specific batch, or "all" to re-describe every ai_*.png template
regardless of date.
"""
import sys
from datetime import datetime, timezone, timedelta

from PIL import Image

from content_engine.image_module.template_batch_generator import (
    TEMPLATE_BASE,
    client,
    describe_generated_image,
    append_template_description,
)
from content_engine.image_module.template_selector import TEMPLATE_CATEGORIES

import os


def main():
    if len(sys.argv) > 1:
        date_prefix = sys.argv[1]
    else:
        ist = timezone(timedelta(hours=5, minutes=30))
        date_prefix = datetime.now(ist).strftime("%Y%m%d")

    match_all = date_prefix == "all"
    print(f"[BACKFILL] Target: {'all ai_*.png templates' if match_all else date_prefix}")

    updated = 0
    for category in TEMPLATE_CATEGORIES:
        outer_dir = os.path.join(TEMPLATE_BASE, category, "outer")
        if not os.path.isdir(outer_dir):
            continue
        for filename in sorted(os.listdir(outer_dir)):
            if not filename.startswith("ai_") or not filename.lower().endswith(".png"):
                continue
            if not match_all and date_prefix not in filename:
                continue

            path = os.path.join(outer_dir, filename)
            master = Image.open(path).convert("RGB")
            visual_mood = describe_generated_image(client, master, category)
            append_template_description(category, filename, visual_mood)
            print(f"[BACKFILL] {category}/{filename} -> {visual_mood['visual'][:70]}...")
            updated += 1

    print(f"[BACKFILL] Done -- {updated} templates re-described")


if __name__ == "__main__":
    main()
