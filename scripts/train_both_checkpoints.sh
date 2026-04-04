#!/usr/bin/env bash
# Train both checkpoint files used by pick_wound_checkpoint():
#   1) models/wound_ensemble.pt  (EfficientNet-B3 + ResNet50 + DenseNet121)
#   2) models/wound_mobilenet.pt (single MobileNet-V3-Small — legacy filename)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PY="${ROOT}/.venv/bin/python"
if [[ ! -x "$PY" ]]; then
  echo "Need .venv with torch: $PY" >&2
  exit 1
fi
EPOCHS="${EPOCHS:-20}"
BS="${BS:-8}"

echo "=== [1/2] Ensemble -> models/wound_ensemble.pt (epochs=$EPOCHS) ==="
"$PY" -u -m ml.train_wound --ensemble --epochs "$EPOCHS" --batch-size "$BS"

echo "=== [2/2] Single MobileNet -> models/wound_mobilenet.pt (epochs=$EPOCHS) ==="
"$PY" -u -m ml.train_wound --epochs "$EPOCHS" --batch-size "$BS" \
  --arch mobilenet_v3_small --out "$ROOT/models/wound_mobilenet.pt"

echo "=== Done. Outputs: models/wound_ensemble.pt models/wound_mobilenet.pt ==="
