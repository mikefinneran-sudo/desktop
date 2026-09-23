#!/usr/bin/env python3
"""Create the WalterFetch client workspaces in Zen and pin their tabs.

Drives Zen via Marionette (Firefox's built-in chrome-level automation), calling
Zen's own gZenWorkspaces API + gBrowser.pinTab — no fragile GUI clicking and no
hand-editing of the compressed session store.

Each workspace is bound to a container (userContextId) so its tabs get an
isolated cookie jar — that is what separates the Google accounts. Container IDs
must already exist in the profile's containers.json (seeded separately).

Usage:
  python3 setup-workspaces.py --profile "/path/to/Profiles/xxxx"          # apply
  python3 setup-workspaces.py --profile "/tmp/scratch" --create-profile   # test
Zen must NOT be running on the target profile.
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

ZEN_APP = os.environ.get("ZEN_APP", "/Applications/Zen.app")
ZEN_BIN = f"{ZEN_APP}/Contents/MacOS/zen"
MARIONETTE_PORT = 2828

# name, icon (emoji or undefined), containerTabId (userContextId), pinned URLs
WORKSPACES = [
    ("WalterSignal", "💼", 6, [
        "https://linear.app", "https://mail.google.com",
        "https://waltersignal.io", "https://gamma.app",
    ]),
    ("Ascend", "✈️", 7, [
        "https://app.hubspot.com", "https://app.asana.com", "https://app.fireflies.ai",
    ]),
    ("ABC Cleaning", "🧹", 8, [
        "https://vercel.com/dashboard", "https://alwaysbecleaning.com", "https://mail.google.com",
    ]),
    ("Research", "🔬", 9, [
        "https://www.perplexity.ai", "https://scholar.google.com", "https://arxiv.org",
    ]),
    # Personal: no pinned tabs by default — do not assume specific sites.
    ("Personal", "🏠", 10, []),
]


class Marionette:
    """Minimal Marionette client (length-prefixed JSON framing)."""

    def __init__(self, host="127.0.0.1", port=MARIONETTE_PORT, timeout=60):
        self.sock = socket.create_connection((host, port), timeout=timeout)
        self.sock.settimeout(timeout)
        self.buf = b""
        self._recv()  # server handshake
        self._msgid = 0

    def _recv(self):
        while b":" not in self.buf:
            self.buf += self.sock.recv(65536)
        length, _, self.buf = self.buf.partition(b":")
        need = int(length)
        while len(self.buf) < need:
            self.buf += self.sock.recv(65536)
        payload, self.buf = self.buf[:need], self.buf[need:]
        return json.loads(payload.decode("utf-8"))

    def cmd(self, name, params=None):
        self._msgid += 1
        msg = [0, self._msgid, name, params or {}]
        data = json.dumps(msg).encode("utf-8")
        self.sock.sendall(f"{len(data)}:".encode() + data)
        resp = self._recv()
        # response framing: [1, msgid, error, result]
        if isinstance(resp, list) and len(resp) >= 4:
            _, _, error, result = resp[0], resp[1], resp[2], resp[3]
            if error:
                raise RuntimeError(f"{name} error: {error}")
            return result
        return resp

    def new_session(self):
        return self.cmd("WebDriver:NewSession", {"capabilities": {}})

    def set_chrome(self):
        return self.cmd("Marionette:SetContext", {"value": "chrome"})

    def execute_async(self, script, args=None, timeout_ms=120000):
        self.cmd("WebDriver:SetTimeouts", {"script": timeout_ms})
        return self.cmd("WebDriver:ExecuteAsyncScript", {
            "script": script, "args": args or [], "newSandbox": False,
        })


CHROME_SCRIPT = r"""
const specs = arguments[0];
const resolve = arguments[arguments.length - 1];
(async () => {
  const out = { created: [], pinned: {}, errors: [] };
  try {
    await gZenWorkspaces.promiseInitialized;
    const existing = new Set(gZenWorkspaces.getWorkspaces().map(w => w.name));
    for (const s of specs) {
      try {
        if (!existing.has(s.name)) {
          await gZenWorkspaces.createAndSaveWorkspace(s.name, s.icon, true, s.container);
        }
        const ws = gZenWorkspaces.getWorkspaces().find(w => w.name === s.name);
        out.created.push({ name: s.name, uuid: ws && ws.uuid, container: ws && ws.containerTabId });
        // Switch to the workspace so newly opened tabs are tagged to it, then pin.
        let n = 0;
        if (ws) {
          await gZenWorkspaces.changeWorkspace(ws);
          for (const url of s.urls) {
            const tab = gBrowser.addTrustedTab(url, { userContextId: s.container, skipAnimation: true });
            gBrowser.pinTab(tab);
            n++;
          }
        }
        out.pinned[s.name] = n;
      } catch (e) {
        out.errors.push(s.name + ": " + (e && e.message ? e.message : String(e)));
      }
    }
  } catch (e) {
    out.errors.push("init: " + (e && e.message ? e.message : String(e)));
  }
  resolve(out);
})();
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", required=True)
    ap.add_argument("--create-profile", action="store_true",
                    help="mkdir the profile dir first (for scratch testing)")
    ap.add_argument("--gui", action="store_true", help="show the window (disable headless)")
    args = ap.parse_args()
    args.headless = not args.gui

    profile = Path(args.profile)
    if args.create_profile:
        profile.mkdir(parents=True, exist_ok=True)
    if not profile.is_dir():
        sys.exit(f"Profile dir not found: {profile}")

    cmd = [ZEN_BIN, "--marionette", "-remote-allow-system-access",
           "--no-remote", "--profile", str(profile)]
    if args.headless:
        cmd.append("--headless")
    print(f"launching: {' '.join(cmd)}")
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        # wait for marionette port
        deadline = time.time() + 75
        client = None
        while time.time() < deadline:
            try:
                client = Marionette()
                break
            except OSError:
                time.sleep(1)
        if client is None:
            sys.exit("Marionette did not come up on :2828")
        client.new_session()
        client.set_chrome()
        client.sock.settimeout(200)  # must exceed the 120s script timeout
        specs = [{"name": n, "icon": i, "container": c, "urls": u} for (n, i, c, u) in WORKSPACES]
        result = client.execute_async(CHROME_SCRIPT, [specs])
        print(json.dumps(result, indent=2))
        # give Zen a moment to persist the session store before quitting
        time.sleep(3)
        try:
            client.cmd("Marionette:Quit", {"flags": ["eForceQuit"]})
        except Exception:
            pass
    finally:
        time.sleep(2)
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()


if __name__ == "__main__":
    main()
