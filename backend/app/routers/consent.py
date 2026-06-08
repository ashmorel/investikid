import uuid
from datetime import UTC, date, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_session
from app.core.rate_limit import limiter
from app.models.user import User
from app.schemas.consent import ChildSummary, ConsentDecision
from app.services.consent_service import age_in_years
from app.services.email import get_email_sender
from app.services.tokens import (
    CONSENT_AUDIENCE,
    CONSENT_EXPIRY,
    TokenAlreadyUsed,
    TokenExpired,
    TokenInvalid,
    consume_one_time_token,
    issue_one_time_token,
)

router = APIRouter(tags=["consent"])


def _gone(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_410_GONE, detail=detail)


@router.get("/consent/verify", response_model=ChildSummary)
async def verify_consent_token(
    token: str,
    session: AsyncSession = Depends(get_session),
):
    """Peek at the token without consuming it. Mutation happens in /decide."""
    try:
        payload = jwt.decode(
            token, settings.jwt_secret,
            algorithms=[settings.jwt_algorithm], audience=CONSENT_AUDIENCE,
        )
    except JWTError:
        raise _gone("Link invalid or expired")
    try:
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError):
        raise _gone("Link invalid")
    user = await session.get(User, user_id)
    if not user:
        raise _gone("Link invalid")
    if user.parent_consent_given_at is not None or user.consent_declined_at is not None:
        raise _gone("Already decided")
    age = age_in_years(user.dob, date.today())
    return ChildSummary(username=user.username, age=age, country_code=user.country_code)


@router.post("/consent/decide", status_code=200)
async def decide_consent(
    token: str,
    payload: ConsentDecision,
    session: AsyncSession = Depends(get_session),
):
    if payload.decision == "approve" and payload.attest_guardian is not True:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Guardian attestation required",
        )
    try:
        record = await consume_one_time_token(session, token, CONSENT_AUDIENCE)
    except TokenInvalid:
        raise _gone("Link invalid or expired")
    except TokenExpired:
        raise _gone("Link expired")
    except TokenAlreadyUsed:
        raise _gone("Link already used")

    if record.subject_id is None:
        raise _gone("Link invalid")
    user = await session.get(User, record.subject_id)
    if user is None:
        raise _gone("User no longer exists")

    now = datetime.now(UTC)
    if payload.decision == "approve":
        user.parent_consent_given_at = now
        user.guardian_attested_at = now
        user.is_active = True
    else:
        user.consent_declined_at = now
        user.is_active = False

    await session.commit()
    return {"status": "ok", "decision": payload.decision}


@router.post("/consent/request/{user_id}", status_code=202)
@limiter.limit("3/hour")
async def request_consent_email(
    request: Request,
    user_id: str,
    session: AsyncSession = Depends(get_session),
):
    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user id")
    user = await session.get(User, uid)
    if user is None or user.parent_email is None:
        # Don't leak existence — generic 202.
        return {"status": "queued"}
    if user.parent_consent_given_at is not None:
        return {"status": "queued"}

    age = age_in_years(user.dob, date.today())
    token = await issue_one_time_token(
        session, purpose=CONSENT_AUDIENCE, email=user.parent_email,
        subject_id=user.id, expires_in=CONSENT_EXPIRY,
    )
    link = f"{settings.app_base_url}/consent/verify?token={token}"
    await get_email_sender().send(
        session, user.parent_email, "consent_request",
        {"child_username": user.username, "age": age,
         "country_code": user.country_code, "link": link},
        subject_id=user.id,
    )
    await session.commit()
    return {"status": "queued"}
