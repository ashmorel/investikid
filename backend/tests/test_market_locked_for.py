from app.services.entitlements import market_locked_for


class FakeUser:
    def __init__(self, is_premium, started):
        self.is_premium = is_premium
        self.started_market_code = started


def test_premium_never_locked():
    assert market_locked_for(FakeUser(True, "GB"), "US") is False


def test_free_no_started_nothing_locked():
    assert market_locked_for(FakeUser(False, None), "US") is False


def test_free_started_other_market_locked():
    u = FakeUser(False, "GB")
    assert market_locked_for(u, "US") is True
    assert market_locked_for(u, "GB") is False
