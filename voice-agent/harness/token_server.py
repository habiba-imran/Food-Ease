"""Harness static file server + deprecated /token shim.

Tokens for new clients: orchestration `POST http://127.0.0.1:8090/v1/session`
(see orchestration/docs/BRINGUP.md). This process only serves harness HTML/JS on :8080.

Deprecated GET /token proxies to the session API for one release (user token only).
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

from dotenv import load_dotenv

load_dotenv()

SESSION_API = os.environ.get("SESSION_API_URL", "http://127.0.0.1:8090").rstrip("/")


def _session_user_token(identity: str, room: str) -> dict[str, str]:
    """Deprecated shim: mint via orchestration session API."""
    payload = json.dumps(
        {
            "consent": True,
            "room": room,
            "user_identity": identity,
            "include_app_token": False,
        }
    ).encode()
    req = urllib.request.Request(
        f"{SESSION_API}/v1/session",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310 — localhost demo
        body = json.loads(resp.read().decode())
    user = body.get("user") or {}
    return {
        "url": body["livekit_url"],
        "token": user["token"],
        "room": body["room"],
        "session_id": body.get("session_id", ""),
        "deprecated": "Use POST /v1/session on foodease-session (:8090)",
    }


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:  # noqa: A003
        print(f"{self.address_string()} {self.command} {self.path.split('?', 1)[0]}")

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path in {"/", "/index.html"}:
            self._file("index.html", "text/html; charset=utf-8")
            return
        if parsed.path == "/app.js":
            self._file("app.js", "application/javascript; charset=utf-8")
            return
        if parsed.path == "/token":
            # Deprecated — harness app.js calls orchestration directly.
            qs = parse_qs(parsed.query)
            identity = (qs.get("identity") or ["harness-user"])[0]
            room = (qs.get("room") or ["foodease-demo"])[0]
            try:
                body = json.dumps(_session_user_token(identity, room)).encode()
            except (urllib.error.URLError, KeyError, TimeoutError) as exc:
                msg = (
                    f"session API unreachable at {SESSION_API} "
                    f"(start: cd orchestration && uv run foodease-session): {exc}"
                ).encode()
                self.send_response(502)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Content-Length", str(len(msg)))
                self.end_headers()
                self.wfile.write(msg)
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_error(404)

    def _file(self, name: str, content_type: str) -> None:
        path = os.path.join(os.path.dirname(__file__), name)
        with open(path, "rb") as f:
            data = f.read()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def main() -> None:
    port = int(os.environ.get("HARNESS_PORT", "8080"))
    server = HTTPServer(("127.0.0.1", port), Handler)
    print(f"harness listening on http://127.0.0.1:{port}")
    print(f"tokens via orchestration {SESSION_API} (GET /token is deprecated shim)")
    server.serve_forever()


if __name__ == "__main__":
    main()
