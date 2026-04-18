"""Per-region snake priors from geo CSV: common/generic names for display, scientific key internally."""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ml.config import CLASS_TO_IDX, CLASSES, GEO_CSV, MODELS
from ml.geo_normalize import apply_canonical_state_column, resolve_canonical_state_from_region_keys
from ml.geo_regions import _key as region_key
from ml.symptom_engine import load_symptom_table

GEO_CLASSES = {"cytotoxic", "hemotoxic", "neurotoxic", "non_venomous"}
TOP_SPECIES_PER_BUCKET = 40
VENOM_KEYS = tuple(CLASSES[:4])


def _map_vt(v: object) -> str | None:
    s = str(v).strip().lower()
    return s if s in GEO_CLASSES else None


def clean_binomial(raw: object) -> str | None:
    """Normalize scientific_name to 'Genus species' when possible."""
    s = str(raw).strip().strip('"').strip()
    if not s:
        return None
    s = re.sub(r",\s*\d{4}.*$", "", s)
    parts = re.split(r"[\s,]+", s)
    parts = [p for p in parts if p and not re.match(r"^\d{4}$", p)]
    if len(parts) < 2:
        return None
    genus = re.sub(r"[^A-Za-z]", "", parts[0])
    epithet = re.sub(r"[^A-Za-z]", "", parts[1])
    if not genus or not epithet:
        return None
    if len(genus) < 2 or len(epithet) < 2:
        return None
    return f"{genus[0].upper()}{genus[1:].lower()} {epithet.lower()}"


def _species_key_row(r: pd.Series) -> str | None:
    sk = clean_binomial(r.get("scientific_name"))
    if sk:
        return sk
    g = str(r.get("generic_name") or "").strip()
    return g if g else None


def build_geo_species_json(out_path: Path | None = None) -> Path:
    """Aggregate snake_geo_clean → models/geo_species_table.json (human-readable names)."""
    out_path = out_path or MODELS / "geo_species_table.json"
    MODELS.mkdir(parents=True, exist_ok=True)

    header = pd.read_csv(GEO_CSV, nrows=0).columns.tolist()
    if "scientific_name" in header:
        want = ["scientific_name", "generic_name", "common_name", "country", "state", "venom_type"]
        usecols = [c for c in want if c in header]
        df = pd.read_csv(GEO_CSV, usecols=usecols, low_memory=False)
        if "generic_name" not in df.columns:
            df["generic_name"] = ""
        if "common_name" not in df.columns:
            df["common_name"] = ""
    else:
        df = pd.read_csv(GEO_CSV, usecols=["species", "country", "state", "venom_type"], low_memory=False)
        df = df.rename(columns={"species": "scientific_name"})
        df["generic_name"] = ""
        df["common_name"] = ""

    df["country"] = df["country"].astype(str).str.strip()
    df["state"] = df["state"].fillna("").astype(str).str.strip()
    apply_canonical_state_column(df)
    df["cls"] = df["venom_type"].map(_map_vt)
    df = df.dropna(subset=["cls"])

    df["species_key"] = df.apply(_species_key_row, axis=1)
    df = df.dropna(subset=["species_key"])

    cn = df["common_name"].fillna("").astype(str).str.strip()
    gn = df["generic_name"].fillna("").astype(str).str.strip()
    df["display_name"] = np.where(cn != "", cn, np.where(gn != "", gn, df["species_key"]))

    df["ci"] = df["cls"].map(lambda x: CLASS_TO_IDX[str(x)])

    def table_for_frame(frame: pd.DataFrame) -> dict[str, list[dict[str, Any]]]:
        out: dict[str, list[dict[str, Any]]] = {vk: [] for vk in VENOM_KEYS}
        display_map = frame.groupby("species_key", observed=True)["display_name"].first()

        for ci, vk in enumerate(VENOM_KEYS):
            sub = frame[frame["ci"] == ci]
            if sub.empty:
                continue
            counts = sub.groupby("species_key", observed=True).size().sort_values(ascending=False)
            counts = counts.head(TOP_SPECIES_PER_BUCKET)
            tot = float(counts.sum()) or 1.0
            ranked: list[dict[str, Any]] = []
            for sp_key, n in counts.items():
                disp = str(display_map.loc[sp_key]) if sp_key in display_map.index else str(sp_key)
                ranked.append(
                    {
                        "scientific": str(sp_key),
                        "name": disp,
                        "p": float(n) / tot,
                    }
                )
            out[vk] = ranked
        return out

    by_region: dict[str, dict[str, Any]] = {}
    for (c, s), part in df.groupby(["country", "state"], observed=True):
        if not s:
            continue
        by_region[region_key(c, s)] = table_for_frame(part)

    by_country: dict[str, dict[str, Any]] = {}
    for c, part in df.groupby("country", observed=True):
        by_country[str(c)] = table_for_frame(part)

    glob = table_for_frame(df)

    payload = {
        "classes_venom": list(VENOM_KEYS),
        "schema_version": 2,
        "note": "name = common or generic label for display; scientific = grouping key from CSV.",
        "by_region": by_region,
        "by_country": by_country,
        "global": glob,
    }
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return out_path


def load_geo_species_payload(path: Path | None = None) -> dict[str, Any]:
    path = path or MODELS / "geo_species_table.json"
    if not path.is_file():
        build_geo_species_json(path)
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _symptom_hints_blob() -> dict[str, str]:
    df = load_symptom_table()
    out: dict[str, str] = {}
    for sym, g in df.groupby("symptom"):
        blobs: list[str] = []
        for x in g["possible_snakes"].fillna("").astype(str):
            blobs.append(x.lower())
        out[str(sym).strip()] = " ".join(blobs)
    return out


def _parse_species_row(row: Any) -> tuple[str, float, str]:
    """(scientific_key, p, display_name)."""
    if isinstance(row, dict):
        sci = str(row.get("scientific") or row.get("scientific_name") or "").strip()
        p = float(row.get("p") or row.get("probability") or 0.0)
        name = str(row.get("name") or sci).strip() or sci
        return sci, p, name
    if isinstance(row, (list, tuple)) and len(row) >= 2:
        return str(row[0]), float(row[1]), str(row[0])
    return "", 0.0, ""


def symptom_species_boost(
    selected: list[str],
    species_keys: list[str],
    display_by_key: dict[str, str],
) -> dict[str, float]:
    """Boost using KB text vs scientific + common/generic labels."""
    hints = _symptom_hints_blob()
    blob = " ".join(hints.get(s, "") for s in selected if s in hints)
    if not blob.strip():
        return {sp: 1.0 for sp in species_keys}

    boost: dict[str, float] = {}
    for sp in species_keys:
        disp = display_by_key.get(sp, "")
        hay = f"{sp} {disp}".lower()
        score = 0.0
        parts = sp.lower().split()
        genus = parts[0] if parts else ""
        epithet = parts[1] if len(parts) > 1 else ""
        if len(genus) >= 3 and genus in blob:
            score += 2.0
        if len(epithet) >= 4 and epithet in blob:
            score += 1.5
        for token in hay.split():
            if len(token) >= 4 and token in blob:
                score += 0.4
        for kw in (
            "krait",
            "cobra",
            "viper",
            "mamba",
            "python",
            "russell",
            "saw-scaled",
            "adder",
            "rattlesnake",
            "pit viper",
        ):
            if kw in blob and kw in hay:
                score += 0.8
        boost[sp] = 1.0 + min(4.0, score) * 0.35
    return boost


def _get_venom_table(
    country: str,
    state: str,
    payload: dict[str, Any],
) -> dict[str, list[Any]]:
    c = (country or "").strip()
    s = (state or "").strip()
    by_region = payload.get("by_region") or {}
    by_country = payload.get("by_country") or {}
    glob = payload.get("global") or {}

    if c and s:
        s = resolve_canonical_state_from_region_keys(c, s, by_region.keys())
        k = region_key(c, s)
        if k in by_region:
            return by_region[k]
    if c and c in by_country:
        return by_country[c]
    return glob


def rank_snake_species(
    venom_probs: np.ndarray,
    country: str,
    state: str,
    symptoms: list[str],
    species_payload: dict[str, Any] | None = None,
    top_k: int = 12,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    payload = species_payload or load_geo_species_payload()
    table = _get_venom_table(country, state, payload)

    species_set: set[str] = set()
    display_by_key: dict[str, str] = {}
    for vk in VENOM_KEYS:
        for row in table.get(vk) or []:
            sci, _, name = _parse_species_row(row)
            if sci:
                species_set.add(sci)
                display_by_key[sci] = name

    if not species_set:
        return [], {"source": "empty", "region_table": "none"}

    p = np.asarray(venom_probs, dtype=np.float64).ravel()
    if p.size != len(CLASSES):
        p = np.ones(len(CLASSES)) / len(CLASSES)
    p = np.maximum(p, 0.0)
    p = p / p.sum()

    score_geo: dict[str, float] = {sp: 0.0 for sp in species_set}
    for i, vk in enumerate(VENOM_KEYS):
        wv = float(p[i])
        if wv < 1e-12:
            continue
        rows = table.get(vk) or []
        for row in rows:
            sci, pv, _ = _parse_species_row(row)
            if sci in score_geo:
                score_geo[sci] += wv * pv

    boost = symptom_species_boost(symptoms, list(score_geo.keys()), display_by_key)
    ranked: list[tuple[str, float, float, float, str]] = []
    for sp, g in score_geo.items():
        b = boost.get(sp, 1.0)
        final = g * b
        ranked.append((sp, final, g, b, display_by_key.get(sp, sp)))

    ranked.sort(key=lambda x: -x[1])
    out = [
        {
            "name": disp,
            "scientific_name": sp,
            "score": round(s, 6),
            "geo_mixture": round(g, 6),
            "symptom_boost": round(b, 4),
        }
        for sp, s, g, b, disp in ranked[:top_k]
    ]
    dbg = {
        "region_resolution": (
            "exact" if state and region_key(country, state) in (payload.get("by_region") or {}) else "country_or_global"
        ),
        "venom_weights_applied": {VENOM_KEYS[i]: round(float(p[i]), 4) for i in range(4)},
    }
    return out, dbg
