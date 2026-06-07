# TEST_RECORD.md — FinVoice 테스트 결과 및 오류 수정 기록

> 기준일: 2026-06-07  
> 테스트 환경: Python 3.13 / pytest 8.x / 외부 API 전부 mock (실제 키 미사용)

---

## 1. 자동화 단위 테스트 결과

### 실행 방법

```bash
# venv 활성화 후 실행
.venv/Scripts/activate      # Windows
# source .venv/bin/activate  # Linux/Mac

pytest -q
```

### 테스트 파일별 커버 범위

| 파일 | 커버 기능 | 주요 케이스 |
|------|-----------|------------|
| `test_api.py` | `POST /search` 캐시 히트·미스 | TC-06 캐시 히트 시 파이프라인 미호출, TC-07 캐시 미스 시 insert+commit 1회 |
| `test_batch.py` | `batch_job.run_batch` 부분 실패 격리 | TC-12 ok=2/failed=1, 실패 종목 rollback·나머지 commit |
| `test_fetch.py` | `fetch.fetch_symbol` | TC-17 필드 매핑, TC-18 url_hash 중복 제거, TC-19 limit 적용 |
| `test_translate.py` | `translate.translate_articles` | TC-21 정상 번역, TC-22 빈값 skip, TC-23 title_ko in-place 갱신 |
| `test_summarize.py` | `summarize.summarize_symbol` | TC-24 정상 요약, TC-25 잘못된 sentiment→neutral 보정, TC-26 malformed JSON fallback, TC-27 "추측 금지" 프롬프트 포함 |
| `test_tts.py` | `tts.synthesize_and_upload` | TC-28 정상 URL 반환, TC-29 빈 문자열→None |
| `test_runner.py` | `runner.process_symbol` | TC-30 전체 성공 흐름, TC-31 TTS 실패 시 audio_url=None + 요약 유지 (graceful) |
| `test_db.py` | `db.py` CRUD | TC-33 insert_item lastrowid, TC-34 find_cached_item, TC-35 epoch→datetime 변환, TC-36 lastrowid=0 fallback |
| `test_config.py` | `config.py` | TC-37 WATCHLIST 튜플 검증, TC-38 get_env 값·RuntimeError |
| `test_auth_helpers.py` | `auth.py` | bcrypt 해시·검증, 틀린 비밀번호 거부 |

**결과: 9개 파일 / 모든 외부 API mock 처리 / pytest -q green**

> 실행 결과 캡처본: `docs/pytest_result.txt` (별도 저장 필요)

---

## 2. 수동 QA 테스트 결과 (2026-06-07, 실서버 기준)

실서버(`http://<서버-IP>:8000`)에서 requests 기반 HTTP 상태 코드 확인.

| # | 엔드포인트 | 기대 상태 | 실제 상태 | 결과 | 비고 |
|---|-----------|-----------|-----------|------|------|
| 1 | `GET /` | 200 | 200 | **PASS** | 브리핑 목록 + 검색 폼 + 면책 푸터 정상 표시 |
| 2 | `GET /login` | 200 | 200 | **PASS** | 한국어 로그인 폼 정상 표시 |
| 3 | `GET /register` | 200 | 200 | **PASS** | 한국어 회원가입 폼 정상 표시 |
| 4 | `GET /api/quotes` | 200 | 200 | **PASS** | 6개 종목 주가 JSON 완비 (`{"AAPL":…, "TSLA":…}`) |
| 5 | `GET /api/today-item-count` | 200 | 200 | **PASS** | `{"count": 6}` 반환 |
| 6 | `POST /search` (AAPL) | 200 | 200 | **PASS** | 캐시 히트, 요약·음성·출처 5건 정상 반환 |
| 7 | `GET /watchlist/edit` (비로그인) | 303 | 303 | **PASS** | `/login`으로 리다이렉트 |
| 8 | `GET /briefing/99999` (없는 id) | 404 | 404 | **PASS** | 한국어 오류 메시지, 스택트레이스 미노출 |
| 9 | `GET /nonexistent` | 404 | 404 | **PASS** | 한국어 안내, 스택트레이스 미노출 |

**9/9 전체 통과**

---

## 3. 파이프라인 동작 증거

| 항목 | 확인 방법 | 결과 |
|------|-----------|------|
| 번역 (Papago) | `POST /search` 응답에서 한국어 요약 확인 | 영→한 정상 변환 |
| 요약·감성 (CLOVA Studio) | 응답 JSON `sentiment` 필드 + 화면 배지 색상 | positive/neutral/negative 정상 분류 |
| TTS + Object Storage | 응답의 `audio_url` 값으로 mp3 직접 재생 | `https://kr.object.ncloudstorage.com/.../AAPL.mp3` 재생 확인 |
| 캐시 동작 | 동일 종목 재검색 시 DB에서 즉시 반환 (파이프라인 미실행) | 응답 속도 < 0.5초 |
| 부분 성공 | 배치 로그에서 ok/failed 카운트 확인 | 일부 종목 실패 시 나머지 정상 처리 |

---

## 4. 개발 중 발생한 오류 수정 기록

| # | 오류 | 원인 | 해결 | 관련 파일 |
|---|------|------|------|-----------|
| 1 | `AttributeError: module 'bcrypt' has no attribute '__about__'` | bcrypt 4.x/5.x가 passlib 1.7.4와 비호환 | `requirements.txt`에 `bcrypt==3.2.2` 버전 고정 | `requirements.txt` |
| 2 | 예외 핸들러에서 500 오류 (404여야 함) | `html_exception_handler`가 `watchlist_meta` 컨텍스트 미전달 → Jinja2 `UndefinedError` | 예외 핸들러에 누락 컨텍스트 전달 | `app/main.py` |
| 3 | 개인 관심종목 주가가 `—` 표시 | `/api/quotes`가 항상 고정 WATCHLIST만 조회하고 `?symbols=` 파라미터 무시 | 엔드포인트에 `symbols` 쿼리 파라미터 처리 추가 | `app/main.py` |
| 4 | 워치리스트 저장 후 히스토리 미노출 | 백그라운드 배치가 `briefing_id=None`으로 `briefing_item` insert → 목록 조회에 미포함 | `insert_briefing` 먼저 실행 후 `briefing_item` 연결 순서 수정 | `app/main.py`, `app/db.py` |
| 5 | 서버 `python3.12-venv` 패키지 설치 실패 | Ubuntu 24.04 패키지명은 `python3-venv`이며 `apt-get update` 선행 필요 | 패키지명 수정, update 선행 | 배포 스크립트 |
| 6 | 배포 후 `.env.example` 서버 미전달 | SFTP 루프가 `.`으로 시작하는 숨김 파일 자동 제외 | `.env.example` 명시적 업로드 추가 | 배포 스크립트 |
| 7 | cron 미등록 → 정기 자동 배치 미실행 | 배포 스크립트에 cron 등록 단계 누락 | paramiko로 cron 등록 추가 + `@app.on_event("startup")`으로 서비스 기동 시 자동 실행 | `app/main.py`, 배포 스크립트 |
| 8 | 티커바 오른쪽 카드 화면 밖으로 잘림 | `.ticker-bar`에 `width: 100%` 없어 `max-width`만으로 flex 컨테이너 폭 미제한, 카드가 뷰포트 밖으로 넘침 | `width: 100%` + `overflow-y: hidden` + `box-sizing: border-box` 추가, `.ticker-item`을 `flex: 0 0 auto`로 변경, `scroll-snap` 적용 | `app/static/style.css` |

---

## 5. 미커버 케이스 (알려진 제한)

| TC | 시나리오 | 현재 상태 | 비고 |
|----|----------|-----------|------|
| TC-08 | 미지원 종목 400 응답 | 자동 테스트 미작성 | 수동 확인 완료 |
| TC-11 | 파이프라인 실패 시 500 직노출 | 미구현 | 데모에서는 캐시 선생성으로 우회 |
| TC-16 | 배치 캐시 재처리 방지 | 미구현 | 현재 같은 날 재실행 시 중복 처리 가능 |
| TC-02 | 목록 빈 상태 안내 문구 | 미구현 | 브리핑 없을 때 빈 `<ul>` 표시 |
| E2E | 브라우저 오디오 재생·폴링 종단 간 테스트 | 자동화 미작성 | 수동 확인으로 대체 |
