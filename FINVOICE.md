# FinVoice — 시스템 산출물 문서

해외 영어 금융뉴스를 수집·번역·요약·음성화하여 "오늘의 증시 브리핑"을 웹으로 제공하는 NCP 기반 서비스.

---

## 목차

1. [서비스 개요](#1-서비스-개요)
2. [전체 아키텍처](#2-전체-아키텍처)
3. [파이프라인 상세 흐름](#3-파이프라인-상세-흐름)
4. [NCP 서비스 구성](#4-ncp-서비스-구성)
5. [디렉터리 구조](#5-디렉터리-구조)
6. [데이터베이스 스키마](#6-데이터베이스-스키마)
7. [API 엔드포인트](#7-api-엔드포인트)
8. [환경변수 목록](#8-환경변수-목록)
9. [실행 방법](#9-실행-방법)
10. [설계 원칙 및 결정 사항](#10-설계-원칙-및-결정-사항)

---

## 1. 서비스 개요

| 항목 | 내용 |
|------|------|
| 서비스명 | FinVoice |
| 목적 | 해외 금융뉴스 자동 수집 → 한국어 요약 → 음성 브리핑 제공 |
| 대상 사용자 | 로그인 없이 접속하는 익명 사용자 (개인화 없음) |
| 핵심 기능 | ① 매일 자동 배치 브리핑 ② 종목 온디맨드 검색 ③ 음성 재생 |
| 관심종목 | AAPL, TSLA, NVDA, MSFT, AMZN, GOOGL (고정, `app/config.py`) |
| 인프라 | NCP (Server + Cloud DB + Object Storage + AI 서비스군) |

---

## 2. 전체 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                        사용자 (브라우저)                          │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTP
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│               NCP Server (Ubuntu VM)                            │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  FastAPI + uvicorn  (app/main.py)                       │   │
│  │                                                         │   │
│  │  GET  /              목록 페이지 (list.html)             │   │
│  │  GET  /briefing/{id} 상세 페이지 (detail.html)           │   │
│  │  POST /search        온디맨드 검색 → pipeline.runner     │   │
│  │  GET  /api/quotes    실시간 주가 (Finnhub, 60s 캐시)     │   │
│  └──────────────────────────┬──────────────────────────────┘   │
│                             │                                   │
│  ┌──────────────────────────▼──────────────────────────────┐   │
│  │  pipeline/runner.py  (process_symbol)                   │   │
│  │                                                         │   │
│  │  fetch → translate → summarize → tts                   │   │
│  └──┬────────────┬──────────────┬──────────────┬──────────┘   │
│     │            │              │              │               │
│  crontab                                                        │
│  batch_job.py ──┘                                              │
│                                                                 │
└─────┬────────────┬──────────────┬──────────────┬───────────────┘
      │            │              │              │
      ▼            ▼              ▼              ▼
┌──────────┐ ┌──────────┐ ┌──────────────┐ ┌──────────────────┐
│ Finnhub  │ │  NCP     │ │  NCP CLOVA   │ │  NCP Object      │
│ News API │ │ Papago   │ │  Studio      │ │  Storage (S3)    │
│ (외부)   │ │ 번역     │ │  요약+감성   │ │  mp3 저장        │
└──────────┘ └──────────┘ └──────┬───────┘ └────────┬─────────┘
                                  │                  │
                    ┌─────────────▼──────────────────▼─────────┐
                    │  NCP CLOVA Voice  (TTS → mp3)             │
                    └───────────────────────────────────────────┘
                                  │
                    ┌─────────────▼──────────────────────────────┐
                    │  NCP Cloud DB for MySQL                     │
                    │  briefing / briefing_item / article         │
                    └────────────────────────────────────────────┘
```

### 두 진입점, 하나의 파이프라인

```
배치(cron)          온디맨드(웹)
     │                   │
     └────────┬───────────┘
              ▼
    pipeline/runner.process_symbol()
              │
    ┌─────────▼──────────┐
    │  fetch_symbol()    │  Finnhub /company-news
    ├────────────────────┤
    │  translate_articles│  NCP Papago NMT
    ├────────────────────┤
    │  summarize_symbol()│  NCP CLOVA Studio (HyperCLOVA X)
    ├────────────────────┤
    │  synthesize_and_   │  NCP CLOVA Voice → Object Storage
    │  upload()          │  (실패 시 audio_url=None, 비치명적)
    └────────────────────┘
```

---

## 3. 파이프라인 상세 흐름

### 3-1. Fetch (`pipeline/fetch.py`)
- Finnhub `/company-news` API로 종목별 최근 기사 수집 (`ARTICLES_PER_SYMBOL = 5`)
- `/quote` API로 실시간 주가(현재가·등락·등락률) 조회
- `NEWS_API_KEY` 환경변수 사용

### 3-2. Translate (`pipeline/translate.py`)
- NCP Papago NMT로 영어 제목·본문 발췌 → 한국어 변환
- 엔드포인트: `https://papago.apigw.ntruss.com/nmt/v1/translation`
- 번역 실패 시 영어 원문으로 진행 (부분 성공 허용)
- 인증: `NCP_APIGW_ACCESS_KEY` + `NCP_APIGW_SECRET_KEY` (HMAC-SHA256)

### 3-3. Summarize (`pipeline/summarize.py`)
- NCP CLOVA Studio (HyperCLOVA X)로 여러 기사를 종목별 한국어 요약문 생성
- 감성 라벨 산출: `positive` / `neutral` / `negative`
- 인증: `CLOVA_STUDIO_API_KEY` (Bearer)

### 3-4. TTS + 업로드 (`pipeline/tts.py`)
- NCP CLOVA Voice로 한국어 요약문 → mp3 합성
- NCP Object Storage(S3 호환)에 `audio/{date}/{symbol}.mp3` 키로 업로드
- 공개 URL 반환 → DB `audio_url` 컬럼에 저장
- TTS 실패는 비치명적 — 텍스트 요약만 표시

### 3-5. 캐시 정책
- 같은 날·같은 종목이 DB에 있으면 파이프라인 재실행 없이 즉시 반환
- `/api/quotes` 주가는 60초 인메모리 캐시

---

## 4. NCP 서비스 구성

| 서비스 | 역할 | 인증 방식 | 환경변수 |
|--------|------|-----------|----------|
| **Papago NMT** | 영→한 번역 | APIGW HMAC | `NCP_APIGW_ACCESS_KEY`, `NCP_APIGW_SECRET_KEY` |
| **CLOVA Studio** | 요약 + 감성 분석 | Bearer Token | `CLOVA_STUDIO_API_KEY` |
| **CLOVA Voice** | 한국어 TTS → mp3 | APIGW HMAC | `NCP_APIGW_VOICE_ACCESS_KEY` (없으면 공용 키 폴백) |
| **Object Storage** | mp3 저장 · 공개 URL | S3 AccessKey/Secret | `NCP_S3_ACCESS_KEY`, `NCP_S3_SECRET_KEY`, `NCP_S3_BUCKET`, `NCP_S3_ENDPOINT` |
| **Cloud DB MySQL** | 브리핑 데이터 저장·조회 | 사용자/비밀번호 | `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` |
| **Server (VM)** | uvicorn 웹앱 + cron 배치 | SSH 키 | — |

외부 서비스:

| 서비스 | 역할 | 환경변수 |
|--------|------|----------|
| **Finnhub** | 영어 금융뉴스 · 실시간 주가 | `NEWS_API_KEY` |
| **Clearbit Logo** | 종목 로고 이미지 | (무인증, 프론트엔드 직접 호출) |

---

## 5. 디렉터리 구조

```
proj/
├── app/
│   ├── main.py          # FastAPI 앱, 라우터, /api/quotes, 주가 캐시
│   ├── config.py        # WATCHLIST, LOGO_DOMAINS, get_env()
│   ├── db.py            # PyMySQL 연결, CRUD 함수
│   ├── templates/
│   │   ├── list.html    # 목록 페이지 (티커바 + 검색 폼 + 히스토리)
│   │   └── detail.html  # 상세/검색결과 페이지 (종목 카드 + 오디오 플레이어)
│   └── static/
│       └── style.css    # 다크 테마 (Toss Invest 스타일)
│
├── pipeline/
│   ├── runner.py        # process_symbol() 오케스트레이터
│   ├── fetch.py         # Finnhub 뉴스·주가 수집
│   ├── translate.py     # Papago 번역
│   ├── summarize.py     # CLOVA Studio 요약·감성
│   └── tts.py           # CLOVA Voice TTS + Object Storage 업로드
│
├── tests/               # pytest 단위 테스트 (외부 API 전부 mock)
├── scripts/
│   ├── init_db.sql      # 테이블 생성 DDL
│   └── apply_schema.py  # 원격 DB에 스키마 적용 스크립트
│
├── batch_job.py         # cron 진입점 (run_batch → process_symbol 반복)
├── requirements.txt
├── .env.example         # 환경변수 키 목록 (값 없음, 커밋 가능)
├── CLAUDE.md            # Claude 작업 안내서
├── SERVER_RUNBOOK.md    # 서버 배포·운영 절차
└── FINVOICE.md          # 이 문서
```

---

## 6. 데이터베이스 스키마

```
briefing
├── id              BIGINT PK AUTO_INCREMENT
├── briefing_date   DATE UNIQUE          -- 날짜별 1행
├── market_summary  TEXT NULL
├── market_audio_url VARCHAR(500) NULL
└── created_at      DATETIME

briefing_item
├── id              BIGINT PK AUTO_INCREMENT
├── briefing_id     BIGINT FK → briefing.id (NULL 허용: 온디맨드)
├── symbol          VARCHAR(16)          -- AAPL 등
├── company         VARCHAR(100)
├── summary_ko      TEXT                 -- 한국어 요약문
├── sentiment       ENUM(positive/neutral/negative)
├── audio_url       VARCHAR(500) NULL    -- Object Storage mp3 URL
├── item_date       DATE
├── source          ENUM(batch/ondemand)
└── created_at      DATETIME
    INDEX: (symbol, item_date)

article
├── id              BIGINT PK AUTO_INCREMENT
├── item_id         BIGINT FK → briefing_item.id
├── title_en        VARCHAR(500)
├── title_ko        VARCHAR(500)
├── url             VARCHAR(1000)
├── source_name     VARCHAR(100)
├── published_at    DATETIME NULL
└── url_hash        CHAR(64)
    INDEX: (url_hash)
```

**캐시 조회 로직**: `briefing_item`에서 `(symbol, item_date)` 조합이 존재하면 파이프라인 재실행 없이 반환.

---

## 7. API 엔드포인트

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `GET` | `/` | 브리핑 히스토리 목록 + 검색 폼 |
| `GET` | `/briefing/{id}` | 특정 날짜 브리핑 상세 (종목 카드 목록) |
| `POST` | `/search` | 종목 심볼 검색 → 캐시 히트 즉시 반환 / 미스 시 파이프라인 실행 |
| `GET` | `/api/quotes` | 관심종목 전체 실시간 주가 JSON (60초 서버 캐시) |
| `GET` | `/static/*` | CSS 등 정적 파일 |

**오류 처리**: 400(미지원 종목), 404(브리핑 없음), 500(파이프라인 실패) 모두 사용자 친화 한국어 메시지로 표시. 스택트레이스 노출 없음.

---

## 8. 환경변수 목록

`.env` 파일에만 저장 (git 제외). `.env.example`에 키 이름만 기재.

| 변수명 | 설명 |
|--------|------|
| `NEWS_API_KEY` | Finnhub API 키 |
| `NCP_APIGW_ACCESS_KEY` | NCP API Gateway 공용 Access Key |
| `NCP_APIGW_SECRET_KEY` | NCP API Gateway 공용 Secret Key |
| `CLOVA_STUDIO_API_KEY` | CLOVA Studio (HyperCLOVA X) Bearer 토큰 |
| `CLOVA_STUDIO_REQUEST_ID` | CLOVA Studio 요청 ID |
| `NCP_APIGW_VOICE_ACCESS_KEY` | CLOVA Voice 전용 키 (없으면 공용 키 폴백) |
| `NCP_S3_ACCESS_KEY` | Object Storage Access Key |
| `NCP_S3_SECRET_KEY` | Object Storage Secret Key |
| `NCP_S3_BUCKET` | 버킷 이름 |
| `NCP_S3_ENDPOINT` | Object Storage 엔드포인트 URL |
| `DB_HOST` | Cloud DB 호스트 |
| `DB_PORT` | Cloud DB 포트 (기본 3306) |
| `DB_USER` | DB 사용자 |
| `DB_PASSWORD` | DB 비밀번호 |
| `DB_NAME` | DB 이름 |

---

## 9. 실행 방법

```bash
# 1. 의존성 설치
pip install -r requirements.txt

# 2. 환경변수 준비
cp .env.example .env   # 값 채우기

# 3. DB 스키마 적용 (최초 1회)
python scripts/apply_schema.py
# 또는 직접: mysql -h <host> -u <user> -p <db> < scripts/init_db.sql

# 4. 웹 서버 실행
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 5. 배치 1회 수동 실행
python batch_job.py

# 6. 테스트 (외부 API 전부 mock)
pytest -q
```

**cron 등록 예시** (서버):
```cron
0 7 * * 1-5 cd /home/ubuntu/finvoice && python batch_job.py >> logs/batch.log 2>&1
```

---

## 10. 설계 원칙 및 결정 사항

### 하나의 파이프라인, 두 진입점
배치(`batch_job.py`)와 온디맨드(`POST /search`) 모두 `pipeline/runner.process_symbol()`을 호출한다. 로직 중복 없음.

### 부분 성공 허용
한 종목 처리 실패가 전체 배치를 중단하지 않는다. `batch_job.py`는 종목별로 try/except 후 `ok/failed` 카운트를 반환.

### TTS 비치명적 처리
CLOVA Voice 또는 Object Storage 실패 시 `audio_url = None`으로 저장하고 텍스트 요약만 표시. 음성이 없어도 서비스는 동작.

### 번역 실패 폴백
Papago 번역 실패 시 영어 원문을 그대로 요약에 넘긴다.

### 429 재시도 없음
API 한도 초과(429) 응답은 재시도 없이 skip + 로그만 남긴다. 무한 루프 방지.

### 캐시 우선
같은 날 같은 종목은 DB 캐시를 반환한다. 동일 날짜 중복 처리 없음.

### 비밀값 하드코딩 금지
API 키, DB 자격증명, SSH 정보는 소스·문서·커밋 어디에도 없음. 모두 `.env`(git 제외) 또는 서버 환경변수로만 관리.

### 프론트엔드 설계
- 다크 테마 (`#0d0e10` 배경, `#3182f6` 액센트) — Toss Invest 스타일 참조
- 한국 주가 관행: 상승 빨강(`#f04452`), 하락 파랑(`#4c8ef7`)
- 감성 색상: positive `#00c471` / negative `#f04452` / neutral `#8c919e`
- 외부 링크 전체 `rel="noopener noreferrer"` 적용
- 푸터 면책 문구 고정: "본 서비스는 정보 제공용이며 투자 조언이 아닙니다"
