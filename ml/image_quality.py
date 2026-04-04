"""Heuristic sharpness / blur detection for wound photos (not a medical device)."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

# Laplacian variance on grayscale (higher = sharper). Tunable; depends on resize.
_DEFAULT_BLUR_MAX = 95.0  # below this → recommend retake


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
    blur_threshold: float = _DEFAULT_BLUR_MAX,
) -> dict[str, Any]:
    """
    Returns sharpness score and whether to ask the user to retake the photo.

    ``sharpness_score`` is Laplacian variance (typical: <~80 very soft, >~150 sharp).
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

    is_blurry = score < blur_threshold
    msg = None
    if is_blurry:
        msg = (
            "This photo looks blurry, too dark, or low detail. "
            "Retake with steady hands, good light, and the wound in focus."
        )
    return {
        "sharpness_score": round(score, 2),
        "blur_threshold": blur_threshold,
        "is_blurry": is_blurry,
        "recommend_retake": is_blurry,
        "reason": "low_sharpness" if is_blurry else None,
        "message": msg,
    }
