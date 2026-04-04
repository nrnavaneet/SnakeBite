"""Symptom salience ranking."""
from __future__ import annotations

import numpy as np

from ml.symptom_engine import rank_selected_symptoms, score_symptoms


def test_rank_orders_by_salience() -> None:
    symptoms = ["a", "b", "c"]
    mat = np.array(
        [
            [1.0, 0.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.0, 1.0],
        ],
        dtype=np.float64,
    )
    selected = ["a", "b", "c"]
    sym_p = score_symptoms(selected, symptoms, mat)
    ranked = rank_selected_symptoms(selected, symptoms, mat, sym_p)
    assert len(ranked) == 3
    assert ranked[0]["value"] in selected
