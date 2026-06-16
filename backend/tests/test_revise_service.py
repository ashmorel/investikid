import uuid

import pytest

from app.services.revise_service import decode_ref, encode_ref

pytestmark = pytest.mark.asyncio(loop_scope="session")


def test_ref_roundtrip():
    lesson_id = uuid.uuid4()
    wc_id = uuid.uuid4()
    ref = encode_ref(kind="weak", topic="stocks", lesson_id=lesson_id,
                     concept="What is a stock?", weak_concept_id=wc_id)
    out = decode_ref(ref)
    assert out == {
        "kind": "weak", "topic": "stocks", "lesson_id": str(lesson_id),
        "concept": "What is a stock?", "weak_concept_id": str(wc_id),
    }


def test_ref_refresher_has_no_weak_id():
    lesson_id = uuid.uuid4()
    ref = encode_ref(kind="refresher", topic="saving", lesson_id=lesson_id,
                     concept="Why save?", weak_concept_id=None)
    out = decode_ref(ref)
    assert out["kind"] == "refresher"
    assert out["weak_concept_id"] is None


def test_decode_ref_rejects_garbage():
    with pytest.raises(ValueError):
        decode_ref("not-a-real-ref")
