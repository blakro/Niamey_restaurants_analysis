"""Tests automatiques : `python -m pytest`"""
import math

import numpy as np
import pandas as pd
import pytest

from niamey import cleaning, config, geo, opportunity, report
from niamey.concepts import GENERIC, NON_FOOD, infer_concept, normalize_text

NF = config.NON_FOOD_CATEGORIES


# ── Concepts ─────────────────────────────────────────────────────────────────
def test_normalize_text():
    assert normalize_text("Côté Jardin !") == "cote jardin"
    assert normalize_text("O’Takoss") == normalize_text("O'Takoss") == "o takoss"
    assert normalize_text(None) == ""


@pytest.mark.parametrize("name, category, expected", [
    ("Burger time", "Restaurant de cuisine d'Odisha", "Burger & fast-food"),   # étiquette Google fausse
    ("Palais de chawarma", "Restaurant diététique", "Tacos, chawarma & sandwichs"),
    ("Restaurant le mafé", "Restaurant thaï", "Cuisine africaine & locale"),
    ("PIZZA CLUB FONDAKAYAN", "Restaurant", "Pizzeria"),
    ("Maquis Doré", "Restaurant", "Cuisine africaine & locale"),
    ("Boulangerie Rayan", "Boulangerie", "Boulangerie & pâtisserie"),
    ("Two two seven", "Restauration rapide", "Burger & fast-food"),           # repli catégorie Google
    ("Amandine", "Restaurant", GENERIC),
    ("RA'SS", "Vente de légumes en gros", NON_FOOD),
    ("Restauran egyptien", "Épicerie", "Cuisine internationale"),             # le nom dit « restaurant »
])
def test_infer_concept(name, category, expected):
    assert infer_concept(name, category, NF)[0] == expected


# ── Note corrigée ────────────────────────────────────────────────────────────
def test_bayesian_score():
    score = pd.Series([5.0, 4.8, np.nan, 4.0])
    n = pd.Series([1, 1000, 0, 0])
    out = cleaning.bayesian_score(score, n, m=4.0, prior=10)
    assert out[0] == pytest.approx((10 * 4 + 5) / 11)
    assert out[1] == pytest.approx(4.8, abs=0.01)     # beaucoup d'avis → presque inchangé
    assert math.isnan(out[2]) and math.isnan(out[3])  # pas d'avis → pas de note


# ── Géographie ───────────────────────────────────────────────────────────────
def test_decode_plus_code():
    lat, lng = geo.decode_plus_code("G476+RX4, Bd du Zarmaganda")
    b = config.BBOX
    assert b["lat_min"] < lat < b["lat_max"] and b["lng_min"] < lng < b["lng_max"]
    assert all(math.isnan(v) for v in geo.decode_plus_code("rue de la tapoa"))
    assert all(math.isnan(v) for v in geo.decode_plus_code(np.nan))


# ── Modèle d'opportunité ─────────────────────────────────────────────────────
def test_typical_reviews_is_geometric_mean():
    assert opportunity.typical_reviews([0, 0, 0]) == 0
    assert opportunity.typical_reviews([1, 3]) == pytest.approx(math.sqrt(2 * 4) - 1)
    # Insensible à une seule adresse très célèbre, contrairement à la moyenne.
    values = [2, 2, 2, 2, 2000]
    assert opportunity.typical_reviews(values) < 0.05 * np.mean(values)


def test_criteria_directions():
    m = pd.DataFrame({
        "avis_typique": [20.0, 2.0],
        "nb_etablissements": [5, 50],
        "note_moyenne": [3.5, 4.5],
    }, index=["rare et demandé", "saturé"])
    c = opportunity.criteria_scores(m)
    assert ((c >= 0) & (c <= 1)).all().all()
    assert c.loc["rare et demandé"].tolist() == [1.0, 1.0, 1.0]
    assert c.loc["saturé"].tolist() == [0.0, 0.0, 0.0]


# ── Données réelles ──────────────────────────────────────────────────────────
@pytest.fixture(scope="module")
def clean_df():
    df, _ = cleaning.clean(cleaning.load_raw())
    return df


def test_clean_dataset_is_consistent(clean_df):
    assert len(clean_df) > 400
    assert not clean_df["maps_url"].dropna().duplicated().any()
    assert (clean_df["concept"] != NON_FOOD).all()
    assert (clean_df["reviews_count"] >= 0).all()
    s = clean_df["score_bayes"].dropna()
    assert s.between(1, 5).all()
    assert clean_df.loc[~clean_df["is_rated"], "score_bayes"].isna().all()


def test_chains_ignore_generic_names(clean_df):
    chains = set(clean_df.loc[clean_df["is_chain"], "name"].map(normalize_text))
    assert "o takoss" in chains                      # vraie enseigne à deux adresses
    assert not chains & {"fast food", "fastfood"}    # simple nom générique, pas une chaîne


def test_funnel_steps_follow_labels():
    from niamey.pipeline import funnel_steps
    _, log = cleaning.clean(cleaning.load_raw())
    log.add("dont : exemple", 1)
    steps = funnel_steps(log)["étape"].tolist()
    assert steps[0].startswith("Fiches") and steps[1] == cleaning.KEPT_LABEL
    assert all(s.startswith("dont") for s in steps[2:])


def test_robustness_is_reproducible(clean_df):
    groups = ["Pizzeria", "Bar & lounge", "Burger & fast-food"]
    a = opportunity.robustness(clean_df, "concept", groups, n_sim=200)
    b = opportunity.robustness(clean_df, "concept", groups, n_sim=200)
    pd.testing.assert_frame_equal(a, b)
    assert a["pct_top3"].eq(100).all()  # 3 groupes → toujours dans le top 3


# ── README ───────────────────────────────────────────────────────────────────
def test_update_readme_only_touches_the_block(tmp_path, monkeypatch):
    readme = tmp_path / "README.md"
    readme.write_text(f"Intro\n{report.START}\nancien\n{report.END}\nFin\n", encoding="utf-8")
    monkeypatch.setattr(report, "readme_block", lambda r: f"{report.START}\nnouveau\n{report.END}")
    assert report.update_readme(None, path=readme)
    text = readme.read_text(encoding="utf-8")
    assert text == f"Intro\n{report.START}\nnouveau\n{report.END}\nFin\n"


# ── Page d'accueil ───────────────────────────────────────────────────────────
def test_md_inline_is_safe():
    from niamey.homepage import md_inline
    assert md_inline("**gras** et *note corrigée*") == "<strong>gras</strong> et <em>note corrigée</em>"
    assert "<script>" not in md_inline("<script>alert(1)</script>")


def test_homepage_links_exist_and_numbers_match():
    import re as _re
    from niamey import homepage, pipeline
    r = pipeline.compute()
    page = homepage.build(r)
    local = [u for u in _re.findall(r'(?:href|src)="([^"]+)"', page) if not u.startswith("http")]
    assert local, "aucun lien local trouvé"
    for u in local:
        assert (config.DOCS_DIR / u).exists(), u
    from html import escape
    for label, value in report.dashboard_kpis(r):          # mêmes chiffres que le README
        assert escape(value) in page and escape(label) in page
    assert report.readme_block(r) == report.readme_block(r)  # pas de date : sortie stable


# ── Carte ────────────────────────────────────────────────────────────────────
def test_map_is_reproducible(tmp_path):
    """Deux exécutions sur les mêmes données donnent exactement le même fichier."""
    from niamey import maps, pipeline
    r = pipeline.compute()
    zones = pipeline.all_poles(r.geo)
    a, b = tmp_path / "a.html", tmp_path / "b.html"
    maps.build_map(r.geo, zones, path=a)
    maps.build_map(r.geo, zones, path=b)
    assert a.read_bytes() == b.read_bytes()
