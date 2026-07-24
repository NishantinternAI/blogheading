import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def save_output(data: dict, filename: str = "output.json"):
    """
    Appends a single blog entry to the output JSON file.
    Deduplicates based on top-level 'Blog_Title'.

    Args:
        data: Single blog dict matching the pipeline output structure
        filename: Target file inside /output/
    """
    output_dir = os.path.join(BASE_DIR, "output")
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, filename)

    # Load existing entries
    existing = []
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            try:
                existing = json.load(f)
            except json.JSONDecodeError:
                existing = []

    # Deduplicate on top-level Blog_Title
    existing_titles = {entry.get("Blog_Title", "").strip().lower() for entry in existing}
    incoming_title = data.get("Blog_Title", "").strip().lower()

    if not incoming_title:
        print("[WARNING] Blog_Title is missing or empty — skipping save.")
        return False

    if incoming_title in existing_titles:
        print(f"[SKIPPED] Duplicate: '{data.get('Blog_Title')}'")
        return False

    existing.append(data)

    # Write to a temp file then atomically replace, so a crash/kill mid-write
    # can't leave output.json (the dedup index) truncated/corrupt.
    tmp_path = filepath + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=4, ensure_ascii=False)  # ensure_ascii=False preserves ₹ symbols
    os.replace(tmp_path, filepath)

    print(f"[SAVED] '{data.get('Blog_Title')}'")
    return True
