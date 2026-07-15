#!/usr/bin/env bash
# Wait until Home Assistant has FULLY restarted after a deploy.
#
# Why this exists: after `homeassistant.restart`, the API answers 200 within a
# second or two (early boot / pre-shutdown) while only ~12 entities exist. Check
# entities then and you'll wrongly conclude the integration failed to load. This
# polls until the entity count stabilizes (typically ~25-30s).
#
# Usage:  scripts/ha-wait-ready.sh          # exits 0 when ready, 1 on timeout
#         TRIES=60 scripts/ha-wait-ready.sh # more attempts (3s each)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; cd "$ROOT"

TOKEN="${HA_API_TOKEN:-$(python3 -c "import yaml;print(yaml.safe_load(open('secrets.yaml'))['ha_api_token'])")}"
URL="${HA_API_URL:-$(python3 -c "import yaml;print(yaml.safe_load(open('deploy.local.yaml'))['ha_api_url'])")}"
URL="${URL%/}"

prev=-1; stable=0; n=0
for _ in $(seq 1 "${TRIES:-40}"); do
  n=$(curl -sS -m 5 -H "Authorization: Bearer $TOKEN" "$URL/api/states" 2>/dev/null \
      | python3 -c "import sys,json;print(len(json.load(sys.stdin)))" 2>/dev/null || echo 0)
  if [[ "$n" -gt 12 && "$n" == "$prev" ]]; then stable=$((stable+1)); else stable=0; fi
  if [[ "$stable" -ge 2 ]]; then echo "HA ready: $n entities."; exit 0; fi
  prev="$n"; sleep 3
done
echo "HA did not stabilize (last count: $n)." >&2
exit 1
