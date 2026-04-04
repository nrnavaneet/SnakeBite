#!/usr/bin/env bash
# SnakeBiteRx — one-shot dev setup after a fresh `git clone`.
# Usage: from repo root →  bash scripts/setup_dev.sh
# Requires: python3 (3.10+), pip. Optional: flutter (for mobile/web app).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " SnakeBiteRx — dev environment setup"
echo " Repo: $ROOT"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 not found. Install Python 3.10+ and retry." >&2
  exit 1
fi

PY_VER="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
echo "→ Using Python $PY_VER"

if [[ ! -d "$ROOT/.venv" ]]; then
  echo "→ Creating virtualenv .venv …"
  python3 -m venv "$ROOT/.venv"
else
  echo "→ Virtualenv .venv already exists (reusing)"
fi

# shellcheck disable=SC1091
source "$ROOT/.venv/bin/activate"

echo "→ Upgrading pip …"
python -m pip install --upgrade pip

echo "→ Installing Python dependencies (this may take several minutes) …"
pip install -r "$ROOT/requirements.txt"

echo "→ Building ML assets (symptom + geo catalogs, geo_index.pkl) …"
python3 -m ml.build_assets

if command -v flutter >/dev/null 2>&1; then
  echo "→ flutter pub get (mobile/snakebite_rx) …"
  (cd "$ROOT/mobile/snakebite_rx" && flutter pub get)
else
  echo "→ Skipping Flutter: 'flutter' not in PATH."
  echo "   Install the Flutter SDK and add it to PATH, then run:"
  echo "     cd mobile/snakebite_rx && flutter pub get"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " Setup finished."
echo ""
echo " Next steps:"
echo ""
echo "  1) Start the API (keep this terminal open):"
echo "       cd \"$ROOT\""
echo "       source .venv/bin/activate"
echo "       make api"
echo ""
echo "  2) In a second terminal, run the Flutter app:"
echo "       cd \"$ROOT/mobile/snakebite_rx\""
echo "       flutter run --dart-define=API_BASE=http://127.0.0.1:8000"
echo ""
echo " Optional — wound CNN checkpoint:"
echo "   • Copy models/wound_ensemble.pt into the repo, OR"
echo "   • Set env WOUND_ENSEMBLE_URL before starting the API (see README)."
echo ""
echo " Verify (needs checkpoint + sample data under data/):"
echo "       make verify"
echo " Tests:"
echo "       python3 -m pytest tests/ -q"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
