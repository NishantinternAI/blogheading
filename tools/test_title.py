# test_title.py
# Run: python tools/test_title.py
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # repo root
# cached_model_call.cache_clear() removed 2026-07-24 -- cached_model_call is no
# longer memoized (the @lru_cache it used to have was removed), so there's no
# cache left to clear.

from generators.blog_generator import generate_blog

test_item = {
    "Blog_Title": "Exide Industries Limited - Ex-Date: 03-Jul-2026",
    "Blog_Content": "SERIES:EQ |PURPOSE:DIVIDEND - RS 2.00 PER SHARE |RECORD DATE:03-Jul-2026"
}

result = generate_blog(test_item)
print("Blog Title :", result["Blog_Title"])
print("Meta Title :", result["Meta_Title"])
print("Meta Desc  :", result["Meta_Description"])