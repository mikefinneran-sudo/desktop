# WalterFetch Zen Bundle

This is a versioned config/mods bundle for Mike's stock Zen Browser install. It is not a Firefox or Zen source build. It installs enterprise policies, profile prefs, CSS, local helper scripts, and optional temporary mods on top of the release app.

## What It Installs

- `policies/policies.json`: disables telemetry/studies/Pocket/sponsored/recommended surfaces, disables Firefox hosted AI surfaces, force-installs uBlock Origin, 1Password, and Firefox Multi-Account Containers, and adds the placeholder SearXNG engine.
- `prefs/user.js`: enables legacy profile CSS, Zen vertical tabs, compact mode, split-view prefs, containers, dense UI defaults, and first-run skips.
- `chrome/userChrome.css` and `chrome/userContent.css`: compact dark UI polish for Zen chrome and built-in pages.
- `scripts/zen-ops.sh`: launches a dedicated ops profile on debug port `9333`, opens the dashboard placeholder, and checks DGX health.
- `helper/server.py`: local-only Phase B helper at `127.0.0.1:8787`.
- `mods/*`: independent temporary WebExtension-style mods for DGX summary, clipping research, and the Linear stub.

## Install

From repo root:

```sh
bash walterfetch/scripts/install.sh
```

The installer detects the active Zen profile from:

```sh
~/Library/Application Support/zen/profiles.ini
```

It installs app policies into:

```sh
/Applications/Zen.app/Contents/Resources/distribution/policies.json
```

Override paths when needed:

```sh
ZEN_APP=/Applications/Zen.app \
ZEN_PROFILE_ROOT="$HOME/Library/Application Support/zen" \
bash walterfetch/scripts/install.sh
```

Existing `user.js`, `chrome/`, and app `policies.json` are backed up adjacent to the original path with a timestamped `.bak` suffix. Replaced directories are moved aside as `.bak`; no installer path uses `rm`.

## Verify

- Restart Zen.
- Open `about:policies` and confirm the policies are active.
- Open `about:addons` and confirm uBlock Origin, 1Password, and Multi-Account Containers are present.
- Confirm `about:config` has `toolkit.legacyUserProfileCustomizations.stylesheets = true`.
- Confirm vertical tabs and compact mode are active.

## Zen Ops Launcher

```sh
bash walterfetch/scripts/zen-ops.sh
```

Set one of these before using it for real:

```sh
export HETZNER_HOST="example-host"
# or
export WALTERFETCH_DASHBOARD_URL="http://example-host:8002/v3/dashboard"
```

The launcher prints an alias snippet for `~/.zshrc`; it does not edit shell config.

## Uninstall

```sh
bash walterfetch/scripts/uninstall.sh
```

The uninstaller restores the latest adjacent `.bak` files where present. If the current policy file matches this bundle and no earlier backup exists, it moves that policy file to Trash.

## Phase B Helper

Run manually:

```sh
python3 walterfetch/helper/server.py
```

Health check:

```sh
curl -s http://127.0.0.1:8787/health
```

Launchd install:

```sh
mkdir -p "$HOME/Library/LaunchAgents"
cp walterfetch/helper/com.waltersignal.zenhelper.plist "$HOME/Library/LaunchAgents/"
launchctl bootstrap "gui/$(id -u)" "$HOME/Library/LaunchAgents/com.waltersignal.zenhelper.plist"
launchctl kickstart -k "gui/$(id -u)/com.waltersignal.zenhelper"
```

Launchd unload:

```sh
launchctl bootout "gui/$(id -u)/com.waltersignal.zenhelper"
trash "$HOME/Library/LaunchAgents/com.waltersignal.zenhelper.plist"
```

If the repo moves, update the absolute paths inside `helper/com.waltersignal.zenhelper.plist` before loading it.

## Phase B Mods

Each mod can be skipped without breaking the rest of the bundle.

- `mods/dgx-sidebar`: sidebar panel sends active page text to `/dgx/summarize`.
- `mods/clip-to-research`: toolbar/context/hotkey sends selected text to `/clip`.
- `mods/send-to-linear`: toolbar/hotkey sends active tab title and URL to `/linear`, which is intentionally a stub.

Manual temporary install:

1. Open `about:debugging#/runtime/this-firefox`.
2. Click "Load Temporary Add-on".
3. Select the mod's `manifest.json`.

Persistent install/signing is intentionally left for a later decision.

## Workspace Setup

Follow `workspaces/SETUP.md`. Workspaces, pinned tabs, and container assignments live in Zen profile state and are documented rather than scripted.

## Verification Notes

Zen pref keys were verified locally in this repo:

- Vertical tabs: `prefs/zen/zen.yaml`, `src/zen/common/modules/ZenUIManager.mjs`.
- Compact mode: `prefs/zen/compact-mode.yaml`, `src/zen/compact-mode/ZenCompactMode.mjs`.
- Split view: `prefs/zen/split-view.yaml`, `src/zen/split-view/ZenViewSplitter.mjs`.
- Welcome screen skip: `prefs/zen/welcome.yaml`, `src/zen/common/modules/ZenStartup.mjs`.

Policy structure and macOS `policies.json` placement follow Mozilla Firefox Enterprise policy docs. Extension IDs/install URLs checked:

- uBlock Origin: `uBlock0@raymondhill.net`, AMO latest URL.
- 1Password: `{d634138d-c276-4fc8-924b-40a0ea21d284}`, 1Password deployment docs.
- Firefox Multi-Account Containers: `@testpilot-containers`, Mozilla/AMO references.

## Open TODOs

- Replace the SearXNG placeholder URL in `policies/policies.json`.
- Set the real Hetzner dashboard host or `WALTERFETCH_DASHBOARD_URL`.
- Decide blank homepage/newtab versus WalterSignal dashboard.
- Decide whether and how to wire Linear token handling.
