from app.core.config import settings


def test_google_play_settings_exist():
    for attr in ("google_play_package_name", "google_play_service_account_json", "google_play_product_id"):
        assert hasattr(settings, attr)
