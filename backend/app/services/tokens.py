import uuid
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.consent import OneTimeToken


CONSENT_AUDIENCE = "consent"
PARENT_MAGIC_AUDIENCE = "parent_magic"
PARENT_SESSION_AUDIENCE = "parent_session"

CONSENT_EXPIRY = timedelta(hours=24)
PARENT_MAGIC_EXPIRY = timedelta(minutes=15)
PARENT_SESSION_EXPIRY = timedelta(days=7)


class TokenInvalid(Exception):
    pass


class TokenExpired(Exception):
    pass


class TokenAlreadyUsed(Exception):
    pass


async def issue_one_time_token(
    session: AsyncSession,
    *,
    purpose: str,
    email: str,
    subject_id: uuid.UUID | None,
    expires_in: timedelta,
) -> str:
    jti = uuid.uuid4()
    now = datetime.now(timezone.utc)
    expires_at = now + expires_in
    record = OneTimeToken(
        jti=jti, purpose=purpose, subject_id=subject_id,
        email=email, issued_at=now, expires_at=expires_at,
    )
    session.add(record)
    await session.flush()

    payload = {
        "jti": str(jti),
        "aud": purpose,
        "sub": str(subject_id) if subject_id else email,
        "exp": expires_at,
        "iat": now,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


async def consume_one_time_token(
    session: AsyncSession, token: str, expected_purpose: str,
) -> OneTimeToken:
    """Verify JWT, atomically mark consumed, return the row."""
    try:
        payload = jwt.decode(
            token, settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            audience=expected_purpose,
        )
    except JWTError as exc:
        raise TokenInvalid(str(exc)) from exc

    try:
        jti = uuid.UUID(payload["jti"])
    except (ValueError, KeyError) as exc:
        raise TokenInvalid("missing jti") from exc

    now = datetime.now(timezone.utc)
    result = await session.execute(
        update(OneTimeToken)
        .where(OneTimeToken.jti == jti, OneTimeToken.consumed_at.is_(None))
        .values(consumed_at=now)
        .returning(OneTimeToken)
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise TokenAlreadyUsed("token already used or unknown")

    if row.expires_at <= now:
        raise TokenExpired("token expired")
    return row


def issue_parent_session(email: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": email,
        "aud": PARENT_SESSION_AUDIENCE,
        "exp": now + PARENT_SESSION_EXPIRY,
        "iat": now,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_parent_session(token: str) -> str:
    """Returns parent email or raises TokenInvalid."""
    try:
        payload = jwt.decode(
            token, settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            audience=PARENT_SESSION_AUDIENCE,
        )
    except JWTError as exc:
        raise TokenInvalid(str(exc)) from exc
    email = payload.get("sub")
    if not email:
        raise TokenInvalid("missing sub")
    return email
