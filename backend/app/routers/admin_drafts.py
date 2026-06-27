import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.rate_limit import limiter
from app.models.content import Lesson, Level
from app.models.lesson_draft import LessonDraft
from app.routers.admin_content import _lesson_out
from app.schemas.admin import (
    AdaptationFlags,
    ApproveDraftsRequest,
    ApproveDraftsResult,
    LessonDraftOut,
    LessonDraftUpdate,
    LessonOut,
    validate_lesson_content_json,
)
from app.services.admin_content_generation_service import (
    _concat_text,
    regenerate_draft,
)
from app.services.content_adaptation_check import find_uk_residue
from app.services.lesson_approval_service import approve_level_drafts
from app.services.moderation import moderate_output

router = APIRouter()


@router.get("/levels/{level_id}/drafts", response_model=list[LessonDraftOut])
async def list_lesson_drafts(
    level_id: uuid.UUID, session: AsyncSession = Depends(get_session),
):
    rows = (await session.scalars(
        select(LessonDraft).where(LessonDraft.level_id == level_id).order_by(LessonDraft.created_at)
    )).all()

    def _draft_out(d):
        residue = find_uk_residue(_concat_text(d.content_json or {}))
        out = LessonDraftOut.model_validate(d)
        out.adaptation_flags = AdaptationFlags(uk_residue=residue, suspect=bool(residue))
        return out

    return [_draft_out(d) for d in rows]


@router.put("/lesson-drafts/{draft_id}", response_model=LessonDraftOut)
async def update_lesson_draft(
    draft_id: uuid.UUID,
    payload: LessonDraftUpdate,
    session: AsyncSession = Depends(get_session),
):
    draft = await session.get(LessonDraft, draft_id)
    if draft is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft not found")
    try:
        validate_lesson_content_json(draft.type, payload.content_json)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    mod = await moderate_output(_concat_text(payload.content_json), surface="lesson")
    draft.content_json = payload.content_json
    draft.moderation_safe = mod.safe
    draft.moderation_category = mod.category
    await session.commit()
    return LessonDraftOut.model_validate(draft)


@router.post("/lesson-drafts/{draft_id}/approve", response_model=LessonOut)
async def approve_lesson_draft(
    draft_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    draft = await session.get(LessonDraft, draft_id)
    if draft is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft not found")
    if not draft.moderation_safe:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Draft failed moderation")
    level = await session.get(Level, draft.level_id)
    max_order = await session.scalar(
        select(func.max(Lesson.order_index)).where(Lesson.level_id == draft.level_id)
    )
    lesson = Lesson(
        module_id=level.module_id, level_id=draft.level_id, type=draft.type,
        content_json=draft.content_json, xp_reward=10, order_index=(max_order or 0) + 1,
    )
    session.add(lesson)
    await session.delete(draft)
    await session.commit()
    await session.refresh(lesson)
    return await _lesson_out(session, lesson)


@router.post("/levels/{level_id}/approve-drafts", response_model=ApproveDraftsResult)
async def approve_level_drafts_endpoint(
    level_id: uuid.UUID,
    payload: ApproveDraftsRequest,
    session: AsyncSession = Depends(get_session),
):
    level = await session.get(Level, level_id)
    if level is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Level not found")
    return ApproveDraftsResult(**await approve_level_drafts(session, level, replace=payload.replace))


@router.post("/lesson-drafts/{draft_id}/regenerate", response_model=LessonDraftOut)
@limiter.limit("5/minute")
async def regenerate_lesson_draft(
    request: Request,
    draft_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    draft = await session.get(LessonDraft, draft_id)
    if draft is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft not found")
    updated = await regenerate_draft(session, draft)
    if updated is None:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Generation failed")
    return LessonDraftOut.model_validate(updated)


@router.delete("/lesson-drafts/{draft_id}", status_code=status.HTTP_204_NO_CONTENT)
async def reject_lesson_draft(
    draft_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    draft = await session.get(LessonDraft, draft_id)
    if draft is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft not found")
    await session.delete(draft)
    await session.commit()
