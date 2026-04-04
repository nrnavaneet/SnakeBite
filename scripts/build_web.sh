#!/usr/bin/env bash
# Local Flutter web build. Defaults API to http://127.0.0.1:8000 (override with API_BASE).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP_DIR="$ROOT/mobile/snakebite_rx"
cd "$APP_DIR"

if ! command -v flutter >/dev/null 2>&1; then
  echo "Flutter is not on PATH. Install: https://docs.flutter.dev/get-started/install" >&2
  exit 1
fi

flutter pub get

# Default: local FastAPI from make api
API="${API_BASE:-http://127.0.0.1:8000}"
echo "Building web (API_BASE=${API})"

flutter build web --release \
  --dart-define=API_BASE="${API}" \
  --base-href /

WEB_OUT="${APP_DIR}/build/web"
python3 -c "import json, pathlib, sys; b=sys.argv[1]; p=pathlib.Path(sys.argv[2]); p.write_text(json.dumps({'apiBase': b}, indent=2) + '\n')" "${API}" "${WEB_OUT}/api_config.json"

echo "Output: ${WEB_OUT}"
echo "Serve with: cd ${WEB_OUT} && python3 -m http.server 8080"
echo "Or open build/web in Chrome after: make api (API on :8000)"
