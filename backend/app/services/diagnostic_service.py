"""Diagnostic session service — item selection + start (Task 2) + scoring (Task 3).

``start_diagnostic`` selects approved items for a child and opens a
``DiagnosticSession``.  ``submit_diagnostic`` scores the session server-side
and writes an immutable ``MasteryCheckpoint``.  Selection rules:

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
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.markets import active_market
from app.models.diagnostic import DiagnosticItem
from app.models.mastery import DiagnosticSession, MasteryCheckpoint, MasteryCheckpointTopic
from app.models.user import User, UserProgress
from app.services.skill_profile_service import update_mastery_on_completion

logger = logging.getLogger(__name__)

MILESTONES: tuple[int, ...] = (5, 15, 30)

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


async def recheck_status(session: AsyncSession, user: User) -> dict:
    """Return the re-check-due signal for *user*.

    completed_checks: count of the user's kind='progress' MasteryCheckpoints.
    active_days: from the user's UserProgress row (0 if no row exists).
    due: True when completed_checks < len(MILESTONES) AND
         active_days >= MILESTONES[completed_checks].
    milestone: MILESTONES[completed_checks] when not exhausted, else None.
    """
    # Count kind='progress' checkpoints for this user
    completed_checks: int = (
        await session.scalar(
            select(func.count()).where(
                MasteryCheckpoint.user_id == user.id,
                MasteryCheckpoint.kind == "progress",
            )
        )
    ) or 0

    # Load active_days (0 when no progress row)
    progress = await session.get(UserProgress, user.id)
    active_days: int = progress.active_days if progress is not None else 0

    exhausted = completed_checks >= len(MILESTONES)
    milestone: int | None = MILESTONES[completed_checks] if not exhausted else None
    due: bool = (not exhausted) and (active_days >= MILESTONES[completed_checks])

    return {
        "due": due,
        "milestone": milestone,
        "active_days": active_days,
        "completed_checks": completed_checks,
    }


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


# ---------------------------------------------------------------------------
# Task 3 — submit_diagnostic
# ---------------------------------------------------------------------------


async def submit_diagnostic(
    session: AsyncSession,
    user: User,
    *,
    session_id: uuid.UUID,
    answers: dict[str, int],
    session_count: int = 0,
    skipped: bool = False,
) -> MasteryCheckpoint:
    """Score a diagnostic session server-side and write an immutable MasteryCheckpoint.

    Raises:
        HTTPException 404  — session not found.
        HTTPException 403  — session belongs to a different user.
        HTTPException 409  — session already completed.

    Scoring rules:
    - For each item_id in session.item_ids: correct = answers.get(item_id) == item.answer_index.
    - Unanswered items count as attempted-and-incorrect (denominator = session size).
    - overall_score = total_correct / total_attempted  (None when attempted == 0).
    - Empty session (item_ids == []) → kind="skipped", overall_score=None, no topic rows.
    - skipped=True (explicit child skip) → same short-circuit as empty session.
    - Bumps times_correct on each correctly-answered item (calibration).
    - Calls update_mastery_on_completion for each item (warm-start TopicMastery).
    - Does NOT touch XP, streak, coins, or any reward/activity paths.
    """
    # 1. Load + guard
    diag_session = await session.get(DiagnosticSession, session_id)
    if diag_session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Diagnostic session not found")
    if diag_session.user_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your diagnostic session")
    if diag_session.completed_at is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Diagnostic session already completed")

    # 2. Empty session OR explicit skip → skipped checkpoint, no scoring
    if skipped or not diag_session.item_ids:
        checkpoint = MasteryCheckpoint(
            user_id=user.id,
            market_code=diag_session.market_code,
            kind="skipped",
            session_count=session_count,
            overall_score=None,
        )
        session.add(checkpoint)
        diag_session.completed_at = datetime.now(UTC)
        await session.flush()
        return checkpoint

    # 3. Score per item, tally per topic
    item_ids: list[str] = diag_session.item_ids
    # topic → [correct_count, attempted_count]
    topic_tally: dict[str, list[int]] = {}
    total_correct = 0
    total_attempted = 0

    for item_id_str in item_ids:
        item_uuid = uuid.UUID(item_id_str)
        item = await session.get(DiagnosticItem, item_uuid)
        if item is None:
            # Defensive: item deleted after session was created — count as incorrect
            topic = "unknown"
            correct = False
        else:
            topic = item.topic
            correct = answers.get(item_id_str) == item.answer_index

            # 5. Calibration: bump times_correct
            if correct:
                item.times_correct += 1

            # 6. Warm-start TopicMastery (diagnostic warm-start, no reward)
            await update_mastery_on_completion(
                session,
                user.id,
                topic,
                is_quiz=True,
                correct=correct,
            )

        if topic not in topic_tally:
            topic_tally[topic] = [0, 0]
        if correct:
            topic_tally[topic][0] += 1
            total_correct += 1
        topic_tally[topic][1] += 1
        total_attempted += 1

    # 4a. Compute overall_score
    overall_score: float | None = (
        total_correct / total_attempted if total_attempted > 0 else None
    )

    # 4b. Write immutable MasteryCheckpoint
    # For progress sessions: session_count is authoritative from the server-side
    # active_days — never trust the client value.
    authoritative_session_count = session_count
    if diag_session.kind == "progress":
        progress_row = await session.get(UserProgress, user.id)
        authoritative_session_count = progress_row.active_days if progress_row is not None else 0

    checkpoint = MasteryCheckpoint(
        user_id=user.id,
        market_code=diag_session.market_code,
        kind=diag_session.kind,
        session_count=authoritative_session_count,
        overall_score=overall_score,
    )
    session.add(checkpoint)
    await session.flush()  # get checkpoint.id

    # 4c. Write per-topic rows
    for topic, (correct_count, attempted_count) in topic_tally.items():
        session.add(
            MasteryCheckpointTopic(
                checkpoint_id=checkpoint.id,
                topic=topic,
                correct=correct_count,
                attempted=attempted_count,
            )
        )

    # 7. Mark session complete
    diag_session.completed_at = datetime.now(UTC)
    await session.flush()

    return checkpoint


# ---------------------------------------------------------------------------
# Task 4 — get_evidence  (read-only aggregation)
# ---------------------------------------------------------------------------


def _topics_from_checkpoint(checkpoint: MasteryCheckpoint) -> dict[str, float | None]:
    """Return {topic: score} from a checkpoint's topic rows, excluding 'unknown'."""
    result: dict[str, float | None] = {}
    for t in checkpoint.topics:
        if t.topic == "unknown":
            continue
        score: float | None = t.correct / t.attempted if t.attempted > 0 else None
        result[t.topic] = score
    return result


async def get_evidence(session: AsyncSession, user: User) -> dict:
    """Return a read-only evidence dict comparing baseline vs latest progress checkpoint.

    States:
    - No baseline  → {has_baseline: false, ...nulls}
    - Skipped      → {has_baseline: true, baseline_skipped: true, baseline: null, ...nulls}
    - Baseline only → baseline present, latest/delta null/empty
    - Baseline + progress → full comparison with deltas
    """
    # Load all checkpoints for this user, ordered oldest-first
    rows = (
        await session.scalars(
            select(MasteryCheckpoint)
            .where(MasteryCheckpoint.user_id == user.id)
            .order_by(MasteryCheckpoint.taken_at.asc())
        )
    ).all()

    # Eagerly load topics for each checkpoint
    for cp in rows:
        await session.refresh(cp, ["topics"])

    # Identify baseline: earliest kind in ("baseline", "skipped")
    baseline_cp: MasteryCheckpoint | None = None
    for cp in rows:
        if cp.kind in ("baseline", "skipped"):
            baseline_cp = cp
            break

    # Identify latest progress: most recent kind=="progress"
    latest_cp: MasteryCheckpoint | None = None
    for cp in reversed(rows):
        if cp.kind == "progress":
            latest_cp = cp
            break

    # ---- No baseline at all ----
    if baseline_cp is None:
        return {
            "has_baseline": False,
            "baseline_skipped": False,
            "baseline": None,
            "latest": None,
            "overall_delta": None,
            "topic_deltas": [],
            "session_count": None,
        }

    # ---- Skipped baseline ----
    if baseline_cp.kind == "skipped":
        return {
            "has_baseline": True,
            "baseline_skipped": True,
            "baseline": None,
            "latest": None,
            "overall_delta": None,
            "topic_deltas": [],
            "session_count": baseline_cp.session_count,
        }

    # ---- Baseline exists (and is not skipped) ----
    baseline_topics = _topics_from_checkpoint(baseline_cp)
    baseline_out = {
        "overall_score": baseline_cp.overall_score,
        "session_count": baseline_cp.session_count,
        "topics": [{"topic": k, "score": v} for k, v in baseline_topics.items()],
    }

    if latest_cp is None:
        return {
            "has_baseline": True,
            "baseline_skipped": False,
            "baseline": baseline_out,
            "latest": None,
            "overall_delta": None,
            "topic_deltas": [],
            "session_count": baseline_cp.session_count,
        }

    # ---- Baseline + progress ----
    latest_topics = _topics_from_checkpoint(latest_cp)
    latest_out = {
        "overall_score": latest_cp.overall_score,
        "session_count": latest_cp.session_count,
        "topics": [{"topic": k, "score": v} for k, v in latest_topics.items()],
    }

    # overall_delta
    overall_delta: float | None = None
    if baseline_cp.overall_score is not None and latest_cp.overall_score is not None:
        overall_delta = latest_cp.overall_score - baseline_cp.overall_score

    # per-topic deltas (only where both baseline and latest have a score)
    topic_deltas: list[dict] = []
    for topic in sorted(set(baseline_topics) & set(latest_topics)):
        b_score = baseline_topics[topic]
        l_score = latest_topics[topic]
        if b_score is not None and l_score is not None:
            topic_deltas.append(
                {
                    "topic": topic,
                    "baseline_score": b_score,
                    "latest_score": l_score,
                    "delta": l_score - b_score,
                }
            )

    return {
        "has_baseline": True,
        "baseline_skipped": False,
        "baseline": baseline_out,
        "latest": latest_out,
        "overall_delta": overall_delta,
        "topic_deltas": topic_deltas,
        "session_count": latest_cp.session_count,
    }
