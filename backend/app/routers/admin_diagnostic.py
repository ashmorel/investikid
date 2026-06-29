"""Admin router for diagnostic item management (Task 3).

Mounted under /admin by admin.py (which already enforces get_current_admin).
The generate endpoint is additionally rate-limited (LLM call).

Lifecycle:
    draft  ─► approved  (approve)
    draft  ─► retired   (reject — kept for audit, never served)
    approved ─► retired (retire — e.g. non-discriminating item)
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.rate_limit import limiter
from app.models.user import User
from app.routers.admin_auth import get_current_admin
from app.schemas.diagnostic import (
    DiagnosticGenerateRequest,
    DiagnosticItemPatch,
    DiagnosticItemRead,
    DiagnosticListResponse,
)
from app.services.diagnostic_item_service import (
    approve_item,
    generate_items,
    get_item,
    list_items,
    patch_item,
    reject_item,
    retire_item,
)

router = APIRouter()

# ---------------------------------------------------------------------------
# POST /admin/diagnostic-items/generate
# ---------------------------------------------------------------------------


@router.post("/diagnostic-items/generate", response_model=list[DiagnosticItemRead])
@limiter.limit("5/minute")
async def generate_diagnostic_items(
    request: Request,
    payload: DiagnosticGenerateRequest,
    _admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session),
) -> list[DiagnosticItemRead]:
    """Generate draft diagnostic items via the LLM."""
    items = await generate_items(
        session,
        market_code=payload.market_code,
        topic=payload.topic,
        difficulty_tier=payload.difficulty_tier,
        count=payload.count,
    )
    await session.commit()
    return [DiagnosticItemRead.model_validate(i) for i in items]


# ---------------------------------------------------------------------------
# GET /admin/diagnostic-items
# ---------------------------------------------------------------------------


@router.get("/diagnostic-items", response_model=DiagnosticListResponse)
async def list_diagnostic_items(
    market_code: str | None = None,
    topic: str | None = None,
    status: str | None = None,
    _admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session),
) -> DiagnosticListResponse:
    """List diagnostic items with optional filters + approved coverage summary."""
    items, coverage = await list_items(
        session, market_code=market_code, topic=topic, status=status
    )
    return DiagnosticListResponse(
        items=[DiagnosticItemRead.model_validate(i) for i in items],
        coverage=coverage,
    )


# ---------------------------------------------------------------------------
# PATCH /admin/diagnostic-items/{id}
# ---------------------------------------------------------------------------


@router.patch("/diagnostic-items/{item_id}", response_model=DiagnosticItemRead)
async def edit_diagnostic_item(
    item_id: uuid.UUID,
    payload: DiagnosticItemPatch,
    _admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session),
) -> DiagnosticItemRead:
    """Edit a draft diagnostic item.  Returns 409 if not in draft status."""
    item = await get_item(session, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    if item.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot edit item with status '{item.status}'; only draft items may be edited",
        )
    item = await patch_item(
        session,
        item,
        fields_set=payload.model_fields_set,
        question=payload.question,
        choices=payload.choices,
        answer_index=payload.answer_index,
        explanation=payload.explanation,
        difficulty_tier=payload.difficulty_tier,
        concept_id=payload.concept_id,
    )
    await session.commit()
    return DiagnosticItemRead.model_validate(item)


# ---------------------------------------------------------------------------
# POST /admin/diagnostic-items/{id}/approve
# ---------------------------------------------------------------------------


@router.post("/diagnostic-items/{item_id}/approve", response_model=DiagnosticItemRead)
async def approve_diagnostic_item(
    item_id: uuid.UUID,
    admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session),
) -> DiagnosticItemRead:
    """Transition a draft item to approved."""
    item = await get_item(session, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    if item.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot approve item with status '{item.status}'; must be draft",
        )
    item = await approve_item(session, item, admin_id=admin.id)
    await session.commit()
    return DiagnosticItemRead.model_validate(item)


# ---------------------------------------------------------------------------
# POST /admin/diagnostic-items/{id}/reject
# ---------------------------------------------------------------------------


@router.post("/diagnostic-items/{item_id}/reject", response_model=DiagnosticItemRead)
async def reject_diagnostic_item(
    item_id: uuid.UUID,
    _admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session),
) -> DiagnosticItemRead:
    """Transition a draft item to retired (kept for audit)."""
    item = await get_item(session, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    if item.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot reject item with status '{item.status}'; must be draft",
        )
    item = await reject_item(session, item)
    await session.commit()
    return DiagnosticItemRead.model_validate(item)


# ---------------------------------------------------------------------------
# POST /admin/diagnostic-items/{id}/retire
# ---------------------------------------------------------------------------


@router.post("/diagnostic-items/{item_id}/retire", response_model=DiagnosticItemRead)
async def retire_diagnostic_item(
    item_id: uuid.UUID,
    _admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session),
) -> DiagnosticItemRead:
    """Transition an approved item to retired."""
    item = await get_item(session, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    if item.status != "approved":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot retire item with status '{item.status}'; must be approved",
        )
    item = await retire_item(session, item)
    await session.commit()
    return DiagnosticItemRead.model_validate(item)
