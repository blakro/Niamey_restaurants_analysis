"""Étape 4 du README — Positionner les restaurants sur la carte et repérer les pôles."""
from __future__ import annotations

import numpy as np
import pandas as pd
from openlocationcode import openlocationcode as olc
from sklearn.cluster import DBSCAN
from sklearn.neighbors import BallTree

from . import config
from .cleaning import PLUS_CODE_RE

EARTH_RADIUS_M = 6_371_000


# ── Géocodage ────────────────────────────────────────────────────────────────
def decode_plus_code(street: object, ref_lat: float = config.NIAMEY_LAT,
                     ref_lng: float = config.NIAMEY_LNG) -> tuple[float, float]:
    """« G476+RX4, Bd ... » → (lat, lng). Les codes courts sont complétés
    à partir du centre de Niamey. Renvoie (nan, nan) si aucun Plus Code."""
    if street is None or (isinstance(street, float) and np.isnan(street)) or pd.isna(street):
        return np.nan, np.nan
    match = PLUS_CODE_RE.search(str(street).upper())
    if not match:
        return np.nan, np.nan
    code = match.group(0)
    try:
        if olc.isFull(code):
            area = olc.decode(code)
        elif olc.isShort(code):
            area = olc.decode(olc.recoverNearest(code, ref_lat, ref_lng))
        else:
            return np.nan, np.nan
    except Exception:  # code invalide
        return np.nan, np.nan
    return round(area.latitudeCenter, 6), round(area.longitudeCenter, 6)


def geocode(df: pd.DataFrame) -> pd.DataFrame:
    """Ajoute lat / lng (NaN si la position est inconnue ou hors de Niamey)."""
    out = df.copy()
    coords = out["street"].map(decode_plus_code)
    out["lat"] = [c[0] for c in coords]
    out["lng"] = [c[1] for c in coords]
    b = config.BBOX
    inside = out["lat"].between(b["lat_min"], b["lat_max"]) & out["lng"].between(b["lng_min"], b["lng_max"])
    out.loc[~inside, ["lat", "lng"]] = np.nan
    out["is_geocoded"] = out["lat"].notna()
    return out


# ── Quartiers ────────────────────────────────────────────────────────────────
def load_quartiers(path=config.QUARTIERS_CSV) -> pd.DataFrame:
    """Référentiel (approximatif) des quartiers : nom, arrondissement, centre."""
    return pd.read_csv(path)


def _to_radians(lat, lng) -> np.ndarray:
    return np.radians(np.column_stack([lat, lng]))


def assign_quartier(df: pd.DataFrame, quartiers: pd.DataFrame) -> pd.DataFrame:
    """Rattache chaque restaurant géolocalisé au quartier de référence le plus proche."""
    out = df.copy()
    out["quartier"] = pd.NA
    out["arrondissement"] = pd.NA
    out["quartier_dist_m"] = np.nan
    geo = out["is_geocoded"]
    if not geo.any():
        return out
    tree = BallTree(_to_radians(quartiers["lat"], quartiers["lng"]), metric="haversine")
    dist, idx = tree.query(_to_radians(out.loc[geo, "lat"], out.loc[geo, "lng"]), k=1)
    idx = idx[:, 0]
    out.loc[geo, "quartier"] = quartiers["quartier"].values[idx]
    out.loc[geo, "arrondissement"] = quartiers["arrondissement"].values[idx]
    out.loc[geo, "quartier_dist_m"] = (dist[:, 0] * EARTH_RADIUS_M).round(0)
    out["is_periphery"] = out["quartier_dist_m"] > config.PERIPHERY_DIST_M
    return out


# ── Pôles de restauration (DBSCAN) ───────────────────────────────────────────
def find_poles(df: pd.DataFrame, eps_m: float = config.DBSCAN_EPS_M,
               min_samples: int = config.DBSCAN_MIN_SAMPLES) -> pd.Series:
    """Regroupe les restaurants proches en « pôles ».

    Renvoie un identifiant de pôle par restaurant : ≥ 0 = pôle,
    -1 = restaurant isolé, -2 = position inconnue.
    """
    labels = pd.Series(-2, index=df.index, dtype=int)
    geo = df["is_geocoded"]
    if geo.sum() < min_samples:
        return labels
    X = _to_radians(df.loc[geo, "lat"], df.loc[geo, "lng"])
    db = DBSCAN(eps=eps_m / EARTH_RADIUS_M, min_samples=min_samples,
                metric="haversine", algorithm="ball_tree").fit(X)
    labels.loc[geo] = db.labels_
    return labels


def name_poles(df: pd.DataFrame) -> dict[int, str]:
    """Nomme chaque pôle d'après le(s) quartier(s) le(s) plus représenté(s).

    Si le premier quartier regroupe moins de la moitié des restaurants du pôle,
    on cite les deux premiers (ex. « Château 1 · Issa Béri »).
    """
    names: dict[int, str] = {}
    for pid, grp in df[df["pole_id"] >= 0].groupby("pole_id"):
        top = grp["quartier"].value_counts()
        q = top.index[0]
        label = f"{q}"
        if top.iloc[0] / len(grp) < 0.5 and len(top) > 1:
            label = f"{q} · {top.index[1]}"
        if grp["is_periphery"].mean() > 0.5:
            label = f"Périphérie (vers {q})"
        names[int(pid)] = label
    # Désambiguïsation : deux pôles sur le même quartier → on précise N/S/E/O.
    by_label: dict[str, list[int]] = {}
    for pid, label in names.items():
        by_label.setdefault(label, []).append(pid)
    for label, pids in by_label.items():
        if len(pids) < 2:
            continue
        centers = df[df["pole_id"].isin(pids)].groupby("pole_id")[["lat", "lng"]].mean()
        clat, clng = centers["lat"].mean(), centers["lng"].mean()
        for pid in pids:
            dlat, dlng = centers.loc[pid, "lat"] - clat, centers.loc[pid, "lng"] - clng
            if abs(dlat) >= abs(dlng):
                suffix = "nord" if dlat > 0 else "sud"
            else:
                suffix = "est" if dlng > 0 else "ouest"
            names[pid] = f"{label} — {suffix}"
    return names


def add_poles(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["pole_id"] = find_poles(out)
    names = name_poles(out)
    out["pole"] = out["pole_id"].map(names)
    out.loc[out["pole_id"] == -1, "pole"] = "Restaurant isolé"
    out.loc[out["pole_id"] == -2, "pole"] = "Position inconnue"
    return out


def run(df_clean: pd.DataFrame) -> pd.DataFrame:
    """Géocodage + quartiers + pôles, en une fois."""
    df = geocode(df_clean)
    df = assign_quartier(df, load_quartiers())
    return add_poles(df)
