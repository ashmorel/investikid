"""Admin router for diagnostic item management (Task 3).

Mounted under /admin by admin.py (which already enforces get_current_admin).
The generate and verify-sweep endpoints are additionally rate-limited (LLM calls).

Lifecycle:
    draft  ─► approved  (approve)
    draft  ─► retired   (reject — kept for audit, never served)
    approved ─► retired (retire — e.g. non-discriminating item)
    approved ─► draft   (unpublish — to fix & re-approve)

Plus an in-place flag action that does NOT change status:
    approved (flagged) ─► approved (clear-verifier-flag — dismiss a false positive)
"""
from __future__ import annotations

import logging
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
    DiagnosticSweepRequest,
    DiagnosticSweepResponse,
    FlaggedItem,
)
from app.services.diagnostic_item_service import (
    approve_item,
    clear_verifier_flag,
    generate_items,
    get_item,
    list_items,
    patch_item,
    reject_item,
    retire_item,
    run_verify_sweep,
    unpublish_item,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# POST /admin/diagnostic-items/verify  (sweep)
# ---------------------------------------------------------------------------


@router.post("/diagnostic-items/verify", response_model=DiagnosticSweepResponse)
@limiter.limit("5/minute")
async def verify_sweep_diagnostic_items(
    request: Request,
    payload: DiagnosticSweepRequest,
    _admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session),
) -> DiagnosticSweepResponse:
    """Run the independent answer-verifier over matching diagnostic items.

    Selects items using the supplied filters (market_code, topic, status,
    only_unverified) bounded by ``limit``, runs ``verify_item`` on each
    (best-effort — one LLM failure sets verifier_status="error" and never
    aborts the sweep), then commits and returns counts + the list of flagged
    (mismatch + ambiguous) items.

    This endpoint NEVER changes answer_index or status — advisory only.
    """
    result = await run_verify_sweep(
        session,
        status=payload.status,
        market_code=payload.market_code,
        topic=payload.topic,
        limit=payload.limit,
        only_unverified=payload.only_unverified,
        tier=payload.tier,
    )
    await session.commit()
    return DiagnosticSweepResponse(
        verified=result["verified"],
        agree=result["agree"],
        mismatch=result["mismatch"],
        ambiguous=result["ambiguous"],
        error=result["error"],
        flagged=[FlaggedItem(**f) for f in result["flagged"]],
    )


# ---------------------------------------------------------------------------
# POST /admin/diagnostic-items/generate
# ---------------------------------------------------------------------------


@router.post("/diagnostic-items/generate", response_model=list[DiagnosticItemRead])
@limiter.limit("20/minute")
async def generate_diagnostic_items(
    request: Request,
    payload: DiagnosticGenerateRequest,
    _admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session),
) -> list[DiagnosticItemRead]:
    """Generate draft diagnostic items via the LLM.

    Admin-gated. The limit is 20/min (not 5) so an operator can bulk-generate
    several topics for a market/tier in one go — the admin UI fires one request
    per selected topic (kept per-topic so each stays well under the gateway timeout).
    """
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
    verifier: str | None = None,
    _admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session),
) -> DiagnosticListResponse:
    """List diagnostic items with optional filters + approved coverage summary.

    Optional ``verifier=needs_review`` restricts to items with
    verifier_status IN (mismatch, ambiguous).
    """
    items, coverage = await list_items(
        session, market_code=market_code, topic=topic, status=status, verifier=verifier
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


# ---------------------------------------------------------------------------
# POST /admin/diagnostic-items/{id}/unpublish
# ---------------------------------------------------------------------------


@router.post("/diagnostic-items/{item_id}/unpublish", response_model=DiagnosticItemRead)
async def unpublish_diagnostic_item(
    item_id: uuid.UUID,
    _admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session),
) -> DiagnosticItemRead:
    """Transition an approved item back to draft so it can be corrected and re-approved."""
    item = await get_item(session, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    if item.status != "approved":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot unpublish item with status '{item.status}'; must be approved",
        )
    item = await unpublish_item(session, item)
    await session.commit()
    return DiagnosticItemRead.model_validate(item)


# ---------------------------------------------------------------------------
# POST /admin/diagnostic-items/{id}/clear-verifier-flag
# ---------------------------------------------------------------------------


@router.post(
    "/diagnostic-items/{item_id}/clear-verifier-flag",
    response_model=DiagnosticItemRead,
)
async def clear_diagnostic_verifier_flag(
    item_id: uuid.UUID,
    _admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session),
) -> DiagnosticItemRead:
    """Dismiss an advisory verifier flag on an approved item judged correct.

    Clears the verifier_* fields in place — the item stays approved/published and
    its answer is untouched — so a false-positive flag drops out of needs_review.
    """
    item = await get_item(session, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    if item.status != "approved":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot clear flag on item with status '{item.status}'; must be approved",
        )
    item = await clear_verifier_flag(session, item)
    await session.commit()
    return DiagnosticItemRead.model_validate(item)
