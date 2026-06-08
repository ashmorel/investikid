import app.services.price_cache as pc


class _FakeRedis:
    def __init__(self):
        self.store = {}
    def get(self, key):
        return self.store.get(key)
    def setex(self, key, ttl, value):
        self.store[key] = value


class _RaisingRedis:
    def get(self, key):
        raise RuntimeError("redis down")
    def setex(self, key, ttl, value):
        raise RuntimeError("redis down")


def setup_function():
    pc.reset()


def test_set_then_get_roundtrips(monkeypatch):
    fake = _FakeRedis()
    monkeypatch.setattr(pc, "_make_client", lambda: fake)
    pc.set_json("k", {"a": 1, "b": ["x"]}, 60)
    assert pc.get_json("k") == {"a": 1, "b": ["x"]}


def test_missing_key_returns_none(monkeypatch):
    monkeypatch.setattr(pc, "_make_client", lambda: _FakeRedis())
    assert pc.get_json("absent") is None


def test_raising_client_disables_and_noops(monkeypatch):
    monkeypatch.setattr(pc, "_make_client", lambda: _RaisingRedis())
    assert pc.get_json("k") is None
    pc.set_json("k", {"a": 1}, 60)  # must not raise
    assert pc._disabled is True


def test_client_build_failure_disables(monkeypatch):
    def boom():
        raise RuntimeError("cannot connect")
    monkeypatch.setattr(pc, "_make_client", boom)
    assert pc.get_json("k") is None
    assert pc._disabled is True
