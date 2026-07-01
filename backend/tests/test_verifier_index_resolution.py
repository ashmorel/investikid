"""The verifier resolves its pick by the QUOTED choice text, so a correct answer
with a mis-counted numeric index is no longer a false mismatch (pure, no DB)."""
from __future__ import annotations

from types import SimpleNamespace

from app.services.diagnostic_item_service import _match_choice_text, _resolve_verifier_index

CHOICES = ["HKD 96,000", "HKD 95,600", "HKD 91,200", "HKD 4,800"]


def test_match_exact_text():
    assert _match_choice_text(CHOICES, "HKD 91,200") == 2


def test_match_strips_leading_bracket_label():
    assert _match_choice_text(CHOICES, "[2] HKD 91,200") == 2


def test_match_case_and_whitespace_insensitive():
    assert _match_choice_text(CHOICES, "  hkd   91,200 ") == 2


def test_match_none_without_text():
    assert _match_choice_text(CHOICES, None) is None
    assert _match_choice_text(CHOICES, "") is None


def test_match_ambiguous_containment_returns_none():
    # target contains two different choices → ambiguous → None (fall back to index)
    assert _match_choice_text(["cat", "cats"], "cats and cat") is None


def test_resolve_prefers_quoted_text_over_wrong_index():
    """The exact failure: verifier reasoned correctly (quoted the right choice)
    but reported the WRONG 0-based index. Text wins → the correct index."""
    item = SimpleNamespace(choices=CHOICES)
    assert _resolve_verifier_index(item, {"answer_text": "HKD 91,200", "answer_index": 1}) == 2


def test_resolve_falls_back_to_index_without_text():
    item = SimpleNamespace(choices=CHOICES)
    assert _resolve_verifier_index(item, {"answer_index": 3}) == 3


def test_resolve_falls_back_when_text_unmatched():
    item = SimpleNamespace(choices=CHOICES)
    assert _resolve_verifier_index(item, {"answer_text": "not a choice", "answer_index": 0}) == 0
