from fastapi.testclient import TestClient
from app import main

class FakeCursor:
    def __init__(self, **kw): self._kw = kw; self.lastrowid = 99; self.executed = []
    def execute(self, sql, params=None): self.executed.append((sql, params))
    def fetchone(self): return self._kw.get("one")
    def fetchall(self): return self._kw.get("all", [])

class FakeConn:
    def __init__(self, cur): self._cur = cur; self.committed = 0
    def cursor(self): return self._cur
    def commit(self): self.committed += 1
    def close(self): pass

def test_search_returns_cached_item(monkeypatch):
    cached = {"id": 5, "symbol": "AAPL", "company": "Apple", "summary_ko": "캐시요약",
              "sentiment": "positive", "audio_url": None}
    cur = FakeCursor(one=cached, all=[])
    main.app.dependency_overrides[main.get_conn] = lambda: FakeConn(cur)

    # process_symbol 은 호출되면 안 됨(캐시 히트)
    monkeypatch.setattr(main.runner, "process_symbol",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("should not run")))
    client = TestClient(main.app)
    resp = client.post("/search", data={"symbol": "AAPL"})
    assert resp.status_code == 200
    assert "캐시요약" in resp.text
    main.app.dependency_overrides.clear()

def test_search_runs_pipeline_on_cache_miss(monkeypatch):
    cur = FakeCursor(one=None, all=[])
    main.app.dependency_overrides[main.get_conn] = lambda: FakeConn(cur)
    monkeypatch.setattr(main.runner, "process_symbol",
                        lambda symbol, company, item_date: {
                            "symbol": symbol, "company": company, "summary_ko": "새요약",
                            "sentiment": "neutral", "audio_url": None, "articles": []})
    client = TestClient(main.app)
    resp = client.post("/search", data={"symbol": "AAPL"})
    assert resp.status_code == 200
    assert "새요약" in resp.text
    main.app.dependency_overrides.clear()
