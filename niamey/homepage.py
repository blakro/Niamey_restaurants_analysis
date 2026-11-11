"""Page d'accueil du site GitHub Pages (docs/index.html).

Générée à partir des mêmes calculs que le README et RESULTATS.md : ses
chiffres sont donc toujours cohérents avec le reste du projet.
"""
from __future__ import annotations

import html
import re

from . import config, report

CSS = """
:root {
  color-scheme: light;
  --bg: #f9f9f7; --surface: #fcfcfb; --surface-2: #f0efec; --ink: #0b0b0b; --ink-2: #52514e;
  --muted: #898781; --line: #e1e0d9; --accent: #2a78d6; --accent-strong: #184f95; --on-accent: #ffffff;
  --accent-soft: #e8f1fc; --warn-bg: #fdf3e1; --warn-line: #c98500;
}
@media (prefers-color-scheme: dark) {
  :root {
    color-scheme: dark;
    --bg: #0d0d0d; --surface: #1a1a19; --surface-2: #232321; --ink: #f0efec; --ink-2: #c3c2b7;
    --muted: #898781; --line: #2c2c2a; --accent: #3987e5; --accent-strong: #86b6ef; --on-accent: #ffffff;
    --accent-soft: #16263b; --warn-bg: #2a2214; --warn-line: #c98500;
  }
}
* { box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%; }
body {
  margin: 0; background: var(--bg); color: var(--ink);
  font: 16px/1.6 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
}
main { max-width: 980px; margin: 0 auto; padding: 32px 16px 48px; }
a { color: var(--accent-strong); }
header .eyebrow { color: var(--ink-2); font-size: 14px; letter-spacing: .02em; margin: 0 0 6px; }
h1 { font-size: clamp(28px, 5vw, 42px); line-height: 1.15; margin: 0 0 12px; }
h2 { font-size: 22px; margin: 44px 0 12px; }
.lead { font-size: 18px; color: var(--ink-2); margin: 0 0 20px; max-width: 70ch; }
.actions { display: flex; flex-wrap: wrap; gap: 10px; margin: 0 0 28px; }
.btn {
  display: inline-flex; align-items: center; gap: 8px; padding: 10px 16px; border-radius: 10px;
  text-decoration: none; font-weight: 600; border: 1px solid var(--line); background: var(--surface); color: var(--ink);
}
.btn.primary { background: var(--accent); border-color: var(--accent); color: var(--on-accent); }
.btn:focus-visible { outline: 3px solid var(--accent); outline-offset: 2px; }
.kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; }
.kpi { background: var(--surface-2); border-radius: 12px; padding: 16px 18px; }
.kpi .value { font-size: 26px; font-weight: 700; line-height: 1.2; overflow-wrap: anywhere; }
.kpi .label { color: var(--ink-2); font-size: 14px; margin-top: 4px; }
ol.findings { padding-left: 1.4em; margin: 0; }
ol.findings li { margin: 0 0 12px; padding-left: 4px; }
ul.leads { padding-left: 1.2em; }
.glossary { margin: 0; }
.glossary dt { font-weight: 700; margin-top: 12px; }
.glossary dd { margin: 2px 0 0; color: var(--ink-2); max-width: 75ch; }
.callout {
  background: var(--warn-bg); border-left: 4px solid var(--warn-line); border-radius: 8px;
  padding: 12px 16px; margin: 20px 0 0; color: var(--ink);
}
.map-frame { width: 100%; height: min(70vh, 560px); border: 1px solid var(--line); border-radius: 12px; background: var(--surface); }
.figure { margin: 20px 0 0; }
.figure img { display: block; width: 100%; height: auto; border-radius: 12px; background: #fcfcfb; border: 1px solid var(--line); }
.figure figcaption { color: var(--ink-2); font-size: 14px; margin-top: 8px; }
.steps { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 12px; padding: 0; list-style: none; }
.steps li { background: var(--surface); border: 1px solid var(--line); border-radius: 12px; padding: 14px 16px; }
.steps b { display: block; margin-bottom: 4px; }
.steps span { color: var(--ink-2); font-size: 15px; }
footer { margin-top: 48px; padding-top: 16px; border-top: 1px solid var(--line); color: var(--ink-2); font-size: 14px; }
code { background: var(--surface-2); padding: 1px 5px; border-radius: 5px; font-size: .92em; }
"""


def md_inline(text: str) -> str:
    """Mini-Markdown sûr : échappe le HTML puis convertit **gras**, *italique* et `code`."""
    s = html.escape(text, quote=False)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<!\*)\*(?!\s)(.+?)(?<!\s)\*(?!\*)", r"<em>\1</em>", s)
    return re.sub(r"`(.+?)`", r"<code>\1</code>", s)


def _steps() -> str:
    w = {k: round(v * 100) for k, v in config.WEIGHTS.items()}
    items = [
        ("📥 Collecter", "Export Google Maps : nom, type, note, nombre d'avis et adresse de chaque établissement."),
        ("🧹 Nettoyer et classer", "Doublons et commerces non-restaurants retirés ; type de restaurant deviné à "
                                  "partir du nom (« Pizza Club » → pizzeria)."),
        ("⭐ Corriger les notes", f"Chaque restaurant reçoit {config.PRIOR_REVIEWS} avis « moyens » fictifs : "
                                 "un 5★ obtenu avec un seul avis ne fausse plus les classements."),
        ("🗺️ Placer sur la carte", f"Plus Codes convertis en coordonnées ; un pôle = au moins "
                                   f"{config.DBSCAN_MIN_SAMPLES} restaurants à moins de {config.DBSCAN_EPS_M} m."),
        ("🎯 Comparer", f"Score d'opportunité : clients par établissement ({w['demande']} %), "
                       f"peu de concurrents ({w['concurrence']} %), marge de progression ({w['marge']} %)."),
        ("✅ Vérifier", f"{report.fr(config.N_SIMULATIONS)} simulations : un résultat est jugé solide s'il reste "
                       "dans le top 3 plus d'une fois sur deux."),
    ]
    return "\n".join(f"<li><b>{html.escape(t)}</b><span>{html.escape(d)}</span></li>" for t, d in items)


def _glossary() -> str:
    items = [
        ("Avis typiques", "Le nombre d'avis Google d'un établissement « ordinaire » d'un groupe. On s'en sert comme "
                          "indice de fréquentation : en général, plus un lieu a de clients, plus il reçoit d'avis."),
        ("Note corrigée", "La note Google, rendue prudente quand elle repose sur très peu d'avis."),
        ("Pôle de restauration", f"Un groupe d'au moins {config.DBSCAN_MIN_SAMPLES} restaurants situés à moins de "
                                 f"{config.DBSCAN_EPS_M} m les uns des autres, comme une « rue des restaurants »."),
        ("Simulations", f"On refait le classement {report.fr(config.N_SIMULATIONS)} fois en modifiant légèrement les "
                        "données et les critères. Un résultat qui revient plus d'une fois sur deux est jugé solide."),
        ("Médiane", "La valeur « du milieu » : la moitié des restaurants est au-dessus, l'autre moitié en dessous."),
        ("p", "La probabilité qu'un écart soit dû au seul hasard. En dessous de 0,05, on considère que l'écart est "
              "réel ; au-dessus, on ne peut rien conclure."),
    ]
    return "\n".join(f"<dt>{html.escape(t)}</dt><dd>{html.escape(d)}</dd>" for t, d in items)


def build(r) -> str:
    s = r.stats
    kpis = "\n".join(
        f'<div class="kpi"><div class="value">{html.escape(v)}</div><div class="label">{html.escape(k)}</div></div>'
        for k, v in report.dashboard_kpis(r)
    )
    findings = "\n".join(f"<li>{md_inline(t)}</li>" for t in report.findings(r))
    leads = "\n".join(f"<li>{md_inline(t)}</li>" for t in report.leads_lines(r))
    results_url = f"{config.REPO_URL}/blob/main/RESULTATS.md"
    map_name = config.PORTFOLIO_MAP.name

    return f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Restaurants de Niamey</title>
<meta name="description" content="Quel restaurant ouvrir à Niamey, et où ? Analyse de {s['n_raw']} fiches Google Maps.">
<style>{CSS}</style>
</head>
<body>
<main>
  <header>
    <p class="eyebrow">Analyse de données · Niamey (Niger)</p>
    <h1>Quel restaurant ouvrir à Niamey, et où&nbsp;?</h1>
    <p class="lead">On a étudié les {report.fr(s['n_raw'])} fiches Google Maps des restaurants de la ville — leur type,
      leur note, leur nombre d'avis et leur emplacement — pour repérer où il reste de la place :
      beaucoup de clients et peu de concurrents.</p>
    <nav class="actions" aria-label="Liens principaux">
      <a class="btn primary" href="{map_name}">🗺️ Ouvrir la carte interactive</a>
      <a class="btn" href="{results_url}">📊 Résultats détaillés</a>
      <a class="btn" href="{config.REPO_URL}">💻 Code et méthode</a>
    </nav>
  </header>

  <section aria-label="Chiffres clés">
    <div class="kpis">
{kpis}
    </div>
  </section>

  <section>
    <h2>Ce que disent les données</h2>
    <ol class="findings">
{findings}
    </ol>
    <h2>Pistes concrètes : quel type, à quel endroit&nbsp;?</h2>
    <ul class="leads">
{leads}
    </ul>
    <p class="callout">{md_inline(report.CAVEAT)}</p>
  </section>

  <section>
    <h2>Les mots utilisés</h2>
    <dl class="glossary">
{_glossary()}
    </dl>
  </section>

  <section>
    <h2>La carte</h2>
    <p>Chaque point est un restaurant ; cliquez dessus pour voir sa fiche. Le bouton « calques », en haut à
      droite de la carte, permet de n'afficher qu'un type de restaurant.
      <a href="{map_name}">Ouvrir la carte en plein écran</a>.</p>
    <iframe class="map-frame" src="{map_name}" title="Carte interactive des restaurants de Niamey" loading="lazy"></iframe>
  </section>

  <section>
    <h2>En images</h2>
    <figure class="figure">
      <img src="figures/05_matrice_opportunite.png" loading="lazy"
           alt="Matrice d'opportunité : chaque type de restaurant placé selon son nombre d'établissements et le nombre d'avis typique par établissement.">
      <figcaption>Où reste-t-il de la place ? En haut à gauche : beaucoup de clients par établissement et peu de concurrents. En bas à droite : marché saturé.</figcaption>
    </figure>
    <figure class="figure">
      <img src="figures/09_robustesse_concepts.png" loading="lazy"
           alt="Part des simulations où chaque type de restaurant termine dans le top 3.">
      <figcaption>Un résultat est jugé solide si le type de restaurant finit dans le top 3 dans plus de la moitié des simulations.</figcaption>
    </figure>
    <figure class="figure">
      <img src="figures/00_tableau_de_bord.png" loading="lazy"
           alt="Tableau de bord : chiffres clés, score d'opportunité par type de restaurant et par arrondissement.">
      <figcaption>Tableau de bord de synthèse.</figcaption>
    </figure>
  </section>

  <section>
    <h2>Comment c'est fait</h2>
    <ol class="steps">
{_steps()}
    </ol>
  </section>

  <footer>
    Données : fiches publiques Google Maps, Niamey (Niger) · Carte © contributeurs OpenStreetMap ·
    Code sous licence MIT, <a href="{config.REPO_URL}">sur GitHub</a>.<br>
    Page générée automatiquement par <code>python run_pipeline.py</code> : ses chiffres sont les mêmes que
    dans le README et le rapport détaillé.
  </footer>
</main>
</body>
</html>
"""


def write(r, path=config.INDEX_HTML) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(build(r), encoding="utf-8")
    # Sert les fichiers tels quels sur GitHub Pages (pas de traitement Jekyll).
    (path.parent / ".nojekyll").touch()
