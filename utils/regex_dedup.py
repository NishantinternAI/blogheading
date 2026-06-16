# utils/regex_dedup.py

import re


# ══════════════════════════════════════════════════════════════
#  ENTITY PATTERNS
# ══════════════════════════════════════════════════════════════

ENTITY_PATTERNS = [
    (r'\brbi\b',                              "rbi"),
    (r'\brepo.?rate\b',                       "repo_rate"),
    (r'\bmpc\b',                              "mpc"),
    (r'\bmonetary.?policy\b',                 "monetary_policy"),
    (r'\bfed\b|\bfederal.?reserve\b',         "fed"),
    (r'\bsensex\b',                           "sensex"),
    (r'\bnifty\b',                            "nifty"),
    (r'\bbse\b',                              "bse"),
    (r'\bnse\b',                              "nse"),
    (r'\bgold\b',                             "gold"),
    (r'\bsilver\b',                           "silver"),
    (r'\bcrude\b|\boil\b',                    "oil"),
    (r'\brupee\b',                            "rupee"),
    (r'\binflation\b',                        "inflation"),
    (r'\bgdp\b',                              "gdp"),
    (r'\bepfo\b|\bprovident.?fund\b',         "epfo"),
    (r'\bipo\b',                              "ipo"),
    (r'\breliance\b',                         "reliance"),
    (r'\bhdfc\b',                             "hdfc"),
    (r'\bicici\b',                            "icici"),
    (r'\bsbi\b',                              "sbi"),
    (r'\btcs\b',                              "tcs"),
    (r'\binfosys\b',                          "infosys"),
    (r'\badani\b',                            "adani"),
    (r'\bbajaj\b',                            "bajaj"),
    (r'\bsebi\b',                             "sebi"),
    (r'\brajesh.?exports\b',                  "rajesh_exports"),
    (r'\bphysicswallah\b|\bpw\b',             "physicswallah"),
    (r'\bsuzlon\b',                           "suzlon"),
    (r'\bindigo\b|\binterglobe\b',            "indigo"),
    (r'\bgroww\b',                            "groww"),
    (r'\blenskart\b',                         "lenskart"),
    (r'\bjbm\b',                              "jbm"),
    (r'\bhero.?motocorp\b',                   "hero_motocorp"),
    (r'\bbhel\b',                             "bhel"),
    (r'\bpoonawalla\b',                       "poonawalla"),
    (r'\bwipro\b',                            "wipro"),
    (r'\btata\b',                             "tata"),
    (r'\bgoldman.?sachs\b',                   "goldman_sachs"),
    (r'\bmotilal\b',                          "motilal"),
    (r'\bjefferies\b',                        "jefferies"),
    (r'\bubs\b',                              "ubs"),
    (r'\bfii\b|\bfpi\b',                      "fii"),
    (r'\bmutual.?fund\b|\bmf\b',              "mutual_fund"),
]

# ══════════════════════════════════════════════════════════════
#  ACTION PATTERNS
# ══════════════════════════════════════════════════════════════

ACTION_PATTERNS = [
    (r'\bunchanged\b|\bsteady\b|\bholds?\b|\bpauses?\b|\bkeeps?\b|\bmaintains?\b',
     "unchanged"),
    (r'\bcuts?\b|\breduced?\b|\blowers?\b|\bslashes?\b',
     "cut"),
    (r'\bhikes?\b|\braises?\b|\bincreases?\b',
     "hike"),
    (r'\brises?\b|\bgains?\b|\bclimbs?\b|\bjumps?\b|\bsurges?\b|\brallies?\b|\bup\b',
     "rises"),
    (r'\bfalls?\b|\bdrops?\b|\bdeclines?\b|\bslides?\b|\bcrashes?\b|\btumbles?\b|\bdown\b',
     "falls"),
    (r'\bopens?\b|\blaunches?\b|\bsubscription\b',
     "opens"),
    (r'\blists?\b|\blisting\b',
     "listing"),
    (r'\bdowngrades?\b',
     "downgrade"),
    (r'\bupgrades?\b',
     "upgrade"),
    (r'\bbuys?\b|\bacquires?\b|\bpurchases?\b',
     "buy"),
    (r'\bsells?\b|\bdivests?\b|\bstake.?sale\b',
     "sell"),
]

# ══════════════════════════════════════════════════════════════
#  NUMBER EXTRACTION
# ══════════════════════════════════════════════════════════════

NUMBER_RE = re.compile(
    r'(\d+(?:\.\d+)?)\s*'
    r'(%|percent|bps|rs\.?|₹|crore|lakh|billion|million)',
    re.IGNORECASE
)

PLAIN_PERCENT_RE = re.compile(r'(\d+(?:\.\d+)?)\s*%')


def _extract_numbers(title: str) -> frozenset:
    numbers = set()
    for match in NUMBER_RE.finditer(title):
        num  = match.group(1)
        unit = match.group(2).lower().replace('.','').replace(' ','')
        if unit in ('percent', '%'):
            unit = '%'
        numbers.add(f"{num}{unit}")
    for match in PLAIN_PERCENT_RE.finditer(title):
        numbers.add(f"{match.group(1)}%")
    return frozenset(numbers)


# ══════════════════════════════════════════════════════════════
#  EXTRACT FINGERPRINT
# ══════════════════════════════════════════════════════════════

def extract_fingerprint(title: str) -> dict:
    """
    Extracts entity + action + number fingerprint from title.

    "RBI Rate Unchanged at 5.25%"
      → entities = {rbi}
      → actions  = {unchanged}
      → numbers  = {5.25%}
    """
    title_lower = title.lower()

    entities = set()
    for pattern, label in ENTITY_PATTERNS:
        if re.search(pattern, title_lower):
            entities.add(label)

    actions = set()
    for pattern, label in ACTION_PATTERNS:
        if re.search(pattern, title_lower):
            actions.add(label)

    numbers = _extract_numbers(title)

    return {
        "entities": frozenset(entities),
        "actions":  frozenset(actions),
        "numbers":  frozenset(numbers),
    }


# ══════════════════════════════════════════════════════════════
#  SIMILARITY SCORE
# ══════════════════════════════════════════════════════════════

def fingerprint_similarity(fp1: dict, fp2: dict) -> float:
    """
    Compares two fingerprints.
    Returns score 0.0 → 1.0

    Weights:
      Entity match → 0.5
      Action match → 0.3
      Number match → 0.2
    """
    e1, e2 = fp1["entities"], fp2["entities"]
    a1, a2 = fp1["actions"],  fp2["actions"]
    n1, n2 = fp1["numbers"],  fp2["numbers"]

    # No entities → cannot compare
    if not e1 or not e2:
        return 0.0

    # Must share at least one entity
    if not (e1 & e2):
        return 0.0

    entity_score = len(e1 & e2) / len(e1 | e2) if (e1 | e2) else 0.0
    action_score = len(a1 & a2) / len(a1 | a2) if (a1 and a2 and (a1|a2)) else 0.0
    number_score = len(n1 & n2) / len(n1 | n2) if (n1 and n2 and (n1|n2)) else 0.0

    return round(
        entity_score * 0.5 +
        action_score * 0.3 +
        number_score * 0.2,
        3
    )


# ══════════════════════════════════════════════════════════════
#  CHECK SINGLE ARTICLE
# ══════════════════════════════════════════════════════════════

def is_regex_duplicate(
    new_title:       str,
    existing_titles: list,
    threshold:       float = 0.5
) -> tuple:
    """
    Returns (is_duplicate, matched_title, score)
    """
    fp_new = extract_fingerprint(new_title)

    best_score   = 0.0
    best_matched = ""

    for existing in existing_titles:
        fp_ex = extract_fingerprint(existing)
        score = fingerprint_similarity(fp_new, fp_ex)
        if score > best_score:
            best_score   = score
            best_matched = existing

    if best_score >= threshold:
        return True, best_matched, best_score

    return False, "", best_score


# ══════════════════════════════════════════════════════════════
#  FILTER LIST
# ══════════════════════════════════════════════════════════════

def filter_regex_duplicates(
    articles:         list,
    published_titles: list,
    threshold:        float = 0.5
) -> list:
    """
    Pass 1 — against published titles
    Pass 2 — within current batch
    """
    if not articles:
        return []

    fresh   = []
    removed = 0

    # Pass 1 — against published
    for article in articles:
        title = article.get("Blog_Title", "")
        dup, matched, score = is_regex_duplicate(
            title, published_titles, threshold
        )
        if dup:
            print(f"[REGEX DEDUP] ❌ Similar to published "
                  f"(score={score:.2f})")
            print(f"[REGEX DEDUP]    New    : '{title[:55]}'")
            print(f"[REGEX DEDUP]    Exists : '{matched[:55]}'")
            removed += 1
        else:
            fresh.append(article)

    # Pass 2 — within batch
    batch_titles = []
    final        = []

    for article in fresh:
        title = article.get("Blog_Title", "")
        dup, matched, score = is_regex_duplicate(
            title, batch_titles, threshold
        )
        if dup:
            print(f"[REGEX DEDUP] ❌ Similar in batch "
                  f"(score={score:.2f})")
            print(f"[REGEX DEDUP]    New    : '{title[:55]}'")
            print(f"[REGEX DEDUP]    Exists : '{matched[:55]}'")
            removed += 1
        else:
            batch_titles.append(title)
            final.append(article)

    if removed:
        print(f"[REGEX DEDUP] Removed {removed} | "
              f"{len(final)}/{len(articles)} kept")
    else:
        print(f"[REGEX DEDUP] No regex duplicates ✅")

    return final