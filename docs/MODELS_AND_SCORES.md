# Models & confidence scores

## Venom-type classes (5)

Outputs are always over:

`cytotoxic` · `hemotoxic` · `neurotoxic` · `non_venomous` · `not_snakebite`

Same labels are used for wound CNN, symptom XGBoost model, Bayesian geo prior, and fused result.

## Wound image branch

- **Preferred checkpoint:** `models/wound_ensemble.pt` — three CNNs (EfficientNet-B3, ResNet50, DenseNet121) with **softmax fusion** (default weights **58% / 26% / 16%**, overridable in checkpoint metadata).
- **Fallback:** `wound_mobilenet.pt` — single backbone; not the same as full lab ensemble.
- **Uncertainty (wound):** The ensemble read is uncertain (`wound_uncertain`) if fused wound max probability **&lt; ~0.65** *or* the gap between 1st and 2nd place is **&lt; ~0.12** (flat / ambiguous softmax). Fusion then shifts weight toward symptoms/geo (see `ml/fusion.py` and `ml/config.py`).
- **Uncertainty (fused result):** If the **multimodal** top probability is **&lt; 0.60**, the API sets `display_top_class` to **`unknown`** and `prediction_uncertain: true`, so the UI should not present a single venom type as a firm answer. `top_class` / `final_probability` still hold the raw argmax for debugging.

## Symptom & geo branches

- **Symptoms:** XGBoost multiclass model maps selected symptom set → probability vector over the 5 classes (catalog fallback only if model asset is missing).
- **Geo:** Country/state → Bayesian (Dirichlet-smoothed) regional venom-type prior + species ranking (GBIF-derived, **not** bite registries).

## Multimodal fusion (`ml/fusion.py`)

- Combines **wound**, **symptom**, **geo**, and **context** (time since bite, circumstance, age, weight) in **log space** with modality weights.
- **Confident wound** (model loaded, not uncertain): wound gets the largest log-weight; symptom/geo vectors are smoothed so a one-hot checklist cannot override a strong image read.
- **Outputs:** `final_probability` (sums to 1), `top_class`, `top_confidence`, plus `display_top_class` / `prediction_uncertain` for safe UI labeling.

## Image quality (not clinical quality)

`ml/image_quality.py` computes **Laplacian variance** (sharpness). The app is **lenient**: only **extreme** softness (score below ~**32**, tunable) sets `recommend_retake` / `severe_blur` and asks for a new photo. Mild or moderate softness does **not** nag. The Flutter client uses the same threshold for blocking analysis before upload. This is a heuristic, not a medical assessment.

## What “confidence” means

- **`top_confidence`**: value of `final_probability` at the argmax class — **model confidence**, not probability of being correct in the real world.
- **Per-backbone lines** in `wound_detail`: each CNN’s softmax top class and confidence before ensemble fusion.

Always treat outputs as **educational**; see disclaimers in the app and README.

For **why** the ensemble is built this way and **exact modality weight tables**, see **[WHY_AND_WEIGHTS.md](WHY_AND_WEIGHTS.md)**.
