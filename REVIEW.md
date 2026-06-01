# Code Review — Blogheading Pipeline
**Reviewer:** Principal AI Engineer  
**Branch:** `test_ipo_news`  
**Date:** 2026-06-01

---

## P0 — Breaks in Production Right Now

**1. `TEST_MODE = True` left on in `RSS/ipo.py:677`**  
The real NSE RSS feed is never called. Every pipeline run injects a fake "Liotech Industries" entry that fails all scrapers, so the priority stack is permanently empty in production. The README says set it to `False` before push — it was never done.

**2. `pillow` missing from `requirements.txt`**  
Five files use `from PIL import Image` — `compositor.py`, `ipo_compositor.py`, `ai_image_generator.py`, `validator.py`, `verify_images.py`. It is not in `requirements.txt`. A fresh Docker build can break image generation silently. Add `pillow` explicitly.

**3. `fetch_nse_corporate.py:41-42` — test code runs on every import**  
```python
result = fetch_nse_corporate()   # runs at module load time
print("NSE COUNT:", len(result))
```
Every time `mergeall_engine.py` is imported (every scheduler start), this fires an extra HTTP request to NSE and prints noise. The `25 / 200 / 10 / 35` lines at container startup come from here. Must be wrapped in `if __name__ == "__main__":`.

---

## P1 — Logic Bugs

**4. Zerodha fallback has no dedup check (`mergeall_engine.py:1592`)**  
When all stacks drain to zero, the fallback picks a random Zerodha article and immediately publishes it — without checking `load_used_titles()`. Every other code path does a dedup check; this one doesn't. The same article can be published on consecutive runs.

**5. Stacks only rebuild when ALL are empty — IPO articles get delayed**  
`run_pipeline` only calls `_full_fetch_and_build_stack` when `total_stack_size == 0`. If the news stack has 5 articles and a live IPO drops on NSE, that IPO won't enter the priority stack until news drains — up to 25 minutes later at 5-min intervals. For a time-sensitive product (IPO opens/closes), this is a meaningful delay. Fix: always re-fetch IPO articles at the start of each run and inject new ones into the priority stack immediately.

**6. Error handling swallows tracebacks (`mergeall_engine.py:1840`)**  
```python
except Exception as e:
    print(f"[ERROR] {e}")
```
Only the error message is printed, not the traceback. Production failures are very hard to debug. Use `import traceback; traceback.print_exc()` or `logging.exception(e)`.

**7. `save_output` and `load_used_titles` use relative paths**  
```python
filepath = f"output/{filename}"   # save_output.py:10
```
Relative to `cwd`, not `BASE_DIR`. Works in Docker because `WORKDIR=/app`, but fragile. Should use the same `BASE_DIR`-absolute pattern used everywhere else in `mergeall_engine.py`.

---

## P2 — Architecture Issues

**8. `mergeall_engine.py` is 5,404 lines — ~80% dead code**  
Active code runs from line 941 to ~1844 (~900 lines). Lines 1–940 and 1847–5404 are two full commented-out old versions of the entire pipeline. Delete them — git history preserves the old versions.

**9. `utils/stack_manager.py` is dead code**  
Old single-stack manager, only referenced from `mergeall.py` (also dead). The active pipeline uses the multi-stack system inline in `mergeall_engine.py`. Can be deleted.

**10. `USE_AI_IMAGES` is hardcoded in two files that must be manually kept in sync**  
`mergeall_engine.py:996` and `app.py:224` both have `USE_AI_IMAGES = False`. If one is changed without the other, the dashboard reads the wrong JSON file. Should be a single env var (`USE_AI_IMAGES=false` in `.env`) read in both files.

**11. `_full_fetch_and_build_stack` and `_fetch_after_timestamp` are near-identical**  
Both functions do: fetch all sources → split IPO/other → AI filter → `_build_stacks_from_articles`. The only difference is a print statement. One function with a parameter removes the duplication.

**12. `output.json` grows unboundedly — no rotation**  
Every saved article appends to `output.json`, and the entire file is loaded on every pipeline run (dedup) and every Streamlit page load. At ~12 articles/hour this grows fast. After a few weeks `load_used_titles()` and the dashboard will noticeably lag. Needs a rolling window or a separate dedup index.

**13. IPO templates not in repo and not flagged in deployment docs**  
`content_engine/templates/ipo_alert.png` and `ipo_inner.png` are required for IPO images but `.gitignore` has `*.png` so they are excluded. A fresh server deploy silently falls back to the generic compositor for all IPO articles. The README "Deploy" section does not mention copying these files. Add a note: *"Copy `ipo_alert.png` and `ipo_inner.png` to `content_engine/templates/` — not in repo."*

---

## P3 — Documentation vs Code Gaps

| # | Location | README says | Code does |
|---|---|---|---|
| 14 | Project Overview | "every 15 minutes" | `cron minute='*/5'` = every 5 min |
| 15 | Section 7.7 | `TEST_MODE = False` | `TEST_MODE = True` |
| 16 | Deployment section | Shows `env_file: .env` in compose | Current compose has no `env_file` |
| 17 | Deployment section | No mention of `config.py` | `config.py` required, not in repo |

---

## P4 — Minor

- `fetch_nse_corporate.py:13` — no `timeout` on `requests.get`, can hang indefinitely and block the scheduler thread
- `add_cached.py` `lru_cache(maxsize=200)` resets on container restart — expected, but worth noting in docs since cost tracking resets too
- `Filter_news/finance_filter.py` — only referenced from `mergeall.py` (dead old file), not the active pipeline; confirm and delete if unused

---

## Priority Order to Fix

1. `requirements.txt` — add `pillow` (1-line fix, prevents silent image failure)
2. `fetch_nse_corporate.py` — wrap test code in `if __name__ == "__main__"`
3. `RSS/ipo.py` — set `TEST_MODE = False` before any real deploy
4. Zerodha fallback — add `load_used_titles()` dedup check
5. `USE_AI_IMAGES` — move to env var
6. `mergeall_engine.py` — delete the ~4,500 lines of commented-out code
7. Error handling — add `traceback.print_exc()` in the except block
8. IPO templates — document required manual copy step in README deployment section
