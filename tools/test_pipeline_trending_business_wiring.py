"""
Ad-hoc verification script confirming the trending-business-topics
source is correctly wired into core/pipeline.py -- run directly with
`python tools/test_pipeline_trending_business_wiring.py`. Inspects
source code/module state rather than running a full pipeline cycle,
since simulating one would require mocking all 10 existing fetchers.
"""
import inspect

import core.pipeline as pipeline

failures = []


def check(label, condition):
    status = "OK" if condition else "FAIL"
    print(f"[{status}] {label}")
    if not condition:
        failures.append(label)


check(
    "google_trends_business is in PRIORITY_SOURCES",
    "google_trends_business" in pipeline.PRIORITY_SOURCES,
)

fetch_all_src = inspect.getsource(pipeline._fetch_all_sources)
check(
    "fetch_trending_business_articles is wired into _fetch_all_sources' source list",
    "fetch_trending_business_articles" in fetch_all_src and "google_trends_business" in fetch_all_src,
)

full_fetch_src = inspect.getsource(pipeline._full_fetch_and_build_stack)
check(
    "google_trends_business gets bypass treatment in _full_fetch_and_build_stack",
    "google_trends_business" in full_fetch_src,
)

after_ts_src = inspect.getsource(pipeline._fetch_after_timestamp)
check(
    "google_trends_business gets bypass treatment in _fetch_after_timestamp",
    "google_trends_business" in after_ts_src,
)

if failures:
    print(f"\n{len(failures)} FAILURE(S)")
    raise SystemExit(1)
print("\nAll cases passed.")
