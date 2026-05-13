import json
import os

def save_output(data: dict, filename: str = "testing_webp_output1.json"):
    """
    Appends a single blog entry to the output JSON file.
    Deduplicates based on top-level 'Blog_Title'.
    
    Args:
        data: Single blog dict matching the pipeline output structure
        filename: Target file inside /output/
    """
    os.makedirs("output", exist_ok=True)
    filepath = f"output/{filename}"

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

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=4, ensure_ascii=False)  # ensure_ascii=False preserves ₹ symbols

    print(f"[SAVED] '{data.get('Blog_Title')}'")
    return True
