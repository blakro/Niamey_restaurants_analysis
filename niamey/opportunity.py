"""Étape 4 — Modèle d'opportunité : quel type de restaurant, et où ?

Pour chaque groupe (un concept comme « Pizzeria », ou une zone de la ville),
on répond à trois questions simples, notées de 0 (défavorable) à 1 (favorable) :

1. **Demande** — un établissement typique de ce groupe attire-t-il beaucoup de
   clients ? Mesure : nombre d'avis Google « typique » par établissement
   (moyenne géométrique, insensible aux 2-3 adresses très célèbres).
2. **Concurrence** — y a-t-il peu d'établissements de ce type ?
   (moins il y en a, plus la note est haute)
3. **Marge de progression** — les clients sont-ils seulement moyennement
   satisfaits de l'offre actuelle ? Une note moyenne de 3,5★ donne 1 (beaucoup
   de place pour mieux faire), une note de 4,5★ donne 0.

Score d'opportunité = moyenne pondérée des trois (poids dans `config.WEIGHTS`).

Les petits groupes étant fragiles, on vérifie la robustesse du classement par
simulation : on rejoue le calcul des milliers de fois en tirant au hasard un
échantillon de restaurants légèrement différent et des poids légèrement
différents, puis on compte combien de fois chaque groupe finit dans le top 3.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config

SATISFACTION_SCALE = (3.5, 4.5)  # note ≤ 3,5★ → marge 1 ; note ≥ 4,5★ → marge 0
CRITERIA = ["demande", "concurrence", "marge"]


def typical_reviews(reviews: pd.Series) -> float:
    """Nombre d'avis « typique » par établissement (moyenne géométrique de 1+avis, moins 1)."""
    r = np.asarray(reviews, dtype=float)
    if r.size == 0:
        return np.nan
    return float(np.expm1(np.log1p(r).mean()))


def group_metrics(df: pd.DataFrame, by: str) -> pd.DataFrame:
    """Indicateurs bruts par groupe."""
    g = df.groupby(by, observed=True)
    out = pd.DataFrame({
        "nb_etablissements": g.size(),
        "nb_notes": g["is_rated"].sum(),
        "nb_notes_fiables": g["reviews_count"].apply(lambda x: int((x >= config.RELIABLE_REVIEWS).sum())),
        "avis_total": g["reviews_count"].sum(),
        "avis_typique": g["reviews_count"].apply(typical_reviews),
        "note_moyenne": g["score_bayes"].mean(),
    })
    out["part_du_marche_pct"] = 100 * out["nb_etablissements"] / len(df)
    return out


def _minmax(s: pd.Series) -> pd.Series:
    rng = s.max() - s.min()
    if not np.isfinite(rng) or rng == 0:
        return pd.Series(0.5, index=s.index)
    return (s - s.min()) / rng


def criteria_scores(metrics: pd.DataFrame) -> pd.DataFrame:
    """Transforme les indicateurs bruts en trois notes de 0 à 1."""
    lo, hi = SATISFACTION_SCALE
    return pd.DataFrame({
        "demande": _minmax(np.log1p(metrics["avis_typique"])),
        "concurrence": _minmax(-np.log(metrics["nb_etablissements"])),
        "marge": ((hi - metrics["note_moyenne"]) / (hi - lo)).clip(0, 1).fillna(0.5),
    }, index=metrics.index)


def confidence_label(n_reliable: int) -> str:
    if n_reliable >= 8:
        return "Bonne"
    if n_reliable >= 4:
        return "Moyenne"
    return "Faible"


def score_groups(df: pd.DataFrame, by: str, min_size: int,
                 exclude: set[str] | None = None,
                 weights: dict[str, float] | None = None) -> pd.DataFrame:
    """Classement des groupes par score d'opportunité."""
    weights = weights or config.WEIGHTS
    metrics = group_metrics(df, by)
    eligible = metrics["nb_etablissements"] >= min_size
    if exclude:
        eligible &= ~metrics.index.isin(list(exclude))
    m = metrics[eligible].copy()
    crit = criteria_scores(m)
    m = m.join(crit)
    m["score_opportunite"] = sum(m[c] * w for c, w in weights.items())
    m["confiance"] = m["nb_notes_fiables"].map(confidence_label)
    m = m.sort_values("score_opportunite", ascending=False)
    m["rang"] = np.arange(1, len(m) + 1)
    return m


def robustness(df: pd.DataFrame, by: str, groups: list[str],
               n_sim: int = config.N_SIMULATIONS, seed: int = config.RANDOM_SEED,
               weight_concentration: float = 10.0, top_k: int = 3) -> pd.DataFrame:
    """Rejoue le classement `n_sim` fois avec (1) un rééchantillonnage des
    restaurants de chaque groupe et (2) des poids tirés autour des poids de
    référence. Renvoie, par groupe, la fréquence d'apparition dans le top k et
    la fourchette de rang (10e – 90e centile)."""
    rng = np.random.default_rng(seed)
    sub = df[df[by].isin(groups)]
    parts = {g: sub[sub[by] == g][["reviews_count", "score_bayes"]].to_numpy() for g in groups}
    base_w = np.array([config.WEIGHTS[c] for c in CRITERIA])
    lo, hi = SATISFACTION_SCALE
    ranks = np.zeros((n_sim, len(groups)), dtype=int)
    n = np.array([len(parts[g]) for g in groups], dtype=float)
    comp = _minmax(pd.Series(-np.log(n))).to_numpy()

    for s in range(n_sim):
        demand, sat = [], []
        for g in groups:
            arr = parts[g]
            sample = arr[rng.integers(0, len(arr), len(arr))]
            demand.append(np.log1p(sample[:, 0]).mean())
            notes = sample[:, 1][~np.isnan(sample[:, 1])]
            sat.append(notes.mean() if notes.size else np.nan)
        dem = _minmax(pd.Series(demand)).to_numpy()
        marge = np.nan_to_num(np.clip((hi - np.array(sat)) / (hi - lo), 0, 1), nan=0.5)
        w = rng.dirichlet(base_w * weight_concentration)
        score = w[0] * dem + w[1] * comp + w[2] * marge
        order = np.argsort(-score)
        ranks[s, order] = np.arange(1, len(groups) + 1)

    return pd.DataFrame({
        "pct_top3": 100 * (ranks <= top_k).mean(axis=0),
        "rang_median": np.median(ranks, axis=0),
        "rang_p10": np.percentile(ranks, 10, axis=0),
        "rang_p90": np.percentile(ranks, 90, axis=0),
    }, index=groups)


def concept_zone_leads(df: pd.DataFrame, concepts: pd.DataFrame, zones: pd.DataFrame,
                       top_concepts: int = 4, max_competitors: int = 1,
                       n_leads: int = 10) -> pd.DataFrame:
    """Pistes concrètes : un concept prometteur dans un pôle prometteur où ce
    concept est absent ou quasi absent (≤ `max_competitors`)."""
    best = concepts.head(top_concepts).index.tolist()
    counts = (df[df["pole"].isin(zones.index)]
              .groupby(["pole", "concept"]).size().unstack(fill_value=0))
    rows = []
    for c in best:
        for z in zones.index:
            n_same = int(counts.loc[z, c]) if (z in counts.index and c in counts.columns) else 0
            if n_same > max_competitors:
                continue
            rows.append({
                "concept": c,
                "pole": z,
                "concurrents_meme_concept": n_same,
                "restaurants_dans_le_pole": int(zones.loc[z, "nb_etablissements"]),
                "avis_total_du_pole": int(zones.loc[z, "avis_total"]),
                "score_concept": concepts.loc[c, "score_opportunite"],
                "score_pole": zones.loc[z, "score_opportunite"],
            })
    leads = pd.DataFrame(rows)
    if leads.empty:
        return leads
    # Le trafic du pôle compte : un concept absent d'un pôle très fréquenté est
    # plus intéressant qu'absent d'un pôle désert.
    traffic = _minmax(np.log1p(leads["avis_total_du_pole"]))
    leads["score_piste"] = (0.4 * leads["score_concept"] + 0.3 * leads["score_pole"] + 0.3 * traffic).round(3)
    return leads.sort_values("score_piste", ascending=False).head(n_leads).reset_index(drop=True)
