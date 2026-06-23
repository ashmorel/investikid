"""Admin word-bank endpoints for MoneyWord (Task 7).

Routes:
  POST   /admin/arcade-words/suggest         — LLM-suggest words, rate-limited
  GET    /admin/arcade-words                 — list by status / language
  POST   /admin/arcade-words/{id}/approve   — optionally edit then approve
  POST   /admin/arcade-words/{id}/reject    — mark rejected
"""
from __future__ import annotations

import re
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.rate_limit import limiter
from app.models.arcade_word import ArcadeWord
from app.routers.admin_auth import get_current_admin
from app.services.arcade_word_admin_service import suggest_words

_WORD_RE = re.compile(r"^[A-Z]{4,8}$")

router = APIRouter(
    prefix="/admin/arcade-words",
    tags=["admin-arcade-words"],
    dependencies=[Depends(get_current_admin)],
)


# ── Pydantic schemas ──────────────────────────────────────────────────


class SuggestWordsIn(BaseModel):
    language: str = "en"
    count: int = 10


class ApproveWordIn(BaseModel):
    word: str | None = None
    definition: str | None = None

    @field_validator("word")
    @classmethod
    def _validate_word(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip().upper()
        if not _WORD_RE.match(v):
            raise ValueError("word must be 4-8 uppercase A-Z letters")
        return v

    @field_validator("definition")
    @classmethod
    def _validate_definition(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError("definition must not be empty")
        if len(v) > 180:
            raise ValueError("definition must be 180 characters or fewer")
        return v


class ArcadeWordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    word: str
    definition: str
    language: str
    length: int
    status: str
    source: str
    created_at: datetime


# ── Endpoints ─────────────────────────────────────────────────────────


@router.post("/suggest")
@limiter.limit("5/minute")
async def suggest(
    request: Request,
    payload: SuggestWordsIn,
    session: AsyncSession = Depends(get_session),
) -> dict:
    result = await suggest_words(session, language=payload.language, count=payload.count)
    await session.commit()
    return result


@router.get("", response_model=list[ArcadeWordOut])
async def list_words(
    status: str = "pending",
    language: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> list[ArcadeWord]:
    q = select(ArcadeWord).where(ArcadeWord.status == status)
    if language is not None:
        q = q.where(ArcadeWord.language == language)
    return list((await session.scalars(q.order_by(ArcadeWord.created_at))).all())


@router.post("/{word_id}/approve", response_model=ArcadeWordOut)
async def approve_word(
    word_id: uuid.UUID,
    payload: ApproveWordIn = ApproveWordIn(),
    session: AsyncSession = Depends(get_session),
) -> ArcadeWord:
    word = await session.get(ArcadeWord, word_id)
    if word is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "word not found")
    if payload.word is not None:
        word.word = payload.word
        word.length = len(payload.word)
    if payload.definition is not None:
        word.definition = payload.definition
    word.status = "approved"
    await session.commit()
    await session.refresh(word)
    return word


@router.post("/{word_id}/reject", response_model=ArcadeWordOut)
async def reject_word(
    word_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> ArcadeWord:
    word = await session.get(ArcadeWord, word_id)
    if word is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "word not found")
    word.status = "rejected"
    await session.commit()
    await session.refresh(word)
    return word
