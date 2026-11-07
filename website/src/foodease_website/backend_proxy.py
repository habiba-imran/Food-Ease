"""Fixed-upstream same-origin gateway for the Vercel frontend; never owns cart state."""

from __future__ import annotations

from urllib.parse import urlsplit

import httpx
from foodease_contract.models import MAX_WIRE_BYTES
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class BackendProxy(BaseHTTPMiddleware):
    def __init__(self, app, *, backend_url: str, transport=None):
        super().__init__(app)
        parsed = urlsplit(backend_url)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or parsed.path not in {"", "/"}
        ):
            raise ValueError(
                "FOODEASE_BACKEND_URL must be an HTTPS origin without credentials or path"
            )
        self.backend_url = backend_url.rstrip("/")
        self.transport = transport

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        is_session = path.startswith("/assist/v2/")
        if not (
            is_session
            or path.startswith("/api/v2/app/")
            or path == "/api/v2/app/context"
            or path.startswith("/api/catalog/")
        ):
            return await call_next(request)
        if request.method not in {"GET", "POST", "OPTIONS"}:
            return JSONResponse({"error": "method_not_allowed"}, status_code=405)
        origin = request.headers.get("origin")
        public_origin = f"{request.url.scheme}://{request.url.netloc}"
        if origin and origin != public_origin:
            return JSONResponse({"error": "unauthorized_origin"}, status_code=403)
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > MAX_WIRE_BYTES:
                return JSONResponse({"error": "payload_too_large"}, status_code=413)
        headers = {
            name: request.headers[name]
            for name in (
                "content-type",
                "x-foodease-session",
                "x-foodease-event-id",
                "x-foodease-worker-proof",
                "access-control-request-method",
                "access-control-request-headers",
            )
            if name in request.headers
        }
        if owner := request.cookies.get("foodease_owner"):
            headers["cookie"] = "foodease_owner=" + owner
        if origin:
            # Validate caller first, then adapt to the upstream website's same-origin check.
            headers["origin"] = public_origin if is_session else self.backend_url
        try:
            async with httpx.AsyncClient(
                timeout=15, follow_redirects=False, trust_env=False, transport=self.transport
            ) as client:
                result = await client.request(
                    request.method,
                    self.backend_url + path,
                    params=request.query_params,
                    content=bytes(body),
                    headers=headers,
                )
        except httpx.HTTPError:
            # Never retry an application mutation after an uncertain transport outcome.
            return JSONResponse(
                {"error": "backend_unavailable_check_cart_before_retry"},
                status_code=503,
                headers={"Cache-Control": "no-store"},
            )
        if 300 <= result.status_code < 400:
            return JSONResponse({"error": "backend_redirect_rejected"}, status_code=502)
        response = Response(
            result.content,
            status_code=result.status_code,
            headers={
                "Content-Type": result.headers.get("content-type", "application/json"),
                "Cache-Control": "no-store",
            },
        )
        for cookie in result.headers.get_list("set-cookie"):
            if cookie.startswith("foodease_owner="):
                response.headers.append("set-cookie", cookie)
        return response
