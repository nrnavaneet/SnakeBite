#!/usr/bin/env bash
# Validate render.yaml and trigger a deploy for snakebite-api + snakebite-web (if they exist).
#
# Prerequisite (one-time):
#   brew install render   # or: curl -fsSL https://raw.githubusercontent.com/render-oss/cli/refs/heads/main/bin/install.sh | sh
#   render login
#   render workspace set
#
# First-time Blueprint: Render still requires Dashboard → New → Blueprint → connect repo (CLI has no "apply yaml" yet).
# After services exist, use this script whenever you want a fresh deploy from the latest git default branch.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if ! command -v render >/dev/null 2>&1; then
  echo "Install the Render CLI: brew install render"
  echo "Docs: https://render.com/docs/cli"
  exit 1
fi

render blueprints validate render.yaml -o text --confirm
echo "render.yaml: OK"

# Find service IDs by name in `render services -o json` output (schema-tolerant).
IDS="$(
  render services -o json --confirm | python3 -c "
import json, sys

def walk(o, found):
    if isinstance(o, dict):
        name, sid = o.get('name'), o.get('id')
        if name in ('snakebite-api', 'snakebite-web') and isinstance(sid, str):
            found[name] = sid
        for v in o.values():
            walk(v, found)
    elif isinstance(o, list):
        for x in o:
            walk(x, found)

data = json.load(sys.stdin)
found = {}
walk(data, found)
for n in ('snakebite-api', 'snakebite-web'):
    if n in found:
        print(found[n])
"

)"

if [[ -z "${IDS}" ]]; then
  echo ""
  echo "No snakebite-api / snakebite-web services found in this workspace yet."
  echo ""
  echo "First-time setup (one browser flow):"
  echo "  1. https://dashboard.render.com → New → Blueprint"
  echo "  2. Connect the GitHub repo that contains this render.yaml, branch main"
  echo "  3. Review + Deploy Blueprint (creates both services from the file)"
  echo "  4. Re-run: bash scripts/render_deploy.sh"
  echo ""
  RENDER_SVCS="$(render services -o json --confirm 2>/dev/null || true)"
  if [[ -n "${RENDER_SVCS}" ]]; then
    echo "Services currently in this workspace (for reference):"
    echo "${RENDER_SVCS}" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
except json.JSONDecodeError:
    print('  (could not parse services JSON)')
    sys.exit(0)
pairs = []
def walk(o):
    if isinstance(o, dict):
        n, i = o.get('name'), o.get('id')
        if isinstance(n, str) and isinstance(i, str) and len(i) > 4:
            pairs.append((n, i))
        for v in o.values():
            walk(v)
    elif isinstance(o, list):
        for x in o:
            walk(x)
walk(data)
if not pairs:
    print('  (none — empty workspace or unexpected API shape)')
else:
    for n, i in sorted(set(pairs)):
        print(f'  • {n}  [{i}]')
" 2>/dev/null || true
  fi
  exit 0
fi

echo "Starting deploys..."
while read -r SID; do
  [[ -z "${SID}" ]] && continue
  echo "  → deploys create ${SID}"
  render deploys create "${SID}" --confirm --wait -o text
done <<< "${IDS}"

echo "Done."
