from unittest.mock import MagicMock

from app.services import storage


def test_not_configured_when_env_missing(monkeypatch):
    monkeypatch.setattr(storage.settings, "r2_bucket", "")
    assert storage.is_configured() is False


def test_configured_when_env_present(monkeypatch):
    for k, v in {
        "r2_account_id": "acct", "r2_access_key_id": "ak", "r2_secret_access_key": "sk",
        "r2_bucket": "vids", "r2_public_base_url": "https://cdn.example.com",
    }.items():
        monkeypatch.setattr(storage.settings, k, v)
    assert storage.is_configured() is True


def test_public_url_joins_base_and_key(monkeypatch):
    monkeypatch.setattr(storage.settings, "r2_public_base_url", "https://cdn.example.com/")
    assert storage.public_url("videos/abc.mp4") == "https://cdn.example.com/videos/abc.mp4"


def test_create_presigned_put_uses_client(monkeypatch):
    fake = MagicMock()
    fake.generate_presigned_url.return_value = "https://r2.example.com/PUT"
    monkeypatch.setattr(storage, "_client", lambda: fake)
    monkeypatch.setattr(storage.settings, "r2_bucket", "vids")
    url = storage.create_presigned_put("videos/abc.mp4", "video/mp4", content_length=1234, expires=900)
    assert url == "https://r2.example.com/PUT"
    args, kwargs = fake.generate_presigned_url.call_args
    assert args[0] == "put_object"
    assert kwargs["Params"]["Bucket"] == "vids"
    assert kwargs["Params"]["Key"] == "videos/abc.mp4"
    assert kwargs["Params"]["ContentType"] == "video/mp4"
    # ContentLength must be signed into the URL so R2 rejects an upload whose
    # actual byte size differs from the (validated) claimed size.
    assert kwargs["Params"]["ContentLength"] == 1234
    assert kwargs["ExpiresIn"] == 900
