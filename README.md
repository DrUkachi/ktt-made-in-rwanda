# S2.T1.3 — 'Made in Rwanda' Content Recommender

**AIMS KTT Hackathon · Tier 1 · RetailTech · Recommender Systems · Low-Tech Distribution**

> A content-based 'niche-first' recommender that nudges buyers toward local Rwandan
> artisan products — with multilingual query support (English, French, Kinyarwanda)
> and a low-tech weekly lead delivery workflow for offline artisans.

---

## The Problem

Generic e-commerce recommenders rank by global popularity, polished marketing copy,
and SEO authority. On a typical search engine, a query for "leather boots" returns
Timberland and Dr Martens — not the leatherworker in Nyamirambo who has no website,
no smartphone, and writes product descriptions on a notebook in Kinyarwanda.

This recommender flips the priority. It treats the catalog of Made-in-Rwanda artisan
products as the primary inventory, mixes in a realistic competitive set of
international brands (Pandora, Coach, Timberland, IKEA, …) so the local-boost is
actually doing real work, and then enforces three rules:

1. A Made-in-Rwanda product **always** appears at rank 1.
2. No single artisan dominates more than 15% of the top-10 (fairness cap).
3. Multilingual queries — including French and Kinyarwanda code-switching — work
   without a translation API.

The output of the search engine is then converted into weekly lead packets that can
be **delivered via SMS or a field-agent voice call** to artisans without internet
access. See [`dispatcher.md`](dispatcher.md) for the full distribution design.

---

## Quick Start

**Two commands — works on Google Colab (free CPU) or any Python 3.10+ environment:**

```bash
pip install -r requirements.txt
python recommender.py --q "leather boots"
```

No model downloads. No GPU. Cold start under 1 second.

### Example queries

```bash
# English
python recommender.py --q "leather boots"

# French (FR→EN dictionary normalisation built-in)
python recommender.py --q "cadeau en cuir pour femme"

# Code-switched (Kinyarwanda + English + French)
python recommender.py --q "agaseke basket cadeau"

# Misspelled — TF-IDF n-grams handle this gracefully
python recommender.py --q "lether boots"

# Real Rwandan brand surfaces #1
python recommender.py --q "handmade shoes Rwanda"

# Local-boost demotes Pandora and promotes a local jeweller to rank 1
python recommender.py --q "silver necklace charm women"

# More results, custom threshold
python recommender.py --q "brass necklace" --n 10 --threshold 0.05
```

### Regenerate synthetic data (optional)

The CSV files are committed. To regenerate deterministically:

```bash
python generate_data.py   # seed=42 — identical output every run
```

---

## Project Structure

```
.
├── recommender.py         # Core recommender: TF-IDF + local-boost + FR→EN + CLI
├── eval.ipynb             # Evaluation: NDCG@5, local-presence rate, fairness audit
├── dispatcher.md          # Product & Business: offline artisan lead workflow + pilot plan
├── generate_data.py       # Reproducible synthetic data generator (seed=42)
│
├── catalog.csv            # 440 products (412 local + 28 international)
├── queries.csv            # 120 queries (EN / FR / code-switched / misspelled)
├── click_log.csv          # 5,000 click events with position-bias noise
│
├── process_log.md         # Hour-by-hour timeline + LLM usage declaration
├── SIGNED.md              # Signed honor code
├── requirements.txt       # CPU-only Python dependencies
└── LICENSE                # MIT
```

---

## Approach

### Indexing

TF-IDF vectorisation over combined product text — `title + description + category +
material` — built once at startup. Configuration:

| Parameter | Value | Reason |
|-----------|-------|--------|
| `analyzer` | `word` | Standard word-token features |
| `ngram_range` | `(1, 2)` | Bigrams capture phrases like "leather boots" |
| `sublinear_tf` | `True` | `log(1+tf)` dampens repeated terms |
| `strip_accents` | `unicode` | `é→e`, `â→a` for French robustness |
| `min_df` | `1` | Don't drop rare terms — small catalog |

Total index size: a sparse 440×~3,000 matrix, built in ~50 ms. Per-query latency
includes the vector transform plus cosine similarity over the full matrix:
**under 5 ms** on a laptop CPU.

### Multilingual query handling

A 60-term **French → English dictionary** (`_FR_TO_EN` in [`recommender.py`](recommender.py))
is applied token-by-token before the TF-IDF transform, covering every product
category:

- `cuir → leather`, `bottes → boots`, `sandales → sandals`
- `chemise → shirt`, `robe → dress`, `tissu → fabric`
- `panier → basket`, `vannerie → basketry`
- `collier → necklace`, `bague → ring`, `boucle → earring`
- `bol → bowl`, `bougie → candle`, `verre → glass`
- modifiers: `cadeau → gift`, `femme → woman`, `artisanal → artisan`, …

Tokens that aren't in the map (French stopwords, Kinyarwanda terms like *agaseke*,
*igitenge*, *urwagwa*) pass through unchanged so they still match the catalog
descriptions, which themselves contain those Kinyarwanda words.

```
Query   : 'cadeau en cuir pour femme'
Normalised: 'gift en leather pour woman'
```

### Ranking

```
final_score = 0.90 × cosine_similarity + 0.10 × normalised_click_popularity
```

The 10% popularity term is loaded from `click_log.csv` and acts as a tie-breaker
between products with similar TF-IDF scores. It's deliberately small so the click
log can never override a strong semantic match.

### Local-boost (two triggers)

The catalog includes **28 international brand products** (Timberland, Dr Martens,
Coach, Fossil, Pandora, Swarovski, IKEA, West Elm, etc.) that compete with local
artisan products on raw similarity. The local-boost guarantees a Made-in-Rwanda
product always appears at rank 1:

| Trigger | Condition | Action |
|---------|-----------|--------|
| **A** | Top result has `is_local=False` | Promote the highest-ranked local product to position 1 |
| **B** | Top result is local but `similarity < threshold` | Inject the most-clicked local product in the guessed category at position 1 |

In both cases the promoted result is marked with `fallback_injected=True` and
displayed with a `[local boost]` tag in the CLI output.

Example — Trigger A in action:

```
Query : 'silver necklace charm women'
#  SKU         Title                                 Category    RWF      Sim    Note
1  RW-0284     silver necklace Rwandan design        jewellery   41,500   0.333  [local boost]
2  INTL-J001   Pandora silver necklace charm women   jewellery   85,000   0.562
3  RW-0255     silver necklace Rwandan design        jewellery   29,500   0.333
```

Pandora has the highest raw similarity (0.562) but gets pushed to rank 2; the
local jeweller (0.333) is promoted to rank 1.

### Real Rwandan brands hardcoded into the catalog

To make the demo credible, the catalog includes **12 products from three verified
Rwandan companies** (in addition to 400 synthetic local products):

| Brand | Founder(s) | Category | Products |
|-------|-----------|----------|----------|
| **Inzuki Designs** | Teta Isibo | jewellery, basketry, apparel | 6 |
| **UZURI K&Y** | Kevine Kagirimpundu, Yvette Shimwe | leather (footwear) | 3 |
| **Urwibutso Enterprise** | Sina Gerard | home-decor (artisanal gift sets) | 3 |

Real-brand vs international ratio in the branded section: **30% / 70%** (12 vs 28).

### Fairness cap *(stretch goal)*

`_apply_fairness_cap` limits any single `artisan_id` to no more than 15% of the
top-10 returned slots per query. Verified across all 120 evaluation queries:
**0 violations**.

---

## Data Schema

### `catalog.csv` — 440 products

| Column | Type | Description |
|--------|------|-------------|
| `sku` | string | Unique SKU. `RW-NNNN` for synthetic locals, `INZUKI-*`/`UZURI-*`/`SINAG-*` for real brands, `INTL-*` for international |
| `title` | string | Product title |
| `description` | string | Marketing copy |
| `category` | enum | `apparel`, `leather`, `basketry`, `jewellery`, `home-decor` |
| `material` | string | e.g. `cow-leather`, `sweetgrass`, `kitenge-fabric` |
| `origin_district` | string | One of 20 Rwandan districts (empty for international) |
| `price_rwf` | int | Rwandan franc price |
| `artisan_id` | string | Stable ID per artisan; `INZUKI`/`UZURI`/`SINAG` for real brands; empty for international |
| `is_local` | bool | `True` for Made-in-Rwanda, `False` for international |

### `queries.csv` — 120 queries

| Column | Type | Description |
|--------|------|-------------|
| `query_id` | string | Stable ID |
| `query_text` | string | Raw search text |
| `language` | enum | `en`, `fr`, `code-switched`, `misspelled` |
| `global_best_match_sku` | string | Baseline answer used for NDCG@5 — points to international brands for 30/120 queries so the metric is non-trivial |

### `click_log.csv` — 5,000 click events

| Column | Type | Description |
|--------|------|-------------|
| `click_id` | int | Sequential ID |
| `query_id` | string | FK → `queries.query_id` |
| `clicked_sku` | string | FK → `catalog.sku` (local SKUs only — clicks are artisan-tracked) |
| `position` | int | Rank position when clicked |
| `dwell_time_s` | float | Synthetic dwell time |
| `timestamp` | datetime | Synthetic UTC timestamp |

Click distribution includes position-bias noise (top-ranked items get clicked
more even when they aren't strictly the most relevant).

---

## Evaluation

Run the full evaluation in [`eval.ipynb`](eval.ipynb). Key methodology:

- **NDCG@5** — single relevant document per query (`global_best_match_sku`),
  binary relevance, log-base-2 discount. Low absolute values are expected because
  the fairness cap diversifies *away from* a single global-best SKU.
- **Local-presence rate (top-3)** — % of queries that have ≥1 local product in
  positions 1–3. Reported **with and without** local-boost so the boost's effect
  is visible.
- **Latency** — `time.perf_counter()` around `recommend()` only (the index is
  already built). Reports mean, p95, max.
- **Fairness** — for each query, count occurrences of each `artisan_id` in the
  top-10 and check no count exceeds 15%.

### Results

| Metric | Value | Notes |
|--------|-------|-------|
| NDCG@5 | 0.069 | Diversification reduces score vs pure relevance — see eval.ipynb §4 |
| Local-presence rate (top-3, with boost) | **100%** | All queries have ≥1 local product in top-3 |
| Local-presence rate (top-3, without boost) | ~95% | Boost intervenes on ~5% of queries |
| Mean query latency | **<5 ms** | p95 <8 ms |
| 250 ms latency budget | **PASS** | All 120 queries under limit |
| Fairness cap violations | **0** | No artisan >15% of top-10 on any query |

---

## Why TF-IDF (and not sentence embeddings)?

A sentence-transformer baseline (`paraphrase-multilingual-MiniLM-L12-v2`) was built
on the [`feat/sentence-transformer`](https://github.com/DrUkachi/ktt-made-in-rwanda/tree/feat/sentence-transformer)
branch and produced higher cosine scores on French queries (0.6+) without any
dictionary. But it loses on three axes that matter for this hackathon:

| Axis | TF-IDF (master) | Sentence transformers (branch) |
|------|----------------|--------------------------------|
| Query latency | **~2 ms** | ~45 ms warm, 2 s cold |
| First-run cost | none | 120 MB download from Hugging Face |
| Reproducibility | 2 commands | 2 commands + model cache |
| Interpretability | `vectorizer.get_feature_names_out()` | opaque 384-d vectors |
| French handling | 60-line dictionary | native |
| Brief alignment | "TF-IDF or sentence-embedding" | also valid |

For an offline, low-tech distribution context — the actual product context for
this brief — TF-IDF is the right call. The branch is preserved as evidence of
honest engineering comparison.

---

## Product & Business Adaptation

See [`dispatcher.md`](dispatcher.md) for the full artifact:

- Weekly leads workflow for a leatherworker in Nyamirambo (no smartphone)
- Three contact protocols: SMS digest, field-agent voice call, cooperative visit
- SMS templates in English and Kinyarwanda (160-char, feature-phone safe)
- 3-month pilot plan: 20 artisans, ~$173 total cost, 1.3× break-even GMV

---

## Reproducibility

Everything is deterministic from `seed=42`:

```bash
python generate_data.py
# Generated 80 artisans
# OK  catalog.csv -- 440 rows
#     412 local (Made in Rwanda) + 28 international brand products
# OK  queries.csv -- 120 rows
#     30/120 queries have an international brand as global_best_match
# OK  click_log.csv -- 5000 rows
```

The TF-IDF index is rebuilt from `catalog.csv` on every run; there is no cache to
invalidate. Latency benchmarks in `eval.ipynb` use `time.perf_counter()` and are
re-runnable.

---

## Limitations & Future Work

- **Synthetic catalog dominates.** 400 of 440 catalog rows are template-generated
  (e.g. eight near-identical "cow leather boots" SKUs). This inflates similarity
  ties and makes the fairness cap a frequent intervention rather than an edge
  case. Real artisan catalogs would be smaller and more idiosyncratic.
- **No personalisation.** The 10% popularity term is a global signal. Per-buyer
  click history is not modelled.
- **Click log is synthetic.** Position bias is injected, but the underlying click
  distribution is not learned from real user behaviour.
- **FR→EN dictionary, not lemmatisation.** Plurals and conjugations beyond the 60
  mapped tokens fall through unchanged. spaCy's `fr_core_news_sm` would help, at
  the cost of a 45 MB extra dependency — rejected for Tier 1 reproducibility.
- **No image features.** Visual similarity (e.g. CLIP) would help for queries
  like "rustic wooden bowl" where wording varies.

---

## 4-Minute Video

[Watch my 4-minute pitch](https://drive.google.com/file/d/1zBdk06YJq82QvwClM4zNa-KO3NAauk12/view?usp=drive_link)

---

## License

MIT — see [LICENSE](LICENSE)
