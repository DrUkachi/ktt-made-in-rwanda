"""
Synthetic Data Generator for 'Made in Rwanda' Content Recommender
=================================================================
Generates three CSV files:
  - catalog.csv:   440 products × {sku, title, description, category, material,
                   origin_district, price_rwf, artisan_id, is_local}
                   (400 local synthetic + 12 real Rwandan brands [30%] + 28 international brands [70%])
  - queries.csv:   120 anonymised search queries with a 'global_best_match' baseline SKU
                   (global_best_match points to international brands where they compete)
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

# ─── International brand products (is_local=False) ───────────────────
# These simulate what a global e-commerce algorithm would surface.
# Descriptions intentionally use the same keywords as local products
# so they compete semantically — making the local-boost genuinely needed.
INTERNATIONAL_PRODUCTS = [
    # leather (8)
    {
        "sku": "INTL-L001",
        "title": "Timberland cow leather boots waterproof",
        "description": "Premium waterproof cow leather boots with rubber sole, built for all-day comfort and durability.",
        "category": "leather", "material": "cow-leather",
        "origin_district": "", "price_rwf": 120000, "artisan_id": "", "is_local": False,
    },
    {
        "sku": "INTL-L002",
        "title": "Dr Martens leather boots classic",
        "description": "Iconic leather boots with air-cushioned sole and classic stitching, a wardrobe staple.",
        "category": "leather", "material": "cow-leather",
        "origin_district": "", "price_rwf": 140000, "artisan_id": "", "is_local": False,
    },
    {
        "sku": "INTL-L003",
        "title": "Coach leather handbag women premium",
        "description": "Premium leather handbag with polished hardware, interior pockets, and signature lining.",
        "category": "leather", "material": "cow-leather",
        "origin_district": "", "price_rwf": 250000, "artisan_id": "", "is_local": False,
    },
    {
        "sku": "INTL-L004",
        "title": "Fossil leather wallet slim card holder",
        "description": "Slim bifold leather wallet with multiple card slots, coin pocket, and hand-finished edges.",
        "category": "leather", "material": "cow-leather",
        "origin_district": "", "price_rwf": 55000, "artisan_id": "", "is_local": False,
    },
    {
        "sku": "INTL-L005",
        "title": "Adidas leather sandals comfort sport",
        "description": "Leather sandals with cushioned footbed and adjustable straps, perfect for everyday wear.",
        "category": "leather", "material": "cow-leather",
        "origin_district": "", "price_rwf": 75000, "artisan_id": "", "is_local": False,
    },
    {
        "sku": "INTL-L006",
        "title": "Clarks leather sandals women cushioned",
        "description": "Women's leather sandals with Clarks cushion plus technology, open-toe summer style.",
        "category": "leather", "material": "goat-leather",
        "origin_district": "", "price_rwf": 90000, "artisan_id": "", "is_local": False,
    },
    {
        "sku": "INTL-L007",
        "title": "Samsonite leather laptop sleeve protection",
        "description": "Padded leather laptop sleeve with water-resistant lining, fits 13 to 15 inch laptops.",
        "category": "leather", "material": "cow-leather",
        "origin_district": "", "price_rwf": 65000, "artisan_id": "", "is_local": False,
    },
    {
        "sku": "INTL-L008",
        "title": "Moleskine leather journal cover classic",
        "description": "Classic leather journal cover with elastic closure, bookmark ribbon, and inner pocket.",
        "category": "leather", "material": "cow-leather",
        "origin_district": "", "price_rwf": 48000, "artisan_id": "", "is_local": False,
    },
    # apparel (6)
    {
        "sku": "INTL-A001",
        "title": "H&M cotton shirt men slim fit",
        "description": "Men's slim-fit cotton shirt with button-down collar, available in multiple colours.",
        "category": "apparel", "material": "cotton",
        "origin_district": "", "price_rwf": 18000, "artisan_id": "", "is_local": False,
    },
    {
        "sku": "INTL-A002",
        "title": "Zara linen dress women summer",
        "description": "Lightweight linen dress with V-neck and side pockets, ideal for warm weather.",
        "category": "apparel", "material": "linen",
        "origin_district": "", "price_rwf": 32000, "artisan_id": "", "is_local": False,
    },
    {
        "sku": "INTL-A003",
        "title": "Uniqlo cotton trousers ankle length",
        "description": "Ankle-length cotton trousers with elastic waistband and relaxed fit, wrinkle-resistant.",
        "category": "apparel", "material": "cotton",
        "origin_district": "", "price_rwf": 22000, "artisan_id": "", "is_local": False,
    },
    {
        "sku": "INTL-A004",
        "title": "Gap cotton baby outfit set newborn",
        "description": "Soft cotton baby outfit set including bodysuit and trousers, gentle on newborn skin.",
        "category": "apparel", "material": "cotton",
        "origin_district": "", "price_rwf": 14000, "artisan_id": "", "is_local": False,
    },
    {
        "sku": "INTL-A005",
        "title": "ASOS silk blouse women printed",
        "description": "Flowy silk blouse with abstract print, relaxed fit and cuffed sleeves.",
        "category": "apparel", "material": "silk",
        "origin_district": "", "price_rwf": 28000, "artisan_id": "", "is_local": False,
    },
    # basketry (4)
    {
        "sku": "INTL-B001",
        "title": "IKEA woven storage basket synthetic large",
        "description": "Large synthetic woven storage basket with handles, stackable and easy to clean.",
        "category": "basketry", "material": "sisal",
        "origin_district": "", "price_rwf": 12000, "artisan_id": "", "is_local": False,
    },
    {
        "sku": "INTL-B002",
        "title": "Pottery Barn woven fruit bowl kitchen",
        "description": "Hand-woven fruit bowl for kitchen countertop display, sturdy and decorative.",
        "category": "basketry", "material": "sweetgrass",
        "origin_district": "", "price_rwf": 20000, "artisan_id": "", "is_local": False,
    },
    {
        "sku": "INTL-B004",
        "title": "West Elm woven wine bottle holder",
        "description": "Woven wine bottle holder in natural fibres, holds one standard bottle upright.",
        "category": "basketry", "material": "sisal",
        "origin_district": "", "price_rwf": 11000, "artisan_id": "", "is_local": False,
    },
    # jewellery (6)
    {
        "sku": "INTL-J001",
        "title": "Pandora silver necklace charm women",
        "description": "Sterling silver necklace with signature charm, lobster clasp, and gift box included.",
        "category": "jewellery", "material": "silver",
        "origin_district": "", "price_rwf": 85000, "artisan_id": "", "is_local": False,
    },
    {
        "sku": "INTL-J002",
        "title": "Swarovski crystal earrings drop women",
        "description": "Drop earrings with Swarovski crystals set in rhodium-plated brass, hypoallergenic posts.",
        "category": "jewellery", "material": "recycled-metal",
        "origin_district": "", "price_rwf": 72000, "artisan_id": "", "is_local": False,
    },
    {
        "sku": "INTL-J003",
        "title": "Tiffany brass ring simple band",
        "description": "Simple polished brass band ring, unisex design available in all sizes.",
        "category": "jewellery", "material": "brass",
        "origin_district": "", "price_rwf": 95000, "artisan_id": "", "is_local": False,
    },
    {
        "sku": "INTL-J004",
        "title": "Alex and Ani silver bracelet layered",
        "description": "Expandable wire silver bracelet with charm, designed for layering and stacking.",
        "category": "jewellery", "material": "silver",
        "origin_district": "", "price_rwf": 38000, "artisan_id": "", "is_local": False,
    },
    {
        "sku": "INTL-J005",
        "title": "Cufflinks Inc silver cufflinks formal",
        "description": "Polished silver cufflinks for formal shirts, engraved geometric face, gift boxed.",
        "category": "jewellery", "material": "silver",
        "origin_district": "", "price_rwf": 42000, "artisan_id": "", "is_local": False,
    },
    {
        "sku": "INTL-J006",
        "title": "H Samuel silver brooch vintage floral",
        "description": "Vintage-style floral brooch in sterling silver, pin fastening, gift wrapped.",
        "category": "jewellery", "material": "silver",
        "origin_district": "", "price_rwf": 35000, "artisan_id": "", "is_local": False,
    },
    # home-decor (6)
    {
        "sku": "INTL-H001",
        "title": "IKEA ceramic vase modern minimalist",
        "description": "Minimalist ceramic vase in matte finish, suitable for dried or fresh flowers.",
        "category": "home-decor", "material": "ceramic",
        "origin_district": "", "price_rwf": 8500, "artisan_id": "", "is_local": False,
    },
    {
        "sku": "INTL-H002",
        "title": "Crate and Barrel glass serving bowl large",
        "description": "Large clear glass serving bowl, dishwasher safe, elegant centrepiece for any table.",
        "category": "home-decor", "material": "recycled-glass",
        "origin_district": "", "price_rwf": 16000, "artisan_id": "", "is_local": False,
    },
    {
        "sku": "INTL-H003",
        "title": "Bamboo Zen coasters set 6 bamboo",
        "description": "Set of 6 natural bamboo coasters with cork backing, heat and moisture resistant.",
        "category": "home-decor", "material": "bamboo",
        "origin_district": "", "price_rwf": 7000, "artisan_id": "", "is_local": False,
    },
    {
        "sku": "INTL-H004",
        "title": "West Elm ceramic candle holder set",
        "description": "Set of three ceramic candle holders in graduated sizes, matte glazed finish.",
        "category": "home-decor", "material": "ceramic",
        "origin_district": "", "price_rwf": 22000, "artisan_id": "", "is_local": False,
    },
    {
        "sku": "INTL-H005",
        "title": "Umbra wood photo frame 5x7",
        "description": "Modern wood photo frame for 5x7 inch prints, tabletop or wall mount, natural finish.",
        "category": "home-decor", "material": "wood",
        "origin_district": "", "price_rwf": 11000, "artisan_id": "", "is_local": False,
    },
    {
        "sku": "INTL-H006",
        "title": "IKEA bamboo lamp shade pendant",
        "description": "Pendant lamp shade in natural bamboo weave, creates warm diffused light effect.",
        "category": "home-decor", "material": "bamboo",
        "origin_district": "", "price_rwf": 19000, "artisan_id": "", "is_local": False,
    },
]

# ─── Real Made-in-Rwanda brand products ──────────────────────────────
# Three verified Rwandan companies hardcoded for demo authenticity.
# Inzuki Designs: jewelry + weaving cooperative (Teta Isibo, Kigali)
# UZURI K&Y: eco-friendly footwear (Kevine Kagirimpundu & Yvette Shimwe, Kigali)
# Sina Gerard / Urwibutso: artisanal food gifts (Nyabihu) — framed as gift sets
REAL_BRAND_PRODUCTS = [
    # ── Inzuki Designs ───────────────────────────────────────────────
    {
        "sku": "INZUKI-J001",
        "title": "Inzuki Designs beaded necklace handmade Rwanda",
        "description": "Handmade statement beaded necklace by Inzuki Designs, crafted by a women's cooperative using traditional Rwandan weaving skills and vibrant natural-dyed beads.",
        "category": "jewellery", "material": "beads",
        "origin_district": "Gasabo", "price_rwf": 18000, "artisan_id": "INZUKI", "is_local": True,
    },
    {
        "sku": "INZUKI-J002",
        "title": "Inzuki Designs beaded earrings drop colourful",
        "description": "Lightweight drop earrings handcrafted by Inzuki Designs artisans, featuring colourful beads and inspired by traditional Rwandan patterns. Empowers local women's cooperatives.",
        "category": "jewellery", "material": "beads",
        "origin_district": "Gasabo", "price_rwf": 9500, "artisan_id": "INZUKI", "is_local": True,
    },
    {
        "sku": "INZUKI-J003",
        "title": "Inzuki Designs woven bracelet accessories Rwanda",
        "description": "Woven bracelet accessory from Inzuki Designs combining traditional Rwandan weaving technique with vibrant colour palettes. Each piece is unique and handmade.",
        "category": "jewellery", "material": "beads",
        "origin_district": "Gasabo", "price_rwf": 7000, "artisan_id": "INZUKI", "is_local": True,
    },
    {
        "sku": "INZUKI-B001",
        "title": "Inzuki Designs agaseke peace basket woven",
        "description": "Traditional Rwandan agaseke peace basket handwoven by Inzuki Designs cooperative artisans using sweetgrass and natural dyes. A symbol of unity, ideal as a gift.",
        "category": "basketry", "material": "sweetgrass",
        "origin_district": "Gasabo", "price_rwf": 25000, "artisan_id": "INZUKI", "is_local": True,
    },
    {
        "sku": "INZUKI-H001",
        "title": "Inzuki Designs woven wall hanging interior decor",
        "description": "Decorative woven wall hanging by Inzuki Designs, blending traditional Rwandan geometric patterns with contemporary interior décor. Handmade by women artisans.",
        "category": "home-decor", "material": "banana-bark",
        "origin_district": "Gasabo", "price_rwf": 32000, "artisan_id": "INZUKI", "is_local": True,
    },
    # ── UZURI K&Y ────────────────────────────────────────────────────
    {
        "sku": "UZURI-L001",
        "title": "UZURI K&Y eco leather sandals women Rwanda",
        "description": "Eco-friendly leather sandals handmade in Rwanda by UZURI K&Y, using sustainably sourced leather. Open-toe design with adjustable straps and cushioned footbed.",
        "category": "leather", "material": "vegetable-tanned-leather",
        "origin_district": "Nyarugenge", "price_rwf": 38000, "artisan_id": "UZURI", "is_local": True,
    },
    {
        "sku": "UZURI-L002",
        "title": "UZURI K&Y sustainable leather boots handmade Kigali",
        "description": "Sustainable leather boots crafted in Kigali by UZURI K&Y founders Kevine and Yvette. Vegetable-tanned leather, rubber sole, built to last. Rwanda-made footwear at its finest.",
        "category": "leather", "material": "vegetable-tanned-leather",
        "origin_district": "Nyarugenge", "price_rwf": 72000, "artisan_id": "UZURI", "is_local": True,
    },
    {
        "sku": "UZURI-L003",
        "title": "UZURI K&Y handmade leather shoes men Rwanda",
        "description": "Men's leather shoes handmade in Rwanda by UZURI K&Y. Eco-conscious production, genuine leather upper, leather lining, durable rubber outsole. Smart casual style.",
        "category": "leather", "material": "cow-leather",
        "origin_district": "Nyarugenge", "price_rwf": 58000, "artisan_id": "UZURI", "is_local": True,
    },
    # ── Inzuki Designs — apparel ─────────────────────────────────────
    {
        "sku": "INZUKI-A001",
        "title": "Inzuki Designs kitenge headwrap African print",
        "description": "Vibrant kitenge headwrap by Inzuki Designs, handcrafted in bold African prints. A staple of Rwandan fashion, made by women artisans empowered through the cooperative.",
        "category": "apparel", "material": "kitenge-fabric",
        "origin_district": "Gasabo", "price_rwf": 6500, "artisan_id": "INZUKI", "is_local": True,
    },
    # ── Sina Gerard / Urwibutso Enterprise ───────────────────────────
    {
        "sku": "SINAG-H001",
        "title": "Urwibutso artisanal chili sauce gift set Rwanda",
        "description": "Gift set of three award-winning Rwandan chili sauces by Sina Gerard / Urwibutso Enterprise, supporting local farmers. Bold, authentic flavours — a uniquely Rwandan gift.",
        "category": "home-decor", "material": "banana-bark",
        "origin_district": "Nyabihu", "price_rwf": 12000, "artisan_id": "SINAG", "is_local": True,
    },
    {
        "sku": "SINAG-H002",
        "title": "Urwibutso banana wine gift Rwanda traditional",
        "description": "Traditionally fermented Rwandan banana wine (urwagwa) bottled by Urwibutso Enterprise. Presented in a handwoven banana-bark gift box. A true taste of Rwandan culture.",
        "category": "home-decor", "material": "banana-bark",
        "origin_district": "Nyabihu", "price_rwf": 8500, "artisan_id": "SINAG", "is_local": True,
    },
    {
        "sku": "SINAG-H003",
        "title": "Urwibutso fruit juice assorted gift Rwanda",
        "description": "Assorted Rwandan fruit juice gift set by Urwibutso Enterprise, made from locally grown tropical fruits. Supports smallholder farmers across Rwanda. Presented in a woven tray.",
        "category": "home-decor", "material": "banana-bark",
        "origin_district": "Nyabihu", "price_rwf": 9500, "artisan_id": "SINAG", "is_local": True,
    },
]

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
    """Generate n local products + all INTERNATIONAL_PRODUCTS."""
    products = []
    sku_counter = 0

    # Distribute local products roughly evenly across categories
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
                "is_local": True,
            })

    random.shuffle(products)

    # Append real Rwandan brand products then international brands
    products.extend(REAL_BRAND_PRODUCTS)
    products.extend(INTERNATIONAL_PRODUCTS)

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


def _keyword_match_score(query_text, product):
    """Count keyword overlaps between query and product title+category+material."""
    q_words = set(query_text.lower().replace("'", " ").replace("à", "a")
                  .replace("é", "e").replace("è", "e").split())
    p_words = set((product["title"] + " " + product["category"] + " "
                   + product["material"]).lower().replace("-", " ").split())
    return len(q_words & p_words)


def generate_queries(products, n=120):
    """
    Generate n search queries with global_best_match baseline.

    global_best_match_sku simulates what a global e-commerce algorithm (e.g. Amazon)
    would return — preferring international brand products when they match the query
    keywords, falling back to a local product otherwise.
    """
    local_products = [p for p in products if p.get("is_local", True)]
    intl_products  = [p for p in products if not p.get("is_local", True)]

    queries = []
    all_q = []

    for lang, qs in QUERY_TEMPLATES.items():
        for q in qs:
            all_q.append((q, lang))

    selected = []
    while len(selected) < n:
        random.shuffle(all_q)
        selected.extend(all_q)
    selected = selected[:n]

    for i, (query_text, lang) in enumerate(selected):
        # Find the best-matching international product by keyword overlap
        best_intl = None
        best_intl_score = 0
        for p in intl_products:
            score = _keyword_match_score(query_text, p)
            if score > best_intl_score:
                best_intl_score = score
                best_intl = p

        # Use the international product as global_best_match when it has at least
        # 2 keyword overlaps (i.e. genuinely competes for that query).
        # Otherwise fall back to a random local product.
        if best_intl and best_intl_score >= 2:
            best_match = best_intl
        else:
            best_match = random.choice(local_products)

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
    # Click log only covers local products (platform tracks artisan engagement)
    local_skus = [p["sku"] for p in products if p.get("is_local", True)]

    for i in range(n):
        query = random.choice(queries)
        result_list = random.sample(local_skus, min(10, len(local_skus)))

        position = random.choices(
            range(1, 11),
            weights=[1.0 / math.log2(pos + 1) for pos in range(1, 11)],
            k=1
        )[0]
        clicked_sku = result_list[position - 1]

        base_dwell = random.gauss(30, 15)
        dwell_time = max(1, round(base_dwell))

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
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(data)
    print(f"  OK  {filepath} -- {len(data)} rows")


def main():
    print("Generating synthetic data for 'Made in Rwanda' Content Recommender...")
    print(f"  Seed: {SEED}\n")

    artisans = generate_artisans(80)
    print(f"  Generated {len(artisans)} artisans")

    catalog = generate_catalog(artisans, 400)
    local_count = sum(1 for p in catalog if p.get("is_local", True))
    intl_count  = sum(1 for p in catalog if not p.get("is_local", True))
    write_csv(
        os.path.join(OUTPUT_DIR, "catalog.csv"),
        catalog,
        ["sku", "title", "description", "category", "material",
         "origin_district", "price_rwf", "artisan_id", "is_local"],
    )
    print(f"    {local_count} local (Made in Rwanda) + {intl_count} international brand products")

    queries = generate_queries(catalog, 120)
    intl_baseline = sum(1 for q in queries if q["global_best_match_sku"].startswith("INTL"))
    write_csv(
        os.path.join(OUTPUT_DIR, "queries.csv"),
        queries,
        ["query_id", "query_text", "language", "global_best_match_sku"],
    )
    print(f"    {intl_baseline}/{len(queries)} queries have an international brand as global_best_match")

    click_log = generate_click_log(catalog, queries, 5000)
    write_csv(
        os.path.join(OUTPUT_DIR, "click_log.csv"),
        click_log,
        ["click_id", "query_id", "clicked_sku", "position", "dwell_time_s", "timestamp"],
    )

    print("\nAll data generated successfully!")
    print(f"   catalog.csv:   {len(catalog)} products ({local_count} local, {intl_count} international)")
    print(f"   queries.csv:   {len(queries)} queries (EN/FR/code-switched/misspelled)")
    print(f"   click_log.csv: {len(click_log)} click events (local SKUs only)")


if __name__ == "__main__":
    main()
