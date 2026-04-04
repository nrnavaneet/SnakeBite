#!/usr/bin/env bash
# Render static site buildCommand (see render.yaml). Delegates to scripts/build_web.sh.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export RENDER=true
exec bash "${ROOT}/scripts/build_web.sh"
