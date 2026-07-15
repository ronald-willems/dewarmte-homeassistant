#!/usr/bin/env bash
# Fetch live Home Assistant Core logs and (by default) filter to this integration.
#
# Why this exists: on this HA install `/api/error_log` returns 404 and there is
# no writable /config/home-assistant.log (Core logs to the journal). The reliable
# source is the Supervisor endpoint /api/hassio/core/logs, which includes the
# integration's DEBUG lines.
#
# Usage:
#   scripts/ha-logs.sh                 # last lines mentioning "dewarmte"
#   scripts/ha-logs.sh writes          # settings-write activity (POST bodies + responses/errors)
#   scripts/ha-logs.sh 'some|regex'    # custom grep -E pattern ('' = no filter)
#   LINES=100 scripts/ha-logs.sh       # override how many trailing lines to show
#
# Config: reads ha_api_url from deploy.local.yaml and ha_api_token from secrets.yaml
# (env HA_API_URL / HA_API_TOKEN override).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; cd "$ROOT"

PATTERN="${1-dewarmte}"
if [[ "$PATTERN" == "writes" ]]; then
  # Shorthand for the settings read-modify-write trail.
  PATTERN='dewarmte.*(POST request|settings update response|Failed to update|Error updating|Updating operation setting|Could not get current|start-forced|stop-forced)'
fi

TOKEN="${HA_API_TOKEN:-$(python3 -c "import yaml;print(yaml.safe_load(open('secrets.yaml'))['ha_api_token'])")}"
URL="${HA_API_URL:-$(python3 -c "import yaml;print(yaml.safe_load(open('deploy.local.yaml'))['ha_api_url'])")}"
URL="${URL%/}"

RAW=$(curl -sS -m 30 -H "Authorization: Bearer $TOKEN" "$URL/api/hassio/core/logs" | sed -E 's/\x1b\[[0-9;]*m//g')
if [[ -z "$PATTERN" ]]; then
  printf '%s\n' "$RAW" | tail -"${LINES:-40}"
else
  printf '%s\n' "$RAW" | grep -iE "$PATTERN" | tail -"${LINES:-60}" || echo "(no log lines matching: $PATTERN)"
fi
