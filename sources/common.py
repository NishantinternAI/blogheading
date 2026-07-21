"""
sources/common.py -- shared helpers used across multiple RSS fetcher modules.

assess_quality() was copy-pasted byte-identically into 7 fetchers
(zerodha, cnbc, paisa, livemint, economic_times, ndtv_profit,
Business_Standard) -- consolidated here so there's one place to change
the word-count thresholds if they're ever tuned.

Deliberately NOT consolidated: each fetcher's dedup-by-title logic
(similar shape -- a `seen_titles` set + normalize + skip-if-seen -- but
embedded inline in each fetcher's main loop with per-file variations)
and each fetcher's article-body cleaning functions (clean_content,
dedup_paragraphs, dedup_sentences, deduplicate_opener, etc. -- similar
names but different logic per site, not true duplicates). Extracting
those would mean restructuring each fetcher's control flow for a small
win; left as-is.
"""


def assess_quality(content: str) -> dict:
    """
    Scores article body text by word count into a coarse quality bucket.

    Args:
        content: the article body text to score.

    Returns:
        {"word_count": int, "quality": "rich"|"thin"|"bare"|"empty"} --
        "rich" >= 300 words, "thin" >= 150, "bare" >= 50, else "empty".
    """
    words = len(content.split()) if content else 0
    return {
        "word_count": words,
        "quality": (
            "rich"  if words >= 300 else
            "thin"  if words >= 150 else
            "bare"  if words >= 50  else
            "empty"
        ),
    }
