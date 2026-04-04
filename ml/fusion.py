"""Fuse wound / symptom / geo logits with context: time since bite, circumstance, age, weight."""
from __future__ import annotations

from typing import Any

import numpy as np

from ml.config import CLASSES, CLASS_TO_IDX

# Default modality weights (sum ~1) — used when wound model missing or wound read is uncertain.
# Symptom KB is checklist-derived and can be one-hot; keep it subordinate to geo when image is absent.
W_WOUND = 0.38
W_SYMPTOM = 0.22
W_GEO = 0.22
W_CTX = 0.18

# When wound ensemble is confident (max softmax ≥ uncertainty threshold), trust image in log fusion.
# Symptoms must not override a strong wound read (e.g. non_venomous vs one-hot hemotoxic checklist).
W_WOUND_CONFIDENT = 0.80
W_SYMPTOM_CONFIDENT = 0.07
W_GEO_CONFIDENT = 0.10
W_CTX_CONFIDENT = 0.03

# When wound model runs but is flagged uncertain: lean on symptoms + geo + context (still cap symptom vs geo).
W_WOUND_UNCERTAIN = 0.28
W_SYMPTOM_UNCERTAIN = 0.28
W_GEO_UNCERTAIN = 0.24
W_CTX_UNCERTAIN = 0.20

# Smoothing: symptom/geo floors before log fusion (one-hot KB would otherwise veto other modalities).
SYMPTOM_PROB_FLOOR = 0.10
GEO_PROB_FLOOR = 0.04

# When raw wound argmax disagrees with raw symptom argmax and wound max ≥ this, blend symptom toward uniform.
WOUND_SYMPTOM_CONFLICT_WOUND_MIN = 0.50
SYMPTOM_CONFLICT_UNIFORM_MIX = 0.55


def modality_weights_for_predict(
    *,
    wound_model_loaded: bool,
    wound_uncertain: bool,
) -> tuple[float, float, float, float]:
    """
    Log-space fusion weights (wound / symptom / geo / context).

    If no checkpoint is deployed, ``wound_prob`` is uniform and does not change the argmax;
    symptoms + geo + context still determine ``final_probability`` — see API ``fusion_warning``.
    When the wound model is loaded and not uncertain, wound gets a higher share so the trained
    image branch matches production behavior when ``wound_ensemble.pt`` is present.
    """
    if wound_model_loaded and not wound_uncertain:
        return (
            W_WOUND_CONFIDENT,
            W_SYMPTOM_CONFIDENT,
            W_GEO_CONFIDENT,
            W_CTX_CONFIDENT,
        )
    if wound_model_loaded and wound_uncertain:
        return (
            W_WOUND_UNCERTAIN,
            W_SYMPTOM_UNCERTAIN,
            W_GEO_UNCERTAIN,
            W_CTX_UNCERTAIN,
        )
    return (W_WOUND, W_SYMPTOM, W_GEO, W_CTX)


def modality_weights_reason(
    *,
    wound_model_loaded: bool,
    wound_uncertain: bool,
) -> str:
    if not wound_model_loaded:
        return "no_wound_model_uniform_image_prior"
    if wound_uncertain:
        return "uncertain_wound_more_symptom_geo"
    return "confident_wound_image_weighted"


def _log(p: np.ndarray, eps: float = 1e-8) -> np.ndarray:
    return np.log(np.clip(p, eps, 1.0))


def _soften_peaked_modality(p: np.ndarray, floor: float = 0.02) -> np.ndarray:
    """
    Symptom/geo KB outputs can be effectively one-hot. In log fusion, very small per-class
    probabilities dominate via log p and let a modality veto others. Apply a per-class floor and
    renormalize. Not applied to wound_prob — keep CNN softmax sharp when confident.
    """
    p = np.asarray(p, dtype=np.float64)
    p = np.maximum(p, floor)
    s = p.sum()
    if s <= 0:
        return np.ones_like(p) / len(p)
    return p / s


def _blend_toward_uniform(p: np.ndarray, mix: float) -> np.ndarray:
    """Convex blend with discrete uniform (mix in [0,1])."""
    p = np.asarray(p, dtype=np.float64)
    u = np.ones_like(p) / len(p)
    out = (1.0 - mix) * p + mix * u
    s = out.sum()
    if s <= 0:
        return u
    return out / s


def _symptom_prob_for_fusion(wound_prob: np.ndarray, symptom_prob: np.ndarray) -> tuple[np.ndarray, str]:
    """
    Soften peaked symptom KB, then if the wound branch is confident and disagrees with the raw
    symptom argmax, blend further toward uniform so checklist data cannot blind-side imaging.
    """
    p = _soften_peaked_modality(symptom_prob.astype(np.float64), floor=SYMPTOM_PROB_FLOOR)
    notes: list[str] = [f"floor={SYMPTOM_PROB_FLOOR}"]
    w_i = int(np.argmax(wound_prob))
    s_i = int(np.argmax(symptom_prob))
    w_max = float(np.max(wound_prob))
    if w_max >= WOUND_SYMPTOM_CONFLICT_WOUND_MIN and w_i != s_i:
        p = _blend_toward_uniform(p, SYMPTOM_CONFLICT_UNIFORM_MIX)
        notes.append(
            f"conflict(wound_argmax={CLASSES[w_i]}@{w_max:.2f} vs symptom_argmax={CLASSES[s_i]})→uniform_mix={SYMPTOM_CONFLICT_UNIFORM_MIX}"
        )
    return p, "; ".join(notes)


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

    sym_adj, sym_note = _symptom_prob_for_fusion(wound_prob.astype(np.float64), symptom_prob.astype(np.float64))
    geo_adj = _soften_peaked_modality(geo_prob.astype(np.float64), floor=GEO_PROB_FLOOR)

    lp = (
        w_w * _log(wound_prob.astype(np.float64))
        + w_s * _log(sym_adj)
        + w_g * _log(geo_adj)
        + w_c * _log(ctx)
    )
    lp = lp - np.max(lp)
    out = np.exp(lp)
    out /= out.sum()
    debug = {
        "context_prior": ctx.tolist(),
        "modality_weights": {"wound": w_w, "symptom": w_s, "geo": w_g, "context": w_c},
        "symptom_probability_adjusted": sym_adj.tolist(),
        "geo_probability_adjusted": geo_adj.tolist(),
        "fusion_note": (
            "symptom: soften + optional conflict blend vs confident wound; geo: floor; "
            "so one-hot KB cannot override a strong wound read. "
            + sym_note
        ),
    }
    return out, debug


def top_prediction(prob: np.ndarray) -> tuple[str, float]:
    i = int(np.argmax(prob))
    return CLASSES[i], float(prob[i])
