# SEO Keyword Tools — Integration Plan for Blogheading

**Audience:** Developer
**Purpose:** Plug Google Keyword Planner (GKP) + Semrush into the existing blog pipeline so blogs target keywords people actually search for — and rank for — without burning our limited Semrush budget.
**Scope:** Pre-publish keyword enrichment only. (A post-publish performance loop is possible later but is out of scope here.)
**Status note:** GKP (Google Ads API) is already set up. This doc focuses on the orchestration and the Semrush build.

---

## 1. The Core Idea (read this first)

These tools are **data sources**, not content writers. They do **not** read, grade, or rewrite blogs — GPT-4 (already in the pipeline) does that. The tools feed GPT-4 **better facts**.

The model: **GKP widens the funnel (free), Semrush narrows it (paid).** GKP generates many keyword candidates; Semrush judges a small shortlist and picks the winner. We never spend Semrush units on discovery — only on judgment.

```
RSS article title
      │
      ▼
extract short SEED term (entity + topic, NOT the headline)   ← see §3
      │
      ▼
GOOGLE KEYWORD PLANNER (free)
  • expand seed → 10–20 candidates + volume
  • keep top ~3–5 by volume + relevance              ← SHORTLIST
      │
      ▼
SEMRUSH (paid — only touches the 3–5 shortlist)
  • phrase_this per keyword → Keyword Difficulty
  • winner = best volume-to-difficulty ratio          ← see §4 for "difficulty"
      │
      ▼
SEMRUSH phrase_questions — ONLY on the winning keyword
  • real questions → FAQ schema
      │
      ▼
GPT-4 blog generation (gets: winning keyword + volume + questions)
      │
      ▼
Webflow draft → publish
```

**Integration point:** `AI_GEN/blog_generator.py`, after keyword extraction and **before** the GPT-4 prompt is assembled.

**Apply only to the `news` stack.** IPO and corporate articles are too time-sensitive ("XYZ IPO GMP", ex-dates) for generic search-volume data to help — and enriching them wastes budget.

---

## 2. The Two Tools — Division of Labor

They overlap only on *search volume*. Use each for what only it can do.

| | Google Keyword Planner | Semrush |
|---|---|---|
| **Cost** | Free | Paid — our 50k units |
| **Role** | Discovery: keyword ideas + volume | Judgment: difficulty + questions |
| **Volume source** | Google's own data (authoritative) | Semrush estimate (modeled) |
| **"Competition" column** | Ad-bidding only — **NOT** organic SEO | True organic **Keyword Difficulty** |
| **Questions people ask** | ❌ | ✅ (`phrase_questions`) |

> ⚠️ **Volume rule:** GKP and Semrush report *different* volume numbers. **Trust GKP's volume** (it's Google's). Use **Semrush only for difficulty + questions.** Don't mix the two volume figures.
>
> ⚠️ **Competition trap:** GKP's "competition" column is advertiser bidding, *not* ranking difficulty. Only Semrush's Keyword Difficulty tells you how hard it is to rank organically.

---

## 3. Seeding GKP Correctly (the #1 failure mode)

**Do not send the full headline.** GKP expects short seed terms (2–3 words), not a sentence. A headline like *"Should You Worry as Gold Falls 1% After RBI's Surprise Move?"* has near-zero exact search volume, so GKP returns **nothing**.

You feed GKP the **topic**, not the title. It then generates the "meaty" high-volume variants for you.

**How to extract a good seed:** Use the pipeline's existing article-type + entity detection. Strip question words and filler ("Should You", "Worry", "Surprise"); keep the **noun + entity**.

> *"Should You Worry as Gold Falls 1% After RBI Move?"* → seed = **`gold price`** / `gold rate today`

**A "meaty" keyword** = a phrase with real volume, specific enough to be relevant but general enough that people search it. `gold price today` is meaty; `gold falls 1% after RBI move` is not. GKP returns the meaty ones — you pick the highest-volume relevant result.

**Fallback ladder — must never block publishing:**

```
1. core 2–3 word phrase   ("gold price today")          ← usually works
2. just the entity         ("gold", "RBI", "Tata Motors") ← broadest, almost always returns
3. still empty? → use today's title-keyword, skip enrichment, publish anyway
```

Enrichment is an *enhancement*. If every lookup fails, the blog must still generate and publish using the current title-derived keyword.

---

## 4. What "Keyword Difficulty" Means

Semrush **Keyword Difficulty (KD)** is a **0–100 score for how hard it is to rank on Google page 1 organically** — based on how strong the sites currently ranking for that keyword are.

| KD score | Meaning | For Swastika |
|---|---|---|
| 0–29 | Easy | ✅ Target these |
| 30–49 | Medium | ✅ Realistic |
| 50–69 | Hard | ⚠️ Only if highly relevant |
| 70–100 | Very hard | ❌ Big authority sites own it |

**Why it's the whole point of using Semrush:** a keyword with huge volume but KD 85 is worthless to us — we'd never appear on page 1. We want **high volume (from GKP) + low difficulty (from Semrush).** Pick the winner by **volume-to-difficulty ratio**, not raw volume: 5K vol / KD 30 beats 20K vol / KD 85.

---

## 5. Semrush — How & Where

**Uses:**
1. **`phrase_this`** → Keyword Difficulty (+ volume, but we ignore its volume per §2). Run on the 3–5 shortlist to pick the winner.
2. **`phrase_questions`** → real questions people search → feed into the **FAQ schema**. Run **only on the winning keyword.**

**API basics:**
- Key-based auth → `.env` as `SEMRUSH_API_KEY`.
- Base endpoint: `https://api.semrush.com/`, `database=in` (India).

**Where in code:**
- New module `AI_GEN/semrush_enrichment.py`: takes the shortlist, returns the winning keyword + its questions.
- Called from `blog_generator.py`; results injected into the GPT-4 prompt (difficulty/volume → H2/H3 targeting; questions → FAQ section).

---

## 6. Cost & Units Strategy

We have **50,000 units**. With this design it lasts **months**, not days.

**Rough cost:** `phrase_this` ~10 units; `phrase_questions` ~10 units/row (cap rows).

| Call | Count/article | Units |
|---|---|---|
| GKP volume + ideas | bulk | **free** |
| Semrush `phrase_this` (shortlist) | 3–5 | ~30–50 |
| Semrush `phrase_questions` (winner only) | 1 | ~50 |
| **Per article** | | **~80–100** |

**The rules that stretch the budget:**
1. **GKP does all discovery + volume (free); Semrush only judges the shortlist.** Never send GKP's full idea list to Semrush.
2. **Cache every Semrush result**, keyed by normalized keyword + database. Repeat topics ("Nifty", "gold price") cost **zero** the second time. TTL 7–30 days (difficulty changes slowly).
3. **Cap and scope:** news stack only; shortlist ≤5; `phrase_questions` top ~5 rows; skip enrichment on empty/garbage seeds.

---

## 7. Build Order

| Phase | What | Effort |
|---|---|---|
| 1 | Seed extraction + GKP shortlist (GKP already wired) → `gkp_enrichment.py` | Low–Med |
| 2 | Semrush `phrase_this` difficulty gate + `phrase_questions`, with caching → `semrush_enrichment.py` | Low |
| 3 | Orchestrate both in `blog_generator.py` (news stack), inject into GPT-4 prompt + fallback ladder | Low |
| 4 | Tune cache TTL + scope against real unit consumption | Low |

---

## 8. Config Checklist

`.env`:
```
SEMRUSH_API_KEY=...      # Semrush dashboard → API Units tab
SEMRUSH_DATABASE=in      # India
# (Google Ads API credentials already configured)
```

New files:
- `AI_GEN/gkp_enrichment.py` — seed → shortlist (+ fallback ladder)
- `AI_GEN/semrush_enrichment.py` — shortlist → winning keyword + questions, with cache
- keyword cache (JSON in `output/` or a small DB table)

Touch point:
- `AI_GEN/blog_generator.py` — orchestrate after keyword extraction, inject into GPT-4 prompt. News stack only. Enrichment must never block publishing.
