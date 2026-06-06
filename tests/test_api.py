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
    called = []
    def must_not_run(*a, **k):
        called.append(1)
        return {}
    monkeypatch.setattr(main.runner, "process_symbol", must_not_run)
    client = TestClient(main.app)
    resp = client.post("/search", data={"symbol": "AAPL"})
    assert resp.status_code == 200
    assert "캐시요약" in resp.text
    assert called == []
    main.app.dependency_overrides.clear()

def test_search_runs_pipeline_on_cache_miss(monkeypatch):
    cur = FakeCursor(one=None, all=[])
    fake_conn = FakeConn(cur)
    main.app.dependency_overrides[main.get_conn] = lambda: fake_conn
    monkeypatch.setattr(main.runner, "process_symbol",
                        lambda symbol, company, item_date: {
                            "symbol": symbol, "company": company, "summary_ko": "새요약",
                            "sentiment": "neutral", "audio_url": None, "articles": []})
    client = TestClient(main.app)
    resp = client.post("/search", data={"symbol": "AAPL"})
    assert resp.status_code == 200
    assert "새요약" in resp.text
    assert fake_conn.committed == 1
    main.app.dependency_overrides.clear()


# ── Auth routes ──────────────────────────────────────────────────────

def test_register_page_returns_200():
    resp = TestClient(main.app).get("/register")
    assert resp.status_code == 200
    assert "회원가입" in resp.text


def test_login_page_returns_200():
    resp = TestClient(main.app).get("/login")
    assert resp.status_code == 200
    assert "로그인" in resp.text


def test_register_creates_user_and_redirects(monkeypatch):
    cur = FakeCursor(one=None, all=[])
    main.app.dependency_overrides[main.get_conn] = lambda: FakeConn(cur)
    monkeypatch.setattr(main.db, "get_user_by_email", lambda cur, email: None)
    monkeypatch.setattr(main.db, "create_user", lambda cur, email, pw: 1)
    resp = TestClient(main.app).post("/register", data={"email": "t@t.com", "password": "pass1234"}, follow_redirects=False)
    assert resp.status_code in (302, 303)
    main.app.dependency_overrides.clear()


def test_login_bad_password_returns_form(monkeypatch):
    cur = FakeCursor(one=None, all=[])
    main.app.dependency_overrides[main.get_conn] = lambda: FakeConn(cur)
    monkeypatch.setattr(main.db, "get_user_by_email", lambda cur, email: {"id": 1, "email": email, "password_hash": "bad"})
    monkeypatch.setattr(main.auth, "verify_password", lambda p, h: False)
    resp = TestClient(main.app).post("/login", data={"email": "t@t.com", "password": "wrong"})
    assert resp.status_code == 401
    assert "이메일 또는 비밀번호" in resp.text
    main.app.dependency_overrides.clear()


# ── Watchlist edit routes ─────────────────────────────────────────────

def test_watchlist_edit_redirects_when_not_logged_in():
    resp = TestClient(main.app).get("/watchlist/edit", follow_redirects=False)
    assert resp.status_code in (302, 303)
    assert "/login" in resp.headers["location"]


def test_watchlist_edit_page_renders_for_logged_in(monkeypatch):
    cur = FakeCursor(one=None, all=[{"symbol": "AAPL", "company": "Apple"}])
    main.app.dependency_overrides[main.get_conn] = lambda: FakeConn(cur)
    monkeypatch.setattr(main.db, "get_watchlist", lambda cur, user_id: [{"symbol": "AAPL", "company": "Apple"}])
    monkeypatch.setattr(main, "_current_user_id", lambda req: 1)
    resp = TestClient(main.app).get("/watchlist/edit")
    assert resp.status_code == 200
    assert "관심종목" in resp.text
    main.app.dependency_overrides.clear()
