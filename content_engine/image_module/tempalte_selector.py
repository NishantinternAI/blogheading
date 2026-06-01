import os, hashlib, json
from add_cached import cached_model_call

BASE_DIR          = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_BASE     = os.path.abspath(os.path.join(BASE_DIR, "../templates"))
FALLBACK_CATEGORY = 'general'


def get_templates_from_folder(folder: str) -> list:
    """Returns sorted list of template paths from a folder."""
    if not os.path.exists(folder):
        raise FileNotFoundError(f"Folder not found: {folder}")

    templates = sorted([
        os.path.join(folder, f)
        for f in os.listdir(folder)
        if f.lower().endswith(('.jpg', '.jpeg', '.png'))
    ])

    if not templates:
        raise FileNotFoundError(f"No templates found in: {folder}")

    return templates


def select_template(category: str, blog_title: str) -> str:
    """
    Original function — kept for backward compatibility.
    Selects from flat category folder.
    """
    cat    = category.lower().strip()
    folder = os.path.join(TEMPLATE_BASE, cat)

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


def select_template_pair(category: str, blog_title: str) -> dict:
    """
    MD5 hash based selection — fallback method.
    Selects SAME index template from outer/ and inner/ subfolders.

    outer/ → 640×480 templates  (blog + instagram)
    inner/ → 1920×490 templates (blog_inner only)
    """
    cat          = category.lower().strip()
    outer_folder = os.path.join(TEMPLATE_BASE, cat, "outer")
    inner_folder = os.path.join(TEMPLATE_BASE, cat, "inner")

    # ── Fallback to general if category folder missing ────────
    if not os.path.exists(outer_folder):
        outer_folder = os.path.join(TEMPLATE_BASE, FALLBACK_CATEGORY, "outer")
        print(f"[TEMPLATE] outer fallback → general/outer")

    if not os.path.exists(inner_folder):
        inner_folder = os.path.join(TEMPLATE_BASE, FALLBACK_CATEGORY, "inner")
        print(f"[TEMPLATE] inner fallback → general/inner")

    outer_templates = get_templates_from_folder(outer_folder)
    inner_templates = get_templates_from_folder(inner_folder)

    hash_val    = int(hashlib.md5(blog_title.encode()).hexdigest(), 16)
    outer_index = hash_val % len(outer_templates)
    inner_index = hash_val % len(inner_templates)

    outer_path = outer_templates[outer_index]
    inner_path = inner_templates[inner_index]

    print(f"[TEMPLATE] outer ({len(outer_templates)} available) → {os.path.basename(outer_path)}")
    print(f"[TEMPLATE] inner ({len(inner_templates)} available) → {os.path.basename(inner_path)}")

    return {
        "outer": outer_path,
        "inner": inner_path
    }


def select_template_pair_smart(
    category: str,
    blog_title: str,
    blog_content: str = ""
) -> dict:
    """
    Smart semantic selection using image descriptions.
    Reads image_descriptions.json for the category.
    Sends blog_title + blog_content + descriptions to OpenAI.
    Model picks best matching template index.
    Falls back to MD5 select_template_pair() if:
    - descriptions file missing
    - API call fails
    - invalid response
    """
    cat          = category.lower().strip()
    outer_folder = os.path.join(TEMPLATE_BASE, cat, "outer")
    inner_folder = os.path.join(TEMPLATE_BASE, cat, "inner")

    # ── Fallback to general if category folder missing ────────
    if not os.path.exists(outer_folder):
        print(f"[TEMPLATE] {cat}/outer not found → fallback to general")
        cat          = FALLBACK_CATEGORY
        outer_folder = os.path.join(TEMPLATE_BASE, cat, "outer")
        inner_folder = os.path.join(TEMPLATE_BASE, cat, "inner")

    # ── Load descriptions for selected category ───────────────
    descriptions_file = os.path.join(TEMPLATE_BASE, cat, "image_descriptions.json")

    if not os.path.exists(descriptions_file):
        print(f"[TEMPLATE] No descriptions file for '{cat}' → MD5 fallback")
        return select_template_pair(category, blog_title)

    with open(descriptions_file, "r", encoding="utf-8") as f:
        descriptions = json.load(f)

    if not descriptions:
        print(f"[TEMPLATE] Empty descriptions for '{cat}' → MD5 fallback")
        return select_template_pair(category, blog_title)

    outer_templates = get_templates_from_folder(outer_folder)
    inner_templates = get_templates_from_folder(inner_folder)

    # ── Build descriptions list for prompt ────────────────────
    desc_list = ""
    for i, tpl in enumerate(outer_templates):
        fname = f"outer/{os.path.basename(tpl)}"
        desc  = descriptions.get(fname, "General financial markets image")
        desc_list += f"{i+1}. {fname}: {desc}\n"

    # ── Prompt — returns JSON for cached_model_call ───────────
    prompt = f"""You are selecting the best background image template for a financial blog post.

Blog Title: {blog_title}
Blog Content: {blog_content}

Available templates with descriptions:
{desc_list}

SELECTION RULES:
- Read the "Best for" field of each template carefully
- Read the "Avoid for" field — if blog topic matches Avoid for, SKIP that template
- Pick the template whose "Best for" most closely matches the blog topic
- If blog is about dividends → pick stock market or handshake template
- If blog is about earnings → pick stock market or general finance template
- If blog is about coal specifically → pick coal template
- If blog is about oil/crude specifically → pick oil template
- If blog is about war/geopolitics → pick geopolitics template
- If blog is about IT/tech → pick technology template
- If blog is about gold → pick gold template
- If blog is about IPO → pick NSE template
- If blog is about banking/RBI → pick banking template
- Default to stock market template if unsure

# IMPORTANT:  Analyze carefully and pick the BEST match.

Return ONLY valid JSON with the correct template number:
{{"template_number": <number between 1 and {len(outer_templates)}>}}"""


    try:
        raw      = cached_model_call(prompt)
        data     = json.loads(raw)
        selected = int(data.get("template_number", 1)) - 1

        # ── Clamp to valid range ──────────────────────────────
        selected = max(0, min(selected, len(outer_templates) - 1))

        outer_path = outer_templates[selected]
        inner_path = inner_templates[selected]

        print(f"[TEMPLATE SMART] Selected index {selected+1} → {os.path.basename(outer_path)}")
        print(f"[TEMPLATE] outer → {os.path.basename(outer_path)}")
        print(f"[TEMPLATE] inner → {os.path.basename(inner_path)}")

        return {"outer": outer_path, "inner": inner_path}

    except Exception as e:
        print(f"[TEMPLATE] Smart selection failed: {e} → MD5 fallback")
        return select_template_pair(category, blog_title)



