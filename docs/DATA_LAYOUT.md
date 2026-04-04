# Data folder layout

```
data/
├── geo_data/
│   ├── snake_geo_clean.csv       # GBIF-style rows: species, country, state, venom_type, coords, …
│   ├── categories/               # Images under venom-type folder names (e.g. hemotoxic/, …)
│   └── snake_wounds_labels.json # Wound image paths + labels (see labeling rubric)
├── wound_data/
│   ├── training_data.csv         # Training index for wound CNN
│   └── …                         # Additional splits / notes as used by training scripts
└── symptom_data/
    └── processed/                # Symptom + context CSVs for KB builders
```

## Regenerating API assets

After changing geo CSVs or symptom sources:

```bash
make assets
```

This refreshes JSON/PKL under **`models/`** (e.g. `geo_region_prior.json`, `geo_species_table.json`, `symptom_catalog.json`, `geo_index.pkl`) consumed by the backend.

## Labeling

Wound images must match the **five** venom classes used by the classifier. Files in `unknown/` or unlabeled folders are **not** used as supervised training for the wound head. See **`docs/SnakeBiteRx_Labeling_Rubric.pdf`** when available in your checkout.
