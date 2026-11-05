"""Paramètres centraux du projet.

Tous les choix méthodologiques (seuils, poids, rayons...) sont regroupés ici
pour qu'on puisse les relire, les discuter et les modifier à un seul endroit.
"""
from pathlib import Path

# ── Chemins ──────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
RAW_CSV = ROOT / "data" / "raw" / "All_Niamey_Restaurants.csv"
QUARTIERS_CSV = ROOT / "data" / "raw" / "niamey_quartiers_reference.csv"

PROC_DIR = ROOT / "data" / "processed"
FIG_DIR = PROC_DIR / "figures"          # toutes les figures (non versionnées)
MAP_DIR = PROC_DIR / "maps"             # toutes les cartes (non versionnées)

DOCS_DIR = ROOT / "docs"                # publié via GitHub Pages (versionné)
DOCS_FIG_DIR = DOCS_DIR / "figures"     # figures affichées dans le README
PORTFOLIO_MAP = DOCS_DIR / "map_PORTFOLIO.html"
RESULTS_MD = ROOT / "RESULTATS.md"      # rapport chiffré, régénéré à chaque exécution
README = ROOT / "README.md"

CLEAN_CSV = PROC_DIR / "restaurants_clean.csv"
GEO_CSV = PROC_DIR / "restaurants_geo.csv"
CONCEPTS_CSV = PROC_DIR / "opportunites_concepts.csv"
ZONES_CSV = PROC_DIR / "opportunites_zones.csv"
COMBOS_CSV = PROC_DIR / "pistes_concept_zone.csv"

# ── Nettoyage ────────────────────────────────────────────────────────────────
# Catégories Google qui ne sont pas des restaurants (commerces, loisirs).
NON_FOOD_CATEGORIES = {
    "Parc de loisirs",
    "Épicerie",
    "Vente de légumes en gros",
    "Magasin vendant du poulet",
}

# ── Note « corrigée » (moyenne bayésienne) ───────────────────────────────────
# On fait comme si chaque restaurant avait déjà reçu PRIOR_REVIEWS avis
# « moyens » avant ses vrais avis. Un 5★ obtenu avec 1 seul avis est donc
# ramené vers la moyenne, alors qu'un 4,8★ sur 400 avis bouge à peine.
# (L'ancienne version utilisait la moyenne du nombre d'avis ≈ 39, valeur tirée
#  vers le haut par quelques établissements très connus : elle écrasait toutes
#  les notes autour de 4,1 et rendait les comparaisons quasi impossibles.)
PRIOR_REVIEWS = 10

# Seuil à partir duquel la note d'un restaurant est jugée « solide ».
RELIABLE_REVIEWS = 10

# ── Géographie ───────────────────────────────────────────────────────────────
NIAMEY_LAT, NIAMEY_LNG = 13.5137, 2.1098
# Boîte englobante large de l'agglomération (contrôle qualité du géocodage).
BBOX = dict(lat_min=13.30, lat_max=13.80, lng_min=1.85, lng_max=2.35)

# DBSCAN : deux restaurants à moins de 500 m sont « voisins » ; il faut au
# moins 4 restaurants proches pour former un pôle de restauration.
DBSCAN_EPS_M = 500
DBSCAN_MIN_SAMPLES = 4
# Au-delà de cette distance du quartier de référence le plus proche, on
# considère la position comme « périphérique » (référentiel moins précis).
PERIPHERY_DIST_M = 1500

# ── Modèle d'opportunité ─────────────────────────────────────────────────────
# Trois questions simples, chacune notée de 0 à 1 :
#   1. Demande     : chaque établissement attire-t-il beaucoup de clients ?
#   2. Concurrence : y a-t-il peu d'établissements de ce type ?
#   3. Marge de progression : les clients sont-ils seulement moyennement
#      satisfaits de l'offre actuelle (place pour mieux faire) ?
WEIGHTS = {"demande": 0.45, "concurrence": 0.35, "marge": 0.20}

# Taille minimale d'un groupe pour être classé (en dessous : trop peu de données).
MIN_CONCEPT_SIZE = 5
MIN_ZONE_SIZE = 5

# Simulations de robustesse (rééchantillonnage + poids aléatoires).
N_SIMULATIONS = 2000
RANDOM_SEED = 42

# Concepts exclus du classement (ce ne sont pas des « concepts » à ouvrir).
NOT_RANKED_CONCEPTS = {"Restaurant généraliste", "Hôtel-restaurant", "Cantine & traiteur"}
