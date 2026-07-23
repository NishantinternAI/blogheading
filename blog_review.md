# Blog Review Log

Running log of issues observed in published blogs (typos, formatting bugs, data
gaps, factual errors, etc). Add a new dated entry whenever a problem is spotted
on a live post; each entry should end with a status so we can track what's
actually been fixed vs. still open.

Severity: P0 = published article is wrong/broken and visible to readers,
P1 = quality/consistency issue, P2 = cosmetic/nice-to-have.

---

## 2026-07-23 — Market-pulse table shows "–" instead of real values (P0)

**Where:** https://www.swastika.co.in/blog/sensex-share-price-and-market-pulse-crude-rally-west-asia-tensions-weigh-on-indi

**Symptom:** The index-snapshot table renders literal "–" (en dash) in the
"Close / Level" and "Point Change" columns for Nifty Midcap 150, Nifty
Smallcap 250, Nifty Bank, Nifty IT, Nifty FMCG, and NSE Auto — only the %
Change column is populated for those rows. Nifty 50, Sensex, and Brent Crude
are fully populated.

**Root cause (confirmed):** Two separate issues stacked:

1. **Cleanup regex bug (fixed):** `generators/blog_generator.py` calls
   `fix_em_dash()` on every string field *before* `fix_table_na()` runs.
   `fix_em_dash()` normalizes em-dash (`—`) → en-dash (`–`), but
   `fix_table_na()`'s regex only matched ASCII hyphens (`-`, `--`), not the
   en-dash character it had just normalized everything to. So any dash the
   model used as a "no data" placeholder in a `<td>` survived cleanup and
   got published raw instead of becoming "To be announced".
   → **Fixed 2026-07-23**: `fix_table_na()` regex now also matches `–` and
   `—`. Verified with a standalone regex test (en-dash, em-dash, single/double
   hyphen, N/A, and blank cells all convert; real numeric values are
   untouched).

2. **Underlying data gap (still open):** Even with the regex fixed, those
   cells will just read "To be announced" instead of the actual index level —
   which is wrong/confusing for same-day market-close data (that phrasing
   reads as IPO-style "pending disclosure" language, not "not reported").
   Checked live financial coverage of the same trading session (Business
   Standard, Liquide) via web search: mainstream RSS/news roundups commonly
   report only the **% change** for sectoral indices (Midcap, Smallcap, Bank,
   IT, FMCG, Auto) and give absolute close + point change only for Nifty 50 /
   Sensex. The source article genuinely doesn't contain those absolute
   figures, so the model has nothing to put there — this isn't something the
   text-cleanup layer can solve.
   Options for an owner decision (none implemented yet):
   - (a) Add a dedicated index-levels fetch (NSE/BSE or an indices API) to
     `sources/` so `blog_generator.py` has real absolute values to hand the
     model for every row, not just what the news article happened to mention.
   - (b) Instruct the prompt (`generators/blog_generator.py`, TABLES section)
     to only include columns it actually has data for — e.g. drop
     Close/Point-Change columns entirely for rows where the source only gives
     %, rather than emitting a dash placeholder for the model to fill.
   - (c) Some combination: fetch what's cheaply available (a), fall back to
     %-only columns for anything still missing (b).

**Live fix applied 2026-07-23:** Manually patched the already-published Webflow
CMS item (`Blog Posts` collection, item `6a61a74f7eb72f2966ca1c15`, site
`Swastika Website` / `649a7bd9d30be4bdd61239e5`) — replaced the 13 raw dash
cells in the `content` rich-text field with "To be announced" (same text the
fixed `fix_table_na()` would now produce) and republished the item. Verified
live on the page afterward. Diffed old vs. new content string before pushing
(182-character delta, matching exactly 13 replacements) to make sure nothing
else in the 14KB HTML blob was altered.

**Follow-up 2026-07-23 (user feedback: "To be announced doesn't make any
sense"):** Correct — for same-day market-close data, a vague placeholder is
still a bad reader experience even if it's not literally broken. Pulled the
official NSE index-closing archive
(`archives.nseindia.com/content/indices/ind_close_all_22072026.csv`) for the
July 22, 2026 session and got real Close/Level + Point Change figures for all
6 rows that had been showing "To be announced". Cross-checked: recomputing %
change from each row's (close, point-change) pair matched the %-change
already published in the table/prose to within rounding, confirming the CSV
is the correct source. Replaced the 6 rows' placeholder cells with real
values and republished. Left the Brent Crude row's "Change" cell (which had
no analogous point-change concept in dollars) as "To be announced" for now —
not flagged by the user this round, but worth revisiting: it's a table
structure mismatch (Brent's %-change is already in the "Point Change" column
for that row) more than a missing-data issue.

**Status:** Regex bug fixed in code. The one published instance has now been
corrected twice — first the raw dashes → "To be announced", then
"To be announced" → real NSE figures. Item 2's real fix (option a/b/c above)
is still open: this shows the value of actually wiring up a real index-data
fetch in `sources/` (option a) instead of relying on whatever numbers happen
to be in the RSS source article — NSE's own archive has all of this data for
free, same-day, machine-readable. That's now the recommended direction absent
other constraints.
