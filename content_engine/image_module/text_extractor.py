# image_module/text_extractor.py
import openai, json, os
from add_cached import cached_model_call
def extract_image_text(blog_title: str, blog_content: str, category: str) -> dict:
    """
    Returns: { headline, subtext, tag }
    """
    prompt = f"""
    Extract overlay text for a social media image.
    Return ONLY valid JSON with no extra text.
    Blog title: {blog_title}
    Category: {category}
    Content excerpt: {blog_content[:300]}
    Return exactly:
    {{
     "headline": "max 6 words, punchy, no punctuation",
     "subtext": "max 10 words, supporting context",
     "tag": "ONE WORD, all caps e.g. FINANCE / BREAKING / GUIDE"
    }}
    """
    raw=cached_model_call(prompt)
    return json.loads(raw)


   
   

