from app.core.config import settings


def test_apple_settings_exist_with_defaults():
    assert settings.apple_iap_environment in ("Sandbox", "Production", "")
    for attr in ("apple_iap_issuer_id", "apple_iap_key_id", "apple_iap_private_key",
                 "apple_iap_bundle_id", "apple_iap_app_apple_id", "apple_iap_product_id"):
        assert hasattr(settings, attr)
