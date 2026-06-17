from pathlib import Path

from app.core.languages import SUPPORTED_LANGUAGES, is_supported_language, language_directive


def test_supported_set_and_validator():
    codes = {lang["code"] for lang in SUPPORTED_LANGUAGES}
    assert codes == {"en", "es", "fr", "de", "zh-Hant", "zh-Hans"}
    assert is_supported_language("en") is True
    assert is_supported_language("zh-Hant") is True
    assert is_supported_language("xx") is False


def test_only_english_available_at_launch():
    available = {lang["code"] for lang in SUPPORTED_LANGUAGES if lang["available"]}
    assert available == {"en"}


def test_frontend_registry_codes_match_backend():
    # The frontend TS registry must list the exact same codes, or language
    # validation will diverge from what the switcher offers.
    ts = Path(__file__).resolve().parents[2] / "frontend" / "src" / "i18n" / "languages.ts"
    text = ts.read_text(encoding="utf-8")
    backend_codes = sorted(lang["code"] for lang in SUPPORTED_LANGUAGES)
    for code in backend_codes:
        assert f"code: '{code}'" in text, f"frontend registry missing {code}"


def test_language_directive_english_is_noop():
    assert language_directive("en") == ""


def test_language_directive_unknown_is_noop():
    assert language_directive("xx") == ""
    assert language_directive("") == ""


def test_language_directive_non_english_names_the_language():
    es = language_directive("es")
    assert "Spanish" in es
    assert language_directive("fr").count("French") >= 1
    assert "German" in language_directive("de")


def test_language_directive_distinguishes_chinese_scripts():
    assert "Traditional Chinese" in language_directive("zh-Hant")
    assert "Simplified Chinese" in language_directive("zh-Hans")
