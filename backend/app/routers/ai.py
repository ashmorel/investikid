import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.content import Lesson, Module
from app.models.user import User
from app.routers.users import get_current_user
from app.schemas.ai import (
    MasteryProfileResponse,
    PracticeRequest,
    PracticeResponse,
    RecommendationsResponse,
    TutorChatRequest,
    TutorChatResponse,
)
from app.services.ai_content_service import generate_practice_quiz
from app.services.entitlements import is_premium
from app.services.recommendation_service import get_recommendations
from app.services.skill_profile_service import get_mastery_profile
from app.services.tutor_service import TutorInputTooLong, TutorLimitReached, chat

router = APIRouter(tags=["ai"])


@router.get("/recommendations", response_model=RecommendationsResponse)
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
        topic=module.topic,
        concept=concept,
        premium=is_premium(current_user),
        wrong_answer_index=payload.wrong_answer_index,
    )
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


@router.get("/profile/mastery", response_model=MasteryProfileResponse)
async def mastery_profile(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    profile = await get_mastery_profile(session, current_user.id)
    return profile
