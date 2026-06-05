"""Guards against shipping a seeded YouTube video id that is known-dead.

MqZmwQoHmAA ("Compound interest explained simply") was deleted on YouTube and
repointed to a live Khan Academy video. This catches a regression that
re-introduces the dead id, and documents the embeddability expectation.
"""
from app.seed.content import _MODULES

_KNOWN_DEAD_IDS = {"MqZmwQoHmAA"}


def _seed_video_ids() -> list[str]:
    ids: list[str] = []
    for module in _MODULES:
        for lesson in module["lessons"]:
            if lesson["type"] == "video":
                yt = lesson["content_json"].get("youtube_id")
                if yt:
                    ids.append(yt)
    return ids


def test_no_known_dead_video_ids_in_seed():
    assert _KNOWN_DEAD_IDS.isdisjoint(_seed_video_ids())


def test_compound_interest_uses_the_replacement_video():
    savings = next(m for m in _MODULES if m["title"] == "Compound Interest Basics")
    video = next(le for le in savings["lessons"] if le["type"] == "video")
    assert video["content_json"]["youtube_id"] == "Rm6UdfRs3gw"
