"""Fuse wound / symptom / geo logits with context: time since bite, circumstance, age, weight."""
from __future__ import annotations

import math
from typing import Any

import numpy as np

from ml.config import CLASSES, CLASS_TO_IDX

# Default modality weights (sum ~1)
W_WOUND = 0.42
W_SYMPTOM = 0.28
W_GEO = 0.18
W_CTX = 0.12


def _log(p: np.ndarray, eps: float = 1e-8) -> np.ndarray:
    return np.log(np.clip(p, eps, 1.0))


def context_prior_vector(
    time_since_bite_hours: float,
    bite_circumstance: str,
    age_years: float,
    weight_kg: float,
) -> np.ndarray:
    """
    Heuristic prior over CLASSES from epidemiology / timing.
    Not a substitute for clinician judgement.
    """
    v = np.ones(len(CLASSES), dtype=np.float64)
    t = max(0.0, float(time_since_bite_hours))
    circ = (bite_circumstance or "unknown").lower()

    # Early local envenomation signs often prominent in first hours (hemo/cyto)
    if t < 2.0:
        v[CLASS_TO_IDX["hemotoxic"]] *= 1.35
        v[CLASS_TO_IDX["cytotoxic"]] *= 1.25
    elif t > 6.0:
        v[CLASS_TO_IDX["neurotoxic"]] *= 1.25

    # Krait / nocturnal indoor pattern (from context KB)
    if "nocturnal" in circ or "sleeping" in circ or "indoor" in circ or "krait" in circ:
        v[CLASS_TO_IDX["neurotoxic"]] *= 1.55
    if "overnight" in circ or "emns" in circ:
        v[CLASS_TO_IDX["neurotoxic"]] *= 1.35

    # Pediatrics: keep mild — slight emphasis on neuro presentation variability
    if age_years < 12:
        v[CLASS_TO_IDX["neurotoxic"]] *= 1.08
        v[CLASS_TO_IDX["hemotoxic"]] *= 1.05

    # Very low body weight → antivenom dosing context only; tiny signal
    if weight_kg < 20:
        v[CLASS_TO_IDX["neurotoxic"]] *= 1.05

    v = np.maximum(v, 1e-8)
    return v / v.sum()


def fuse_multimodal(
    wound_prob: np.ndarray,
    symptom_prob: np.ndarray,
    geo_prob: np.ndarray,
    time_since_bite_hours: float = 3.0,
    bite_circumstance: str = "unknown",
    age_years: float = 35.0,
    weight_kg: float = 60.0,
    modality_weights: tuple[float, float, float, float] | None = None,
) -> tuple[np.ndarray, dict[str, Any]]:
    """
    Combine modality distributions + context into final venom-type distribution.
    Returns (final_prob, debug_dict).
    """
    w_w, w_s, w_g, w_c = modality_weights or (W_WOUND, W_SYMPTOM, W_GEO, W_CTX)
    ctx = context_prior_vector(time_since_bite_hours, bite_circumstance, age_years, weight_kg)

    lp = (
        w_w * _log(wound_prob.astype(np.float64))
        + w_s * _log(symptom_prob.astype(np.float64))
        + w_g * _log(geo_prob.astype(np.float64))
        + w_c * _log(ctx)
    )
    lp = lp - np.max(lp)
    out = np.exp(lp)
    out /= out.sum()
    debug = {
        "context_prior": ctx.tolist(),
        "modality_weights": {"wound": w_w, "symptom": w_s, "geo": w_g, "context": w_c},
    }
    return out, debug


def top_prediction(prob: np.ndarray) -> tuple[str, float]:
    i = int(np.argmax(prob))
    return CLASSES[i], float(prob[i])
