"""Carte interactive (Folium) publiée sur GitHub Pages."""
from __future__ import annotations

import html

import folium
import pandas as pd
import xyzservices.providers as xyz
from folium.plugins import Fullscreen, HeatMap, MarkerCluster

from . import config

# Rampe ordinale à une seule teinte (bleu) : plus c'est foncé, meilleure est la note.
# Trois niveaux seulement : avec quatre, les deux bleus clairs étaient indiscernables
# (écart de luminosité insuffisant, vérifié avec un validateur de palette).
SCORE_LEVELS = [
    (4.5, "#0d366b", "4,5★ et plus — excellent"),
    (4.0, "#2a78d6", "4,0 à 4,5★ — bon"),
    (0.0, "#86b6ef", "moins de 4,0★ — moyen ou faible"),
]
NO_SCORE = ("#898781", "pas encore noté")
POLE_COLOR = "#eb6834"

# Groupes de points en gris neutre : les couleurs par défaut du plugin (vert,
# jaune, orange) laissaient croire à une information de qualité.
CLUSTER_ICON_JS = """
function(cluster) {
  var n = cluster.getChildCount();
  var s = n < 10 ? 30 : (n < 50 ? 38 : 46);
  return L.divIcon({
    html: '<div style="width:' + s + 'px;height:' + s + 'px;border-radius:50%;'
        + 'background:rgba(82,81,78,.88);color:#fff;font:600 12px system-ui,sans-serif;'
        + 'line-height:' + s + 'px;text-align:center;'
        + 'box-shadow:0 0 0 3px rgba(255,255,255,.85)">' + n + '</div>',
    className: 'groupe-restaurants', iconSize: L.point(s, s)
  });
}
"""


def score_color(score) -> str:
    if pd.isna(score):
        return NO_SCORE[0]
    for threshold, color, _ in SCORE_LEVELS:
        if score >= threshold:
            return color
    return SCORE_LEVELS[-1][1]


def radius(n_reviews: int) -> int:
    return 4 if n_reviews < 5 else 6 if n_reviews < 20 else 8 if n_reviews < 50 else 11


def _fmt(x: float, nd: int = 1) -> str:
    return f"{x:.{nd}f}".replace(".", ",")


def popup_html(r: pd.Series) -> str:
    e = html.escape
    raw = f"{_fmt(r['score_raw'])}★ sur {int(r['reviews_count'])} avis" if pd.notna(r["score_raw"]) else "pas de note"
    bayes = f"{_fmt(r['score_bayes'], 2)}★" if pd.notna(r["score_bayes"]) else "—"
    header = (f"<b style='font-size:14px'>{e(str(r['name']))}</b><br>"
              f"<span style='color:#52514e'>{e(r['concept'])}</span><hr style='margin:6px 0'>")
    lines = [
        f"Note Google : {raw}",
        f"Note corrigée : <b>{bayes}</b>",
        f"Zone : {e(str(r['pole']))}" + (f" · quartier ≈ {e(str(r['quartier']))}" if pd.notna(r.get("quartier")) else ""),
    ]
    if r.get("has_phone"):
        lines.append(f"Tél. : {e(str(r['phone']))}")
    if r.get("has_website"):
        lines.append(f"<a href='{e(str(r['website']))}' target='_blank' rel='noopener'>Site web</a>")
    if pd.notna(r.get("maps_url")):
        lines.append(f"<a href='{e(str(r['maps_url']))}' target='_blank' rel='noopener'>Voir sur Google Maps</a>")
    return ("<div style='font-family:system-ui,sans-serif;font-size:12px;min-width:210px;line-height:1.5'>"
            + header + "<br>".join(lines) + "</div>")


def _marker(r: pd.Series, color: str | None = None) -> folium.CircleMarker:
    c = color or score_color(r["score_bayes"])
    tip = f"{r['name']} — {r['concept']}"
    return folium.CircleMarker(
        location=[r["lat"], r["lng"]], radius=radius(int(r["reviews_count"])),
        color="#ffffff", weight=1, fill=True, fill_color=c, fill_opacity=0.9,
        popup=folium.Popup(popup_html(r), max_width=300), tooltip=html.escape(tip),
    )


def _legend(zones: pd.DataFrame) -> str:
    rows = "".join(
        f"<div><span style='color:{c};font-size:15px'>●</span> {lab}</div>" for _, c, lab in SCORE_LEVELS
    ) + f"<div><span style='color:{NO_SCORE[0]};font-size:15px'>●</span> {NO_SCORE[1]}</div>"
    zone_rows = "".join(
        f"<div style='display:flex;justify-content:space-between;gap:8px'><span>{html.escape(z)}</span>"
        f"<span style='color:#52514e'>{int(r.nb_etablissements)} · {_fmt(r.avis_typique)} avis/resto</span></div>"
        for z, r in zones.sort_values("nb_etablissements", ascending=False).iterrows()
    )
    return f"""
    <div style="position:fixed;bottom:56px;left:12px;z-index:1000;max-width:300px;
         background:rgba(252,252,251,.97);padding:10px 14px;border-radius:10px;
         box-shadow:0 2px 10px rgba(0,0,0,.18);font-family:system-ui,sans-serif;font-size:12px;color:#0b0b0b">
      <b>Note corrigée</b> (taille du point = nombre d'avis)
      {rows}
      <div><span style="display:inline-block;width:14px;height:14px;border-radius:50%;background:#52514e;
           vertical-align:-2px"></span> groupe de restaurants (zoomer pour les voir)</div>
      <details style="margin-top:6px"><summary style="cursor:pointer"><b>Pôles de restauration</b></summary>
        <div style="max-height:180px;overflow:auto;margin-top:4px">{zone_rows}</div>
      </details>
      <div style="color:#52514e;margin-top:6px;font-size:11px">
        Bouton « calques » en haut à droite : filtrer par type de restaurant.</div>
    </div>"""


def build_map(g: pd.DataFrame, zones: pd.DataFrame, path=config.PORTFOLIO_MAP) -> folium.Map:
    geo = g[g["is_geocoded"]]
    m = folium.Map(location=[config.NIAMEY_LAT, config.NIAMEY_LNG], zoom_start=13, tiles=None,
                   control_scale=True)
    Fullscreen().add_to(m)
    # Fonds sans clé d'API (les fonds CartoDB en exigent désormais une).
    folium.TileLayer("OpenStreetMap", name="Fond OpenStreetMap", show=True).add_to(m)
    folium.TileLayer(xyz.Esri.WorldGrayCanvas, name="Fond gris clair (Esri)", show=False).add_to(m)

    # 1. Tous les restaurants, couleur = note corrigée.
    fg_all = folium.FeatureGroup(name=f"Tous les restaurants ({len(geo)})", show=True)
    cluster = MarkerCluster(options={"disableClusteringAtZoom": 15}, icon_create_function=CLUSTER_ICON_JS)
    for _, r in geo.iterrows():
        _marker(r).add_to(cluster)
    cluster.add_to(fg_all)
    fg_all.add_to(m)

    # 2. Un calque par type de restaurant (masqués par défaut).
    for concept, sub in sorted(geo.groupby("concept"), key=lambda kv: -len(kv[1])):
        fg = folium.FeatureGroup(name=f"Type : {concept} ({len(sub)})", show=False)
        for _, r in sub.iterrows():
            _marker(r).add_to(fg)
        fg.add_to(m)

    # 3. Densité.
    fg_heat = folium.FeatureGroup(name="Densité de restaurants", show=False)
    HeatMap(geo[["lat", "lng"]].values.tolist(), radius=20, blur=18, min_opacity=0.3).add_to(fg_heat)
    fg_heat.add_to(m)

    # 4. Pôles.
    fg_poles = folium.FeatureGroup(name="Pôles de restauration", show=False)
    centers = geo[geo["pole_id"] >= 0].groupby("pole")[["lat", "lng"]].mean()
    nmax = zones["nb_etablissements"].max()
    for z, r in zones.iterrows():
        if z not in centers.index:
            continue
        folium.CircleMarker(
            location=[centers.loc[z, "lat"], centers.loc[z, "lng"]],
            radius=8 + 18 * (r["nb_etablissements"] / nmax) ** 0.5,
            color="#ffffff", weight=2, fill=True, fill_color=POLE_COLOR, fill_opacity=0.85,
            tooltip=html.escape(f"{z} : {int(r['nb_etablissements'])} restaurants, "
                                f"{_fmt(r['avis_typique'])} avis typiques par restaurant"),
        ).add_to(fg_poles)
    fg_poles.add_to(m)

    title = """
    <div style="position:fixed;top:10px;left:50%;transform:translateX(-50%);z-index:1000;
         background:rgba(252,252,251,.97);padding:6px 16px;border-radius:8px;max-width:80vw;
         box-shadow:0 2px 8px rgba(0,0,0,.18);font-family:system-ui,sans-serif;font-size:13px;text-align:center">
      <b>Restaurants de Niamey</b> · cliquez sur un point pour voir sa fiche
    </div>"""
    m.get_root().html.add_child(folium.Element(title))
    m.get_root().html.add_child(folium.Element(_legend(zones)))
    folium.LayerControl(collapsed=True, position="topright").add_to(m)

    path.parent.mkdir(parents=True, exist_ok=True)
    m.save(str(path))
    return m
