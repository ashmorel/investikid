"""Per-topic strengths and gaps analysis — read-only service."""
import uuid
from collections import defaultdict
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.concept import Concept
from app.models.skill_profile import ConceptMastery, SpacedRepetitionItem, TopicMastery, WeakConcept
from app.schemas.ai import ConceptStrength, StrengthsAndGaps, TopicStrength

_STRONG_THRESHOLD = 0.8
_STATUS_ORDER = {"needs_practice": 0, "strong": 1, "new": 2}


def _classify(mastery_score: float | None) -> str:
    """Classify a topic or concept based on mastery score."""
    if mastery_score is None:
        return "new"
    if mastery_score >= _STRONG_THRESHOLD:
        return "strong"
    return "needs_practice"


# Backward-compat alias kept so existing callers/tests continue to work.
_classify_topic = _classify


def _compute_overall_mastery(scores: list[float]) -> float:
    """Average of all mastery scores, or 0.0 if empty."""
    if not scores:
        return 0.0
    return round(sum(scores) / len(scores), 4)


def _sort_topics(topics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sort: needs_practice first, strong second, new last."""
    return sorted(topics, key=lambda t: _STATUS_ORDER.get(t["status"], 99))


async def get_strengths_and_gaps(
    session: AsyncSession,
    user_id: uuid.UUID,
) -> StrengthsAndGaps:
    """Per-topic summary combining TopicMastery + WeakConcept + SR schedule."""
    # Load mastery data
    mastery_rows = (
        await session.scalars(
            select(TopicMastery).where(TopicMastery.user_id == user_id)
        )
    ).all()
    mastery_by_topic = {tm.topic: tm for tm in mastery_rows}

    # Load per-concept mastery (attempted only) joined to Concept for topic/slug/name
    concept_rows_result = await session.execute(
        select(ConceptMastery, Concept)
        .join(Concept, Concept.id == ConceptMastery.concept_id)
        .where(
            ConceptMastery.user_id == user_id,
            ConceptMastery.attempts > 0,
        )
    )
    concepts_by_topic: dict[str, list[ConceptStrength]] = defaultdict(list)
    for cm, concept in concept_rows_result.all():
        cs = ConceptStrength(
            concept_id=concept.id,
            slug=concept.slug,
            name=concept.name,
            mastery_score=cm.mastery_score,
            status=_classify(cm.mastery_score),
            attempts=cm.attempts,
        )
        concepts_by_topic[concept.topic].append(cs)

    # Load weak concept counts per topic (unresolved only)
    # TODO(C2b): filter WeakConcept by the child's active market once multi-market is user-visible
    weak_counts_result = await session.execute(
        select(WeakConcept.topic, func.count(WeakConcept.id))
        .where(WeakConcept.user_id == user_id, WeakConcept.resolved == False)  # noqa: E712
        .group_by(WeakConcept.topic)
    )
    weak_counts: dict[str, int] = dict(weak_counts_result.all())

    # Load total concept counts per topic (all, including resolved)
    # TODO(C2b): filter WeakConcept by the child's active market once multi-market is user-visible
    total_counts_result = await session.execute(
        select(WeakConcept.topic, func.count(WeakConcept.id))
        .where(WeakConcept.user_id == user_id)
        .group_by(WeakConcept.topic)
    )
    total_concepts: dict[str, int] = dict(total_counts_result.all())

    # Load due-for-review counts per topic
    due_counts_result = await session.execute(
        select(WeakConcept.topic, func.count(SpacedRepetitionItem.id))
        .join(WeakConcept, WeakConcept.id == SpacedRepetitionItem.weak_concept_id)
        .where(
            SpacedRepetitionItem.user_id == user_id,
            SpacedRepetitionItem.next_review_at <= func.now(),
            WeakConcept.resolved == False,  # noqa: E712
        )
        .group_by(WeakConcept.topic)
    )
    due_counts: dict[str, int] = dict(due_counts_result.all())

    # Collect all known topics
    all_topics = set(mastery_by_topic.keys()) | set(weak_counts.keys()) | set(total_concepts.keys())

    topic_list: list[dict[str, Any]] = []
    mastery_scores: list[float] = []

    for topic in all_topics:
        mastery = mastery_by_topic.get(topic)
        score = mastery.mastery_score if mastery else None
        status = _classify(score)

        if score is not None:
            mastery_scores.append(score)

        # Sort concepts needs_practice-first (mirrors topic sort order)
        topic_concepts = sorted(
            concepts_by_topic.get(topic, []),
            key=lambda c: _STATUS_ORDER.get(c.status, 99),
        )

        topic_list.append({
            "topic": topic,
            "mastery_score": score if score is not None else 0.0,
            "status": status,
            "weak_count": weak_counts.get(topic, 0),
            "due_for_review": due_counts.get(topic, 0),
            "total_concepts": total_concepts.get(topic, 0),
            "concepts": topic_concepts,
        })

    sorted_topics = _sort_topics(topic_list)

    return StrengthsAndGaps(
        topics=[TopicStrength(**t) for t in sorted_topics],
        overall_mastery=_compute_overall_mastery(mastery_scores),
    )
