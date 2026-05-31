import batch_job

class FakeCursor:
    def __init__(self): self.executed = []; self.lastrowid = 1
    def execute(self, sql, params=None): self.executed.append((sql, params))
    def fetchone(self): return None
    def fetchall(self): return []

class FakeConn:
    def __init__(self): self.cur = FakeCursor(); self.committed = 0
    def cursor(self): return self.cur
    def commit(self): self.committed += 1
    def close(self): pass

def test_run_batch_continues_on_symbol_failure(monkeypatch):
    calls = {"n": 0}
    def flaky(symbol, company, item_date):
        calls["n"] += 1
        if symbol == "TSLA":
            raise RuntimeError("api down")
        return {"symbol": symbol, "company": company, "summary_ko": "요약",
                "sentiment": "neutral", "audio_url": None, "articles": []}
    monkeypatch.setattr(batch_job.runner, "process_symbol", flaky)
    monkeypatch.setattr(batch_job.config, "WATCHLIST", [("AAPL", "Apple"), ("TSLA", "Tesla"), ("NVDA", "NVIDIA")])

    conn = FakeConn()
    ok, failed = batch_job.run_batch(conn, "2026-05-31")
    assert ok == 2 and failed == 1          # TSLA 실패해도 나머지 처리
    assert calls["n"] == 3
