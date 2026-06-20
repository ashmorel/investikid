from app.services.market_curriculum.backbone import BACKBONE, backbone_keys


def test_backbone_has_nine_unique_concepts():
    keys = [c["key"] for c in BACKBONE]
    assert len(keys) == 9
    assert len(set(keys)) == 9
    assert backbone_keys() == set(keys)


def test_tax_and_giving_is_required():
    assert "tax_giving" in backbone_keys()


def test_every_concept_has_title_and_description():
    for c in BACKBONE:
        assert c["title"] and c["description"]
