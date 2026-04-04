"""checkpoint_bootstrap: no download when env unset."""
from __future__ import annotations

from pathlib import Path

import pytest


def test_ensure_skips_when_no_env(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("WOUND_ENSEMBLE_URL", raising=False)
    monkeypatch.delenv("WOUND_CHECKPOINT_URL", raising=False)

    from backend.checkpoint_bootstrap import ensure_wound_checkpoint_from_env

    ensure_wound_checkpoint_from_env(tmp_path)
    from ml.checkpoint_util import WOUND_ENSEMBLE_FILENAME

    assert not (tmp_path / "models" / WOUND_ENSEMBLE_FILENAME).is_file()
