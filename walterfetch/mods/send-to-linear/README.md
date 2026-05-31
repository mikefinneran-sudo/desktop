# Send to Linear

Phase B Zen mod that captures the active tab title and URL, then posts them to `http://127.0.0.1:8787/linear`. The helper creates a real Linear issue.

## Credentials (no secret in the repo)

The helper reads `LINEAR_API_KEY` from its environment (populated by `creds refresh`) — it is never hardcoded and never fetched via a direct `op` call. Because launchd does not inherit that env, **start the helper with `scripts/start-helper.sh`** (run from a shell where `creds refresh` has run) when you want Linear capture to work. If the key is absent, `/linear` returns HTTP 503 with a message telling you to run `creds refresh`.

Defaults: new issues go to the WalterSignal team (`LINEAR_TEAM_ID`), team default state. Override with env vars `LINEAR_TEAM_ID`, `LINEAR_STATE_ID`, `LINEAR_PROJECT_ID`.

## Manual Install

1. Start the local helper with `bash walterfetch/scripts/start-helper.sh`.
2. Open `about:debugging#/runtime/this-firefox` in Zen.
3. Click "Load Temporary Add-on".
4. Select `walterfetch/mods/send-to-linear/manifest.json`.

Use the toolbar button or `Alt+Shift+L`. On success the notification reports the new issue identifier (e.g. `WAL-366`); verified end-to-end during WAL-364 validation.
