# WalterFetch Zen Workspaces

Zen stores workspaces, pinned tabs, and container site assignment in the profile DB. Treat this as manual per-machine state. The bundle installs the Multi-Account Containers extension and enables container prefs; Mike still needs to create the workspaces and pin/assign sites inside Zen.

## Automated setup (scripts/setup-workspaces.py)

`scripts/setup-workspaces.py` creates the 5 client workspaces, binds each to its
container, and pins its tabs by driving Zen over Marionette (chrome-context
`gZenWorkspaces` API). Zen must not be running on the target profile.

```
python3 walterfetch/scripts/setup-workspaces.py --profile "<profiles>/xxxx.Default"
```

Known limitation: reliable only on a **freshly-initialized profile**. On a profile
with prior session state, `gZenWorkspaces` init blocks under headless Marionette
(script timeout). To configure a clean daily profile: run on a new bare profile,
then seed `containers.json` (ids 6-10) + copy `prefs/user.js` + `chrome/`, then
point `profiles.ini`'s `[Install]` Default at it. Otherwise use the manual steps below.

## Baseline Steps (manual)

1. Run `bash walterfetch/scripts/install.sh`.
2. Restart Zen and confirm Multi-Account Containers is installed.
3. Open the Containers menu and create containers for `mike@`, `outreach@`, `nrwalker@`, `Ascend Google`, `Research`, and `Personal`.
4. Create the six Zen workspaces below.
5. Pin the listed tabs in each workspace.
6. For each pinned site, use Multi-Account Containers to always open that site in the assigned container.

## Workspace Map

| Workspace | Pinned tabs | Container/account |
|---|---|---|
| WalterFetch Ops | LinkedIn, Sales Nav, WalterFetch dashboard, DGX health | Ops profile launched by `zen-ops.sh` on debug port `9333` |
| WalterSignal | Linear, Cairn, Gmail `mike@`, `waltersignal.io`, Gamma, Substack | `mike@` |
| Ascend | HubSpot, Asana, Fireflies, Ascend tools, commission sheet | `Ascend Google` |
| ABC Cleaning | Vercel, site, Gmail | `nrwalker@` real account, not alias |
| Research | CASCADE, Perplexity, Scholar, arXiv | `Research` isolated |
| Personal | TillerBot/banking, CryptoBot, crypto | `Personal` |

## Container Pinning Notes

- Use the container extension's "Always open this site in..." flow for each pinned site.
- Keep Google accounts isolated by container instead of relying on `authuser` URL juggling.
- If a site asks to reopen in its assigned container, accept it and tick the remember option.
- Do not script this state unless Zen exposes a stable import/export surface later.

## Per-Machine TODOs

- Replace the SearXNG placeholder in `walterfetch/policies/policies.json`.
- Set `HETZNER_HOST` or `WALTERFETCH_DASHBOARD_URL` before using `zen-ops.sh`.
- Decide whether homepage/newtab stays blank or points at the WalterSignal dashboard.
- Decide whether the Linear helper should be wired to a local token.
