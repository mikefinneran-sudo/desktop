#!/usr/bin/env python3
"""Local-only helper for WalterFetch Zen Phase B mods."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import urllib.error
import urllib.request
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8787
DEFAULT_MODEL = "Intel/Qwen3.5-122B-A10B-int4-AutoRound"
DEFAULT_DGX_BASE = "http://192.168.68.62:8000/v1"
DEFAULT_DGX_FALLBACK = "http://100.114.213.8:8000/v1"
DEFAULT_SEARXNG_URL = "http://100.114.213.8:8890"
DEFAULT_WALTERFETCH_API_URL = "http://100.78.198.105:8002"
MAX_BODY_BYTES = 2_000_000
MAX_SUMMARY_CHARS = 60_000
MAX_STATUS_BYTES = 200_000
STATUS_TIMEOUT = 3.0
DASHBOARD_PATH = Path(__file__).with_name("dashboard.html")


def env_path(name: str, fallback: Path) -> Path:
  return Path(os.environ.get(name, str(fallback))).expanduser()


RESEARCH_DIR = env_path(
  "WALTERFETCH_RESEARCH_DIR",
  Path.home() / "Desktop" / "Daily Working Files" / "Research",
)
DGX_BASE_URL = os.environ.get("DGX_BASE_URL", DEFAULT_DGX_BASE)
DGX_FALLBACK_URL = os.environ.get("DGX_FALLBACK_URL", DEFAULT_DGX_FALLBACK)
DGX_MODEL = os.environ.get("DGX_MODEL", DEFAULT_MODEL)
DGX_TIMEOUT = float(os.environ.get("DGX_TIMEOUT", "60"))
SEARXNG_URL = os.environ.get("SEARXNG_URL", DEFAULT_SEARXNG_URL).rstrip("/")
WALTERFETCH_API_URL = os.environ.get("WALTERFETCH_API_URL", DEFAULT_WALTERFETCH_API_URL).rstrip("/")
WALTERFETCH_RUN_STATUS_URL = os.environ.get("WALTERFETCH_RUN_STATUS_URL", "")
WALTERFETCH_RUN_STATUS_FILE = os.environ.get("WALTERFETCH_RUN_STATUS_FILE", "")

# Linear: the key is read from the environment (populated by `creds refresh`),
# never hardcoded and never via a direct `op` call. Team defaults to WalterSignal;
# state/project are optional (Linear uses the team default state when stateId is omitted).
LINEAR_API_KEY = os.environ.get("LINEAR_API_KEY", "")
LINEAR_API_URL = "https://api.linear.app/graphql"
LINEAR_TEAM_ID = os.environ.get("LINEAR_TEAM_ID", "68ff47d4-6e61-42aa-ad91-858b6858f924")
LINEAR_STATE_ID = os.environ.get("LINEAR_STATE_ID", "")
LINEAR_PROJECT_ID = os.environ.get("LINEAR_PROJECT_ID", "")


def slugify(value: str, fallback: str = "zen-clip") -> str:
  value = value.strip().lower()
  value = re.sub(r"https?://", "", value)
  value = re.sub(r"[^a-z0-9]+", "-", value)
  value = value.strip("-")
  return (value or fallback)[:80]


def yaml_string(value: str) -> str:
  return json.dumps(value or "", ensure_ascii=False)


def unique_path(directory: Path, slug: str) -> Path:
  candidate = directory / f"{slug}.md"
  if not candidate.exists():
    return candidate

  for index in range(1, 1000):
    candidate = directory / f"{slug}-{index}.md"
    if not candidate.exists():
      return candidate

  raise RuntimeError(f"Could not allocate unique file for slug {slug!r}")


def chat_completions_url(base_url: str) -> str:
  base = base_url.rstrip("/")
  if base.endswith("/v1"):
    return f"{base}/chat/completions"
  return f"{base}/v1/chat/completions"


def models_url(base_url: str) -> str:
  base = base_url.rstrip("/")
  if base.endswith("/v1"):
    return f"{base}/models"
  return f"{base}/v1/models"


def post_json(url: str, payload: dict[str, Any], timeout: float) -> dict[str, Any]:
  data = json.dumps(payload).encode("utf-8")
  request = urllib.request.Request(
    url,
    data=data,
    headers={"Content-Type": "application/json", "Accept": "application/json"},
    method="POST",
  )
  with urllib.request.urlopen(request, timeout=timeout) as response:
    return json.loads(response.read().decode("utf-8"))


def get_status_url(url: str, accept: str = "*/*") -> tuple[int, bytes]:
  request = urllib.request.Request(
    url,
    headers={"Accept": accept, "User-Agent": "WalterFetchZenHelper/0.1"},
    method="GET",
  )
  with urllib.request.urlopen(request, timeout=STATUS_TIMEOUT) as response:
    body = response.read(MAX_STATUS_BYTES + 1)
    return int(response.status), body[:MAX_STATUS_BYTES]


def status_error(exc: Exception) -> str:
  if isinstance(exc, urllib.error.HTTPError):
    detail = exc.read(500).decode("utf-8", "replace").strip()
    if detail:
      return f"HTTP {exc.code}: {detail[:200]}"
    return f"HTTP {exc.code}"
  if isinstance(exc, urllib.error.URLError):
    return str(exc.reason)
  return str(exc) or exc.__class__.__name__


def model_ids(payload: bytes) -> list[str]:
  try:
    parsed = json.loads(payload.decode("utf-8"))
  except (UnicodeDecodeError, json.JSONDecodeError):
    return []
  data = parsed.get("data") if isinstance(parsed, dict) else parsed
  if not isinstance(data, list):
    return []
  ids: list[str] = []
  for item in data:
    if isinstance(item, dict) and item.get("id"):
      ids.append(str(item["id"]))
  return ids


def check_dgx() -> dict[str, Any]:
  errors: list[str] = []
  bases = [DGX_BASE_URL]
  if DGX_FALLBACK_URL and DGX_FALLBACK_URL != DGX_BASE_URL:
    bases.append(DGX_FALLBACK_URL)

  for base_url in bases:
    url = models_url(base_url)
    try:
      status, body = get_status_url(url, "application/json")
      ids = model_ids(body)
      if status == 200 and DGX_MODEL in ids:
        return {
          "up": True,
          "detail": "model listed",
          "model": DGX_MODEL,
          "url": url,
        }
      if ids:
        return {
          "up": False,
          "detail": "HTTP 200 but configured model is not listed",
          "model": ids[0],
          "expected_model": DGX_MODEL,
          "url": url,
        }
      return {
        "up": False,
        "detail": "HTTP 200 but no model ids returned",
        "model": DGX_MODEL,
        "url": url,
      }
    except Exception as exc:  # A down DGX must not take down /status.
      errors.append(f"{url}: {status_error(exc)}")

  return {
    "up": False,
    "detail": "; ".join(errors) or "not configured",
    "model": DGX_MODEL,
    "url": models_url(DGX_BASE_URL),
  }


def check_http_service(url: str, accept: str = "*/*") -> dict[str, Any]:
  try:
    status, _ = get_status_url(url, accept)
    return {"up": status == 200, "detail": f"HTTP {status}", "url": url}
  except Exception as exc:
    return {"up": False, "detail": status_error(exc), "url": url}


def parse_run_status(raw: bytes, source: str) -> dict[str, Any]:
  text = raw.decode("utf-8", "replace").strip()
  if not text:
    return {"configured": True, "up": True, "detail": f"{source} returned empty status"}
  try:
    return {
      "configured": True,
      "up": True,
      "detail": f"loaded from {source}",
      "data": json.loads(text),
    }
  except json.JSONDecodeError:
    return {"configured": True, "up": True, "detail": text[:500]}


def run_status() -> dict[str, Any]:
  if WALTERFETCH_RUN_STATUS_URL:
    try:
      status, body = get_status_url(WALTERFETCH_RUN_STATUS_URL, "application/json, text/plain, */*")
      if status != 200:
        return {"configured": True, "up": False, "detail": f"HTTP {status}"}
      return parse_run_status(body, "WALTERFETCH_RUN_STATUS_URL")
    except Exception as exc:
      return {"configured": True, "up": False, "detail": status_error(exc)}

  if WALTERFETCH_RUN_STATUS_FILE:
    path = Path(WALTERFETCH_RUN_STATUS_FILE).expanduser()
    # Trusted local config path (operator-set env var). Require a regular file so
    # this localhost endpoint can't be pointed at a device/FIFO; size is capped below.
    if not path.is_file():
      return {"configured": True, "up": False, "detail": "run status file not found or not a regular file"}
    try:
      with path.open("rb") as status_file:
        body = status_file.read(MAX_STATUS_BYTES + 1)
    except OSError as exc:
      return {"configured": True, "up": False, "detail": str(exc)}
    if len(body) > MAX_STATUS_BYTES:
      return {"configured": True, "up": False, "detail": "run status file is too large"}
    return parse_run_status(body, "WALTERFETCH_RUN_STATUS_FILE")

  return {"configured": False, "up": False, "detail": "not configured"}


def status_report() -> dict[str, Any]:
  return {
    "ok": True,
    "checked_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    "services": {
      "dgx": check_dgx(),
      "searxng": check_http_service(SEARXNG_URL, "text/html, */*"),
      "walterfetch_api": check_http_service(WALTERFETCH_API_URL, "application/json, text/html, */*"),
    },
    "run_progress": run_status(),
  }


def dgx_summary(data: dict[str, Any]) -> str:
  title = str(data.get("title") or "Untitled page")
  url = str(data.get("url") or "")
  text = str(data.get("text") or data.get("selection") or data.get("markdown") or "")
  text = text.strip()[:MAX_SUMMARY_CHARS]
  if not text:
    raise ValueError("No page text supplied.")

  prompt = (
    f"Title: {title}\n"
    f"URL: {url}\n\n"
    f"{text}\n\n"
    "Return a concise operational summary with bullets for key facts, risks, "
    "open questions, and useful follow-up actions. Do not invent facts."
  )
  payload = {
    "model": DGX_MODEL,
    "messages": [
      {
        "role": "system",
        "content": "You summarize browser research for WalterSignal using only supplied page text.",
      },
      {"role": "user", "content": prompt},
    ],
    "temperature": 0.2,
    "max_tokens": 900,
  }

  last_error: Exception | None = None
  for base_url in (DGX_BASE_URL, DGX_FALLBACK_URL):
    try:
      response = post_json(chat_completions_url(base_url), payload, DGX_TIMEOUT)
      return str(response["choices"][0]["message"]["content"]).strip()
    except (KeyError, IndexError, TypeError, urllib.error.URLError, TimeoutError) as exc:
      last_error = exc

  raise RuntimeError(f"DGX summarize request failed: {last_error}")


def linear_create_issue(data: dict[str, Any]) -> dict[str, str]:
  if not LINEAR_API_KEY:
    raise PermissionError(
      "LINEAR_API_KEY not set in the helper environment. Run `creds refresh`, "
      "then restart the helper via scripts/start-helper.sh."
    )

  title = (str(data.get("title") or "Untitled tab").strip() or "Untitled tab")[:250]
  url = str(data.get("url") or "")
  note = str(data.get("note") or data.get("selection") or "")
  description = f"Captured from Zen.\n\nURL: {url}\n"
  if note.strip():
    description += f"\n{note.strip()}\n"

  input_fields: dict[str, Any] = {
    "title": title,
    "teamId": LINEAR_TEAM_ID,
    "description": description,
  }
  if LINEAR_STATE_ID:
    input_fields["stateId"] = LINEAR_STATE_ID
  if LINEAR_PROJECT_ID:
    input_fields["projectId"] = LINEAR_PROJECT_ID

  query = (
    "mutation IssueCreate($input: IssueCreateInput!) { "
    "issueCreate(input: $input) { success issue { identifier url } } }"
  )
  body = json.dumps({"query": query, "variables": {"input": input_fields}}).encode("utf-8")
  request = urllib.request.Request(
    LINEAR_API_URL,
    data=body,
    headers={"Content-Type": "application/json", "Authorization": LINEAR_API_KEY},
    method="POST",
  )
  try:
    with urllib.request.urlopen(request, timeout=20) as response:
      result = json.loads(response.read().decode("utf-8"))
  except urllib.error.HTTPError as exc:
    detail = exc.read().decode("utf-8", "replace")[:500]
    raise RuntimeError(f"Linear API HTTP {exc.code}: {detail}") from exc

  if result.get("errors"):
    messages = "; ".join(str(e.get("message", e)) for e in result["errors"])
    raise RuntimeError(f"Linear API error: {messages}")
  issue = result.get("data", {}).get("issueCreate", {}).get("issue")
  if not issue:
    raise RuntimeError("Linear issueCreate returned no issue.")
  return {"identifier": str(issue["identifier"]), "url": str(issue["url"])}


def write_clip(data: dict[str, Any]) -> Path:
  title = str(data.get("title") or "Untitled")
  url = str(data.get("url") or "")
  body = str(data.get("markdown") or data.get("selection") or "")
  if not body.strip():
    raise ValueError("No selection or markdown supplied.")

  RESEARCH_DIR.mkdir(parents=True, exist_ok=True)
  created = dt.datetime.now(dt.timezone.utc).isoformat()
  slug = slugify(title or url)
  path = unique_path(RESEARCH_DIR, slug)
  # Defense in depth: slugify already strips path separators, but assert the
  # resolved write target never escapes the research directory.
  if path.resolve().parent != RESEARCH_DIR.resolve():
    raise ValueError("Refusing to write outside the research directory.")
  content = (
    "---\n"
    f"title: {yaml_string(title)}\n"
    f"url: {yaml_string(url)}\n"
    f"created: {yaml_string(created)}\n"
    'source: "zen"\n'
    "---\n\n"
    f"# {title}\n\n"
  )
  if url:
    content += f"Source: {url}\n\n"
  content += body.strip() + "\n"

  path.write_text(content, encoding="utf-8")
  return path


class Handler(BaseHTTPRequestHandler):
  server_version = "WalterFetchZenHelper/0.1"

  def _cors_origin(self) -> str | None:
    # Only browser extensions may call this helper. A wildcard ACAO would let
    # any website the user visits POST to /clip (write files) or hit the DGX
    # proxy, since the request originates from the page in the same browser.
    origin = self.headers.get("Origin", "")
    if origin.startswith("moz-extension://"):
      return origin
    return None

  def end_headers(self) -> None:
    origin = self._cors_origin()
    if origin is not None:
      self.send_header("Access-Control-Allow-Origin", origin)
      self.send_header("Vary", "Origin")
      self.send_header("Access-Control-Allow-Headers", "content-type")
      self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    super().end_headers()

  def log_message(self, fmt: str, *args: Any) -> None:
    sys.stderr.write("[%s] %s\n" % (self.log_date_time_string(), fmt % args))

  def do_OPTIONS(self) -> None:  # noqa: N802
    self.send_response(HTTPStatus.NO_CONTENT)
    self.end_headers()

  def do_GET(self) -> None:  # noqa: N802
    if self.path in {"/", "/health"}:
      self.send_json(
        HTTPStatus.OK,
        {
          "ok": True,
          "service": "walterfetch-zen-helper",
          "bind": f"{DEFAULT_HOST}:{DEFAULT_PORT}",
          "research_dir": str(RESEARCH_DIR),
          "dgx_model": DGX_MODEL,
        },
      )
      return
    if self.path == "/status":
      self.send_json(HTTPStatus.OK, status_report())
      return
    if self.path in {"/dashboard", "/dashboard/"}:
      self.send_html(DASHBOARD_PATH)
      return
    self.send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "Not found"})

  def do_POST(self) -> None:  # noqa: N802
    try:
      data = self.read_json()
      if self.path == "/clip":
        path = write_clip(data)
        self.send_json(HTTPStatus.OK, {"ok": True, "path": str(path)})
      elif self.path == "/dgx/summarize":
        summary = dgx_summary(data)
        self.send_json(HTTPStatus.OK, {"ok": True, "summary": summary, "model": DGX_MODEL})
      elif self.path == "/linear":
        issue = linear_create_issue(data)
        self.send_json(HTTPStatus.OK, {"ok": True, "issue": issue})
      else:
        self.send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "Not found"})
    except ValueError as exc:
      self.send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(exc)})
    except PermissionError as exc:
      self.send_json(HTTPStatus.SERVICE_UNAVAILABLE, {"ok": False, "error": str(exc)})
    except Exception as exc:  # Keep helper failures visible to the browser mods.
      self.send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"ok": False, "error": str(exc)})

  def read_json(self) -> dict[str, Any]:
    try:
      length = int(self.headers.get("Content-Length", "0"))
    except ValueError as exc:
      raise ValueError("Invalid Content-Length.") from exc
    if length <= 0:
      raise ValueError("Empty request body.")
    if length > MAX_BODY_BYTES:
      raise ValueError("Request body too large.")

    raw = self.rfile.read(length)
    try:
      data = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as exc:
      raise ValueError(f"Invalid JSON: {exc}") from exc
    if not isinstance(data, dict):
      raise ValueError("JSON body must be an object.")
    return data

  def send_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
    body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    self.send_response(status)
    self.send_header("Content-Type", "application/json; charset=utf-8")
    self.send_header("Content-Length", str(len(body)))
    self.end_headers()
    self.wfile.write(body)

  def send_html(self, path: Path) -> None:
    try:
      body = path.read_bytes()
    except OSError as exc:
      self.send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"ok": False, "error": str(exc)})
      return
    self.send_response(HTTPStatus.OK)
    self.send_header("Content-Type", "text/html; charset=utf-8")
    self.send_header("Content-Length", str(len(body)))
    self.end_headers()
    self.wfile.write(body)


def parse_args() -> argparse.Namespace:
  parser = argparse.ArgumentParser(description="WalterFetch Zen local helper")
  parser.add_argument("--host", default=DEFAULT_HOST)
  parser.add_argument("--port", default=DEFAULT_PORT, type=int)
  return parser.parse_args()


def main() -> None:
  args = parse_args()
  if args.host != DEFAULT_HOST:
    raise SystemExit("Refusing to bind anywhere except 127.0.0.1")

  server = ThreadingHTTPServer((args.host, args.port), Handler)
  print(f"walterfetch helper listening on http://{args.host}:{args.port}", flush=True)
  server.serve_forever()


if __name__ == "__main__":
  main()
