"""Species table: priors sum, Karnataka neuro species plausible, fusion uses 5-class vector."""
from __future__ import annotations

import numpy as np

from ml.config import CLASSES
from ml.geo_species import load_geo_species_payload, rank_snake_species


def _row_sci(row: object) -> str:
    if isinstance(row, dict):
        return str(row.get("scientific") or row.get("name") or "")
    return str(row[0])


def test_payload_has_karnataka_neuro() -> None:
    p = load_geo_species_payload()
    reg = p.get("by_region") or {}
    assert "India|Karnataka" in reg
    neuro = reg["India|Karnataka"].get("neurotoxic") or []
    names = [_row_sci(row) for row in neuro[:5]]
    assert any("Naja" in str(x) for x in names) or any("Bungarus" in str(x) for x in names)


def test_rank_sums_order_decreases() -> None:
    p = load_geo_species_payload()
    venom = np.array([0.05, 0.1, 0.7, 0.1, 0.05], dtype=np.float64)
    venom /= venom.sum()
    ranked, _ = rank_snake_species(venom, "India", "Karnataka", ["ptosis"], p, top_k=8)
    assert len(ranked) >= 1
    scores = [x["score"] for x in ranked]
    assert scores == sorted(scores, reverse=True)


def test_full_class_vector_length() -> None:
    p = load_geo_species_payload()
    assert len(CLASSES) == 5
    u = np.ones(5) / 5.0
    ranked, dbg = rank_snake_species(u, "India", "", [], p)
    assert "venom_weights_applied" in dbg
    assert isinstance(ranked, list)
