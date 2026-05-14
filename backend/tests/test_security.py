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
