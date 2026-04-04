#!/usr/bin/env bash
# Shared Flutter web build for Vercel, Render static, or local.
# Set API_BASE to your public HTTPS API root (no trailing slash). Bakes into --dart-define + build/web/api_config.json.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP_DIR="$ROOT/mobile/snakebite_rx"
cd "$APP_DIR"

# Cache Flutter between builds (Vercel sets VERCEL_CACHE_DIR).
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

API="${API_BASE:-}"
# On Vercel, default to same-origin /api/proxy → Render (vercel.json) to avoid cross-origin "Failed to fetch".
# Set API_BASE to https://YOUR_CUSTOM_DOMAIN/api/proxy if you use a custom domain on Vercel.
if [[ -n "${VERCEL:-}" && -n "${VERCEL_URL:-}" ]]; then
  if [[ -n "${API_BASE:-}" && "${API_BASE}" == *"/api/proxy"* ]]; then
    API="${API_BASE}"
  else
    API="https://${VERCEL_URL}/api/proxy"
  fi
  echo "Vercel: API base = ${API}"
fi
echo "Building web (effective API base length: ${#API})"

if [[ -z "${API}" && -n "${VERCEL:-}" ]]; then
  echo "WARNING: No API URL. Use Git-integrated deploy so VERCEL_URL is set, or set API_BASE."
fi
if [[ -z "${API}" && "${RENDER:-}" == "true" ]]; then
  echo "WARNING: API_BASE is unset. For Render static, set API_BASE on the static site (see render.yaml) or point web/api_config.json at your API."
fi

flutter build web --release \
  --dart-define=API_BASE="${API}" \
  --base-href /

WEB_OUT="${APP_DIR}/build/web"
if [[ -n "${API}" ]]; then
  python3 -c "import json, pathlib, sys; b=sys.argv[1]; p=pathlib.Path(sys.argv[2]); p.write_text(json.dumps({'apiBase': b}, indent=2) + '\n')" "${API}" "${WEB_OUT}/api_config.json"
fi

echo "Output: ${WEB_OUT}"
