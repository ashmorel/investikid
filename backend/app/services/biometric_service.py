"""Opaque biometric credential issuance/verification (SP-Bio).

The ONLY module that touches biometric_credentials. Secret = 256-bit random,
stored as SHA-256 (high-entropy → no bcrypt), rotated on each successful verify,
device-bound and revocable.
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import delete, select, update

from app.models.biometric import BiometricCredential

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession

CREDENTIAL_TTL = timedelta(days=90)


def _hash(secret: str) -> str:
    return hashlib.sha256(secret.encode()).hexdigest()


def subject_key_for_child(user_id) -> str:
    return f"child:{user_id}"


def subject_key_for_parent(email: str) -> str:
    return f"parent:{email.lower()}"


async def issue(
    session: AsyncSession,
    *,
    subject_kind: str,
    user_id: uuid.UUID | None,
    parent_email: str | None,
    device_id: str,
    label: str,
) -> str:
    """Create (replacing any existing for this device+subject) and return a fresh
    plaintext secret. The caller stores it in the biometric keychain."""
    email = parent_email.lower() if parent_email else None
    key = (
        subject_key_for_child(user_id)
        if subject_kind == "child"
        else subject_key_for_parent(email or "")
    )
    await session.execute(
        delete(BiometricCredential).where(
            BiometricCredential.device_id == device_id,
            BiometricCredential.subject_key == key,
        )
    )
    secret = secrets.token_urlsafe(32)
    session.add(
        BiometricCredential(
            subject_kind=subject_kind,
            user_id=user_id,
            parent_email=email,
            subject_key=key,
            device_id=device_id,
            label=label[:60],
            secret_hash=_hash(secret),
            expires_at=datetime.now(UTC) + CREDENTIAL_TTL,
        )
    )
    return secret


async def verify_and_rotate(
    session: AsyncSession, *, device_id: str, secret: str
) -> BiometricCredential | None:
    """Validate a presented secret for a device; on success rotate it and stamp
    last_used_at. Returns the row (with a transient ``last_secret`` attribute =
    the new plaintext) or None. NEVER raises for a bad secret."""
    now = datetime.now(UTC)
    row = await session.scalar(
        select(BiometricCredential).where(
            BiometricCredential.device_id == device_id,
            BiometricCredential.secret_hash == _hash(secret),
            BiometricCredential.revoked_at.is_(None),
            BiometricCredential.expires_at > now,
        )
    )
    if row is None:
        return None
    new_secret = secrets.token_urlsafe(32)
    row.secret_hash = _hash(new_secret)
    row.last_used_at = now
    row.last_secret = new_secret  # transient; the endpoint returns it to the client
    await session.flush()
    return row


async def revoke_subject(session: AsyncSession, *, subject_key: str) -> int:
    result = await session.execute(
        update(BiometricCredential)
        .where(
            BiometricCredential.subject_key == subject_key,
            BiometricCredential.revoked_at.is_(None),
        )
        .values(revoked_at=datetime.now(UTC))
    )
    return result.rowcount or 0


async def revoke_device(session: AsyncSession, *, subject_key: str, device_id: str) -> int:
    result = await session.execute(
        update(BiometricCredential)
        .where(
            BiometricCredential.subject_key == subject_key,
            BiometricCredential.device_id == device_id,
            BiometricCredential.revoked_at.is_(None),
        )
        .values(revoked_at=datetime.now(UTC))
    )
    return result.rowcount or 0
