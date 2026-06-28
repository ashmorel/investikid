"""Concept taxonomy mapper.

``resolve_concept_slug`` looks up an existing Concept by slug within a topic.
It NEVER inserts concepts — the taxonomy is authored-only.
"""
from __future__ import annotations

import re
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.concept import Concept


def _normalize(s: str) -> str:
    """Lower-case, collapse whitespace/underscores/hyphens to a single hyphen."""
    s = s.lower().strip()
    s = re.sub(r"[\s_-]+", "-", s)
    return s


async def resolve_concept_slug(
    session: AsyncSession,
    slug: str | None,
    topic: str,
) -> uuid.UUID | None:
    """Return the concept id for ``slug`` within ``topic``, or ``None``.

    Resolution order:
    1. Exact slug match scoped to the topic.
    2. Normalized fuzzy match (lower-case, whitespace/underscores/hyphens all
       become a single hyphen) against slug and name for that topic.

    This function only reads — it MUST NEVER insert a Concept row.
    """
    if not slug or not topic:
        return None

    # 1. Exact slug match within topic.
    row = await session.scalar(
        select(Concept).where(Concept.slug == slug, Concept.topic == topic)
    )
    if row is not None:
        return row.id

    # 2. Normalized fuzzy match: load topic's concepts and compare normalised forms.
    normalized_input = _normalize(slug)
    if not normalized_input:
        return None

    candidates = (
        await session.scalars(select(Concept).where(Concept.topic == topic))
    ).all()

    for c in candidates:
        if _normalize(c.slug) == normalized_input:
            return c.id
        # Also match against the concept name (e.g. "Compound Interest" → compound-interest).
        if _normalize(c.name) == normalized_input:
            return c.id

    return None
