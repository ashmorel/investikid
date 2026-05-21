"""WCAG 2.2 AA video transcript policy (sub-project 5).

Every seeded video lesson must carry a non-empty `transcript` and
`captions_available: True` in its `content_json` so the frontend
VideoLesson component can render the transcript Disclosure deterministically.

If the seed currently contains no video lessons, the test skips with an
explicit note — the policy is enforced as soon as a video lesson is added.
See `frontend/docs/accessibility/conformance-2026-05.md` (residual items).
"""

import pytest

from app.seed.content import _MODULES


def _seeded_video_lessons() -> list[dict]:
    return [
        lesson
        for module in _MODULES
        for lesson in module["lessons"]
        if lesson["type"] == "video"
    ]


def test_every_seeded_video_lesson_has_non_empty_transcript_and_captions_flag():
    video_lessons = _seeded_video_lessons()
    if not video_lessons:
        pytest.skip(
            "no video lessons currently seeded; transcript policy enforced when added"
        )
    for lesson in video_lessons:
        content = lesson["content_json"]
        label = content.get("caption") or repr(content)
        assert content.get("transcript"), (
            f"video lesson {label} missing non-empty transcript"
        )
        assert content.get("captions_available") is True, (
            f"video lesson {label} missing captions_available=True"
        )
