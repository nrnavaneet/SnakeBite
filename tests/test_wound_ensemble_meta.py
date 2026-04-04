"""Wound ensemble metadata: weights and uncertainty threshold."""
from __future__ import annotations

import numpy as np

from ml.config import CLASSES, WOUND_UNCERTAIN_CONFIDENCE_THRESHOLD
from ml.wound_arch import DEFAULT_ENSEMBLE_WEIGHTS, ENSEMBLE_ARCHS


def test_default_ensemble_weights_sum_and_efficientnet_heaviest() -> None:
    assert len(DEFAULT_ENSEMBLE_WEIGHTS) == len(ENSEMBLE_ARCHS)
    assert abs(sum(DEFAULT_ENSEMBLE_WEIGHTS) - 1.0) < 1e-6
    assert DEFAULT_ENSEMBLE_WEIGHTS[0] > DEFAULT_ENSEMBLE_WEIGHTS[1] > DEFAULT_ENSEMBLE_WEIGHTS[2]


def test_wound_predictor_marks_uncertain_when_max_below_threshold() -> None:
    import torch
    import torch.nn as nn
    from ml.infer import WoundPredictor

    dev = torch.device("cpu")

    class Dummy(nn.Module):
        def forward(self, x: torch.Tensor) -> torch.Tensor:
            return torch.ones(x.shape[0], len(CLASSES), dtype=torch.float32, device=x.device)

    pred = WoundPredictor(dev, [("dummy", Dummy())], [1.0], kind="single")
    import tempfile
    from pathlib import Path

    from PIL import Image

    p = Path(tempfile.mkdtemp()) / "t.jpg"
    Image.new("RGB", (224, 224), color=(100, 50, 30)).save(p)
    out, meta = pred.predict(p)
    assert meta["wound_uncertain"] is True
    assert meta["wound_effective_class"] == "unknown"
    assert meta["ensemble_max_confidence"] < WOUND_UNCERTAIN_CONFIDENCE_THRESHOLD
