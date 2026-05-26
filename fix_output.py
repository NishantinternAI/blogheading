import json
import re

OUTPUT_FILE = "output/output.json"

def clean_newlines(text):
    if not isinstance(text, str):
        return text
    return text.replace('\\n\\n', '').replace('\\n', '')

def clean_obj(obj):
    if isinstance(obj, str):
        return clean_newlines(obj)
    if isinstance(obj, dict):
        return {k: clean_obj(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [clean_obj(i) for i in obj]
    return obj

# ── Load existing output.json ─────────────────────────────────
with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

print(f"Total blogs found: {len(data)}")

# ── Clean all fields recursively ──────────────────────────────
cleaned_data = clean_obj(data)

# ── Save back ─────────────────────────────────────────────────
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(cleaned_data, f, ensure_ascii=False, indent=2)

print(f"✅ Done — {len(cleaned_data)} blogs cleaned in output.json")