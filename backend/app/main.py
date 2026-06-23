
import asyncio
import logging
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.config import settings
from app.core.csrf import CSRFMiddleware
from app.core.rate_limit import limiter
from app.routers import admin as admin_router
from app.routers import admin_analytics as admin_analytics_router
from app.routers import ai as ai_router
from app.routers import analytics as analytics_router
from app.routers import arcade as arcade_router
from app.routers import arcade_words_admin as arcade_words_admin_router
from app.routers import auth as auth_router
from app.routers import billing as billing_router
from app.routers import consent as consent_router
from app.routers import content as content_router
from app.routers import cosmetics as cosmetics_router
from app.routers import feedback as feedback_router
from app.routers import gamification as gamification_router
from app.routers import groups as groups_router
from app.routers import internal as internal_router
from app.routers import markets as markets_router
from app.routers import missions as missions_router
from app.routers import parent as parent_router
from app.routers import parent_auth as parent_auth_router
from app.routers import premium as premium_router
from app.routers import revise as revise_router
from app.routers import simulator as simulator_router
from app.routers import users as users_router
from app.routers import video_curation as video_curation_router
from app.services.alerting import on_all_providers_down, on_provider_degraded
from app.services.llm_client import LLMError, set_failure_hook


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


logger = logging.getLogger(__name__)


async def _llm_error_handler(request: Request, exc: LLMError) -> JSONResponse:
    """Surface LLM/provider failures as a friendly 503 instead of a raw 500."""
    # Log the underlying provider error (status/message) for diagnosis. The
    # provider error string never contains the API key (keys are passed as
    # headers, not interpolated into messages — see audit LLM-05).
    logger.warning("LLM request to %s failed: %s", request.url.path, exc)
    try:
        asyncio.create_task(on_all_providers_down(str(exc), request.url.path))
    except RuntimeError:
        pass
    return JSONResponse(
        status_code=503,
        content={"detail": "The AI helper is unavailable right now. Please try again in a moment."},
    )


def warm_price_cache(provider=None) -> None:
    """Prime the market-movers cache (and featured quotes) for all regions.

    Best-effort: every failure is logged and swallowed so a Yahoo outage can
    never affect startup.
    """
    if provider is None:
        from app.routers.simulator import _price_provider

        provider = _price_provider
    for region in ("US", "GB", "HK"):
        try:
            provider.get_market_movers(region)
        except Exception:
            logger.warning("price cache warm failed for region %s", region)


@asynccontextmanager
async def lifespan(application: FastAPI):
    # Fire-and-forget cache warm; daemon thread so it never delays startup.
    threading.Thread(target=warm_price_cache, name="price-warm", daemon=True).start()
    yield


def create_app() -> FastAPI:
    application = FastAPI(title="InvestiKid API", version="1.0.0", lifespan=lifespan)
    application.state.limiter = limiter
    application.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    application.add_exception_handler(LLMError, _llm_error_handler)
    set_failure_hook(on_provider_degraded)

    # Middleware execution order note: add_middleware wraps the app, so the
    # LAST middleware added runs OUTERMOST (first on request, last on response).
    # We want CORS outermost (preflight handling, CORS headers on errors),
    # CSRF next (reject state-changing requests early), and
    # SecurityHeaders innermost so its response hook observes and augments
    # every response — including the 403 from CSRF and any CORS-handled
    # responses that pass through the stack.
    # Known first-party frontends are always allowed (native app + hosted web),
    # merged with any extra origins from CORS_ORIGINS. Baking these in means the
    # app keeps working regardless of env-var drift between deploys.
    _baseline_origins = {
        "capacitor://localhost",
        "https://localhost",
        "https://app.investikid.ai",
        "https://lee-local-code-repo.vercel.app",
    }
    _env_origins = {o.strip() for o in settings.cors_origins.split(",") if o.strip()}
    application.add_middleware(SecurityHeadersMiddleware, environment=settings.environment)
    application.add_middleware(CSRFMiddleware)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=sorted(_baseline_origins | _env_origins),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE"],
        allow_headers=["Content-Type", "X-CSRF-Token", "Authorization", "X-Device-Id"],
    )

    @application.get("/health")
    async def health():
        return JSONResponse({"status": "ok"})

    application.include_router(auth_router.router)
    application.include_router(users_router.router)
    application.include_router(markets_router.router)
    application.include_router(content_router.router)
    application.include_router(cosmetics_router.router)
    application.include_router(consent_router.router)
    application.include_router(gamification_router.router)
    application.include_router(groups_router.router)
    application.include_router(simulator_router.router)
    application.include_router(missions_router.router)
    application.include_router(parent_auth_router.router)
    application.include_router(parent_router.router)
    application.include_router(ai_router.router)
    application.include_router(revise_router.router)
    application.include_router(premium_router.router)
    application.include_router(billing_router.router)
    application.include_router(admin_router.router)
    application.include_router(admin_analytics_router.router)
    application.include_router(video_curation_router.router)
    application.include_router(arcade_words_admin_router.router)
    application.include_router(feedback_router.router)
    application.include_router(feedback_router.admin_router)
    application.include_router(feedback_router.parent_feedback_router)
    application.include_router(analytics_router.router)
    application.include_router(internal_router.router)
    application.include_router(arcade_router.router)

    return application


app = create_app()
