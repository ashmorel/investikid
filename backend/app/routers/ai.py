import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.content import Lesson, Module
from app.models.user import User
from app.routers.users import get_current_user
from app.schemas.ai import (
    CategorisedRecommendations,
    CoachChatRequest,
    CoachChatResponse,
    MasteryProfileResponse,
    PracticeRequest,
    PracticeResponse,
    StrengthsAndGaps,
    TutorChatRequest,
    TutorChatResponse,
)
from app.services.ai_content_service import generate_practice_quiz
from app.services.entitlements import is_premium
from app.services.recommendation_service import get_recommendations
from app.services.skill_profile_service import get_mastery_profile
from app.services.spaced_repetition_service import record_review
from app.services.coach_service import coach_chat
from app.services.tutor_service import TutorInputTooLong, TutorLimitReached, chat

router = APIRouter(tags=["ai"])


@router.get("/recommendations", response_model=CategorisedRecommendations)
async def recommendations(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await get_recommendations(session, current_user)
    return result


@router.post("/lessons/{lesson_id}/practice", response_model=PracticeResponse)
async def practice_quiz(
    lesson_id: uuid.UUID,
    payload: PracticeRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    lesson = await session.get(Lesson, lesson_id)
    if not lesson:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lesson not found")

    module = await session.get(Module, lesson.module_id)
    if not module:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Module not found")

    # Derive concept from lesson title
    content = lesson.content_json or {}
    concept = content.get("question") or content.get("title") or content.get("prompt") or "general"

    result = await generate_practice_quiz(
        session,
        lesson,
        user=current_user,
        topic=module.topic,
        concept=concept,
        premium=is_premium(current_user),
        wrong_answer_index=payload.wrong_answer_index,
    )

    # Track spaced repetition for the concept
    # If wrong_answer_index is provided, the user answered wrong previously
    if payload.wrong_answer_index is not None:
        # Find or create a weak concept for this topic+concept
        from app.models.skill_profile import WeakConcept
        from sqlalchemy import select as sa_select
        weak = await session.scalar(
            sa_select(WeakConcept).where(
                WeakConcept.user_id == current_user.id,
                WeakConcept.topic == module.topic,
                WeakConcept.concept == concept,
            )
        )
        if weak:
            await record_review(
                session, current_user.id, weak.id, correct=False,
            )
            await session.commit()

    return result


@router.post("/tutor/chat", response_model=TutorChatResponse)
async def tutor_chat(
    payload: TutorChatRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    lesson = await session.get(Lesson, payload.lesson_id)
    if not lesson:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lesson not found")

    module = await session.get(Module, lesson.module_id)
    if not module:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Module not found")

    try:
        result = await chat(
            session=session,
            user=current_user,
            lesson=lesson,
            topic=module.topic,
            message=payload.message,
            conversation_id=payload.conversation_id,
            premium=is_premium(current_user),
        )
    except TutorInputTooLong as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
    except TutorLimitReached as exc:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, str(exc))

    return result


@router.post("/tutor/coach", response_model=CoachChatResponse)
async def coach_eddie(
    payload: CoachChatRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    try:
        result = await coach_chat(
            session=session,
            user=current_user,
            message=payload.message,
            conversation_id=payload.conversation_id,
            premium=is_premium(current_user),
        )
    except TutorInputTooLong as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
    except TutorLimitReached as exc:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, str(exc))

    return result


@router.get("/profile/mastery", response_model=MasteryProfileResponse)
async def mastery_profile(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    profile = await get_mastery_profile(session, current_user.id)
    return profile


from app.services.gap_detection_service import get_strengths_and_gaps


@router.get("/profile/strengths", response_model=StrengthsAndGaps)
async def strengths(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await get_strengths_and_gaps(session, current_user.id)
    return result
