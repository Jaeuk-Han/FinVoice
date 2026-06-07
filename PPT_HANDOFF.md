# PPT_HANDOFF.md — FinVoice Day 8 발표 제출 전 체크리스트

> Claude Design 초안(`claudedesign/FinVoice — Day 8 발표.pdf`) 검토 결과를 바탕으로 작성.
> 수정·캡처·보안 점검을 발표 제출 전 완료해야 한다.

---

## 1. 그대로 사용할 장표

| 장표 | 제목 | 이유 |
|------|------|------|
| 01 | 표지 | 서비스명·기간·스택 태그·평가 항목 매핑 완비 |
| 02 | 기획 배경 | AI열풍→반도체→서학개미→정보격차 흐름 명확 |
| 03 | 문제 정의 & 대상 사용자 | 3문제 + 사용자 표 충분 |
| 05 | AI 서비스 상세 | 3카드(입력·출력·실패) 구성 양호 — 여백만 조정 여부 판단 |
| 06 | CLOVA Studio 프롬프트 | HCX-003 파라미터, NVDA JSON 출력, 감성 배지 연결 완비 |

---

## 2. 수정해야 할 장표

| 우선순위 | 장표 | 수정 내용 |
|----------|------|-----------|
| **필수** | 11 | **슬라이드를 11a(QA·품질)와 11b(오류수정·문제해결)로 분리.** 평가 기준 30점(15+15)이 한 장에 압축됨. 11a는 9/9 전체 엔드포인트, 11b는 8건 오류 전체 표시 |
| **필수** | 13 | GitHub URL `github.com/finvoice(데모)` → 실제 URL(`github.com/Jaeuk-Han/FinVoice`)로 교체 |
| 권장 | 04 | 파이프라인 박스 하단 또는 온디맨드 카드 옆에 "검색 → 파이프라인 실행 중(수 초) → 결과 반환" 단계 표기 추가 |
| 권장 | 07 | 오른쪽 패널 하단 빈 공간에 서비스 연결 아키텍처 다이어그램 추가(Server→DB, Server→NCP AI, Server→Object Storage) |
| 권장 | 10 | 왼쪽 다이어그램 패널 하단에 `runner.process_symbol()` 호출 코드 한 줄 또는 "동일 함수 재사용 → 로직 중복 없음" 콜아웃 추가 |
| 선택 | 12 | 하단 빈 공간에 `pytest -q` 통과 결과 한 줄 + "외부 API 전체 mock" 설명 추가 |

---

## 3. 직접 캡처를 넣어야 하는 위치

| 위치 | 필요한 캡처 | 비고 |
|------|------------|------|
| 11a (QA 장표) | `pytest -q` 터미널 결과 — `9 passed` 한 줄 캡처 | 작게 우측 하단 삽입 가능 |
| 11b (오류수정 장표) | 선택적: 수정 전후 CSS 비교 diff 캡처 | 없어도 무방, 있으면 신뢰도 상승 |
| 12 (문서화 장표) | 선택적: GitHub 커밋 히스토리 스크린샷 | 하단 빈 공간 활용 |

---

## 4. 실제 프로젝트 화면으로 교체할 더미 화면

| 장표 | 현재 더미 화면 | 교체할 실제 화면 | 주의사항 |
|------|---------------|-----------------|----------|
| 08 (주요 화면 1 — 홈) | 주소창 `finvoice.demo` / 티커바 META·NFLX·NVDA·KO·MCD / 브리핑 목록 1건만 표시 | 실서버 홈 화면 캡처 — 티커바 WATCHLIST 6종목, 날짜별 브리핑 2~3건 이상 노출 | **캡처 전 주소창에 서버 IP가 노출되지 않도록 브라우저 주소창 가린 뒤 캡처** |
| 08 (주요 화면 1 — 상세) | NVDA 상세 목업 | 실서버 상세 페이지(감성 배지 + 요약 + 오디오 플레이어 + 출처 접이식) 캡처 | 오디오 파일 있는 종목으로 캡처 |
| 09 (주요 화면 2 — 워치리스트) | 워치리스트 편집 칩 목업 | 실서버 `/watchlist/edit` 화면 캡처 | 로그인 상태 필요 |
| 09 (주요 화면 2 — 로그인) | 로그인 폼 목업 | 실서버 `/login` 화면 캡처 | 오류 메시지 없는 빈 폼 상태 |

---

## 5. 발표자 메모에서 보강할 문장

| 장표 | 보강 문장 |
|------|-----------|
| 04 | "온디맨드 검색 시 파이프라인이 즉석 실행되며 수 초 소요됩니다. 처리 중에는 로딩 스피너를 표시하고 버튼을 비활성화하여 중복 제출을 방지합니다." |
| 06 | "실제 HyperCLOVA X HCX-003 모델을 사용하며 temperature 0.3으로 고정해 결과 변동성을 줄였습니다. 한 번에 최대 5개 기사를 묶어 전달하여 단일 기사 대비 맥락이 풍부합니다." |
| 07 | "bcrypt를 3.2.2 버전으로 고정한 이유는 passlib 1.7.4와의 호환성 문제 때문입니다. 4.x 이상 버전에서는 해시 검증이 실패합니다." |
| 11a | "pytest 9/9 PASS. 외부 API(Finnhub, Papago, CLOVA Studio, CLOVA Voice, Object Storage)는 전부 mock 처리하여 네트워크 없이 테스트가 완전히 동작합니다." |
| 11b | "한 종목·단계 실패가 전체 배치를 중단하지 않도록 부분 성공을 허용했습니다. TTS 실패 시에도 텍스트 요약은 정상 표시됩니다." |
| 13 | "투자 조언이 아님 면책 문구는 모든 화면 푸터에 고정으로 표시됩니다." |

---

## 6. 제출 전 확인할 파일 목록

- [ ] `claudedesign/FinVoice — Day 8 발표.pdf` — 최종 수정본으로 교체됐는지 확인
- [ ] `PPT_EVIDENCE.md` — 발표 자료와 내용 일치 여부 확인(특히 QA 9/9, 오류 8건)
- [ ] `app/static/style.css` — 티커바 CSS 수정본이 반영됐는지 확인(`width: 100%` 포함 여부)
- [ ] `.gitignore` — `.env`, `_deploy_css.py`, `*.pyc`, `__pycache__` 포함 여부 확인
- [ ] `requirements.txt` — `bcrypt==3.2.2` 핀 버전 포함 여부 확인
- [ ] `scripts/init_db.sql` — `user`, `user_watchlist` 테이블 DDL 포함 여부 확인
- [ ] `tests/` — `pytest -q` 로컬에서 green 확인 후 제출
- [ ] GitHub 레포지터리 — `main`/`master` 브랜치 최신 커밋 push 완료 여부 확인

---

## 8. 슬라이드 07 다이어그램 개선 — 실제 데이터 흐름 (코드 기반)

> 현재 슬라이드 07의 "서비스 연결 구조"가 `Server → 3개 화살표` 수준으로 단순하여 -3점 요인.
> 아래 내용을 바탕으로 각 화살표에 **요청 형식 · 응답 데이터**를 병기하면 AI·클라우드 활용 점수 개선 가능.

---

### 실제 데이터 흐름 (pipeline/ 코드 직접 추출)

```
① Finnhub (외부)
   GET /company-news?symbol=AAPL&from=...&to=...&token=...
   └→ [{ headline, summary, url, source, datetime }] × N건
      ↓ parse_articles() → url_hash 중복 제거 → 최대 5건 슬라이싱

② NCP Papago
   POST https://papago.apigw.ntruss.com/nmt/v1/translation
   Header: X-NCP-APIGW-API-KEY-ID / X-NCP-APIGW-API-KEY
   Body:   source=en, target=ko, text=기사제목+본문 (≤4,500자)
   └→ translatedText (한국어)
      ↓ 각 기사에 title_ko, body_ko 추가 (in-place)

③ CLOVA Studio HCX-003
   POST https://clovastudio.stream.ntruss.com/v1/chat-completions/HCX-003
   Header: Authorization: Bearer {CLOVA_STUDIO_API_KEY}
           X-NCP-CLOVASTUDIO-REQUEST-ID: {uuid}
   Body:   messages=[system, user], maxTokens=500, temperature=0.3
   └→ { "summary": "한국어 3~5문장", "sentiment": "positive|neutral|negative" }

④ CLOVA Voice
   POST https://naveropenapi.apigw.ntruss.com/tts-premium/v1/tts
   Header: X-NCP-APIGW-API-KEY-ID / X-NCP-APIGW-API-KEY
   Body:   speaker=nara, format=mp3, text=요약문 (≤1,900자)
   └→ mp3 binary (bytes)

⑤ Object Storage (S3 호환)
   boto3 PUT → endpoint: NCP_OS_ENDPOINT
               bucket:   NCP_OS_BUCKET (stock-briefing-audio)
               key:      audio/{item_date}/{symbol}.mp3
               ACL:      public-read
   └→ 공개 URL: {endpoint}/{bucket}/audio/{date}/{symbol}.mp3

⑥ Cloud DB for MySQL
   [캐시 조회] SELECT briefing_item WHERE symbol=? AND item_date=?
   └→ 히트 시 파이프라인 건너뜀 (즉시 반환)
   [결과 저장] INSERT briefing → INSERT briefing_item (summary_ko, sentiment, audio_url)
              INSERT article × N건
```

---

### 슬라이드 07 다이어그램 개선안 (Claude Design 전달용)

현재 다이어그램:
```
Server FastAPI → Cloud DB for MySQL
               → NCP AI · Papago / CLOVA
               → Object Storage · mp3
```

개선 다이어그램 (화살표에 데이터 레이블 추가):
```
                  ┌─────────────────────────────────────────────────────────┐
Finnhub ─────────▶│                  Server (FastAPI)                       │
뉴스 JSON          │                                                         │
                  │  fetch → translate → summarize → tts → upload           │
                  └──────┬────────────┬──────────────────┬──────────────────┘
                         │            │                  │
          캐시 조회·결과 저장 │  번역·요약·음성 요청 │       mp3 PUT │
          (SQL CRUD)     │  (HTTPS REST API)  │  (S3 호환 API) │
                         ▼            ▼                  ▼
                   Cloud DB      NCP AI 서비스      Object Storage
                   for MySQL     Papago / CLOVA     stock-briefing-audio
                                 Studio / Voice     → 공개 재생 URL
```

**화살표별 핵심 표기 (슬라이드에 작게 병기 권장)**

| 화살표 | 표기 내용 |
|--------|-----------|
| Finnhub → Server | `GET /company-news · JSON 배열` |
| Server → Cloud DB | `SELECT(캐시) / INSERT(저장) · PyMySQL` |
| Server → Papago | `POST · text≤4,500자 · translatedText 반환` |
| Server → CLOVA Studio | `POST · messages+temperature=0.3 · JSON {summary, sentiment}` |
| Server → CLOVA Voice | `POST · text≤1,900자 · speaker=nara · mp3 binary` |
| Server → Object Storage | `S3 PUT · public-read ACL · 공개 URL 반환` |

---

## 7. 보안상 지워야 할 텍스트나 이미지

| 위치 | 내용 | 조치 |
|------|------|------|
| PPT 08, 09 더미 화면 | 실서버 화면 캡처 시 브라우저 주소창에 서버 IP 노출 가능 | **캡처 전 주소창 영역 크롭 또는 모자이크 처리** |
| PPT 13 | `github.com/finvoice` 가짜 URL — 발표 중 접속 시도 시 혼란 | 실제 URL로 교체 또는 "(발표 후 공개)" 명시 |
| `_deploy_css.py` | 서버 IP `110.165.16.194` 하드코딩 — 소스 제출 시 포함되지 않도록 주의 | `.gitignore`에 `_deploy_css.py` 추가 확인, 커밋·ZIP 제출 시 제외 |
| 발표자 메모 전체 | DB 비밀번호, NCP API 키, SSH 정보를 메모에 적지 않음 | 발표자 메모에는 말할 내용만 기재, 자격증명 일절 금지 |
| 실제 캡처 화면 | 로그인 세션에 이메일/비밀번호가 화면에 노출되는 상태로 캡처 금지 | 테스트 계정(`test@example.com` 등)으로 로그인 후 캡처 |
