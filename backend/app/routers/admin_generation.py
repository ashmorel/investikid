import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.rate_limit import limiter
from app.models.content import Level, Module
from app.models.user import User
from app.routers.admin_auth import get_current_admin
from app.schemas.admin import (
    CurriculumDesignOut,
    GenerateLessonsRequest,
    GenerateLessonsResponse,
    GenerateMarketLessonsRequest,
    GenerateModuleMarketRequest,
    GenerateNativeLessonsRequest,
    LessonDraftOut,
)
from app.services.admin_content_generation_service import (
    generate_level_lessons,
    generate_market_level_lessons,
    generate_module_market_lessons,
    generate_native_level_lessons,
)
from app.services.market_brief_service import require_verified_brief
from app.services.market_curriculum.curriculum_publish_service import publish_market_curriculum
from app.services.market_curriculum.designer import CurriculumDesignError, design_curriculum
from app.services.market_curriculum.native_batch import generate_market_native
from app.services.market_curriculum.proposal_service import (
    accept_proposal,
    get_active_proposal,
    get_proposal_for_generation,
    save_proposal,
)

router = APIRouter()


@router.post("/levels/{level_id}/generate", response_model=GenerateLessonsResponse)
@limiter.limit("5/minute")
async def generate_level_lessons_endpoint(
    request: Request,
    level_id: uuid.UUID,
    payload: GenerateLessonsRequest,
    _admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session),
):
    level = await session.get(Level, level_id)
    if level is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Level not found")
    result = await generate_level_lessons(
        session, level, concept=payload.concept, count=payload.count, types=payload.types,
    )
    return GenerateLessonsResponse(
        created=[LessonDraftOut.model_validate(d) for d in result.created],
        skipped=result.skipped,
    )


@router.post("/levels/{level_id}/generate-market", response_model=GenerateLessonsResponse)
@limiter.limit("5/minute")
async def generate_market_level_lessons_endpoint(
    request: Request,
    level_id: uuid.UUID,
    payload: GenerateMarketLessonsRequest,
    _admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session),
):
    target_level = await session.get(Level, level_id)
    if target_level is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Level not found")
    source_level = await session.get(Level, payload.source_level_id)
    if source_level is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source level not found")
    target_module = await session.get(Module, target_level.module_id)
    if target_module is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found")
    brief = await require_verified_brief(session, target_module.market_code)
    result = await generate_market_level_lessons(
        session, target_level, source_level=source_level, brief=brief,
    )
    return GenerateLessonsResponse(
        created=[LessonDraftOut.model_validate(d) for d in result.created],
        skipped=result.skipped,
    )


@router.post("/modules/{module_id}/generate-market")
@limiter.limit("5/minute")
async def generate_module_market_lessons_endpoint(
    request: Request,
    module_id: uuid.UUID,
    payload: GenerateModuleMarketRequest,
    _admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session),
):
    module = await session.get(Module, module_id)
    if module is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found")
    brief = await require_verified_brief(session, module.market_code)
    return await generate_module_market_lessons(
        session, module, brief=brief, include_populated=payload.include_populated,
    )


@router.post("/levels/{level_id}/generate-native", response_model=GenerateLessonsResponse)
@limiter.limit("5/minute")
async def generate_native_level_lessons_endpoint(
    request: Request,
    level_id: uuid.UUID,
    payload: GenerateNativeLessonsRequest,
    _admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session),
):
    level = await session.get(Level, level_id)
    if level is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Level not found")
    module = await session.get(Module, level.module_id)
    if module is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found")
    brief = await require_verified_brief(session, module.market_code)
    result = await generate_native_level_lessons(
        session, level, brief=brief, concepts=payload.concepts, types=payload.types,
    )
    return GenerateLessonsResponse(
        created=[LessonDraftOut.model_validate(d) for d in result.created],
        skipped=result.skipped,
    )


@router.post("/markets/{market_code}/curriculum/design", response_model=CurriculumDesignOut)
@limiter.limit("5/minute")
async def design_market_curriculum_endpoint(
    request: Request, market_code: str,
    _admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session),
):
    brief = await require_verified_brief(session, market_code)
    try:
        proposal, report = await design_curriculum(market_code, brief.brief_json)
    except CurriculumDesignError:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY,
                            detail="Could not design a curriculum, try again")
    row = await save_proposal(session, proposal, report)
    await session.commit()
    return CurriculumDesignOut(proposal_id=str(row.id), proposal=row.proposal_json,
                               coverage=row.coverage_json)


@router.get("/markets/{market_code}/curriculum", response_model=CurriculumDesignOut)
async def get_market_curriculum_endpoint(
    market_code: str,
    _admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session),
):
    # Prefer a staged proposal in progress (proposed/accepted); otherwise fall
    # back to the published one so a LIVE curriculum stays visible and can be
    # regenerated (the panel + lesson list key off this).
    row = await get_active_proposal(session, market_code)
    if row is None:
        row = await get_proposal_for_generation(session, market_code)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No curriculum")
    return CurriculumDesignOut(proposal_id=str(row.id), proposal=row.proposal_json,
                               coverage=row.coverage_json)


@router.post("/markets/{market_code}/curriculum/accept")
async def accept_market_curriculum_endpoint(
    market_code: str,
    _admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session),
):
    row = await get_active_proposal(session, market_code)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No curriculum")
    try:
        result = await accept_proposal(session, row)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    await session.commit()
    return result


@router.post("/markets/{market_code}/curriculum/publish")
async def publish_market_curriculum_endpoint(
    market_code: str,
    _admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session),
):
    try:
        result = await publish_market_curriculum(session, market_code)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    await session.commit()
    return result


@router.post("/modules/{module_id}/generate-native-batch")
@limiter.limit("5/minute")
async def generate_native_batch_endpoint(
    request: Request, module_id: uuid.UUID,
    payload: GenerateModuleMarketRequest,
    _admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session),
):
    module = await session.get(Module, module_id)
    if module is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found")
    brief = await require_verified_brief(session, module.market_code)
    proposal_row = await get_proposal_for_generation(session, module.market_code)
    if proposal_row is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail="No accepted or published curriculum for this market")
    summary = await generate_market_native(
        session, module, brief=brief, proposal_row=proposal_row,
        include_populated=payload.include_populated)
    await session.commit()
    return summary
