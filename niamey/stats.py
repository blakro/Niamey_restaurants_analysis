"""Étape 2 — Constats chiffrés et tests statistiques (calculés, jamais écrits à la main)."""
from __future__ import annotations

import pandas as pd
from scipy import stats

from . import config


def key_stats(g: pd.DataFrame, n_raw: int) -> dict:
    """Tous les chiffres cités dans le README et le rapport."""
    rated = g[g["is_rated"]]
    reliable = g[g["reviews_count"] >= config.RELIABLE_REVIEWS]
    five = rated[rated["score_raw"] == 5]

    rho, p_rho = stats.spearmanr(rated["reviews_count"], rated["score_raw"])

    groups = [x["score_raw"].values for _, x in reliable.groupby("concept") if len(x) >= 5]
    kw_h, kw_p = stats.kruskal(*groups)

    web, noweb = g[g["has_website"]], g[~g["has_website"]]
    _, p_web_reviews = stats.mannwhitneyu(web["reviews_count"], noweb["reviews_count"], alternative="two-sided")
    rw, rnw = reliable[reliable["has_website"]], reliable[~reliable["has_website"]]
    _, p_web_score = stats.mannwhitneyu(rw["score_raw"], rnw["score_raw"], alternative="two-sided")

    geo = g[g["is_geocoded"]]
    pole_sizes = geo[geo["pole_id"] >= 0]["pole"].value_counts()
    top2 = pole_sizes.head(2)

    return {
        "n_raw": n_raw,
        "n_restaurants": len(g),
        "n_rated": len(rated),
        "pct_rated": 100 * len(rated) / len(g),
        "n_no_review": int((g["reviews_count"] == 0).sum()),
        "pct_lt5_reviews": 100 * (g["reviews_count"] < 5).mean(),
        "median_reviews": float(g["reviews_count"].median()),
        "n_reliable": len(reliable),
        "pct_reliable": 100 * len(reliable) / len(g),
        "market_mean_score": float(rated["score_raw"].mean()),
        "n_five_star": len(five),
        "n_five_star_le5": int((five["reviews_count"] <= 5).sum()),
        "spearman_rho": float(rho),
        "spearman_p": float(p_rho),
        "kruskal_h": float(kw_h),
        "kruskal_p": float(kw_p),
        "kruskal_groups": len(groups),
        "n_website": len(web),
        "median_reviews_web": float(web["reviews_count"].median()),
        "median_reviews_noweb": float(noweb["reviews_count"].median()),
        "p_web_reviews": float(p_web_reviews),
        "median_score_web": float(rw["score_raw"].median()),
        "median_score_noweb": float(rnw["score_raw"].median()),
        "p_web_score": float(p_web_score),
        "n_geocoded": len(geo),
        "pct_geocoded": 100 * len(geo) / len(g),
        "n_poles": int(pole_sizes.size),
        "n_in_poles": int(pole_sizes.sum()),
        "top2_poles": list(top2.index),
        "pct_geo_in_top2_poles": 100 * top2.sum() / max(len(geo), 1),
        "n_generic": int((g["concept"] == "Restaurant généraliste").sum()),
        "pct_generic_google": 100 * (g["category"] == "Restaurant").mean(),
    }
