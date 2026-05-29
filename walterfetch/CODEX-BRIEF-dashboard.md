## Task: WalterFetch ops dashboard in the Zen helper — Linear WAL-366
## Repo: ~/Code/zen-desktop (branch walterfetch-bundle, code under walterfetch/)

Follow-on to WAL-364 (the Zen bundle, already committed). Build a local ops status dashboard INTO the existing helper.

## Context (from Claude)
- The helper is `walterfetch/helper/server.py` — a loopback-only (`127.0.0.1`) stdlib `http.server`. It already serves `GET /health`, `POST /clip`, `POST /dgx/summarize`, `POST /linear`. REUSE its existing patterns (Handler class, send_json, post helpers, env config block).
- Serve the dashboard FROM the helper so it is same-origin (`http://127.0.0.1:8787/dashboard`). This lets health checks for DGX/SearXNG/WalterFetch run SERVER-SIDE — a browser page cannot cross-origin those hosts, but the Python helper can.
- CORS note: the helper only sends Access-Control-Allow-Origin for `moz-extension://` origins. `/dashboard` and `/status` are loaded same-origin (127.0.0.1:8787) so they need no CORS header — do not loosen the existing CORS gate.
- Verified reachable now: DGX `http://192.168.68.62:8000/v1/models` (HTTP 200), SearXNG `http://100.114.213.8:8890` (HTTP 200, returns HTML), WalterFetch API `http://100.78.198.105:8002/` (HTTP 200; `/v3/dashboard` returns 500 — do not depend on that path).

## Constraints
- Helper stays bound to 127.0.0.1 only — do not change the bind guard.
- Do NOT break existing endpoints (/health, /clip, /dgx/summarize, /linear).
- All upstream health checks server-side with SHORT timeouts (~3s each) and try/except so one dead service never hangs or 500s the whole /status. Return per-service {up, detail} objects.
- No secrets. Local models only (DGX). Never reference port 9222 or ~/Code/walterfetch-browser.
- Run-progress is UNKNOWN data — show "not configured" unless a `WALTERFETCH_RUN_STATUS_URL`/file is set. Do NOT fabricate lead counts.
- Plain stdlib + vanilla HTML/JS/CSS. No new dependencies.

## Files (expected — drift check compares diff to this)
- [ ] walterfetch/helper/server.py — modify: add config (SEARXNG_URL default http://100.114.213.8:8890, WALTERFETCH_API_URL default http://100.78.198.105:8002, optional WALTERFETCH_RUN_STATUS_URL); add `status_report()` aggregator; add `GET /status` (JSON) and `GET /dashboard` (serves dashboard.html) routes in do_GET
- [ ] walterfetch/helper/dashboard.html — create: status board, polls /status every ~15s, up/down lights, shows DGX model + last-checked timestamp + run-progress panel ("not configured" when absent)
- [ ] walterfetch/scripts/zen-ops.sh — modify: default the ops dashboard tab to http://127.0.0.1:8787/dashboard (still overridable by WALTERFETCH_DASHBOARD_URL); keep the "launch without tab" path only if the helper isn't expected
- [ ] walterfetch/README.md — modify: document the dashboard, /status shape, and the env vars

## Suspicions / verify
- /status must never hang: use per-request urllib timeouts AND wrap each check; a down host returns {up:false} fast, not an exception that 500s /status.
- SearXNG "health": a plain GET to its base or `/search?q=ping` returns 200 HTML — treat HTTP 200 as up. Don't parse results.
- DGX up = `/v1/models` returns 200 and lists the model; surface the model id.
- Serve dashboard.html with correct Content-Type text/html; read it relative to the helper file path (not cwd).
- zen-ops opens the dashboard tab, but the helper may not be running yet — that's fine (the tab will just fail to load until start-helper.sh runs); note this in README.

## Ask
Plan first (short), then implement. Self-test: py_compile, start the helper, curl /status (JSON with 3 service entries) and /dashboard (HTML 200). Do NOT commit, push, or open a PR — /validate gates the commit.
