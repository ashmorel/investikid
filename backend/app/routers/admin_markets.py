import json

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.rate_limit import limiter
from app.models.content import Lesson, Level, Module
from app.models.market import Market
from app.models.market_brief import MarketBrief
from app.schemas.admin import (
    CuratedModuleSuggestion,
    MarketBriefOut,
    MarketBriefUpdate,
    MarketScaffoldResult,
    ModuleFromSuggestionResult,
    ModuleSuggestion,
)
from app.services.market_brief_service import (
    BriefGenerationError,
    generate_brief,
)
from app.services.market_module_suggester import suggest_modules
from app.services.market_scaffold_service import scaffold_market_from_gb

router = APIRouter()


# ── Market briefs ───────────────────────────────────────────────────
@router.post("/markets/{code}/brief/generate", response_model=MarketBriefOut)
@limiter.limit("5/minute")
async def generate_market_brief(
    request: Request,
    code: str,
    session: AsyncSession = Depends(get_session),
):
    market = await session.get(Market, code)
    if market is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Market not found")
    try:
        brief = await generate_brief(session, market)
    except (BriefGenerationError, ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail="brief generation failed"
        ) from exc
    await session.commit()
    return MarketBriefOut.model_validate(brief)


@router.get("/markets/{code}/brief", response_model=MarketBriefOut)
async def get_market_brief(code: str, session: AsyncSession = Depends(get_session)):
    brief = await session.get(MarketBrief, code)
    if brief is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brief not found")
    return MarketBriefOut.model_validate(brief)


@router.put("/markets/{code}/brief", response_model=MarketBriefOut)
async def update_market_brief(
    code: str,
    payload: MarketBriefUpdate,
    session: AsyncSession = Depends(get_session),
):
    brief = await session.get(MarketBrief, code)
    if brief is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brief not found")
    if not isinstance(payload.brief_json, dict):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="brief_json must be an object"
        )
    brief.brief_json = payload.brief_json
    await session.commit()
    return MarketBriefOut.model_validate(brief)


@router.post("/markets/{code}/brief/verify", response_model=MarketBriefOut)
async def verify_market_brief(code: str, session: AsyncSession = Depends(get_session)):
    brief = await session.get(MarketBrief, code)
    if brief is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brief not found")
    brief.status = "verified"
    await session.commit()
    return MarketBriefOut.model_validate(brief)


@router.post("/markets/{code}/scaffold", response_model=MarketScaffoldResult)
@limiter.limit("5/minute")
async def scaffold_market(
    request: Request,
    code: str,
    session: AsyncSession = Depends(get_session),
):
    market = await session.get(Market, code)
    if market is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Market not found")
    summary = await scaffold_market_from_gb(session, code)
    return MarketScaffoldResult.model_validate(summary)


@router.post("/markets/{code}/module-suggestions", response_model=list[ModuleSuggestion])
@limiter.limit("5/minute")
async def market_module_suggestions(
    request: Request,
    code: str,
    session: AsyncSession = Depends(get_session),
):
    market = await session.get(Market, code)
    if market is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Market not found")
    suggestions = await suggest_modules(session, market)
    return [ModuleSuggestion(**s) for s in suggestions]


@router.post(
    "/markets/{code}/modules/from-suggestion", response_model=ModuleFromSuggestionResult
)
@limiter.limit("5/minute")
async def create_module_from_suggestion(
    request: Request,
    code: str,
    body: CuratedModuleSuggestion,
    session: AsyncSession = Depends(get_session),
):
    """One-click scaffold: create a new module + one starter level (no lessons) in
    the given market from a curated suggester item. No auto-publish, no auto-delete."""
    market = await session.get(Market, code)
    if market is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Market not found")
    max_order = await session.scalar(
        select(func.max(Module.order_index)).where(Module.market_code == code)
    )
    module = Module(
        topic=(body.topic or "general")[:30],
        title=body.title,
        country_codes=[],
        market_code=code,
        is_premium=False,
        order_index=(max_order or -1) + 1,
        prerequisite_ids=[],
    )
    session.add(module)
    await session.flush()
    level = Level(module_id=module.id, title="Level 1", order_index=0, is_premium=False)
    session.add(level)
    await session.commit()
    return ModuleFromSuggestionResult(
        module_id=module.id,
        level_id=level.id,
        suggested_concepts=body.suggested_concepts,
    )


@router.post("/markets/{code}/publish")
async def publish_market(code: str, session: AsyncSession = Depends(get_session)):
    market = await session.get(Market, code)
    if market is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Market not found")
    lesson_count = await session.scalar(
        select(func.count(Lesson.id))
        .select_from(Lesson)
        .join(Module, Module.id == Lesson.module_id)
        .where(Module.market_code == code)
    ) or 0
    if lesson_count == 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="market has no lessons to publish"
        )
    market.has_content = True
    await session.commit()
    return {"code": code, "has_content": True}


@router.post("/markets/{code}/unpublish")
async def unpublish_market(code: str, session: AsyncSession = Depends(get_session)):
    market = await session.get(Market, code)
    if market is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Market not found")
    market.has_content = False
    await session.commit()
    return {"code": code, "has_content": False}
