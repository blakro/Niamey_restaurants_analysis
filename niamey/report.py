"""Rapports en français simple, générés à partir des chiffres calculés.

- `RESULTATS.md` : rapport complet, entièrement régénéré à chaque exécution.
- `README.md`    : seul le bloc entre les balises RESULTATS:DEBUT / RESULTATS:FIN
                   est mis à jour ; le reste du texte n'est jamais touché.
"""
from __future__ import annotations

import datetime as dt
import re

import pandas as pd

from . import config

START, END = "<!-- RESULTATS:DEBUT -->", "<!-- RESULTATS:FIN -->"


def fr(x: float, nd: int = 0) -> str:
    """Format français : 1 234,5"""
    s = f"{x:,.{nd}f}"
    return s.replace(",", " ").replace(".", ",")


def pval(p: float) -> str:
    return "p < 0,001" if p < 0.001 else f"p = {fr(p, 2)}"


def _top_concepts(r) -> pd.DataFrame:
    c = r.concepts.join(r.concepts_robust)
    robust = c[c["pct_top3"] >= 50].sort_values(["pct_top3", "score_opportunite"], ascending=False)
    return robust if len(robust) else c.head(2)


def _big_poles(r) -> pd.DataFrame:
    names = [p for p in r.stats["top2_poles"] if p in r.poles.index]
    return r.poles.loc[names]


def findings(r) -> list[str]:
    """Les enseignements clés, en phrases courtes."""
    s = r.stats
    top = _top_concepts(r)
    worst = r.concepts.sort_values("score_opportunite").head(2)
    arr = r.arrondissements.join(r.arrondissements_robust)
    arr_top = arr.sort_values("score_opportunite", ascending=False).iloc[0]
    big = _big_poles(r)
    ratio_web = s["median_reviews_web"] / max(s["median_reviews_noweb"], 1)
    generic = r.concepts_all.loc["Restaurant généraliste", "avis_typique"]

    items = [
        f"**{fr(s['n_restaurants'])} restaurants analysés** (sur {fr(s['n_raw'])} fiches Google Maps, "
        f"après suppression des doublons et des commerces qui ne sont pas des restaurants).",
        f"**{fr(s['pct_lt5_reviews'])} % des restaurants ont moins de 5 avis** : la réputation en ligne "
        f"reste très peu développée à Niamey. Seuls {fr(s['n_reliable'])} restaurants "
        f"({fr(s['pct_reliable'])} %) ont une note vraiment solide (au moins {config.RELIABLE_REVIEWS} avis).",
        f"**{fr(s['n_five_star_le5'])} des {fr(s['n_five_star'])} restaurants notés 5★ ont 5 avis ou moins.** "
        f"C'est pourquoi on utilise une *note corrigée*, qui ne se laisse pas impressionner par 1 ou 2 avis.",
        f"**Aucun type de cuisine n'est mieux noté qu'un autre** de façon fiable ({pval(s['kruskal_p'])}). "
        f"Ce qui distingue les concepts, c'est la **demande** (clients par établissement) et la **concurrence**.",
    ]
    lines = [f"**{name}** ({int(row.nb_etablissements)} établissements, {fr(row.avis_typique, 1)} avis "
             f"typiques chacun, top 3 dans {fr(row.pct_top3)} % des simulations)" for name, row in top.iterrows()]
    items.append("**Concepts les plus prometteurs** : " + " ; ".join(lines)
                 + f". À comparer avec {fr(generic, 1)} avis pour un restaurant généraliste.")
    items.append(
        "**Concepts saturés : " + "** et **".join(worst.index) + "** — "
        + " ; ".join(f"{int(row.nb_etablissements)} établissements, seulement {fr(row.avis_typique, 1)} avis chacun"
                     for _, row in worst.iterrows()) + ".")
    if len(big) == 2:
        hi, lo = big.sort_values("avis_typique", ascending=False).index
        items.append(
            f"**Où ?** {fr(s['pct_geo_in_top2_poles'])} % des restaurants localisés sont concentrés dans "
            f"2 pôles. Dans le pôle **{hi}**, chaque restaurant attire {fr(big.loc[hi, 'avis_typique'], 1)} avis "
            f"typiques, contre {fr(big.loc[lo, 'avis_typique'], 1)} dans le pôle **{lo}**, presque aussi "
            f"fourni mais nettement plus saturé. Par arrondissement, **{arr_top.name}** arrive en tête "
            f"(n°1 dans {fr(arr_top.pct_top3)} % des simulations).")
    items.append(
        f"**Un site web va de pair avec {fr(ratio_web)}× plus d'avis** (médiane {fr(s['median_reviews_web'], 1)} "
        f"contre {fr(s['median_reviews_noweb'], 1)}, {pval(s['p_web_reviews'])}), **mais pas avec une "
        f"meilleure note** ({pval(s['p_web_score'])}) : c'est un levier de visibilité, pas de qualité.")
    return items


def leads_lines(r, n: int = 3) -> list[str]:
    out = []
    for _, row in r.leads.head(n).iterrows():
        comp = ("aucun établissement de ce type" if row.concurrents_meme_concept == 0
                else f"{int(row.concurrents_meme_concept)} seul établissement de ce type")
        out.append(f"**{row.concept}** dans le pôle **{row.pole}** : {comp} parmi "
                   f"{int(row.restaurants_dans_le_pole)} restaurants ({fr(row.avis_total_du_pole)} avis au total).")
    return out


CAVEAT = (
    "⚠️ Les données viennent d'une recherche « restaurants » sur Google Maps : les boulangeries, bars ou "
    "cafés qui ne se présentent pas aussi comme restaurants n'y figurent pas. Avant d'investir, il faut "
    "**compter la concurrence réelle sur le terrain** — ces résultats indiquent des pistes, pas des certitudes."
)


def readme_block(r) -> str:
    today = dt.date.today().strftime("%d/%m/%Y")
    parts = [START, "", f"*Chiffres calculés automatiquement le {today}.*", ""]
    parts += [f"{i}. {t}" for i, t in enumerate(findings(r), 1)]
    if len(r.leads):
        parts += ["", "**Pistes concrètes (type × lieu)** — un concept prometteur là où il est absent :", ""]
        parts += [f"- {t}" for t in leads_lines(r)]
    parts += ["", f"> {CAVEAT}", "", END]
    return "\n".join(parts)


def update_readme(r, path=config.README) -> bool:
    """Remplace le bloc de résultats du README. Ne touche à rien d'autre."""
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    if START not in text or END not in text:
        return False
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)
    path.write_text(pattern.sub(lambda _: readme_block(r), text), encoding="utf-8")
    return True


def dashboard_kpis(r) -> list[tuple[str, str]]:
    s = r.stats
    top = _top_concepts(r).index[0]
    arr = r.arrondissements.sort_values("score_opportunite", ascending=False).index[0]
    return [
        ("restaurants analysés", fr(s["n_restaurants"])),
        ("ont moins de 5 avis Google", f"{fr(s['pct_lt5_reviews'])} %"),
        ("type de restaurant n°1", top),
        ("arrondissement n°1", arr),
    ]


def summary_text(r) -> str:
    return "\n".join(re.sub(r"\*", "", f"• {t}") for t in findings(r))


# ── Rapport complet ──────────────────────────────────────────────────────────
def _table(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join(["---"] * len(cols)) + "|"]
    for _, row in df.iterrows():
        lines.append("| " + " | ".join(str(v) for v in row.values) + " |")
    return "\n".join(lines)


def _ranking_table(scores: pd.DataFrame, robust: pd.DataFrame, top_label: str) -> str:
    t = scores.join(robust).reset_index()
    name_col = t.columns[0]
    out = pd.DataFrame({
        "Rang": t["rang"],
        "Groupe": "**" + t[name_col].astype(str) + "**",
        "Établissements": t["nb_etablissements"].astype(int),
        "Avis typiques / établissement": t["avis_typique"].map(lambda v: fr(v, 1)),
        "Note corrigée moyenne": t["note_moyenne"].map(lambda v: fr(v, 2)),
        "Demande (0-1)": t["demande"].map(lambda v: fr(v, 2)),
        "Concurrence (0-1)": t["concurrence"].map(lambda v: fr(v, 2)),
        "Marge (0-1)": t["marge"].map(lambda v: fr(v, 2)),
        "**Score**": t["score_opportunite"].map(lambda v: f"**{fr(v, 2)}**"),
        top_label: t["pct_top3"].map(lambda v: f"{fr(v)} %"),
        "Confiance": t["confiance"],
    })
    return _table(out)


def write_results_md(r, path=config.RESULTS_MD) -> None:
    s = r.stats
    w = config.WEIGHTS
    log = r.log.to_frame()
    log["nombre"] = log["nombre"].map(fr)
    all_c = r.concepts_all.sort_values("nb_etablissements", ascending=False).reset_index()
    panorama = pd.DataFrame({
        "Type de restaurant": all_c["concept"],
        "Établissements": all_c["nb_etablissements"].astype(int),
        "Part du marché": all_c["part_du_marche_pct"].map(lambda v: f"{fr(v, 1)} %"),
        "Avis au total": all_c["avis_total"].map(fr),
        "Avis typiques / établissement": all_c["avis_typique"].map(lambda v: fr(v, 1)),
        "Note corrigée moyenne": all_c["note_moyenne"].map(lambda v: fr(v, 2)),
    })
    leads = r.leads.copy()
    if len(leads):
        leads = pd.DataFrame({
            "Type": leads["concept"], "Pôle": leads["pole"],
            "Concurrents du même type dans le pôle": leads["concurrents_meme_concept"],
            "Restaurants dans le pôle": leads["restaurants_dans_le_pole"],
            "Avis dans le pôle": leads["avis_total_du_pole"].map(fr),
            "Score de la piste": leads["score_piste"].map(lambda v: fr(v, 2)),
        })

    md = f"""# Résultats détaillés

> Ce fichier est **généré automatiquement** par `python run_pipeline.py`
> (dernière exécution : {dt.date.today().strftime("%d/%m/%Y")}). Ne pas le modifier à la main.
> Pour l'explication de la démarche, voir le [README](README.md).

## En bref

{chr(10).join(f"{i}. {t}" for i, t in enumerate(findings(r), 1))}

> {CAVEAT}

## 1. Les données

{_table(log)}

- Source : export Google Maps (`data/raw/All_Niamey_Restaurants.csv`).
- {fr(s['pct_generic_google'])} % des fiches sont simplement étiquetées « Restaurant » par Google. En lisant
  aussi le nom de l'établissement (« pizza », « grill », « maquis », « pâtisserie »…), on a pu
  préciser le type de {fr(s['n_restaurants'] - s['n_generic'])} établissements ; {fr(s['n_generic'])} restent
  « Restaurant généraliste ».

![Parcours des données](docs/figures/01_parcours_des_donnees.png)

## 2. Ce que disent les avis

| Constat | Chiffre |
|---|---|
| Note Google moyenne du marché | {fr(s['market_mean_score'], 2)}★ |
| Nombre d'avis médian par restaurant | {fr(s['median_reviews'])} |
| Restaurants sans aucun avis | {fr(s['n_no_review'])} |
| Restaurants avec moins de 5 avis | {fr(s['pct_lt5_reviews'])} % |
| Restaurants notés 5★ dont la note repose sur 5 avis ou moins | {fr(s['n_five_star_le5'])} sur {fr(s['n_five_star'])} |
| Lien entre nombre d'avis et note (Spearman) | ρ = {fr(s['spearman_rho'], 2)} ({pval(s['spearman_p'])}) : plus un restaurant a d'avis, plus sa note est « réaliste » |
| Les notes diffèrent-elles selon le type de cuisine ? (Kruskal-Wallis, {s['kruskal_groups']} types) | Non : {pval(s['kruskal_p'])} |
| Avis (médiane) avec / sans site web | {fr(s['median_reviews_web'], 1)} / {fr(s['median_reviews_noweb'], 1)} ({pval(s['p_web_reviews'])}) |
| Note (médiane, ≥ {config.RELIABLE_REVIEWS} avis) avec / sans site web | {fr(s['median_score_web'], 1)} / {fr(s['median_score_noweb'], 1)} ({pval(s['p_web_score'])}) |

**Note corrigée** : on fait comme si chaque restaurant avait déjà reçu {config.PRIOR_REVIEWS} avis « moyens »
({fr(s['market_mean_score'], 2)}★) avant ses vrais avis. Exemple : 5★ sur 1 avis devient
{fr((config.PRIOR_REVIEWS * s['market_mean_score'] + 5) / (config.PRIOR_REVIEWS + 1), 2)}★, alors que 4,9★ sur
443 avis reste à {fr((config.PRIOR_REVIEWS * s['market_mean_score'] + 443 * 4.9) / (config.PRIOR_REVIEWS + 443), 2)}★.

![Notes corrigées](docs/figures/02_notes_corrigees.png)

## 3. Quel type de restaurant ouvrir ?

### Panorama

{_table(panorama)}

*Avis typiques / établissement* : nombre d'avis d'un établissement « ordinaire » du groupe
(moyenne géométrique, qui n'est pas faussée par une ou deux adresses très célèbres).

![Panorama](docs/figures/04_panorama_concepts.png)

### Classement d'opportunité

Score = {fr(w['demande'] * 100)} % **demande** + {fr(w['concurrence'] * 100)} % **concurrence**
+ {fr(w['marge'] * 100)} % **marge de progression**. Seuls les types comptant au moins
{config.MIN_CONCEPT_SIZE} établissements sont classés ; « Restaurant généraliste », « Hôtel-restaurant »
et « Cantine & traiteur » servent de référence.

{_ranking_table(r.concepts, r.concepts_robust, "Top 3 (simulations)")}

*Top 3 (simulations)* : part des {fr(config.N_SIMULATIONS)} simulations (échantillon de restaurants et poids des
critères tirés au hasard) où le type finit dans les 3 premiers. **Au-dessus de 50 %, le résultat est robuste.**
*Confiance* : Bonne = au moins 8 établissements avec une note solide, Moyenne = 4 à 7, Faible = moins de 4.

![Matrice d'opportunité](docs/figures/05_matrice_opportunite.png)

![Robustesse](docs/figures/09_robustesse_concepts.png)

## 4. Où ?

{fr(s['n_geocoded'])} restaurants ({fr(s['pct_geocoded'])} %) ont une position exploitable (Plus Code Google).
L'arrondissement et le quartier sont estimés en rattachant chaque restaurant au centre de quartier le plus
proche (référentiel approximatif : `data/raw/niamey_quartiers_reference.csv`).

### Par arrondissement

{_ranking_table(r.arrondissements, r.arrondissements_robust, "N°1 (simulations)")}

![Arrondissements](docs/figures/10_zones_arrondissements.png)

### Par pôle de restauration

Un **pôle** est un groupe d'au moins {config.DBSCAN_MIN_SAMPLES} restaurants situés à moins de
{config.DBSCAN_EPS_M} m les uns des autres (algorithme DBSCAN). On en trouve {s['n_poles']}, qui regroupent
{fr(s['n_in_poles'])} restaurants ; les {len(r.poles)} pôles d'au moins {config.MIN_ZONE_SIZE} restaurants sont classés
ci-dessous. Attention : la plupart sont petits (confiance *faible*), seul le contraste entre les deux grands
pôles est vraiment solide.

{_ranking_table(r.poles, r.poles_robust, "Top 3 (simulations)")}

![Pôles](docs/figures/08_carte_poles.png)

## 5. Pistes concrètes : quel type, à quel endroit ?

Pour les types les plus prometteurs, les pôles où ils sont absents (ou presque) :

{_table(leads) if len(leads) else "_Aucune piste._"}

## 6. Limites à garder en tête

- **Avis ≠ ventes.** Le nombre d'avis Google sert d'indicateur de fréquentation, mais beaucoup de clients
  ne laissent jamais d'avis, surtout dans les établissements populaires et informels.
- **Données incomplètes.** Recherche « restaurants » uniquement ; {fr(100 - s['pct_geocoded'])} % des
  établissements n'ont pas de position exploitable ; une partie des restaurants de Niamey n'est pas sur
  Google Maps.
- **Petits groupes.** Plusieurs types et pôles comptent moins de 15 établissements : la colonne
  *Confiance* et les simulations indiquent jusqu'où on peut s'y fier.
- **Quartiers approximatifs.** Les centres de quartiers sont des repères approximatifs, pas des limites officielles.
- **Photo à un instant donné.** Pas d'historique : impossible de voir les ouvertures/fermetures ni les tendances.
"""
    path.write_text(md, encoding="utf-8")
