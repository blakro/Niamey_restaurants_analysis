"""Classement de chaque établissement dans un « concept » de restauration.

Problème : sur Google Maps, 2 établissements sur 3 sont simplement étiquetés
« Restaurant », et les autres étiquettes sont parfois fausses (« Burger time »
classé « cuisine d'Odisha », « Palais de chawarma » classé « diététique »...).

Solution : on lit d'abord le NOM de l'établissement (mots-clés : pizza, grill,
maquis, tacos, pâtisserie...), puis, à défaut, la catégorie Google. Ce qui
reste sans indice clair est rangé dans « Restaurant généraliste ».
"""
from __future__ import annotations

import re
import unicodedata

import pandas as pd

GENERIC = "Restaurant généraliste"
NON_FOOD = "Hors restauration"

# Ordre = priorité : la première règle qui correspond l'emporte.
NAME_RULES: list[tuple[str, str]] = [
    ("Hôtel-restaurant", r"\bhotel|\bauberge\b|\bresidence\b|\bcampement\b"),
    ("Cantine & traiteur", r"traiteur|catering|cantine|\bmess\b|\buam\b|universit|\bfac\b|fsjp|\bfoyer\b|\bservices?\b"),
    ("Pizzeria", r"pizz"),
    ("Boulangerie & pâtisserie", r"boulanger|patisser|gourmandise|mignardise"),
    ("Tacos, chawarma & sandwichs", r"taco|takos|chawarma|shawarma|kebab|donair|sandwich|\bwrap"),
    ("Burger & fast-food", r"burger|fast ?food|chicken|frite|fryz|chips|\bsnack"),
    ("Grillades & méchoui", r"grill|bbq|barbecue|brochette|mechoui|dibi|choukouya|braise|roast|\bfour\b|tsire|suya|battara|charcoal|merguez|\bporc\b|poulet|boudin"),
    ("Cuisine internationale", r"liban|\bturc|turk|hunkar|sofrasi|maroc|marrakech|carthage|yemen|egypt|indien|indian|tandoor|mumbai|chinois|dragon|asia|\bnems?\b|\bthai|japon|sushi|bakso|italien|casa d luca|toulousain|mexic|byblos|aladdin"),
    ("Cuisine africaine & locale", r"maquis|\bafri|attieke|senegal|senagal|ivoir|togo|nigerien|nigeria\b|mafe|igname|foufou|foofoo|garba|doukounou|degue|tchiombiano|damouree|djolof|teranga"),
    ("Café, glacier & salon de thé", r"\bcafe|coffee|cafeteria|cafetaria|glace|glaci|juice|\bjus\b|chocolat|\btea\b"),
    ("Bar & lounge", r"lounge|\bbar\b|buvette|\bpub\b|\bchill\b"),
]

# Repli : catégorie Google → concept.
GOOGLE_MAP: dict[str, str] = {
    "Restauration rapide": "Burger & fast-food",
    "Snack": "Burger & fast-food",
    "Restaurant de hamburgers": "Burger & fast-food",
    "Tiffin center": "Burger & fast-food",
    "Restaurant de plats à emporter": "Burger & fast-food",
    "Saladerie": "Burger & fast-food",
    "Kebab": "Tacos, chawarma & sandwichs",
    "Sandwicherie": "Tacos, chawarma & sandwichs",
    "Restaurant de tacos": "Tacos, chawarma & sandwichs",
    "Restaurant mexicain": "Tacos, chawarma & sandwichs",
    "Pizzeria": "Pizzeria",
    "Pizzas à emporter": "Pizzeria",
    "Restaurant de grillades": "Grillades & méchoui",
    "Restaurant servant des abats au barbecue": "Grillades & méchoui",
    "Restaurant de viande grillée (yakiniku)": "Grillades & méchoui",
    "Restaurant servant des grillades de mouton": "Grillades & méchoui",
    "Restaurant de volaille": "Grillades & méchoui",
    "Café et restaurant de grillades": "Grillades & méchoui",
    "Restaurant africain": "Cuisine africaine & locale",
    "Restaurant de spécialités d'Afrique de l'Ouest": "Cuisine africaine & locale",
    "Restaurant indien": "Cuisine internationale",
    "Restaurant italien": "Cuisine internationale",
    "Restaurant turc": "Cuisine internationale",
    "Restaurant libanais": "Cuisine internationale",
    "Restaurant marocain": "Cuisine internationale",
    "Restaurant indonésien": "Cuisine internationale",
    "Restaurant thaï": "Cuisine internationale",
    "Restaurant japonais": "Cuisine internationale",
    "Restaurant asiatique": "Cuisine internationale",
    "Restaurant égyptien": "Cuisine internationale",
    "Restaurant yéménite": "Cuisine internationale",
    "Restaurant français": "Cuisine internationale",
    "Cuisine française moderne": "Cuisine internationale",
    "Restaurant de spécialités de la région de Rome": "Cuisine internationale",
    "Restaurant gastronomique": "Cuisine internationale",
    "Restaurant de cuisine d'Odisha": "Cuisine internationale",
    "Café": "Café, glacier & salon de thé",
    "Cafétéria": "Café, glacier & salon de thé",
    "Café des arts": "Café, glacier & salon de thé",
    "Restaurant servant le petit-déjeuner": "Café, glacier & salon de thé",
    "Boulangerie": "Boulangerie & pâtisserie",
    "Bar": "Bar & lounge",
    "Bar-restaurant à huîtres": "Bar & lounge",
    "Hôtel": "Hôtel-restaurant",
}

_COMPILED = [(concept, re.compile(pattern)) for concept, pattern in NAME_RULES]


def normalize_text(text: object) -> str:
    """Minuscules, sans accents ni ponctuation : « Côté Jardin ! » → « cote jardin »."""
    if text is None or (isinstance(text, float) and pd.isna(text)):
        return ""
    s = unicodedata.normalize("NFKD", str(text))
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.lower().replace("’", "'")
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def infer_concept(name: object, google_category: object, non_food_categories: set[str]) -> tuple[str, str]:
    """Renvoie (concept, source) où source ∈ {« nom », « catégorie Google », « aucun indice »}."""
    norm = normalize_text(name)
    cat = "" if google_category is None or pd.isna(google_category) else str(google_category)

    if cat in non_food_categories and "restau" not in norm:
        return NON_FOOD, "catégorie Google"

    for concept, pattern in _COMPILED:
        if pattern.search(norm):
            return concept, "nom"

    if cat in GOOGLE_MAP:
        return GOOGLE_MAP[cat], "catégorie Google"
    return GENERIC, "aucun indice"


def add_concepts(df: pd.DataFrame, non_food_categories: set[str]) -> pd.DataFrame:
    """Ajoute les colonnes `concept` et `concept_source`."""
    out = df.copy()
    res = [infer_concept(n, c, non_food_categories) for n, c in zip(out["name"], out["category"])]
    out["concept"] = [r[0] for r in res]
    out["concept_source"] = [r[1] for r in res]
    return out
