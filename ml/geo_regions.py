"""Build and query venom-type priors by (country, state) from snake_geo_clean.csv."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ml.config import CLASS_TO_IDX, CLASSES, GEO_CSV, MODELS
from ml.geo_normalize import apply_canonical_state_column, resolve_canonical_state_from_region_keys

GEO_CLASSES = {"cytotoxic", "hemotoxic", "neurotoxic", "non_venomous"}


def _map_vt(v: object) -> str | None:
    s = str(v).strip().lower()
    return s if s in GEO_CLASSES else None


def _vec_to_prob(c4: np.ndarray) -> np.ndarray:
    """4 venom counts → 5-class prob with small not_snakebite mass."""
    v = np.zeros(len(CLASSES), dtype=np.float64)
    v[:4] = np.maximum(c4.astype(np.float64), 0.0)
    v[4] = 0.05 * (v[:4].sum() + 1.0)
    v = np.maximum(v, 1e-8)
    return v / v.sum()


def build_geo_region_json(out_path: Path | None = None) -> Path:
    """Aggregate full CSV → models/geo_region_prior.json."""
    out_path = out_path or MODELS / "geo_region_prior.json"
    MODELS.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(GEO_CSV, usecols=["country", "state", "venom_type"], low_memory=False)
    df["country"] = df["country"].astype(str).str.strip()
    df["state"] = df["state"].fillna("").astype(str).str.strip()
    apply_canonical_state_column(df)
    df["cls"] = df["venom_type"].map(_map_vt)
    df = df.dropna(subset=["cls"])
    df["ci"] = df["cls"].map(lambda x: CLASS_TO_IDX[str(x)])

    # (country, state) -> counts per class index 0..3
    pair = (
        df.groupby(["country", "state", "ci"])
        .size()
        .unstack(fill_value=0)
        .rename_axis(index=["country", "state"])
    )
    # Ensure columns 0..3
    for k in range(4):
        if k not in pair.columns:
            pair[k] = 0
    pair = pair[[0, 1, 2, 3]]

    region: dict[str, list[float]] = {}
    country_tot: dict[str, np.ndarray] = {}
    glob = np.zeros(4, dtype=np.float64)

    for (c, s), row in pair.iterrows():
        c4 = row.values.astype(np.float64)
        glob += c4
        country_tot[c] = country_tot.get(c, np.zeros(4)) + c4
        key = _key(c, s)
        region[key] = _vec_to_prob(c4).tolist()

    country_default: dict[str, list[float]] = {}
    for c, c4 in country_tot.items():
        country_default[c] = _vec_to_prob(c4).tolist()

    default = _vec_to_prob(glob).tolist()

    # States per country for UI
    states_by_country: dict[str, list[str]] = {}
    for (c, s) in pair.index.unique():
        if not s:
            continue
        states_by_country.setdefault(c, []).append(s)
    for c in states_by_country:
        states_by_country[c] = sorted(set(states_by_country[c]))

    countries_sorted = sorted(country_tot.keys())

    payload: dict[str, Any] = {
        "classes": list(CLASSES),
        "countries": countries_sorted,
        "states_by_country": states_by_country,
        "region_prior": region,
        "country_default": country_default,
        "global_default": default,
    }
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return out_path


def _key(country: str, state: str) -> str:
    return f"{country.strip()}|{state.strip()}"


def load_geo_region_payload(path: Path | None = None) -> dict[str, Any]:
    path = path or MODELS / "geo_region_prior.json"
    if not path.is_file():
        build_geo_region_json(path)
    return json.loads(path.read_text(encoding="utf-8"))


def geo_prior_from_region(country: str, state: str, payload: dict[str, Any] | None = None) -> np.ndarray:
    """Return 5-class distribution; fallback country → global."""
    if payload is None:
        payload = load_geo_region_payload()
    c = (country or "").strip()
    s = (state or "").strip()

    region_prior = payload.get("region_prior") or {}
    country_default = payload.get("country_default") or {}
    default = np.array(payload.get("global_default") or [0.2] * len(CLASSES), dtype=np.float64)

    if c and s:
        s = resolve_canonical_state_from_region_keys(c, s, region_prior.keys())
        k = _key(c, s)
        if k in region_prior:
            return np.array(region_prior[k], dtype=np.float64)

    if c and c in country_default:
        return np.array(country_default[c], dtype=np.float64)

    return default / default.sum()
