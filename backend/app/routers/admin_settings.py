import json
import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.user import User
from app.schemas.admin import (
    AdminSettingsOut,
    AdminSettingsUpdate,
)
from app.schemas.parent import PremiumToggleRequest
from app.services.app_settings import (
    get_alert_emails,
    get_enabled_content_languages,
    get_investing_mission_cash,
    get_market_completion_bonus_coins,
    get_market_enroll_bonus_coins,
    get_setting,
    get_starting_cash,
    get_trade_commission_pct,
    set_alert_emails,
    set_enabled_content_languages,
    set_investing_mission_cash,
    set_market_completion_bonus_coins,
    set_market_enroll_bonus_coins,
    set_starting_cash,
    set_trade_commission_pct,
)
from app.services.entitlements import set_premium
from app.services.event_service import EVENT_KEY, set_event
from app.services.llm_client import probe_all_providers

router = APIRouter()


# ── Utility ─────────────────────────────────────────────────────────
@router.get("/countries")
async def list_countries(session: AsyncSession = Depends(get_session)):
    result = await session.scalars(
        select(User.country_code).where(User.country_code.isnot(None)).distinct()
    )
    return sorted(result.all())


# ── Settings ────────────────────────────────────────────────────────
@router.get("/settings", response_model=AdminSettingsOut)
async def get_settings(session: AsyncSession = Depends(get_session)):
    emails = await get_alert_emails(session)
    cash = await get_starting_cash(session)
    mission_cash = await get_investing_mission_cash(session)
    pct = await get_trade_commission_pct(session)
    enroll_bonus = await get_market_enroll_bonus_coins(session)
    completion_bonus = await get_market_completion_bonus_coins(session)
    content_languages = await get_enabled_content_languages(session)
    raw_event = await get_setting(session, EVENT_KEY)
    return AdminSettingsOut(
        alert_emails=emails,
        starting_cash={k: str(v) for k, v in cash.items()},
        investing_mission_cash={k: str(v) for k, v in mission_cash.items()},
        trade_commission_pct=str(pct),
        market_enroll_bonus_coins=enroll_bonus,
        market_completion_bonus_coins=completion_bonus,
        enabled_content_languages=content_languages,
        seasonal_event=json.loads(raw_event) if raw_event else None,
    )


@router.put("/settings", response_model=AdminSettingsOut)
async def update_settings(
    body: AdminSettingsUpdate, session: AsyncSession = Depends(get_session),
):
    await set_alert_emails(session, body.alert_emails)
    if body.starting_cash is not None:
        await set_starting_cash(session, {k: Decimal(v) for k, v in body.starting_cash.items()})
    if body.investing_mission_cash is not None:
        await set_investing_mission_cash(
            session, {k: Decimal(v) for k, v in body.investing_mission_cash.items()}
        )
    if body.trade_commission_pct is not None:
        await set_trade_commission_pct(session, Decimal(body.trade_commission_pct))
    if body.market_enroll_bonus_coins is not None:
        await set_market_enroll_bonus_coins(session, body.market_enroll_bonus_coins)
    if body.market_completion_bonus_coins is not None:
        await set_market_completion_bonus_coins(session, body.market_completion_bonus_coins)
    if body.enabled_content_languages is not None:
        await set_enabled_content_languages(session, body.enabled_content_languages)
    if body.clear_seasonal_event:
        await set_event(session, None)
    elif body.seasonal_event is not None:
        await set_event(session, {
            "title": body.seasonal_event.title,
            "emoji": body.seasonal_event.emoji,
            "starts_at": body.seasonal_event.starts_at.isoformat(),
            "ends_at": body.seasonal_event.ends_at.isoformat(),
            "xp_bonus_pct": body.seasonal_event.xp_bonus_pct,
        })
    await session.commit()
    cash = await get_starting_cash(session)
    mission_cash = await get_investing_mission_cash(session)
    pct = await get_trade_commission_pct(session)
    enroll_bonus = await get_market_enroll_bonus_coins(session)
    completion_bonus = await get_market_completion_bonus_coins(session)
    content_languages = await get_enabled_content_languages(session)
    raw_event = await get_setting(session, EVENT_KEY)
    return AdminSettingsOut(
        alert_emails=body.alert_emails,
        starting_cash={k: str(v) for k, v in cash.items()},
        investing_mission_cash={k: str(v) for k, v in mission_cash.items()},
        trade_commission_pct=str(pct),
        market_enroll_bonus_coins=enroll_bonus,
        market_completion_bonus_coins=completion_bonus,
        enabled_content_languages=content_languages,
        seasonal_event=json.loads(raw_event) if raw_event else None,
    )


# ── Premium comp (admin-only) ────────────────────────────────────────────────
@router.post("/users/{user_id}/premium")
async def admin_set_user_premium(
    user_id: uuid.UUID,
    payload: PremiumToggleRequest,
    session: AsyncSession = Depends(get_session),
):
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "user_not_found")
    await set_premium(session, user, value=payload.premium, actor="admin")
    await session.commit()
    return {"status": "ok", "premium": payload.premium}


# ── LLM provider health probe ────────────────────────────────────────────────
@router.get("/llm-status")
async def llm_status() -> list[dict]:
    """Ping each configured LLM provider with a trivial completion.

    Returns per-provider ok/error status without exposing any API key material.
    Admin-only (enforced by the router-level dependency).
    """
    return await probe_all_providers()
