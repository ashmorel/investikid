"""The rate limiter must key authenticated requests per-user, not per-IP —
behind Railway's proxy all clients can share one IP, so IP-only keying would
make every user share one bucket (the beta-breaking 429 storm)."""

from types import SimpleNamespace

from jose import jwt as jose_jwt

from app.core.rate_limit import rate_limit_key


def _request(cookies=None, host="203.0.113.7"):
    return SimpleNamespace(
        cookies=cookies or {},
        client=SimpleNamespace(host=host),
        headers={},
    )


def test_authenticated_request_keys_on_user_sub():
    token = jose_jwt.encode({"sub": "user-123", "type": "access"}, "k", algorithm="HS256")
    assert rate_limit_key(_request({"access_token": token})) == "user:user-123"


def test_two_users_same_ip_get_distinct_keys():
    a = jose_jwt.encode({"sub": "a"}, "k", algorithm="HS256")
    b = jose_jwt.encode({"sub": "b"}, "k", algorithm="HS256")
    ka = rate_limit_key(_request({"access_token": a}, host="10.0.0.1"))
    kb = rate_limit_key(_request({"access_token": b}, host="10.0.0.1"))
    assert ka != kb


def test_unauthenticated_request_falls_back_to_ip():
    assert rate_limit_key(_request()) == "203.0.113.7"


def test_malformed_token_falls_back_to_ip():
    assert rate_limit_key(_request({"access_token": "not-a-jwt"})) == "203.0.113.7"


def test_token_without_sub_falls_back_to_ip():
    token = jose_jwt.encode({"type": "access"}, "k", algorithm="HS256")
    assert rate_limit_key(_request({"access_token": token})) == "203.0.113.7"
