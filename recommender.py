#!/usr/bin/env python3
"""
recommender.py — 'Made in Rwanda' content-based niche-first recommender.
Embedding backend: paraphrase-multilingual-MiniLM-L12-v2 (sentence-transformers).

Usage:
    python recommender.py --q 'leather boots'
    python recommender.py --q 'cadeau en cuir pour femme' --n 5
    python recommender.py --q 'agaseke basket gift' --threshold 0.25
"""

import argparse
import contextlib
import io
import logging
import os
import time
import warnings
from pathlib import Path
from typing import Dict, List, Optional

# ---- silence HF Hub noise BEFORE importing sentence_transformers ----
# HF_HUB_OFFLINE is read at huggingface_hub import time, so it must be set here.
# We only go offline when the model is already in the local cache so that a
# first-run download still works normally.
_HF_CACHE = Path.home() / ".cache" / "huggingface" / "hub"
_MODEL_CACHE_DIR = "models--paraphrase-multilingual-MiniLM-L12-v2"
if (_HF_CACHE / _MODEL_CACHE_DIR).exists():
    os.environ["HF_HUB_OFFLINE"] = "1"

os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")

import numpy as np
import pandas as pd
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    from sentence_transformers import SentenceTransformer

logging.getLogger("transformers").setLevel(logging.ERROR)
logging.getLogger("sentence_transformers").setLevel(logging.ERROR)
logging.getLogger("huggingface_hub").setLevel(logging.ERROR)


@contextlib.contextmanager
def _quiet():
    """Redirect stdout+stderr to /dev/null for the duration of the block."""
    sink = io.StringIO()
    with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
        yield


CATALOG_PATH = Path(__file__).parent / "catalog.csv"
CLICK_LOG_PATH = Path(__file__).parent / "click_log.csv"
CACHE_PATH = Path(__file__).parent / ".embedding_cache.npz"

# Model: multilingual MiniLM — handles EN, FR, Kinyarwanda code-switching natively.
# ~120 MB download, cached after first run.
MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"

# Sentence embeddings produce much higher cosine scores than TF-IDF sparse vectors,
# so the fallback threshold is calibrated accordingly.
SIMILARITY_THRESHOLD = 0.25

ARTISAN_CAP_FRACTION = 0.15
TOP_N_DEFAULT = 5


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_text(df: pd.DataFrame) -> List[str]:
    """Concatenate text fields into one string per product for embedding."""
    return (
        df["title"].fillna("") + " "
        + df["description"].fillna("") + " "
        + df["category"].fillna("") + " "
        + df["material"].fillna("")
    ).tolist()


def _load_popularity(click_log_path: Path, catalog: pd.DataFrame) -> np.ndarray:
    """Return a normalised (0–1) popularity score per catalog row from click counts."""
    try:
        clicks = pd.read_csv(click_log_path)
        counts = clicks["clicked_sku"].value_counts()
        pop = catalog["sku"].map(counts).fillna(0).to_numpy(dtype=float).copy()
    except Exception:
        pop = np.zeros(len(catalog), dtype=float)
    max_c = pop.max()
    if max_c > 0:
        pop /= max_c
    return pop


# Category keyword map — used for fallback injection; kept broad to cover
# EN, FR, and common Kinyarwanda terms.
_CATEGORY_KEYWORDS: Dict[str, List[str]] = {
    "leather": [
        "leather", "cuir", "lether", "bag", "sac", "boot", "botte",
        "sandal", "sandle", "wallet", "purse", "sleeve", "belt", "maroquin",
    ],
    "apparel": [
        "shirt", "chemise", "dress", "robe", "scarf", "top", "blouse",
        "skirt", "jupe", "trousers", "blazer", "headwrap", "igitenge",
        "vetement", "vêtement", "fashion", "clothes", "cloth", "apparel",
        "mode", "tissu",
    ],
    "basketry": [
        "basket", "panier", "agaseke", "weave", "woven", "tray", "storage",
        "baskett", "corbeille", "vannerie",
    ],
    "jewellery": [
        "necklace", "collier", "ring", "bague", "bracelet", "earring",
        "boucle", "jewel", "bijou", "pendant", "bead", "brass", "laiton",
        "bijoux", "urukundo",
    ],
    "home-decor": [
        "vase", "bowl", "decor", "décor", "home", "candle", "bougie",
        "frame", "pillow", "cushion", "ceramic", "céramique", "ceramique",
        "glass", "serving", "maison",
    ],
}


def _guess_category(query: str) -> Optional[str]:
    """Return the most likely catalog category for `query`, or None."""
    q = query.lower()
    for cat, keywords in _CATEGORY_KEYWORDS.items():
        if any(kw in q for kw in keywords):
            return cat
    return None


# ---------------------------------------------------------------------------
# Recommender
# ---------------------------------------------------------------------------

class MadeInRwandaRecommender:
    """
    Content-based 'niche-first' recommender using multilingual sentence embeddings.

    Algorithm
    ---------
    1. At init, encode all catalog texts with paraphrase-multilingual-MiniLM-L12-v2
       and cache the resulting matrix to disk (.embedding_cache.npz).
       Subsequent runs load the cache and skip re-encoding (~2s → <0.1s).
    2. At query time, encode the query string (single forward pass, ~20–80 ms CPU).
    3. Cosine similarity between the query embedding and all catalog embeddings.
    4. Blend with a 10% click-log popularity signal to break ties.
    5. Local-boost: if the top result is an international brand, promote the
       best-ranked local product to rank 1. If the top result is local but below
       `similarity_threshold`, inject the curated category fallback instead.
    6. Fairness cap: no artisan occupies > 15% of the top-K returned slots.
    """

    def __init__(
        self,
        catalog_path: Path = CATALOG_PATH,
        click_log_path: Path = CLICK_LOG_PATH,
        similarity_threshold: float = SIMILARITY_THRESHOLD,
        cache_path: Path = CACHE_PATH,
    ):
        self.similarity_threshold = similarity_threshold
        self.catalog = pd.read_csv(catalog_path)
        self._popularity = _load_popularity(click_log_path, self.catalog)
        with _quiet(), warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self._model = SentenceTransformer(MODEL_NAME)
        self._catalog_embeddings = self._load_or_build_embeddings(cache_path)
        self._curated: Dict[str, int] = self._build_curated_fallbacks()

    # ------------------------------------------------------------------
    # Embedding index
    # ------------------------------------------------------------------

    def _load_or_build_embeddings(self, cache_path: Path) -> np.ndarray:
        texts = _build_text(self.catalog)

        if cache_path.exists():
            data = np.load(cache_path)
            # Invalidate cache if catalog size changed
            if data["embeddings"].shape[0] == len(texts):
                return data["embeddings"]

        print(f"Building embedding index for {len(texts)} products… ", end="", flush=True)
        t0 = time.perf_counter()
        embeddings = self._model.encode(
            texts,
            batch_size=64,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,   # unit vectors → dot product == cosine sim
        )
        elapsed = time.perf_counter() - t0
        np.savez(cache_path, embeddings=embeddings)
        print(f"done ({elapsed:.1f}s). Cached to {cache_path.name}")
        return embeddings

    def _build_curated_fallbacks(self) -> Dict[str, int]:
        """Pre-select the highest-popularity LOCAL catalog index per category."""
        fallbacks: Dict[str, int] = {}
        is_local = self._is_local_mask()
        for cat in self.catalog["category"].unique():
            mask = (self.catalog["category"] == cat) & is_local
            idxs = self.catalog.index[mask].tolist()
            if idxs:
                fallbacks[cat] = idxs[int(np.argmax(self._popularity[idxs]))]
        return fallbacks

    def _is_local_mask(self) -> "pd.Series":
        """Return boolean Series: True for Made-in-Rwanda products."""
        if "is_local" in self.catalog.columns:
            return self.catalog["is_local"].astype(bool)
        return pd.Series([True] * len(self.catalog), index=self.catalog.index)

    # ------------------------------------------------------------------
    # Fairness cap
    # ------------------------------------------------------------------

    def _apply_fairness_cap(
        self, ranked: List[int], k: int, max_per_artisan: int
    ) -> List[int]:
        artisan_counts: Dict[str, int] = {}
        accepted: List[int] = []
        deferred: List[int] = []

        for idx in ranked:
            artisan = str(self.catalog.iloc[idx]["artisan_id"])
            count = artisan_counts.get(artisan, 0)
            if count < max_per_artisan:
                artisan_counts[artisan] = count + 1
                accepted.append(idx)
            else:
                deferred.append(idx)
            if len(accepted) == k:
                break

        for idx in deferred:
            if len(accepted) >= k:
                break
            artisan = str(self.catalog.iloc[idx]["artisan_id"])
            count = artisan_counts.get(artisan, 0)
            if count < max_per_artisan:
                artisan_counts[artisan] = count + 1
                accepted.append(idx)

        return accepted

    # ------------------------------------------------------------------
    # Core recommend
    # ------------------------------------------------------------------

    def recommend(self, query: str, n: int = TOP_N_DEFAULT) -> pd.DataFrame:
        """
        Return top-n local recommendations for `query`.

        Columns: sku, title, category, material, origin_district,
                 price_rwf, artisan_id, similarity, fallback_injected
        """
        # 1. Encode query (the model handles EN/FR/Kinyarwanda natively)
        q_emb = self._model.encode(
            [query],
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )

        # 2. Cosine similarity (dot product because embeddings are unit-normalised)
        sims: np.ndarray = (self._catalog_embeddings @ q_emb.T).flatten()

        # 3. Blend with popularity: 90% semantic, 10% popularity
        blended: np.ndarray = 0.90 * sims + 0.10 * self._popularity

        # 4. Sort descending
        ranked: List[int] = np.argsort(-blended).tolist()

        # 5. Local-boost
        #    Trigger A: top result is an international (non-local) brand — promote
        #               the highest-ranked local product to position 1.
        #    Trigger B: top result is local but similarity is very weak — inject
        #               the curated category fallback (most-clicked local product).
        #    Without this, international brands with polished English descriptions
        #    would dominate the ranking; the local-presence rate would be < 100%.
        is_local = self._is_local_mask().values
        fallback_at_top = False
        top_is_local = bool(is_local[ranked[0]])
        top_sim = float(sims[ranked[0]])

        if not top_is_local:
            # Find the best-ranked local product and promote it to rank 1
            for i, idx in enumerate(ranked):
                if bool(is_local[idx]):
                    if i > 0:
                        ranked.pop(i)
                        ranked.insert(0, idx)
                        fallback_at_top = True
                    break
        elif top_sim < self.similarity_threshold:
            # Local but very weak match — inject curated category fallback
            cat = _guess_category(query)
            if cat and cat in self._curated:
                fb_idx = self._curated[cat]
                if fb_idx in ranked:
                    ranked.remove(fb_idx)
                ranked.insert(0, fb_idx)
                fallback_at_top = True

        # 6. Fairness cap over max(n, 10) candidates
        k = max(n, 10)
        max_slots = max(1, int(k * ARTISAN_CAP_FRACTION))
        capped = self._apply_fairness_cap(ranked, k=k, max_per_artisan=max_slots)

        # 7. Slice to n
        result_idxs = capped[:n]
        result = self.catalog.iloc[result_idxs].copy()
        result["similarity"] = sims[result_idxs]
        result["fallback_injected"] = False
        if fallback_at_top and result_idxs:
            result.iloc[0, result.columns.get_loc("fallback_injected")] = True

        result = result.reset_index(drop=True)
        result.index = result.index + 1
        result.index.name = "rank"

        return result[[
            "sku", "title", "category", "material",
            "origin_district", "price_rwf", "artisan_id",
            "similarity", "fallback_injected",
        ]]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _print_results(results: pd.DataFrame, query: str, elapsed_ms: float) -> None:
    print(f"\nQuery : '{query}'")
    print(f"Time  : {elapsed_ms:.1f} ms\n")
    header = (
        f"{'#':<3} {'SKU':<10} {'Title':<38} {'Category':<12} "
        f"{'RWF':>8}  {'District':<14} {'Sim':>5}  Note"
    )
    print(header)
    print("-" * len(header))
    for rank, row in results.iterrows():
        title = str(row["title"])
        if len(title) > 36:
            title = title[:35] + "…"
        note = "[local boost]" if row["fallback_injected"] else ""
        print(
            f"{rank:<3} {row['sku']:<10} {title:<38} {row['category']:<12} "
            f"{int(row['price_rwf']):>8,}  {row['origin_district']:<14} "
            f"{row['similarity']:>5.3f}  {note}"
        )
    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Made in Rwanda — niche-first recommender (multilingual embeddings)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python recommender.py --q 'leather boots'
  python recommender.py --q 'cadeau en cuir pour femme'
  python recommender.py --q 'agaseke basket gift' --threshold 0.2
""",
    )
    parser.add_argument("--q", required=True, metavar="QUERY",
                        help="Search query")
    parser.add_argument("--n", type=int, default=TOP_N_DEFAULT, metavar="N",
                        help=f"Number of results (default: {TOP_N_DEFAULT})")
    parser.add_argument("--threshold", type=float, default=SIMILARITY_THRESHOLD,
                        metavar="T",
                        help=f"Min similarity before fallback kicks in (default: {SIMILARITY_THRESHOLD})")
    parser.add_argument("--catalog", default=str(CATALOG_PATH), metavar="PATH")
    parser.add_argument("--clicks", default=str(CLICK_LOG_PATH), metavar="PATH")
    parser.add_argument("--cache", default=str(CACHE_PATH), metavar="PATH",
                        help="Path to embedding cache (.npz)")
    args = parser.parse_args()

    rec = MadeInRwandaRecommender(
        catalog_path=Path(args.catalog),
        click_log_path=Path(args.clicks),
        similarity_threshold=args.threshold,
        cache_path=Path(args.cache),
    )

    t0 = time.perf_counter()
    results = rec.recommend(args.q, n=args.n)
    elapsed_ms = (time.perf_counter() - t0) * 1_000

    _print_results(results, args.q, elapsed_ms)


if __name__ == "__main__":
    main()
