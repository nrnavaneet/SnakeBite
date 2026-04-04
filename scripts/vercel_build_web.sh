#!/usr/bin/env bash
# Build Flutter web for Vercel. Set API_BASE in the Vercel project env to your *public HTTPS* API URL
# (e.g. https://snakebite-api.onrender.com). Local dev: omit API_BASE to keep http://127.0.0.1:8000 default.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP_DIR="$ROOT/mobile/snakebite_rx"
cd "$APP_DIR"

# Cache Flutter between builds (Vercel exposes VERCEL_CACHE_DIR when available).
CACHE="${VERCEL_CACHE_DIR:-$HOME/.cache}"
FLUTTER_DIR="${CACHE}/flutter_stable"

if [[ ! -x "${FLUTTER_DIR}/bin/flutter" ]]; then
  echo "Installing Flutter stable to ${FLUTTER_DIR}..."
  rm -rf "${FLUTTER_DIR}"
  mkdir -p "$(dirname "${FLUTTER_DIR}")"
  git clone https://github.com/flutter/flutter.git -b stable --depth 1 "${FLUTTER_DIR}"
fi

export PATH="${FLUTTER_DIR}/bin:${PATH}"
flutter --version
flutter config --no-analytics
flutter pub get

# Production API URL (HTTPS). Empty on Vercel: use web/api_config.json "apiBase" or set URL in-app Settings (never 127.0.0.1).
API="${API_BASE:-}"
echo "Building web (API_BASE length: ${#API})"

flutter build web --release \
  --dart-define=API_BASE="${API}" \
  --base-href /

echo "Output: ${APP_DIR}/build/web"
