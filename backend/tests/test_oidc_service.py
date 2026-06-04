import time

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jose import jwk, jwt

from app.services import oidc

pytestmark = pytest.mark.asyncio(loop_scope="session")


def _keypair(kid="test-kid"):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    priv_pem = key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
    ).decode()
    pub_pem = key.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode()
    pub_jwk = jwk.construct(pub_pem, "RS256").to_dict()
    pub_jwk.update({"kid": kid, "alg": "RS256", "use": "sig"})
    return priv_pem, {"keys": [pub_jwk]}, kid


def _token(priv_pem, kid, *, iss, aud, sub="sub-1", email="p@example.com", email_verified=True, nonce="n1", exp_delta=600):
    now = int(time.time())
    return jwt.encode(
        {"iss": iss, "aud": aud, "sub": sub, "email": email, "email_verified": email_verified,
         "nonce": nonce, "iat": now, "exp": now + exp_delta},
        priv_pem, algorithm="RS256", headers={"kid": kid},
    )


def _make_async(d):
    async def f(_url):
        return d
    return f


@pytest.fixture
def google_cfg(monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "google_web_client_id", "web-aud", raising=False)
    monkeypatch.setattr(settings, "google_ios_client_id", "ios-aud", raising=False)


async def _verify(id_token, jwks, nonce="n1", provider="google"):
    return await oidc.verify_id_token(provider, id_token, nonce, jwks_fetch=_make_async(jwks))


@pytest.fixture
def apple_cfg(monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "apple_services_id", "apple-web", raising=False)
    monkeypatch.setattr(settings, "apple_bundle_id", "apple-app", raising=False)


async def test_valid_apple_token_with_string_email_verified(apple_cfg):
    priv, jwks, kid = _keypair()
    tok = _token(priv, kid, iss="https://appleid.apple.com", aud="apple-app", email_verified="true")
    result = await _verify(tok, jwks, provider="apple")
    assert result.sub == "sub-1"
    assert result.email_verified is True


async def test_accepts_list_audience(google_cfg):
    priv, jwks, kid = _keypair()
    tok = _token(priv, kid, iss="https://accounts.google.com", aud=["web-aud", "other"])
    result = await _verify(tok, jwks)
    assert result.sub == "sub-1"


async def test_wrong_issuer(google_cfg):
    priv, jwks, kid = _keypair()
    tok = _token(priv, kid, iss="https://evil.example.com", aud="web-aud")
    with pytest.raises(oidc.OidcInvalid):
        await _verify(tok, jwks)


async def test_empty_nonce_rejected(google_cfg):
    priv, jwks, kid = _keypair()
    tok = _token(priv, kid, iss="https://accounts.google.com", aud="web-aud")
    with pytest.raises(oidc.OidcInvalid):
        await _verify(tok, jwks, nonce="")


async def test_hs256_jwks_algorithm_confusion_rejected(google_cfg):
    """A poisoned JWKS advertising a symmetric HS256 key must not verify."""
    priv, jwks, kid = _keypair()
    # craft an HS256 token and a matching oct JWKS entry under the same kid
    secret = "attacker-known-secret"
    forged = jwt.encode(
        {"iss": "https://accounts.google.com", "aud": "web-aud", "sub": "evil",
         "nonce": "n1", "exp": int(time.time()) + 600},
        secret, algorithm="HS256", headers={"kid": kid},
    )
    import base64
    k = base64.urlsafe_b64encode(secret.encode()).rstrip(b"=").decode()
    poisoned = {"keys": [{"kty": "oct", "alg": "HS256", "use": "sig", "kid": kid, "k": k}]}
    with pytest.raises(oidc.OidcError):
        await _verify(forged, poisoned)


async def test_valid_google_token(google_cfg):
    priv, jwks, kid = _keypair()
    tok = _token(priv, kid, iss="https://accounts.google.com", aud="web-aud")
    result = await _verify(tok, jwks)
    assert result.sub == "sub-1"
    assert result.email == "p@example.com"
    assert result.email_verified is True


async def test_wrong_audience(google_cfg):
    priv, jwks, kid = _keypair()
    tok = _token(priv, kid, iss="https://accounts.google.com", aud="someone-else")
    with pytest.raises(oidc.OidcAudienceMismatch):
        await _verify(tok, jwks)


async def test_expired(google_cfg):
    priv, jwks, kid = _keypair()
    tok = _token(priv, kid, iss="https://accounts.google.com", aud="web-aud", exp_delta=-10)
    with pytest.raises(oidc.OidcExpired):
        await _verify(tok, jwks)


async def test_bad_signature(google_cfg):
    priv, jwks, kid = _keypair()
    _, other_jwks, _ = _keypair(kid="test-kid")  # different key, same kid
    tok = _token(priv, kid, iss="https://accounts.google.com", aud="web-aud")
    with pytest.raises(oidc.OidcInvalid):
        await _verify(tok, other_jwks)


async def test_nonce_mismatch(google_cfg):
    priv, jwks, kid = _keypair()
    tok = _token(priv, kid, iss="https://accounts.google.com", aud="web-aud", nonce="n1")
    with pytest.raises(oidc.OidcNonceMismatch):
        await _verify(tok, jwks, nonce="different")


async def test_not_configured(monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "google_web_client_id", "", raising=False)
    monkeypatch.setattr(settings, "google_ios_client_id", "", raising=False)
    priv, jwks, kid = _keypair()
    tok = _token(priv, kid, iss="https://accounts.google.com", aud="web-aud")
    with pytest.raises(oidc.OidcNotConfigured):
        await _verify(tok, jwks)
