"""Diagnostic session service — item selection + start (Task 2).

``start_diagnostic`` selects approved items for a child and opens a
``DiagnosticSession``.  Selection rules:

1. In-scope topics = {"budgeting", "savings", "risk"} ∪ (user.topic_path
   if set and is one of the 9 recognised topics).
2. Market = active_market(user).
3. For each in-scope topic: pick up to 2 approved items in that market,
   preferring unseen items (not in any prior DiagnosticSession.item_ids for
   this user) and a spread of difficulty tiers.  Falls back to seen items
   when the bank is thin; logs a caveat.
4. Cap total at 10 items.
5. Persist a DiagnosticSession row; bump times_shown on each selected item.
6. Return (session, items) where each item dict is
   {id, topic, difficulty_tier, question, choices} — NO answer_index, NO
   explanation.

Empty path: if zero approved items exist for the scope, a session with
item_ids=[] is created and (session, []) returned.  Never raises.
"""
from __future__ import annotations

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.markets import active_market
from app.models.diagnostic import DiagnosticItem
from app.models.mastery import DiagnosticSession
from app.models.user import User

logger = logging.getLogger(__name__)

_BASE_TOPICS = frozenset({"budgeting", "savings", "risk"})
_ALL_VALID_TOPICS = frozenset(
    {
        "budgeting",
        "savings",
        "risk",
        "stocks",
        "investing",
        "debt",
        "taxes",
        "insurance",
        "retirement",
    }
)
_ITEMS_PER_TOPIC = 2
_TOTAL_CAP = 10


def _safe_item_dict(item: DiagnosticItem) -> dict:
    """Return the public-facing item payload (NO answer_index, NO explanation)."""
    return {
        "id": str(item.id),
        "topic": item.topic,
        "difficulty_tier": item.difficulty_tier,
        "question": item.question,
        "choices": item.choices,
    }


async def _seen_item_ids(session: AsyncSession, user_id: uuid.UUID) -> frozenset[str]:
    """Return the set of item id strings that appear in any prior session for this user."""
    rows = (
        await session.scalars(
            select(DiagnosticSession.item_ids).where(
                DiagnosticSession.user_id == user_id,
                DiagnosticSession.completed_at.isnot(None),
            )
        )
    ).all()
    # item_ids is stored as a JSON list[str]
    seen: set[str] = set()
    for id_list in rows:
        if isinstance(id_list, list):
            seen.update(str(i) for i in id_list)
    return frozenset(seen)


def _select_for_topic(
    candidates: list[DiagnosticItem],
    seen_ids: frozenset[str],
    limit: int,
) -> list[DiagnosticItem]:
    """Choose up to *limit* items from *candidates*, preferring:
    1. Unseen items first.
    2. Diversity of difficulty tiers (don't pick two of the same tier when avoidable).

    If fewer than *limit* unseen items exist, falls back to seen items.
    """
    unseen = [i for i in candidates if str(i.id) not in seen_ids]
    seen_fallback = [i for i in candidates if str(i.id) in seen_ids]

    def _spread(pool: list[DiagnosticItem], n: int) -> list[DiagnosticItem]:
        """Pick up to *n* items with tier diversity (greedy: prefer different tiers)."""
        chosen: list[DiagnosticItem] = []
        tiers_used: set[int] = set()
        # First pass: pick items with unseen tiers
        for item in pool:
            if len(chosen) >= n:
                break
            if item.difficulty_tier not in tiers_used:
                chosen.append(item)
                tiers_used.add(item.difficulty_tier)
        # Second pass: fill remainder from items with already-used tiers
        for item in pool:
            if len(chosen) >= n:
                break
            if item not in chosen:
                chosen.append(item)
        return chosen

    selected = _spread(unseen, limit)
    remaining = limit - len(selected)
    if remaining > 0:
        if seen_fallback:
            logger.info(
                "diagnostic_service: thin bank for topic — falling back to %d "
                "already-seen item(s).",
                min(remaining, len(seen_fallback)),
            )
        selected += _spread(seen_fallback, remaining)

    return selected


async def start_diagnostic(
    session: AsyncSession,
    user: User,
    *,
    kind: str = "baseline",
) -> tuple[DiagnosticSession, list[dict]]:
    """Select approved items and open a DiagnosticSession for *user*.

    Returns (DiagnosticSession, list[item_dict]) where each item_dict is
    {id, topic, difficulty_tier, question, choices} — no answer_index, no
    explanation.  On empty bank returns (session, []).
    """
    market = active_market(user)

    # Build in-scope topics
    topics = set(_BASE_TOPICS)
    if user.topic_path and user.topic_path in _ALL_VALID_TOPICS:
        topics.add(user.topic_path)

    # All approved items for this market in scope topics
    rows = (
        await session.scalars(
            select(DiagnosticItem)
            .where(
                DiagnosticItem.status == "approved",
                DiagnosticItem.market_code == market,
                DiagnosticItem.topic.in_(topics),
            )
            .order_by(DiagnosticItem.created_at)  # stable ordering for tests
        )
    ).all()

    # Identify items this user has already seen
    seen_ids = await _seen_item_ids(session, user.id)

    # Group by topic
    by_topic: dict[str, list[DiagnosticItem]] = {}
    for item in rows:
        by_topic.setdefault(item.topic, []).append(item)

    selected: list[DiagnosticItem] = []
    for topic in sorted(topics):  # deterministic order
        candidates = by_topic.get(topic, [])
        chosen = _select_for_topic(candidates, seen_ids, _ITEMS_PER_TOPIC)
        selected.extend(chosen)
        if len(selected) >= _TOTAL_CAP:
            selected = selected[:_TOTAL_CAP]
            break

    # Bump times_shown
    for item in selected:
        item.times_shown += 1

    # Create session
    diag_session = DiagnosticSession(
        user_id=user.id,
        market_code=market,
        kind=kind,
        item_ids=[str(i.id) for i in selected],
    )
    session.add(diag_session)
    await session.flush()

    items_out = [_safe_item_dict(i) for i in selected]
    return diag_session, items_out
