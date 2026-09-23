#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

log() {
  printf '[walterfetch-install] %s\n' "$*"
}

die() {
  printf '[walterfetch-install] ERROR: %s\n' "$*" >&2
  exit 1
}

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
bundle_dir="$(cd -- "$script_dir/.." && pwd)"
timestamp="$(date +%Y%m%d-%H%M%S)"

zen_app="${ZEN_APP:-/Applications/Zen.app}"
profile_root="${ZEN_PROFILE_ROOT:-$HOME/Library/Application Support/zen}"
profiles_ini="$profile_root/profiles.ini"

policy_src="$bundle_dir/policies/policies.json"
prefs_src="$bundle_dir/prefs/user.js"
chrome_src="$bundle_dir/chrome"

require_file() {
  [[ -f "$1" ]] || die "Missing required file: $1"
}

require_dir() {
  [[ -d "$1" ]] || die "Missing required directory: $1"
}

trash_path() {
  local path="$1"
  [[ -e "$path" ]] || return 0

  if command -v trash >/dev/null 2>&1; then
    trash "$path" >/dev/null 2>&1 || true
    if [[ ! -e "$path" ]]; then
      return
    fi
  fi

  if command -v osascript >/dev/null 2>&1; then
    osascript -e 'on run argv' \
      -e 'tell application "Finder" to delete POSIX file (item 1 of argv)' \
      -e 'end run' "$path" >/dev/null 2>&1 || true
    if [[ ! -e "$path" ]]; then
      return
    fi
  fi

  die "Could not move path to Trash: $path"
}

validate_json() {
  if command -v python3 >/dev/null 2>&1; then
    python3 -m json.tool "$policy_src" >/dev/null
  elif command -v plutil >/dev/null 2>&1; then
    plutil -lint "$policy_src" >/dev/null
  else
    die "Need python3 or plutil to validate policies.json"
  fi
}

detect_profile() {
  require_file "$profiles_ini"

  local parsed
  parsed="$(
    awk '
      function flush_profile() {
        if (in_profile && default_profile == "1" && profile_path != "") {
          chosen_path = profile_path
          chosen_isrel = profile_isrel
        }
      }
      BEGIN {
        profile_isrel = "1"
        install_isrel = "1"
      }
      /^\[/ {
        flush_profile()
        in_profile = ($0 ~ /^\[Profile/)
        in_install = ($0 ~ /^\[Install/)
        profile_path = ""
        profile_isrel = "1"
        default_profile = "0"
        next
      }
      in_profile && /^Path=/ {
        profile_path = substr($0, 6)
        next
      }
      in_profile && /^IsRelative=/ {
        profile_isrel = substr($0, 12)
        next
      }
      in_profile && /^Default=1/ {
        default_profile = "1"
        next
      }
      in_install && /^Default=/ {
        install_path = substr($0, 9)
        next
      }
      in_install && /^IsRelative=/ {
        install_isrel = substr($0, 12)
        next
      }
      END {
        flush_profile()
        # Modern Zen/Firefox uses a dedicated profile per install: the [Install]
        # section Default is authoritative for which profile actually launches.
        # The legacy [Profile] Default=1 is only the fallback when no [Install].
        if (install_path != "") {
          print install_path "\t" install_isrel
        } else if (chosen_path != "") {
          print chosen_path "\t" chosen_isrel
        } else {
          exit 1
        }
      }
    ' "$profiles_ini"
  )" || die "Could not find a default profile in $profiles_ini"

  local rel_path is_relative
  rel_path="${parsed%%$'\t'*}"
  is_relative="${parsed##*$'\t'}"

  if [[ "$is_relative" == "1" ]]; then
    printf '%s/%s\n' "$profile_root" "$rel_path"
  else
    printf '%s\n' "$rel_path"
  fi
}

backup_path() {
  local target="$1"
  printf '%s.%s.bak\n' "$target" "$timestamp"
}

backup_existing() {
  local target="$1"
  [[ -e "$target" ]] || return 0

  local backup
  backup="$(backup_path "$target")"
  if [[ -d "$target" ]]; then
    cp -pR "$target" "$backup"
  else
    cp -p "$target" "$backup"
  fi
  log "Backed up $target -> $backup"
}

move_existing_to_backup() {
  local target="$1"
  [[ -e "$target" ]] || return 0

  local backup
  backup="$(backup_path "$target")"
  mv "$target" "$backup"
  log "Moved existing $target -> $backup"
}

install_profile_files() {
  local profile="$1"
  require_dir "$profile"

  backup_existing "$profile/user.js"
  cp -p "$prefs_src" "$profile/user.js"
  log "Installed prefs/user.js -> $profile/user.js"

  move_existing_to_backup "$profile/chrome"
  mkdir -p "$profile/chrome"
  cp -p "$chrome_src/userChrome.css" "$profile/chrome/userChrome.css"
  cp -p "$chrome_src/userContent.css" "$profile/chrome/userContent.css"
  log "Installed chrome CSS -> $profile/chrome"
}

install_policies() {
  [[ -d "$zen_app" ]] || die "Zen app not found at $zen_app. Set ZEN_APP=/path/to/Zen.app and retry."

  local resources_dir="$zen_app/Contents/Resources"
  local distribution_dir="$resources_dir/distribution"
  local policy_dest="$distribution_dir/policies.json"

  [[ -d "$resources_dir" ]] || die "Zen resources directory not found: $resources_dir"

  if [[ ! -d "$distribution_dir" ]]; then
    mkdir -p "$distribution_dir" || die "Cannot create $distribution_dir. Retry with appropriate macOS permissions."
  fi

  [[ -w "$distribution_dir" ]] || die "Cannot write $distribution_dir. Try: sudo env HOME=\"$HOME\" ZEN_PROFILE_ROOT=\"$profile_root\" ZEN_APP=\"$zen_app\" bash \"$script_dir/install.sh\""

  backup_existing "$policy_dest"
  cp -p "$policy_src" "$policy_dest"
  log "Installed policies -> $policy_dest"

  # App-bundle policies are wiped by Zen auto-updates. Opt-in durable copy in
  # the Mozilla system policy dir survives updates (needs sudo once). This path
  # is documented Firefox behavior but unverified for this Zen build, so it is
  # an addition, not a replacement.
  if [[ "${WALTERFETCH_DURABLE_POLICIES:-0}" == "1" ]]; then
    local sys_dir="/Library/Application Support/Mozilla/policies"
    local sys_dest="$sys_dir/policies.json"
    if mkdir -p "$sys_dir" 2>/dev/null && [[ -w "$sys_dir" ]]; then
      backup_existing "$sys_dest"
      cp -p "$policy_src" "$sys_dest"
      log "Installed durable policies -> $sys_dest (survives Zen updates)"
    else
      log "WARNING: cannot write $sys_dir. Re-run as: sudo env HOME=\"$HOME\" WALTERFETCH_DURABLE_POLICIES=1 bash \"$script_dir/install.sh\""
    fi
  fi
}

main() {
  require_file "$policy_src"
  require_file "$prefs_src"
  require_dir "$chrome_src"
  require_file "$chrome_src/userChrome.css"
  require_file "$chrome_src/userContent.css"

  validate_json

  local profile
  profile="$(detect_profile)"
  log "Detected active Zen profile: $profile"

  install_profile_files "$profile"
  install_policies

  cat <<EOF

WalterFetch Zen bundle installed.

Next steps:
  1. Restart Zen and open about:policies to confirm active policies.
  2. Open about:addons to confirm uBlock Origin, 1Password, and Multi-Account Containers.
  3. Default search is SearXNG on the DGX via Tailscale (http://100.114.213.8:8890).
     Requires the Tailscale mesh to be up; falls back to nothing if both Tailscale and
     LAN are unreachable. Edit walterfetch/policies/policies.json to change it.
  4. Confirm homepage/newtab and dashboard host choices in walterfetch/README.md TODOs.
  5. Launch ops mode with: bash "$script_dir/zen-ops.sh"

  NOTE: Zen auto-updates overwrite the app bundle and will WIPE these policies
  (telemetry/sponsored tiles silently return). Re-run this installer after a Zen
  update, OR install the durable copy once with:
    sudo env HOME="$HOME" WALTERFETCH_DURABLE_POLICIES=1 bash "$script_dir/install.sh"
EOF
}

main "$@"
