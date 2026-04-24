"""Score venom-type priors from selected clinical symptoms (XGBoost + catalog utilities)."""
from __future__ import annotations

import json
import pickle
import platform
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.preprocessing import MultiLabelBinarizer

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


def _xgb_runtime_allowed() -> bool:
    """
    Guard known unstable runtime combo:
    - macOS + Python 3.13 + OpenMP-backed XGBoost can segfault in libomp.
    Allow explicit override with SNAKEBITE_FORCE_XGB=1.
    """
    import os

    if os.environ.get("SNAKEBITE_FORCE_XGB", "").strip() == "1":
        return True
    return not (platform.system() == "Darwin" and sys.version_info >= (3, 13))


def _get_xgb_classifier() -> Any | None:
    """Lazy import XGBoost to avoid loading libomp at module import time."""
    if not _xgb_runtime_allowed():
        return None
    try:
        from xgboost import XGBClassifier
    except Exception:
        return None
    return XGBClassifier


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
    """Rows: symptoms, cols: CLASSES aggregate weights (used for ranking/explainability)."""
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


def _train_xgb_symptom_model(df: pd.DataFrame, symptoms: list[str]) -> Any | None:
    """Train multiclass XGBoost on symptom rows (single-symptom samples with row weights)."""
    XGBClassifier = _get_xgb_classifier()
    if XGBClassifier is None or not symptoms:
        return None
    rows = []
    labels = []
    weights = []
    for _, r in df.iterrows():
        vt = VENOM_MAP.get(str(r["venom_type"]).strip().lower())
        sym = str(r.get("symptom") or "").strip()
        if vt is None or not sym or sym not in symptoms:
            continue
        rows.append([sym])
        labels.append(CLASS_TO_IDX[vt])
        try:
            w = float(r.get("weight") or 1.0)
        except Exception:
            w = 1.0
        weights.append(max(1e-6, w))
    if not rows:
        return None
    mlb = MultiLabelBinarizer(classes=symptoms)
    X = mlb.fit_transform(rows).astype(np.float32)
    y = np.asarray(labels, dtype=np.int64)
    sw = np.asarray(weights, dtype=np.float32)
    model = XGBClassifier(
        objective="multi:softprob",
        num_class=len(CLASSES),
        n_estimators=180,
        max_depth=4,
        learning_rate=0.08,
        subsample=0.9,
        colsample_bytree=0.9,
        reg_lambda=1.0,
        random_state=42,
        tree_method="hist",
        eval_metric="mlogloss",
        n_jobs=1,
    )
    model.fit(X, y, sample_weight=sw)
    return model


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

    xgb_path = MODELS / "symptom_xgb.pkl"
    if _xgb_runtime_allowed() and xgb_path.is_file():
        try:
            blob = pickle.loads(xgb_path.read_bytes())
            model = blob.get("model")
            vocab = blob.get("symptoms") or []
            if model is not None and vocab and all(s in set(vocab) for s in selected):
                mlb = MultiLabelBinarizer(classes=vocab)
                X = mlb.fit_transform([selected]).astype(np.float32)
                proba = np.asarray(model.predict_proba(X)[0], dtype=np.float64)
                proba = np.maximum(proba, 1e-8)
                return proba / proba.sum()
        except Exception:
            pass

    # Fallback catalog scoring for missing model or out-of-vocabulary symptoms.
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
        "model_type": "xgboost_symptom_classifier",
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    xgb = _train_xgb_symptom_model(df, symptoms)
    if xgb is not None:
        xgb_payload = {"symptoms": symptoms, "model": xgb}
        (MODELS / "symptom_xgb.pkl").write_bytes(pickle.dumps(xgb_payload))

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
