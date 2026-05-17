from datetime import timedelta

import pytest
from fastapi import HTTPException

from app.core.security import create_token, decode_token, hash_password, verify_password


def test_hash_and_verify_password():
    hashed = hash_password("secret123")
    assert hashed != "secret123"
    assert verify_password("secret123", hashed)
    assert not verify_password("wrong", hashed)


def test_create_and_decode_access_token():
    token = create_token({"sub": "user-123"}, expires_delta=timedelta(minutes=15))
    payload = decode_token(token)
    assert payload["sub"] == "user-123"


def test_expired_token_raises():
    token = create_token({"sub": "user-123"}, expires_delta=timedelta(seconds=-1))
    with pytest.raises(HTTPException) as exc_info:
        decode_token(token)
    assert exc_info.value.status_code == 401


def test_jose_version_not_vulnerable():
    import importlib.metadata as md

    from packaging.version import Version
    v = Version(md.version("python-jose"))
    assert v >= Version("3.4.0"), f"python-jose {v} is CVE-vulnerable (<3.4.0)"


def test_jwt_decode_rejects_token_signed_with_wrong_secret():
    from jose import jwt

    from app.core.config import settings

    bad = jwt.encode({"sub": "x"}, "not-the-secret", algorithm=settings.jwt_algorithm)
    with pytest.raises(HTTPException) as exc_info:
        decode_token(bad)
    assert exc_info.value.status_code == 401
