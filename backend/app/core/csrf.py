"""CSRF double-submit cookie middleware.

Pure ASGI middleware (not BaseHTTPMiddleware) to keep parity with
SecurityHeadersMiddleware and avoid thread/task boundaries around the
request-scoped asyncpg session.

For state-changing methods (anything other than GET/HEAD/OPTIONS) the
client must echo the `csrf_token` cookie in the `X-CSRF-Token` header.
If either is missing, or the two do not match under a constant-time
comparison, the request is rejected with 403 before reaching the app.

Exempt paths (exact match) bypass the check entirely — use sparingly,
only for endpoints where there is no session to protect yet
(e.g. /auth/login, /auth/register) or a trivial health probe.
"""
from __future__ import annotations

import json
import secrets
from collections.abc import Iterable
from http.cookies import SimpleCookie

from starlette.types import ASGIApp, Receive, Scope, Send

_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
_DEFAULT_EXEMPT_PATHS = frozenset({
    "/auth/login", "/auth/register", "/health",
    "/auth/forgot-password", "/auth/reset-password",
    "/consent/decide",
    "/parent/auth/request",
    "/tutor/chat",
})
# Path prefixes that bypass CSRF (for dynamic segments like /consent/request/{id})
_DEFAULT_EXEMPT_PREFIXES = ("/consent/request/",)


class CSRFMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        exempt_paths: Iterable[str] | None = None,
        exempt_prefixes: Iterable[str] | None = None,
        cookie_name: str = "csrf_token",
        header_name: str = "x-csrf-token",
    ) -> None:
        self.app = app
        self.exempt_paths = frozenset(exempt_paths) if exempt_paths is not None else _DEFAULT_EXEMPT_PATHS
        self.exempt_prefixes = tuple(exempt_prefixes) if exempt_prefixes is not None else _DEFAULT_EXEMPT_PREFIXES
        self.cookie_name = cookie_name
        self.header_name = header_name.lower().encode("latin-1")

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "GET").upper()
        if method in _SAFE_METHODS:
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if path in self.exempt_paths or any(path.startswith(p) for p in self.exempt_prefixes):
            await self.app(scope, receive, send)
            return

        headers = scope.get("headers", [])
        cookie_header = b""
        header_token = b""
        for name, value in headers:
            if name == b"cookie":
                cookie_header = value
            elif name == self.header_name:
                header_token = value

        cookie_token = ""
        if cookie_header:
            jar: SimpleCookie = SimpleCookie()
            try:
                jar.load(cookie_header.decode("latin-1"))
            except Exception:
                jar = SimpleCookie()
            morsel = jar.get(self.cookie_name)
            if morsel is not None:
                cookie_token = morsel.value

        header_token_str = header_token.decode("latin-1") if header_token else ""

        if not cookie_token or not header_token_str or not secrets.compare_digest(
            cookie_token, header_token_str
        ):
            await self._reject(send)
            return

        await self.app(scope, receive, send)

    async def _reject(self, send: Send) -> None:
        body = json.dumps({"detail": "CSRF validation failed"}).encode("utf-8")
        await send(
            {
                "type": "http.response.start",
                "status": 403,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode("latin-1")),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})
