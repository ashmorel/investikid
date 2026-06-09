import json
import time

from app.schemas.simulator import InvestingTipOut
from app.services.llm_client import get_llm_client
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


async def generate_generic_tips() -> list[InvestingTipOut]:
    cache_key = "global"
    now = time.time()

    cached = _generic_cache.get(cache_key)
    if cached and (now - cached[0]) < _GENERIC_TTL:
        return cached[1]

    try:
        llm = get_llm_client(tier="lite")
        raw = await llm.complete(
            system_prompt=_TIPS_PROMPT,
            messages=[{"role": "user", "content": "Generate 6 fresh investing tips for young learners."}],
            temperature=0.9,
            max_tokens=800,
            response_format="json",
        )
        items = json.loads(raw)
        tips = [InvestingTipOut(**item) for item in items]
        # Kid-safe moderation of generated tips. Best-effort: this service
        # has no DB session in scope, so no AuditLog row is written here by
        # design (unlike the session-bearing tutor/chart-coach/quiz surfaces).
        joined = " ".join(f"{t.title} {t.description}" for t in tips)
        _mod = await moderate_output(joined, surface="tips")
        if not _mod.safe:
            return _FALLBACK_TIPS
        if len(tips) >= 3:
            _generic_cache[cache_key] = (now, tips)
            return tips
    except Exception:
        pass

    return _FALLBACK_TIPS
