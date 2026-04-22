"""
Synthetic Data Generator for 'Made in Rwanda' Content Recommender
=================================================================
Generates three CSV files:
  - catalog.csv:   400 products × {sku, title, description, category, material, origin_district, price_rwf, artisan_id}
  - queries.csv:   120 anonymised search queries with a 'global_best_match' baseline SKU
  - click_log.csv: 5,000 synthetic click events with position-bias noise

Reproducible with seed=42. Runs in <2 min on a laptop.
"""

import csv
import random
import math
import os

SEED = 42
random.seed(SEED)

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

# ─── Rwanda Districts ────────────────────────────────────────────────
DISTRICTS = [
    "Nyarugenge", "Kicukiro", "Gasabo",          # Kigali
    "Huye", "Muhanga", "Karongi", "Rubavu",       # Southern/Western
    "Musanze", "Nyagatare", "Rwamagana",          # Northern/Eastern
    "Rusizi", "Nyamasheke", "Ngoma", "Bugesera",
    "Nyabihu", "Rutsiro", "Gakenke", "Kayonza",
    "Kirehe", "Gicumbi",
]

# Neighbourhood for product flavour
NEIGHBOURHOODS = {
    "Nyarugenge": ["Nyamirambo", "Biryogo", "Gitega"],
    "Kicukiro": ["Gatenga", "Niboye", "Kanombe"],
    "Gasabo": ["Kimironko", "Remera", "Kacyiru"],
}

# ─── Categories, materials, product templates ────────────────────────
CATEGORIES = {
    "apparel": {
        "materials": ["cotton", "silk", "kitenge-fabric", "ankara-fabric", "linen", "denim"],
        "templates": [
            ("{mat} dress with African print", "Elegant {mat} dress featuring hand-dyed African prints, perfect for formal and casual occasions."),
            ("{mat} shirt with Rwandan motifs", "Handcrafted {mat} shirt adorned with traditional Rwandan geometric motifs."),
            ("Handwoven {mat} scarf", "Soft handwoven {mat} scarf with intricate patterns inspired by Rwandan hill landscapes."),
            ("{mat} skirt with embroidery", "Flowing {mat} skirt with hand-stitched embroidery from local artisans."),
            ("{mat} blazer Kigali style", "Modern {mat} blazer blending contemporary Kigali fashion with traditional textiles."),
            ("{mat} headwrap igitenge", "Vibrant {mat} headwrap (igitenge) in bold colours, a staple of Rwandan fashion."),
            ("{mat} trousers tailored", "Custom-tailored {mat} trousers with a comfortable fit and African-inspired details."),
            ("{mat} baby outfit set", "Adorable {mat} baby clothing set with soft Rwandan-printed fabric, safe for infants."),
        ],
    },
    "leather": {
        "materials": ["cow-leather", "goat-leather", "recycled-leather", "vegetable-tanned-leather"],
        "templates": [
            ("Handmade {mat} boots", "Durable handmade {mat} boots crafted by Kigali leatherworkers, built for comfort and longevity."),
            ("{mat} handbag artisan", "Artisan-made {mat} handbag with hand-stitched seams and brass buckle closure."),
            ("{mat} wallet minimalist", "Slim minimalist {mat} wallet with card slots and coin pocket, hand-finished edges."),
            ("{mat} belt with brass buckle", "Classic {mat} belt featuring a locally forged brass buckle, adjustable sizing."),
            ("{mat} sandals Nyamirambo style", "Open-toe {mat} sandals inspired by Nyamirambo street style, hand-cut soles."),
            ("{mat} laptop sleeve", "Protective {mat} laptop sleeve with soft lining, fits up to 15 inches."),
            ("{mat} journal cover", "Beautiful {mat} journal cover with embossed Rwandan patterns, refillable insert."),
            ("{mat} keychain set", "Set of three {mat} keychains with hand-stamped initials, great as gifts."),
        ],
    },
    "basketry": {
        "materials": ["sisal", "sweetgrass", "banana-leaf", "raffia", "papyrus"],
        "templates": [
            ("Agaseke peace basket {mat}", "Traditional Rwandan agaseke peace basket woven from {mat}, symbolising unity and reconciliation."),
            ("{mat} storage basket large", "Large {mat} storage basket with lid, handwoven by women's cooperative artisans."),
            ("{mat} wall hanging decorative", "Decorative {mat} wall hanging with geometric Imigongo-inspired patterns."),
            ("{mat} fruit bowl", "Elegant {mat} fruit bowl woven with natural dyes, a functional art piece for the home."),
            ("{mat} tray woven", "Flat woven {mat} tray, ideal for serving or as a centrepiece, with zigzag pattern."),
            ("{mat} placemat set of 4", "Set of four {mat} placemats with coordinated colour patterns, handwoven."),
            ("{mat} wine bottle holder", "Unique {mat} wine bottle holder, a conversation starter and perfect gift."),
        ],
    },
    "jewellery": {
        "materials": ["brass", "recycled-metal", "beads", "cow-horn", "wood", "silver"],
        "templates": [
            ("{mat} necklace Rwandan design", "Statement {mat} necklace with pendant inspired by traditional Rwandan royal jewellery."),
            ("{mat} earrings drop style", "Elegant drop-style {mat} earrings, lightweight and handcrafted."),
            ("{mat} bracelet layered", "Layered {mat} bracelet set with adjustable clasp, great for stacking."),
            ("{mat} ring geometric", "Geometric {mat} ring with clean lines, available in multiple sizes."),
            ("{mat} anklet with charms", "{mat} anklet featuring small charms inspired by Lake Kivu waves."),
            ("{mat} brooch traditional", "Traditional-style {mat} brooch with Imigongo pattern inlay."),
            ("{mat} cufflinks artisan", "Handmade {mat} cufflinks with subtle Rwandan motifs, perfect for formal wear."),
        ],
    },
    "home-decor": {
        "materials": ["ceramic", "wood", "recycled-glass", "clay", "bamboo", "banana-bark"],
        "templates": [
            ("{mat} vase hand-painted", "Hand-painted {mat} vase with motifs depicting Rwandan thousand hills landscape."),
            ("{mat} candle holder set", "Set of three {mat} candle holders with carved geometric patterns."),
            ("{mat} wall art Imigongo", "Imigongo-style {mat} wall art panel, traditional cow-dung painting technique."),
            ("{mat} serving bowl", "Large {mat} serving bowl glazed with earth-toned colours, food-safe finish."),
            ("{mat} photo frame", "Rustic {mat} photo frame with hand-carved border, fits 5×7 inch photo."),
            ("{mat} coasters set of 6", "Set of six {mat} coasters with protective felt backing and cultural patterns."),
            ("{mat} lamp shade", "Unique {mat} lamp shade casting warm patterned light, handmade by local craftspeople."),
            ("{mat} incense burner", "Artisan {mat} incense burner with ventilation slots and ash catcher tray."),
        ],
    },
}

# ─── Artisan names ───────────────────────────────────────────────────
FIRST_NAMES = [
    "Jean", "Marie", "Pierre", "Claudine", "Emmanuel", "Diane", "Patrick",
    "Josiane", "Théogène", "Béatrice", "Innocent", "Aimée", "Félicien",
    "Consolée", "Damascène", "Vestine", "Augustin", "Donatha", "Cyprien",
    "Espérance", "Faustin", "Goretti", "Habimana", "Ingabire", "Kalisa",
    "Mukamana", "Ndayisaba", "Uwimana", "Tuyisenge", "Niyonzima",
]

LAST_NAMES = [
    "Mugisha", "Uwimana", "Habimana", "Niyonzima", "Mukamana", "Tuyisenge",
    "Ndayisaba", "Ingabire", "Kalisa", "Nsengimana", "Mukamusoni",
    "Nshimiyimana", "Uwizeye", "Bizimungu", "Gasana", "Hakizimana",
    "Iradukunda", "Kamanzi", "Mahoro", "Rugamba",
]

# ─── Real-ish brand / cooperative names ──────────────────────────────
BRAND_PREFIXES = [
    "Kigali", "Inzuki", "Azizi", "Uruhu", "Ejo", "Umuco", "Ishema",
    "Igitenge", "Imana", "Ubuntu", "Amahoro", "Ikaze", "Tuzamurane",
    "Ubumwe", "Ingabo", "Intore", "Urukundo", "Isoko", "Akeza", "Imena",
]
BRAND_SUFFIXES = [
    "Designs", "Crafts", "Studio", "Workshop", "Collective", "Artisans",
    "Creations", "Handmade", "Co-op", "Atelier",
]


def generate_artisans(n=80):
    """Generate n unique artisans."""
    artisans = []
    used = set()
    for i in range(n):
        while True:
            first = random.choice(FIRST_NAMES)
            last = random.choice(LAST_NAMES)
            name = f"{first} {last}"
            if name not in used:
                used.add(name)
                break
        district = random.choice(DISTRICTS)
        brand = f"{random.choice(BRAND_PREFIXES)} {random.choice(BRAND_SUFFIXES)}"
        artisans.append({
            "artisan_id": f"ART-{i+1:03d}",
            "name": name,
            "district": district,
            "brand": brand,
        })
    return artisans


def generate_catalog(artisans, n=400):
    """Generate n products across all categories."""
    products = []
    sku_counter = 0

    # Distribute products roughly evenly across categories
    cats = list(CATEGORIES.keys())
    per_cat = n // len(cats)
    remainder = n % len(cats)

    for ci, cat in enumerate(cats):
        count = per_cat + (1 if ci < remainder else 0)
        info = CATEGORIES[cat]
        for _ in range(count):
            sku_counter += 1
            mat = random.choice(info["materials"])
            title_tpl, desc_tpl = random.choice(info["templates"])
            title = title_tpl.format(mat=mat.replace("-", " "))
            description = desc_tpl.format(mat=mat.replace("-", " "))

            artisan = random.choice(artisans)

            # Price ranges by category (in RWF)
            price_ranges = {
                "apparel": (3000, 45000),
                "leather": (5000, 80000),
                "basketry": (2000, 35000),
                "jewellery": (1500, 50000),
                "home-decor": (2000, 60000),
            }
            lo, hi = price_ranges[cat]
            price = random.randint(lo // 500, hi // 500) * 500

            products.append({
                "sku": f"RW-{sku_counter:04d}",
                "title": title,
                "description": description,
                "category": cat,
                "material": mat,
                "origin_district": artisan["district"],
                "price_rwf": price,
                "artisan_id": artisan["artisan_id"],
            })

    random.shuffle(products)
    return products


# ─── Queries ─────────────────────────────────────────────────────────
QUERY_TEMPLATES = {
    "en": [
        "leather boots", "leather handbag", "leather wallet", "leather sandals",
        "African print dress", "cotton shirt", "kitenge fabric skirt",
        "handwoven scarf", "baby clothes African", "woven basket",
        "peace basket Rwanda", "storage basket large", "fruit bowl woven",
        "brass necklace", "beaded bracelet", "wooden earrings",
        "ceramic vase", "wall art African", "candle holder set",
        "gift for her", "gift for him", "wedding gift Rwanda",
        "home decoration African", "traditional jewellery",
        "cow horn ring", "recycled glass lamp", "bamboo coasters",
        "artisan belt", "laptop sleeve leather", "journal cover",
        "headwrap African", "Kigali fashion", "Rwandan crafts",
        "handmade shoes", "woven placemat set", "wine holder basket",
        "silver cufflinks", "brooch traditional", "incense burner clay",
        "photo frame wooden",
    ],
    "fr": [
        "bottes en cuir", "sac à main cuir", "portefeuille cuir",
        "robe imprimé africain", "chemise coton", "jupe en tissu kitenge",
        "écharpe tissée", "panier tressé", "panier de paix Rwanda",
        "collier en laiton", "bracelet en perles", "boucles d'oreilles bois",
        "vase en céramique", "décoration murale africaine",
        "cadeau pour femme", "cadeau en cuir pour femme",
        "bijoux traditionnels", "artisanat rwandais",
        "sandales en cuir", "ceinture artisanale",
        "porte-bougie ensemble", "bol en bois",
        "cadre photo bois", "lampe en verre recyclé",
        "sous-verres bambou",
    ],
    "code_switched": [
        "leather boots nziza", "umukenyero cotton dress",
        "agaseke basket gift", "igitenge headwrap nice",
        "amaboko bracelet brass", "urukundo necklace cadeau",
        "imigongo wall art décoration", "isuku ceramic vase",
        "inkweto leather sandals", "umuhango jewellery set",
    ],
    "misspelled": [
        "lether boots", "leater handbag", "baskett woven",
        "necklase brass", "ceramik vase", "sandles leather",
        "jewlery traditional", "handmde wallet", "Rawanda crafts",
        "afrikan print dress",
    ],
}


def generate_queries(products, n=120):
    """Generate n search queries with global_best_match baseline."""
    queries = []
    all_q = []

    # Flatten all query templates
    for lang, qs in QUERY_TEMPLATES.items():
        for q in qs:
            all_q.append((q, lang))

    # Repeat/sample to get n queries
    selected = []
    while len(selected) < n:
        random.shuffle(all_q)
        selected.extend(all_q)
    selected = selected[:n]

    for i, (query_text, lang) in enumerate(selected):
        # Pick a "global best match" — just a random product as baseline
        best_match = random.choice(products)
        queries.append({
            "query_id": f"Q-{i+1:03d}",
            "query_text": query_text,
            "language": lang,
            "global_best_match_sku": best_match["sku"],
        })

    return queries


def generate_click_log(products, queries, n=5000):
    """Generate n click events with position-bias noise model."""
    clicks = []
    skus = [p["sku"] for p in products]

    for i in range(n):
        query = random.choice(queries)
        # Simulate a result list of 10 items
        result_list = random.sample(skus, min(10, len(skus)))

        # Position bias: higher positions get more clicks (1/log2(pos+1))
        position = random.choices(
            range(1, 11),
            weights=[1.0 / math.log2(pos + 1) for pos in range(1, 11)],
            k=1
        )[0]
        clicked_sku = result_list[position - 1]

        # Dwell time with noise (seconds)
        base_dwell = random.gauss(30, 15)
        dwell_time = max(1, round(base_dwell))

        # Timestamp within a 90-day window
        day_offset = random.randint(0, 89)
        hour = random.randint(6, 22)
        minute = random.randint(0, 59)
        timestamp = f"2025-{(day_offset // 30) + 1:02d}-{(day_offset % 30) + 1:02d}T{hour:02d}:{minute:02d}:00"

        clicks.append({
            "click_id": f"CLK-{i+1:05d}",
            "query_id": query["query_id"],
            "clicked_sku": clicked_sku,
            "position": position,
            "dwell_time_s": dwell_time,
            "timestamp": timestamp,
        })

    return clicks


def write_csv(filepath, data, fieldnames):
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)
    print(f"  ✓ {filepath} — {len(data)} rows")


def main():
    print("Generating synthetic data for 'Made in Rwanda' Content Recommender...")
    print(f"  Seed: {SEED}\n")

    artisans = generate_artisans(80)
    print(f"  Generated {len(artisans)} artisans")

    catalog = generate_catalog(artisans, 400)
    write_csv(
        os.path.join(OUTPUT_DIR, "catalog.csv"),
        catalog,
        ["sku", "title", "description", "category", "material", "origin_district", "price_rwf", "artisan_id"],
    )

    queries = generate_queries(catalog, 120)
    write_csv(
        os.path.join(OUTPUT_DIR, "queries.csv"),
        queries,
        ["query_id", "query_text", "language", "global_best_match_sku"],
    )

    click_log = generate_click_log(catalog, queries, 5000)
    write_csv(
        os.path.join(OUTPUT_DIR, "click_log.csv"),
        click_log,
        ["click_id", "query_id", "clicked_sku", "position", "dwell_time_s", "timestamp"],
    )

    print("\n✅ All data generated successfully!")
    print(f"   catalog.csv:   {len(catalog)} products across {len(CATEGORIES)} categories")
    print(f"   queries.csv:   {len(queries)} queries (EN/FR/code-switched/misspelled)")
    print(f"   click_log.csv: {len(click_log)} click events")


if __name__ == "__main__":
    main()
