# FUNCTION_TEST_PLAN.md — 해외 금융뉴스 음성 브리핑 서비스 기능 검증 계획

## 1. 문서 머리말
- **목적**: 이미 구현된 기능을 실제 코드 기준으로 식별하고, 기능별 검증 시나리오·자동화 매핑·발표 데모 경로를 정의한다.
- **범위**: 파이프라인(fetch/translate/summarize/tts), 오케스트레이션(runner), 배치(batch_job), 웹 라우트(/, /briefing/{id}, /search), DB(db), 설정(config), 템플릿(list/detail).
- **전제**:
  - 외부 API(Finnhub, Papago, CLOVA Studio, CLOVA Voice, Object Storage)는 **자동 테스트에서 전부 mock**한다(실제 키 미사용).
  - 비밀값은 `.env`로만 다루며 `.env.example`에는 자리표시자만 둔다. 코드는 `config.get_env`로 로딩.
  - 자동 테스트는 실제 DB에 연결하지 않는다(`FakeCursor`/`FakeConn` 사용).
- **테스트 환경**: Python 3.13 / pytest 8.2.2. 별도 `pytest.ini`·`conftest.py` 없음. 루트에 `README.md` 없음(확인됨).
- **실행 명령**:
  ```
  pip install -r requirements.txt
  pytest -q                                                   # 외부 API 전부 mock
  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000    # 웹앱
  python batch_job.py                                         # 배치 1회
  ```
- **완료 기준**: `pytest -q` green + 변경 영역 동작 증거(CLAUDE.md §3).

## 2. 실제 기능 목록
| 기능명 | 진입점 | 코드 위치 | 구현상태 |
|---|---|---|---|
| 브리핑 목록 페이지 | `GET /` | `app/main.py:23-27`, `list.html` | 구현 |
| 브리핑 상세 / 404 | `GET /briefing/{id}` | `app/main.py:29-39`, `detail.html` | 구현 |
| 온디맨드 검색(정규화·검증·캐시·즉석실행) | `POST /search` | `app/main.py:41-66` | 구현 |
| 뉴스 수집(7일·dedupe·limit5) | `fetch.fetch_symbol` | `pipeline/fetch.py:8-50` | 구현 |
| 번역(Papago, 빈값 skip, in-place) | `translate.translate_articles` | `pipeline/translate.py:18-28` | 구현 |
| 요약(CLOVA HCX-003, JSON 파싱, sentiment 검증) | `summarize.summarize_symbol` | `pipeline/summarize.py:8-53` | 구현 |
| 음성합성+업로드(빈값→None, 1900자컷) | `tts.synthesize_and_upload` | `pipeline/tts.py:7-37` | 구현 |
| 종목 오케스트레이션(TTS 실패 graceful, non-https→None) | `runner.process_symbol` | `pipeline/runner.py:6-30` | 구현 |
| 정기 배치(commit/rollback, 부분성공, exit code) | `batch_job.main/run_batch` | `batch_job.py:10-46` | 구현 |
| DB 저장/캐시 조회 | `app/db.py` | `app/db.py:20-80` | 구현 |
| 설정·WATCHLIST·get_env | `app/config.py` | `app/config.py:7-24` | 구현 |
| 시장 전반 요약(B) | 배치 | `batch_job.py:13`(`market_summary=None`) | **미구현** |
| 배치 캐시 재처리 방지 | 배치 | `batch_job.py:18-26`(`find_cached_item` 미사용) | **미구현** |
| `/search` 파이프라인 실패 친화 메시지 | `POST /search` | `app/main.py:56`(핸들러 없음) | **미구현** |
| 온디맨드 로딩표시·중복제출 방지 | `list.html` | `app/templates/list.html:5-8` | **미구현** |
| 빈 상태 안내(목록/검색) | 템플릿 | `list.html:9-13`, `detail.html:6-15` | **미구현** |
| 재시도/백오프·429 skip | 파이프라인 | 해당 코드 없음 | **미구현** |

## 3. 기능별 테스트 시나리오
흐름: 입력 → 처리 중 → 결과 → 다시 시도 / 오류·빈 상태.

### 3.1 목록 페이지 (`GET /`)
| TC | 시나리오 | 입력 | 기대 결과 | 상태 |
|---|---|---|---|---|
| TC-01 | 브리핑 존재 | GET / | 200, 날짜 링크 + 검색폼 + 면책푸터 | 자동 미커버(수동) |
| TC-02 | 빈 상태 | GET / (briefings=[]) | 200, 폼·푸터 표시되나 안내문 없음(현재 빈 `<ul>`) → 기능 gap | 미구현 |

### 3.2 상세 페이지 (`GET /briefing/{id}`)
| TC | 시나리오 | 입력 | 기대 결과 | 상태 |
|---|---|---|---|---|
| TC-03 | 정상 조회 | 존재하는 id | 200, 종목 카드(회사명·심볼·`s-{sentiment}`·요약·출처) | 자동 미커버(수동) |
| TC-04 | 없는 브리핑 | 없는 id | 404 "브리핑을 찾을 수 없습니다"(`main.py:33-34`) | 자동 미커버(TODO) |
| TC-05 | audio 유무 | audio_url=None | 플레이어 미표시, 텍스트만(`detail.html:10`) | 자동 미커버(수동) |

### 3.3 온디맨드 검색 (`POST /search`)
| TC | 시나리오 | 처리 중 | 기대 결과 | 상태 |
|---|---|---|---|---|
| TC-06 | 캐시 히트(AAPL) | `process_symbol` **미호출** | 200, 캐시 요약, 파이프라인 0회(`main.py:49-54`) | 커버 `test_api.py:16-33` |
| TC-07 | 캐시 미스→즉석 | `process_symbol`→insert→commit 1회 | 200, 새 요약, `committed==1`(`main.py:55-62`) | 커버 `test_api.py:35-48` |
| TC-08 | 미지원 종목(FOO) | 즉시 종료 | 400 "지원하지 않는 종목…"(`main.py:44-45`) | 자동 미커버(TODO) |
| TC-09 | 소문자 정규화(aapl) | `.upper()`→AAPL | 정상 분기(`main.py:43`) | 자동 미커버(TODO) |
| TC-10 | 캐시 sentiment 비정상 | neutral 보정 | 배지 `s-neutral`(`main.py:52-53`) | 자동 미커버(TODO) |
| TC-11 | 파이프라인 실패 | 예외 핸들러 없음 | **현재 500 직노출(친화 메시지 없음)** — 기능 gap(`main.py:56`) | 미구현(확인 필요) |

### 3.4 배치 (`batch_job`)
| TC | 시나리오 | 기대 결과 | 상태 |
|---|---|---|---|
| TC-12 | 부분 실패 격리 | ok=2,failed=1, rollback 1회, 나머지 commit(`batch_job.py:18-33`) | 커버 `test_batch.py:16-31` |
| TC-13 | 전체 성공 exit | `main()`→exit 0(`batch_job.py:41`) | 자동 미커버(TODO) |
| TC-14 | 실패 존재 exit | `main()`→exit 1(`batch_job.py:41`) | 자동 미커버(TODO) |
| TC-15 | briefing 생성 실패 | 배치 중단(raise)(`batch_job.py:13-16`) | 자동 미커버(TODO) |
| TC-16 | 같은날 재처리 방지 | **현재 캐시 분기 없음 → 무조건 재처리**(`batch_job.py:18-26`) | 미구현(확인 필요) |

### 3.5 파이프라인 단계별
| TC | 시나리오 | 기대 결과 | 상태 |
|---|---|---|---|
| TC-17 | fetch 필드 매핑 | headline→title_en, url/source/url_hash(`fetch.py:19-33`) | 커버 `test_fetch.py` |
| TC-18 | fetch 중복 제거 | 동일 url_hash 1건(`fetch.py:35-43`) | 커버 `test_fetch.py` |
| TC-19 | fetch limit | limit=1→1건(`fetch.py:45-50`) | 커버 `test_fetch.py` |
| TC-20 | fetch 비정상 URL 차단 | http/https 아니면 ""(`fetch.py:22-24`) | 자동 미커버(TODO) |
| TC-21~23 | translate 정상/빈값 skip/in-place | 번역·원문유지·title_ko 채움(`translate.py:18-28`) | 커버 `test_translate.py` |
| TC-24~27 | summarize 정상/잘못된 sentiment/malformed JSON/가드레일 | 추출·neutral 보정·fallback·"추측 금지" 포함(`summarize.py`) | 커버 `test_summarize.py` |
| TC-28~29 | tts 정상/빈문자열 | URL 반환 / None(`tts.py:33-37`) | 커버 `test_tts.py` |
| TC-30~31 | runner 전체성공/TTS 실패 graceful | audio_url=URL / None+요약 유지(`runner.py`) | 커버 `test_runner.py` |
| TC-32 | runner non-https→None | http URL이면 None(`runner.py:20-21`) | 자동 미커버(TODO) |

### 3.6 DB / 설정
| TC | 시나리오 | 기대 결과 | 상태 |
|---|---|---|---|
| TC-33 | insert_item lastrowid | 반환 id(`db.py:34-41`) | 커버 `test_db.py` |
| TC-34 | find_cached_item | symbol+date 조회(`db.py:55-60`) | 커버 `test_db.py` |
| TC-35 | insert_article epoch→datetime | datetime 변환(`db.py:45-46`) | 커버 `test_db.py` |
| TC-36 | insert_briefing lastrowid=0 fallback | SELECT로 id(`db.py:28-31`) | 커버 `test_db.py` |
| TC-37~38 | WATCHLIST·get_env | 튜플 검증 / 값·RuntimeError(`config.py:7-24`) | 커버 `test_config.py` |

## 4. 자동화 테스트 매핑 요약
- **커버(자동)**: TC-06·07·12·17~19·21~31·33~38 → 9개 테스트 파일. 실행 `pytest -q`.
- **TODO(자동 추가 권장)**: TC-04·08·09·10·13·14·15·20·32.
- **수동(템플릿/E2E)**: TC-01·02·03·05·11·16.
- **미구현 기능(시나리오 보류)**: 시장요약(B), 배치 캐시(TC-16), `/search` 친화 에러(TC-11), 로딩·빈상태·재시도.

> 정확한 통과 개수는 `pytest -q` 실행으로 확정(본 계획은 읽기 전용 작성 — 미실행).

## 5. 발표 데모 경로(수동 체크리스트)
전제: `.env`에 실제 키(`<redacted>`) 채움, `scripts/init_db.sql`로 DB 초기화, `python batch_job.py` 1회로 당일 데이터 생성.

| 단계 | 동작 | 기대 화면/증거 | 실패 지점 / fallback |
|---|---|---|---|
| D-1 | `python batch_job.py` | 로그 "처리 완료…", exit 0 | 일부 실패해도 부분성공(exit 1 가능) → 로그로 실패 종목만 확인 |
| D-2 | `/` 접속 | 날짜 링크 + 검색폼 + 면책 | 데이터 없으면 빈 목록 → D-1 재실행 |
| D-3 | 검색폼 AAPL 제출 | 단일 종목 카드(요약·배지) | 캐시 미스 시 수 초 지연(로딩표시 없음) → 캐시 선적재 권장 |
| D-4 | 카드 확인 | 회사명·심볼·감성배지·한국어 요약·출처 details | 감성색 `s-*`(`style.css:3`) |
| D-5 | 음성 재생 | `<audio controls>` 재생(`detail.html:10`) | audio_url 없으면 텍스트만(graceful) |
| D-6 | 미지원 심볼 | 400 한국어(`main.py:45`) | 파이프라인 실패는 현재 500 가능(TC-11) → 데모 종목 캐시 선생성 |

## 6. 비밀값 취급 주의
- 데모·테스트·문서·스크린샷 어디에도 실제 키·토큰·DB 비번·SSH 정보 노출 금지(CLAUDE.md §8).
- 문서에 예시가 필요하면 `your_xxx_key` 자리표시자 또는 `<redacted>`만.
- 자동 테스트는 가짜 값만 사용, 실 키로 외부 API 호출 금지.
- 노출 시: 즉시 통보 → 해당 키 NCP/Finnhub에서 폐기·재발급(rotate) → 필요 시 git 히스토리 정리 → 증거 기록.
- 화면 캡처 시 URL 쿼리스트링(토큰 가능)·서버 주소·계정명 마스킹.
