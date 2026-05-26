"""Coach Eddie standalone service — context building and action parsing."""
from __future__ import annotations

import re
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.audit import AuditLog
from app.models.content import Module
from app.models.tutor import TutorConversation
from app.models.user import User
from app.services.entitlements import is_premium
from app.services.gap_detection_service import get_strengths_and_gaps
from app.services.llm_client import get_llm_client, get_model_name
from app.services.moderation import moderate_output
from app.services.recommendation_service import get_recommendations
from app.services.spaced_repetition_service import get_due_count
from app.services.tutor_service import TutorInputTooLong, TutorLimitReached, _skill_level


_ACTION_RE = re.compile(
    r"\[ACTION:(lesson|module|review):([a-zA-Z0-9][a-zA-Z0-9\-]*)(?::([a-zA-Z0-9][a-zA-Z0-9\-]*))?\]"
)

_TYPE_LABELS = {
    "lesson": "Start lesson in {title}",
    "module": "Go to {title}",
    "review": "Review {title}",
}


def build_coach_context(
    *,
    strengths: list[dict[str, Any]],
    overall_mastery: float,
    continue_learning: list[dict[str, Any]],
    practise_again: list[dict[str, Any]],
    something_new: list[dict[str, Any]],
    due_count: int,
) -> str:
    """Build a human-readable learning-state block for the system prompt.

    All inputs are plain dicts — caller is responsible for shaping data
    from the various services into this format.
    """
    lines: list[str] = []

    if not strengths and not continue_learning and not practise_again and not something_new and due_count == 0:
        return "No learning data yet — this student is just getting started."

    lines.append("Your student's learning state:")

    # Topic mastery
    for t in strengths:
        score_pct = f"{round(t['mastery_score'] * 100)}%"
        weak = f", {t['weak_count']} weak concepts" if t.get("weak_count", 0) > 0 else ""
        topic_display = t["topic"].replace("_", " ")
        lines.append(f"- {topic_display}: {score_pct} mastery ({t['status']}){weak}")

    if overall_mastery > 0:
        lines.append(f"- Overall mastery: {round(overall_mastery * 100)}%")

    # Recommendations
    for item in continue_learning:
        pct = item.get("completed_pct", 0)
        lines.append(f"- Currently working on: {item['module_title']} ({pct}% complete)")

    for item in practise_again:
        concepts = item.get("weak_concepts", [])
        concept_str = f" — weak: {', '.join(concepts)}" if concepts else ""
        lines.append(f"- Needs practice: {item['module_title']}{concept_str}")

    for item in something_new:
        lines.append(f"- Suggested next: {item['module_title']} (something new)")

    # SR summary
    if due_count > 0:
        lines.append(f"- Due for review: {due_count} concept{'s' if due_count != 1 else ''}")

    return "\n".join(lines)


def parse_actions(
    raw_text: str,
    module_titles: dict[str, str],
) -> tuple[str, list[dict[str, Any]]]:
    """Extract [ACTION:...] markers from LLM text.

    Returns (cleaned_text, actions_list).
    """
    actions: list[dict[str, Any]] = []

    for match in _ACTION_RE.finditer(raw_text):
        action_type = match.group(1)
        module_id = match.group(2)
        lesson_id = match.group(3)  # may be None

        title = module_titles.get(module_id, "module")
        label = _TYPE_LABELS.get(action_type, "Go to {title}").format(title=title)

        # Use fallback label when module not found
        if module_id not in module_titles:
            label = _TYPE_LABELS.get(action_type, "Go to module").format(title="module")
            # Special case: "Go to module" is the expected fallback for unknown module ids
            if action_type == "module":
                label = "Go to module"

        actions.append({
            "type": action_type,
            "module_id": module_id,
            "lesson_id": lesson_id,
            "label": label,
        })

    cleaned = _ACTION_RE.sub("", raw_text).strip()

    return cleaned, actions


_COACH_SYSTEM_PROMPT = (
    "You are Coach Eddie, a friendly money tutor for kids. You help them navigate "
    "their learning journey — what to learn next, what to review, and how they're doing.\n\n"
    "Rules:\n"
    "1. Reference the student's actual learning state (provided below).\n"
    "2. When suggesting a lesson or module, include an action marker: "
    "[ACTION:lesson:<module_id>:<lesson_id>] or [ACTION:module:<module_id>]\n"
    "3. When suggesting a review session, use: [ACTION:review:<module_id>]\n"
    "4. Never give real financial advice or suggest spending real money.\n"
    "5. Keep responses under 120 words.\n"
    "6. Use simple, encouraging language.\n"
    "7. {skill_level_instruction}\n\n"
    "{learning_state_context}"
)

_SKILL_INSTRUCTIONS = {
    "low": (
        "The student is a beginner. Use very simple words, short sentences, and lots of encouragement."
        " Give examples they can relate to (pocket money, toys, snacks)."
    ),
    "medium": (
        "The student has some understanding. Give clear explanations with relatable examples."
        " Encourage them to think about why."
    ),
    "high": (
        "The student is doing well. Challenge them with deeper questions."
        " Ask 'what if' scenarios to deepen understanding."
    ),
}


async def coach_chat(
    *,
    session: AsyncSession,
    user: User,
    message: str,
    conversation_id: uuid.UUID | None,
    premium: bool,
) -> dict[str, Any]:
    """Process a standalone Coach Eddie message."""
    max_chars = settings.tutor_max_input_chars
    if len(message) > max_chars:
        raise TutorInputTooLong(f"Message must be under {max_chars} characters")

    max_messages = (
        settings.tutor_max_messages_premium if premium
        else settings.tutor_max_messages_free
    )

    # Load or create conversation (lesson_id=None for standalone coach)
    conversation: TutorConversation | None = None
    if conversation_id:
        conversation = await session.get(TutorConversation, conversation_id)

    model_name = get_model_name("premium" if premium else "standard")

    if conversation is None:
        conversation = TutorConversation(
            user_id=user.id,
            lesson_id=None,
            messages=[],
            message_count=0,
            model_used=model_name,
        )
        session.add(conversation)
        await session.flush()

    if conversation.message_count >= max_messages:
        raise TutorLimitReached(
            f"Message limit reached ({max_messages}). "
            + ("Upgrade to premium for more!" if not premium else "Limit reached for this conversation.")
        )

    # Gather learning context
    recs = await get_recommendations(session, user)
    gaps = await get_strengths_and_gaps(session, user.id)
    due_count = await get_due_count(session, user.id)

    # Load module titles for action label resolution
    all_modules = (await session.scalars(select(Module))).all()
    module_titles: dict[str, str] = {str(m.id): m.title for m in all_modules}

    # Build recommendation summaries for context
    continue_learning = []
    for item in recs.get("continue_learning", []):
        mid = str(item["module_id"])
        continue_learning.append({
            "module_title": module_titles.get(mid, "Module"),
            "completed_pct": 0,
        })

    practise_again = []
    for item in recs.get("practise_again", []):
        mid = str(item["module_id"])
        practise_again.append({
            "module_title": module_titles.get(mid, "Module"),
            "weak_concepts": item.get("weak_concepts", []),
        })

    something_new = []
    for item in recs.get("something_new", []):
        mid = str(item["module_id"])
        something_new.append({"module_title": module_titles.get(mid, "Module")})

    strengths = [
        {
            "topic": t.topic,
            "mastery_score": t.mastery_score,
            "status": t.status,
            "weak_count": t.weak_count,
        }
        for t in gaps.topics
    ]

    context_block = build_coach_context(
        strengths=strengths,
        overall_mastery=gaps.overall_mastery,
        continue_learning=continue_learning,
        practise_again=practise_again,
        something_new=something_new,
        due_count=due_count,
    )

    # Get overall mastery for skill level
    mastery_score = gaps.overall_mastery
    level = _skill_level(mastery_score)

    system_prompt = _COACH_SYSTEM_PROMPT.format(
        skill_level_instruction=_SKILL_INSTRUCTIONS[level],
        learning_state_context=context_block,
    )

    # Build message history
    history = [
        {"role": m["role"], "content": m["content"]}
        for m in conversation.messages
    ]
    history.append({"role": "user", "content": message})

    # Call LLM
    client = get_llm_client(tier="premium" if premium else "standard")
    raw_response = await client.complete(
        system_prompt=system_prompt,
        messages=history,
        temperature=0.5,
        max_tokens=settings.tutor_max_response_tokens,
    )

    # Kid-safe moderation
    _mod = await moderate_output(raw_response, surface="tutor")
    filtered_response = _mod.text
    if not _mod.safe:
        session.add(AuditLog(
            user_id=user.id,
            event_type="moderation_block",
            metadata_json={"surface": "coach", "category": _mod.category},
        ))

    # Parse actions from response
    cleaned_text, actions = parse_actions(filtered_response, module_titles)

    # Persist conversation
    conversation.messages = [
        *conversation.messages,
        {"role": "user", "content": message},
        {"role": "assistant", "content": cleaned_text},
    ]
    conversation.message_count += 2
    await session.flush()

    return {
        "response": cleaned_text,
        "conversation_id": conversation.id,
        "messages_remaining": max(0, max_messages - conversation.message_count),
        "actions": actions,
    }
