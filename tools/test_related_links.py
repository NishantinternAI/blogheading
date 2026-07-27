"""
Ad-hoc verification script for keywords/related_links.py -- run directly
with `python tools/test_related_links.py`. No network calls, no file I/O
(a graph dict is built in-memory for each case).
"""
from keywords.related_links import get_related_links

failures = []


def check(label, condition):
    status = "OK" if condition else "FAIL"
    print(f"[{status}] {label}")
    if not condition:
        failures.append(label)


# -- Tier 1: same primary-keyword group, ranked by secondary overlap -------
graph = {
    "gold price today": [
        {"url": "/delhi", "title": "Delhi gold blog", "volume": 500,
         "secondary_kws": ["silver price rate today", "gold rate today delhi"]},
    ],
    "ibja gold price": [
        {"url": "/ibja", "title": "IBJA gold blog", "volume": 300,
         "secondary_kws": ["ibja gold rate", "ibja silver rate"]},
    ],
    "gold price world gold council": [
        {"url": "/wgc", "title": "WGC gold blog", "volume": 200,
         "secondary_kws": ["rbi gold reserves", "sovereign gold bond investment"]},
    ],
}

primary = "gold price today"
secondary = [
    "kalyan jewellers stock price", "ibja rates", "ibja gold rate",
    "tanishq stock price", "malabar gold stock price", "joyalukkas stock price",
]

result = get_related_links(primary, secondary, graph)
check("tier1+tier2 returns both the same-group and cross-group match", len(result) == 2)
check("tier1 match (same primary group) ranked first", result[0]["url"] == "/delhi" if result else False)
check("tier2 match (secondary-keyword overlap, different group) included", any(r["url"] == "/ibja" for r in result))
check("WGC blog (no secondary overlap) is NOT pulled in", not any(r["url"] == "/wgc" for r in result))

# -- No primary match, no secondary overlap anywhere -> empty --------------
result_empty = get_related_links("completely unrelated topic", ["nothing shared"], graph)
check("no match anywhere returns []", result_empty == [])

# -- max_links cap respected across tier1+tier2 combined -------------------
graph2 = {
    "p1": [{"url": "/p1-0", "title": "p1-0", "volume": 10, "secondary_kws": ["shared"]}],
    "p2": [
        {"url": f"/p2-{i}", "title": f"p2-{i}", "volume": 10, "secondary_kws": ["shared"]}
        for i in range(5)
    ],
}
result_capped = get_related_links("p1", ["shared"], graph2, max_links=3)
check("max_links cap holds even with many tier2 candidates", len(result_capped) == 3)

# -- Tier1 alone still fills max_links without needing tier2 ---------------
graph3 = {
    "p1": [
        {"url": f"/p1-{i}", "title": f"p1-{i}", "volume": 10, "secondary_kws": []}
        for i in range(3)
    ],
}
result_tier1_only = get_related_links("p1", [], graph3, max_links=3)
check("tier1 alone fills max_links with no secondary keywords needed", len(result_tier1_only) == 3)

if failures:
    print(f"\n{len(failures)} FAILURE(S)")
    raise SystemExit(1)
print("\nAll cases passed.")
