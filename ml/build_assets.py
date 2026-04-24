#!/usr/bin/env python3
"""Build symptom catalog/model and Bayesian geo priors (no GPU). Run once before serving."""
from __future__ import annotations

from ml.geo_model import build_geo_index
from ml.geo_regions import build_geo_region_json
from ml.geo_species import build_geo_species_json
from ml.symptom_engine import save_catalog


def main() -> None:
    print("Building symptom catalog + XGBoost symptom model...")
    p = save_catalog()
    print("  wrote", p)
    print("Building Bayesian geo region priors (country/state)...")
    gr = build_geo_region_json()
    print("  wrote", gr)
    print("Building geo species table (region × venom → species)...")
    gs = build_geo_species_json()
    print("  wrote", gs)
    print("Building geo index (India lat/lon BallTree, optional)...")
    g = build_geo_index()
    print("  wrote", g)


if __name__ == "__main__":
    main()
