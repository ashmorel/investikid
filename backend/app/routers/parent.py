import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_session
from app.models.audit import AuditLog
from app.models.group import GroupMembership, LeaderboardGroup
from app.models.parent_preferences import ParentPreferences
from app.models.premium_request import PremiumRequest
from app.models.user import User
from app.routers.auth import _cookie_samesite
from app.routers.parent_auth import _PARENT_COOKIE, get_current_parent
from app.schemas.group import GroupCreateRequest, GroupJoinRequest, GroupMemberOut, GroupOut
from app.schemas.parent import (
    AccountDeleteRequest,
    ChildOut,
    FreezeRequest,
    MasteryReportOut,
    PremiumRequestOut,
    PremiumToggleRequest,
    PushToggleRequest,
    TierOverrideOut,
    TierOverrideRequest,
)
from app.schemas.parent_preferences import ParentPreferencesOut, ParentPreferencesUpdate
from app.services import group_service
from app.services.account_deletion_service import delete_parent_account
from app.services.analytics_service import build_child_analytics
from app.services.content_service import content_region_for
from app.services.entitlements import set_premium
from app.services.export_service import build_user_export
from app.services.mastery_report_service import build_mastery_report

router = APIRouter(prefix="/parent", tags=["parent"])


async def _get_owned_child(
    session: AsyncSession, parent_email: str, user_id: uuid.UUID,
) -> User:
    user = await session.scalar(
        select(User).where(
            User.id == user_id,
            User.parent_email == parent_email,
        ).execution_options(include_deleted=True)
    )
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Child not found")
    return user


@router.get("/children", response_model=list[ChildOut])
async def list_children(
    parent_email: str = Depends(get_current_parent),
    session: AsyncSession = Depends(get_session),
):
    rows = (await session.scalars(
        select(User).where(User.parent_email == parent_email)
        .execution_options(include_deleted=True)
        .order_by(User.created_at)
    )).all()

    children = []
    for r in rows:
        analytics = None
        if r.deleted_at is None:
            analytics = await build_child_analytics(session, r.id, content_region_for(r))
        children.append(
            ChildOut(
                user_id=r.id, username=r.username, country_code=r.country_code,
                is_active=r.is_active, is_premium=r.is_premium,
                push_enabled=r.push_enabled,
                parent_consent_given_at=r.parent_consent_given_at,
                consent_declined_at=r.consent_declined_at,
                deleted_at=r.deleted_at,
                deletion_requested_at=r.deletion_requested_at,
                age_tier=r.age_tier,
                tier_override=r.tier_override,
                analytics=analytics,
            )
        )
    return children


@router.get("/mastery-report", response_model=MasteryReportOut)
async def mastery_report(
    days: int = Query(default=30, ge=1, le=180),
    parent_email: str = Depends(get_current_parent),
    session: AsyncSession = Depends(get_session),
):
    return await build_mastery_report(session, parent_email, days=days)


@router.get("/preferences", response_model=ParentPreferencesOut)
async def get_preferences(
    parent_email: str = Depends(get_current_parent),
    session: AsyncSession = Depends(get_session),
):
    pref = await session.get(ParentPreferences, parent_email)
    return ParentPreferencesOut(
        trial_reminder_opt_out=bool(pref and pref.trial_reminder_opt_out),
        weekly_digest_opt_out=bool(pref and pref.weekly_digest_opt_out),
    )


@router.patch("/preferences", response_model=ParentPreferencesOut)
async def update_preferences(
    body: ParentPreferencesUpdate,
    parent_email: str = Depends(get_current_parent),
    session: AsyncSession = Depends(get_session),
):
    updates = body.model_dump(exclude_unset=True, exclude_none=True)
    pref = await session.get(ParentPreferences, parent_email)
    if pref is None:
        pref = ParentPreferences(parent_email=parent_email, **updates)
        session.add(pref)
    else:
        for field, value in updates.items():
            setattr(pref, field, value)
    await session.commit()
    return ParentPreferencesOut(
        trial_reminder_opt_out=pref.trial_reminder_opt_out,
        weekly_digest_opt_out=pref.weekly_digest_opt_out,
    )


@router.get("/premium-requests", response_model=list[PremiumRequestOut])
async def list_premium_requests(
    parent_email: str = Depends(get_current_parent),
    session: AsyncSession = Depends(get_session),
):
    rows = (await session.execute(
        select(PremiumRequest, User.username)
        .join(User, User.id == PremiumRequest.child_user_id)
        .where(PremiumRequest.parent_email == parent_email,
               PremiumRequest.resolved_at.is_(None),
               PremiumRequest.declined_at.is_(None))
        .order_by(PremiumRequest.created_at.desc())
    )).all()
    return [
        PremiumRequestOut(id=r.id, child_username=username, context_kind=r.context_kind,
                          context_label=r.context_label, created_at=r.created_at)
        for r, username in rows
    ]


@router.post("/premium-requests/{request_id}/decline")
async def decline_premium_request(
    request_id: uuid.UUID,
    parent_email: str = Depends(get_current_parent),
    session: AsyncSession = Depends(get_session),
):
    row = await session.scalar(select(PremiumRequest).where(
        PremiumRequest.id == request_id,
        PremiumRequest.parent_email == parent_email))
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
    if row.declined_at is None and row.resolved_at is None:
        row.declined_at = datetime.now(UTC)
        await session.commit()
    return {"status": "ok"}


@router.post("/children/{user_id}/freeze")
async def freeze_child(
    user_id: uuid.UUID,
    payload: FreezeRequest,
    parent_email: str = Depends(get_current_parent),
    session: AsyncSession = Depends(get_session),
):
    child = await _get_owned_child(session, parent_email, user_id)
    if child.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Account deleted")
    child.is_active = not payload.frozen
    await session.commit()
    return {"status": "ok", "frozen": payload.frozen}


@router.post("/children/{user_id}/push")
async def set_child_push(
    user_id: uuid.UUID,
    payload: PushToggleRequest,
    parent_email: str = Depends(get_current_parent),
    session: AsyncSession = Depends(get_session),
):
    """Parent master switch for server push (M7). Both this AND the child's
    in-app toggle must be on before any device token is registered."""
    child = await _get_owned_child(session, parent_email, user_id)
    if child.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Account deleted")
    child.push_enabled = payload.enabled
    session.add(AuditLog(
        user_id=child.id,
        event_type="push_enabled" if payload.enabled else "push_disabled",
        metadata_json={"actor": f"parent:{parent_email}"},
    ))
    await session.commit()
    return {"status": "ok", "push_enabled": payload.enabled}


@router.post("/children/{user_id}/premium")
async def set_child_premium(
    user_id: uuid.UUID,
    payload: PremiumToggleRequest,
    parent_email: str = Depends(get_current_parent),
    session: AsyncSession = Depends(get_session),
):
    child = await _get_owned_child(session, parent_email, user_id)
    if child.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Account deleted")
    await set_premium(session, child, value=payload.premium, actor=parent_email)
    await session.commit()
    return {"status": "ok", "premium": payload.premium}


@router.post("/children/{user_id}/tier", response_model=TierOverrideOut)
async def set_child_tier_override(
    user_id: uuid.UUID,
    payload: TierOverrideRequest,
    parent_email: str = Depends(get_current_parent),
    session: AsyncSession = Depends(get_session),
):
    child = await _get_owned_child(session, parent_email, user_id)
    if child.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Account deleted")
    child.tier_override = payload.tier_override
    await session.commit()
    return TierOverrideOut(tier_override=child.tier_override, age_tier=child.age_tier)


@router.post("/children/{user_id}/erasure")
async def erase_child(
    user_id: uuid.UUID,
    parent_email: str = Depends(get_current_parent),
    session: AsyncSession = Depends(get_session),
):
    child = await _get_owned_child(session, parent_email, user_id)
    if child.deleted_at is not None:
        return {"status": "already_deleted"}
    now = datetime.now(UTC)
    child.deletion_requested_at = now
    child.deleted_at = now
    child.is_active = False
    await session.commit()
    return {"status": "ok"}


@router.post("/account/delete")
async def delete_account(
    payload: AccountDeleteRequest,
    response: Response,
    parent_email: str = Depends(get_current_parent),
    session: AsyncSession = Depends(get_session),
):
    """Irreversibly delete the parent account (Apple Guideline 5.1.1(v)).

    Parent auth is passwordless, so the destructive gate is a typed-email
    confirmation: the body must echo the authenticated parent's own email.
    """
    if payload.confirm_email.strip().lower() != parent_email.lower():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Confirmation email does not match",
        )
    result = await delete_parent_account(session, parent_email)
    # Clear the parent session cookie exactly like logout does.
    secure = settings.environment != "development"
    response.delete_cookie(
        _PARENT_COOKIE,
        samesite=_cookie_samesite(),
        secure=secure,
        httponly=True,
        path="/",
    )
    return result


@router.get("/children/{user_id}/export")
async def export_child_data(
    user_id: uuid.UUID,
    parent_email: str = Depends(get_current_parent),
    session: AsyncSession = Depends(get_session),
):
    child = await _get_owned_child(session, parent_email, user_id)
    if child.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Account deleted")
    data = await build_user_export(session, child)
    return JSONResponse(
        content=data,
        headers={"Content-Disposition": 'attachment; filename="invest-ed-child-export.json"'},
    )


async def _group_out(session: AsyncSession, group: LeaderboardGroup, parent_email: str) -> GroupOut:
    rows = (await session.execute(
        select(GroupMembership.user_id, User.username)
        .join(User, User.id == GroupMembership.user_id)
        .where(GroupMembership.group_id == group.id)
        .order_by(User.username)
    )).all()
    is_owner = group.owner_parent_email == parent_email
    return GroupOut(
        id=group.id, name=group.name,
        code=group.code if is_owner else None,
        is_owner=is_owner,
        members=[GroupMemberOut(child_user_id=uid, username=uname) for uid, uname in rows],
    )


@router.post("/groups", response_model=GroupOut, status_code=201)
async def create_group(
    payload: GroupCreateRequest,
    parent_email: str = Depends(get_current_parent),
    session: AsyncSession = Depends(get_session),
):
    try:
        group = await group_service.create_group(session, parent_email, payload.name)
    except group_service.GroupLimitError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Group limit reached")
    await session.commit()
    return GroupOut(id=group.id, name=group.name, code=group.code, is_owner=True, members=[])


@router.post("/groups/join", response_model=GroupOut)
async def join_group(
    payload: GroupJoinRequest,
    parent_email: str = Depends(get_current_parent),
    session: AsyncSession = Depends(get_session),
):
    child = await _get_owned_child(session, parent_email, payload.child_user_id)
    try:
        group = await group_service.join_child(session, payload.code, child, parent_email)
    except group_service.GroupNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    except group_service.GroupLimitError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Group is full")
    await session.commit()
    return await _group_out(session, group, parent_email)


@router.get("/groups", response_model=list[GroupOut])
async def list_groups(
    parent_email: str = Depends(get_current_parent),
    session: AsyncSession = Depends(get_session),
):
    owned = (await session.scalars(
        select(LeaderboardGroup).where(LeaderboardGroup.owner_parent_email == parent_email)
    )).all()
    child_group_ids = (await session.scalars(
        select(GroupMembership.group_id)
        .join(User, User.id == GroupMembership.user_id)
        .where(User.parent_email == parent_email)
    )).all()
    member_groups = (await session.scalars(
        select(LeaderboardGroup).where(LeaderboardGroup.id.in_(child_group_ids))
    )).all() if child_group_ids else []
    seen: dict = {}
    for g in [*owned, *member_groups]:
        seen[g.id] = g
    return [await _group_out(session, g, parent_email) for g in seen.values()]


@router.delete("/groups/{group_id}/members/{child_user_id}", status_code=200)
async def remove_group_member(
    group_id: uuid.UUID,
    child_user_id: uuid.UUID,
    parent_email: str = Depends(get_current_parent),
    session: AsyncSession = Depends(get_session),
):
    await _get_owned_child(session, parent_email, child_user_id)
    await group_service.remove_member(session, group_id, child_user_id)
    await session.commit()
    return {"status": "ok"}


@router.delete("/groups/{group_id}", status_code=200)
async def delete_group(
    group_id: uuid.UUID,
    parent_email: str = Depends(get_current_parent),
    session: AsyncSession = Depends(get_session),
):
    group = await session.scalar(
        select(LeaderboardGroup).where(
            LeaderboardGroup.id == group_id, LeaderboardGroup.owner_parent_email == parent_email
        )
    )
    if group is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    await group_service.delete_group(session, group)
    await session.commit()
    return {"status": "ok"}
