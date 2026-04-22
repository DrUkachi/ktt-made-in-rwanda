#!/usr/bin/env python3
"""
recommender.py — 'Made in Rwanda' content-based niche-first recommender.

Usage:
    python recommender.py --q 'leather boots'
    python recommender.py --q 'cadeau en cuir pour femme' --n 5
    python recommender.py --q 'agaseke basket gift' --threshold 0.05
"""

import argparse
import time
import unicodedata
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

CATALOG_PATH = Path(__file__).parent / "catalog.csv"
CLICK_LOG_PATH = Path(__file__).parent / "click_log.csv"

# Minimum cosine similarity for a result to count as a "good" local match.
# Below this threshold we inject a curated fallback to guarantee local presence.
SIMILARITY_THRESHOLD = 0.10

# Fairness cap (stretch goal): no single artisan fills more than this fraction
# of the top-10 slots for any query.
ARTISAN_CAP_FRACTION = 0.15

TOP_N_DEFAULT = 5


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_text(df: pd.DataFrame) -> pd.Series:
    """Concatenate text fields used for TF-IDF indexing."""
    return (
        df["title"].fillna("") + " "
        + df["description"].fillna("") + " "
        + df["category"].fillna("") + " "
        + df["material"].fillna("")
    )


def _load_popularity(click_log_path: Path, catalog: pd.DataFrame) -> np.ndarray:
    """Return a normalised popularity score (0–1) per catalog row from click counts."""
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


# Category keyword map for fallback injection — covers EN, FR, Kinyarwanda hints
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


# ---------------------------------------------------------------------------
# French → English query normalisation
# ---------------------------------------------------------------------------

# Domain-specific FR→EN term map covering the five product categories.
# Keys are lowercase French tokens (accented and de-accented where they differ).
_FR_TO_EN: Dict[str, str] = {
    # leather & accessories
    "cuir":          "leather",
    "maroquinerie":  "leather",
    "sac":           "bag",
    "sacoche":       "bag",
    "bottes":        "boots",
    "botte":         "boots",
    "chaussures":    "shoes",
    "chaussure":     "shoes",
    "sandales":      "sandals",
    "sandale":       "sandals",
    "portefeuille":  "wallet",
    "ceinture":      "belt",
    # apparel
    "vetements":     "apparel",
    "vetement":      "apparel",
    "chemise":       "shirt",
    "robe":          "dress",
    "jupe":          "skirt",
    "pantalon":      "trousers",
    "foulard":       "scarf",
    "echarpe":       "scarf",
    "tissu":         "fabric",
    "coton":         "cotton",
    "soie":          "silk",
    "lin":           "linen",
    "mode":          "fashion",
    # basketry
    "panier":        "basket",
    "corbeille":     "basket",
    "vannerie":      "basketry",
    "tresse":        "woven",
    "raphia":        "raffia",
    # jewellery
    "bijou":         "jewellery",
    "bijoux":        "jewellery",
    "collier":       "necklace",
    "bague":         "ring",
    "pendentif":     "pendant",
    "perle":         "bead",
    "laiton":        "brass",
    "boucle":        "earring",
    # home-decor
    "maison":        "home",
    "decoration":    "decor",
    "bol":           "bowl",
    "saladier":      "bowl",
    "bougie":        "candle",
    "coussin":       "cushion",
    "cadre":         "frame",
    "ceramique":     "ceramic",
    "verre":         "glass",
    "bois":          "wood",
    # common modifiers / descriptors
    "cadeau":        "gift",
    "femme":         "woman",
    "homme":         "man",
    "enfant":        "child",
    "artisanal":     "artisan",
    "artisanale":    "artisan",
    "traditionnel":  "traditional",
    "traditionnelle":"traditional",
    "naturel":       "natural",
    "naturelle":     "natural",
    "grand":         "large",
    "grande":        "large",
    "petit":         "small",
    "petite":        "small",
    "tisse":         "woven",
    "brode":         "embroidered",
    "sculpte":       "carved",
    "peint":         "painted",
}


def _strip_accents(s: str) -> str:
    """Remove combining diacritical marks (é→e, â→a, etc.)."""
    return "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    )


def _normalize_query(query: str) -> str:
    """
    Translate known French product tokens to their English catalog equivalents.

    Strategy: replace token-by-token using _FR_TO_EN, trying the raw lowercased
    token first and the de-accented form second.  Unknown tokens (including
    French stopwords and Kinyarwanda terms) are kept as-is, so code-switched
    queries like 'agaseke basket cadeau' still work without any loss.

    Examples:
        'cadeau en cuir pour femme'  →  'gift en leather pour woman'
        'bottes sandale cuir'        →  'boots sandals leather'
        'agaseke basket cadeau'      →  'agaseke basket gift'
    """
    out: List[str] = []
    for tok in query.lower().split():
        clean = _strip_accents(tok)
        en = _FR_TO_EN.get(tok) or _FR_TO_EN.get(clean)
        out.append(en if en else tok)
    return " ".join(out)


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
    Content-based 'niche-first' recommender for Made-in-Rwanda products.

    Algorithm
    ---------
    1. TF-IDF (unigram + bigram, sublinear TF, unicode accent stripping)
       built over: title + description + category + material.
    2. Cosine similarity gives the base relevance score per query.
    3. A 10% popularity blend (from click_log) breaks ties between
       equally-matched products.
    4. Local-boost (two triggers):
       Trigger A — top result is international (is_local=False): promote the
                   highest-ranked local product to position 1.
       Trigger B — top result is local but similarity < threshold: inject the
                   most-clicked local product in the guessed category at pos 1.
       Both triggers set fallback_injected=True on the promoted result.
    5. Fairness cap (stretch goal): no single artisan occupies more than 15%
       of the top-K returned slots.
    """

    def __init__(
        self,
        catalog_path: Path = CATALOG_PATH,
        click_log_path: Path = CLICK_LOG_PATH,
        similarity_threshold: float = SIMILARITY_THRESHOLD,
    ):
        self.similarity_threshold = similarity_threshold
        self.catalog = pd.read_csv(catalog_path)
        self._popularity = _load_popularity(click_log_path, self.catalog)
        self._build_tfidf_index()
        self._curated: Dict[str, int] = self._build_curated_fallbacks()

    # ------------------------------------------------------------------
    # Index construction
    # ------------------------------------------------------------------

    def _build_tfidf_index(self) -> None:
        texts = _build_text(self.catalog)
        self.vectorizer = TfidfVectorizer(
            analyzer="word",
            ngram_range=(1, 2),
            min_df=1,
            sublinear_tf=True,        # log(1+tf) dampens very frequent terms
            strip_accents="unicode",  # normalise accented chars (French queries)
            token_pattern=r"(?u)\b\w+\b",
        )
        self.tfidf_matrix = self.vectorizer.fit_transform(texts)

    def _is_local_mask(self) -> "pd.Series":
        """Return boolean Series: True for Made-in-Rwanda products."""
        if "is_local" in self.catalog.columns:
            return self.catalog["is_local"].astype(bool)
        return pd.Series([True] * len(self.catalog), index=self.catalog.index)

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

    # ------------------------------------------------------------------
    # Fairness cap
    # ------------------------------------------------------------------

    def _apply_fairness_cap(
        self, ranked: List[int], k: int, max_per_artisan: int
    ) -> List[int]:
        """
        Re-order `ranked` so no artisan_id appears more than `max_per_artisan`
        times in the first `k` positions.  Overflow items are moved to the back.
        """
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

        # Back-fill from deferred in their original order
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

        Returns a DataFrame (1-based rank as index) with columns:
          sku, title, category, material, origin_district,
          price_rwf, artisan_id, similarity, fallback_injected
        """
        # 1. Normalise French tokens → English before TF-IDF
        normalized = _normalize_query(query)

        # 2. TF-IDF similarity against the full catalog
        q_vec = self.vectorizer.transform([normalized])
        sims: np.ndarray = cosine_similarity(q_vec, self.tfidf_matrix).flatten()

        # 3. Blend with popularity: 90% relevance, 10% popularity
        blended: np.ndarray = 0.90 * sims + 0.10 * self._popularity

        # 4. Sort descending by blended score
        ranked: List[int] = np.argsort(-blended).tolist()

        # 5. Local-boost (two triggers)
        is_local = self._is_local_mask().values
        fallback_at_top = False
        top_is_local = bool(is_local[ranked[0]])
        top_sim = float(sims[ranked[0]])

        if not top_is_local:
            # Trigger A: international brand at top — promote best-ranked local
            for i, idx in enumerate(ranked):
                if bool(is_local[idx]):
                    if i > 0:
                        ranked.pop(i)
                        ranked.insert(0, idx)
                        fallback_at_top = True
                    break
        elif top_sim < self.similarity_threshold:
            # Trigger B: local but weak match — inject curated category fallback
            cat = _guess_category(query)
            if cat and cat in self._curated:
                fb_idx = self._curated[cat]
                if fb_idx in ranked:
                    ranked.remove(fb_idx)
                ranked.insert(0, fb_idx)
                fallback_at_top = True

        # 6. Fairness cap over max(n, 10) candidates (stretch goal)
        k = max(n, 10)
        max_slots = max(1, int(k * ARTISAN_CAP_FRACTION))
        capped = self._apply_fairness_cap(ranked, k=k, max_per_artisan=max_slots)

        # 7. Slice to n results
        result_idxs = capped[:n]
        result = self.catalog.iloc[result_idxs].copy()
        result["similarity"] = sims[result_idxs]
        result["fallback_injected"] = False
        if fallback_at_top and result_idxs:
            result.iloc[0, result.columns.get_loc("fallback_injected")] = True

        result = result.reset_index(drop=True)
        result.index = result.index + 1  # 1-based rank
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
    sep = "-" * len(header)
    print(header)
    print(sep)
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
        description="Made in Rwanda — niche-first content recommender",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python recommender.py --q 'leather boots'
  python recommender.py --q 'cadeau en cuir pour femme' --n 5
  python recommender.py --q 'agaseke basket gift' --threshold 0.05
""",
    )
    parser.add_argument(
        "--q", required=True, metavar="QUERY",
        help="Search query (quote multi-word queries)",
    )
    parser.add_argument(
        "--n", type=int, default=TOP_N_DEFAULT, metavar="N",
        help=f"Number of results to return (default: {TOP_N_DEFAULT})",
    )
    parser.add_argument(
        "--threshold", type=float, default=SIMILARITY_THRESHOLD, metavar="T",
        help=(
            f"Min cosine similarity before curated fallback is injected "
            f"(default: {SIMILARITY_THRESHOLD})"
        ),
    )
    parser.add_argument(
        "--catalog", default=str(CATALOG_PATH), metavar="PATH",
        help="Path to catalog CSV",
    )
    parser.add_argument(
        "--clicks", default=str(CLICK_LOG_PATH), metavar="PATH",
        help="Path to click_log CSV",
    )
    args = parser.parse_args()

    rec = MadeInRwandaRecommender(
        catalog_path=Path(args.catalog),
        click_log_path=Path(args.clicks),
        similarity_threshold=args.threshold,
    )

    t0 = time.perf_counter()
    results = rec.recommend(args.q, n=args.n)
    elapsed_ms = (time.perf_counter() - t0) * 1_000

    _print_results(results, args.q, elapsed_ms)


if __name__ == "__main__":
    main()
