# Why these models? How fusion is weighted

This doc explains **design intent** — not a clinical validation report. Tune weights in `ml/fusion.py` / `ml/config.py` only with proper offline evaluation.

---

## Why a wound **ensemble** (three CNNs)?

- **Single architectures can overfit** texture quirks (lighting, skin tone, camera). Combining **EfficientNet-B3**, **ResNet50**, and **DenseNet121** averages their softmax outputs with fixed weights so no one backbone dominates by mistake.
- **Default softmax fusion weights (58% / 26% / 16%)** favor EfficientNet-B3 because it usually transfers best from ImageNet to fine-grained medical-style crops; ResNet and DenseNet add diversity and stabilize borders / local patterns.
- Weights are **stored in the checkpoint** (`wound_ensemble.pt`); training can override them. MobileNet-only checkpoints (`wound_mobilenet.pt`) exist for **small deploys** — same 5-class head, **not** the same lab ensemble as the 3-model stack.

---

## Why symptom + geo + context, not image alone?

- A photo **cannot** show systemic neurotoxic progression, coagulopathy, or many hemotoxic signs. **Symptoms** (checklist → XGBoost symptom classifier) encode that side.
- **Geography** injects **species / regional priors** (GBIF-derived, **not** bite registries): it answers “what venom patterns occur in this region?” not “this patient was bitten here.”
- **Context** (time since bite, circumstance, age, weight) adjusts a **weak heuristic prior** in log-space (e.g. early hours → slightly more local hemo/cyto emphasis; krait-like contexts → neuro bump). It is **not** a substitute for exam.

---

## How multimodal **weights** work (`ml/fusion.py`)

Fusion is **log-space**: `w_w·log(p_wound) + w_s·log(p_sym) + w_g·log(p_geo) + w_c·log(p_context)`, then softmax. That avoids one modality zeroing another out compared to linear mixing.

### Modality weights (two regimes)

| Situation | Wound | Symptom | Geo | Context | Rationale |
|-----------|-------|---------|-----|---------|-----------|
| **Wound model missing** | 0.38 | 0.22 | 0.22 | 0.18 | Image branch is **uniform**; symptoms + geo carry the signal. |
| **Wound uncertain** (`wound_uncertain`) | 0.28 | 0.28 | 0.24 | 0.20 | Trust the image **less**; symptoms and geo rise. |
| **Wound confident** (loaded + not uncertain) | **0.80** | **0.07** | **0.10** | **0.03** | Strong image read should **not** be overridden by a one-hot symptom checklist or a narrow geo prior. |

Constants: `W_WOUND`, `W_SYMPTOM`, … through `W_WOUND_CONFIDENT` / `W_UNCERTAIN_*` in `ml/fusion.py`.

### Why smooth symptom / geo probabilities?

- Symptom model outputs can become highly peaked. Taking `log` of tiny probabilities would **veto** other classes. **Floors** (`SYMPTOM_PROB_FLOOR`, `GEO_PROB_FLOOR`) renormalize so fusion stays stable.
- If the **wound argmax disagrees** with the **symptom argmax** but the wound is confident (≥ ~0.5 max), the symptom vector is **blended toward uniform** (`SYMPTOM_CONFLICT_UNIFORM_MIX`) so a single checked box cannot flip a strong image read.

---

## Why “unknown” / confidence gates?

- **Wound branch:** If ensemble max is low or the softmax is **flat** (top classes too close), `wound_uncertain` is true and fusion uses the **uncertain** row in the table above.
- **Fused output:** If the **final** top probability is **&lt; 0.60**, the API sets `display_top_class` to **`unknown`** so the UI does not imply a firm venom type when the model is not confident (see `FINAL_PREDICTION_UNCERTAIN_THRESHOLD` in `ml/config.py`).

---

## Image quality (Laplacian variance)

- **Why:** Bad focus / motion blur makes CNN features unreliable before any fusion question.
- **How:** Variance of a **discrete Laplacian** on grayscale (same idea in `ml/image_quality.py` and the Flutter client’s local check after pick).
- **Not** a clinical “quality of wound” score — only **sharpness / detail** heuristics.

---

## Where to change behavior

| Goal | Location |
|------|----------|
| Modality balance (more/less image vs symptoms) | `ml/fusion.py` — `W_WOUND_CONFIDENT`, floors, conflict mix |
| When wound is “uncertain” | `ml/config.py` — `WOUND_UNCERTAIN_*`, `ml/infer.py` |
| When fused headline shows `unknown` | `ml/config.py` — `FINAL_PREDICTION_UNCERTAIN_THRESHOLD` |
| Blur thresholds | `ml/image_quality.py` + Flutter `lib/utils/image_quality_local.dart` (keep in sync) |

---

## Disclaimer

Educational / research software — not a medical device. Geography and species tables are **not** incidence data; models **err**. Always use local emergency protocols.
