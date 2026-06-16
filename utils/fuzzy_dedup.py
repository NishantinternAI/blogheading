# utils/fuzzy_dedup.py

import re

try:
    from thefuzz import fuzz
    FUZZY_AVAILABLE = True
except ImportError:
    FUZZY_AVAILABLE = False
    print("[FUZZY] Not installed — run: pip install thefuzz python-Levenshtein")


# ══════════════════════════════════════════════════════════════
#  CONFIG
# ══════════════════════════════════════════════════════════════

FUZZY_THRESHOLD = 85

STOP_WORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at",
    "to", "for", "of", "with", "is", "are", "was", "were",
    "you", "your", "should", "how", "what", "why", "when",
    "will", "can", "may", "now", "today", "after", "before",
    "check", "here", "know", "watch", "read", "see",
    "would", "could", "does", "do", "did", "its", "it",
    "this", "that", "these", "those", "amid", "as", "by",
    "from", "into", "than", "says", "said",
}


# ══════════════════════════════════════════════════════════════
#  NORMALIZE
# ══════════════════════════════════════════════════════════════

def _normalize(title: str) -> str:
    """
    Normalizes title before fuzzy comparison.
    Removes stop words, normalizes synonyms.
    """
    text = title.lower()
    text = re.sub(r'[^\w\s%.]', ' ', text)
    text = text.replace("percent", "%").replace("per cent", "%")

    # Normalize action synonyms
    replacements = {
        r'\bunchanged\b|\bsteady\b|\bholds?\b|\bpauses?\b|\bkeeps?\b': "unchanged",
        r'\bcuts?\b|\breduced?\b|\blowers?\b':                         "cut",
        r'\bhikes?\b|\braises?\b|\bincreases?\b':                      "hike",
        r'\brises?\b|\bgains?\b|\bclimbs?\b|\bsurges?\b':              "rise",
        r'\bfalls?\b|\bdrops?\b|\bdeclines?\b|\bslides?\b':            "fall",
    }
    for pattern, replacement in replacements.items():
        text = re.sub(pattern, replacement, text)

    words = [w for w in text.split()
             if w not in STOP_WORDS and len(w) > 1]
    return " ".join(words)


# ══════════════════════════════════════════════════════════════
#  FUZZY SIMILARITY
# ══════════════════════════════════════════════════════════════

def fuzzy_similarity(title1: str, title2: str) -> int:
    """
    Returns 0-100 similarity score using 4 fuzzy algorithms.
    Returns max score across all 4.
    """
    if not FUZZY_AVAILABLE:
        return 0

    n1 = _normalize(title1)
    n2 = _normalize(title2)

    if not n1 or not n2:
        return 0

    return max(
        fuzz.ratio(n1, n2),
        fuzz.partial_ratio(n1, n2),
        fuzz.token_sort_ratio(n1, n2),
        fuzz.token_set_ratio(n1, n2),
    )


# ══════════════════════════════════════════════════════════════
#  CHECK SINGLE ARTICLE
# ══════════════════════════════════════════════════════════════

def is_fuzzy_duplicate(
    new_title:       str,
    existing_titles: list,
    threshold:       int = FUZZY_THRESHOLD
) -> tuple:
    """
    Returns (is_duplicate, matched_title, score)
    """
    if not FUZZY_AVAILABLE:
        return False, "", 0

    best_score   = 0
    best_matched = ""

    for existing in existing_titles:
        score = fuzzy_similarity(new_title, existing)
        if score > best_score:
            best_score   = score
            best_matched = existing

    if best_score >= threshold:
        return True, best_matched, best_score

    return False, "", best_score


# ══════════════════════════════════════════════════════════════
#  FILTER LIST
# ══════════════════════════════════════════════════════════════

def filter_fuzzy_duplicates(
    articles:         list,
    published_titles: list,
    threshold:        int = FUZZY_THRESHOLD
) -> list:
    """
    Pass 1 — against published titles
    Pass 2 — within current batch
    """
    if not articles:
        return []

    if not FUZZY_AVAILABLE:
        print("[FUZZY] Not available — skipping")
        return articles

    fresh   = []
    removed = 0

    # Pass 1 — against published
    for article in articles:
        title = article.get("Blog_Title", "")
        dup, matched, score = is_fuzzy_duplicate(
            title, published_titles, threshold
        )
        if dup:
            print(f"[FUZZY DEDUP] ❌ Similar to published "
                  f"(score={score})")
            print(f"[FUZZY DEDUP]    New    : '{title[:55]}'")
            print(f"[FUZZY DEDUP]    Exists : '{matched[:55]}'")
            removed += 1
        else:
            fresh.append(article)

    # Pass 2 — within batch
    batch_titles = []
    final        = []

    for article in fresh:
        title = article.get("Blog_Title", "")
        dup, matched, score = is_fuzzy_duplicate(
            title, batch_titles, threshold
        )
        if dup:
            print(f"[FUZZY DEDUP] ❌ Similar in batch "
                  f"(score={score})")
            print(f"[FUZZY DEDUP]    New    : '{title[:55]}'")
            print(f"[FUZZY DEDUP]    Exists : '{matched[:55]}'")
            removed += 1
        else:
            batch_titles.append(title)
            final.append(article)

    if removed:
        print(f"[FUZZY DEDUP] Removed {removed} | "
              f"{len(final)}/{len(articles)} kept")
    else:
        print(f"[FUZZY DEDUP] No fuzzy duplicates ✅")

    return final