"""Single source of truth for app display languages (BCP-47).

`available` flips to True once a UI catalog ships for that language. Keep this
list in lockstep with frontend/src/i18n/languages.ts (a test enforces parity).
"""
from __future__ import annotations

SUPPORTED_LANGUAGES: list[dict] = [
    {"code": "en", "endonym": "English", "available": True},
    {"code": "es", "endonym": "Español", "available": False},
    {"code": "fr", "endonym": "Français", "available": False},
    {"code": "de", "endonym": "Deutsch", "available": False},
    {"code": "zh-Hant", "endonym": "繁體中文", "available": False},
    {"code": "zh-Hans", "endonym": "简体中文", "available": False},
]

_CODES = frozenset(lang["code"] for lang in SUPPORTED_LANGUAGES)


def is_supported_language(code: str) -> bool:
    return code in _CODES
