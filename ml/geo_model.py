"""Geographic venom-type prior from GBIF-style occurrences (India subset)."""
from __future__ import annotations

import json
import pickle
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.neighbors import BallTree

from ml.config import CLASSES, CLASS_TO_IDX, GEO_CSV, MODELS

GEO_CLASSES = {"cytotoxic", "hemotoxic", "neurotoxic", "non_venomous"}


def _map_geo_label(v: str) -> str | None:
    s = str(v).strip().lower()
    if s in GEO_CLASSES:
        return s
    return None


def build_geo_index(
    out_path: Path | None = None,
    max_rows: int | None = None,
) -> Path:
    """Filter India rows, build BallTree on lat/lon. Saves pickle."""
    out_path = out_path or MODELS / "geo_index.pkl"
    MODELS.mkdir(parents=True, exist_ok=True)

    parts: list[pd.DataFrame] = []
    usecols = ["latitude", "longitude", "country", "venom_type"]
    for chunk in pd.read_csv(GEO_CSV, chunksize=400_000, usecols=usecols, low_memory=False):
        m = chunk["country"].astype(str).str.contains("India", case=False, na=False)
        sub = chunk.loc[m, ["latitude", "longitude", "venom_type"]].dropna()
        parts.append(sub)
        if max_rows and sum(len(p) for p in parts) >= max_rows:
            break
    if not parts:
        raise RuntimeError("No India rows found in geo CSV.")
    df = pd.concat(parts, ignore_index=True)
    if max_rows:
        df = df.head(max_rows)

    labs: list[int] = []
    coords: list[tuple[float, float]] = []
    for _, row in df.iterrows():
        m = _map_geo_label(row["venom_type"])
        if m is None:
            continue
        coords.append((float(row["latitude"]), float(row["longitude"])))
        labs.append(CLASS_TO_IDX[m])

    X = np.radians(np.array(coords, dtype=np.float64))
    y = np.array(labs, dtype=np.int64)
    tree = BallTree(X, metric="haversine")

    payload = {"tree": tree, "y": y, "classes": list(CLASSES)}
    out_path.write_bytes(pickle.dumps(payload))
    meta = {"n_points": len(y), "path": str(out_path)}
    (MODELS / "geo_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return out_path


def load_geo_index(path: Path | None = None) -> dict:
    path = path or MODELS / "geo_index.pkl"
    if not path.is_file():
        build_geo_index(path)
    return pickle.loads(path.read_bytes())


def geo_prior(lat: float, lon: float, radius_km: float = 120.0) -> np.ndarray:
    """Softmax-ish distribution over CLASSES from neighbors within radius."""
    data = load_geo_index()
    tree: BallTree = data["tree"]
    y: np.ndarray = data["y"]
    rad = radius_km / 6371.0  # earth radius km
    q = np.radians([[lat, lon]])
    idx = tree.query_radius(q, r=rad, count_only=False)[0]
    counts = np.zeros(len(CLASSES), dtype=np.float64)
    counts[4] = 0.05  # tiny prior for not_snakebite (geo signal weak)
    if len(idx) == 0:
        counts[:4] = 0.25
        return counts / counts.sum()
    for j in idx:
        counts[y[j]] += 1.0
    counts = np.maximum(counts, 1e-6)
    return counts / counts.sum()
