import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.content import Lesson, Level, VideoCandidate
from app.routers.admin_auth import get_current_admin
from app.schemas.admin import ApproveCandidateIn, SuggestVideosIn, VideoCandidateOut
from app.services.video_suggest_service import suggest_videos

router = APIRouter(
    prefix="/admin/video-candidates",
    tags=["admin-video"],
    dependencies=[Depends(get_current_admin)],
)


@router.post("/suggest")
async def suggest(
    payload: SuggestVideosIn, session: AsyncSession = Depends(get_session)
) -> dict:
    return await suggest_videos(session, module_id=payload.module_id, level_id=payload.level_id)


@router.get("", response_model=list[VideoCandidateOut])
async def list_candidates(
    status: str = "pending",
    market: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> list[VideoCandidate]:
    q = select(VideoCandidate).where(VideoCandidate.status == status)
    if market:
        q = q.where(VideoCandidate.market_code == market)
    return list((await session.scalars(q.order_by(VideoCandidate.created_at))).all())


@router.post("/{candidate_id}/approve", response_model=VideoCandidateOut)
async def approve_candidate(
    candidate_id: uuid.UUID,
    payload: ApproveCandidateIn,
    session: AsyncSession = Depends(get_session),
) -> VideoCandidate:
    cand = await session.get(VideoCandidate, candidate_id)
    if cand is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "candidate not found")
    if cand.embeddable is not True:
        raise HTTPException(status.HTTP_409_CONFLICT, "video failed the embeddability/safety check")
    level = await session.get(Level, payload.level_id)
    if level is None or level.module_id != payload.module_id:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "level does not belong to module")
    max_idx = await session.scalar(
        select(func.max(Lesson.order_index)).where(Lesson.level_id == level.id)
    )
    next_order = 0 if max_idx is None else max_idx + 1
    lesson = Lesson(
        module_id=payload.module_id,
        level_id=level.id,
        type="video",
        content_json={
            "video_source": "youtube",
            "youtube_id": cand.youtube_id,
            "caption": cand.title,
        },
        xp_reward=10,
        order_index=next_order,
    )
    session.add(lesson)
    await session.flush()
    cand.status = "approved"
    cand.created_lesson_id = lesson.id
    await session.commit()
    await session.refresh(cand)
    return cand


@router.post("/{candidate_id}/skip", response_model=VideoCandidateOut)
async def skip_candidate(
    candidate_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> VideoCandidate:
    cand = await session.get(VideoCandidate, candidate_id)
    if cand is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "candidate not found")
    cand.status = "skipped"
    await session.commit()
    await session.refresh(cand)
    return cand
