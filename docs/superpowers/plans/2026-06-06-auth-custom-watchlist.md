# Auth + Custom Watchlist Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 이메일/비밀번호 로그인을 추가하고, 로그인 사용자가 최대 6개 커스텀 종목을 저장·조회할 수 있게 한다.

**Architecture:** Starlette `SessionMiddleware` + 서명 쿠키로 세션 관리. `passlib[bcrypt]`로 비밀번호 해싱. DB에 `user` / `user_watchlist` 테이블 추가. 비로그인 사용자는 기존 고정 WATCHLIST만 열람 가능하고, 로그인 사용자는 커스텀 6개 종목 설정 및 임의 Finnhub 심볼 검색이 가능하다.

**Tech Stack:** FastAPI, Starlette SessionMiddleware, passlib[bcrypt], itsdangerous, PyMySQL, Jinja2, Finnhub `/stock/profile2`

---

## File Map

| 파일 | 역할 |
|------|------|
| `scripts/init_db.sql` | `user`, `user_watchlist` 테이블 추가 |
| `requirements.txt` | `passlib[bcrypt]`, `itsdangerous` 추가 |
| `.env.example` | `SESSION_SECRET` 키 추가 |
| `app/auth.py` | **신규** — bcrypt 해싱/검증 헬퍼 |
| `app/db.py` | user/watchlist CRUD 4개 함수 추가 |
| `pipeline/fetch.py` | `lookup_company(symbol)` 추가 |
| `app/main.py` | SessionMiddleware, auth 의존성, 신규 라우트 5개, `/`·`/search` 수정 |
| `app/templates/login.html` | **신규** — 로그인 폼 |
| `app/templates/register.html` | **신규** — 회원가입 폼 |
| `app/templates/watchlist_edit.html` | **신규** — 커스텀 종목 편집 |
| `app/templates/list.html` | 헤더 로그인 상태, 동적 티커바 |
| `app/templates/detail.html` | 헤더 로그인 상태 |
| `app/static/style.css` | 로그인/회원가입 폼, 워치리스트 편집 스타일 추가 |
| `tests/test_auth_helpers.py` | **신규** — auth.py 단위 테스트 |
| `tests/test_db.py` | user/watchlist CRUD 테스트 추가 |
| `tests/test_fetch.py` | `lookup_company` 테스트 추가 |
| `tests/test_api.py` | 로그인/회원가입/워치리스트 라우트 테스트 추가 |

---

## Task 1: DB 스키마 — user · user_watchlist 테이블 추가

**Files:**
- Modify: `scripts/init_db.sql`

- [ ] **Step 1: init_db.sql 끝에 두 테이블 추가**

```sql
-- scripts/init_db.sql 끝에 추가

CREATE TABLE IF NOT EXISTS user (
    id            BIGINT AUTO_INCREMENT PRIMARY KEY,
    email         VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_watchlist (
    id        BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id   BIGINT NOT NULL,
    symbol    VARCHAR(16) NOT NULL,
    company   VARCHAR(100) NOT NULL,
    position  TINYINT DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE,
    UNIQUE KEY uq_user_symbol (user_id, symbol)
);
```

- [ ] **Step 2: 커밋**

```
git add scripts/init_db.sql
git commit -m "feat: add user and user_watchlist tables to schema"
```

---

## Task 2: 의존성 및 환경변수 추가

**Files:**
- Modify: `requirements.txt`
- Modify: `.env.example`

- [ ] **Step 1: requirements.txt에 패키지 추가**

```
# requirements.txt 기존 내용 유지 + 아래 두 줄 추가
passlib[bcrypt]==1.7.4
itsdangerous==2.2.0
```

- [ ] **Step 2: 의존성 설치 확인**

```powershell
.venv\Scripts\pip install passlib[bcrypt]==1.7.4 itsdangerous==2.2.0
```

Expected: `Successfully installed ...` (이미 설치됐으면 "already satisfied")

- [ ] **Step 3: .env.example에 SESSION_SECRET 추가**

```
# .env.example 끝에 추가

# ── [발급처 F] 세션 서명 키 ─────────────────────────────────────────
#   아무 긴 랜덤 문자열. python -c "import secrets; print(secrets.token_hex(32))" 로 생성.
#   이 값이 노출되면 세션 위조 가능 — 절대 커밋하지 말 것.
SESSION_SECRET=your_session_secret_key
```

- [ ] **Step 4: 커밋**

```
git add requirements.txt .env.example
git commit -m "feat: add passlib, itsdangerous deps and SESSION_SECRET env"
```

---

## Task 3: app/auth.py — 비밀번호 헬퍼

**Files:**
- Create: `app/auth.py`
- Create: `tests/test_auth_helpers.py`

- [ ] **Step 1: 실패 테스트 작성**

```python
# tests/test_auth_helpers.py
from app.auth import hash_password, verify_password

def test_hash_is_not_plaintext():
    hashed = hash_password("secret123")
    assert hashed != "secret123"
    assert hashed.startswith("$2b$")

def test_verify_correct_password():
    hashed = hash_password("mypassword")
    assert verify_password("mypassword", hashed) is True

def test_verify_wrong_password():
    hashed = hash_password("mypassword")
    assert verify_password("wrong", hashed) is False
```

- [ ] **Step 2: 실패 확인**

```
pytest tests/test_auth_helpers.py -v
```
Expected: `ERROR` (app/auth.py 없음)

- [ ] **Step 3: app/auth.py 구현**

```python
# app/auth.py
from passlib.context import CryptContext

_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(plain: str) -> str:
    return _ctx.hash(plain)

def verify_password(plain: str, hashed: str) -> bool:
    return _ctx.verify(plain, hashed)
```

- [ ] **Step 4: 통과 확인**

```
pytest tests/test_auth_helpers.py -v
```
Expected: 3 passed

- [ ] **Step 5: 커밋**

```
git add app/auth.py tests/test_auth_helpers.py
git commit -m "feat: add password hashing helpers (bcrypt)"
```

---

## Task 4: app/db.py — user / watchlist CRUD 추가

**Files:**
- Modify: `app/db.py`
- Modify: `tests/test_db.py`

- [ ] **Step 1: 기존 test_db.py 확인 후 새 테스트 추가**

```python
# tests/test_db.py 끝에 추가

from app.db import create_user, get_user_by_email, get_watchlist, save_watchlist

class _Cur:
    def __init__(self): self.lastrowid = 7; self._rows = []; self.sqls = []
    def execute(self, sql, params=None): self.sqls.append((sql, params))
    def fetchone(self): return self._rows[0] if self._rows else None
    def fetchall(self): return list(self._rows)

def test_create_user_executes_insert():
    cur = _Cur()
    rid = create_user(cur, "a@b.com", "hash123")
    assert rid == 7
    sql, params = cur.sqls[0]
    assert "INSERT INTO user" in sql
    assert params == ("a@b.com", "hash123")

def test_get_user_by_email_queries_correctly():
    cur = _Cur()
    cur._rows = [{"id": 1, "email": "a@b.com", "password_hash": "h"}]
    result = get_user_by_email(cur, "a@b.com")
    assert result["email"] == "a@b.com"
    assert "WHERE email" in cur.sqls[0][0]

def test_get_watchlist_returns_rows():
    cur = _Cur()
    cur._rows = [{"symbol": "AAPL", "company": "Apple"}, {"symbol": "TSLA", "company": "Tesla"}]
    result = get_watchlist(cur, user_id=1)
    assert len(result) == 2
    assert result[0]["symbol"] == "AAPL"

def test_save_watchlist_deletes_then_inserts():
    cur = _Cur()
    save_watchlist(cur, user_id=1, symbols=[("AAPL", "Apple"), ("TSLA", "Tesla")])
    sqls = [s for s, _ in cur.sqls]
    assert any("DELETE" in s for s in sqls)
    assert sqls.count(next(s for s in sqls if "INSERT" in s)) >= 1
```

- [ ] **Step 2: 실패 확인**

```
pytest tests/test_db.py -v -k "test_create_user or test_get_user or test_get_watchlist or test_save_watchlist"
```
Expected: 4 FAILED (함수 없음)

- [ ] **Step 3: app/db.py에 4개 함수 추가**

```python
# app/db.py 끝에 추가

def create_user(cur, email: str, password_hash: str) -> int:
    cur.execute(
        "INSERT INTO user (email, password_hash) VALUES (%s, %s)",
        (email, password_hash),
    )
    return cur.lastrowid


def get_user_by_email(cur, email: str):
    cur.execute("SELECT * FROM user WHERE email=%s", (email,))
    return cur.fetchone()


def get_watchlist(cur, user_id: int) -> list:
    cur.execute(
        "SELECT symbol, company FROM user_watchlist WHERE user_id=%s ORDER BY position",
        (user_id,),
    )
    return cur.fetchall()


def save_watchlist(cur, user_id: int, symbols: list) -> None:
    cur.execute("DELETE FROM user_watchlist WHERE user_id=%s", (user_id,))
    for i, (symbol, company) in enumerate(symbols):
        cur.execute(
            "INSERT INTO user_watchlist (user_id, symbol, company, position) VALUES (%s,%s,%s,%s)",
            (user_id, symbol, company, i),
        )
```

- [ ] **Step 4: 통과 확인**

```
pytest tests/test_db.py -v
```
Expected: 전체 통과

- [ ] **Step 5: 커밋**

```
git add app/db.py tests/test_db.py
git commit -m "feat: add user/watchlist CRUD to db.py"
```

---

## Task 5: pipeline/fetch.py — lookup_company 추가

**Files:**
- Modify: `pipeline/fetch.py`
- Modify: `tests/test_fetch.py`

- [ ] **Step 1: 실패 테스트 추가**

```python
# tests/test_fetch.py 끝에 추가

from pipeline.fetch import lookup_company

def test_lookup_company_returns_name(monkeypatch):
    monkeypatch.setattr(fetch, "_call_profile_api", lambda sym: {"name": "Tesla Inc", "ticker": "TSLA"})
    assert lookup_company("TSLA") == "Tesla Inc"

def test_lookup_company_returns_none_for_empty(monkeypatch):
    monkeypatch.setattr(fetch, "_call_profile_api", lambda sym: {})
    assert lookup_company("ZZZZ") is None

def test_lookup_company_returns_none_on_error(monkeypatch):
    def boom(sym): raise Exception("network error")
    monkeypatch.setattr(fetch, "_call_profile_api", boom)
    assert lookup_company("FAIL") is None
```

- [ ] **Step 2: 실패 확인**

```
pytest tests/test_fetch.py -v -k "lookup"
```
Expected: 3 FAILED

- [ ] **Step 3: fetch.py에 구현 추가**

```python
# pipeline/fetch.py 기존 import 아래에 추가

def _call_profile_api(symbol: str) -> dict:
    """Finnhub /stock/profile2 호출. 테스트에서 mock된다."""
    key = config.get_env("NEWS_API_KEY")
    resp = httpx.get(
        f"{NEWS_API_BASE}/stock/profile2",
        params={"symbol": symbol, "token": key},
        timeout=5.0,
    )
    resp.raise_for_status()
    return resp.json()


def lookup_company(symbol: str) -> str | None:
    """Finnhub에서 종목 회사명 조회. 존재하지 않는 심볼이면 None 반환."""
    try:
        data = _call_profile_api(symbol)
        return data.get("name") or None
    except Exception:
        return None
```

- [ ] **Step 4: 통과 확인**

```
pytest tests/test_fetch.py -v
```
Expected: 전체 통과

- [ ] **Step 5: 커밋**

```
git add pipeline/fetch.py tests/test_fetch.py
git commit -m "feat: add lookup_company via Finnhub profile2"
```

---

## Task 6: app/main.py — SessionMiddleware + 인증 라우트

**Files:**
- Modify: `app/main.py`
- Create: `app/templates/login.html`
- Create: `app/templates/register.html`
- Modify: `tests/test_api.py`

- [ ] **Step 1: 실패 테스트 추가**

```python
# tests/test_api.py 끝에 추가

def _fresh_client():
    """SessionMiddleware가 붙은 TestClient를 반환."""
    return TestClient(main.app, raise_server_exceptions=True)

def test_register_page_returns_200():
    resp = _fresh_client().get("/register")
    assert resp.status_code == 200
    assert "회원가입" in resp.text

def test_login_page_returns_200():
    resp = _fresh_client().get("/login")
    assert resp.status_code == 200
    assert "로그인" in resp.text

def test_register_creates_user_and_redirects(monkeypatch):
    cur = FakeCursor(one=None, all=[])
    main.app.dependency_overrides[main.get_conn] = lambda: FakeConn(cur)
    monkeypatch.setattr(main.db, "get_user_by_email", lambda cur, email: None)
    monkeypatch.setattr(main.db, "create_user", lambda cur, email, pw: 1)
    resp = _fresh_client().post("/register", data={"email": "t@t.com", "password": "pass1234"}, follow_redirects=False)
    assert resp.status_code in (302, 303)
    main.app.dependency_overrides.clear()

def test_login_bad_password_returns_form(monkeypatch):
    cur = FakeCursor(one=None, all=[])
    main.app.dependency_overrides[main.get_conn] = lambda: FakeConn(cur)
    monkeypatch.setattr(main.db, "get_user_by_email", lambda cur, email: {"id": 1, "email": email, "password_hash": "bad"})
    monkeypatch.setattr(main.auth, "verify_password", lambda p, h: False)
    resp = _fresh_client().post("/login", data={"email": "t@t.com", "password": "wrong"})
    assert resp.status_code == 200
    assert "이메일 또는 비밀번호" in resp.text
    main.app.dependency_overrides.clear()
```

- [ ] **Step 2: 실패 확인**

```
pytest tests/test_api.py -v -k "register or login"
```
Expected: 4 FAILED

- [ ] **Step 3: main.py 상단 import + SessionMiddleware 추가**

```python
# app/main.py 상단 import에 추가
import os
from starlette.middleware.sessions import SessionMiddleware
from fastapi.responses import RedirectResponse
from app import auth

# app = FastAPI(...) 바로 아래에 추가
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET", "dev-secret-change-in-prod"),
)
```

- [ ] **Step 4: main.py에 auth 라우트 5개 추가**

```python
# app/main.py — get_conn 함수 아래에 추가

def _current_user_id(request: Request) -> int | None:
    return request.session.get("user_id")


@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return templates.TemplateResponse(request, "register.html", {"error": None})


@app.post("/register", response_class=HTMLResponse)
def register(request: Request, email: str = Form(...), password: str = Form(...), conn=Depends(get_conn)):
    cur = conn.cursor()
    if db.get_user_by_email(cur, email):
        return templates.TemplateResponse(request, "register.html", {"error": "이미 사용 중인 이메일입니다."}, status_code=400)
    db.create_user(cur, email, auth.hash_password(password))
    conn.commit()
    return RedirectResponse("/login", status_code=303)


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html", {"error": None})


@app.post("/login", response_class=HTMLResponse)
def login(request: Request, email: str = Form(...), password: str = Form(...), conn=Depends(get_conn)):
    cur = conn.cursor()
    user = db.get_user_by_email(cur, email)
    if not user or not auth.verify_password(password, user["password_hash"]):
        return templates.TemplateResponse(request, "login.html", {"error": "이메일 또는 비밀번호가 올바르지 않습니다."}, status_code=401)
    request.session["user_id"] = user["id"]
    request.session["user_email"] = user["email"]
    return RedirectResponse("/", status_code=303)


@app.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=303)
```

- [ ] **Step 5: login.html 생성**

```html
<!-- app/templates/login.html -->
<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>로그인 — FinVoice</title>
  <link rel="stylesheet" href="/static/style.css">
</head>
<body>
<div class="app" id="app">
  <header class="appbar">
    <div class="appbar-in">
      <div class="brand">
        <a href="/" style="text-decoration:none;color:inherit">
          <span class="brand-mark">FinVoice</span>
          <span class="brand-sub">해외 금융뉴스 음성 브리핑</span>
        </a>
      </div>
    </div>
  </header>
  <div class="wrap">
    <div class="auth-box">
      <h1 class="auth-title">로그인</h1>
      {% if error %}
      <div class="alert-banner" role="alert">{{ error }}</div>
      {% endif %}
      <form class="auth-form" method="POST" action="/login">
        <div class="auth-field">
          <label for="email">이메일</label>
          <input id="email" name="email" type="email" autocomplete="email" required placeholder="you@example.com">
        </div>
        <div class="auth-field">
          <label for="password">비밀번호</label>
          <input id="password" name="password" type="password" autocomplete="current-password" required placeholder="비밀번호 입력">
        </div>
        <button class="btn btn-primary" type="submit" style="width:100%;margin-top:8px">로그인</button>
      </form>
      <p class="auth-link">계정이 없으신가요? <a href="/register">회원가입</a></p>
    </div>
  </div>
</div>
</body>
</html>
```

- [ ] **Step 6: register.html 생성**

```html
<!-- app/templates/register.html -->
<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>회원가입 — FinVoice</title>
  <link rel="stylesheet" href="/static/style.css">
</head>
<body>
<div class="app" id="app">
  <header class="appbar">
    <div class="appbar-in">
      <div class="brand">
        <a href="/" style="text-decoration:none;color:inherit">
          <span class="brand-mark">FinVoice</span>
          <span class="brand-sub">해외 금융뉴스 음성 브리핑</span>
        </a>
      </div>
    </div>
  </header>
  <div class="wrap">
    <div class="auth-box">
      <h1 class="auth-title">회원가입</h1>
      {% if error %}
      <div class="alert-banner" role="alert">{{ error }}</div>
      {% endif %}
      <form class="auth-form" method="POST" action="/register">
        <div class="auth-field">
          <label for="email">이메일</label>
          <input id="email" name="email" type="email" autocomplete="email" required placeholder="you@example.com">
        </div>
        <div class="auth-field">
          <label for="password">비밀번호</label>
          <input id="password" name="password" type="password" autocomplete="new-password" required placeholder="8자 이상 권장">
        </div>
        <button class="btn btn-primary" type="submit" style="width:100%;margin-top:8px">가입하기</button>
      </form>
      <p class="auth-link">이미 계정이 있으신가요? <a href="/login">로그인</a></p>
    </div>
  </div>
</div>
</body>
</html>
```

- [ ] **Step 7: 통과 확인**

```
pytest tests/test_api.py -v
```
Expected: 전체 통과

- [ ] **Step 8: 커밋**

```
git add app/main.py app/auth.py app/templates/login.html app/templates/register.html tests/test_api.py
git commit -m "feat: add email/password auth routes (register, login, logout)"
```

---

## Task 7: 워치리스트 편집 라우트 + 템플릿

**Files:**
- Modify: `app/main.py`
- Create: `app/templates/watchlist_edit.html`
- Modify: `tests/test_api.py`

- [ ] **Step 1: 실패 테스트 추가**

```python
# tests/test_api.py 끝에 추가

def test_watchlist_edit_redirects_when_not_logged_in():
    client = TestClient(main.app, raise_server_exceptions=True)
    resp = client.get("/watchlist/edit", follow_redirects=False)
    assert resp.status_code in (302, 303)
    assert "/login" in resp.headers["location"]

def test_watchlist_edit_page_renders_for_logged_in(monkeypatch):
    cur = FakeCursor(all=[{"symbol": "AAPL", "company": "Apple"}])
    main.app.dependency_overrides[main.get_conn] = lambda: FakeConn(cur)
    monkeypatch.setattr(main.db, "get_watchlist", lambda cur, user_id: [{"symbol": "AAPL", "company": "Apple"}])
    client = TestClient(main.app, raise_server_exceptions=True)
    with client as c:
        c.get("/login")  # 세션 시작
        # 세션에 직접 user_id 주입
        with c.session_transaction() as sess:
            sess["user_id"] = 1
            sess["user_email"] = "t@t.com"
        resp = c.get("/watchlist/edit")
    assert resp.status_code == 200
    assert "관심종목" in resp.text
    main.app.dependency_overrides.clear()
```

- [ ] **Step 2: 실패 확인**

```
pytest tests/test_api.py -v -k "watchlist"
```
Expected: 2 FAILED

- [ ] **Step 3: main.py에 워치리스트 라우트 2개 추가**

```python
# app/main.py — logout 라우트 아래에 추가

@app.get("/watchlist/edit", response_class=HTMLResponse)
def watchlist_edit_page(request: Request, conn=Depends(get_conn)):
    user_id = _current_user_id(request)
    if not user_id:
        return RedirectResponse("/login", status_code=303)
    cur = conn.cursor()
    watchlist = db.get_watchlist(cur, user_id)
    return templates.TemplateResponse(request, "watchlist_edit.html", {
        "watchlist": watchlist,
        "user_email": request.session.get("user_email"),
        "error": None,
    })


@app.post("/watchlist/edit", response_class=HTMLResponse)
def watchlist_edit_save(request: Request, symbols: str = Form(default=""), conn=Depends(get_conn)):
    user_id = _current_user_id(request)
    if not user_id:
        return RedirectResponse("/login", status_code=303)

    # symbols: "AAPL,TSLA,NVDA" 형식
    raw = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    raw = list(dict.fromkeys(raw))[:6]  # 중복 제거, 최대 6개

    from pipeline.fetch import lookup_company
    pairs = []
    errors = []
    for sym in raw:
        # 알려진 종목이면 config에서 바로 사용
        if sym in _COMPANY:
            pairs.append((sym, _COMPANY[sym]))
        else:
            name = lookup_company(sym)
            if name:
                pairs.append((sym, name))
            else:
                errors.append(sym)

    if errors:
        cur = conn.cursor()
        watchlist = db.get_watchlist(cur, user_id)
        return templates.TemplateResponse(request, "watchlist_edit.html", {
            "watchlist": watchlist,
            "user_email": request.session.get("user_email"),
            "error": f"존재하지 않는 종목: {', '.join(errors)}",
        }, status_code=400)

    cur = conn.cursor()
    db.save_watchlist(cur, user_id, pairs)
    conn.commit()
    return RedirectResponse("/", status_code=303)
```

- [ ] **Step 4: watchlist_edit.html 생성**

```html
<!-- app/templates/watchlist_edit.html -->
<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>관심종목 편집 — FinVoice</title>
  <link rel="stylesheet" href="/static/style.css">
</head>
<body>
<div class="app" id="app">
  <header class="appbar">
    <div class="appbar-in">
      <div class="brand">
        <a href="/" style="text-decoration:none;color:inherit">
          <span class="brand-mark">FinVoice</span>
          <span class="brand-sub">해외 금융뉴스 음성 브리핑</span>
        </a>
      </div>
      <div class="appbar-auth">
        <span class="auth-email">{{ user_email }}</span>
        <form method="POST" action="/logout" style="display:inline">
          <button class="btn-auth-ghost" type="submit">로그아웃</button>
        </form>
      </div>
    </div>
  </header>
  <div class="wrap">
    <div class="detail-head">
      <div class="detail-date"><a href="/">← 목록</a></div>
      <h1 class="detail-title">관심종목 편집</h1>
    </div>
    {% if error %}
    <div class="alert-banner" role="alert">{{ error }}</div>
    {% endif %}
    <div class="wl-edit-box">
      <p class="wl-desc">최대 6개 종목을 설정하세요. 심볼을 입력하고 Enter 또는 추가 버튼을 누르세요.</p>
      <div class="wl-chips" id="wlChips">
        {% for w in watchlist %}
        <span class="wl-chip">{{ w.symbol }}<button type="button" class="wl-chip-rm" data-sym="{{ w.symbol }}">✕</button></span>
        {% endfor %}
      </div>
      <div class="wl-input-row">
        <input id="wlInput" type="text" placeholder="예: META" maxlength="10" autocomplete="off" spellcheck="false">
        <button type="button" id="wlAddBtn" class="btn btn-primary" style="height:44px;padding:0 20px">추가</button>
      </div>
      <p class="wl-hint">추천: AAPL · TSLA · NVDA · MSFT · AMZN · GOOGL · META · NFLX</p>
      <form id="wlForm" method="POST" action="/watchlist/edit">
        <input type="hidden" id="wlHidden" name="symbols" value="">
        <button class="btn btn-primary" type="submit" style="width:100%;margin-top:20px">저장</button>
      </form>
    </div>
    <div class="disclaimer" role="contentinfo">
      <span>본 서비스는 정보 제공용이며 투자 조언이 아닙니다.</span>
    </div>
  </div>
</div>
<script>
(function () {
  var MAX = 6;
  var chips = document.getElementById('wlChips');
  var input = document.getElementById('wlInput');
  var addBtn = document.getElementById('wlAddBtn');
  var hidden = document.getElementById('wlHidden');
  var form = document.getElementById('wlForm');

  function getSymbols() {
    return Array.from(chips.querySelectorAll('.wl-chip')).map(function (c) {
      return c.dataset.sym;
    });
  }

  function renderCount() {
    input.disabled = getSymbols().length >= MAX;
    addBtn.disabled = getSymbols().length >= MAX;
  }

  chips.querySelectorAll('.wl-chip-rm').forEach(function (btn) {
    btn.addEventListener('click', function () {
      btn.closest('.wl-chip').remove();
      renderCount();
    });
  });

  function addSymbol() {
    var sym = input.value.trim().toUpperCase();
    if (!sym) return;
    if (getSymbols().includes(sym)) { input.value = ''; return; }
    if (getSymbols().length >= MAX) return;
    var chip = document.createElement('span');
    chip.className = 'wl-chip';
    chip.dataset.sym = sym;
    chip.innerHTML = sym + '<button type="button" class="wl-chip-rm" data-sym="' + sym + '">✕</button>';
    chip.querySelector('.wl-chip-rm').addEventListener('click', function () {
      chip.remove(); renderCount();
    });
    chips.appendChild(chip);
    input.value = '';
    renderCount();
  }

  addBtn.addEventListener('click', addSymbol);
  input.addEventListener('keydown', function (e) {
    if (e.key === 'Enter') { e.preventDefault(); addSymbol(); }
  });
  input.addEventListener('input', function () {
    this.value = this.value.toUpperCase();
  });

  form.addEventListener('submit', function () {
    hidden.value = getSymbols().join(',');
  });

  renderCount();
}());
</script>
</body>
</html>
```

- [ ] **Step 5: 통과 확인**

```
pytest tests/test_api.py -v
```
Expected: 전체 통과

- [ ] **Step 6: 커밋**

```
git add app/main.py app/templates/watchlist_edit.html tests/test_api.py
git commit -m "feat: add watchlist edit route and template"
```

---

## Task 8: / 와 /search 라우트 수정 — 동적 워치리스트 · 임의 심볼 허용

**Files:**
- Modify: `app/main.py`
- Modify: `tests/test_api.py`

- [ ] **Step 1: 실패 테스트 추가**

```python
# tests/test_api.py 끝에 추가

def test_search_rejects_unknown_symbol_when_not_logged_in(monkeypatch):
    cur = FakeCursor(one=None, all=[])
    main.app.dependency_overrides[main.get_conn] = lambda: FakeConn(cur)
    resp = TestClient(main.app).post("/search", data={"symbol": "META"})
    # META는 현재 WATCHLIST에 없음 → 비로그인 시 400
    assert resp.status_code == 400
    main.app.dependency_overrides.clear()

def test_search_allows_arbitrary_symbol_when_logged_in(monkeypatch):
    cur = FakeCursor(one=None, all=[])
    main.app.dependency_overrides[main.get_conn] = lambda: FakeConn(cur)
    monkeypatch.setattr(main.fetch, "lookup_company", lambda sym: "Meta Platforms")
    monkeypatch.setattr(main.runner, "process_symbol",
                        lambda symbol, company, item_date: {
                            "symbol": symbol, "company": company, "summary_ko": "메타요약",
                            "sentiment": "neutral", "audio_url": None, "articles": []})
    client = TestClient(main.app, raise_server_exceptions=True)
    with client as c:
        with c.session_transaction() as sess:
            sess["user_id"] = 1
            sess["user_email"] = "t@t.com"
        resp = c.post("/search", data={"symbol": "META"})
    assert resp.status_code == 200
    assert "메타요약" in resp.text
    main.app.dependency_overrides.clear()
```

- [ ] **Step 2: 실패 확인**

```
pytest tests/test_api.py -v -k "unknown_symbol or arbitrary_symbol"
```
Expected: 2 FAILED

- [ ] **Step 3: main.py의 index() 수정 — 로그인 시 커스텀 워치리스트 반영**

```python
# 기존 index() 함수를 아래로 교체

@app.get("/", response_class=HTMLResponse)
def index(request: Request, conn=Depends(get_conn)):
    today = date.today().isoformat()
    cur = conn.cursor()
    briefings = db.list_briefings(cur)
    user_id = _current_user_id(request)
    if user_id:
        rows = db.get_watchlist(cur, user_id)
        watchlist_meta = [
            {"sym": r["symbol"], "company": r["company"],
             "domain": config.LOGO_DOMAINS.get(r["symbol"], "")}
            for r in rows
        ] or list(templates.env.globals["WATCHLIST_META"])
    else:
        watchlist_meta = list(templates.env.globals["WATCHLIST_META"])
    return templates.TemplateResponse(request, "list.html", {
        "briefings": briefings,
        "supported": SUPPORTED,
        "today": today,
        "error": None,
        "user_email": request.session.get("user_email"),
        "watchlist_meta": watchlist_meta,
    })
```

- [ ] **Step 4: main.py의 search() 수정 — 비로그인/로그인 분기**

```python
# 기존 search() 함수를 아래로 교체

from pipeline import fetch as _fetch_module  # 파일 상단에 추가

@app.post("/search", response_class=HTMLResponse)
def search(request: Request, symbol: str = Form(...), conn=Depends(get_conn)):
    today = date.today().isoformat()
    symbol = symbol.strip().upper()
    cur = conn.cursor()
    user_id = _current_user_id(request)

    # 심볼 유효성 검사: 비로그인 → WATCHLIST만, 로그인 → Finnhub 조회
    if symbol in _COMPANY:
        company_name = _COMPANY[symbol]
    elif user_id:
        company_name = _fetch_module.lookup_company(symbol)
        if not company_name:
            briefings = db.list_briefings(cur)
            return templates.TemplateResponse(request, "list.html", {
                "briefings": briefings, "supported": SUPPORTED, "today": today,
                "error": f"존재하지 않는 종목입니다: {symbol}",
                "user_email": request.session.get("user_email"),
                "watchlist_meta": list(templates.env.globals["WATCHLIST_META"]),
            }, status_code=400)
    else:
        briefings = db.list_briefings(cur)
        return templates.TemplateResponse(request, "list.html", {
            "briefings": briefings, "supported": SUPPORTED, "today": today,
            "error": f"지원하지 않는 종목입니다. 지원 종목: {', '.join(SUPPORTED)}",
            "user_email": request.session.get("user_email"),
            "watchlist_meta": list(templates.env.globals["WATCHLIST_META"]),
        }, status_code=400)

    item = db.find_cached_item(cur, symbol, today)
    if item:
        item = dict(item)
        if item.get("sentiment") not in {"positive", "neutral", "negative"}:
            item["sentiment"] = "neutral"
        item["articles"] = db.get_articles_for_item(cur, item["id"])
    else:
        try:
            result = runner.process_symbol(symbol, company_name, today)
        except Exception:
            briefings = db.list_briefings(cur)
            return templates.TemplateResponse(request, "list.html", {
                "briefings": briefings, "supported": SUPPORTED, "today": today,
                "error": "요약 생성에 실패했습니다. 잠시 후 다시 시도해주세요.",
                "user_email": request.session.get("user_email"),
                "watchlist_meta": list(templates.env.globals["WATCHLIST_META"]),
            }, status_code=500)
        item_id = db.insert_item(
            cur, None, symbol, company_name,
            result["summary_ko"], result["sentiment"], result["audio_url"],
            today, "ondemand",
        )
        for art in result["articles"]:
            db.insert_article(cur, item_id, art)
        conn.commit()
        item = {**result, "id": item_id, "articles": result["articles"]}

    briefing = {"briefing_date": today, "market_summary": None}
    return templates.TemplateResponse(request, "detail.html", {
        "briefing": briefing, "items": [item], "is_search": True,
        "supported": SUPPORTED, "today": today,
        "user_email": request.session.get("user_email"),
    })
```

main.py 상단 import에 아래 추가:
```python
from pipeline import fetch as _fetch_module
```

- [ ] **Step 5: 통과 확인**

```
pytest tests/test_api.py -v
```
Expected: 전체 통과

- [ ] **Step 6: 커밋**

```
git add app/main.py tests/test_api.py
git commit -m "feat: allow arbitrary symbol search for logged-in users, dynamic watchlist on /"
```

---

## Task 9: 템플릿 업데이트 — 헤더 로그인 상태 + 동적 티커바

**Files:**
- Modify: `app/templates/list.html`
- Modify: `app/templates/detail.html`

- [ ] **Step 1: list.html appbar에 로그인 상태 추가**

`list.html`의 `<div class="appbar-in">` 블록을 아래로 교체:

```html
<div class="appbar-in">
  <div class="brand">
    <span class="brand-mark">FinVoice</span>
    <span class="brand-sub">해외 금융뉴스 음성 브리핑</span>
  </div>
  <div class="appbar-auth">
    {% if user_email %}
      <span class="auth-email">{{ user_email }}</span>
      <a class="btn-auth-ghost" href="/watchlist/edit">관심종목 편집</a>
      <form method="POST" action="/logout" style="display:inline">
        <button class="btn-auth-ghost" type="submit">로그아웃</button>
      </form>
    {% else %}
      <a class="btn-auth-ghost" href="/login">로그인</a>
      <a class="btn-auth-primary" href="/register">회원가입</a>
    {% endif %}
  </div>
</div>
```

- [ ] **Step 2: list.html 티커바를 `watchlist_meta` 변수로 교체**

기존 `{% for w in WATCHLIST_META %}` → `{% for w in watchlist_meta %}`

- [ ] **Step 3: list.html 티커바 JS도 동적 심볼 반영 확인**

티커바 `click` 이벤트는 `data-sym` 기반이라 이미 동작함. `/api/quotes` 호출도 그대로.

- [ ] **Step 4: detail.html appbar에 로그인 상태 추가**

`detail.html`의 `<div class="appbar-in">` 블록을 아래로 교체:

```html
<div class="appbar-in">
  <div class="brand">
    <span class="brand-mark">FinVoice</span>
    <span class="brand-sub">해외 금융뉴스 음성 브리핑</span>
  </div>
  <div class="appbar-auth">
    {% if user_email %}
      <span class="auth-email">{{ user_email }}</span>
      <a class="btn-auth-ghost" href="/watchlist/edit">관심종목 편집</a>
      <form method="POST" action="/logout" style="display:inline">
        <button class="btn-auth-ghost" type="submit">로그아웃</button>
      </form>
    {% else %}
      <a class="btn-auth-ghost" href="/login">로그인</a>
      <a class="btn-auth-primary" href="/register">회원가입</a>
    {% endif %}
  </div>
</div>
```

- [ ] **Step 5: briefing_detail 라우트에 user_email 전달 추가**

```python
# main.py의 briefing_detail() return 부분 수정
return templates.TemplateResponse(request, "detail.html", {
    "briefing": briefing,
    "items": items,
    "is_search": False,
    "supported": SUPPORTED,
    "today": today,
    "user_email": request.session.get("user_email"),  # 추가
})
```

- [ ] **Step 6: 전체 테스트 통과 확인**

```
pytest -q
```
Expected: 전체 통과

- [ ] **Step 7: 커밋**

```
git add app/templates/list.html app/templates/detail.html app/main.py
git commit -m "feat: add login state to appbar, dynamic ticker bar"
```

---

## Task 10: CSS — 인증·워치리스트 편집 스타일 추가

**Files:**
- Modify: `app/static/style.css`

- [ ] **Step 1: style.css 끝에 스타일 블록 추가**

```css
/* ── Appbar auth ────────────────────────────────────── */
.appbar-auth {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: auto;
}
.auth-email {
  font-size: 13px;
  color: var(--text-2);
  max-width: 160px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.btn-auth-ghost {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-2);
  background: none;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 5px 12px;
  cursor: pointer;
  text-decoration: none;
  transition: color var(--dur), border-color var(--dur);
}
.btn-auth-ghost:hover { color: var(--text-1); border-color: var(--text-3); }
.btn-auth-primary {
  font-size: 13px;
  font-weight: 600;
  color: #fff;
  background: var(--accent);
  border: none;
  border-radius: var(--radius-sm);
  padding: 5px 12px;
  cursor: pointer;
  text-decoration: none;
}
.btn-auth-primary:hover { opacity: 0.85; }

/* ── Auth pages (login / register) ─────────────────── */
.auth-box {
  max-width: 400px;
  margin: 48px auto 0;
  padding: 32px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
}
.auth-title {
  font-size: 22px;
  font-weight: 700;
  color: var(--text-1);
  margin-bottom: 24px;
}
.auth-form { display: flex; flex-direction: column; gap: 16px; }
.auth-field { display: flex; flex-direction: column; gap: 6px; }
.auth-field label { font-size: 13px; font-weight: 500; color: var(--text-2); }
.auth-field input {
  height: 44px;
  padding: 0 14px;
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  color: var(--text-1);
  font-size: 14px;
  transition: border-color var(--dur);
}
.auth-field input:focus { outline: none; border-color: var(--accent); }
.auth-link {
  margin-top: 20px;
  text-align: center;
  font-size: 13px;
  color: var(--text-2);
}
.auth-link a { color: var(--accent); }

/* ── Watchlist edit page ────────────────────────────── */
.wl-edit-box {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 24px;
  margin-top: 8px;
}
.wl-desc { font-size: 14px; color: var(--text-2); margin-bottom: 16px; }
.wl-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  min-height: 44px;
  margin-bottom: 12px;
}
.wl-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 10px;
  background: var(--accent-bg);
  color: var(--accent);
  border-radius: var(--radius-sm);
  font-size: 13px;
  font-weight: 600;
}
.wl-chip-rm {
  background: none;
  border: none;
  color: var(--text-3);
  cursor: pointer;
  padding: 0;
  font-size: 12px;
  line-height: 1;
}
.wl-chip-rm:hover { color: var(--s-negative); }
.wl-input-row { display: flex; gap: 8px; }
.wl-input-row input {
  flex: 1;
  height: 44px;
  padding: 0 14px;
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  color: var(--text-1);
  font-size: 14px;
  text-transform: uppercase;
}
.wl-input-row input:focus { outline: none; border-color: var(--accent); }
.wl-hint { font-size: 12px; color: var(--text-3); margin-top: 8px; }

@media (max-width: 480px) {
  .appbar-auth { gap: 6px; }
  .auth-email { display: none; }
  .auth-box { margin: 24px auto 0; padding: 20px; }
}
```

- [ ] **Step 2: 전체 테스트 최종 확인**

```
pytest -q
```
Expected: 전체 통과

- [ ] **Step 3: 최종 커밋**

```
git add app/static/style.css
git commit -m "feat: add auth and watchlist edit CSS"
```

---

## 자기 검토 (Spec Coverage)

| 요구사항 | 구현 태스크 |
|---------|------------|
| 이메일/비밀번호 로그인 | Task 3, 6 |
| bcrypt 비밀번호 해싱 | Task 3 |
| 회원가입 | Task 6 |
| 로그아웃 | Task 6 |
| 커스텀 6개 워치리스트 저장 | Task 4, 7 |
| 로그인 시 커스텀 티커바 | Task 8, 9 |
| 비로그인 → 기본 6개만 | Task 8 |
| 로그인 → 임의 Finnhub 심볼 검색 | Task 5, 8 |
| 헤더 로그인 상태 표시 | Task 9 |
| 전체 테스트 통과 | 각 태스크 Step |
