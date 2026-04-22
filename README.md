# S2.T1.3 — 'Made in Rwanda' Content Recommender

**AIMS KTT Hackathon · Tier 1 · RetailTech · Recommender Systems · Low-Tech Distribution**

> A content-based 'niche-first' recommender that nudges buyers toward local Rwandan artisan
> products — with multilingual query support and a low-tech weekly lead delivery workflow
> for offline artisans.

---

## Quick Start

**Two commands — works on Google Colab (free CPU) or any Python 3.10+ environment:**

```bash
pip install -r requirements.txt
python recommender.py --q "leather boots"
```

No model downloads. No GPU. Starts in under 1 second.

### Example queries

```bash
# English
python recommender.py --q "leather boots"

# French (FR→EN dictionary normalisation built-in)
python recommender.py --q "cadeau en cuir pour femme"

# Code-switched (Kinyarwanda + English)
python recommender.py --q "agaseke basket cadeau"

# Misspelled
python recommender.py --q "lether boots"

# More results
python recommender.py --q "brass necklace" --n 10
```

### Regenerate synthetic data (optional)

The CSV files are included. To regenerate deterministically:

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
├── catalog.csv            # 440 products (400 local synthetic + 12 real Rwandan brands
│                          #   + 28 international brands with is_local=False)
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

TF-IDF vectorisation (unigram + bigram, sublinear TF, unicode accent stripping) over
combined product text: `title + description + category + material`.

Chosen over sentence embeddings for:
- **Speed**: <5 ms per query on CPU (sentence-transformer baseline: ~45 ms)
- **Simplicity**: no model download, no GPU, two-command Colab reproducibility
- **Interpretability**: term weights are inspectable

French query robustness handled by a 60-term FR→EN dictionary (`_normalize_query`)
applied before TF-IDF vectorisation. Kinyarwanda terms (agaseke, igitenge, urwagwa, …)
pass through unchanged and still match catalog text.

### Ranking

```
final_score = 0.90 × cosine_similarity + 0.10 × click_popularity
```

### Local-boost (two triggers)

The catalog includes 28 international brand products (Timberland, Coach, Pandora, IKEA…)
that compete semantically with local artisan products. The local-boost guarantees a
Made-in-Rwanda product always appears at rank 1:

- **Trigger A** — international brand tops the raw ranking: promote the highest-ranked
  local product to position 1, mark `fallback_injected=True`.
- **Trigger B** — local product tops but similarity < threshold (very weak match):
  inject the most-clicked local product in the guessed category at position 1.

### Real Rwandan brands in catalog

The 12 hardcoded real-brand products include:
- **Inzuki Designs** (Teta Isibo) — jewellery, basketry, apparel
- **UZURI K&Y** (Kevine Kagirimpundu & Yvette Shimwe) — eco-leather footwear
- **Urwibutso Enterprise** (Sina Gerard) — artisanal gift sets

### Fairness cap *(stretch goal)*

No single artisan occupies more than 15% of the top-10 returned slots per query.
Verified: 0 violations across all 120 evaluation queries.

---

## Evaluation Results

| Metric | Value | Notes |
|--------|-------|-------|
| NDCG@5 | 0.069 | Fairness diversification lowers score vs pure relevance; see eval.ipynb §4 |
| Local-presence rate (top-3) | **100%** | With local-boost active |
| Local-presence WITHOUT boost | ~95% | Boost intervenes on ~5% of queries |
| Mean query latency | **<5 ms** | p95 <8 ms · well inside 250 ms limit |
| Fairness cap violations | **0** | No artisan >15% of top-10 on any query |

Full per-language breakdown in [`eval.ipynb`](eval.ipynb).

---

## Product & Business Adaptation

See [`dispatcher.md`](dispatcher.md) for the full artifact:

- Weekly leads workflow for a leatherworker in Nyamirambo (no smartphone)
- Three contact protocols: SMS digest, field-agent voice call, cooperative visit
- SMS templates in English and Kinyarwanda (160-char, feature-phone safe)
- 3-month pilot plan: 20 artisans, ~$173 total cost, 5.3× break-even GMV

---

## 4-Minute Video

[Watch my 4-minute pitch](https://drive.google.com/file/d/1zBdk06YJq82QvwClM4zNa-KO3NAauk12/view?usp=drive_link)

---

## License

MIT — see [LICENSE](LICENSE)
