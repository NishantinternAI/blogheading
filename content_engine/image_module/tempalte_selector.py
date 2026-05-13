# image_module/template_selector.py
import os, hashlib

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

TEMPLATE_BASE = os.path.abspath(
    os.path.join(BASE_DIR, "../templates")
)

FALLBACK_CATEGORY = 'general'

def select_template(category: str, blog_title: str) -> str:

    cat = category.lower().strip()
    folder = os.path.join(TEMPLATE_BASE, cat)

    # fallback
    if not os.path.exists(folder) or not os.listdir(folder):
        folder = os.path.join(TEMPLATE_BASE, FALLBACK_CATEGORY)

    if not os.path.exists(folder):
        raise FileNotFoundError(f"Folder not found: {folder}")

    templates = sorted([
        f for f in os.listdir(folder)
        if f.lower().endswith(('.jpg', '.jpeg', '.png'))
    ])

    if not templates:
        raise FileNotFoundError(f"No templates found in {folder}")

    idx = int(hashlib.md5(blog_title.encode()).hexdigest(), 16) % len(templates)

    return os.path.join(folder, templates[idx])