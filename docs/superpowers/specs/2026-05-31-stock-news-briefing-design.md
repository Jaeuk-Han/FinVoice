# 해외 금융뉴스 번역·요약·음성 브리핑 서비스 — 설계 문서

- **작성일**: 2026-05-31
- **목적**: 수업 평가용 포트폴리오 (1주일 일정)
- **플랫폼**: 네이버 클라우드 플랫폼(NCP) — 필수
- **한 줄 정의**: 해외 영어 금융뉴스를 수집해 Papago로 번역하고, CLOVA Studio로 요약한 뒤, CLOVA Voice로 음성 브리핑을 제공하는 웹 서비스.

---

## 1. 목표와 범위

### 핵심 가치
NCP의 AI 서비스 3종(Papago 번역 + CLOVA Studio 요약 + CLOVA Voice TTS)을 하나의 완결된 파이프라인으로 통합하고, VM·Cloud DB·Object Storage·배치 자동화로 클라우드 인프라 역량을 함께 보여준다.

### 제공 기능
- **정기 브리핑 (배치)**: 매일 정해진 시각에 시장 전반 + 고정 관심종목 뉴스를 자동 수집·번역·요약·음성화하여 "오늘의 증시 브리핑" 생성.
- **온디맨드 검색**: 사용자가 고정 관심종목 중 하나를 검색하면, 캐시가 있으면 즉시 반환하고 없으면 같은 파이프라인을 즉석 실행.
- **2단 구성**: ① 시장 전반 요약(B) + ② 종목별 요약(A, 고정 5~8개).

### 비범위 (YAGNI)
- 로그인 / 회원가입 / 사용자별 개인화 없음 (모두 같은 브리핑을 봄).
- 사용자가 임의 티커를 추가하는 기능 없음 (관심종목은 설정파일로 고정).
- OCR 기능은 사용하지 않음 (Papago + CLOVA Studio + CLOVA Voice만 사용).

### 확정된 의사결정
| 항목 | 결정 |
|------|------|
| 사용 흐름 | 정기 브리핑(B) + 온디맨드(A) 혼합 = "하나의 파이프라인 + 두 진입점" |
| 종목 범위 | 시장 전반 + 고정 관심종목 5~8개 |
| 뉴스 소스 | 영어 금융뉴스 API 단독 (Finnhub 등 무료 티어) |
| 요약 LLM | NCP CLOVA Studio (HyperCLOVA X) |
| 기술 스택 | Python / FastAPI |
| 프론트엔드 | 최소 UI(Jinja2 템플릿), 로그인 없음 |
| 배치 방식 | FastAPI 웹 + 별도 배치 스크립트(system cron) — 공용 파이프라인 모듈 공유 |

---

## 2. 아키텍처

```
┌─────────────────────── NCP ───────────────────────┐
│  [Server (VM) - Ubuntu]                             │
│   ├─ FastAPI 웹앱 (uvicorn)                          │
│   │    · GET  /              브리핑 목록             │
│   │    · GET  /briefing/{id} 상세 + 음성 재생        │
│   │    · POST /search        온디맨드 종목 검색       │
│   └─ batch_job.py (crontab, 매일 1회)               │
│        수집→번역→요약→TTS→저장                       │
│   두 진입점이 공용 모듈 pipeline/ 을 호출            │
│         │                  │                        │
│         ▼                  ▼                        │
│  [Cloud DB for MySQL]   [Object Storage]            │
│   기사/번역/요약/종목     음성 mp3 파일               │
│                                                     │
│  [NCP AI APIs] Papago / CLOVA Studio / CLOVA Voice  │
└─────────────────────────────────────────────────────┘
        ▲
        │ (외부) 영어 금융뉴스 API (Finnhub 등)
```

### 디렉토리 구조
```
proj/
├─ app/
│  ├─ main.py            # FastAPI 앱, 라우트
│  ├─ config.py          # 환경변수/키 로딩(.env), 관심종목 목록
│  ├─ templates/         # Jinja2 (목록, 상세)
│  ├─ static/            # css, js
│  └─ db.py              # MySQL 연결/쿼리
├─ pipeline/             # 공용 파이프라인 (핵심)
│  ├─ fetch.py           # 뉴스 API 수집
│  ├─ translate.py       # Papago 번역
│  ├─ summarize.py       # CLOVA Studio 요약
│  ├─ tts.py             # CLOVA Voice + Object Storage 업로드
│  └─ runner.py          # 단계 오케스트레이터
├─ batch_job.py          # cron 진입점 → pipeline.runner 호출
├─ scripts/init_db.sql   # 테이블 생성
├─ tests/
├─ requirements.txt
├─ .env.example
└─ README.md
```

**핵심 설계 포인트**: 번역·요약·TTS 로직은 전부 `pipeline/`에 모으고, `batch_job.py`(자동)와 `/search` 엔드포인트(온디맨드)가 같은 `runner`를 호출한다. 로직 중복 없이 "하나의 파이프라인 + 두 진입점"을 구현한다.

---

## 3. 데이터 흐름

### A. 정기 브리핑 (배치, 매일 cron — 예: 07:00)
1. **fetch.py** — 시장 전반 뉴스 N건 + 고정 관심종목별 뉴스 각 M건 수집. 영어 금융뉴스 API를 종목 심볼로 조회. URL/제목 해시로 중복 제거, 이미 처리한 기사 skip.
2. **translate.py** — 영어 원문(제목 + 요약 대상 텍스트) → 한국어 (Papago).
3. **summarize.py** (CLOVA Studio) — 종목별로 여러 기사를 묶어 "핵심 이슈 3~5줄" 요약. 시장 전반은 주요 기사들을 묶어 "오늘의 시장 요약". 감성(positive/neutral/negative) 라벨 1개를 프롬프트로 함께 산출.
4. **tts.py** (CLOVA Voice) — 요약문 → mp3 생성 → Object Storage 업로드 → URL 획득.
5. **db 저장** — `briefing`(날짜별 1건) + 하위 `briefing_item`(종목별) + `article`(출처).

### B. 온디맨드 검색 (사용자 요청 시)
```
POST /search {symbol: "AAPL"}
  · DB에 오늘자 해당 종목 요약이 있으면 즉시 반환 (캐시)
  · 없으면 → pipeline.runner 를 그 종목 1개에 대해 즉석 실행
            (fetch→translate→summarize→tts) → DB 저장 후 반환
```

### 핵심 설계 결정
- **요약 단위**: 기사 1건씩이 아니라 종목별로 여러 기사를 묶어 한 번에 요약 → 호출 수 절감, 요약 품질 향상.
- **TTS 시점**: 요약 완료 후 1회만 생성해 Object Storage에 저장, 재생은 저장 URL 스트리밍.
- **캐싱**: 같은 날·같은 종목은 재처리하지 않음 → API 비용/할당량 보호.
- **출처 보존**: 각 요약에 원본 기사 링크를 함께 저장하여 화면에 "출처" 표기 → 신뢰성·할루시네이션 방지.

---

## 4. 데이터 모델 (Cloud DB for MySQL)

```sql
-- 일자별 브리핑 (하루 1건)
CREATE TABLE briefing (
    id          BIGINT AUTO_INCREMENT PRIMARY KEY,
    briefing_date DATE NOT NULL,
    market_summary TEXT,            -- 시장 전반 요약 (B)
    market_audio_url VARCHAR(500),  -- 시장 요약 음성
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_date (briefing_date)
);

-- 종목별 요약 항목 (관심종목 A + 온디맨드 결과)
CREATE TABLE briefing_item (
    id          BIGINT AUTO_INCREMENT PRIMARY KEY,
    briefing_id BIGINT,             -- 정기 브리핑 소속 (온디맨드는 NULL 가능)
    symbol      VARCHAR(16) NOT NULL,
    company     VARCHAR(100),
    summary_ko  TEXT NOT NULL,          -- 한국어 요약 (CLOVA Studio)
    sentiment   ENUM('positive','neutral','negative') DEFAULT 'neutral',
    audio_url   VARCHAR(500),           -- 종목 요약 음성 (Object Storage)
    item_date   DATE NOT NULL,
    source      ENUM('batch','ondemand') DEFAULT 'batch',
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (briefing_id) REFERENCES briefing(id),
    KEY idx_symbol_date (symbol, item_date)  -- 캐시 조회용
);

-- 요약 근거가 된 원본 기사 (출처 표기·할루시네이션 방지)
CREATE TABLE article (
    id          BIGINT AUTO_INCREMENT PRIMARY KEY,
    item_id     BIGINT NOT NULL,
    title_en    VARCHAR(500),
    title_ko    VARCHAR(500),           -- Papago 번역 제목
    url         VARCHAR(1000),
    source_name VARCHAR(100),           -- Reuters, CNBC ...
    published_at DATETIME,
    url_hash    CHAR(64),               -- 중복 수집 방지 (URL 해시)
    FOREIGN KEY (item_id) REFERENCES briefing_item(id),
    KEY idx_url_hash (url_hash)
);
```

**설계 의도**
- `briefing(1) → briefing_item(N) → article(N)` 계층.
- 캐싱: `idx_symbol_date`로 "오늘 이 종목 처리했나?" 즉시 조회.
- 중복 수집 방지: `article.url_hash`.
- 온디맨드: `briefing_id = NULL`, `source='ondemand'`로 구분, 같은 테이블 재사용.
- 관심종목 목록(고정 5~8개)은 DB 대신 설정파일(config)에 둔다 (YAGNI).

---

## 5. 외부 API 연동 & 에러 처리

### 연동 API
| 단계 | API | 인증 | 핵심 주의점 |
|------|-----|------|------------|
| 수집 | 영어 금융뉴스 API (Finnhub 등) | API 키 | 무료 티어 호출 한도(분/일) → 종목 수·호출 간격 조절 |
| 번역 | NCP Papago | NCP API 키 헤더 | 요청당 글자 수 제한 → 발췌/문단 단위 번역 |
| 요약 | NCP CLOVA Studio | NCP API 키 + 요청ID | 토큰 한도, 응답 지연 → 타임아웃·재시도 |
| 음성 | NCP CLOVA Voice | NCP API 키 헤더 | 입력 길이 제한, mp3 바이너리 반환 |

### 에러 처리 원칙 — "한 단계 실패가 전체 배치를 죽이지 않게"
```
for symbol in watchlist:
    try:
        articles = fetch(symbol)          # 실패 → 이 종목 skip, 로그
        translated = translate(articles)  # 실패 → 원문(영어)으로라도 진행 + 플래그
        summary = summarize(translated)   # 실패 → 이 종목 skip, 로그
        audio = tts(summary)              # 실패 → audio_url=NULL, 텍스트만 제공
        save(...)
    except Exception as e:
        log.error(symbol, e); continue    # 다음 종목 계속
```
- **부분 성공 허용**: 한 종목/단계가 실패해도 나머지 브리핑은 정상 생성.
- **TTS 실패는 비치명적**: 음성 없으면 텍스트 요약만 표시 (graceful degradation).
- **재시도**: 네트워크/일시 오류는 짧게 2회 재시도(지수 백오프). 한도 초과(429)는 재시도 없이 skip+로그.
- **레이트리밋 보호**: 종목 간 짧은 sleep, 캐시 우선 조회로 불필요한 호출 차단.
- **키 관리**: 모든 키는 `.env`(git 제외), `.env.example`만 커밋. README에 발급 방법 명시.
- **로깅**: 배치는 `logs/batch_YYYYMMDD.log`에 단계별 성공/실패 기록.

### 할루시네이션 방어
- 요약 프롬프트에 "제공된 기사 내용에서만 작성, 추측 금지" 명시.
- 화면에 항상 출처 링크 노출.
- "투자 조언 아님" 면책 문구를 푸터에 고정.

---

## 6. 테스트 전략

```
tests/
├─ test_pipeline_unit.py   # 각 단계 단위 테스트 (외부 API는 mock)
│    · fetch: 가짜 JSON → 파싱·중복제거 검증
│    · translate/summarize/tts: 호출부 mock → 입출력 형태 검증
│    · 에러 주입: 한 종목 실패 시 나머지 진행(부분 성공) 검증
├─ test_db.py              # 저장/캐시 조회 쿼리 검증
└─ test_api.py             # FastAPI 라우트(TestClient) — 200 응답, 캐시 분기
```
- 외부 API는 전부 mock (비용·한도·불안정).
- 통합 확인은 1회 수동: 실제 키로 배치 1번 실행해 end-to-end 검증 (증거: 로그 + DB row + 재생되는 mp3).

---

## 7. 1주일 일정 (검증 게이트 포함)

| 일자 | 작업 | 완료 기준(증거) |
|------|------|----------------|
| 1일차 | NCP VM·Cloud DB·Object Storage 생성, CLOVA Studio·Papago·Voice 신청, 뉴스 API 키 발급, FastAPI 뼈대 | 빈 앱 VM 기동, DB 접속 OK |
| 2일차 | `fetch` + `translate` 구현·테스트 | 영어 수집→한국어 번역 결과 확인 |
| 3일차 | `summarize`(CLOVA Studio) + `runner` 연결 | 종목별 한국어 요약 생성 |
| 4일차 | `tts` + Object Storage 업로드, DB 저장 | mp3 생성·재생, 브리핑 1건 저장 |
| 5일차 | `batch_job` + crontab, 온디맨드 `/search` | cron 자동 실행 1회 성공, 검색 동작 |
| 6일차 | Jinja2 UI(목록·상세·음성재생·출처), VM 배포 | 브라우저에서 전체 흐름 시연 |
| 7일차 | 테스트 정리, README·아키텍처 다이어그램, 데모 리허설 | 테스트 green, 문서 완성 |

**최종 산출물**: 동작하는 웹앱 + GitHub 리포(README·아키텍처도·`.env.example`·`init_db.sql`) + 데모 시나리오. 평가 포인트(NCP AI 3종 + LLM + VM/DB/Storage + 배치 자동화)가 한눈에 드러남.
