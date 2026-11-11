"""Graphiques (PNG) — style sobre, lisible par un public non spécialiste.

Règles suivies : une couleur par série (le bleu pour ce qui compte, le gris
pour le contexte), grilles fines et discrètes, étiquettes directes seulement
sur les éléments importants, jamais de double axe.
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import FixedLocator, FuncFormatter, NullLocator

from . import config

# Palette de référence (validée daltonisme).
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
BLUE = "#2a78d6"        # série principale / mise en avant
BLUE_DARK = "#184f95"
ORANGE = "#eb6834"      # 2e série quand il en faut une
GRAY = "#c3c2b7"        # contexte

# adjustText s'arrête par défaut après 1 seconde de calcul : le placement des
# étiquettes dépendait alors de la vitesse de la machine. Un nombre fixe
# d'itérations rend les images identiques d'une exécution à l'autre.
ADJUST_ITER = 1000

plt.rcParams.update({
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
    "savefig.facecolor": SURFACE,
    "axes.edgecolor": AXIS,
    "axes.labelcolor": INK_2,
    "axes.titlecolor": INK,
    "axes.titleweight": "bold",
    "axes.titlesize": 13,
    "axes.titlelocation": "left",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.color": GRID,
    "grid.linestyle": "-",
    "grid.linewidth": 0.8,
    "axes.axisbelow": True,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "xtick.labelcolor": INK_2,
    "ytick.labelcolor": INK_2,
    "font.size": 11,
    "legend.frameon": False,
})


def _fr(v: float, fmt: str = "{:g}") -> str:
    return fmt.format(v).replace(".", ",")


def _fr_axis(ax, which: str = "x") -> None:
    """Graduations au format français (virgule décimale, nombres simples)."""
    f = FuncFormatter(lambda v, _: _fr(v))
    (ax.xaxis if which == "x" else ax.yaxis).set_major_formatter(f)


def save(fig, name: str, publish: bool = False) -> Path:
    """Enregistre dans data/processed/figures (et docs/figures si `publish`)."""
    config.FIG_DIR.mkdir(parents=True, exist_ok=True)
    path = config.FIG_DIR / f"{name}.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    if publish:
        config.DOCS_FIG_DIR.mkdir(parents=True, exist_ok=True)
        fig.savefig(config.DOCS_FIG_DIR / f"{name}.png", dpi=150, bbox_inches="tight")
    return path


def _subtitle(ax, text: str) -> None:
    ax.text(0, 1.02, text, transform=ax.transAxes, fontsize=10, color=INK_2, va="bottom")


def _hbars(ax, labels, values, colors, fmt="{:.0f}", xmax=None):
    y = np.arange(len(labels))
    ax.barh(y, values, color=colors, height=0.62, edgecolor=SURFACE, linewidth=2)
    ax.set_yticks(y, labels)
    ax.invert_yaxis()
    ax.grid(axis="y", visible=False)
    span = xmax or (max(values) if len(values) else 1)
    for yi, v in zip(y, values):
        ax.text(v + span * 0.015, yi, _fr(v, fmt), va="center", fontsize=9.5, color=INK_2)
    ax.set_xlim(0, span * 1.15)
    _fr_axis(ax, "x")


# ── 1. Le parcours des données ───────────────────────────────────────────────
def fig_funnel(steps: pd.DataFrame, publish: bool = False):
    """`steps` : colonnes « étape » et « nombre », dans l'ordre."""
    fig, ax = plt.subplots(figsize=(9, 0.55 * len(steps) + 1.4))
    _hbars(ax, steps["étape"], steps["nombre"], [BLUE] * len(steps))
    ax.set_title("De l'export Google Maps aux données vraiment exploitables", pad=24)
    _subtitle(ax, "Nombre d'établissements restant à chaque étape")
    ax.set_xlabel("Nombre d'établissements")
    return fig, save(fig, "01_parcours_des_donnees", publish)


# ── 2. Pourquoi corriger les notes ───────────────────────────────────────────
def fig_bayes(df: pd.DataFrame, publish: bool = False):
    d = df[df["is_rated"]]
    fig, ax = plt.subplots(figsize=(10, 5.2))
    x = d["reviews_count"]
    ax.scatter(x, d["score_raw"], s=22, color=GRAY, alpha=0.9, label="Note Google brute", zorder=2)
    ax.scatter(x, d["score_bayes"], s=22, color=BLUE, alpha=0.85, label="Note corrigée", zorder=3,
               edgecolor=SURFACE, linewidth=0.6)
    ax.axhline(df.attrs.get("market_mean_score", d["score_raw"].mean()), color=INK_2, lw=1)
    ax.set_xscale("log")
    ax.xaxis.set_major_locator(FixedLocator([1, 2, 5, 10, 20, 50, 100, 200, 500, 1000]))
    ax.xaxis.set_minor_locator(NullLocator())
    _fr_axis(ax, "x")
    _fr_axis(ax, "y")
    ax.set_xlabel("Nombre d'avis du restaurant")
    ax.set_ylabel("Note sur 5")
    ax.set_ylim(0.8, 5.2)
    ax.set_title("Une note de 5★ sur 1 avis ne vaut pas une note de 4,8★ sur 400 avis", pad=24)
    _subtitle(ax, f"La correction ramène les notes basées sur peu d'avis vers la moyenne du marché "
                  f"(trait noir, {d['score_raw'].mean():.2f}★)".replace(".", ","))
    ax.legend(loc="lower right")
    return fig, save(fig, "02_notes_corrigees", publish)


# ── 3. Peu d'avis pour la plupart des restaurants ────────────────────────────
def fig_reviews_tiers(df: pd.DataFrame, publish: bool = False):
    counts = df["reliability_tier"].value_counts().sort_index()
    labels = [c.split("· ")[1] for c in counts.index]
    colors = [GRAY if i < 2 else BLUE for i in range(len(counts))]
    fig, ax = plt.subplots(figsize=(9, 4.4))
    ax.bar(labels, counts.values, color=colors, width=0.62, edgecolor=SURFACE, linewidth=2)
    ax.grid(axis="x", visible=False)
    for i, v in enumerate(counts.values):
        ax.text(i, v + counts.max() * 0.02, f"{v}\n({100 * v / len(df):.0f} %)", ha="center",
                va="bottom", fontsize=9.5, color=INK_2)
    ax.set_ylim(0, counts.max() * 1.25)
    ax.set_ylabel("Nombre de restaurants")
    ax.set_title("La plupart des restaurants n'ont presque aucun avis", pad=24)
    _subtitle(ax, "En gris : moins de 5 avis, trop peu pour juger de la qualité")
    return fig, save(fig, "03_volume_avis", publish)


# ── 4. Panorama des concepts ─────────────────────────────────────────────────
def fig_concepts(metrics: pd.DataFrame, publish: bool = False):
    m = metrics.sort_values("nb_etablissements", ascending=False)
    colors = [GRAY if c in config.NOT_RANKED_CONCEPTS else BLUE for c in m.index]
    fig, axes = plt.subplots(1, 2, figsize=(13, 0.48 * len(m) + 1.8), sharey=True)
    _hbars(axes[0], m.index, m["nb_etablissements"], colors)
    axes[0].set_title("Combien d'établissements ?", pad=8)
    axes[0].set_xlabel("Nombre d'établissements (= concurrence)")
    _hbars(axes[1], m.index, m["avis_typique"], colors, fmt="{:.1f}")
    axes[1].set_title("Combien de clients chacun attire-t-il ?", pad=8)
    axes[1].set_xlabel("Avis typiques par établissement (= demande)")
    fig.suptitle("Les types de restaurants à Niamey : concurrence et demande", x=0.01, ha="left",
                 fontweight="bold", fontsize=14, y=1.02)
    fig.text(0.01, 0.97, "En gris : catégories servant de référence, non classées",
             color=INK_2, fontsize=10, ha="left")
    fig.tight_layout()
    return fig, save(fig, "04_panorama_concepts", publish)


# ── 5. Matrice d'opportunité ─────────────────────────────────────────────────
def fig_matrix(scores: pd.DataFrame, robust: pd.DataFrame, publish: bool = False):
    s = scores.join(robust)
    fig, ax = plt.subplots(figsize=(11, 6.8))
    x, y = s["nb_etablissements"], s["avis_typique"]
    xm, ym = np.exp(np.log(x).mean()), np.exp(np.log(y).mean())
    ax.axvline(xm, color=AXIS, lw=1)
    ax.axhline(ym, color=AXIS, lw=1)
    highlight = s["pct_top3"] >= 50
    size = 60 + 900 * s["avis_total"] / s["avis_total"].max()
    ax.scatter(x[~highlight], y[~highlight], s=size[~highlight], color=GRAY, alpha=0.9,
               edgecolor=SURFACE, linewidth=2, zorder=3)
    ax.scatter(x[highlight], y[highlight], s=size[highlight], color=BLUE, alpha=0.9,
               edgecolor=SURFACE, linewidth=2, zorder=4)
    ax.set_xscale("log")
    ax.set_yscale("log")
    for axis, ticks in ((ax.xaxis, [5, 10, 15, 20, 30, 40, 60, 100, 200]), (ax.yaxis, [1, 2, 3, 5, 10, 15, 20, 30])):
        axis.set_major_locator(FixedLocator(ticks))
        axis.set_minor_locator(NullLocator())
        axis.set_major_formatter(FuncFormatter(lambda v, _: _fr(v)))
    ax.set_xlim(x.min() / 1.25, x.max() * 1.3)
    ax.set_ylim(y.min() / 1.3, y.max() * 1.25)
    ax.set_xlabel("Concurrence : nombre d'établissements de ce type  →  plus de concurrents")
    ax.set_ylabel("Demande : avis typiques par établissement  →  plus de clients")
    # Étiquette collée à son rond : à droite, ou à gauche pour les ronds proches
    # du bord droit (sinon le nom sortirait du cadre ou recouvrirait un voisin).
    x_split = np.exp(np.log(x.min()) + 0.72 * (np.log(x.max()) - np.log(x.min())))
    for name, row in s.iterrows():
        gap = np.sqrt(size[name]) / 2 + 4          # rayon du rond, en points
        left = row["nb_etablissements"] > x_split
        ax.annotate(name, (row["nb_etablissements"], row["avis_typique"]),
                    xytext=(-gap if left else gap, 0), textcoords="offset points",
                    ha="right" if left else "left", va="center", fontsize=9.5,
                    color=INK if highlight[name] else INK_2,
                    fontweight="bold" if highlight[name] else "normal", zorder=5)
    ax.text(0.01, 0.99, "↖ OPPORTUNITÉ : peu de concurrents, beaucoup de clients",
            transform=ax.transAxes, fontsize=9, color=BLUE_DARK, va="top", fontweight="bold")
    ax.text(0.99, 0.01, "SATURÉ : beaucoup de concurrents, peu de clients chacun ↘",
            transform=ax.transAxes, fontsize=9, color=INK_2, va="bottom", ha="right", fontweight="bold")
    ax.set_title("Où est la place pour un nouveau restaurant ?", pad=24)
    _subtitle(ax, "En bleu : types de restaurant dans le top 3 dans plus de la moitié des simulations · "
                  "taille du rond = nombre total d'avis")
    return fig, save(fig, "05_matrice_opportunite", publish)


# ── 6. Robustesse ────────────────────────────────────────────────────────────
def fig_robustness(robust: pd.DataFrame, title: str, name: str, publish: bool = False):
    r = robust.sort_values("pct_top3", ascending=False)
    colors = [BLUE if v >= 50 else GRAY for v in r["pct_top3"]]
    fig, ax = plt.subplots(figsize=(10, 0.5 * len(r) + 1.6))
    _hbars(ax, r.index, r["pct_top3"], colors, fmt="{:.0f} %", xmax=100)
    ax.set_xlabel("Part des simulations où le type de restaurant finit dans le top 3")
    ax.set_title(title, pad=24)
    _subtitle(ax, f"{config.N_SIMULATIONS:,} simulations avec des données et des critères légèrement modifiés · "
                  "en bleu : résultat solide (plus de 50 %)".replace(",", " "))
    return fig, save(fig, name, publish)


# ── 7. Zones ─────────────────────────────────────────────────────────────────
def fig_zones(scores: pd.DataFrame, title: str, name: str, publish: bool = False):
    s = scores.sort_values("avis_typique", ascending=False)
    labels = [f"{z}  ({int(n)} restaurants)" for z, n in zip(s.index, s["nb_etablissements"])]
    top = s["avis_typique"].nlargest(min(2, len(s))).index
    colors = [BLUE if z in top else GRAY for z in s.index]
    fig, ax = plt.subplots(figsize=(10, 0.5 * len(s) + 1.6))
    _hbars(ax, labels, s["avis_typique"], colors, fmt="{:.1f}")
    ax.set_xlabel("Avis typiques par établissement (= clients attirés par chaque restaurant)")
    ax.set_title(title, pad=24)
    _subtitle(ax, "En bleu : les 2 zones où chaque restaurant attire le plus de clients")
    return fig, save(fig, name, publish)


# ── 8. Carte statique ────────────────────────────────────────────────────────
def fig_static_map(g: pd.DataFrame, publish: bool = False):
    geo = g[g["is_geocoded"]]
    in_pole = geo["pole_id"] >= 0
    fig, ax = plt.subplots(figsize=(9, 8))
    ax.scatter(geo.loc[~in_pole, "lng"], geo.loc[~in_pole, "lat"], s=14, color=GRAY, label="Restaurant isolé")
    ax.scatter(geo.loc[in_pole, "lng"], geo.loc[in_pole, "lat"], s=18, color=BLUE, alpha=0.85,
               edgecolor=SURFACE, linewidth=0.5, label="Restaurant dans un pôle")
    centers = geo[in_pole].groupby("pole").agg(lat=("lat", "mean"), lng=("lng", "mean"), n=("name", "size"))
    texts = [ax.text(r.lng, r.lat, f"{p} ({int(r.n)})", fontsize=8.5, color=INK, fontweight="bold")
             for p, r in centers.iterrows()]
    try:
        from adjustText import adjust_text
        adjust_text(texts, ax=ax, iter_lim=ADJUST_ITER, arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.6))
    except ImportError:
        pass
    ax.set_aspect(1 / np.cos(np.radians(config.NIAMEY_LAT)))
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    _fr_axis(ax, "x")
    _fr_axis(ax, "y")
    ax.set_title("Les pôles de restauration de Niamey", pad=24)
    _subtitle(ax, f"{len(geo)} restaurants localisés · un pôle = au moins {config.DBSCAN_MIN_SAMPLES} "
                  f"restaurants à moins de {config.DBSCAN_EPS_M} m les uns des autres")
    ax.legend(loc="lower right")
    return fig, save(fig, "08_carte_poles", publish)


# ── EDA : site web et notes par concept ──────────────────────────────────────
def fig_website(df: pd.DataFrame, p_reviews: float, p_score: float, publish: bool = False):
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6))
    groups = [("Avec site web", df[df["has_website"]]), ("Sans site web", df[~df["has_website"]])]
    med = [g["reviews_count"].median() for _, g in groups]
    axes[0].bar([g[0] for g in groups], med, color=[BLUE, GRAY], width=0.5)
    for i, v in enumerate(med):
        axes[0].text(i, v + max(med) * 0.02, _fr(v), ha="center", va="bottom", color=INK_2)
    axes[0].grid(axis="x", visible=False)
    axes[0].set_ylabel("Nombre d'avis (médiane)")
    axes[0].set_title("Visibilité : nombre d'avis", pad=8)
    axes[0].set_xlabel(_pval_text(p_reviews))
    rel = df[df["reviews_count"] >= config.RELIABLE_REVIEWS]
    data = [rel[rel["has_website"]]["score_raw"], rel[~rel["has_website"]]["score_raw"]]
    bp = axes[1].boxplot(data, patch_artist=True, widths=0.45, medianprops=dict(color=INK))
    for patch, c in zip(bp["boxes"], [BLUE, GRAY]):
        patch.set_facecolor(c)
        patch.set_edgecolor(c)
    axes[1].set_xticks([1, 2], [f"Avec site web\n(n={len(data[0])})", f"Sans site web\n(n={len(data[1])})"])
    axes[1].set_ylabel("Note Google")
    axes[1].set_title(f"Qualité : note (restaurants ≥ {config.RELIABLE_REVIEWS} avis)", pad=8)
    axes[1].set_xlabel(_pval_text(p_score))
    _fr_axis(axes[1], "y")
    fig.suptitle("Avoir un site web : plus de visibilité, pas forcément une meilleure note",
                 x=0.01, ha="left", fontweight="bold", fontsize=13, y=1.03)
    fig.tight_layout()
    return fig, save(fig, "06_site_web", publish)


def fig_scores_by_concept(df: pd.DataFrame, p_value: float, publish: bool = False):
    rel = df[df["reviews_count"] >= config.RELIABLE_REVIEWS]
    order = rel.groupby("concept")["score_raw"].median().sort_values(ascending=False)
    order = [c for c in order.index if (rel["concept"] == c).sum() >= 5]
    fig, ax = plt.subplots(figsize=(11, 5))
    data = [rel[rel["concept"] == c]["score_raw"] for c in order]
    bp = ax.boxplot(data, patch_artist=True, widths=0.5, medianprops=dict(color=INK), vert=True)
    for patch in bp["boxes"]:
        patch.set_facecolor(BLUE)
        patch.set_edgecolor(BLUE)
        patch.set_alpha(0.75)
    ax.set_xticks(range(1, len(order) + 1), [f"{c}\n(n={len(d)})" for c, d in zip(order, data)],
                  rotation=30, ha="right", fontsize=9)
    ax.set_ylabel("Note Google")
    _fr_axis(ax, "y")
    ax.set_title("Les notes se ressemblent d'un type de cuisine à l'autre", pad=24)
    _subtitle(ax, f"Restaurants avec au moins {config.RELIABLE_REVIEWS} avis · "
                  f"test de Kruskal-Wallis : {_pval_text(p_value)}")
    return fig, save(fig, "07_notes_par_concept", publish)


def _pval_text(p: float) -> str:
    verdict = "différence significative" if p < 0.05 else "pas de différence significative"
    ptxt = "p < 0,001" if p < 0.001 else f"p = {p:.2f}".replace(".", ",")
    return f"{ptxt} → {verdict}"


# ── 9. Tableau de bord de synthèse ───────────────────────────────────────────
def fig_dashboard(kpis: list[tuple[str, str]], concepts: pd.DataFrame, robust: pd.DataFrame,
                  zones: pd.DataFrame, publish: bool = True):
    fig = plt.figure(figsize=(15, 8.2))
    gs = fig.add_gridspec(2, 4, height_ratios=[0.5, 2.3], hspace=0.32, wspace=0.6,
                          top=0.86, bottom=0.07, left=0.16, right=0.97)
    fig.text(0.16, 0.955, "Ouvrir un restaurant à Niamey : ce que disent les données",
             fontsize=19, fontweight="bold", color=INK)
    fig.text(0.16, 0.915, "D'après les fiches Google Maps · score d'opportunité = beaucoup de clients "
             "et peu de concurrents", fontsize=11, color=INK_2)
    for i, (label, value) in enumerate(kpis[:4]):
        ax = fig.add_subplot(gs[0, i])
        ax.axis("off")
        ax.add_patch(plt.Rectangle((0, 0), 1, 1, transform=ax.transAxes, facecolor="#f0efec",
                                   edgecolor="none", zorder=0))
        long = len(value) >= 14     # un nom long passe sur deux lignes, en plus petit
        ax.text(0.06, 0.64, textwrap.fill(value, 15) if long else value, fontsize=13 if long else 18,
                fontweight="bold", color=INK, transform=ax.transAxes, va="center", linespacing=1.15)
        ax.text(0.06, 0.2, label, fontsize=9.5, color=INK_2, transform=ax.transAxes, va="center")

    ax1 = fig.add_subplot(gs[1, :2])
    c = concepts.join(robust).sort_values("score_opportunite", ascending=False)
    colors = [BLUE if v >= 50 else GRAY for v in c["pct_top3"]]
    _hbars(ax1, c.index, c["score_opportunite"], colors, fmt="{:.2f}", xmax=1)
    ax1.set_title("Quel type de restaurant ? (score d'opportunité, 0 à 1)", fontsize=12)
    ax1.set_xlabel("En bleu : top 3 dans plus de 50 % des simulations")

    ax2 = fig.add_subplot(gs[1, 2:])
    z = zones.sort_values("score_opportunite", ascending=False)
    zc = [BLUE if i < 1 else GRAY for i in range(len(z))]
    _hbars(ax2, [f"{n} ({int(k)} restaurants)" for n, k in zip(z.index, z["nb_etablissements"])],
           z["score_opportunite"], zc, fmt="{:.2f}", xmax=1)
    ax2.set_title("Où ? (score d'opportunité par arrondissement)", fontsize=12)
    ax2.set_xlabel("En bleu : l'arrondissement n°1 · position estimée d'après les adresses Google")
    return fig, save(fig, "00_tableau_de_bord", publish)
