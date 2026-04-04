"""Checkpoint paths only — no PyTorch import (keeps Render free-tier RAM usable when no *.pt is deployed)."""
from __future__ import annotations

from pathlib import Path


def pick_wound_checkpoint(root: Path | None = None) -> Path | None:
    root = root or Path(__file__).resolve().parents[1]
    ens = root / "models" / "wound_ensemble.pt"
    leg = root / "models" / "wound_mobilenet.pt"
    if ens.is_file():
        return ens
    if leg.is_file():
        return leg
    return None
