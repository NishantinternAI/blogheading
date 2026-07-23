"""
Ad-hoc verification script for classify_template_category() -- run directly
with `python tools/test_classify_template_category.py`, matching this repo's
existing convention of no pytest/unittest runner.
"""
from content_engine.image_module.template_selector import classify_template_category

CASES = [
    ("Company announces dividend payout and record date", "", "dividend"),
    ("RBI hikes repo rate to curb inflation", "", "rbi_policy"),
    ("Gold prices surge to record high", "", "gold_oil"),
    ("Crude oil prices tumble on demand worries", "", "gold_oil"),
    ("TCS Q1 results beat estimates", "", "tech"),
    ("HDFC Bank posts record profit", "", "banking"),
    ("Sensex surges 500 points on strong buying", "", "finance"),
    ("Rupee weakens against dollar amid forex outflows", "", "finance"),
    ("Local temple festival draws record crowds", "", "general"),
]

failures = []
for title, content, expected in CASES:
    actual = classify_template_category(title, content)
    status = "OK" if actual == expected else "FAIL"
    if actual != expected:
        failures.append((title, expected, actual))
    print(f"[{status}] {title!r} -> {actual} (expected {expected})")

if failures:
    print(f"\n{len(failures)} FAILURE(S)")
    raise SystemExit(1)
print("\nAll cases passed.")
