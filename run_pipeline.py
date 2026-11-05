"""Relance toute l'analyse en une commande :

    python run_pipeline.py

Produit : les tableaux (data/processed/), les graphiques (data/processed/figures/
et docs/figures/), la carte interactive (docs/map_PORTFOLIO.html), le rapport
RESULTATS.md et met à jour le bloc de résultats du README.
"""
import matplotlib

matplotlib.use("Agg")  # pas de fenêtre : on enregistre seulement les images

from niamey.pipeline import run_all  # noqa: E402

if __name__ == "__main__":
    run_all()
