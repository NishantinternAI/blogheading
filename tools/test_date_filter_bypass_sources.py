"""
Ad-hoc verification script for utils/date_filter.py's BYPASS_SOURCES --
run directly with `python tools/test_date_filter_bypass_sources.py`.

Covers the fix adding "google_trends_business" to BYPASS_SOURCES: this
module, in isolation, always lets a google_trends_business article
through regardless of its date, exactly like nse_ipo/nse_corporate/
market_summary already do -- content-verification (assess_quality/
_is_content_valid) checks relevance and word count, not recency, so
this bypass is safe ONLY because sources/google_trends.py's
_pick_best_candidate() already rejects any candidate older than
MAX_CANDIDATE_AGE_DAYS before an article ever reaches this filter (see
that function's docstring for the 2026-07-28 stale-repost incident this
fixed). This test only proves the bypass-source list itself; it does
NOT prove staleness is actually caught -- that's covered separately in
sources/google_trends.py's own candidate-recency behavior.
"""
import utils.date_filter as date_filter_module

failures = []


def check(label, condition):
    status = "OK" if condition else "FAIL"
    print(f"[{status}] {label}")
    if not condition:
        failures.append(label)


check("google_trends_business is in BYPASS_SOURCES",
      "google_trends_business" in date_filter_module.BYPASS_SOURCES)

check("existing bypass sources are still present",
      {"nse_ipo", "nse_corporate", "market_summary"} <= date_filter_module.BYPASS_SOURCES)

# -- behavioral check: an old/stale-dated google_trends_business article survives --
stale_article = {
    "Blog_Title":       "Old trending business article -- content already verified",
    "Blog_PublishDate": "Mon, 01 Jun 2020 10:00:00 +0530",  # far outside today's window
    "source":           "google_trends_business",
}

result = date_filter_module.filter_fresh_articles([stale_article])
check("a stale-dated google_trends_business article is NOT filtered out", len(result) == 1)

check("is_fresh() directly returns True for a stale google_trends_business article",
      date_filter_module.is_fresh(stale_article) is True)

# -- sanity: a stale article from a non-bypass source IS still filtered out --
stale_non_bypass = {
    "Blog_Title":       "Old regular article",
    "Blog_PublishDate": "Mon, 01 Jun 2020 10:00:00 +0530",
    "source":           "livemint",
}
result_non_bypass = date_filter_module.filter_fresh_articles([stale_non_bypass])
check("a stale-dated non-bypass article IS still filtered out (no regression)", len(result_non_bypass) == 0)

if failures:
    print(f"\n{len(failures)} FAILURE(S)")
    raise SystemExit(1)
print("\nAll cases passed.")
