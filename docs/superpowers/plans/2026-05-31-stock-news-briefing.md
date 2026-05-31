# 해외 금융뉴스 번역·요약·음성 브리핑 서비스 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 해외 영어 금융뉴스를 수집→Papago 번역→CLOVA Studio 요약→CLOVA Voice 음성화하여 정기 브리핑과 온디맨드 검색으로 제공하는 FastAPI 웹 서비스를 구현한다.

**Architecture:** 번역·요약·TTS 로직을 `pipeline/` 공용 모듈에 모으고, `batch_job.py`(cron 자동 배치)와 FastAPI `/search`(온디맨드)가 같은 `runner`를 호출하는 "하나의 파이프라인 + 두 진입점" 구조. 데이터는 NCP Cloud DB for MySQL에, 음성 mp3는 NCP Object Storage에 저장.

**Tech Stack:** Python 3.10+, FastAPI, uvicorn, Jinja2, PyMySQL, httpx, boto3(Object Storage, S3 호환), pytest, python-dotenv. 외부: 영어 금융뉴스 API(Finnhub 등). NCP: Papago / CLOVA Studio / CLOVA Voice / Object Storage / Cloud DB for MySQL / Server(VM).

---

## 참고: NCP API 엔드포인트 확인

아래 작업의 코드는 NCP의 일반적인 REST 패턴을 따른다. **키 발급 후 NCP 콘솔의 각 서비스 문서에서 정확한 엔드포인트·헤더명을 1일차에 확인**하고, 다르면 해당 모듈의 상수만 교체한다(로직은 동일). 본 계획에서 사용하는 값:

- Papago 번역: `POST https://naveropenapi.apigw.ntruss.com/nmt/v1/translation`, 헤더 `X-NCP-APIGW-API-KEY-ID`, `X-NCP-APIGW-API-KEY`
- CLOVA Voice(Premium TTS): `POST https://naveropenapi.apigw.ntruss.com/tts-premium/v1/tts`, 동일 헤더, 응답 = mp3 바이너리
- CLOVA Studio(요약): `POST https://clovastudio.stream.ntruss.com/testapp/v1/chat-completions/HCX-003`, 헤더 `X-NCP-CLOVASTUDIO-API-KEY`, `X-NCP-APIGW-API-KEY`
- Object Storage: S3 호환, endpoint `https://kr.object.ncloudstorage.com`, boto3 사용

각 모듈은 외부 호출부를 함수 하나로 격리하므로, 테스트는 그 함수를 mock하고 실제 엔드포인트 변경의 영향은 최소화된다.

---

## 파일 구조

| 파일 | 책임 |
|------|------|
| `requirements.txt` | 의존성 |
| `.env.example` | 키/설정 템플릿 (실제 `.env`는 git 제외) |
| `.gitignore` | `.env`, `__pycache__`, `logs/` 제외 |
| `app/config.py` | 환경변수 로딩, 고정 관심종목 목록 |
| `app/db.py` | MySQL 연결, 저장/조회 쿼리 |
| `app/main.py` | FastAPI 앱, 라우트(`/`, `/briefing/{id}`, `/search`) |
| `app/templates/` | Jinja2 템플릿(목록, 상세) |
| `app/static/style.css` | 최소 스타일 |
| `pipeline/fetch.py` | 뉴스 API 수집 + 중복 제거 |
| `pipeline/translate.py` | Papago 번역 |
| `pipeline/summarize.py` | CLOVA Studio 요약 |
| `pipeline/tts.py` | CLOVA Voice 합성 + Object Storage 업로드 |
| `pipeline/runner.py` | 종목 단위 오케스트레이션(부분 성공 허용) |
| `batch_job.py` | cron 진입점 |
| `scripts/init_db.sql` | 테이블 생성 |
| `tests/` | 단위/통합 테스트 |

각 `pipeline/*` 모듈은 외부 호출부를 하나의 함수로 격리하여 단위 테스트에서 mock 가능하게 한다.

---

## Task 0: 프로젝트 스캐폴딩 & git 초기화

**Files:**
- Create: `requirements.txt`, `.gitignore`, `.env.example`, `app/__init__.py`, `pipeline/__init__.py`, `tests/__init__.py`

- [ ] **Step 1: git 저장소 초기화**

```bash
cd C:/Users/Administrator/Downloads/claude/proj
git init
```

- [ ] **Step 2: `requirements.txt` 작성**

```
fastapi==0.111.0
uvicorn[standard]==0.30.1
jinja2==3.1.4
python-multipart==0.0.9
PyMySQL==1.1.1
httpx==0.27.0
boto3==1.34.140
python-dotenv==1.0.1
pytest==8.2.2
```

- [ ] **Step 3: `.gitignore` 작성**

```
.env
__pycache__/
*.pyc
logs/
.pytest_cache/
.venv/
```

- [ ] **Step 4: `.env.example` 작성**

```
# 외부 금융뉴스 API
NEWS_API_KEY=your_finnhub_key

# NCP API Gateway 공통
NCP_APIGW_KEY_ID=your_apigw_key_id
NCP_APIGW_KEY=your_apigw_key

# CLOVA Studio
CLOVA_STUDIO_API_KEY=your_clova_studio_key

# Object Storage (S3 호환)
NCP_OS_ACCESS_KEY=your_access_key
NCP_OS_SECRET_KEY=your_secret_key
NCP_OS_ENDPOINT=https://kr.object.ncloudstorage.com
NCP_OS_BUCKET=stock-briefing-audio

# Cloud DB for MySQL
DB_HOST=your_db_host
DB_PORT=3306
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_NAME=stock_briefing
```

- [ ] **Step 5: 빈 패키지 파일 생성**

`app/__init__.py`, `pipeline/__init__.py`, `tests/__init__.py` 를 빈 파일로 생성.

- [ ] **Step 6: 가상환경·의존성 설치 확인**

Run: `python -m venv .venv && .venv\Scripts\pip install -r requirements.txt`
Expected: 모든 패키지 설치 성공.

- [ ] **Step 7: Commit**

```bash
git add requirements.txt .gitignore .env.example app/__init__.py pipeline/__init__.py tests/__init__.py
git commit -m "chore: scaffold project structure and dependencies"
```

---

## Task 1: 설정 모듈 (`app/config.py`)

**Files:**
- Create: `app/config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: 실패하는 테스트 작성** — `tests/test_config.py`

```python
from app import config

def test_watchlist_is_fixed_nonempty_list():
    assert isinstance(config.WATCHLIST, list)
    assert 5 <= len(config.WATCHLIST) <= 8
    # 각 항목은 (symbol, company) 튜플
    for symbol, company in config.WATCHLIST:
        assert symbol and company

def test_env_helper_reads_value(monkeypatch):
    monkeypatch.setenv("NEWS_API_KEY", "abc123")
    assert config.get_env("NEWS_API_KEY") == "abc123"

def test_env_helper_raises_when_missing(monkeypatch):
    monkeypatch.delenv("DEFINITELY_MISSING", raising=False)
    import pytest
    with pytest.raises(RuntimeError):
        config.get_env("DEFINITELY_MISSING")
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `.venv\Scripts\pytest tests/test_config.py -v`
Expected: FAIL (`ModuleNotFoundError` 또는 `AttributeError`)

- [ ] **Step 3: `app/config.py` 구현**

```python
import os
from dotenv import load_dotenv

load_dotenv()

# 고정 관심종목 (symbol, 회사명)
WATCHLIST = [
    ("AAPL", "Apple"),
    ("TSLA", "Tesla"),
    ("NVDA", "NVIDIA"),
    ("MSFT", "Microsoft"),
    ("AMZN", "Amazon"),
    ("GOOGL", "Alphabet"),
]

# 수집 파라미터
ARTICLES_PER_SYMBOL = 5
MARKET_ARTICLE_COUNT = 8

def get_env(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise RuntimeError(f"환경변수 {key} 가 설정되지 않았습니다. .env 를 확인하세요.")
    return value
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `.venv\Scripts\pytest tests/test_config.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add app/config.py tests/test_config.py
git commit -m "feat: add config module with fixed watchlist and env helper"
```

---

## Task 2: 뉴스 수집 (`pipeline/fetch.py`)

**Files:**
- Create: `pipeline/fetch.py`
- Test: `tests/test_fetch.py`

수집부 `_call_news_api(symbol)` 를 격리하고, 파싱·중복제거 로직 `parse_articles`, `dedupe` 를 분리한다. 테스트는 `_call_news_api` 를 mock한다.

- [ ] **Step 1: 실패하는 테스트 작성** — `tests/test_fetch.py`

```python
from pipeline import fetch

RAW = [
    {"headline": "Apple hits record", "url": "http://x.com/a", "source": "Reuters", "datetime": 1717000000, "summary": "body a"},
    {"headline": "Apple hits record", "url": "http://x.com/a", "source": "Reuters", "datetime": 1717000000, "summary": "body a"},  # 중복
    {"headline": "Apple new chip", "url": "http://x.com/b", "source": "CNBC", "datetime": 1717000100, "summary": "body b"},
]

def test_parse_articles_maps_fields():
    parsed = fetch.parse_articles(RAW)
    assert parsed[0]["title_en"] == "Apple hits record"
    assert parsed[0]["url"] == "http://x.com/a"
    assert parsed[0]["source_name"] == "Reuters"
    assert "url_hash" in parsed[0]

def test_dedupe_removes_same_url():
    parsed = fetch.parse_articles(RAW)
    deduped = fetch.dedupe(parsed)
    assert len(deduped) == 2

def test_fetch_symbol_uses_api_and_limits(monkeypatch):
    monkeypatch.setattr(fetch, "_call_news_api", lambda symbol: RAW)
    result = fetch.fetch_symbol("AAPL", limit=1)
    assert len(result) == 1
    assert result[0]["title_en"]
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `.venv\Scripts\pytest tests/test_fetch.py -v`
Expected: FAIL (module/attr 없음)

- [ ] **Step 3: `pipeline/fetch.py` 구현**

```python
import hashlib
import httpx
from app import config

NEWS_API_BASE = "https://finnhub.io/api/v1"

def _call_news_api(symbol: str) -> list[dict]:
    """외부 금융뉴스 API 호출. 격리되어 테스트에서 mock 된다."""
    key = config.get_env("NEWS_API_KEY")
    # 최근 뉴스 조회 (날짜 범위는 호출 측에서 고정 기간 사용)
    url = f"{NEWS_API_BASE}/company-news"
    params = {"symbol": symbol, "from": "2026-05-24", "to": "2026-05-31", "token": key}
    resp = httpx.get(url, params=params, timeout=10.0)
    resp.raise_for_status()
    return resp.json()

def parse_articles(raw: list[dict]) -> list[dict]:
    out = []
    for r in raw:
        url = r.get("url", "")
        out.append({
            "title_en": r.get("headline", ""),
            "url": url,
            "source_name": r.get("source", ""),
            "published_at": r.get("datetime"),
            "body_en": r.get("summary", ""),
            "url_hash": hashlib.sha256(url.encode()).hexdigest(),
        })
    return out

def dedupe(articles: list[dict]) -> list[dict]:
    seen = set()
    out = []
    for a in articles:
        if a["url_hash"] in seen:
            continue
        seen.add(a["url_hash"])
        out.append(a)
    return out

def fetch_symbol(symbol: str, limit: int = None) -> list[dict]:
    limit = limit or config.ARTICLES_PER_SYMBOL
    raw = _call_news_api(symbol)
    articles = dedupe(parse_articles(raw))
    return articles[:limit]
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `.venv\Scripts\pytest tests/test_fetch.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add pipeline/fetch.py tests/test_fetch.py
git commit -m "feat: add news fetch with parsing and dedupe"
```

---

## Task 3: 번역 (`pipeline/translate.py`)

**Files:**
- Create: `pipeline/translate.py`
- Test: `tests/test_translate.py`

외부 호출부 `_call_papago(text)` 격리. `translate_text` 가 공백/빈 입력은 그대로 반환(불필요 호출 방지).

- [ ] **Step 1: 실패하는 테스트 작성** — `tests/test_translate.py`

```python
from pipeline import translate

def test_translate_text_returns_translation(monkeypatch):
    monkeypatch.setattr(translate, "_call_papago", lambda text: "사과 주가 사상 최고")
    assert translate.translate_text("Apple hits record") == "사과 주가 사상 최고"

def test_translate_text_skips_empty(monkeypatch):
    called = {"n": 0}
    def fake(text):
        called["n"] += 1
        return "x"
    monkeypatch.setattr(translate, "_call_papago", fake)
    assert translate.translate_text("") == ""
    assert translate.translate_text("   ") == "   "
    assert called["n"] == 0

def test_translate_articles_fills_title_ko(monkeypatch):
    monkeypatch.setattr(translate, "_call_papago", lambda text: "번역됨")
    arts = [{"title_en": "A", "body_en": "B"}]
    out = translate.translate_articles(arts)
    assert out[0]["title_ko"] == "번역됨"
    assert out[0]["body_ko"] == "번역됨"
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `.venv\Scripts\pytest tests/test_translate.py -v`
Expected: FAIL

- [ ] **Step 3: `pipeline/translate.py` 구현**

```python
import httpx
from app import config

PAPAGO_URL = "https://naveropenapi.apigw.ntruss.com/nmt/v1/translation"

def _call_papago(text: str) -> str:
    """Papago 번역 호출. 테스트에서 mock 된다."""
    headers = {
        "X-NCP-APIGW-API-KEY-ID": config.get_env("NCP_APIGW_KEY_ID"),
        "X-NCP-APIGW-API-KEY": config.get_env("NCP_APIGW_KEY"),
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {"source": "en", "target": "ko", "text": text[:4500]}  # 글자 수 제한 보호
    resp = httpx.post(PAPAGO_URL, headers=headers, data=data, timeout=10.0)
    resp.raise_for_status()
    return resp.json()["message"]["result"]["translatedText"]

def translate_text(text: str) -> str:
    if not text or not text.strip():
        return text
    return _call_papago(text)

def translate_articles(articles: list[dict]) -> list[dict]:
    for a in articles:
        a["title_ko"] = translate_text(a.get("title_en", ""))
        a["body_ko"] = translate_text(a.get("body_en", ""))
    return articles
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `.venv\Scripts\pytest tests/test_translate.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add pipeline/translate.py tests/test_translate.py
git commit -m "feat: add Papago translation module"
```

---

## Task 4: 요약 (`pipeline/summarize.py`)

**Files:**
- Create: `pipeline/summarize.py`
- Test: `tests/test_summarize.py`

`_call_clova_studio(prompt)` 격리. `build_prompt` 는 할루시네이션 방지 지시문 포함. `summarize_symbol` 은 여러 기사를 묶어 요약 + 감성 라벨 반환. 반환은 `{"summary_ko": str, "sentiment": "positive|neutral|negative"}`.

- [ ] **Step 1: 실패하는 테스트 작성** — `tests/test_summarize.py`

```python
from pipeline import summarize

ARTS = [
    {"title_ko": "사과 신고가", "body_ko": "실적 호조"},
    {"title_ko": "사과 신제품", "body_ko": "아이폰 출시"},
]

def test_build_prompt_includes_guardrail_and_articles():
    prompt = summarize.build_prompt("Apple", ARTS)
    assert "추측" in prompt  # "추측 금지" 가드레일
    assert "사과 신고가" in prompt

def test_summarize_symbol_parses_response(monkeypatch):
    fake = '{"summary": "애플은 실적 호조로 신고가를 기록했다.", "sentiment": "positive"}'
    monkeypatch.setattr(summarize, "_call_clova_studio", lambda prompt: fake)
    result = summarize.summarize_symbol("Apple", ARTS)
    assert result["summary_ko"].startswith("애플")
    assert result["sentiment"] == "positive"

def test_summarize_symbol_defaults_neutral_on_bad_sentiment(monkeypatch):
    fake = '{"summary": "요약", "sentiment": "weird"}'
    monkeypatch.setattr(summarize, "_call_clova_studio", lambda prompt: fake)
    result = summarize.summarize_symbol("Apple", ARTS)
    assert result["sentiment"] == "neutral"
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `.venv\Scripts\pytest tests/test_summarize.py -v`
Expected: FAIL

- [ ] **Step 3: `pipeline/summarize.py` 구현**

```python
import json
import httpx
from app import config

CLOVA_URL = "https://clovastudio.stream.ntruss.com/testapp/v1/chat-completions/HCX-003"
VALID_SENTIMENT = {"positive", "neutral", "negative"}

def build_prompt(company: str, articles: list[dict]) -> str:
    bullets = "\n".join(f"- {a.get('title_ko','')}: {a.get('body_ko','')}" for a in articles)
    return (
        f"다음은 '{company}' 관련 최신 뉴스 기사들이다.\n{bullets}\n\n"
        "위 기사 내용에서만 근거하여 작성하라. 기사에 없는 내용은 추측하지 마라.\n"
        "핵심 이슈를 한국어 3~5문장으로 요약하고, 전반적 시장 감성을 "
        "positive/neutral/negative 중 하나로 판단하라.\n"
        '반드시 JSON 형식으로만 답하라: {"summary": "...", "sentiment": "..."}'
    )

def _call_clova_studio(prompt: str) -> str:
    """CLOVA Studio 호출. 테스트에서 mock 된다. 반환은 모델 답변 문자열."""
    headers = {
        "X-NCP-CLOVASTUDIO-API-KEY": config.get_env("CLOVA_STUDIO_API_KEY"),
        "X-NCP-APIGW-API-KEY": config.get_env("NCP_APIGW_KEY"),
        "Content-Type": "application/json",
    }
    body = {
        "messages": [
            {"role": "system", "content": "너는 금융 뉴스 요약 도우미다. 제공된 내용만 사용한다."},
            {"role": "user", "content": prompt},
        ],
        "maxTokens": 500,
        "temperature": 0.3,
    }
    resp = httpx.post(CLOVA_URL, headers=headers, json=body, timeout=30.0)
    resp.raise_for_status()
    return resp.json()["result"]["message"]["content"]

def _extract_json(text: str) -> dict:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        return {"summary": text.strip(), "sentiment": "neutral"}
    return json.loads(text[start:end + 1])

def summarize_symbol(company: str, articles: list[dict]) -> dict:
    raw = _call_clova_studio(build_prompt(company, articles))
    parsed = _extract_json(raw)
    sentiment = parsed.get("sentiment", "neutral")
    if sentiment not in VALID_SENTIMENT:
        sentiment = "neutral"
    return {"summary_ko": parsed.get("summary", "").strip(), "sentiment": sentiment}
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `.venv\Scripts\pytest tests/test_summarize.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add pipeline/summarize.py tests/test_summarize.py
git commit -m "feat: add CLOVA Studio summarization with sentiment"
```

---

## Task 5: 음성 합성 + 업로드 (`pipeline/tts.py`)

**Files:**
- Create: `pipeline/tts.py`
- Test: `tests/test_tts.py`

`_call_clova_voice(text) -> bytes` 와 `_upload_to_storage(data, key) -> url` 격리. `synthesize_and_upload(text, key)` 가 둘을 묶고, TTS 실패는 호출 측(runner)에서 처리하도록 예외를 그대로 전파.

- [ ] **Step 1: 실패하는 테스트 작성** — `tests/test_tts.py`

```python
from pipeline import tts

def test_synthesize_and_upload_returns_url(monkeypatch):
    monkeypatch.setattr(tts, "_call_clova_voice", lambda text: b"FAKE_MP3")
    captured = {}
    def fake_upload(data, key):
        captured["data"] = data
        captured["key"] = key
        return f"https://cdn/{key}"
    monkeypatch.setattr(tts, "_upload_to_storage", fake_upload)
    url = tts.synthesize_and_upload("안녕하세요", "audio/2026-05-31/AAPL.mp3")
    assert url == "https://cdn/audio/2026-05-31/AAPL.mp3"
    assert captured["data"] == b"FAKE_MP3"

def test_synthesize_skips_empty(monkeypatch):
    monkeypatch.setattr(tts, "_call_clova_voice", lambda text: b"X")
    assert tts.synthesize_and_upload("", "k") is None
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `.venv\Scripts\pytest tests/test_tts.py -v`
Expected: FAIL

- [ ] **Step 3: `pipeline/tts.py` 구현**

```python
import boto3
import httpx
from app import config

TTS_URL = "https://naveropenapi.apigw.ntruss.com/tts-premium/v1/tts"

def _call_clova_voice(text: str) -> bytes:
    """CLOVA Voice 호출. mp3 바이너리 반환. 테스트에서 mock 된다."""
    headers = {
        "X-NCP-APIGW-API-KEY-ID": config.get_env("NCP_APIGW_KEY_ID"),
        "X-NCP-APIGW-API-KEY": config.get_env("NCP_APIGW_KEY"),
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {"speaker": "nara", "text": text[:1900], "format": "mp3"}  # 길이 제한 보호
    resp = httpx.post(TTS_URL, headers=headers, data=data, timeout=30.0)
    resp.raise_for_status()
    return resp.content

def _upload_to_storage(data: bytes, key: str) -> str:
    """Object Storage(S3 호환)에 업로드 후 공개 URL 반환. 테스트에서 mock 된다."""
    endpoint = config.get_env("NCP_OS_ENDPOINT")
    bucket = config.get_env("NCP_OS_BUCKET")
    client = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=config.get_env("NCP_OS_ACCESS_KEY"),
        aws_secret_access_key=config.get_env("NCP_OS_SECRET_KEY"),
    )
    client.put_object(Bucket=bucket, Key=key, Body=data, ContentType="audio/mpeg", ACL="public-read")
    return f"{endpoint}/{bucket}/{key}"

def synthesize_and_upload(text: str, key: str) -> str | None:
    if not text or not text.strip():
        return None
    audio = _call_clova_voice(text)
    return _upload_to_storage(audio, key)
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `.venv\Scripts\pytest tests/test_tts.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add pipeline/tts.py tests/test_tts.py
git commit -m "feat: add CLOVA Voice synthesis and Object Storage upload"
```

---

## Task 6: DB 모듈 (`app/db.py`) + 스키마 (`scripts/init_db.sql`)

**Files:**
- Create: `app/db.py`, `scripts/init_db.sql`
- Test: `tests/test_db.py`

DB 연결부 `get_connection()` 격리. 저장/조회 함수는 커서를 인자로 받는 순수 함수로 작성해 fake 커서로 테스트한다.

- [ ] **Step 1: `scripts/init_db.sql` 작성**

```sql
CREATE DATABASE IF NOT EXISTS stock_briefing CHARACTER SET utf8mb4;
USE stock_briefing;

CREATE TABLE IF NOT EXISTS briefing (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    briefing_date DATE NOT NULL,
    market_summary TEXT,
    market_audio_url VARCHAR(500),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_date (briefing_date)
);

CREATE TABLE IF NOT EXISTS briefing_item (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    briefing_id BIGINT NULL,
    symbol VARCHAR(16) NOT NULL,
    company VARCHAR(100),
    summary_ko TEXT NOT NULL,
    sentiment ENUM('positive','neutral','negative') DEFAULT 'neutral',
    audio_url VARCHAR(500),
    item_date DATE NOT NULL,
    source ENUM('batch','ondemand') DEFAULT 'batch',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (briefing_id) REFERENCES briefing(id),
    KEY idx_symbol_date (symbol, item_date)
);

CREATE TABLE IF NOT EXISTS article (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    item_id BIGINT NOT NULL,
    title_en VARCHAR(500),
    title_ko VARCHAR(500),
    url VARCHAR(1000),
    source_name VARCHAR(100),
    published_at DATETIME NULL,
    url_hash CHAR(64),
    FOREIGN KEY (item_id) REFERENCES briefing_item(id),
    KEY idx_url_hash (url_hash)
);
```

- [ ] **Step 2: 실패하는 테스트 작성** — `tests/test_db.py`

```python
from app import db

class FakeCursor:
    def __init__(self, fetchone_result=None, fetchall_result=None):
        self.executed = []
        self._one = fetchone_result
        self._all = fetchall_result or []
        self.lastrowid = 42
    def execute(self, sql, params=None):
        self.executed.append((sql, params))
    def fetchone(self):
        return self._one
    def fetchall(self):
        return self._all

def test_insert_item_returns_lastrowid():
    cur = FakeCursor()
    new_id = db.insert_item(cur, briefing_id=1, symbol="AAPL", company="Apple",
                            summary_ko="요약", sentiment="positive",
                            audio_url="http://a", item_date="2026-05-31", source="batch")
    assert new_id == 42
    assert "INSERT INTO briefing_item" in cur.executed[0][0]

def test_find_cached_item_returns_row():
    row = {"id": 7, "symbol": "AAPL", "summary_ko": "요약"}
    cur = FakeCursor(fetchone_result=row)
    result = db.find_cached_item(cur, "AAPL", "2026-05-31")
    assert result == row
    assert "WHERE symbol" in cur.executed[0][0]
```

- [ ] **Step 3: 테스트 실패 확인**

Run: `.venv\Scripts\pytest tests/test_db.py -v`
Expected: FAIL

- [ ] **Step 4: `app/db.py` 구현**

```python
import pymysql
from app import config

def get_connection():
    """MySQL 연결 생성. 테스트에서는 호출하지 않는다."""
    return pymysql.connect(
        host=config.get_env("DB_HOST"),
        port=int(config.get_env("DB_PORT")),
        user=config.get_env("DB_USER"),
        password=config.get_env("DB_PASSWORD"),
        database=config.get_env("DB_NAME"),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )

def insert_briefing(cur, briefing_date, market_summary, market_audio_url) -> int:
    cur.execute(
        "INSERT INTO briefing (briefing_date, market_summary, market_audio_url) "
        "VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE "
        "market_summary=VALUES(market_summary), market_audio_url=VALUES(market_audio_url)",
        (briefing_date, market_summary, market_audio_url),
    )
    return cur.lastrowid

def insert_item(cur, briefing_id, symbol, company, summary_ko, sentiment,
                audio_url, item_date, source) -> int:
    cur.execute(
        "INSERT INTO briefing_item (briefing_id, symbol, company, summary_ko, "
        "sentiment, audio_url, item_date, source) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
        (briefing_id, symbol, company, summary_ko, sentiment, audio_url, item_date, source),
    )
    return cur.lastrowid

def insert_article(cur, item_id, art: dict):
    cur.execute(
        "INSERT INTO article (item_id, title_en, title_ko, url, source_name, url_hash) "
        "VALUES (%s,%s,%s,%s,%s,%s)",
        (item_id, art.get("title_en"), art.get("title_ko"), art.get("url"),
         art.get("source_name"), art.get("url_hash")),
    )

def find_cached_item(cur, symbol, item_date):
    cur.execute(
        "SELECT * FROM briefing_item WHERE symbol=%s AND item_date=%s LIMIT 1",
        (symbol, item_date),
    )
    return cur.fetchone()

def list_briefings(cur, limit=30):
    cur.execute("SELECT * FROM briefing ORDER BY briefing_date DESC LIMIT %s", (limit,))
    return cur.fetchall()

def get_briefing(cur, briefing_id):
    cur.execute("SELECT * FROM briefing WHERE id=%s", (briefing_id,))
    return cur.fetchone()

def get_items_for_briefing(cur, briefing_id):
    cur.execute("SELECT * FROM briefing_item WHERE briefing_id=%s ORDER BY symbol", (briefing_id,))
    return cur.fetchall()

def get_articles_for_item(cur, item_id):
    cur.execute("SELECT * FROM article WHERE item_id=%s", (item_id,))
    return cur.fetchall()
```

- [ ] **Step 5: 테스트 통과 확인**

Run: `.venv\Scripts\pytest tests/test_db.py -v`
Expected: PASS (2 passed)

- [ ] **Step 6: Commit**

```bash
git add app/db.py scripts/init_db.sql tests/test_db.py
git commit -m "feat: add MySQL schema and db access layer"
```

---

## Task 7: 오케스트레이터 (`pipeline/runner.py`)

**Files:**
- Create: `pipeline/runner.py`
- Test: `tests/test_runner.py`

`process_symbol(symbol, company, item_date)` 가 fetch→translate→summarize→tts 를 묶어 dict를 반환한다. 각 단계는 독립적이며, TTS 실패는 `audio_url=None`으로 graceful degradation, 그 외 단계 실패는 예외를 발생시켜 호출 측(batch/route)에서 종목 skip 처리한다.

- [ ] **Step 1: 실패하는 테스트 작성** — `tests/test_runner.py`

```python
from pipeline import runner

def _patch_pipeline(monkeypatch, tts_raises=False):
    monkeypatch.setattr(runner.fetch, "fetch_symbol",
                        lambda symbol, limit=None: [{"title_en": "A", "body_en": "B", "url": "u",
                                                     "source_name": "Reuters", "url_hash": "h"}])
    monkeypatch.setattr(runner.translate, "translate_articles",
                        lambda arts: [dict(a, title_ko="가", body_ko="나") for a in arts])
    monkeypatch.setattr(runner.summarize, "summarize_symbol",
                        lambda company, arts: {"summary_ko": "요약", "sentiment": "positive"})
    if tts_raises:
        def boom(text, key): raise RuntimeError("tts down")
        monkeypatch.setattr(runner.tts, "synthesize_and_upload", boom)
    else:
        monkeypatch.setattr(runner.tts, "synthesize_and_upload",
                            lambda text, key: "http://cdn/a.mp3")

def test_process_symbol_full_success(monkeypatch):
    _patch_pipeline(monkeypatch)
    result = runner.process_symbol("AAPL", "Apple", "2026-05-31")
    assert result["summary_ko"] == "요약"
    assert result["sentiment"] == "positive"
    assert result["audio_url"] == "http://cdn/a.mp3"
    assert len(result["articles"]) == 1
    assert result["articles"][0]["title_ko"] == "가"

def test_process_symbol_tts_failure_is_graceful(monkeypatch):
    _patch_pipeline(monkeypatch, tts_raises=True)
    result = runner.process_symbol("AAPL", "Apple", "2026-05-31")
    assert result["audio_url"] is None      # 음성 없이도 결과 반환
    assert result["summary_ko"] == "요약"
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `.venv\Scripts\pytest tests/test_runner.py -v`
Expected: FAIL

- [ ] **Step 3: `pipeline/runner.py` 구현**

```python
import logging
from pipeline import fetch, translate, summarize, tts

log = logging.getLogger("pipeline")

def process_symbol(symbol: str, company: str, item_date: str) -> dict:
    """한 종목 처리. fetch/translate/summarize 실패는 예외 전파(호출측 skip),
    tts 실패는 audio_url=None 으로 graceful degradation."""
    articles = fetch.fetch_symbol(symbol)
    articles = translate.translate_articles(articles)
    summary = summarize.summarize_symbol(company, articles)

    audio_url = None
    try:
        key = f"audio/{item_date}/{symbol}.mp3"
        audio_url = tts.synthesize_and_upload(summary["summary_ko"], key)
    except Exception as e:  # TTS 실패는 비치명적
        log.warning("TTS 실패 %s: %s", symbol, e)

    return {
        "symbol": symbol,
        "company": company,
        "summary_ko": summary["summary_ko"],
        "sentiment": summary["sentiment"],
        "audio_url": audio_url,
        "articles": articles,
    }
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `.venv\Scripts\pytest tests/test_runner.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add pipeline/runner.py tests/test_runner.py
git commit -m "feat: add pipeline orchestrator with graceful TTS degradation"
```

---

## Task 8: 배치 작업 (`batch_job.py`)

**Files:**
- Create: `batch_job.py`
- Test: `tests/test_batch.py`

`run_batch(conn, item_date)` 가 WATCHLIST 전체를 돌며 `process_symbol`을 호출하고 DB에 저장한다. 한 종목 실패가 전체를 죽이지 않도록 종목 단위 try/except.

- [ ] **Step 1: 실패하는 테스트 작성** — `tests/test_batch.py`

```python
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
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `.venv\Scripts\pytest tests/test_batch.py -v`
Expected: FAIL

- [ ] **Step 3: `batch_job.py` 구현**

```python
import logging
import sys
from datetime import date
from app import config, db
from pipeline import runner

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("batch")

def run_batch(conn, item_date: str) -> tuple[int, int]:
    cur = conn.cursor()
    briefing_id = db.insert_briefing(cur, item_date, market_summary=None, market_audio_url=None)
    ok = failed = 0
    for symbol, company in config.WATCHLIST:
        try:
            result = runner.process_symbol(symbol, company, item_date)
            item_id = db.insert_item(
                cur, briefing_id, symbol, company, result["summary_ko"],
                result["sentiment"], result["audio_url"], item_date, "batch")
            for art in result["articles"]:
                db.insert_article(cur, item_id, art)
            conn.commit()
            ok += 1
            log.info("처리 완료: %s", symbol)
        except Exception as e:
            failed += 1
            log.error("처리 실패 %s: %s", symbol, e)
    return ok, failed

def main():
    item_date = date.today().isoformat()
    conn = db.get_connection()
    try:
        ok, failed = run_batch(conn, item_date)
        log.info("배치 종료: 성공 %d, 실패 %d", ok, failed)
    finally:
        conn.close()

if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `.venv\Scripts\pytest tests/test_batch.py -v`
Expected: PASS (1 passed)

- [ ] **Step 5: Commit**

```bash
git add batch_job.py tests/test_batch.py
git commit -m "feat: add daily batch job with per-symbol error isolation"
```

---

## Task 9: FastAPI 앱 + 온디맨드 검색 (`app/main.py`)

**Files:**
- Create: `app/main.py`, `app/templates/list.html`, `app/templates/detail.html`, `app/static/style.css`
- Test: `tests/test_api.py`

라우트: `GET /`(브리핑 목록), `GET /briefing/{id}`(상세), `POST /search`(온디맨드). 검색은 캐시 우선: 오늘자 항목 있으면 즉시 반환, 없으면 `process_symbol` 실행 후 저장. DB 연결은 의존성 주입(`get_conn`)으로 분리해 테스트에서 override.

- [ ] **Step 1: 템플릿 작성** — `app/templates/list.html`

```html
<!doctype html><html lang="ko"><head><meta charset="utf-8">
<title>증시 브리핑</title><link rel="stylesheet" href="/static/style.css"></head>
<body>
<h1>📈 해외 증시 브리핑</h1>
<form action="/search" method="post">
  <input name="symbol" placeholder="종목 심볼 (예: AAPL)" required>
  <button type="submit">검색</button>
</form>
<ul>
{% for b in briefings %}
  <li><a href="/briefing/{{ b.id }}">{{ b.briefing_date }} 브리핑</a></li>
{% endfor %}
</ul>
<footer>※ 본 서비스는 정보 제공용이며 투자 조언이 아닙니다.</footer>
</body></html>
```

- [ ] **Step 2: 템플릿 작성** — `app/templates/detail.html`

```html
<!doctype html><html lang="ko"><head><meta charset="utf-8">
<title>{{ briefing.briefing_date }} 브리핑</title><link rel="stylesheet" href="/static/style.css"></head>
<body>
<a href="/">← 목록</a>
<h1>{{ briefing.briefing_date }} 증시 브리핑</h1>
{% for item in items %}
  <section>
    <h2>{{ item.company }} ({{ item.symbol }}) <span class="s-{{ item.sentiment }}">{{ item.sentiment }}</span></h2>
    <p>{{ item.summary_ko }}</p>
    {% if item.audio_url %}<audio controls src="{{ item.audio_url }}"></audio>{% endif %}
    <details><summary>출처</summary><ul>
      {% for a in item.articles %}<li><a href="{{ a.url }}" target="_blank">{{ a.title_ko or a.title_en }}</a> ({{ a.source_name }})</li>{% endfor %}
    </ul></details>
  </section>
{% endfor %}
<footer>※ 본 서비스는 정보 제공용이며 투자 조언이 아닙니다.</footer>
</body></html>
```

- [ ] **Step 3: 스타일 작성** — `app/static/style.css`

```css
body { font-family: system-ui, sans-serif; max-width: 760px; margin: 2rem auto; padding: 0 1rem; }
section { border: 1px solid #ddd; border-radius: 8px; padding: 1rem; margin: 1rem 0; }
.s-positive { color: #0a0; } .s-negative { color: #c00; } .s-neutral { color: #888; }
footer { margin-top: 2rem; color: #888; font-size: .85rem; }
```

- [ ] **Step 4: 실패하는 테스트 작성** — `tests/test_api.py`

```python
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
```

- [ ] **Step 5: 테스트 실패 확인**

Run: `.venv\Scripts\pytest tests/test_api.py -v`
Expected: FAIL

- [ ] **Step 6: `app/main.py` 구현**

```python
from datetime import date
from fastapi import FastAPI, Form, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app import db, config
from pipeline import runner

app = FastAPI(title="증시 브리핑")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

def get_conn():
    conn = db.get_connection()
    try:
        yield conn
    finally:
        conn.close()

# WATCHLIST 심볼 -> 회사명 매핑 (온디맨드 검증/회사명 조회용)
_COMPANY = {sym: name for sym, name in config.WATCHLIST}

@app.get("/", response_class=HTMLResponse)
def index(request: Request, conn=Depends(get_conn)):
    cur = conn.cursor()
    briefings = db.list_briefings(cur)
    return templates.TemplateResponse("list.html", {"request": request, "briefings": briefings})

@app.get("/briefing/{briefing_id}", response_class=HTMLResponse)
def briefing_detail(briefing_id: int, request: Request, conn=Depends(get_conn)):
    cur = conn.cursor()
    briefing = db.get_briefing(cur, briefing_id)
    if not briefing:
        raise HTTPException(404, "브리핑을 찾을 수 없습니다")
    items = db.get_items_for_briefing(cur, briefing_id)
    for item in items:
        item["articles"] = db.get_articles_for_item(cur, item["id"])
    return templates.TemplateResponse("detail.html",
                                      {"request": request, "briefing": briefing, "items": items})

@app.post("/search", response_class=HTMLResponse)
def search(request: Request, symbol: str = Form(...), conn=Depends(get_conn)):
    symbol = symbol.strip().upper()
    if symbol not in _COMPANY:
        raise HTTPException(400, f"지원하지 않는 종목입니다. 가능: {', '.join(_COMPANY)}")
    today = date.today().isoformat()
    cur = conn.cursor()

    item = db.find_cached_item(cur, symbol, today)
    if item:
        item = dict(item)
        item["articles"] = db.get_articles_for_item(cur, item["id"])
    else:
        result = runner.process_symbol(symbol, _COMPANY[symbol], today)
        item_id = db.insert_item(cur, None, symbol, _COMPANY[symbol], result["summary_ko"],
                                 result["sentiment"], result["audio_url"], today, "ondemand")
        for art in result["articles"]:
            db.insert_article(cur, item_id, art)
        conn.commit()
        item = {**result, "id": item_id, "articles": result["articles"]}

    briefing = {"briefing_date": f"{today} (검색: {symbol})"}
    return templates.TemplateResponse("detail.html",
                                      {"request": request, "briefing": briefing, "items": [item]})
```

- [ ] **Step 7: 테스트 통과 확인**

Run: `.venv\Scripts\pytest tests/test_api.py -v`
Expected: PASS (2 passed)

- [ ] **Step 8: 전체 테스트 실행**

Run: `.venv\Scripts\pytest -v`
Expected: 모든 테스트 PASS

- [ ] **Step 9: Commit**

```bash
git add app/main.py app/templates/ app/static/ tests/test_api.py
git commit -m "feat: add FastAPI routes, templates, and on-demand search"
```

---

## Task 10: 배포 · cron · 문서 · 통합 검증

**Files:**
- Create: `README.md`

- [ ] **Step 1: `README.md` 작성** (발급/배포 가이드)

다음 내용을 포함: 프로젝트 개요, 아키텍처 다이어그램(스펙 참조), 사전 준비(NCP VM·Cloud DB·Object Storage 생성, CLOVA Studio/Papago/Voice 신청, 뉴스 API 키), 설치(`pip install -r requirements.txt`), DB 초기화(`mysql < scripts/init_db.sql`), `.env` 설정, 실행(`uvicorn app.main:app --host 0.0.0.0 --port 8000`), 배치 수동 실행(`python batch_job.py`), cron 등록 예시, 테스트(`pytest`).

- [ ] **Step 2: cron 등록 (VM에서)**

```bash
# crontab -e 에 추가 — 매일 07:00 KST 배치 실행
0 7 * * * cd /home/ubuntu/proj && /home/ubuntu/proj/.venv/bin/python batch_job.py >> logs/batch_$(date +\%Y\%m\%d).log 2>&1
```

- [ ] **Step 3: DB 초기화 (Cloud DB)**

Run: `mysql -h $DB_HOST -u $DB_USER -p < scripts/init_db.sql`
Expected: 3개 테이블 생성, 에러 없음.

- [ ] **Step 4: 통합 검증 — 배치 1회 실제 실행**

Run: `python batch_job.py`
Expected (증거 3종):
1. 로그에 종목별 "처리 완료" 출력, "배치 종료: 성공 N, 실패 M"
2. DB: `SELECT COUNT(*) FROM briefing_item WHERE item_date=CURDATE();` ≥ 1
3. Object Storage에 mp3 업로드됨, `audio_url` 브라우저에서 재생 가능

- [ ] **Step 5: 통합 검증 — 웹 흐름**

Run: 브라우저로 `http://<VM_IP>:8000/` 접속
Expected: 목록 → 상세에서 요약·음성 재생·출처 링크 표시. `/search`로 종목 검색 동작(캐시 히트/미스 모두).

- [ ] **Step 6: 최종 Commit**

```bash
git add README.md
git commit -m "docs: add README with setup, deployment, and cron guide"
```

---

## 자체 점검 결과

- **스펙 커버리지**: ① 정기 브리핑(Task 8) ② 온디맨드 검색·캐시(Task 9) ③ 수집(2)/번역(3)/요약+감성(4)/TTS+업로드(5) ④ 스키마 3테이블(6) ⑤ 에러 처리·부분 성공(7,8) ⑥ 출처 표기(템플릿, 9) ⑦ 테스트(각 Task) ⑧ 배포·cron(10) — 모든 스펙 섹션이 작업에 매핑됨.
- **Placeholder**: 모든 코드 단계에 실제 코드 포함, "TBD/적절히 처리" 없음.
- **타입 일관성**: `process_symbol` 반환 키(`symbol/company/summary_ko/sentiment/audio_url/articles`)가 Task 7 정의와 Task 8·9 사용처에서 일치. `find_cached_item`/`insert_item` 시그니처가 Task 6 정의와 9 사용처 일치.
- **주의**: NCP API 엔드포인트/헤더는 1일차 콘솔 확인 후 각 모듈 상수만 교체(상단 "참고" 섹션). 외부 호출부가 함수로 격리되어 영향 최소.
