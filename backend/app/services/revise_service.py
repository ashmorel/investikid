from __future__ import annotations

import base64
import json
import logging
import uuid

from app.models.content import Lesson

logger = logging.getLogger(__name__)

SESSION_CAP = 5
XP_PER_CORRECT = 5


def _concept_of(lesson: Lesson) -> str:
    """Same derivation the practice flow uses (ai.py practice_quiz)."""
    c = lesson.content_json or {}
    return c.get("question") or c.get("title") or c.get("prompt") or "general"


def encode_ref(
    *,
    kind: str,
    topic: str,
    lesson_id: uuid.UUID,
    concept: str,
    weak_concept_id: uuid.UUID | None,
) -> str:
    payload = {
        "kind": kind,
        "topic": topic,
        "lesson_id": str(lesson_id),
        "concept": concept,
        "weak_concept_id": str(weak_concept_id) if weak_concept_id else None,
    }
    raw = json.dumps(payload, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode()


def decode_ref(ref: str) -> dict:
    try:
        raw = base64.urlsafe_b64decode(ref.encode())
        data = json.loads(raw)
        if data.get("kind") not in ("weak", "refresher") or "lesson_id" not in data:
            raise ValueError("bad ref payload")
        return data
    except Exception as exc:  # noqa: BLE001
        raise ValueError("invalid ref") from exc
