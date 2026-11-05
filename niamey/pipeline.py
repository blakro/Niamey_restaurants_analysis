"""Enchaîne toutes les étapes. Utilisé par `run_pipeline.py` et les notebooks."""
from __future__ import annotations

from dataclasses import dataclass

import matplotlib.pyplot as plt
import pandas as pd

from . import cleaning, config, geo, maps, opportunity, report, stats, viz


@dataclass
class Results:
    raw: pd.DataFrame
    clean: pd.DataFrame
    log: cleaning.CleaningLog
    geo: pd.DataFrame
    stats: dict
    concepts_all: pd.DataFrame
    concepts: pd.DataFrame
    concepts_robust: pd.DataFrame
    arrondissements: pd.DataFrame
    arrondissements_robust: pd.DataFrame
    poles: pd.DataFrame
    poles_robust: pd.DataFrame
    leads: pd.DataFrame


def compute() -> Results:
    raw = cleaning.load_raw()
    clean, log = cleaning.clean(raw)
    g = geo.run(clean)
    g.attrs.update(clean.attrs)
    log.add("dont : avec une note Google", int(g["is_rated"].sum()))
    log.add("dont : localisés sur la carte (Plus Code)", int(g["is_geocoded"].sum()))
    log.add(f"dont : note solide (≥ {config.RELIABLE_REVIEWS} avis)",
            int((g["reviews_count"] >= config.RELIABLE_REVIEWS).sum()))

    concepts = opportunity.score_groups(g, "concept", config.MIN_CONCEPT_SIZE,
                                        exclude=config.NOT_RANKED_CONCEPTS)
    concepts_robust = opportunity.robustness(g, "concept", concepts.index.tolist())

    g_arr = g[g["arrondissement"].notna()]
    arr = opportunity.score_groups(g_arr, "arrondissement", config.MIN_ZONE_SIZE)
    arr_robust = opportunity.robustness(g_arr, "arrondissement", arr.index.tolist(), top_k=1)

    g_pole = g[g["pole_id"] >= 0]
    poles = opportunity.score_groups(g_pole, "pole", config.MIN_ZONE_SIZE)
    poles_robust = opportunity.robustness(g_pole, "pole", poles.index.tolist())

    leads = opportunity.concept_zone_leads(g, concepts.join(concepts_robust)
                                           .sort_values(["pct_top3", "score_opportunite"], ascending=False),
                                           poles)
    return Results(
        raw=raw, clean=clean, log=log, geo=g, stats=stats.key_stats(g, len(raw)),
        concepts_all=opportunity.group_metrics(g, "concept"),
        concepts=concepts, concepts_robust=concepts_robust,
        arrondissements=arr, arrondissements_robust=arr_robust,
        poles=poles, poles_robust=poles_robust, leads=leads,
    )


def export_tables(r: Results) -> None:
    config.PROC_DIR.mkdir(parents=True, exist_ok=True)
    r.clean.to_csv(config.CLEAN_CSV, index=False, encoding="utf-8-sig")
    r.geo.to_csv(config.GEO_CSV, index=False, encoding="utf-8-sig")
    r.concepts.join(r.concepts_robust).to_csv(config.CONCEPTS_CSV, encoding="utf-8-sig")
    pd.concat({
        "arrondissement": r.arrondissements.join(r.arrondissements_robust),
        "pole": r.poles.join(r.poles_robust),
    }, names=["niveau", "zone"]).to_csv(config.ZONES_CSV, encoding="utf-8-sig")
    r.leads.to_csv(config.COMBOS_CSV, index=False, encoding="utf-8-sig")


def make_figures(r: Results, show: bool = False) -> None:
    s = r.stats
    figs = [
        viz.fig_funnel(r.log.to_frame().iloc[[0, -4, -3, -2, -1]].reset_index(drop=True), publish=True),
        viz.fig_bayes(r.geo, publish=True),
        viz.fig_reviews_tiers(r.geo),
        viz.fig_concepts(r.concepts_all, publish=True),
        viz.fig_matrix(r.concepts, r.concepts_robust, publish=True),
        viz.fig_website(r.geo, s["p_web_reviews"], s["p_web_score"]),
        viz.fig_scores_by_concept(r.geo, s["kruskal_p"]),
        viz.fig_static_map(r.geo, publish=True),
        viz.fig_robustness(r.concepts_robust, "Le classement des concepts résiste-t-il au hasard ?",
                           "09_robustesse_concepts", publish=True),
        viz.fig_zones(r.arrondissements, "Clients attirés par restaurant, par arrondissement",
                      "10_zones_arrondissements", publish=True),
        viz.fig_zones(r.poles, "Clients attirés par restaurant, par pôle de restauration",
                      "11_zones_poles"),
        viz.fig_dashboard(report.dashboard_kpis(r), r.concepts, r.concepts_robust, r.arrondissements),
    ]
    if not show:
        for fig, _ in figs:
            plt.close(fig)


def run_all(verbose: bool = True) -> Results:
    r = compute()
    export_tables(r)
    make_figures(r)
    maps.build_map(r.geo, r.poles)
    report.write_results_md(r)
    report.update_readme(r)
    if verbose:
        print(r.log.to_frame().to_string(index=False))
        print()
        print(report.summary_text(r))
    return r
