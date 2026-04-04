"""Sanity checks: fusion outputs valid distributions (requires wound checkpoint)."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]


def _has_any_wound_checkpoint() -> bool:
    from ml.infer import pick_wound_checkpoint

    return pick_wound_checkpoint(ROOT) is not None


def test_modality_weights_sum_to_one():
    from ml.fusion import modality_weights_for_predict

    for loaded, uncertain in (
        (True, False),
        (True, True),
        (False, True),
    ):
        t = modality_weights_for_predict(wound_model_loaded=loaded, wound_uncertain=uncertain)
        assert len(t) == 4
        assert abs(sum(t) - 1.0) < 1e-6


def test_fuse_multimodal_sums():
    from ml.config import CLASSES
    from ml.fusion import fuse_multimodal

    w = np.ones(len(CLASSES)) / len(CLASSES)
    s = np.ones(len(CLASSES)) / len(CLASSES)
    g = np.ones(len(CLASSES)) / len(CLASSES)
    final, dbg = fuse_multimodal(
        w,
        s,
        g,
        time_since_bite_hours=2.0,
        bite_circumstance="nocturnal_indoor_sleeping",
        age_years=30.0,
        weight_kg=60.0,
    )
    assert len(final) == len(CLASSES)
    assert abs(final.sum() - 1.0) < 1e-5
    assert "context_prior" in dbg


def test_confident_wound_wins_over_one_hot_symptom_when_they_disagree():
    """Peaked symptom KB must not override a confident non_venomous wound read."""
    from ml.config import CLASSES
    from ml.fusion import fuse_multimodal, modality_weights_for_predict, top_prediction

    wound = np.array(
        [0.01762, 0.02591, 0.01770, 0.91350, 0.02526],
        dtype=np.float64,
    )
    symptom = np.array([1e-8, 1.0 - 1e-7, 1e-8, 1e-8, 1e-8], dtype=np.float64)
    geo = np.array([1e-12, 0.369, 0.297, 0.286, 0.048], dtype=np.float64)

    mw = modality_weights_for_predict(wound_model_loaded=True, wound_uncertain=False)
    final, dbg = fuse_multimodal(wound, symptom, geo, modality_weights=mw)
    top, conf = top_prediction(final)
    assert top == "non_venomous"
    assert conf > 0.5
    assert "conflict" in dbg.get("fusion_note", "")


@pytest.mark.skipif(
    not _has_any_wound_checkpoint(),
    reason="no wound checkpoint (wound_ensemble.pt or wound_mobilenet.pt)",
)
def test_wound_infer_runs():
    from ml.infer import load_wound_model, pick_wound_checkpoint, predict_wound_probs

    sample = next((ROOT / "data" / "geo_data" / "categories" / "hemotoxic").glob("*.jpg"))
    ck = pick_wound_checkpoint(ROOT)
    assert ck is not None
    m, dev = load_wound_model(ck)
    p = predict_wound_probs(m, dev, sample)
    assert len(p) == 5
    assert abs(p.sum() - 1.0) < 1e-4
