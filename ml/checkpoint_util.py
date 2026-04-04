"""Checkpoint paths only — no PyTorch import (keeps API startup light when no *.pt is present)."""
from __future__ import annotations

from pathlib import Path

# Canonical names under models/ — keep in sync with train_wound.py, train_both_checkpoints.sh, bootstrap.
WOUND_ENSEMBLE_FILENAME = "wound_ensemble.pt"
WOUND_MOBILENET_FILENAME = "wound_mobilenet.pt"


def pick_wound_checkpoint(root: Path | None = None) -> Path | None:
    root = root or Path(__file__).resolve().parents[1]
    ens = root / "models" / WOUND_ENSEMBLE_FILENAME
    leg = root / "models" / WOUND_MOBILENET_FILENAME
    if ens.is_file():
        return ens
    if leg.is_file():
        return leg
    return None
