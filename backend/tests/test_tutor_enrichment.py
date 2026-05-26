from app.services.tutor_service import _build_weak_concept_addendum


def test_no_weak_concepts_returns_empty():
    result = _build_weak_concept_addendum([])
    assert result == ""


def test_single_concept():
    result = _build_weak_concept_addendum(["compound interest"])
    assert "compound interest" in result
    assert "struggled" in result


def test_multiple_concepts():
    result = _build_weak_concept_addendum(["APR", "compound interest", "50/30/20 rule"])
    assert "APR" in result
    assert "compound interest" in result
    assert "50/30/20 rule" in result
