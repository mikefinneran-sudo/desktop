#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

log() {
  printf '[walterfetch-uninstall] %s\n' "$*"
}

die() {
  printf '[walterfetch-uninstall] ERROR: %s\n' "$*" >&2
  exit 1
}

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
bundle_dir="$(cd -- "$script_dir/.." && pwd)"
timestamp="$(date +%Y%m%d-%H%M%S)"

zen_app="${ZEN_APP:-/Applications/Zen.app}"
profile_root="${ZEN_PROFILE_ROOT:-$HOME/Library/Application Support/zen}"
profiles_ini="$profile_root/profiles.ini"
policy_src="$bundle_dir/policies/policies.json"

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

detect_profile() {
  [[ -f "$profiles_ini" ]] || die "Missing profiles.ini: $profiles_ini"

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
        if (chosen_path != "") {
          print chosen_path "\t" chosen_isrel
        } else if (install_path != "") {
          print install_path "\t" install_isrel
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

latest_backup() {
  local pattern="$1"
  find "$(dirname "$pattern")" -maxdepth 1 -name "$(basename "$pattern")" -print 2>/dev/null | sort -r | head -n 1
}

backup_current() {
  local target="$1"
  [[ -e "$target" ]] || return 0

  local backup="$target.uninstall-current.$timestamp.bak"
  mv "$target" "$backup"
  log "Moved current $target -> $backup"
}

restore_file() {
  local target="$1"
  local pattern="$2"
  local backup
  backup="$(latest_backup "$pattern")"

  if [[ -z "$backup" ]]; then
    log "No backup found for $target; leaving current file untouched."
    return
  fi

  backup_current "$target"
  cp -p "$backup" "$target"
  log "Restored $target from $backup"
}

restore_dir() {
  local target="$1"
  local pattern="$2"
  local backup
  backup="$(latest_backup "$pattern")"

  if [[ -z "$backup" ]]; then
    log "No backup found for $target; leaving current directory untouched."
    return
  fi

  backup_current "$target"
  cp -pR "$backup" "$target"
  log "Restored $target from $backup"
}

restore_policies() {
  local policy_dest="$zen_app/Contents/Resources/distribution/policies.json"
  local backup
  backup="$(latest_backup "$policy_dest.*.bak")"

  if [[ -n "$backup" ]]; then
    backup_current "$policy_dest"
    cp -p "$backup" "$policy_dest"
    log "Restored policies from $backup"
    return
  fi

  if [[ -f "$policy_dest" ]] && [[ -f "$policy_src" ]] && cmp -s "$policy_dest" "$policy_src"; then
    backup_current "$policy_dest"
    trash_path "$policy_dest"
    log "Removed WalterFetch policies; no earlier policy backup existed."
    return
  fi

  log "No policy backup found, or current policies differ from the bundle; leaving $policy_dest untouched."
}

main() {
  local profile
  profile="$(detect_profile)"
  [[ -d "$profile" ]] || die "Detected profile does not exist: $profile"

  log "Detected active Zen profile: $profile"
  restore_file "$profile/user.js" "$profile/user.js.*.bak"
  restore_dir "$profile/chrome" "$profile/chrome.*.bak"

  if [[ -d "$zen_app" ]]; then
    restore_policies
  else
    log "Zen app not found at $zen_app; skipping app policy restore."
  fi

  # Remove the opt-in durable system copy if it matches this bundle.
  local sys_dest="/Library/Application Support/Mozilla/policies/policies.json"
  if [[ -f "$sys_dest" ]] && [[ -f "$policy_src" ]] && cmp -s "$sys_dest" "$policy_src"; then
    if [[ -w "$(dirname "$sys_dest")" ]]; then
      backup_current "$sys_dest"
      trash_path "$sys_dest"
      log "Removed durable policies at $sys_dest"
    else
      log "Durable policies present at $sys_dest but not writable; re-run with sudo to remove."
    fi
  fi
}

main "$@"
