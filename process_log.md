# Process Log — S2.T1.3 · 'Made in Rwanda' Content Recommender

## Hour-by-Hour Timeline

| Time (approx.) | Activity |
|----------------|----------|
| 0:00–0:20 | Read brief in full. Reviewed scaffold: existing `generate_data.py`, `catalog.csv`, `queries.csv`, `click_log.csv`. Noted what was missing: `recommender.py`, `eval.ipynb`, `dispatcher.md`. |
| 0:20–1:00 | **Phase 2 — TF-IDF recommender.** Built TF-IDF index (unigram+bigram, sublinear TF) over `title + description + category + material`. Implemented cosine similarity ranking with 10% click-log popularity blend. Added local-boost rule and curated fallback logic. Shipped CLI (`--q`, `--n`, `--threshold` flags). Tested on English, misspelled, and code-switched queries. |
| 1:00–1:20 | **French robustness.** Noticed TF-IDF gave 0.000 similarity to all French queries. Evaluated three options (FR→EN dictionary, catalog augmentation, multilingual embeddings). Chose FR→EN dictionary as the immediate fix — added `_normalize_query()` with ~60 term mappings covering all 5 product categories. |
| 1:20–1:45 | Committed Phase 2 to `master`. Created `feat/sentence-transformer` branch. Replaced TF-IDF backend with `paraphrase-multilingual-MiniLM-L12-v2`. Tested latency (45 ms first query, ~10 ms warm). Confirmed French queries now return real semantic matches (sim 0.607) without any dictionary. Suppressed noisy HF Hub output by setting `HF_HUB_OFFLINE=1` before import when model is cached. |
| 1:45–2:30 | **Phase 3 — Evaluation.** Wrote `eval.ipynb` with NDCG@5, local-presence rate, latency stats, and fairness cap audit. Executed against all 120 queries. Documented why NDCG@5 is expected to be low (fairness diversification away from global-best SKU). |
| 2:30–3:15 | **Phase 4 — dispatcher.md.** Designed the weekly lead aggregation pipeline. Wrote 4 contact protocol variants (standard SMS, Kinyarwanda SMS, high-demand alert, voice call script). Modelled conversion funnel and 3-month pilot unit economics (20 artisans, ~$173 total, 5.3× break-even GMV). |
| 3:15–3:45 | **Phase 5 — Documentation.** Updated `README.md` with accurate metrics, 2-command Colab reproducibility, and Hugging Face model link. Filled `process_log.md`. Updated `requirements.txt` with `sentence-transformers`. |
| 3:45–4:00 | Final checks: ran both branches end-to-end, verified all files present, pushed to GitHub. |

---

## LLM / Tool Usage

| Tool | Version | Why I Used It |
|------|---------|---------------|
| **Claude Code** (Anthropic) | claude-sonnet-4-6 | Primary coding assistant throughout. Used for: generating `recommender.py` boilerplate, implementing the fairness cap algorithm, writing `eval.ipynb` cell-by-cell, drafting `dispatcher.md` structure, and suppressing HF Hub startup noise. All output was reviewed, tested, and in several cases corrected before committing. |
| **Git / GitHub** | — | Version control. Committed each phase separately so the evaluator can follow the build-up (`git log --oneline`). |
| **Jupyter / nbconvert** | — | Executed `eval.ipynb` in-place to produce real output cells before committing. |

---

## Three Sample Prompts I Actually Sent

**Prompt 1** — kicking off Phase 2:
> *"This is the context of what I am working on. The existing code is a scaffold or placeholder. I want to get to working code in the next 2 hours. Let's work on Phase 2 — build a TF-IDF index over the catalog's text fields (title + description + category + material), implement cosine similarity search, add the local-boost rule: if the top global match has no local substitute within a similarity threshold, inject a curated fallback. Wrap it in a CLI: python recommender.py --q 'leather boots'."*

**Why:** I had the scaffold and the brief in hand. One concrete prompt with all four subtasks prevented Claude from going off in the wrong direction. I wanted a single working file, not a research discussion.

---

**Prompt 2** — after seeing French queries return zeros:
> *"How do we make it robust to French language?"*

**Why:** Short deliberate question to force a tradeoffs discussion before committing to implementation. Claude offered three options (dictionary, catalog augmentation, multilingual embeddings). I evaluated them myself and chose the dictionary first, then chose embeddings on the branch — the decision was mine, not the model's.

---

**Prompt 3** — deciding to branch for embeddings:
> *"Let's commit this version using 'Phase 2: TF-IDF recommender with local-boost + CLI', then create a new branch and use it with a sentence transformer — see if we can get improved results within the time limit."*

**Why:** I wanted to preserve the TF-IDF baseline (required by the brief) on `master` while exploring whether sentence embeddings fit within the 250 ms constraint. Phrasing it as "see if we can" kept the experiment honest — I was genuinely uncertain about latency before testing.

---

## One Prompt I Discarded (and Why)

**Prompt (discarded):**
> *"Add spaCy French language processing to handle multilingual queries. Install fr_core_news_sm and use it to lemmatise French tokens before TF-IDF matching."*

**Why I discarded it:** After reflection, spaCy's `fr_core_news_sm` model is ~45 MB and requires a separate `python -m spacy download fr_core_news_sm` step, breaking the ≤2-command Colab reproducibility requirement. It also adds a second large dependency for a problem that a 60-entry dictionary solved in 20 lines of stdlib-only code. The lemmatisation benefit wasn't worth the complexity cost at Tier 1.

---

## Hardest Decision

**Whether to submit TF-IDF (brief-compliant) or sentence embeddings (better results) as the primary backend.**

The brief explicitly asks for "TF-IDF or sentence-embedding index" and the video walk-through names TF-IDF specifically. Switching wholesale to embeddings risked looking like I missed the point. But keeping TF-IDF meant submitting a system that scored 0.000 on one-third of evaluation queries — all the French ones — which felt indefensible in a live demo where the required demo query is `cadeau en cuir pour femme`.

I resolved this by doing both: TF-IDF with FR→EN normalization on `master` (shows I understood the brief and can build a lightweight baseline), and sentence embeddings on `feat/sentence-transformer` (shows depth and honest engineering judgement). The README explains the evolution explicitly. In the live defense I can walk either branch and defend the tradeoffs of each. The TF-IDF question in the video is answered from a position of having actually compared the two — not guessing.
