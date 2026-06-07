# FinVoice 기능 구현 마일스톤

---

## M1. 파이프라인 기반 구조 설계

`pipeline/` 디렉토리 아래 4단계 파이프라인을 구축했다.

```
fetch → translate → summarize → tts
```

- `fetch.py`: Finnhub API로 종목 뉴스 수집, 회사명 조회(`lookup_company`)
- `translate.py`: Papago로 영어 기사 → 한국어 번역
- `summarize.py`: CLOVA Studio(HyperCLOVA X)로 종목별 요약 + 감성 라벨(positive/neutral/negative) 산출
- `tts.py`: CLOVA Voice로 한국어 요약문 → mp3 생성, NCP Object Storage 업로드 후 재생 URL 반환
  - CLOVA Voice 전용 키(`NCP_VOICE_KEY_ID/KEY`) 미설정 시 Papago 키(`NCP_APIGW_KEY_ID/KEY`)로 자동 폴백 (`config.get_env_or()`)
- `runner.process_symbol`: 위 4단계를 오케스트레이션하는 단일 진입점

**설계 원칙**: `batch_job.py`(배치), `/search`(온디맨드), 워치리스트 저장 후 백그라운드 스레드 — 세 진입점이 동일한 `runner`를 호출하여 로직 중복 없음.

---

## M2. 배치 브리핑 자동 생성

`batch_job.py`를 crontab 진입점으로 구현했다.

- 매일 정해진 시각에 `config.WATCHLIST`의 고정 종목 전체를 순회
- 당일 캐시(`find_cached_item`) 존재 시 재처리 생략
- 한 종목 실패가 전체 배치를 중단하지 않도록 `try/except`로 부분 성공 허용
- `briefing` + `briefing_item` + `article` 3단계 DB 구조로 날짜별 이력 관리
- **서버 cron 등록**: `0 7 * * * cd /srv/finvoice && .venv/bin/python batch_job.py >> /srv/finvoice/logs/batch.log 2>&1`

## M10. 서비스 기동 시 자동 배치

배포 직후나 서버 재시작 시 오늘 브리핑이 없으면 즉시 배치를 실행한다.

- `@app.on_event("startup")`에서 오늘 `briefing` 행 존재 여부 확인
- 없으면 `batch_job.run_batch()`를 백그라운드 daemon 스레드로 즉시 실행
- `Restart=always` systemd 설정으로 인한 재시작 시 중복 실행 방지 (오늘 briefing 있으면 스킵)
- 배포 후 별도 수동 실행 없이 서비스 재시작만으로 오늘치 브리핑 자동 생성됨

---

## M3. 온디맨드 검색

`POST /search` 엔드포인트에서 즉석 브리핑을 생성한다.

- 비로그인 사용자: `WATCHLIST` 고정 종목만 허용
- 로그인 사용자: Finnhub `lookup_company`로 임의 종목 검색 허용
- 당일 캐시 있으면 파이프라인 생략, 즉시 반환
- 결과는 `detail.html` 템플릿 재사용(단일 종목 카드)

---

## M4. 회원가입 / 로그인 / 로그아웃

Starlette `SessionMiddleware`(서명 쿠키) 기반 인증 구현.

- `app/auth.py`: `passlib[bcrypt]`로 비밀번호 해시·검증 (`bcrypt==3.2.2` 고정 — 4.x 이상 passlib 비호환)
- `app/db.py`: `create_user`, `get_user_by_email` CRUD
- 라우트: `GET/POST /register`, `GET/POST /login`, `POST /logout`
- 세션에 `user_id`, `user_email` 저장
- 템플릿 헤더에 로그인 상태에 따라 다른 UI 표시

---

## M5. 개인 관심종목 편집

로그인 사용자가 최대 5개 종목을 직접 설정할 수 있다.

- `user_watchlist` 테이블에 `(user_id, symbol, company)` 저장
- `GET/POST /watchlist/edit` 라우트
- 프론트: 칩(chip) UI로 종목 추가/삭제, 저장 시 hidden input으로 서버 전송
- 존재하지 않는 종목 입력 시 Finnhub으로 검증 후 오류 반환

---

## M6. 관심종목 저장 시 자동 브리핑 생성

워치리스트 저장 직후 백그라운드에서 오늘 브리핑을 미리 생성한다.

- `threading.Thread(daemon=True)`로 비동기 처리 — 사용자는 기다리지 않고 홈으로 리다이렉트
- `briefing` 레코드를 먼저 생성한 뒤 `briefing_item`을 연결 — 히스토리 목록에 정상 노출
- 당일 캐시 이미 있으면 재생성 생략

---

## M7. 브리핑 생성 완료 자동 새로고침

관심종목 저장 후 `/?generating=1`으로 리다이렉트되면 폴링을 시작한다.

- `/api/today-item-count` 엔드포인트: 당일 `briefing_item` 수 반환
- 프론트에서 3초 간격으로 폴링, 카운트 증가 시 자동 새로고침
- 3분 후 타임아웃으로 무한 폴링 방지

---

## M8. 실시간 주가 티커바

홈 상단에 관심종목 실시간 주가를 표시한다.

- `/api/quotes?symbols=` 엔드포인트: Finnhub 주가 조회, 60초 서버 캐시
- 로그인 사용자: 개인 워치리스트 심볼로 조회
- 비로그인: 고정 `WATCHLIST` 심볼로 조회
- 프론트: 페이지 로드 시 한 번 fetch, `▲/▼` + 등락률 표시

---

## M11. 에이전트 역할 재정립 (유지보수 시나리오 추가)

전체 기능 구현 완료 후 CLAUDE.md의 Sub Agent 라우팅 규칙에 유지보수 시나리오를 추가했다.

- 배치 실패, 서버 업데이트, DB 스키마 변경, API 키 교체, 서비스 500 오류, API 한도 초과, TTS 실패 — 7가지 상황별 에이전트 라우팅 기준 정의
- 각 상황에서 어떤 에이전트가 어떤 순서로 개입하는지 명시 → 반복 판단 비용 제거
- 구현 중심 규칙에서 운영·유지보수까지 포함하는 규칙으로 확장

## M9. NCP 서버 배포

Ubuntu 24.04 VM에 systemd 서비스로 배포했다.

- paramiko 기반 Python 배포 스크립트로 SFTP 업로드 + 원격 명령 자동화
- 배포 경로: `/srv/finvoice`, cron 실행: `.venv/bin/python batch_job.py`
- `.venv` 생성, `pip install`, `.env` 설정, DB 마이그레이션 원스텝 실행
- systemd `finvoice.service`로 서버 재시작 시 자동 복구
- `SESSION_SECRET` 배포 시 자동 생성(`secrets.token_hex(32)`)
