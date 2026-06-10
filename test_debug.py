# test_dedup.py

from utils.regex_dedup import extract_fingerprint, fingerprint_similarity, is_regex_duplicate
from utils.fuzzy_dedup import fuzzy_similarity, is_fuzzy_duplicate, _normalize

# ══════════════════════════════════════════════════════════════
#  TEST CASES
#  Format: (title1, title2, expected_result, description)
# ══════════════════════════════════════════════════════════════

TEST_CASES = [

    # ── SHOULD BE DUPLICATE ───────────────────────────────────

    (
        "RBI policy unchanged 5.25% Should You Hold Your Portfolio?",
        "RBI Rate Unchanged at 5.25% Should You Rework Your Portfolio?",
        "DUPLICATE",
        "Same RBI rate news — different advice words"
    ),
    (
        "RBI rate outlook 5.1% inflation Should You Invest Now?",
        "RBI 5.1% Inflation Forecast You Should Watch Your Portfolio?",
        "DUPLICATE",
        "Same RBI inflation news — different wording"
    ),
    (
        "Sensex falls 300 points on FII selling",
        "Sensex drops 300 points amid FII outflow",
        "DUPLICATE",
        "Same Sensex fall — falls vs drops"
    ),
    (
        "Gold rises Rs 1300 per 10 gm on Iran war fears",
        "Gold price up Rs 1300 as Middle East tensions rise",
        "DUPLICATE",
        "Same gold price move — different reason words"
    ),
    (
        "EPFO 8.25% interest rate credited to PF accounts",
        "EPFO subscribers get 8.25% interest for FY2026",
        "DUPLICATE",
        "Same EPFO interest news"
    ),
    (
        "RBI keeps repo rate unchanged at 5.25%",
        "RBI holds repo rate at 5.25% unchanged",
        "DUPLICATE",
        "Word reorder — keeps vs holds"
    ),
    (
        "Nifty gains 150 points as RBI policy announced",
        "Nifty rises 150 points after RBI policy decision",
        "DUPLICATE",
        "Same Nifty move — gains vs rises"
    ),
    (
        "SEBI order against Rajesh Exports — 97% revenue inflated",
        "Rajesh Exports SEBI probe — revenue inflation 97 percent",
        "DUPLICATE",
        "Same SEBI news — different word order"
    ),
    (
        "Sensex recovers 700 points from day low",
        "Sensex gains 700 points recovering from morning lows",
        "DUPLICATE",
        "Same Sensex recovery news"
    ),
    (
        "HDFC AMC expects RBI to raise rates by 100 bps",
        "HDFC AMC sees RBI hiking rates 100 bps next year",
        "DUPLICATE",
        "Same HDFC AMC forecast"
    ),

    # ── SHOULD BE UNIQUE ──────────────────────────────────────

    (
        "RBI Rate Unchanged at 5.25%",
        "Sensex falls 300 points on FII selling",
        "UNIQUE",
        "Completely different topics"
    ),
    (
        "GenXAI Analytics IPO opens today at Rs 110 to 116",
        "Hexagon Nutrition IPO price band Rs 42 to 45",
        "UNIQUE",
        "Different IPOs"
    ),
    (
        "Gold falls Rs 1300 today",
        "Nifty rises 200 points today",
        "UNIQUE",
        "Different assets"
    ),
    (
        "Sensex falls 300 points",
        "Sensex rises 200 points",
        "UNIQUE",
        "Same index but opposite direction"
    ),
    (
        "HDFC Bank shares rise 2% after Goldman target raised",
        "ICICI Bank shares rise 3% after Motilal upgrade",
        "UNIQUE",
        "Different banks — similar structure"
    ),
    (
        "Suzlon Energy shares rise 2% after solar expansion",
        "JBM Auto shares climb 5% on electric bus market share",
        "UNIQUE",
        "Different companies entirely"
    ),
    (
        "Wipro among stocks with sharp rise in futures open interest",
        "Infosys shares fall 2% after weak quarterly guidance",
        "UNIQUE",
        "Different IT companies different news"
    ),
]


# ══════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════

def print_separator(char="─", width=70):
    print(char * width)


def print_header(text):
    print("\n" + "═" * 70)
    print(f"  {text}")
    print("═" * 70)


# ══════════════════════════════════════════════════════════════
#  TEST REGEX
# ══════════════════════════════════════════════════════════════

def test_regex():
    print_header("REGEX DEDUP TEST")
    print(f"  Threshold: 0.5")
    print(f"  Total cases: {len(TEST_CASES)}")

    correct  = 0
    wrong    = 0
    fp_risk  = 0

    for t1, t2, expected, desc in TEST_CASES:
        fp1   = extract_fingerprint(t1)
        fp2   = extract_fingerprint(t2)
        score = fingerprint_similarity(fp1, fp2)

        result   = "DUPLICATE" if score >= 0.5 else "UNIQUE"
        is_right = result == expected

        if is_right:
            icon = "✅"
            correct += 1
        else:
            icon = "❌"
            wrong += 1

        print(f"\n{icon} {desc}")
        print(f"   T1      : {t1[:65]}")
        print(f"   T2      : {t2[:65]}")
        print(f"   Score   : {score:.2f}")
        print(f"   Result  : {result:<10} Expected: {expected}")
        print(f"   FP1 → e:{set(fp1['entities'])} "
              f"a:{set(fp1['actions'])} "
              f"n:{set(fp1['numbers'])}")
        print(f"   FP2 → e:{set(fp2['entities'])} "
              f"a:{set(fp2['actions'])} "
              f"n:{set(fp2['numbers'])}")

    print_separator("═")
    print(f"  REGEX RESULT: {correct}/{len(TEST_CASES)} correct | "
          f"{wrong} wrong")
    print_separator("═")
    return correct, wrong


# ══════════════════════════════════════════════════════════════
#  TEST FUZZY
# ══════════════════════════════════════════════════════════════

def test_fuzzy():
    print_header("FUZZY DEDUP TEST")
    print(f"  Threshold: 85")
    print(f"  Total cases: {len(TEST_CASES)}")

    correct = 0
    wrong   = 0

    for t1, t2, expected, desc in TEST_CASES:
        score  = fuzzy_similarity(t1, t2)
        result = "DUPLICATE" if score >= 85 else "UNIQUE"

        is_right = result == expected

        if is_right:
            icon = "✅"
            correct += 1
        else:
            icon = "❌"
            wrong += 1

        n1 = _normalize(t1)
        n2 = _normalize(t2)

        print(f"\n{icon} {desc}")
        print(f"   T1 raw  : {t1[:65]}")
        print(f"   T2 raw  : {t2[:65]}")
        print(f"   T1 norm : {n1[:65]}")
        print(f"   T2 norm : {n2[:65]}")
        print(f"   Score   : {score}")
        print(f"   Result  : {result:<10} Expected: {expected}")

    print_separator("═")
    print(f"  FUZZY RESULT: {correct}/{len(TEST_CASES)} correct | "
          f"{wrong} wrong")
    print_separator("═")
    return correct, wrong


# ══════════════════════════════════════════════════════════════
#  TEST COMBINED — REGEX + FUZZY TOGETHER
# ══════════════════════════════════════════════════════════════

def test_combined():
    print_header("COMBINED DEDUP TEST (REGEX + FUZZY)")
    print(f"  Regex threshold : 0.5")
    print(f"  Fuzzy threshold : 85")
    print(f"  Logic: DUPLICATE if EITHER regex OR fuzzy catches it")
    print(f"  Total cases: {len(TEST_CASES)}")

    correct = 0
    wrong   = 0

    for t1, t2, expected, desc in TEST_CASES:
        # Regex check
        fp1          = extract_fingerprint(t1)
        fp2          = extract_fingerprint(t2)
        regex_score  = fingerprint_similarity(fp1, fp2)
        regex_dup    = regex_score >= 0.5

        # Fuzzy check
        fuzzy_score  = fuzzy_similarity(t1, t2)
        fuzzy_dup    = fuzzy_score >= 85

        # Combined — duplicate if EITHER catches it
        is_dup = regex_dup or fuzzy_dup
        result = "DUPLICATE" if is_dup else "UNIQUE"

        is_right = result == expected

        if is_right:
            icon = "✅"
            correct += 1
        else:
            icon = "❌"
            wrong += 1

        # Which method caught it
        caught_by = []
        if regex_dup: caught_by.append(f"REGEX({regex_score:.2f})")
        if fuzzy_dup: caught_by.append(f"FUZZY({fuzzy_score})")
        caught_str = " + ".join(caught_by) if caught_by else "none"

        print(f"\n{icon} {desc}")
        print(f"   T1       : {t1[:65]}")
        print(f"   T2       : {t2[:65]}")
        print(f"   Caught by: {caught_str}")
        print(f"   Result   : {result:<10} Expected: {expected}")

    print_separator("═")
    print(f"  COMBINED RESULT: {correct}/{len(TEST_CASES)} correct | "
          f"{wrong} wrong")
    print_separator("═")
    return correct, wrong


# ══════════════════════════════════════════════════════════════
#  SUMMARY
# ══════════════════════════════════════════════════════════════

def print_summary(regex_correct, regex_wrong,
                  fuzzy_correct, fuzzy_wrong,
                  combined_correct, combined_wrong):
    total = len(TEST_CASES)

    print_header("FINAL SUMMARY")

    print(f"  {'Method':<15} {'Correct':>8} {'Wrong':>8} {'Accuracy':>10}")
    print_separator()
    print(f"  {'Regex':<15} {regex_correct:>8} {regex_wrong:>8} "
          f"{regex_correct/total*100:>9.1f}%")
    print(f"  {'Fuzzy':<15} {fuzzy_correct:>8} {fuzzy_wrong:>8} "
          f"{fuzzy_correct/total*100:>9.1f}%")
    print(f"  {'Combined':<15} {combined_correct:>8} {combined_wrong:>8} "
          f"{combined_correct/total*100:>9.1f}%")
    print_separator()

    print(f"\n  Recommendation:")
    if combined_correct >= regex_correct and combined_correct >= fuzzy_correct:
        print(f"  ✅ Use COMBINED (Regex + Fuzzy) — best accuracy")
    elif regex_correct > fuzzy_correct:
        print(f"  ✅ Regex performs better for financial news")
    else:
        print(f"  ✅ Fuzzy performs better for this dataset")

    print(f"\n  Threshold tuning:")
    print(f"  Regex  → lower threshold (0.4) = catches more but risky")
    print(f"  Regex  → higher threshold (0.6) = safer but misses some")
    print(f"  Fuzzy  → lower threshold (75) = catches more but risky")
    print(f"  Fuzzy  → higher threshold (90) = safer but misses some")


# ══════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":

    print("\n" + "█" * 70)
    print("  BLOGHEADING DEDUP SYSTEM TEST")
    print("  Tests: Regex + Fuzzy + Combined")
    print("█" * 70)

    regex_c,    regex_w    = test_regex()
    fuzzy_c,    fuzzy_w    = test_fuzzy()
    combined_c, combined_w = test_combined()

    print_summary(
        regex_c,    regex_w,
        fuzzy_c,    fuzzy_w,
        combined_c, combined_w,
    )