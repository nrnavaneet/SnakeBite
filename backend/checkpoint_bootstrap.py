"""Optional download of wound ensemble weights before PyTorch load (when local file is missing)."""
from __future__ import annotations

import logging
import os
import urllib.error
import urllib.request
from pathlib import Path

from ml.checkpoint_util import WOUND_ENSEMBLE_FILENAME

logger = logging.getLogger(__name__)

# Refuse to treat tiny/corrupt files as a valid checkpoint
_MIN_BYTES = 1_000_000


def ensure_wound_checkpoint_from_env(root: Path) -> None:
    """
    If ``WOUND_ENSEMBLE_URL`` or ``WOUND_CHECKPOINT_URL`` is set, download to
    ``models/wound_ensemble.pt`` when the file is missing or too small.

    This makes production match a local dev machine that has the same file under ``models/``.
    Use a release asset URL (GitHub, S3, etc.); keep the link private in your environment.
    """
    url = (os.environ.get("WOUND_ENSEMBLE_URL") or os.environ.get("WOUND_CHECKPOINT_URL") or "").strip()
    if not url:
        return

    dest = root / "models" / WOUND_ENSEMBLE_FILENAME
    force = os.environ.get("WOUND_ENSEMBLE_FORCE", "").strip() in ("1", "true", "yes")

    if dest.is_file() and dest.stat().st_size >= _MIN_BYTES and not force:
        logger.info("Wound ensemble already present at %s (%s bytes)", dest, dest.stat().st_size)
        return

    dest.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Downloading wound ensemble checkpoint from WOUND_ENSEMBLE_URL …")

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "SnakeBiteRx-API/1.0"})
        with urllib.request.urlopen(req, timeout=900) as resp:
            data = resp.read()
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        logger.error("Could not download wound checkpoint: %s", e)
        return

    if len(data) < _MIN_BYTES:
        logger.error(
            "Downloaded payload too small (%s bytes); expected a full .pt file. Not writing.",
            len(data),
        )
        return

    dest.write_bytes(data)
    logger.info("Saved wound ensemble to %s (%s bytes)", dest, len(data))
