# DGX Sidebar

Temporary/Phase B Zen mod that opens a sidebar panel, extracts the active page text, posts it to `http://127.0.0.1:8787/dgx/summarize`, and renders the local DGX summary.

## Requirements

- `python3 walterfetch/helper/server.py` running locally, or the launchd agent loaded.
- The helper must stay bound to `127.0.0.1:8787`.
- DGX vLLM reachable at the configured local endpoint.

## Manual Install

1. Open `about:debugging#/runtime/this-firefox` in Zen.
2. Click "Load Temporary Add-on".
3. Select `walterfetch/mods/dgx-sidebar/manifest.json`.
4. Open the sidebar and choose "WalterFetch DGX".

This is intentionally independent. Removing it does not affect the other mods or Phase A config.
