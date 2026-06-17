from app.services import llm_usage
from app.services.age_tier import AGE_REGISTER_DIRECTIVE, AgeTier
from app.services.guardrails import log_guardrail_event, with_guardrail_preamble
from app.services.llm_client import get_llm_client
from app.services.moderation import moderate_output

_MAX_LEN = 160


def _build_messages(
    *,
    name: str,
    mode: str,
    lesson_label: str | None,
    streak_count: int,
    due_count: int,
    tier: AgeTier,
    language: str = "en",
) -> tuple[str, list[dict]]:
    system_prompt = (
        "You are Coach Penny, a warm, encouraging piggy-bank money-skills buddy for a child. "
        "Write ONE short, upbeat greeting (max 20 words) for the home screen that nudges "
        "them toward their next lesson. Friendly, age-appropriate, at most one emoji. "
        "Do not give financial advice. Output only the greeting text. "
        + AGE_REGISTER_DIRECTIVE[tier]
    )
    context = (
        f"Child's name: {name or 'there'}. Mode: {mode}. "
        f"Next lesson: {lesson_label or 'n/a'}. Streak: {streak_count} days. "
        f"Concepts due for review: {due_count}."
    )
    messages = [{"role": "user", "content": context}]
    return with_guardrail_preamble(system_prompt, language=language), messages


@llm_usage.surface("home_greeting")
async def generate_home_greeting(
    *,
    name: str,
    mode: str,
    lesson_label: str | None,
    streak_count: int,
    due_count: int,
    tier: AgeTier,
    language: str = "en",
) -> str:
    """Premium AI greeting. Raises on provider/moderation failure so the caller
    can fall back to the client-side templated line."""
    client = get_llm_client(tier="premium")
    system_prompt, messages = _build_messages(
        name=name,
        mode=mode,
        lesson_label=lesson_label,
        streak_count=streak_count,
        due_count=due_count,
        tier=tier,
        language=language,
    )

    # Exact completion call pattern from coach_service.coach_chat:
    raw = await client.complete(
        system_prompt=system_prompt,
        messages=messages,
        max_tokens=60,
        temperature=0.3,
    )
    text = (raw or "").strip().strip('"')[:_MAX_LEN]
    if not text:
        raise ValueError("empty greeting")

    _mod = await moderate_output(text, surface="coach")
    if not _mod.safe:
        log_guardrail_event(
            action="output_block", surface="home_greeting",
            category=_mod.category, child_id=None,
        )
        raise ValueError("greeting blocked by moderation")
    return _mod.text[:_MAX_LEN]
