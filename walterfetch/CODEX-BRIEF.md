# Codex Brief — Zen Browser config bundle ("perfect browser for our needs")

**Repo:** `~/Code/zen-desktop` (fork of `zen-browser/desktop`, base Firefox 151.0.2 / Zen 1.20.1b)
**Branch:** `walterfetch-bundle` (already created and checked out — do NOT commit to `dev`).
**Working dir:** all bundle code lives under `walterfetch/` (skeleton already scaffolded). Leave the upstream tree untouched.
**Mode:** plan first, then build. This is a *config/mods bundle layered on stock Zen* — **DO NOT build Firefox from source.** No `surfer build`, no `npm run init`. Everything ships as declarative config + CSS + JS mods + helper scripts that install into the running Zen profile.
**Owner:** Mike Finneran (solo operator). macOS, Apple Silicon (aarch64). Stock Zen release build at `/Applications/Zen.app`. Install script must auto-detect the active profile under `~/Library/Application Support/zen/Profiles/`.

---

## Goal
A versioned bundle in this repo that turns a stock Zen install into Mike's purpose-built browser with **one `git pull` + one install command**. Reproducible across machines.

## Hard constraints (do not violate)
1. **No source build.** Mod/pref/CSS/extension layer only. Binary rebrand/fingerprint is explicitly OUT of scope.
2. **Do not touch the WalterFetch enrichment scraper.** The Chrome/Comet CDP path (`~/Code/walterfetch-browser`, `connect_over_cdp` on port **9222**) stays exactly as is. The Zen ops launcher must use a **different debug port: 9333** so it can never collide with the live Chrome scraper. Nothing in this bundle may reference or modify `~/Code/walterfetch-browser`.
3. **Local models only** for any AI feature. DGX vLLM is OpenAI-compatible at `http://192.168.68.62:8000/v1` (Tailscale fallback `http://100.114.213.8:8000/v1`), model id `Intel/Qwen3.5-122B-A10B-int4-AutoRound`. No paid APIs, ever.
4. **No secrets in the repo or git history.** Account/1Password logins happen interactively in-browser. No tokens hardcoded.
5. Install script is **idempotent and safe**: detect profile, back up any overwritten file to `*.bak`, use `trash` (not `rm`), fail fast with clear errors, fully re-runnable.
6. Follow Mike's script-quality standards: error handling, clear logging, no silent failures.

## Bundle structure (skeleton already created — fill it in)
```
walterfetch/
  CODEX-BRIEF.md                  # this file
  README.md                       # NEW — what it is, install, per-machine setup, uninstall, TODO list
  policies/policies.json          # Firefox Enterprise Policies (declarative defaults)
  prefs/user.js                   # profile prefs
  chrome/userChrome.css           # UI restyle
  chrome/userContent.css          # page-level tweaks
  mods/dgx-sidebar/               # Phase B
  mods/clip-to-research/          # Phase B
  mods/send-to-linear/            # Phase B
  helper/server.py                # Phase B — localhost helper, stdlib only, bind 127.0.0.1:8787
  scripts/install.sh              # copy policies+prefs+chrome into profile, enable legacy stylesheets
  scripts/uninstall.sh
  scripts/zen-ops.sh              # launch Zen: --remote-debugging-port=9333 + ops profile + dashboard + DGX health
  workspaces/SETUP.md             # manual workspace + container setup (stateful, documented not scripted)
```

## Phase A — declarative layer (do FIRST, zero risk)
**policies/policies.json** (Firefox Enterprise Policies — clean declarative path):
- `DisableTelemetry`, `DisableFirefoxStudies`, `DisablePocket`, disable sponsored/"recommended" tiles, `NoDefaultBookmarks`.
- Force-install extensions (`ExtensionSettings` / `Extensions.Install`): uBlock Origin, 1Password, Firefox Multi-Account Containers.
- `SearchEngines`: add Mike's SearXNG as an OpenSearch engine and set default. Use placeholder `https://SEARXNG_URL/search?q={searchTerms}` and flag it as a required TODO — **do not invent an endpoint.**
- Homepage/newtab: leave a clearly-marked TODO (blank vs. WalterSignal dashboard — Mike's call).

**prefs/user.js:**
- `toolkit.legacyUserProfileCustomizations.stylesheets = true`.
- Zen vertical tabs + compact mode + split-view defaults (research the correct `zen.*` pref keys; verify against this Zen version, do not guess key names — cite where you confirmed them).
- Skip first-run / what's-new.

**chrome/userChrome.css + userContent.css:** vertical-tab emphasis, compact chrome, dense dark UI. Minimal, commented.

**scripts/install.sh:** detect active profile; back up existing `user.js` and `chrome/`; copy bundle in; drop `policies.json` into `/Applications/Zen.app/Contents/Resources/distribution/policies.json` (back up first); print next steps + the open TODOs.

**scripts/zen-ops.sh:** launch Zen with `--remote-debugging-port=9333` + dedicated ops profile; open the WalterFetch dashboard tab (host is a TODO — Mike to confirm Hetzner host, default `http://<HETZNER_HOST>:8002/v3/dashboard`); run and echo `curl -s http://192.168.68.62:8000/v1/models`. Print a `~/.zshrc` alias snippet (`alias zen-ops=...`) but DO NOT auto-edit zshrc.

**workspaces/SETUP.md:** documented manual steps to create 6 workspaces, pin sites, assign containers (this state lives in the profile DB and is not cleanly scriptable):

| Workspace | Pinned tabs | Container/account |
|---|---|---|
| WalterFetch Ops | LinkedIn, Sales Nav, WalterFetch dashboard, DGX health | ops profile (debug 9333) |
| WalterSignal | Linear, Cairn, Gmail mike@, waltersignal.io, Gamma, Substack | mike@ |
| Ascend | HubSpot, Asana, Fireflies, Ascend tools, commission sheet | Ascend Google |
| ABC Cleaning | Vercel, site, Gmail | nrwalker@ (real, not the alias) |
| Research | CASCADE, Perplexity, Scholar, arXiv | isolated |
| Personal | TillerBot/banking, CryptoBot, crypto | personal |

## Phase B — JS mods + localhost helper (AFTER Phase A installs cleanly)
Browser JS can't write files or reach DGX cross-origin, so a tiny **local-only helper** backs the mods:
**helper/server.py** — Python stdlib (`http.server`), bind `127.0.0.1:8787` only:
- `POST /clip` → write `{title,url,selection|markdown}` to `~/Desktop/Daily Working Files/Research/<slug>.md` with YAML frontmatter (later drained by `/ingest`).
- `POST /dgx/summarize` → proxy page text to DGX `/v1/chat/completions` (model above), return summary text.
- `POST /linear` → documented stub; Linear token handling is Mike's decision (do NOT hardcode a token).
- Ship `helper/com.waltersignal.zenhelper.plist` launchd agent + document load/unload.

**mods/dgx-sidebar:** Zen sidebar/web-panel that sends current page text to `127.0.0.1:8787/dgx/summarize` and renders the summary.
**mods/clip-to-research:** toolbar button / hotkey → POST selection to `/clip`.
**mods/send-to-linear:** capture tab title+url → POST `/linear` (stub until token decided).
Each mod independent, with its own README (Sine or manual userChrome-JS install). Any mod can be skipped without breaking the others.

## Acceptance criteria
- `bash walterfetch/scripts/install.sh` on a clean Zen profile is idempotent, backs up overwrites, and leaves Zen launching with telemetry/pocket/sponsored off, vertical+compact UI, the 3 extensions present, and userChrome applied.
- `bash walterfetch/scripts/zen-ops.sh` launches on port **9333** (never 9222), opens the dashboard tab, prints the DGX model list.
- Phase B helper runs local-only; `/clip` writes a valid frontmatter file to the Research inbox; `/dgx/summarize` returns text from the local model.
- `README.md` documents install, the open TODOs Mike must fill, and uninstall.
- Nothing in the diff references `~/Code/walterfetch-browser` or port 9222.

## Open items — flag in README, DO NOT guess
1. Real SearXNG endpoint URL (Mike runs `searxng_query` in walter-tools).
2. Hetzner dashboard host for the ops tab.
3. Homepage/newtab choice.
4. Whether to wire Linear send (needs an API-token decision).

## Deliverables
1. Short plan (file list + order) before building.
2. Phase A implemented and self-tested where possible (lint JSON, shellcheck scripts).
3. Phase B implemented.
4. `README.md` with install/uninstall/TODOs.
5. Commit on `walterfetch-bundle` with a clear message. Do NOT push or open a PR unless asked.
