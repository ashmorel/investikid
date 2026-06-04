import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

import httpx
from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTError

from app.core.config import settings

GOOGLE_ISSUERS = {"https://accounts.google.com", "accounts.google.com"}
GOOGLE_JWKS_URL = "https://www.googleapis.com/oauth2/v3/certs"
APPLE_ISSUERS = {"https://appleid.apple.com"}
APPLE_JWKS_URL = "https://appleid.apple.com/auth/keys"

_JWKS_TTL = 3600
_jwks_cache: dict[str, tuple[float, dict]] = {}

# Pinned signature algorithms (Google = RS256; Apple = ES256/RS256). We never
# honour the `alg` advertised by a JWKS entry — that would enable algorithm
# confusion (e.g. forcing HS256 against the public key).
_ALLOWED_ALGORITHMS = ["RS256", "ES256"]


class OidcError(Exception): ...
class OidcInvalid(OidcError): ...
class OidcExpired(OidcError): ...
class OidcAudienceMismatch(OidcError): ...
class OidcNonceMismatch(OidcError): ...
class OidcNotConfigured(OidcError): ...


@dataclass
class VerifiedIdentity:
    sub: str
    email: str | None
    email_verified: bool


def _provider_config(provider: str) -> tuple[set[str], str, set[str]]:
    if provider == "google":
        auds = {a for a in (settings.google_web_client_id, settings.google_ios_client_id) if a}
        return GOOGLE_ISSUERS, GOOGLE_JWKS_URL, auds
    if provider == "apple":
        auds = {a for a in (settings.apple_services_id, settings.apple_bundle_id) if a}
        return APPLE_ISSUERS, APPLE_JWKS_URL, auds
    raise OidcInvalid(f"unknown provider: {provider}")


async def _http_fetch(url: str) -> dict:
    async with httpx.AsyncClient(timeout=5.0) as c:
        r = await c.get(url)
        r.raise_for_status()
        return r.json()


async def _get_jwks(url: str, fetch: Callable[[str], Awaitable[dict]] | None) -> dict:
    # Bypass cache when an injected fetch is provided (tests + isolation)
    if fetch is not None:
        return await fetch(url)
    now = time.time()
    cached = _jwks_cache.get(url)
    if cached and cached[0] > now:
        return cached[1]
    data = await _http_fetch(url)
    _jwks_cache[url] = (now + _JWKS_TTL, data)
    return data


async def verify_id_token(
    provider: str,
    id_token: str,
    nonce: str,
    *,
    jwks_fetch: Callable[[str], Awaitable[dict]] | None = None,
) -> VerifiedIdentity:
    if not nonce:
        raise OidcInvalid("nonce must not be empty")
    issuers, jwks_url, auds = _provider_config(provider)
    if not auds:
        raise OidcNotConfigured(provider)
    jwks = await _get_jwks(jwks_url, jwks_fetch)
    try:
        header = jwt.get_unverified_header(id_token)
    except JWTError as exc:
        raise OidcInvalid(f"bad header: {exc}") from exc
    key = next((k for k in jwks.get("keys", []) if k.get("kid") == header.get("kid")), None)
    if key is None:
        raise OidcInvalid("no matching JWKS key")
    try:
        # Pin algorithms to an asymmetric allowlist — never trust the JWKS
        # entry's `alg` (a poisoned JWKS could otherwise force HS256 and let a
        # forged token verify against the public key as an HMAC secret).
        payload = jwt.decode(
            id_token, key, algorithms=_ALLOWED_ALGORITHMS,
            options={"verify_aud": False},
        )
    except ExpiredSignatureError as exc:
        raise OidcExpired() from exc
    except JWTError as exc:
        raise OidcInvalid(str(exc)) from exc
    if payload.get("iss") not in issuers:
        raise OidcInvalid("issuer mismatch")
    # `aud` may be a string or a list per RFC 7519 — accept either.
    aud_val = payload.get("aud")
    aud_set = {aud_val} if isinstance(aud_val, str) else set(aud_val or [])
    if not aud_set & auds:
        raise OidcAudienceMismatch()
    if payload.get("nonce") != nonce:
        raise OidcNonceMismatch()
    ev = payload.get("email_verified")
    if isinstance(ev, str):
        ev = ev.lower() == "true"
    return VerifiedIdentity(sub=payload["sub"], email=payload.get("email"), email_verified=bool(ev))
