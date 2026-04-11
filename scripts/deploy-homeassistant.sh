#!/usr/bin/env bash
# Deploy custom_components/dewarmte to Home Assistant over SMB, then restart Core.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

DEPLOY="$ROOT/deploy.local.yaml"
DEPLOY_EXAMPLE="$ROOT/deploy.local.yaml.example"
SECRETS="$ROOT/secrets.yaml"

SMB_SHARE="config"

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  cat <<'EOF'
Deploy custom_components/dewarmte via Samba (share name: config), then restart Home Assistant.

Requires:
  deploy.local.yaml  — copy from deploy.local.yaml.example (ha_samba_host, ha_api_url)
  secrets.yaml       — ha_samba_username, ha_samba_password, ha_api_token

Environment overrides: HA_SAMBA_HOST, HA_API_URL, HA_SAMBA_USERNAME, HA_SAMBA_PASSWORD, HA_API_TOKEN

Requires: rsync (macOS/Linux), smbclient (e.g. brew install samba)
EOF
  exit 0
fi

if [[ ! -f "$DEPLOY" ]]; then
  echo "Missing deploy.local.yaml — copy from deploy.local.yaml.example." >&2
  echo "  cp \"$DEPLOY_EXAMPLE\" \"$DEPLOY\"" >&2
  exit 1
fi

if [[ ! -f "$SECRETS" ]]; then
  echo "Missing secrets.yaml in repo root — copy from secrets.yaml.example." >&2
  exit 1
fi

_get_scalar() {
  local file="$1" key="$2"
  local line rest
  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ -z "${line//[[:space:]]/}" ]] && continue
    [[ "$line" =~ ^[[:space:]]*# ]] && continue
    if [[ "$line" =~ ^[[:space:]]*${key}:[[:space:]]*(.*)$ ]]; then
      rest="${BASH_REMATCH[1]}"
      rest="${rest//$'\r'/}"
      rest="${rest%%#*}"
      rest="${rest#"${rest%%[![:space:]]*}"}"
      rest="${rest%"${rest##*[![:space:]]}"}"
      if [[ "$rest" == \"*\" ]]; then
        rest="${rest#\"}"
        rest="${rest%\"}"
      elif [[ "$rest" == \'*\' ]]; then
        rest="${rest#\'}"
        rest="${rest%\'}"
      fi
      printf '%s' "$rest"
      return 0
    fi
  done < "$file"
}

HOST="${HA_SAMBA_HOST:-$(_get_scalar "$DEPLOY" ha_samba_host)}"
HA_URL="${HA_API_URL:-$(_get_scalar "$DEPLOY" ha_api_url)}"
USER="${HA_SAMBA_USERNAME:-$(_get_scalar "$SECRETS" ha_samba_username)}"
PASS="${HA_SAMBA_PASSWORD:-$(_get_scalar "$SECRETS" ha_samba_password)}"
TOKEN="${HA_API_TOKEN:-$(_get_scalar "$SECRETS" ha_api_token)}"

if [[ -z "$HOST" ]]; then
  echo "Set ha_samba_host in deploy.local.yaml (or HA_SAMBA_HOST)." >&2
  exit 1
fi
if [[ -z "$HA_URL" ]]; then
  echo "Set ha_api_url in deploy.local.yaml (or HA_API_URL)." >&2
  exit 1
fi
if [[ -z "$USER" || -z "$PASS" ]]; then
  echo "Set ha_samba_username and ha_samba_password in secrets.yaml (or env)." >&2
  exit 1
fi
if [[ -z "$TOKEN" ]]; then
  echo "Set ha_api_token in secrets.yaml (or HA_API_TOKEN) for restart." >&2
  exit 1
fi

if ! command -v rsync >/dev/null 2>&1; then
  echo "rsync not found." >&2
  exit 1
fi
if ! command -v smbclient >/dev/null 2>&1; then
  echo "smbclient not found. On macOS: brew install samba" >&2
  exit 1
fi
if ! command -v curl >/dev/null 2>&1; then
  echo "curl not found." >&2
  exit 1
fi

SRC="$ROOT/custom_components/dewarmte"
if [[ ! -d "$SRC" ]]; then
  echo "Missing integration directory: $SRC" >&2
  exit 1
fi

if [[ -z "${SMB_CONF_PATH:-}" ]]; then
  if [[ -f "/opt/homebrew/etc/smb.conf" ]]; then
    export SMB_CONF_PATH="/opt/homebrew/etc/smb.conf"
  else
    export SMB_CONF_PATH="/dev/null"
  fi
fi

if [[ "$HOST" == *.local ]]; then
  echo "Note: mDNS hostnames sometimes fail SMB; try the IP in ha_samba_host if needed." >&2
fi

# Stage a clean tree (exclude macOS/bytecode junk), then one recursive mput — quiet (-q) and
# filter harmless "directory already exists" noise on stderr.
echo "Uploading custom_components/dewarmte to //$HOST/$SMB_SHARE ..."
STAGE=$(mktemp -d)
cleanup_stage() { rm -rf "$STAGE"; }
trap cleanup_stage EXIT

rsync -a --delete \
  --exclude '.DS_Store' --exclude '__pycache__' --exclude '*.pyc' --exclude '._*' --exclude 'Thumbs.db' \
  "$SRC/" "$STAGE/dewarmte/"

set +e
smbclient "//$HOST/$SMB_SHARE" -U "${USER}%${PASS}" -m SMB3 -q \
  -c "lcd \"$STAGE\"; cd custom_components; recurse; prompt; mput dewarmte" \
  2> >(grep -v 'NT_STATUS_OBJECT_NAME_COLLISION' >&2)
smb_rc=$?
set -e

if [[ "$smb_rc" -ne 0 ]]; then
  echo "smbclient failed (exit $smb_rc)." >&2
  exit 1
fi

# homeassistant.restart stops Core; reverse proxies often return 502/503/504 or close the
# connection before curl gets a 200 — that still means the restart was triggered.
echo "Restarting Home Assistant..."
curl_rc=0
code=$(
  curl -sS -m 120 -o /dev/null -w "%{http_code}" \
    -H "Authorization: Bearer ${TOKEN}" \
    -H "Content-Type: application/json" \
    -X POST \
    -d "{}" \
    "${HA_URL%/}/api/services/homeassistant/restart"
) || curl_rc=$?

if [[ "$curl_rc" -eq 0 ]]; then
  case "$code" in
    200|201|204|502|503|504) ;;
    401|403|404)
      echo "Restart API returned HTTP $code — check ha_api_url and ha_api_token." >&2
      exit 1
      ;;
    *)
      echo "Restart API returned HTTP $code — verify Core restarted in the UI." >&2
      exit 1
      ;;
  esac
elif [[ "$curl_rc" -eq 52 || "$curl_rc" -eq 56 ]]; then
  echo "Connection closed while Core restarted (curl exit $curl_rc) — this is common."
else
  echo "curl failed (exit $curl_rc) calling restart." >&2
  exit 1
fi

echo "Done. Give Home Assistant a minute to finish restarting."
