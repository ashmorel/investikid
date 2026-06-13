from jose import jwt
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings


def rate_limit_key(request) -> str:
    """Per-user key for authenticated requests, client IP otherwise.

    Authenticated routes verify the JWT signature in their auth dependency
    BEFORE the handler (and therefore the limiter wrapper) runs, so reading the
    unverified `sub` here is safe: a forged token 401s without ever consuming a
    bucket. The IP fallback covers pre-auth routes (login/signup/reset) — it
    requires uvicorn to run with --proxy-headers behind Railway's edge proxy,
    otherwise every client resolves to the proxy IP and shares one bucket.
    """
    token = request.cookies.get("access_token")
    if token:
        try:
            sub = jwt.get_unverified_claims(token).get("sub")
            if sub:
                return f"user:{sub}"
        except Exception:  # malformed token → fall through to IP
            pass
    return get_remote_address(request)


def biometric_exchange_key(request) -> str:
    """Per-device key for the cookieless biometric exchange routes.

    The exchange carries no auth cookie, so the default key collapses to the
    proxy IP and shares one bucket across every user behind Railway's edge.
    Keying on the client-sent `X-Device-Id` gives each device its own bucket
    (the feature's natural unit). The 256-bit secret makes brute force
    infeasible regardless, so device-controlled keying only affects DoS
    isolation, not credential strength. Falls back to IP when absent.
    """
    device_id = request.headers.get("X-Device-Id")
    if device_id:
        return f"biodev:{device_id}"
    return get_remote_address(request)


# In development the limiter is disabled so test suites and rapid local iteration
# don't trip per-IP thresholds that exist for production abuse protection.
limiter = Limiter(
    key_func=rate_limit_key,
    enabled=settings.environment != "development",
)
