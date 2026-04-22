# S2.T1.3 — 'Made in Rwanda' Content Recommender

**AIMS KTT Hackathon · Tier 1 · RetailTech · Recommender Systems · Low-Tech Distribution**

> A content-based 'niche-first' recommender that nudges buyers toward local Rwandan artisan products, with a low-tech lead distribution workflow for offline artisans.

---

## Quick Start

**Two commands — works on Google Colab (free CPU) or any Python 3.10+ environment:**

```bash
pip install -r requirements.txt
python recommender.py --q "leather boots"
```

### Try More Queries

```bash
# French query
python recommender.py --q "cadeau en cuir pour femme"

# Code-switched query
python recommender.py --q "agaseke basket gift"

# Evaluate on all 120 queries
python recommender.py --evaluate
```

### Regenerate Data (optional)

The CSV files are included in this repo, but you can regenerate them deterministically:

```bash
python generate_data.py   # seed=42, produces identical output every time
```

---

## Project Structure

```
.
├── recommender.py         # Core recommender — TF-IDF + local-boost + CLI
├── generate_data.py       # Reproducible synthetic data generator (seed=42)
├── eval.ipynb             # Evaluation notebook: NDCG@5, local-presence rate
│
├── catalog.csv            # 400 products × 8 fields (5 categories, 80 artisans)
├── queries.csv            # 120 queries (EN / FR / code-switched / misspelled)
├── click_log.csv          # 5,000 click events with position-bias noise
│
├── dispatcher.md          # Product & Business: artisan lead workflow + pilot plan
├── process_log.md         # Hour-by-hour timeline + LLM usage declaration
├── SIGNED.md              # Honor code (signed)
│
├── requirements.txt       # Python dependencies (CPU-only)
├── LICENSE                # MIT
└── README.md              # You are here
```

---

## Approach

**Indexing:** TF-IDF vectorisation over combined product text (title + description + category + material). Chosen over sentence embeddings for CPU speed (<250ms query time), interpretability, and simplicity at Tier 1.

**Local-boost:** When the top-ranked result is not from a local artisan within a similarity threshold, the system injects curated local fallbacks into the results. This ensures Rwandan products surface even for generic global queries.

**Fairness cap (stretch):** No single artisan occupies more than 15% of top-10 recommendations on any given day.

---

## Metrics

| Metric | Value |
|--------|-------|
| NDCG@5 | TBD |
| Local-presence rate (top 3) | TBD |
| Avg query latency | TBD |

---

## Product & Business Adaptation

See [dispatcher.md](dispatcher.md) for the full artifact, including:

- Weekly 'leads' workflow for a leatherworker in Nyamirambo without a smartphone
- SMS/voice contact design with sample messages
- 3-month pilot plan with 20 artisans and back-of-envelope unit economics

---

## 4-Minute Video

📹 [Video URL TBD]

---

## License

MIT — see [LICENSE](LICENSE)
