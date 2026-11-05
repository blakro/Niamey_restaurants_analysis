"""Étape 1 — Nettoyage et enrichissement des fiches Google Maps."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from . import config
from .concepts import NON_FOOD, add_concepts, normalize_text

RENAME_MAP = {
    "title": "name",
    "totalScore": "score_raw",
    "reviewsCount": "reviews_count",
    "street": "street",
    "city": "city",
    "countryCode": "country_code",
    "website": "website",
    "phone": "phone",
    "categoryName": "category",
    "url": "maps_url",
}

PLUS_CODE_RE = re.compile(r"[23456789CFGHJMPQRVWX]{4,8}\+[23456789CFGHJMPQRVWX]{2,3}", re.IGNORECASE)

KEPT_LABEL = "Restaurants retenus pour l'analyse"

# Noms trop génériques pour signaler une enseigne (« Fast food », « Restaurant »...).
GENERIC_NAME_WORDS = {"restaurant", "restaurent", "resto", "fast", "food", "fastfood", "snack", "cafe", "bar"}

TIER_BINS = [
    (0, 0, "0 · Aucun avis"),
    (1, 4, "1 · 1 à 4 avis"),
    (5, 19, "2 · 5 à 19 avis"),
    (20, 49, "3 · 20 à 49 avis"),
    (50, 199, "4 · 50 à 199 avis"),
    (200, np.inf, "5 · 200 avis et +"),
]


@dataclass
class CleaningLog:
    """Journal des opérations : chaque étape et le nombre de lignes concernées."""
    steps: list[tuple[str, int]] = field(default_factory=list)

    def add(self, label: str, n: int) -> None:
        self.steps.append((label, int(n)))

    def to_frame(self) -> pd.DataFrame:
        return pd.DataFrame(self.steps, columns=["étape", "nombre"])


def load_raw(path=config.RAW_CSV) -> pd.DataFrame:
    """Charge le CSV brut exporté de Google Maps (gère le BOM UTF-8)."""
    for enc in ("utf-8-sig", "latin-1"):
        try:
            return pd.read_csv(path, encoding=enc)
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Impossible de lire {path}")


def bayesian_score(score: pd.Series, n_reviews: pd.Series, m: float, prior: float) -> pd.Series:
    """Note corrigée = (prior × m + n × note) / (prior + n).

    `m` est la note moyenne du marché, `prior` le nombre d'avis « fictifs »
    ajoutés. Renvoie NaN pour les restaurants sans note ni avis.
    """
    valid = score.notna() & (n_reviews > 0)
    out = (prior * m + n_reviews * score) / (prior + n_reviews)
    return out.where(valid)


def reliability_tier(n: int) -> str:
    for lo, hi, label in TIER_BINS:
        if lo <= n <= hi:
            return label
    return TIER_BINS[-1][2]


def clean(df_raw: pd.DataFrame) -> tuple[pd.DataFrame, CleaningLog]:
    """Pipeline de nettoyage complet. Renvoie (dataset propre, journal)."""
    log = CleaningLog()
    df = df_raw.copy()
    log.add("Fiches dans l'export Google Maps", len(df))

    # 1. Ligne décalée : l'URL a glissé dans la colonne parasite « Column ».
    if "Column" in df.columns:
        shifted = df["url"].isna() & df["Column"].notna()
        df.loc[shifted, "url"] = df.loc[shifted, "Column"]
        log.add("Lignes décalées réparées (URL dans la mauvaise colonne)", shifted.sum())
        df = df.drop(columns=["Column"])
    df = df.drop(columns=[c for c in ["state"] if c in df.columns])
    df = df.rename(columns=RENAME_MAP)

    # 2. Champs texte.
    df["name"] = df["name"].astype("string").str.strip()
    df = df[df["name"].notna() & (df["name"] != "")]
    city = df["city"].astype("string").str.strip()
    df["city"] = city.where(~city.str.contains(r"\d", na=False))

    # 3. Notes et nombre d'avis.
    df["score_raw"] = pd.to_numeric(df["score_raw"], errors="coerce")
    df.loc[~df["score_raw"].between(1, 5), "score_raw"] = np.nan
    df["reviews_count"] = pd.to_numeric(df["reviews_count"], errors="coerce").fillna(0).astype(int)

    # 4. Doublons exacts (même fiche Google).
    df = df.sort_values("reviews_count", ascending=False)
    before = len(df)
    df = df[~(df["maps_url"].notna() & df.duplicated("maps_url"))]
    log.add("Doublons exacts supprimés (même lien Google Maps)", before - len(df))

    # 5. Doublons « probables » : même nom (normalisé) ET même adresse.
    #    Même nom mais adresse différente = succursales d'une même enseigne.
    df["name_norm"] = df["name"].map(normalize_text)
    df["street_norm"] = df["street"].map(normalize_text)
    before = len(df)
    df = df[~df.duplicated(["name_norm", "street_norm"])]
    log.add("Doublons probables supprimés (même nom et même adresse)", before - len(df))
    generic_name = df["name_norm"].map(lambda n: set(n.split()) <= GENERIC_NAME_WORDS)
    df["is_chain"] = df.duplicated("name_norm", keep=False) & ~generic_name

    # 6. Type de restaurant (concept) et exclusion des commerces non-restaurants.
    df = add_concepts(df, config.NON_FOOD_CATEGORIES)
    non_food = df["concept"] == NON_FOOD
    log.add("Commerces hors restauration exclus (épicerie, parc, volailler...)", non_food.sum())
    df = df[~non_food]

    # 7. Indicateurs de présence en ligne / complétude de la fiche.
    df["has_phone"] = df["phone"].notna() & (df["phone"].astype("string").str.strip() != "")
    df["has_address"] = df["street"].notna() & (df["street"].astype("string").str.strip() != "")
    df["is_plus_code"] = df["street"].astype("string").str.contains(PLUS_CODE_RE, na=False)
    df["has_website"] = df["website"].astype("string").str.match(r"https?://\S+", na=False)
    df["is_rated"] = df["score_raw"].notna() & (df["reviews_count"] > 0)
    df["completeness_score"] = (
        df["has_phone"].astype(int) + df["has_address"].astype(int)
        + df["has_website"].astype(int) + df["is_rated"].astype(int)
    )

    # 8. Note corrigée (moyenne bayésienne).
    m = df.loc[df["is_rated"], "score_raw"].mean()
    df["score_bayes"] = bayesian_score(df["score_raw"], df["reviews_count"], m, config.PRIOR_REVIEWS).round(3)
    df["reliability_tier"] = df["reviews_count"].map(reliability_tier)
    df.attrs["market_mean_score"] = float(m)

    log.add(KEPT_LABEL, len(df))

    cols = [
        "name", "concept", "concept_source", "category", "is_chain",
        "street", "city", "country_code", "has_address", "is_plus_code",
        "phone", "has_phone", "website", "has_website",
        "score_raw", "reviews_count", "is_rated", "score_bayes",
        "reliability_tier", "completeness_score", "maps_url",
    ]
    out = df[cols].reset_index(drop=True)
    out.attrs["market_mean_score"] = float(m)
    return out, log
