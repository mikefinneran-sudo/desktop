#!/usr/bin/env bash
# Start the WalterFetch Zen helper with credentials from the current shell.
# Use this instead of the launchd agent when you want the Linear-send mod to work,
# because launchd does not inherit the env vars that `creds refresh` populates.
set -euo pipefail
IFS=$'\n\t'

log() { printf '[start-helper] %s\n' "$*"; }

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
helper="$script_dir/../helper/server.py"

[[ -f "$helper" ]] || { printf '[start-helper] ERROR: missing %s\n' "$helper" >&2; exit 1; }

if [[ -z "${LINEAR_API_KEY:-}" ]]; then
  log "LINEAR_API_KEY is not set — the Linear-send mod will return 503 until it is."
  log "Run 'creds refresh' in this shell first if you want Linear capture to work."
fi

log "Clip target: ${WALTERFETCH_RESEARCH_DIR:-$HOME/Desktop/Daily Working Files/Research}"
log "DGX: ${DGX_BASE_URL:-http://192.168.68.62:8000/v1}"
log "Listening on http://127.0.0.1:${WF_HELPER_PORT:-8787} (loopback only)"
exec python3 "$helper" --host 127.0.0.1 --port "${WF_HELPER_PORT:-8787}"
