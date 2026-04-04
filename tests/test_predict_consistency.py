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
