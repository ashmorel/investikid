from __future__ import annotations

import asyncio
import hashlib
import re
import time
from dataclasses import dataclass

_CACHE_TTL = 3600
_ESCALATION_TIMEOUT = 5.0

_SAFE_FALLBACKS: dict[str, str] = {
    "tutor": "That's a great question! Let's get back to your lesson — "
             "ask a parent or teacher about real money decisions. 😊",
    "chart_coach": "Let's look at the chart together — what do you notice "
                   "about the line going up or down?",
    "quiz": "Let's review the lesson and try a practice question from there.",
    "tips": "Keep learning with your lessons — you're doing great!",
}
_DEFAULT_FALLBACK = "Let's get back to learning!"

_ADVICE_IMPERATIVE = re.compile(
    r"\byou should (buy|sell|invest|trade)\b", re.IGNORECASE)
# NO re.IGNORECASE: the asset name must start with a capital (ticker AAPL or
# proper noun Apple). With IGNORECASE this arm would match "buy something" /
# "sell them" — exactly the over-block this guard fixes.
_ADVICE_NAMED = re.compile(
    r"\b(?:buy|sell|invest in) (?:[A-Z]{2,}|[A-Z][a-z]+)\b")  # NO IGNORECASE


def _is_financial_advice(text: str) -> bool:
    return bool(_ADVICE_IMPERATIVE.search(text) or _ADVICE_NAMED.search(text))


_CATEGORY_PATTERNS: dict[str, re.Pattern] = {
    "sexual": re.compile(
        r"\b(sex|sexual|porn|nude|naked|explicit content|genital)\w*\b", re.I),
    "violence": re.compile(
        r"\b(kill|murder|stab|shoot|bomb|weapon|hurt someone|attack (you|him|her|them))\b",
        re.I),
    "hate": re.compile(
        r"\b(subhuman|inferior race|should be hated|slur)\b", re.I),
    "self_harm": re.compile(
        r"\b(hurt yourself|kill yourself|end your life|self[- ]harm|suicide)\b",
        re.I),
    "illegal_dangerous": re.compile(
        r"\b(buy (illegal )?drugs|make (a )?(bomb|explosive)|how to steal|hack into)\b",
        re.I),
    "pii": re.compile(
        r"[\w.+-]+@[\w-]+\.[\w.-]+"
        r"|\b(?:\+?\d[\d ()-]{7,}\d)\b"
        r"|\b\d{1,4} [A-Z][a-z]+ (Street|Road|Avenue|Lane|Drive)\b",
        re.I),
    "prompt_injection": re.compile(
        r"\b(ignore (all )?(previous|prior) instructions"
        r"|system prompt|you are now|disregard the rules)\b", re.I),
}

_REVIEW_TOKENS = re.compile(r"\b(weapon|suicide|kill yourself|explicit)\b", re.I)


@dataclass(frozen=True)
class ModerationResult:
    safe: bool
    category: str | None
    text: str


_verdict_cache: dict[tuple[str, str], tuple[float, ModerationResult]] = {}


def _fallback_for(surface: str) -> str:
    return _SAFE_FALLBACKS.get(surface, _DEFAULT_FALLBACK)


def _prefilter_category(text: str) -> str | None:
    if _is_financial_advice(text):
        return "financial_advice"
    for name, pat in _CATEGORY_PATTERNS.items():
        if pat.search(text):
            return name
    return None


def _needs_escalation(text: str) -> bool:
    return bool(_REVIEW_TOKENS.search(text))


async def _model_moderation(text: str) -> tuple[bool, str | None]:
    import json

    from app.services.llm_client import get_llm_client

    client = get_llm_client(tier="standard")
    raw = await client.complete(
        system_prompt=(
            "You are a strict child-safety classifier for a kids' (ages 8-16) "
            "financial-education app. Decide if the ASSISTANT TEXT is safe to "
            "show a child. Unsafe categories: sexual, violence, hate, "
            "self_harm, illegal_dangerous, pii, prompt_injection, "
            "financial_advice. Educational discussion of money, risk, loss, "
            "debt, tax, or crypto is SAFE. Reply ONLY with compact JSON: "
            '{"safe": true|false, "category": "<name>"|null}.'
        ),
        messages=[{"role": "user", "content": text}],
        temperature=0.0,
        max_tokens=40,
        response_format="json",
    )
    data = json.loads(raw)
    safe = data["safe"]
    if not isinstance(safe, bool):
        raise ValueError("non-bool 'safe'")
    return safe, (None if safe else (data.get("category") or "model_flagged"))


async def moderate_output(text: str, *, surface: str) -> ModerationResult:
    fallback = _fallback_for(surface)
    try:
        if not text or not text.strip():
            return ModerationResult(False, "empty", fallback)
        cat = _prefilter_category(text)
        if cat is not None:
            return ModerationResult(False, cat, fallback)
        if not _needs_escalation(text):
            return ModerationResult(True, None, text)
        key = (hashlib.sha256(text.encode()).hexdigest(), surface)
        now = time.time()
        hit = _verdict_cache.get(key)
        if hit and (now - hit[0]) < _CACHE_TTL:
            return hit[1]
        safe, category = await asyncio.wait_for(
            _model_moderation(text), _ESCALATION_TIMEOUT)
        result = (ModerationResult(True, None, text) if safe
                  else ModerationResult(False, category, fallback))
        _verdict_cache[key] = (now, result)
        return result
    except Exception:
        return ModerationResult(False, "error", fallback)
