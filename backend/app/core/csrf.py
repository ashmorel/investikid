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
    "/auth/login", "/auth/register", "/auth/biometric/exchange", "/parent/auth/biometric/exchange", "/health",
    "/auth/forgot-password", "/auth/reset-password",
    "/consent/decide",
    "/parent/auth/request",
    "/billing/webhook",
    "/billing/apple/notifications",
    "/billing/google/notifications",
    "/internal/video-health/run",
    "/internal/trial-reminders/run",
    "/internal/weekly-digest/run",
    "/internal/analytics-retention/run",
    "/internal/push-streak-risk/run",
    "/internal/subscriptions/reconcile",
    "/internal/purge-archived-modules",
    "/internal/purge-accounts/run",
    "/internal/market-content",
    "/internal/video-candidates/extract",
    "/internal/collectables/reconcile",
    "/parent/auth/oauth/google",
    "/parent/auth/oauth/apple",
})
# Path prefixes that bypass CSRF (for dynamic segments like /consent/request/{id})
_DEFAULT_EXEMPT_PREFIXES = ("/consent/request/",)

# First-party frontend origins (native app + hosted web). Trusting our own
# origins is a sound CSRF defence (OWASP-recommended) for this cross-domain
# SPA + API setup: the frontend domain (app.investikid.ai) cannot read the API
# domain's (railway) csrf cookie, so the double-submit header can never be sent.
# Browsers cannot forge the Origin header and no malicious site can claim these
# origins; a non-browser client could spoof Origin but lacks the victim's auth
# cookies — so this does not weaken protection. Kept in sync with CORS_ORIGINS.
_BASELINE_TRUSTED_ORIGINS = frozenset({
    "capacitor://localhost",
    "https://localhost",
    "https://app.investikid.ai",
    "https://lee-local-code-repo.vercel.app",
})


def _trusted_origins() -> frozenset[bytes]:
    from app.core.config import settings
    env = {o.strip() for o in settings.cors_origins.split(",") if o.strip()}
    return frozenset(o.encode("latin-1") for o in (_BASELINE_TRUSTED_ORIGINS | env))


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
        self.trusted_origins = _trusted_origins()

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
        origin = b""
        native_app = False
        for name, value in headers:
            if name == b"cookie":
                cookie_header = value
            elif name == self.header_name:
                header_token = value
            elif name == b"origin":
                origin = value
            elif name == b"x-capacitor-app":
                native_app = True

        # Native app traffic: identified by a custom header the native HTTP
        # layer sends (its Origin is unreliable). Browsers cannot add a custom
        # header cross-site without a CORS preflight, which the server denies
        # for untrusted origins — so this cannot be forged by a malicious site.
        if native_app:
            await self.app(scope, receive, send)
            return

        # Requests from a trusted first-party origin bypass the double-submit
        # check (origin-based CSRF defence) — see _BASELINE_TRUSTED_ORIGINS.
        if origin and origin in self.trusted_origins:
            await self.app(scope, receive, send)
            return

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
