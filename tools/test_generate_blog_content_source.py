"""
Ad-hoc verification script for generators/blog_generator.py's generate_blog() --
run directly with `python tools/test_generate_blog_content_source.py`.

Covers the fix where generate_blog() must prefer an item's already-verified
Blog_Content (e.g. from google_trends_business, whose Blog_Links is an
unresolvable Google News redirect token) over re-fetching via
fetch_via_websearch(Blog_Links), while leaving the existing re-fetch
behavior for the 9 other sources (whose Blog_Content is a short RSS
snippet that doesn't clear assess_quality()'s "thin" bar) unchanged.

No live network/API calls -- cached_model_call, extract_keywords, and
get_keyword_volumes are all patched on generators.blog_generator's
namespace (they are imported at module-load time, so they must be
patched there, not on their origin modules).
"""
from unittest.mock import patch

import generators.blog_generator as blog_generator_module

failures = []


def check(label, condition):
    status = "OK" if condition else "FAIL"
    print(f"[{status}] {label}")
    if not condition:
        failures.append(label)


_RICH_CONTENT = " ".join(["IDFC First Bank shares rose sharply today after strong quarterly results."] * 30)  # >=150 words


def _fake_keyword_data(content):
    # Records what content it was called with, for assertion.
    _fake_keyword_data.last_content = content
    return {"primary_keyword": "idfc first bank share", "secondary_keywords": ["idfc bank stock"]}


def _fake_volume_data(primary, secondary):
    return {
        "primary_keyword": {"original": primary, "google_keyword": primary, "volume": 1000},
        "secondary_keywords": [{"original": s, "google_keyword": s, "volume": 500} for s in secondary],
    }


def _fake_model_call(*args, **kwargs):
    return '{"Blog_Title": "fake title", "Blog_Content": "<p>fake</p>"}'


# ── Case 1: substantial pre-verified Blog_Content -> no re-fetch ──────────
def test_uses_existing_blog_content_when_substantial():
    item = {
        "Blog_Links": "https://news.google.com/rss/articles/CBMifakeToken",
        "Blog_Content": _RICH_CONTENT,
        "source": "google_trends_business",
    }
    with patch.object(blog_generator_module, "fetch_via_websearch") as mock_fetch, \
         patch.object(blog_generator_module, "extract_keywords", side_effect=_fake_keyword_data) as mock_extract, \
         patch.object(blog_generator_module, "get_keyword_volumes", side_effect=_fake_volume_data), \
         patch.object(blog_generator_module, "cached_model_call", side_effect=_fake_model_call):
        blog_generator_module.generate_blog(item)

    check("does NOT call fetch_via_websearch when Blog_Content is already substantial", mock_fetch.call_count == 0)
    check("passes the item's own Blog_Content onward to extract_keywords",
          mock_extract.call_args[0][0] == _RICH_CONTENT if mock_extract.call_args else False)


test_uses_existing_blog_content_when_substantial()


# ── Case 2: thin/empty Blog_Content -> falls back to fetch_via_websearch ──
def test_refetches_when_blog_content_is_thin():
    item = {
        "Blog_Links": "https://www.moneycontrol.com/real-article-url",
        "Blog_Content": "IDFC First Bank shares rose today.",  # well under 150 words
        "source": "moneycontrol",
    }
    with patch.object(blog_generator_module, "fetch_via_websearch", return_value=_RICH_CONTENT) as mock_fetch, \
         patch.object(blog_generator_module, "extract_keywords", side_effect=_fake_keyword_data) as mock_extract, \
         patch.object(blog_generator_module, "get_keyword_volumes", side_effect=_fake_volume_data), \
         patch.object(blog_generator_module, "cached_model_call", side_effect=_fake_model_call):
        blog_generator_module.generate_blog(item)

    check("calls fetch_via_websearch with Blog_Links when Blog_Content is thin", mock_fetch.call_count == 1)
    check("calls fetch_via_websearch with the correct URL",
          mock_fetch.call_args[0][0] == item["Blog_Links"] if mock_fetch.call_args else False)
    check("passes the re-fetched content onward to extract_keywords",
          mock_extract.call_args[0][0] == _RICH_CONTENT if mock_extract.call_args else False)


test_refetches_when_blog_content_is_thin()


# ── Case 3: missing Blog_Content entirely -> falls back to fetch_via_websearch ──
def test_refetches_when_blog_content_missing():
    item = {
        "Blog_Links": "https://www.livemint.com/real-article-url",
        "source": "livemint",
    }
    with patch.object(blog_generator_module, "fetch_via_websearch", return_value=_RICH_CONTENT) as mock_fetch, \
         patch.object(blog_generator_module, "extract_keywords", side_effect=_fake_keyword_data), \
         patch.object(blog_generator_module, "get_keyword_volumes", side_effect=_fake_volume_data), \
         patch.object(blog_generator_module, "cached_model_call", side_effect=_fake_model_call):
        blog_generator_module.generate_blog(item)

    check("calls fetch_via_websearch when Blog_Content key is absent entirely", mock_fetch.call_count == 1)


test_refetches_when_blog_content_missing()


if failures:
    print(f"\n{len(failures)} FAILURE(S)")
    raise SystemExit(1)
print("\nAll cases passed.")
