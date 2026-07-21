# A/B Analysis — Alpine Texworld IPO Blog: Pipeline vs Human-Curated

**Date:** 17 July 2026
**Analyst:** Claude (automated content-forensics pass over raw HTML + pipeline source code)

| | Blog A — AI Pipeline | Blog B — User (AI-assisted) |
|---|---|---|
| URL | `/blog/alpine-texworld-ipo-apply-avoid-or-wait-for-listing` | `/blog/alpine-texworld-ipo-review-should-you-apply-for-this-textile-ipo` |
| Total views | **19** | **411** (≈21.6× more) |

---

## 1. Executive Summary

The 21× view gap is **not primarily a writing-quality problem — it is a data-supply problem.**
The pipeline's LLM was handed a single news article as its entire source material
(`AI_GEN/blog_generator.py:979-984`), while the human author (or their AI, fed richer inputs)
had the RHP financials, day-1 subscription numbers, live GMP, machinery specs, and peer
comparisons. The pipeline article was forced to publish sentences like *"GMP data isn't
available yet"* and tables full of *"To be announced"* — and a post-processor in the pipeline
(`fix_table_na`) actively **converts missing data into "To be announced" instead of blocking
publication**.

Everything else — hedging density, thin tables, weaker title targeting, zero external
citations — is downstream of that one root cause, amplified by a shorter word-count target
and the absence of any publish-gate or refresh step.

**The five highest-impact fixes, in order:**

1. Re-enable / rebuild the IPO data-enrichment layer (`RSS/ipo.py` is fully commented out).
2. Add a publication gate: block or defer publishing when financials/GMP/subscription are missing.
3. Add a refresh cycle: regenerate on IPO open day (subscription + GMP) and pre-listing.
4. Raise the depth target for IPO reviews to 3,000–4,000 words with mandatory data tables.
5. Add external authority citations (SEBI RHP, exchange filings) to the generated HTML.

### Caveat — this is not a controlled A/B test

Both posts target the same IPO but differ in publish timing, freshness (Blog B contains
day-1 subscription data, so it was published/updated *during* the subscription window when
search volume peaks), possible social/newsletter promotion, and title keywords. Views alone
can't isolate content quality. The content gap documented below is real and fixable
regardless, but before drawing final conclusions, pull from Google Search Console for both
URLs: impressions, average position, CTR, and top queries. That will show whether Blog A
lost on **rankings** (content/SEO) or on **distribution** (promotion/timing).

---

## 2. Methodology

- Downloaded raw HTML of both pages (185,981 vs 215,527 bytes) and parsed programmatically:
  title/meta tags, JSON-LD blocks, heading trees, tables, links, images, word counts.
- Extracted article-only body text (boilerplate header/footer excluded) and computed
  hedging density, numeric density, and sentence-length statistics.
- Read the pipeline source (`AI_GEN/blog_generator.py`, `RSS/ipo.py`, `webflow_poster.py`,
  `mergeall_engine.py`) to trace each published defect to the code that produced it.

Note: an earlier AI-summarized read of the pages claimed Blog B had FAQ schema and Blog A
didn't. Raw HTML shows the **opposite** — always verify schema at the HTML level.

---

## 3. Page-Level Facts (parsed from raw HTML)

| Element | Blog A (Pipeline) | Blog B (User) |
|---|---|---|
| `<title>` tag | "Alpine Texworld Limited IPO: Should You Apply?" | "Alpine Texworld IPO Review: Should You Apply?" |
| H1 | "Alpine Texworld IPO: Apply, Avoid, or Wait for Listing?" | "Alpine Texworld IPO Review: Should You Apply for This Textile IPO?" |
| URL slug | `...-apply-avoid-or-wait-for-listing` | `...-review-should-you-apply-for-this-textile-ipo` |
| Title / H1 / slug consistency | **Three different phrasings** | Aligned (all "IPO Review / Should You Apply") |
| Meta description | "…GMP not available yet–read the risks and how to apply." | "Discover Alpine Texworld IPO details, from price band to key risks. Read our full review…" |
| Article word count (body only) | ~1,828 | ~3,461 (1.9×) |
| Article H2 sections | 10 | 18 |
| Article H3 subsections | ~6 (FAQ only) | 21 (incl. Peer Comparison, GMP Trend, per-investor-type verdicts) |
| Data tables | **1** | **11** |
| FAQPage JSON-LD schema | ✅ Present (5 questions) | ❌ Absent |
| External authority citations | **0** (only app-store/social boilerplate) | SEBI RHP filing, Investopedia, IPO Watch GMP page + research note PDF, INDmoney review, company site, 4 machinery-manufacturer sites |
| Canonical tag | ❌ Missing | ❌ Missing (site-wide issue) |
| `datePublished`/`article:published_time` | ❌ Missing | ❌ Missing (site-wide issue) |
| `og:type` | `website` (should be `article`) | `website` (site-wide issue) |
| One JSON-LD block failing to parse | ⚠️ Yes | ⚠️ Yes (site-wide issue) |

---

## 4. Data Completeness — the decisive difference

| Data point | Blog A (Pipeline) | Blog B (User) |
|---|---|---|
| Price band / lot / dates | ✅ ₹100–₹105, 142 shares, 14–16 Jul | ✅ Same + min investment ₹14,910 |
| Revenue | ❌ "not provided" | ✅ ₹237.66 Cr → ₹350.18 Cr (+47%) |
| PAT | ❌ | ✅ ₹8.63 Cr → ₹21.72 Cr (+152%) |
| Debt / leverage | ❌ | ✅ D/E 2.35x, borrowings ₹183.39 Cr |
| Valuation | ❌ (a section titled "Is the band fair?" with no numbers to answer it) | ✅ P/E 18.49x + peer comparison table |
| GMP | ❌ "Not available yet" | ✅ ₹5 (~4.76%) + trend section |
| Day-1 subscription | ❌ | ✅ Retail 0.08x, NII 0.15x, QIB 0.00x |
| Earnings-quality analysis | ❌ | ✅ Dedicated section (subsidy dependence behind profit growth) |
| Business operations detail | Generic | ✅ 112 Toyota air-jet looms, 4 open-end spinning machines, 10+ MW solar, 276 lakh m capacity |
| Registrar / lead manager | "To be announced" | ✅ Present |
| Use of proceeds | Vague | ✅ Itemized breakdown |
| Analyst commentary | ❌ | ✅ "What are Analysts Saying" section incl. Swastika's own view |

Blog A repeatedly **tells the reader it is incomplete** — "the source material does not
disclose", "absence of revenue or profit data", "GMP data isn't available yet" (its own
*meta description* leads with GMP being unavailable, which suppresses CTR in search results).
A reader searching "Alpine Texworld IPO review" wants exactly the numbers Blog A admits it
doesn't have. Dwell time, pogo-sticking back to Google, and zero shareability follow directly.

Percentage figures are a good proxy for analytical content: Blog B uses **14 "%" figures**
(growth rates, GMP %, subscription multiples); Blog A uses **zero**.

---

## 5. Writing-Quality Metrics (computed on article body text)

| Metric | Blog A (Pipeline) | Blog B (User) | Reading |
|---|---|---|---|
| Hedging phrases per 1,000 words | **18.1** (33 total: "not available" ×7, "to be announced" ×5, "uncertain" ×4, "cautious" ×4, "not disclosed" ×3, "absence of" ×3…) | **6.1** (21 total, mostly ordinary "may/could") | Blog A hedges 3× as often, and its hedges are *data-missing admissions*, not analytical nuance |
| Average sentence length | **30.0 words** | **20.5 words** | Blog A is significantly harder to read; 30-word average is far above the 15–20 readability sweet spot |
| Numbers per 1,000 words | 48.7 (but mostly the same price band/lot/date repeated) | 35.2 across a much wider *variety* of figures | Blog A repeats its 5 known numbers; Blog B introduces new data each section |
| Verdict | "Watchlist — because GMP data is not available and crucial financials are not disclosed" (a non-answer) | Segmented: listing-gain seekers vs long-term investors vs "who should consider this" | Blog B's conditional verdict still *feels* like advice |
| Redundancy | "Pros And Cons" appears as **two separate H2 sections** | None | Padding to hit word count without data |

---

## 6. SEO / Search-Intent Comparison

### 6.1 Keyword targeting
- "**{Company} IPO review**" is the canonical high-volume query pattern for IPO decision
  content in India. Blog B owns it in title, H1, and slug. Blog A targets "apply, avoid,
  or wait for listing" — a clever editorial angle nobody types into Google.
- Blog B also captures the "**textile IPO**" modifier.
- Blog A's title tag, H1, and slug are **three different phrasings** — diluted relevance
  signal and a worse search-snippet-to-page match. Blog B's are aligned.

### 6.2 Heading structure as query coverage
Blog B's 18 H2s each map to a discrete search intent: *What is X? / Why the IPO? /
Subscription day 1? / How will money be used? / How strong are financials? / Fairly valued? /
GMP? / What are analysts saying? / Should you apply?* — this is long-tail coverage that
matches People-Also-Ask boxes. Blog A's H2s stuff "Alpine Texworld IPO" into nearly every
heading (7 of 10), which reads as keyword stuffing, and two of them are the same section
("Pros and Cons" twice).

### 6.3 Structured data
- Blog A actually **wins** on FAQ schema (FAQPage JSON-LD with 5 questions; Blog B has none).
  This is the one pipeline advantage — keep it.
- Both pages share site-level defects worth fixing independently of the pipeline:
  no canonical URL, no `article:published_time`/`datePublished`, `og:type=website` instead
  of `article`, and one malformed JSON-LD block that fails to parse. Freshness signals
  matter enormously for IPO content, which is intrinsically time-sensitive; Google cannot
  currently tell when either post was published.

### 6.4 E-E-A-T and AI-search citability
Blog B links out to the **SEBI RHP filing, IPO Watch's GMP page and research-note PDF,
Investopedia, the company's own site, and the loom manufacturers**. These outbound citations
are exactly what Google's E-E-A-T guidelines and AI search engines (Perplexity, ChatGPT,
Gemini) reward when choosing what to cite. Blog A has **zero** article-level external
references — ironic, because the pipeline prompt explicitly claims the goal is to "get cited
by AI search engines." An uncited article citing nothing is the least citable format possible.

### 6.5 Freshness
Blog B contains day-1 subscription data → it was published or updated **inside the 3-day
subscription window**, when query volume for "{company} IPO GMP / subscription status /
allotment" spikes. Blog A reads as generated once from the pre-open announcement and never
touched again. IPO search traffic is a ~5-day pulse; a static early article misses most of it.

---

## 7. Root Causes in the Pipeline Code

Each published defect traces to a specific place in this repo:

### 7.1 The generator is data-starved *(primary root cause)*
`AI_GEN/blog_generator.py:979-984` — `generate_ipo_blog()` builds its prompt from only:
```
News Title: {item['Blog_Title']}
News Content: {item['Blog_Content']}
```
One news article in → one thin blog out. The model cannot write financials it was never given.
The prompt even instructs "Only include sections where the source material gives you
something real to say" — but the model still emits GMP/valuation sections filled with
"not available", and nothing downstream stops it.

### 7.2 The enrichment layer exists but is disabled
`RSS/ipo.py` — an entire scraper for **Chittorgarh (IPO details), InvestorGain (GMP),
and Moneycontrol**, with caching and company-name normalization, is **100% commented out**.
The pipeline once knew how to fetch exactly the data Blog B had; it was switched off.

### 7.3 Post-processors mask missing data instead of gating on it
- `AI_GEN/blog_generator.py:131-137` — `fix_table_na()` rewrites `N/A` / empty `<td>` cells
  to **"To be announced"**. This is how five "To be announced" cells reached production.
  A cell the model couldn't fill should *fail the build*, not get a nicer label.
- `AI_GEN/blog_generator.py:453-468` — `fix_ensure_conclusion()` Case D appends the literal
  placeholder *"This article was published without a generated conclusion. Please review and
  add a conclusion before publishing."* — text that can (and by design will) ship to readers.
- There is **no publish-gate** anywhere between `generate_ipo_blog()` and
  `webflow_poster.py`: no check for "not available", "not disclosed", "to be announced",
  missing financial tables, or minimum data coverage.

### 7.4 Depth target is too low for decision-intent content
The general prompt (`blog_generator.py:742`) targets **1,200–2,000 words**; the IPO prompt
sets no floor at all. Blog A landed at ~1,800; Blog B at ~3,461 with 11 tables. For
"should I apply" queries, comprehensiveness is the ranking currency.

### 7.5 One-shot generation, no refresh
Nothing in `mergeall_engine.py` / `scheduler.py` re-generates or patches an IPO article
after publication. GMP and subscription data *by definition* arrive after the initial
announcement — a single-shot pipeline structurally cannot cover an IPO's peak-traffic window.

### 7.6 Template hygiene issues
- Duplicate "Pros and Cons" sections (prompt doesn't forbid near-duplicate H2s).
- Sarthi AI cross-promotion appears ~4×; `fix_duplicate_swastika()` exists but only
  deduplicates paragraphs containing the word "Swastika", missing Sarthi-link-only mentions.
- Title/H1/meta-title/slug generated as independent fields with no consistency constraint.
- Meta description generated from the same starved data, so it advertises the article's
  weakness ("GMP not available yet") right in the SERP snippet.

---

## 8. What Blog A Did *Better* (keep these)

1. **FAQPage JSON-LD** — present and valid (5 Q&As). Blog B lacks it entirely.
2. **"How to Apply via UPI/ASBA" section** — genuine practical search intent Blog B skipped.
3. **Key Takeaways / TLDR block** — good for featured snippets and AI-engine extraction.
4. Meta title/description length discipline (`fix_meta_length` enforces 60/155 chars).

---

## 9. Recommendations (prioritized)

### P0 — Data enrichment layer *(fixes ~80% of the gap)*
Build an `enrich_ipo_data(company)` step that runs **before** `generate_ipo_blog()` and
merges into the prompt:
- **RHP/DRHP financials** — revenue, PAT, margins, D/E, borrowings, use of proceeds
  (SEBI filings page or Chittorgarh; the commented-out `RSS/ipo.py` code is a starting point).
- **Live GMP** — InvestorGain / IPO Watch (scraper already drafted in `RSS/ipo.py`).
- **Subscription status** — NSE/BSE bid data by category, once the issue opens.
- **Peer P/E comparison** — from the RHP's "Basis for Issue Price" section (it's always there).
- Pass this as a structured `IPO_DATA` block in the prompt and require the model to build
  the financials + peer tables from it.

### P0 — Publication gate
Before `webflow_poster` runs, fail (or route to human review) any IPO article where:
- Blog_Content matches `to be announced|not available|not disclosed|source material does not|published without a generated conclusion` (case-insensitive), or
- fewer than N (e.g. 3) `<table>` elements, or
- no `%` figure appears (proxy for absent financial analysis), or
- word count < 2,500 for IPO-review pieces.
Replace `fix_table_na`'s rewrite behavior with a hard failure for IPO sources.

### P1 — Refresh scheduler
Re-run generation (or a targeted "update sections" pass) at three fixed points:
T-1 day (announcement piece), open-day evening (inject day-1 subscription + GMP),
close/allotment day (final GMP + allotment guidance). Update the same Webflow item — this
also creates the content-freshness signal Google rewards.

### P1 — Prompt changes for IPO reviews
- Word target 3,000–4,000; require ≥4 tables (details, financials, peer comparison, GMP trend).
- Title pattern: `{Company} IPO Review: Should You Apply?` and **force title = H1 = meta-title
  stem = slug source string** (single field, derived, not four generations).
- H2s must be natural-language questions; explicitly forbid repeating "{Company} IPO" in more
  than ~40% of headings and forbid duplicate/near-duplicate H2 topics.
- Add an "Earnings quality / what's behind the growth" section requirement when financials exist.
- Require 2–4 outbound citations to primary sources (SEBI filing URL, exchange page) —
  provide the URLs in the enrichment block so the model can't hallucinate them.
- Verdict framework: per-investor-type guidance ("listing-gain seekers… / long-term
  investors… / who should skip") instead of a single hedge.
- Cap Sarthi/Swastika mentions at 1 in body (+1 in conclusion max).
- Max ~22 words average sentence length; the current output averages 30.

### P2 — Site-level SEO fixes (affects every post, not just pipeline ones)
- Emit `datePublished`/`dateModified` (Article JSON-LD) and `article:published_time` OG tags.
- Add canonical URLs; switch `og:type` to `article` on blog posts.
- Fix the JSON-LD block that currently fails to parse on every page.
- Keep and extend FAQPage schema (pipeline already wins here — Blog B doesn't have it).

### P2 — Measurement before the next A/B round
- Pull GSC impressions/position/CTR for both URLs to separate ranking vs distribution effects.
- For the next test, publish both variants at the same time with equal promotion, and compare
  GSC clicks + impressions rather than raw page views.

---

## 10. Suggested Success Metrics for the Improved Pipeline

| Metric | Current (Blog A) | Target |
|---|---|---|
| Article word count (IPO reviews) | ~1,800 | 3,000–4,000 |
| Data tables per article | 1 | ≥4 |
| "Missing-data" phrases published | 16+ | **0** (gate blocks them) |
| External primary-source citations | 0 | 2–4 |
| Hedges per 1,000 words | 18.1 | <8 |
| Avg sentence length | 30 words | ≤22 words |
| Post-publication refreshes per IPO | 0 | 2–3 |
| GSC clicks within IPO window | baseline | track per release |

---

## 11. Addendum (2026-07-21) — GSC Data Resolves the Open Caveat, Mapped to Webflow's AEO Framework

### 11.1 The "not a controlled A/B test" caveat is resolved

Section 1 flagged that raw pageviews couldn't separate a **ranking** problem from a
**distribution** problem, and asked for Google Search Console data before drawing final
conclusions. That data is now in:

| | Blog A (Pipeline) | Blog B (User) | Ratio |
|---|---|---|---|
| Window pulled | Last 90 days | Last 28 days | Blog A's window is 3x longer |
| GSC Impressions | 650 | 91,500 | **~140x** |
| GSC Clicks | 21 | 896 | ~43x |
| CTR | 3.2% | 1% | Blog A's CTR is *higher* |
| Avg. position | 5.7 | 7.1 | Blog A ranks *better* on average |
| GA sessions (landing page) | 30 (90-day window) | 1,090 (28-day window) | ~36x |

**Reading this correctly:** Blog A is not being suppressed by a spam/manual-action penalty —
it actually has a *better* average position and *higher* CTR than Blog B. The gap is almost
entirely **impressions volume**: Google simply has far fewer query-matches to show Blog A
for. This points squarely at **query coverage**, i.e. how many distinct real-world questions
the page's content actually answers — which is a direct read on Section 6.2 (heading
structure as query coverage: Blog B's 18 H2s map to 18 discrete search intents; Blog A's 10
H2s largely restate the same "Alpine Texworld IPO" phrase). More headings answering more
distinct questions → more query strings Google can match the page against → more
impressions. Word count and data depth (Section 4) are the raw material that makes that
many genuinely distinct headings possible — a 1,800-word, single-source article cannot
sustain 18 non-redundant H2s without padding.

This reframes the fix priority slightly: **P0 is still data enrichment** (Section 9), because
without more source data there's nothing to write the additional distinct sections *about*.
But the mechanism by which that data converts to traffic is impressions via query coverage,
not just "better writing."

### 11.2 Mapping to Webflow's AEO Maturity Model

The user supplied Webflow's "AEO Playbook" (four categories: Content, Technical, Authority,
Measurement; five maturity levels each). Scoring the pipeline's current output against it:

| Category | Pipeline's current level | Why |
|---|---|---|
| **Content** | Level 1 ("Write for keywords") | One-off generation from a single source, no update cycle, thin per-question coverage — the guide's own description of Level 1 ("rarely updated... FAQs missing or stale... traffic mostly branded") matches Blog A almost exactly. |
| **Technical** | Level 1–2 | FAQ schema present (a Level-1/2 win) but no `datePublished`/`dateModified`, no canonical tag, one malformed JSON-LD block, `og:type=website` not `article` — all called out in the guide's Level 1–2 checklist as basics. |
| **Authority** | Level 1 | Zero external citations (Section 6.4), no author byline, no E-E-A-T signals — the guide's Level 1 description ("limited third-party mentions... backlinks the primary signal") is the ceiling here. |
| **Measurement** | Level 0 (pre-Level-1) | No tracking of AI-referral traffic, LLM citations, or brand mentions in AI answers at all — this AB test itself *is* the pipeline's first measurement effort, done manually, once. |

Two data points from the guide sharpen the priority order already in Section 9:

- **"95% of ChatGPT citations point to pages updated in the last 10 months."** The pipeline
  has *zero* refresh mechanism (Section 7.5) — a single-shot article ages out of AI-citation
  eligibility on a clock the pipeline currently ignores entirely, independent of content
  quality.
- **Webflow's own case study: "simply increasing the pace of content refreshes drove 42% more
  traffic... in under two months."** This is an existing playbook result for the exact fix
  already prioritized as P1 in Section 9 ("Add a refresh cycle") — refreshing is not a
  nice-to-have, it's demonstrated to move traffic on its own, separate from the data-depth fix.

### 11.3 Additions to Section 9's recommendations (do not replace — these are additive)

**P0/P1 (pulls forward from Section 9, now with an AEO citation attached):**
- Ship the refresh cycle (already P1 in Section 9) — the guide's freshness stat makes this
  higher-leverage than it looked in isolation; treat as co-equal with the data-enrichment P0.
- Fix `datePublished`/`dateModified`/`article:published_time`/canonical/`og:type` (already P2
  in Section 9) — bump to P1. These are free, mechanical, site-wide fixes with no dependency
  on the data-enrichment work, and the guide frames them as Level-1 fundamentals every page
  should already have.

**New, not previously in Section 9:**
- **Author byline + short bio** on every post (e.g. "Reviewed by Swastika Investmart Research
  Desk"). Zero-cost E-E-A-T signal the guide's Authority Level-1 explicitly calls for
  ("add author bios to key content"); the pipeline currently publishes with no author field
  at all.
- **"In summary" / TLDR-first structure** — the pipeline already has a TLDR block (Section 8
  lists this as a kept strength); the guide confirms this is directly aligned with AEO Level-1
  ("bullet points, in-summary statements... so LLMs can interpret your content"). No change
  needed, just don't regress it.
- **Start tracking AI-referral traffic and brand mentions in LLM answers** (Measurement
  Level 1 in the guide) — the pipeline has no equivalent of this at all today. Minimum viable
  version: filter GA referral traffic for `chatgpt.com`, `perplexity.ai`, `gemini.google.com`
  sources, and periodically ask ChatGPT/Perplexity/Gemini "{company} IPO review" for the
  covered companies to see if Swastika is cited. This is the only way to know if the "get
  cited by AI search engines" line in the blog-generation prompt (Section 7.1) is doing
  anything.

### 11.4 What this doesn't change

The AEO guide is Webflow's own B2B SaaS marketing content, not finance-vertical-specific —
its stats (ChatGPT citation freshness, 42% refresh lift) are directional evidence, not a
guarantee those exact percentages transfer to a SEBI-regulated Indian retail-finance blog.
Treat Section 11.3 as reinforcing and re-prioritizing Section 9's existing plan, not as a
separate workstream.
