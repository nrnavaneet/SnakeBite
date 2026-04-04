"""Score venom-type priors from selected clinical symptoms (knowledge base CSV)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ml.config import CLASSES, CLASS_TO_IDX, MODELS, SYMPTOM_CSV
from ml.symptom_plain_labels import attach_plain_labels

# Map dataset venom types to 5-class head
VENOM_MAP = {
    "cytotoxic": "cytotoxic",
    "hemotoxic": "hemotoxic",
    "neurotoxic": "neurotoxic",
    "non_venomous": "non_venomous",
    "myotoxic": "hemotoxic",  # coarse: muscle involvement → hemotoxic lean
    "unknown": None,
}


def load_symptom_table() -> pd.DataFrame:
    """Symptom rows from KB CSV. If the file is absent (e.g. *.csv gitignored on deploy), return empty."""
    if not SYMPTOM_CSV.is_file():
        return pd.DataFrame(
            columns=[
                "feature_type",
                "venom_type",
                "symptom",
                "severity",
                "importance_rank",
                "weight_tier",
                "weight",
                "possible_snakes",
                "family",
                "onset_min_hours",
                "onset_max_hours",
                "local_signs_absent_or_minimal",
                "source",
            ]
        )
    df = pd.read_csv(SYMPTOM_CSV)
    return df[df["feature_type"].astype(str).str.lower() == "symptom"].copy()


def build_symptom_catalog(df: pd.DataFrame) -> tuple[list[str], np.ndarray]:
    """Rows: symptoms, cols: CLASSES weights (sum of CSV weights per class)."""
    rows: list[tuple[str, np.ndarray]] = []
    for sym, g in df.groupby("symptom"):
        vec = np.zeros(len(CLASSES), dtype=np.float64)
        for _, r in g.iterrows():
            vt = VENOM_MAP.get(str(r["venom_type"]).strip().lower())
            if vt is None:
                continue
            w = float(r["weight"])
            vec[CLASS_TO_IDX[vt]] += w
        if vec.sum() <= 0:
            continue
        rows.append((str(sym).strip(), vec))
    rows.sort(key=lambda x: x[0])
    symptoms = [r[0] for r in rows]
    if not rows:
        mat = np.zeros((0, len(CLASSES)), dtype=np.float64)
    else:
        mat = np.stack([r[1] for r in rows], axis=0)
    return symptoms, mat


def rank_selected_symptoms(
    selected: list[str],
    symptoms: list[str],
    mat: np.ndarray,
    sym_p: np.ndarray,
    *,
    label_by_value: dict[str, dict[str, str]] | None = None,
) -> list[dict[str, Any]]:
    """
    Sort chosen symptoms by salience: overlap between each symptom's venom-weight row
    (normalized) and the combined ``sym_p`` distribution (higher = more central to the blend).
    """
    if not selected:
        return []
    sym_p = np.asarray(sym_p, dtype=np.float64)
    sym_p = sym_p / (sym_p.sum() + 1e-12)
    out: list[dict[str, Any]] = []
    for s in selected:
        if s not in symptoms:
            continue
        i = symptoms.index(s)
        row = mat[i].astype(np.float64)
        rs = float(row.sum())
        if rs <= 0:
            salience = 0.0
        else:
            rn = row / rs
            salience = float(np.dot(rn, sym_p))
        item: dict[str, Any] = {
            "value": s,
            "salience": round(salience, 6),
        }
        if label_by_value and s in label_by_value:
            item["label"] = label_by_value[s].get("label", s)
            item["category"] = label_by_value[s].get("category", "")
        out.append(item)
    out.sort(key=lambda x: -float(x["salience"]))
    return out


def score_symptoms(selected: list[str], symptoms: list[str], mat: np.ndarray) -> np.ndarray:
    """Return normalized probability vector over CLASSES."""
    if not selected:
        return np.ones(len(CLASSES), dtype=np.float64) / len(CLASSES)
    idx = [symptoms.index(s) for s in selected if s in symptoms]
    if not idx:
        return np.ones(len(CLASSES), dtype=np.float64) / len(CLASSES)
    v = mat[idx].sum(axis=0)
    v = np.maximum(v, 1e-8)
    return v / v.sum()


def save_catalog(path: Path | None = None) -> Path:
    MODELS.mkdir(parents=True, exist_ok=True)
    path = path or MODELS / "symptom_catalog.json"
    df = load_symptom_table()
    symptoms, mat = build_symptom_catalog(df)
    items = attach_plain_labels(symptoms)
    payload = {
        "classes": list(CLASSES),
        "symptoms": symptoms,
        "weight_rows": mat.tolist(),
        "items": items,
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def load_catalog(
    path: Path | None = None,
) -> tuple[list[str], np.ndarray, list[dict[str, str]]]:
    path = path or MODELS / "symptom_catalog.json"
    if not path.is_file():
        save_catalog(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    symptoms: list[str] = data["symptoms"]
    mat = np.array(data["weight_rows"], dtype=np.float64)
    items: list[dict[str, str]] = data.get("items") or attach_plain_labels(symptoms)
    return symptoms, mat, items
