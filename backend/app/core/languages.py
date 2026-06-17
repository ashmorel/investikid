"""Single source of truth for app display languages (BCP-47).

`available` flips to True once a UI catalog ships for that language. Keep this
list in lockstep with frontend/src/i18n/languages.ts (a test enforces parity).
"""
from __future__ import annotations

SUPPORTED_LANGUAGES: list[dict[str, str | bool]] = [
    {"code": "en", "endonym": "English", "prompt_name": "English", "available": True},
    {"code": "es", "endonym": "Español", "prompt_name": "Spanish", "available": False},
    {"code": "fr", "endonym": "Français", "prompt_name": "French", "available": False},
    {"code": "de", "endonym": "Deutsch", "prompt_name": "German", "available": False},
    {"code": "zh-Hant", "endonym": "繁體中文", "prompt_name": "Traditional Chinese (繁體中文)", "available": False},
    {"code": "zh-Hans", "endonym": "简体中文", "prompt_name": "Simplified Chinese (简体中文)", "available": False},
]

_CODES = frozenset(lang["code"] for lang in SUPPORTED_LANGUAGES)
_PROMPT_NAMES: dict[str, str] = {
    str(lang["code"]): str(lang["prompt_name"]) for lang in SUPPORTED_LANGUAGES
}


def is_supported_language(code: str) -> bool:
    return code in _CODES


def language_directive(code: str) -> str:
    """A system-prompt directive instructing the model to reply in `code`'s
    language. Returns "" for English or any unknown/empty code (no-op), so
    English users see byte-identical prompts and unknown codes degrade to English.
    """
    if code == "en":
        return ""
    name = _PROMPT_NAMES.get(code)
    if not name:
        return ""
    return (
        f"Always respond entirely in {name}. Translate all examples and "
        f"explanations into {name}. Keep proper nouns, company names, and ticker "
        f"symbols unchanged. Respond in {name} regardless of the language the "
        f"user writes in."
    )
