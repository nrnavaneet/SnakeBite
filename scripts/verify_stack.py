#!/usr/bin/env python3
"""Verify models/assets exist and multimodal pipeline runs (no server)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    errors: list[str] = []
    models = ROOT / "models"
    wound_ck = None
    if (models / "wound_ensemble.pt").is_file():
        wound_ck = models / "wound_ensemble.pt"
    elif (models / "wound_mobilenet.pt").is_file():
        wound_ck = models / "wound_mobilenet.pt"
    else:
        errors.append("missing models/wound_ensemble.pt or models/wound_mobilenet.pt")

    for name in (
        "symptom_catalog.json",
        "geo_index.pkl",
        "geo_region_prior.json",
        "geo_species_table.json",
    ):
        p = models / name
        if not p.is_file():
            errors.append(f"missing {p.relative_to(ROOT)}")

    wound_csv = ROOT / "data" / "wound_data" / "training_data.csv"
    if not wound_csv.is_file():
        errors.append("missing data/wound_data/training_data.csv")

    if errors:
        print("FAIL:")
        for e in errors:
            print(" ", e)
        return 1

    from ml.config import CLASSES
    from ml.fusion import fuse_multimodal, top_prediction
    from ml.geo_regions import geo_prior_from_region, load_geo_region_payload
    from ml.geo_species import load_geo_species_payload, rank_snake_species
    from ml.infer import load_wound_model, predict_wound_probs
    from ml.symptom_engine import load_catalog, score_symptoms

    payload = load_geo_region_payload()
    sp_payload = load_geo_species_payload()
    syms, mat, _items = load_catalog()
    sym_p = score_symptoms(["ptosis"], syms, mat)
    g_p = geo_prior_from_region("India", "Karnataka", payload)
    assert wound_ck is not None
    model, dev = load_wound_model(wound_ck)
    sample = ROOT / "data" / "geo_data" / "categories" / "hemotoxic"
    jpgs = list(sample.glob("*.jpg"))
    if not jpgs:
        print("FAIL: no data/geo_data/categories/hemotoxic/*.jpg for smoke test")
        return 1
    w_p = predict_wound_probs(model, dev, jpgs[0])
    final, _ = fuse_multimodal(
        w_p,
        sym_p,
        g_p,
        time_since_bite_hours=2.0,
        bite_circumstance="nocturnal_indoor_sleeping",
        age_years=35.0,
        weight_kg=60.0,
    )
    top, conf = top_prediction(final)
    species_rank, _ = rank_snake_species(final, "India", "Karnataka", ["ptosis"], sp_payload)

    print("OK — SnakeBiteRx stack verified")
    print("  classes:", list(CLASSES))
    print("  wound checkpoint:", wound_ck.name, getattr(model, "kind", ""))
    print("  smoke image:", jpgs[0].name)
    print("  geo: India / Karnataka →", g_p.round(3).tolist())
    print("  fusion top:", top, f"({conf:.3f})")
    if species_rank:
        print(
            "  likely snakes (top-3):",
            [(x.get("name"), x.get("scientific_name"), round(x["score"], 4)) for x in species_rank[:3]],
        )
    cat = json.loads((models / "symptom_catalog.json").read_text(encoding="utf-8"))
    print("  symptom_catalog symptoms:", len(cat.get("symptoms", [])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
