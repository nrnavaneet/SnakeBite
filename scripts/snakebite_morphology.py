"""
Geometry hints for snakebite wound crops (not a clinical diagnosis).

``tooth_row_score`` — high values suggest many distinct bright puncture-like foci
along an arc (typical non-venomous tooth rows). Empirically ~>1.55 separates
known U-shaped tooth rows from typical two-fang bleeds in this dataset.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from PIL import Image


def scattered_blood_fraction(pil_img: Image.Image, size: int = 200) -> float:
    a = np.asarray(pil_img.convert("RGB").resize((size, size)), dtype=np.float32)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    mask = (r > 85.0) & (r > g + 18.0) & (r > b + 15.0)
    return float(mask.mean())


def necrosis_dark_fraction(pil_img: Image.Image, size: int = 128) -> float:
    g = np.asarray(pil_img.convert("L").resize((size, size)), dtype=np.float64)
    return float((g < 52.0).mean())


def tooth_row_score(pil_img: Image.Image, size: int = 256) -> float:
    """
    Local maxima of strict blood-colored pixels, normalized by sqrt(blood pixel count).
    High scores ≈ many separate puncture foci (tooth row); low ≈ one or two blobs.
    """
    try:
        from scipy import ndimage
    except ImportError:
        return 0.0

    a = np.asarray(pil_img.convert("RGB").resize((size, size)), dtype=np.float64)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    cond = (r > 105.0) & (r > g + 28.0) & (r > b + 22.0)
    r2 = np.where(cond, r, 0.0)
    rf = ndimage.gaussian_filter(r2, 1.0)
    mx = ndimage.maximum_filter(rf, size=5)
    p120 = float(((rf == mx) & (rf > 120.0) & cond).sum())
    nb = float(cond.sum()) + 1e-6
    return float(p120 / np.sqrt(nb))


# Above this, prefer non-venomous over hemotoxic/neuro CLIP (calibrated on project samples)
TOOTH_ROW_SCORE_THRESHOLD = 1.55


def morphology_bite_pattern(pil_img: Image.Image) -> tuple[str, dict[str, Any]]:
    """Backward-compatible: ``many_small_teeth`` if tooth_row_score is high."""
    s = tooth_row_score(pil_img)
    if s >= TOOTH_ROW_SCORE_THRESHOLD:
        return "many_small_teeth", {"tooth_row_score": round(s, 3)}
    if s <= 0.65:
        return "paired_or_few", {"tooth_row_score": round(s, 3)}
    return "ambiguous", {"tooth_row_score": round(s, 3)}
