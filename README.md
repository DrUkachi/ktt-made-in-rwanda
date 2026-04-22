# S2.T1.3 — 'Made in Rwanda' Content Recommender

**AIMS KTT Hackathon · Tier 1 · RetailTech · Recommender Systems · Low-Tech Distribution**

> A content-based 'niche-first' recommender that nudges buyers toward local Rwandan artisan
> products — with a multilingual embedding backend and a low-tech weekly lead delivery
> workflow for offline artisans.

---

## Quick Start

**Two commands — runs on Google Colab free CPU tier:**

```bash
pip install -r requirements.txt
python recommender.py --q "leather boots"
```

> On first run the model (`paraphrase-multilingual-MiniLM-L12-v2`, ~120 MB) downloads
> from Hugging Face and catalog embeddings are cached to `.embedding_cache.npz`.
> All subsequent runs start in under 2 seconds.

### Example queries

```bash
# English
python recommender.py --q "leather boots"

# French
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
├── recommender.py         # Core recommender: multilingual embeddings + local-boost + CLI
├── eval.ipynb             # Evaluation: NDCG@5, local-presence rate, fairness audit
├── dispatcher.md          # Product & Business: offline artisan lead workflow + pilot plan
├── generate_data.py       # Reproducible synthetic data generator (seed=42)
│
├── catalog.csv            # 400 products × 8 fields (5 categories, 80 artisans)
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

### Embedding index

`paraphrase-multilingual-MiniLM-L12-v2` (sentence-transformers) encodes the combined
product text — `title + description + category + material` — into 384-dimensional
vectors at startup. Query encoding takes ~45 ms on CPU.

**Why multilingual embeddings over TF-IDF:**  
TF-IDF was the Phase 1 baseline (see `master` branch). It scored 0.000 similarity on
French queries because the vocabulary was English-only. Sentence embeddings handle
English, French, and Kinyarwanda code-switching natively with no translation dictionary.

### Ranking

```
final_score = 0.90 × cosine_similarity + 0.10 × click_popularity
```

### Local-boost

When the top cosine score falls below `--threshold` (default 0.25), the system injects
the most-clicked product from the query's best-guess category at rank 1. This guarantees
a local Made-in-Rwanda product always appears at the top, even for zero-match queries.

### Fairness cap *(stretch goal)*

No single artisan occupies more than 15% of the top-10 returned slots per query
(`_apply_fairness_cap` in `recommender.py`). Empirically verified: 0 violations across
all 120 evaluation queries.

---

## Evaluation Results

| Metric | Value | Notes |
|--------|-------|-------|
| NDCG@5 | 0.0119 | Low by design — fairness cap diversifies across artisans away from the single global-best SKU; see `eval.ipynb` §4 for explanation |
| Local-presence rate (top-3) | **100.0%** | All catalog products are Made in Rwanda |
| Mean query latency | **10 ms** | p95: 13 ms · max: 45 ms |
| 250 ms constraint | **PASS** | All 120 queries under limit |
| Fairness cap violations | **0** | No artisan > 15% of top-10 on any query |

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

📹 **[VIDEO URL — insert before submission]**

---

## Model

The sentence-transformer model is downloaded automatically from Hugging Face on first run:

- **Model:** `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
- **Size:** ~120 MB
- **Hugging Face:** https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2

---

## License

MIT — see [LICENSE](LICENSE)
