import os
import base64
import re
import unicodedata
from openai import OpenAI

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))




# ── Build prompt ──────────────────────────────────────────────
# def build_image_prompt(blog_title: str, blog_content: str, image_type: str) -> str:
#     content_preview = blog_content if blog_content else ""

#     if image_type in ("blog_outer", "blog_inner"):
#         return f"""
# Create a professional stock market and financial news image.

# Topic: {blog_title}
# Context: {content_preview}

# Style requirements:
# - Professional financial news look
# - Modern, clean, corporate feel
# - NO text overlay on the image
# - NO watermarks
# - High quality, sharp details
# - Suitable for a financial blog header
# """
#     else:  # instagram
#         return f"""
# Create a bold, eye-catching square financial news image for Instagram.

# Topic: {blog_title}
# Context: {content_preview}

# Style requirements:
# - Stock market / trading themed
# - Modern and dynamic composition
# - Square format optimized for Instagram
# - NO text overlay on the image
# - NO watermarks
# - High contrast, vibrant colors
# - Professional financial news aesthetic
# """




# def build_image_prompt(blog_title: str, blog_content: str, image_type: str) -> str:

#     # Extract first 200 chars of content for context
#     content_preview = blog_content if blog_content else ""

#     if image_type in ("blog_outer", "blog_inner"):
#         return f"""
# Create a highly engaging, visually striking financial news image for Indian stock market investors.

# Topic: {blog_title}
# Context: {content_preview}

# Visual storytelling requirements:
# - The image must INSTANTLY communicate the emotion of the news
#   * If market is falling → show red charts, worried traders, downward arrows
#   * If market is rising → show green charts, confident traders, upward arrows
#   * If dividend/bonus → show coins, currency notes, wealth symbols
#   * If IPO news → show stock exchange floor, crowd, excitement
#   * If RBI/policy news → show RBI building, rupee symbol, banking visuals
#   * If gold/silver news → show gold bars, coins, precious metals
#   * If IT/tech news → show tech screens, digital charts, modern office

# Composition:
# - Strong focal point that draws eye immediately
# - Dynamic lighting — bright highlights on key elements
# - Depth and layers — foreground subject + background story
# - Indian financial context — rupee symbol ₹, Mumbai skyline

# Color mood:
# - Bullish news → vibrant greens and golds on dark background
# - Bearish news → deep reds and oranges on dark background
# - Neutral/dividend → rich blues and golds, premium feel

# Style:
# - Photorealistic, magazine cover quality
# - NO text overlay on the image
# - NO watermarks
# - NO logos
# - Ultra sharp, high detail
# - Professional financial journalism aesthetic
# - Cinematic lighting
# """

#     else:  # instagram
#         return f"""
# Create a bold, thumb-stopping square financial news image for Instagram — must make someone stop scrolling instantly.

# Topic: {blog_title}
# Context: {content_preview}

# Hook requirements:
# - ONE powerful visual element that tells the whole story
# - Dramatic, high contrast composition
# - Emotionally charged — viewer should FEEL the market movement

# Visual storytelling:
# - If market crash/fall → dramatic red downward chart, panic energy
# - If market rally → explosive green upward chart, euphoric energy  
# - If dividend/payout → gold coins raining, wealth abundance
# - If IPO/listing → spotlight on stock ticker, crowd excitement
# - If inflation/RBI → currency notes, economic tension
# - If gold/silver → gleaming precious metals, luxury feel

# Composition for Instagram square:
# - Bold center focus — 60% of frame
# - Blurred dynamic background for depth
# - Strong color contrast — dark background with bright subject
# - Indian market context — ₹ symbol, Mumbai financial district

# Color palette:
# - Bullish → electric green + gold on black
# - Bearish → crimson red + orange on black
# - Neutral → royal blue + gold on dark navy

# Style:
# - Ultra dramatic cinematic look
# - Magazine advertisement quality
# - NO text overlay
# - NO watermarks
# - NO logos
# - Square format 1:1
# - Maximum visual impact
# """


def build_image_prompt(blog_title: str, blog_content: str, image_type: str) -> str:

    # ── Extract key signals from title + content ──────────────
    title_lower   = blog_title.lower()
    content_lower = blog_content.lower() if blog_content else ""
    combined      = title_lower + " " + content_lower

    # ── Detect market direction ───────────────────────────────
    is_bullish  = any(w in combined for w in ["surge", "rally", "jump", "rise", "gain", "profit", "high", "record", "soar", "climb", "up", "positive", "boost"])
    is_bearish  = any(w in combined for w in ["fall", "crash", "drop", "decline", "loss", "slump", "down", "plunge", "sink", "dip", "weak", "negative"])
    is_dividend = any(w in combined for w in ["dividend", "ex-date", "record date", "payout", "buyback"])
    is_ipo      = any(w in combined for w in ["ipo", "listing", "subscribed", "issue price", "allotment"])
    is_rbi      = any(w in combined for w in ["rbi", "reserve bank", "rate", "monetary", "inflation", "cpi", "repo"])
    is_gold     = any(w in combined for w in ["gold", "silver", "bullion", "precious metal"])
    is_oil      = any(w in combined for w in ["oil", "crude", "petroleum", "fuel", "ongc", "bpcl", "hpcl"])
    is_it       = any(w in combined for w in ["infosys", "tcs", "wipro", "it sector", "tech", "software"])
    is_rupee    = any(w in combined for w in ["rupee", "dollar", "forex", "currency", "usd"])

    # ── Build emotion + visual based on detected signals ──────
    if is_dividend or "ex-date" in combined:
        emotion       = "wealth, reward, passive income"
        visual_scene  = "golden coins and currency notes falling like rain, a happy investor holding dividend cheque, BSE ticker showing stock gains, warm golden light"
        color_mood    = "rich gold and deep green on dark background — premium wealth feel"

    elif is_ipo:
        emotion       = "excitement, opportunity, new beginning"
        visual_scene  = "crowded stock exchange floor with excited traders, IPO listing board glowing green, confetti, NSE/BSE building facade, upward ticker"
        color_mood    = "electric blue and bright green on dark background — energy and excitement"

    elif is_rbi:
        emotion       = "authority, policy power, economic control"
        visual_scene  = "RBI building facade, rupee symbol ₹ large and bold, interest rate arrows, Indian currency notes, serious financial tension"
        color_mood    = "deep navy blue and gold — authority and trust"

    elif is_gold:
        emotion       = "value, luxury, safe haven"
        visual_scene  = "gleaming gold bars stacked high, gold coins, silver ingots, precious metal market board, Indian jewelry market context"
        color_mood    = "warm gold and silver on black — luxury and value"

    elif is_oil:
        emotion       = "energy, power, market impact"
        visual_scene  = "oil barrels, crude oil price chart, refinery silhouette at sunset, ONGC/oil company visual, price spike indicator"
        color_mood    = "deep orange and red on dark background — energy and power"

    elif is_it:
        emotion       = "innovation, digital power, market leadership"
        visual_scene  = "modern tech office, multiple trading screens showing code and charts, Indian IT professionals, Infosys/TCS campus visual, digital data flowing"
        color_mood    = "electric blue and white on dark background — technology and precision"

    elif is_rupee:
        emotion       = "currency tension, economic pressure, forex battle"
        visual_scene  = "rupee vs dollar tug of war, forex trading screen, Indian currency notes, exchange rate board, Mumbai financial district"
        color_mood    = "orange and green on dark background — Indian economic identity"

    elif is_bullish:
        emotion       = "confidence, growth, winning"
        visual_scene  = "strong upward green chart arrow breaking through ceiling, celebrating traders on BSE floor, Sensex/Nifty board showing gains, bull statue"
        color_mood    = "vibrant green and gold on black — confidence and growth"

    elif is_bearish:
        emotion       = "urgency, caution, market fear"
        visual_scene  = "dramatic red downward chart crashing, worried traders watching screens, Sensex board showing losses, bear market shadow"
        color_mood    = "deep red and dark orange on black — urgency and caution"

    else:
        emotion       = "market intelligence, financial insight"
        visual_scene  = "professional trader analyzing multiple screens, Indian stock market data, NSE/BSE trading floor, financial charts and graphs"
        color_mood    = "deep blue and gold on dark background — intelligence and trust"

    # ── Key facts to visually communicate ────────────────────
    key_facts = f"Title: {blog_title}\nContext: {blog_content if blog_content else ''}"

    if image_type in ("blog_outer", "blog_inner"):
        return f"""
Create a powerful, story-driven financial news image that INSTANTLY communicates this specific story to Indian investors.

STORY TO TELL:
{key_facts}

EMOTION TO CONVEY: {emotion}

MAIN VISUAL SCENE:
{visual_scene}

COLOR MOOD:
{color_mood}

COMPOSITION RULES:
- ONE strong hero element takes 60% of frame — viewer knows the story in 1 second
- Supporting elements tell the background story
- Indian financial market context — ₹ symbol, BSE/NSE, Mumbai skyline where relevant
- Dramatic depth — sharp foreground, atmospheric background
- Cinematic lighting — strong directional light on hero element

QUALITY:
- Photorealistic, magazine cover standard
- Ultra sharp, high detail on hero element
- NO text overlay
- NO watermarks
- NO logos
- Landscape format for blog header
"""

    else:  # instagram
        return f"""
Create a thumb-stopping, scroll-halting square Instagram image that makes someone stop and read this story.

STORY TO TELL:
{key_facts}

EMOTION TO CONVEY: {emotion}

MAIN VISUAL SCENE:
{visual_scene}

COLOR MOOD:
{color_mood}

INSTAGRAM COMPOSITION:
- SINGLE powerful image — one look tells the whole story
- Dead center composition — hero element fills frame
- Extreme contrast between subject and background
- Indian market identity — ₹, BSE/NSE, Mumbai where relevant
- Bokeh background — sharp subject, blurred depth
- Dramatic shadows and highlights — cinematic feel

QUALITY:
- Maximum visual impact in square 1:1 format
- Photorealistic, advertisement quality
- NO text overlay
- NO watermarks  
- NO logos
- Must work as standalone image without any caption
"""

# ── Save image in all required formats ───────────────────────
def save_image_formats(image_bytes: bytes, paths: dict, image_type: str):
    from PIL import Image
    import io

    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")

    saved = {}

    if image_type == "blog_outer":
        # Thumbnail outer → 640x480
        resized = img.resize((640, 480), Image.LANCZOS)
        os.makedirs(os.path.dirname(paths["jpg"]),  exist_ok=True)
        os.makedirs(os.path.dirname(paths["webp"]), exist_ok=True)
        resized.save(paths["jpg"],  "JPEG")
        resized.save(paths["webp"], "WEBP")
        print(f"[AI IMAGE] blog_outer JPG  → {paths['jpg']}")
        print(f"[AI IMAGE] blog_outer WebP → {paths['webp']}")
        saved = {"jpg": paths["jpg"], "webp": paths["webp"]}

    elif image_type == "blog_inner":
        # Thumbnail inner → 1920x490
        resized = img.resize((1920, 490), Image.LANCZOS)
        os.makedirs(os.path.dirname(paths["jpg"]),  exist_ok=True)
        os.makedirs(os.path.dirname(paths["webp"]), exist_ok=True)
        resized.save(paths["jpg"],  "JPEG")
        resized.save(paths["webp"], "WEBP")
        print(f"[AI IMAGE] blog_inner JPG  → {paths['jpg']}")
        print(f"[AI IMAGE] blog_inner WebP → {paths['webp']}")
        saved = {"jpg": paths["jpg"], "webp": paths["webp"]}

    elif image_type == "instagram":
        # Instagram → 1080x1080
        resized = img.resize((1080, 1080), Image.LANCZOS)
        os.makedirs(os.path.dirname(paths["jpg"]),  exist_ok=True)
        os.makedirs(os.path.dirname(paths["webp"]), exist_ok=True)
        resized.save(paths["jpg"],  "JPEG", quality=98, subsampling=0)
        resized.save(paths["webp"], "WEBP", quality=92, method=6)
        print(f"[AI IMAGE] instagram JPG  → {paths['jpg']}")
        print(f"[AI IMAGE] instagram WebP → {paths['webp']}")
        saved = {"jpg": paths["jpg"], "webp": paths["webp"]}

    return saved


# ── Single API call → reuse bytes for blog_outer + blog_inner ─
def generate_ai_image(
    blog_title:        str,
    blog_content:      str,
    blog_outer_paths:  dict,
    blog_inner_paths:  dict,
    instagram_paths:   dict,
    quality:           str = "medium"
) -> dict:
    """
    Makes 2 API calls:
      Call 1 → blog image (reused for outer 640x480 + inner 1920x490)
      Call 2 → instagram image (1080x1080)

    Returns:
    {
      "blog_outer":  {"jpg": "...", "webp": "..."},
      "blog_inner":  {"jpg": "...", "webp": "..."},
      "instagram":   {"jpg": "...", "webp": "..."}
    }
    """

    # ── Call 1 — Blog image (reuse for outer + inner) ─────────
    print(f"[AI IMAGE] Generating blog image: {blog_title[:50]}...")

    blog_prompt  = build_image_prompt(blog_title, blog_content, "blog_outer")
    blog_response = client.images.generate(
        model   = "gpt-image-1",
        prompt  = blog_prompt,
        size    = "1536x1024",   # landscape — best for blog
        quality = quality,
        n       = 1,
    )
    blog_bytes = base64.b64decode(blog_response.data[0].b64_json)

    # Save outer (640x480) from same blog bytes
    outer_saved = save_image_formats(blog_bytes, blog_outer_paths, "blog_outer")

    # Save inner (1920x490) from same blog bytes
    inner_saved = save_image_formats(blog_bytes, blog_inner_paths, "blog_inner")

    # ── Call 2 — Instagram image ──────────────────────────────
    print(f"[AI IMAGE] Generating instagram image: {blog_title[:50]}...")

    insta_prompt   = build_image_prompt(blog_title, blog_content, "instagram")
    insta_response = client.images.generate(
        model   = "gpt-image-1",
        prompt  = insta_prompt,
        size    = "1024x1024",   # square — best for instagram
        quality = quality,
        n       = 1,
    )
    insta_bytes  = base64.b64decode(insta_response.data[0].b64_json)
    insta_saved  = save_image_formats(insta_bytes, instagram_paths, "instagram")

    return {
        "blog_outer": outer_saved,
        "blog_inner": inner_saved,
        "instagram":  insta_saved
    }