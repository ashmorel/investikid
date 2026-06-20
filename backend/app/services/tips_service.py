import json
import time

from app.schemas.simulator import InvestingTipOut
from app.services import llm_usage
from app.services.guardrails import with_guardrail_preamble
from app.services.llm_client import get_llm_client
from app.services.llm_json import extract_json_list
from app.services.moderation import moderate_output

_FALLBACK_TIPS = [
    InvestingTipOut(
        id="price-vs-value",
        title="Price Doesn't Equal Value",
        description=(
            "A $10 stock can grow just as much as a $1,000 stock. What matters is the percentage change, "
            "not the dollar amount. A stock going from $10 to $15 is the same 50% gain as one going from "
            "$1,000 to $1,500!"
        ),
        example_ticker="F",
        example_exchange="NYSE",
    ),
    InvestingTipOut(
        id="time-in-market",
        title="Time in the Market",
        description=(
            "The longer you hold, the more likely you are to see gains. Even after big drops, patient "
            "investors usually recover. Trying to time the market is nearly impossible — time IN the market "
            "is what counts."
        ),
        example_ticker="MSFT",
        example_exchange="NASDAQ",
    ),
    InvestingTipOut(
        id="diversification",
        title="Don't Put All Your Eggs in One Basket",
        description=(
            "Spreading your money across different companies and industries protects you if one has a bad "
            "year. This is called diversification — it's one of the most important rules of investing!"
        ),
        example_ticker="JNJ",
        example_exchange="NYSE",
    ),
]

_TIPS_PROMPT = (
    "You are writing short investing tips for kids aged 8-16 learning about the stock market.\n\n"
    "Generate 6 different investing tips. Each tip should:\n"
    "- Have a short catchy title (under 8 words)\n"
    "- Have a 2-3 sentence description that explains the concept simply\n"
    "- Include an example stock ticker and exchange from well-known companies kids would recognise\n"
    "- Be educational, encouraging, and never give real investment advice\n"
    "- Cover different concepts (don't repeat themes)\n\n"
    "Return JSON: [{\"id\": \"slug-id\", \"title\": \"...\", \"description\": \"...\", "
    "\"example_ticker\": \"AAPL\", \"example_exchange\": \"NASDAQ\"}]\n\n"
    "Only return the JSON array, nothing else."
)

_generic_cache: dict[str, tuple[float, list[InvestingTipOut]]] = {}
_GENERIC_TTL = 3600


def learning_stage(completed_lessons: int) -> str:
    if completed_lessons <= 0:
        return "new"
    if completed_lessons <= 5:
        return "beginner"
    if completed_lessons <= 15:
        return "intermediate"
    return "advanced"


@llm_usage.surface("tips_generic")
async def generate_generic_tips(*, language: str = "en") -> list[InvestingTipOut]:
    cache_key = "global"
    now = time.time()

    cached = _generic_cache.get(cache_key)
    if cached and (now - cached[0]) < _GENERIC_TTL:
        return cached[1]

    try:
        llm = get_llm_client(tier="lite")
        raw = await llm.complete(
            system_prompt=with_guardrail_preamble(_TIPS_PROMPT, language=language),
            messages=[{"role": "user", "content": "Generate 6 fresh investing tips for young learners."}],
            temperature=0.9,
            max_tokens=800,
            response_format="json",
        )
        items = extract_json_list(json.loads(raw))
        tips = [InvestingTipOut(**item) for item in items if isinstance(item, dict)]
        # Kid-safe moderation of generated tips. Best-effort: this service
        # has no DB session in scope, so no AuditLog row is written here by
        # design (unlike the session-bearing tutor/chart-coach/quiz surfaces).
        joined = " ".join(f"{t.title} {t.description}" for t in tips)
        _mod = await moderate_output(joined, surface="tips", language=language)
        if not _mod.safe:
            return _FALLBACK_TIPS
        if len(tips) >= 3:
            _generic_cache[cache_key] = (now, tips)
            return tips
    except Exception:
        pass

    return _FALLBACK_TIPS


_personal_cache: dict[str, tuple[float, list[InvestingTipOut]]] = {}
_PERSONAL_TTL = 3600


def _personal_key(user_id: int, holdings: list[tuple[str, str]], stage: str, age: int) -> str:
    sig = ",".join(sorted(t for t, _ in holdings))
    return f"{user_id}:{sig}:{stage}:{age}"


def _personal_prompt(holdings: list[tuple[str, str]], stage: str, age: int) -> str:
    owned = ", ".join(f"{name} ({ticker})" for ticker, name in holdings[:5]) or "none yet"
    return (
        f"You are writing personalised investing tips for a {age}-year-old kid who is at the "
        f"'{stage}' stage of learning about the stock market. They currently own: {owned}.\n\n"
        "Generate EXACTLY 2 short, encouraging, age-appropriate tips that connect to a stock they "
        "own and/or a concept suited to their stage. Each tip:\n"
        "- Short catchy title (under 8 words)\n"
        "- 2-3 sentence description in simple language for their age\n"
        "- Reference one of their owned tickers in example_ticker where natural "
        "(else a well-known kid-friendly stock)\n"
        "- Be educational and encouraging; NEVER give real investment advice\n\n"
        "Return JSON: [{\"id\": \"slug\", \"title\": \"...\", \"description\": \"...\", "
        "\"example_ticker\": \"AAPL\", \"example_exchange\": \"NASDAQ\"}]\n"
        "Only return the JSON array."
    )


@llm_usage.surface("tips_personalised")
async def generate_personalised_tips(
    *,
    user_id: int,
    holdings: list[tuple[str, str]],
    stage: str,
    age: int,
    refresh: bool = False,
    language: str = "en",
) -> tuple[list[InvestingTipOut], bool]:
    """2 holdings/level-tailored tips. Returns (tips, was_unsafe). was_unsafe is
    True only when the model output was moderated out (so the endpoint can write
    an AuditLog); False for no-context, cache, success, and error paths. Takes no
    session and writes no AuditLog itself."""
    if not holdings and stage == "new":
        return [], False

    key = _personal_key(user_id, holdings, stage, age)
    now = time.time()
    if not refresh:
        cached = _personal_cache.get(key)
        if cached and (now - cached[0]) < _PERSONAL_TTL:
            return cached[1], False

    try:
        llm = get_llm_client(tier="lite")
        raw = await llm.complete(
            system_prompt=with_guardrail_preamble(_personal_prompt(holdings, stage, age), language=language),
            messages=[{"role": "user", "content": "Generate 2 personalised tips."}],
            temperature=0.8,
            max_tokens=400,
            response_format="json",
        )
        items = extract_json_list(json.loads(raw))[:2]
        tips = [
            InvestingTipOut(**{k: v for k, v in item.items() if k != "personalised"}, personalised=True)
            for item in items
            if isinstance(item, dict)
        ]
        joined = " ".join(f"{t.title} {t.description}" for t in tips)
        _mod = await moderate_output(joined, surface="tips", language=language)
        if not _mod.safe:
            return [], True
        _personal_cache[key] = (now, tips)
        return tips, False
    except Exception:
        return [], False
