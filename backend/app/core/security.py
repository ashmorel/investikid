import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import HTTPException, Request, status
from jose import JWTError, jwt

from app.core.config import settings

_ph = PasswordHasher()

# Pre-computed at import time so dummy_verify() runs in constant time on
# every call (no hashing work during a login miss).
_DUMMY_HASH = _ph.hash("dummy_password_for_timing")


def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return _ph.verify(hashed, plain)
    except VerifyMismatchError:
        return False


def dummy_verify() -> None:
    """Run a verify against a pre-computed dummy hash to equalise timing
    between the 'user not found' and 'wrong password' paths.
    """
    try:
        _ph.verify(_DUMMY_HASH, "dummy_password_for_timing_mismatch")
    except VerifyMismatchError:
        pass


def create_token(data: dict[str, Any], expires_delta: timedelta) -> str:
    payload = data.copy()
    payload["exp"] = datetime.now(UTC) + expires_delta
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str, expected_type: str | None = None) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        ) from exc

    token_type = payload.get("type")
    if expected_type is not None:
        if token_type != expected_type:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type"
            )
    else:
        # No specific type requested == an access token is expected. Positively
        # require type == "access" so that refresh tokens, one-time tokens
        # (consent/verify/reset/parent-magic) or any other claims-only JWT
        # signed with the app secret cannot be substituted for a session.
        if token_type != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type"
            )
    return payload


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def get_token_from_cookie(request: Request) -> str:
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )
    return token
