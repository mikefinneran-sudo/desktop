#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

log() {
  printf '[zen-ops] %s\n' "$*"
}

die() {
  printf '[zen-ops] ERROR: %s\n' "$*" >&2
  exit 1
}

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_dir="$(cd -- "$script_dir/../.." && pwd)"

zen_app="${ZEN_APP:-/Applications/Zen.app}"
ops_profile="${ZEN_OPS_PROFILE:-$HOME/Library/Application Support/zen/Profiles/walterfetch-ops}"
debug_port="${ZEN_OPS_DEBUG_PORT:-9333}"
dgx_base="${DGX_BASE_URL:-http://192.168.68.62:8000}"
dgx_fallback="${DGX_FALLBACK_URL:-http://100.114.213.8:8000}"
helper_port="${WF_HELPER_PORT:-8787}"
helper_expected="${WALTERFETCH_HELPER_EXPECTED:-1}"

case "$helper_expected" in
  0|false|False|FALSE|no|No|NO)
    dashboard_url=""
    ;;
  *)
    dashboard_url="${WALTERFETCH_DASHBOARD_URL:-http://127.0.0.1:$helper_port/dashboard}"
    ;;
esac

# 9222 is the Chrome/Chromium remote-debugging port used by the WalterFetch
# enrichment scraper. Refuse it so the Zen ops browser can never collide.
[[ "$debug_port" != "9222" ]] || die "ZEN_OPS_DEBUG_PORT must not be 9222 (reserved for the enrichment scraper)."
[[ -d "$zen_app" ]] || die "Zen app not found at $zen_app. Set ZEN_APP=/path/to/Zen.app and retry."

mkdir -p "$ops_profile"

# Seed prefs into a fresh ops profile so it inherits the bundle's vertical/compact
# UI instead of launching as a bare first-run profile. Never clobber existing prefs.
prefs_src="$repo_dir/walterfetch/prefs/user.js"
if [[ ! -f "$ops_profile/user.js" ]] && [[ -f "$prefs_src" ]]; then
  cp -p "$prefs_src" "$ops_profile/user.js"
  log "Seeded ops profile prefs -> $ops_profile/user.js"
fi

dgx_models_url="${dgx_base%/}"
if [[ "$dgx_models_url" == */v1 ]]; then
  dgx_models_url="$dgx_models_url/models"
else
  dgx_models_url="$dgx_models_url/v1/models"
fi

dgx_fallback_models_url="${dgx_fallback%/}"
if [[ "$dgx_fallback_models_url" == */v1 ]]; then
  dgx_fallback_models_url="$dgx_fallback_models_url/models"
else
  dgx_fallback_models_url="$dgx_fallback_models_url/v1/models"
fi

log "DGX health check: $dgx_models_url"
if ! curl -fsS --max-time 5 "$dgx_models_url"; then
  printf '\n'
  log "Primary DGX endpoint unavailable, trying fallback: $dgx_fallback_models_url"
  curl -fsS --max-time 5 "$dgx_fallback_models_url" || log "DGX health check failed; continuing to launch Zen."
fi
printf '\n'

log "Launching Zen ops profile at $ops_profile"
if [[ -n "$dashboard_url" ]]; then
  log "Dashboard URL: $dashboard_url"
  open -na "$zen_app" --args \
    --profile "$ops_profile" \
    --remote-debugging-port="$debug_port" \
    "$dashboard_url"
else
  log "Helper dashboard not expected; launching without a dashboard tab."
  open -na "$zen_app" --args \
    --profile "$ops_profile" \
    --remote-debugging-port="$debug_port"
fi

cat <<EOF

Optional ~/.zshrc alias:
alias zen-ops='bash "$repo_dir/walterfetch/scripts/zen-ops.sh"'
EOF
