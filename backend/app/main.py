from typing import Callable

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.config import settings
from app.core.csrf import CSRFMiddleware
from app.core.rate_limit import limiter
from app.routers import auth as auth_router
from app.routers import consent as consent_router
from app.routers import content as content_router
from app.routers import gamification as gamification_router
from app.routers import parent_auth as parent_auth_router
from app.routers import simulator as simulator_router
from app.routers import users as users_router


class SecurityHeadersMiddleware:
    """Pure ASGI middleware that injects security headers into every response.

    Unlike BaseHTTPMiddleware this does not spawn a background task so it is
    compatible with asyncpg connections shared across a request.
    """

    def __init__(self, app: ASGIApp, environment: str = "production") -> None:
        self.app = app
        self.environment = environment

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message: dict) -> None:
            if message["type"] == "http.response.start":
                # Preserve existing headers including multi-valued ones (e.g., Set-Cookie)
                existing_headers = message.get("headers", [])
                headers_dict = {}
                headers_list = []

                # Add existing headers to the list, preserving multi-valued headers
                for name, value in existing_headers:
                    headers_list.append((name, value))
                    # Track single-valued headers for override checking
                    if name not in (b"set-cookie",):
                        headers_dict[name] = value

                # Add new security headers (these are single-valued)
                headers_dict[b"x-content-type-options"] = b"nosniff"
                headers_dict[b"x-frame-options"] = b"DENY"
                headers_dict[b"referrer-policy"] = b"strict-origin-when-cross-origin"
                headers_dict[b"content-security-policy"] = (
                    b"default-src 'self'; script-src 'self'; "
                    b"style-src 'self' 'unsafe-inline'; "
                    b"img-src 'self' data:; frame-ancestors 'none'"
                )
                if self.environment != "development":
                    headers_dict[b"strict-transport-security"] = (
                        b"max-age=31536000; includeSubDomains"
                    )

                # Replace single-valued headers in the list
                final_headers = []
                added_keys = set()
                for name, value in headers_list:
                    if name not in (b"set-cookie",):
                        # Skip old values of single-valued headers
                        if name not in added_keys:
                            final_headers.append((name, headers_dict.get(name, value)))
                            added_keys.add(name)
                    else:
                        # Preserve multi-valued headers like Set-Cookie
                        final_headers.append((name, value))

                # Add any new headers that weren't in the original list
                for name, value in headers_dict.items():
                    if name not in added_keys:
                        final_headers.append((name, value))

                message = {
                    **message,
                    "headers": final_headers,
                }
            await send(message)

        await self.app(scope, receive, send_with_headers)


def create_app() -> FastAPI:
    application = FastAPI(title="Invest-Ed API", version="1.0.0")
    application.state.limiter = limiter
    application.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # Middleware execution order note: add_middleware wraps the app, so the
    # LAST middleware added runs OUTERMOST (first on request, last on response).
    # We want CORS outermost (preflight handling, CORS headers on errors),
    # CSRF next (reject state-changing requests early), and
    # SecurityHeaders innermost so its response hook observes and augments
    # every response — including the 403 from CSRF and any CORS-handled
    # responses that pass through the stack.
    application.add_middleware(SecurityHeadersMiddleware, environment=settings.environment)
    application.add_middleware(CSRFMiddleware)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=(
            ["http://localhost:5173"] if settings.environment == "development" else []
        ),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Content-Type", "X-CSRF-Token"],
    )

    @application.get("/health")
    async def health():
        return JSONResponse({"status": "ok"})

    application.include_router(auth_router.router)
    application.include_router(users_router.router)
    application.include_router(content_router.router)
    application.include_router(consent_router.router)
    application.include_router(gamification_router.router)
    application.include_router(simulator_router.router)
    application.include_router(parent_auth_router.router)

    return application


app = create_app()
