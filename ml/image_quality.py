"""Heuristic sharpness / blur detection for wound photos (not a medical device)."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

# Laplacian variance on grayscale (higher = sharper). Tunable; depends on resize.
# Lenient policy: only **extreme** softness triggers retake / messaging (unusable detail).
# Typical: >~120 sharp phone; ~50–90 acceptable; <~32 effectively unusable.
_EXTREME_BLUR_MAX = 32.0


def _gray_array(path: Path, *, max_side: int = 768) -> np.ndarray:
    img = Image.open(path).convert("L")
    w, h = img.size
    m = max(w, h)
    if m > max_side:
        s = max_side / m
        img = img.resize((int(w * s), int(h * s)), Image.Resampling.LANCZOS)
    return np.asarray(img, dtype=np.float64)


def laplacian_variance(gray: np.ndarray) -> float:
    """Variance of discrete Laplacian (interior pixels)."""
    if gray.ndim != 2 or gray.shape[0] < 3 or gray.shape[1] < 3:
        return 0.0
    g = gray
    lap = (
        g[2:, 1:-1]
        + g[:-2, 1:-1]
        + g[1:-1, 2:]
        + g[1:-1, :-2]
        - 4.0 * g[1:-1, 1:-1]
    )
    return float(lap.var())


def assess_image_quality(
    image_path: Path,
    *,
    blur_threshold: float = _EXTREME_BLUR_MAX,
) -> dict[str, Any]:
    """
    Returns sharpness score and whether the photo is **extremely** soft (unusable).

    ``sharpness_score`` is Laplacian variance. ``recommend_retake`` is True only for
    extreme blur (below ``blur_threshold``), not for mild softness.
    """
    try:
        gray = _gray_array(image_path)
        score = laplacian_variance(gray)
    except OSError:
        return {
            "sharpness_score": None,
            "is_blurry": True,
            "recommend_retake": True,
            "reason": "unreadable_image",
            "message": "Could not read the image — try again with a standard JPG/PNG.",
        }

    extreme_blur = score < blur_threshold
    msg = None
    if extreme_blur:
        msg = (
            "This image is extremely blurry or lacks usable detail — please reupload a clearer photo. "
            "Use bright, even light, hold the phone steady, and tap the wound to focus."
        )
    return {
        "sharpness_score": round(score, 2),
        "blur_threshold": blur_threshold,
        "severe_blur_threshold": blur_threshold,
        "severe_blur": extreme_blur,
        "is_blurry": extreme_blur,
        "recommend_retake": extreme_blur,
        "reason": "extreme_blur" if extreme_blur else None,
        "message": msg,
    }
