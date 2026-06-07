# FinVoice — 해외 금융뉴스 음성 브리핑 서비스

해외 영어 금융뉴스를 자동 수집해 **한국어 번역 → 요약 → 음성**으로 변환하여 "오늘의 증시 브리핑"을 웹으로 제공하는 NCP 기반 서비스.

> ⚠️ 본 서비스는 정보 제공 목적이며 투자 조언이 아닙니다.

- **GitHub**: https://github.com/Jaeuk-Han/FinVoice
- **개발 기간**: 1주일 (수업 평가용 포트폴리오)
- **스택**: Python 3.13 / FastAPI / Jinja2 / PyMySQL / NCP AI 서비스군

---

## 목적

국내 개인 투자자는 핵심 금융 정보가 영어로만 제공되어 정보 접근에 언어 장벽이 존재한다. FinVoice는 다음 세 가지 문제를 해결하기 위해 기획됐다.

1. **언어 장벽**: 영어 뉴스를 빠르게 소화하지 못하면 고점 매수·저점 매도 위험이 커짐
2. **시간 부족**: 여러 종목의 뉴스를 일일이 읽을 시간이 없는 투자자
3. **정보 비대칭**: "오늘 내 관심 종목이 왜 올랐는지"를 빠르게 파악할 수단 부족

NCP Papago·CLOVA Studio·CLOVA Voice를 파이프라인으로 연결해 영어 뉴스를 30초 안에 한국어 음성 브리핑으로 전달한다.

---

## 주요 기능

| 기능 | 설명 |
|------|------|
| **정기 브리핑** | 매일 오전 7시 cron으로 고정 관심종목 6개(AAPL·TSLA·NVDA·MSFT·AMZN·GOOGL) 자동 처리 |
| **기동 시 자동 배치** | 서버 재시작 시 오늘 브리핑이 없으면 즉시 실행 (중복 방지) |
| **온디맨드 검색** | 당일 캐시 있으면 즉시 반환, 없으면 파이프라인 즉석 실행 |
| **개인 관심종목 편집** | 로그인 사용자가 최대 5개 종목을 칩(chip) UI로 직접 설정 |
| **자동 새로고침** | 브리핑 생성 완료 시 3초 폴링으로 자동 감지·새로고침 |
| **실시간 주가 티커바** | 상단에 관심종목 실시간 주가 표시 (60초 서버 캐시) |
| **음성 재생** | CLOVA Voice로 생성한 한국어 mp3를 브라우저에서 바로 재생 |

### 4단계 AI 파이프라인

```
Finnhub (영어 뉴스 수집)
    ↓
NCP Papago (영→한 번역)
    ↓
NCP CLOVA Studio HCX-003 (한국어 요약 + positive/neutral/negative 감성 분석)
    ↓
NCP CLOVA Voice (TTS → mp3)  +  NCP Object Storage (mp3 저장 · 공개 URL)
```

세 가지 진입점(cron 배치 / 서비스 기동 / 온디맨드 검색) 모두 동일한 `pipeline/runner.process_symbol()`을 호출한다.

---

## 시스템 구성

### NCP 서비스

| 서비스 | 역할 | 인증 |
|--------|------|------|
| **Server (Ubuntu VM)** | FastAPI + uvicorn 호스팅, cron 배치 실행 | SSH |
| **Cloud DB for MySQL** | briefing / briefing_item / article / user / user_watchlist | DB 자격증명 |
| **Papago NMT** | 영→한 번역 | NCP APIGW API Key |
| **CLOVA Studio (HCX-003)** | 한국어 요약 + 감성 라벨 | Bearer Token |
| **CLOVA Voice** | 한국어 TTS → mp3 생성 | NCP APIGW API Key |
| **Object Storage (S3 호환)** | mp3 저장 · 공개 URL 서빙 | Access/Secret Key |

### 디렉터리 구조

```
FinVoice/
├── app/
│   ├── main.py              # FastAPI 라우터, 세션 미들웨어
│   ├── config.py            # WATCHLIST, 환경변수 로더
│   ├── db.py                # PyMySQL CRUD
│   ├── auth.py              # bcrypt 비밀번호 해시·검증
│   ├── templates/           # Jinja2 템플릿 (list / detail / login / register / watchlist_edit)
│   └── static/style.css     # 다크 테마 (Toss Invest 스타일)
├── pipeline/
│   ├── runner.py            # process_symbol() 오케스트레이터
│   ├── fetch.py             # Finnhub 뉴스·주가·회사명 수집
│   ├── translate.py         # Papago 번역
│   ├── summarize.py         # CLOVA Studio 요약·감성
│   └── tts.py               # CLOVA Voice TTS + Object Storage 업로드
├── tests/                   # pytest 단위 테스트 (외부 API 전부 mock)
├── scripts/
│   ├── init_db.sql          # 전체 테이블 DDL
│   └── migrate_auth.py      # user·user_watchlist 마이그레이션
├── batch_job.py             # cron 진입점
├── requirements.txt
└── .env.example             # 환경변수 키 목록 (값 없음)
```

### 데이터베이스 스키마 (요약)

```
briefing          날짜별 브리핑 헤더 (briefing_date UNIQUE)
briefing_item     종목별 요약·감성·음성 URL (symbol, item_date 인덱스)
article           원본 기사 제목·URL·출처
user              이메일 + bcrypt 해시
user_watchlist    사용자별 관심종목 (최대 5개)
```

---

## 실행 방법

### 사전 준비

```bash
# 1. 의존성 설치
pip install -r requirements.txt

# 2. 환경변수 설정 (.env는 절대 커밋하지 않는다)
cp .env.example .env
# .env에 Finnhub API 키, NCP API 키, DB 접속 정보, SESSION_SECRET 입력
```

필요한 환경변수는 `.env.example` 주석에 발급처 안내가 있다.

### 실행

```bash
# DB 초기화 (최초 1회)
python scripts/migrate_auth.py
# 또는 전체: mysql -h <host> -u <user> -p <db> < scripts/init_db.sql

# 웹 서버 시작 (기동 시 오늘 브리핑 자동 생성)
uvicorn app.main:app --host 0.0.0.0 --port 8000

# 배치 수동 실행 (선택)
python batch_job.py

# 테스트 (외부 API 전부 mock — 실제 키 불필요)
pytest -q
```

### 서버 운영 (NCP VM)

```bash
# systemd 서비스로 등록된 경우
sudo systemctl start finvoice
sudo systemctl status finvoice

# cron 등록 (매일 07:00 자동 배치)
# 0 7 * * * cd /srv/finvoice && .venv/bin/python batch_job.py >> logs/batch.log 2>&1
```

자세한 배포 절차는 `SERVER_RUNBOOK.md` 참조.

---

## 에러 처리 원칙

- **한 종목 실패 → 전체 배치 중단 없음** (부분 성공 허용)
- **번역 실패** → 영어 원문으로 요약 진행
- **TTS 실패** → `audio_url=None`, 텍스트 요약만 표시 (비치명적)
- **API 한도(429)** → 재시도 없이 skip + 로그
- **같은 날 같은 종목** → DB 캐시 반환, 파이프라인 재실행 없음
