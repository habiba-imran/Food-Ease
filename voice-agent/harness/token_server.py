"""Minimal token server for the Phase 5 talk client (dev only)."""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

from dotenv import load_dotenv
from livekit.api import AccessToken, VideoGrants

load_dotenv()


def _mint(identity: str, room: str) -> dict[str, str]:
    url = os.environ["LIVEKIT_URL"]
    key = os.environ["LIVEKIT_API_KEY"]
    secret = os.environ["LIVEKIT_API_SECRET"]
    token = (
        AccessToken(key, secret)
        .with_identity(identity)
        .with_name(identity)
        .with_grants(
            VideoGrants(
                room_join=True,
                room=room,
                can_publish=True,
                can_subscribe=True,
                can_publish_data=True,
            )
        )
        .to_jwt()
    )
    return {"url": url, "token": token, "room": room}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:  # noqa: A003
        # Avoid dumping query strings that might contain identities.
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
            qs = parse_qs(parsed.query)
            identity = (qs.get("identity") or ["harness-user"])[0]
            room = (qs.get("room") or ["foodease-demo"])[0]
            try:
                body = json.dumps(_mint(identity, room)).encode()
            except KeyError as exc:
                self.send_error(500, f"missing env: {exc}")
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
    server.serve_forever()


if __name__ == "__main__":
    main()
