"""Paths and label order for SnakeBiteRx multimodal models."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
GEO_DATA = DATA / "geo_data"
MODELS = ROOT / "models"
# Wound images live under data/geo_data/categories/<label>/
SNAKE_WOUNDS_LABELS_JSON = GEO_DATA / "snake_wounds_labels.json"
WOUND_CSV = DATA / "wound_data" / "training_data.csv"
SYMPTOM_CSV = DATA / "symptom_data" / "processed" / "symptom_dataset.csv"
CONTEXT_CSV = DATA / "symptom_data" / "processed" / "context_features.csv"
GEO_CSV = GEO_DATA / "snake_geo_clean.csv"

# 5-class venom / wound head (aligned with wound classifier)
CLASSES: tuple[str, ...] = (
    "cytotoxic",
    "hemotoxic",
    "neurotoxic",
    "non_venomous",
    "not_snakebite",
)

CLASS_TO_IDX = {c: i for i, c in enumerate(CLASSES)}

# Wound ensemble softmax: if max probability is below this, the wound branch is flagged
# uncertain and `wound_effective_class` becomes "unknown" (display / triage only).
WOUND_UNCERTAIN_CONFIDENCE_THRESHOLD = 0.60
