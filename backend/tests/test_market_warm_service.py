from app.services import market_warm_service


class _FakeProvider:
    def __init__(self): self.calls = []
    def warm_region(self, region):
        self.calls.append(region)
        if region == "GB":
            raise RuntimeError("boom")
        return {"region": region, "featured": 3, "movers": True}


def test_warm_all_is_best_effort_per_region():
    p = _FakeProvider()
    out = market_warm_service.warm_all(p)
    assert set(p.calls) == {"US", "GB", "HK"}          # all attempted
    regions = {r["region"]: r for r in out["regions"]}
    assert regions["US"]["featured"] == 3
    assert regions["GB"]["error"] is True               # failure captured, not raised
