"""Blur / sharpness heuristics."""
from __future__ import annotations

import numpy as np

from ml.image_quality import assess_image_quality, laplacian_variance


def test_laplacian_variance_uniform_is_zero() -> None:
    g = np.ones((32, 32), dtype=np.float64) * 128.0
    assert laplacian_variance(g) == 0.0


def test_laplacian_variance_noise_positive() -> None:
    rng = np.random.default_rng(0)
    g = rng.standard_normal((64, 64)) * 50 + 128.0
    assert laplacian_variance(g) > 1.0


def test_assess_image_quality_returns_keys(tmp_path) -> None:
    from PIL import Image

    p = tmp_path / "x.png"
    Image.new("RGB", (64, 64), color=(120, 90, 70)).save(p)
    q = assess_image_quality(p)
    assert "sharpness_score" in q
    assert "recommend_retake" in q
    assert "severe_blur" in q
    assert q["sharpness_score"] is not None
