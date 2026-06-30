"""Diagnostic router — child-facing assessment endpoints.

Task 2: POST /diagnostic/start  — item selection + session creation.
Task 3: POST /diagnostic/submit — server-side scoring + checkpoint.
Task 4: GET  /diagnostic/evidence — read-only baseline vs progress comparison.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.rate_limit import limiter
from app.models.user import User
from app.routers.users import get_current_user
from app.schemas.diagnostic_session import (
    CheckpointTopicOut,
    DiagnosticStartRequest,
    DiagnosticStartResponse,
    DiagnosticSubmitRequest,
    DiagnosticSubmitResponse,
)
from app.services import diagnostic_service

router = APIRouter(prefix="/diagnostic", tags=["diagnostic"])


@router.post("/start", response_model=DiagnosticStartResponse)
@limiter.limit("20/hour")
async def start_diagnostic(
    request: Request,
    body: DiagnosticStartRequest | None = None,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> DiagnosticStartResponse:
    """Select approved diagnostic items and open a DiagnosticSession.

    Returns the session id and the item list (no answer_index, no
    explanation).  On empty bank returns session with items=[].

    ``kind`` (baseline | progress) is taken from the request body and
    validated to those two values; it defaults to ``"baseline"`` when no body
    is sent (the onboarding flow).
    """
    kind = body.kind if body is not None else "baseline"
    diag_session, items = await diagnostic_service.start_diagnostic(
        session, user, kind=kind
    )
    await session.commit()
    return DiagnosticStartResponse(
        session_id=diag_session.id,
        items=items,
    )


@router.post("/submit", response_model=DiagnosticSubmitResponse)
@limiter.limit("20/hour")
async def submit_diagnostic(
    body: DiagnosticSubmitRequest,
    request: Request,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> DiagnosticSubmitResponse:
    """Score a diagnostic session and write an immutable MasteryCheckpoint.

    The server scores every item authoritatively — client-sent scores are
    never trusted.  Returns the checkpoint summary including per-topic
    breakdowns.  No XP, streak, or coin rewards are issued.

    Errors:
    - 404 if the session does not exist.
    - 403 if the session belongs to another user.
    - 409 if the session has already been completed.
    """
    checkpoint = await diagnostic_service.submit_diagnostic(
        session,
        user,
        session_id=body.session_id,
        answers=body.answers,
        skipped=body.skipped,
    )
    await session.commit()
    # Reload topic rows (flush guarantees they are persisted)
    await session.refresh(checkpoint, ["topics"])
    return DiagnosticSubmitResponse(
        kind=checkpoint.kind,
        overall_score=checkpoint.overall_score,
        session_count=checkpoint.session_count,
        topics=[
            CheckpointTopicOut(
                topic=t.topic,
                correct=t.correct,
                attempted=t.attempted,
            )
            for t in checkpoint.topics
        ],
    )


@router.get("/recheck-status")
async def get_recheck_status(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Return the re-check-due signal for the authenticated child.

    Response:
      due            — true when the next milestone is reached and unchecked
      milestone      — the next active-days milestone (5/15/30), or null when all done
      active_days    — the child's total active-days count from UserProgress
      completed_checks — number of completed progress checkpoints
    """
    return await diagnostic_service.recheck_status(session, user)


@router.get("/evidence")
async def get_evidence(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Return the read-only evidence comparison for the authenticated child.

    Compares the child's baseline checkpoint (earliest baseline/skipped) to
    their most recent progress checkpoint, computing per-topic and overall
    mastery deltas.

    States:
    - No baseline  → {has_baseline: false, ...nulls}
    - Skipped baseline → {has_baseline: true, baseline_skipped: true, baseline: null, ...}
    - Baseline only → baseline present, latest/deltas null/empty
    - Baseline + progress → full comparison including deltas
    """
    return await diagnostic_service.get_evidence(session, user)
