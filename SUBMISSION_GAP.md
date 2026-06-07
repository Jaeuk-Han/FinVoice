# SUBMISSION_GAP.md — 제출 산출물 점검 결과

> 점검일: 2026-06-07  
> 기준: `FinVoice.zip` (git archive HEAD, _deploy_css.py 제외, 67개 파일)

---

## 0. 요약 현황

| 제출 항목 | 상태 | 비고 |
|-----------|------|------|
| 발표 PPT | △ 수정 필요 | PDF 있으나 슬라이드 11 분리·GitHub URL 교체 미완료 |
| README.md | ✕ 없음 | `FINVOICE.md`가 내용은 갖춤 — 파일명만 다름 |
| 실행 방법 | ✓ 있음 | `FINVOICE.md` §9, `SERVER_RUNBOOK.md` §3 |
| 데모 캡처 이미지 | ✕ 없음 | 실제 스크린샷 0장 (HTML 목업만 존재) |
| 테스트 결과 | △ 계획만 있음 | `FUNCTION_TEST_PLAN.md` 존재, 실행 결과 파일 없음 |
| 오류 수정 기록 | ✓ 있음 | `PPT_EVIDENCE.md` 오류 8건, `MILESTONE.md` 버그픽스 기록 |
| AI/Ncloud 서비스 설명 | ✓ 있음 | `FINVOICE.md` §4, PPT 슬라이드 05~07 |
| 민감정보 노출 | ⚠️ 위험 | 아래 섹션 4 상세 확인 필수 |

---

## 1. 발표 PPT

- [x] PDF 파일 존재: `claudedesign/FinVoice — Day 8 발표.pdf` (13장)
- [ ] **슬라이드 11 분리 필수** — QA(품질·15점)와 오류수정(문제해결·15점)이 한 장에 압축됨
  - 11a: QA 9/9 엔드포인트 전체 표시
  - 11b: 오류 수정 8건 전체 표시
- [ ] **슬라이드 13 GitHub URL 교체** — `github.com/finvoice`(가짜) → `github.com/Jaeuk-Han/FinVoice`
- [ ] 슬라이드 08·09 더미 화면 → 실서버 캡처로 교체 (권장)
- [ ] 슬라이드 04 "처리 중" 상태 표현 추가 (권장)
- [ ] 제출 전 PDF 재출력(최종 수정본으로 덮어쓰기)

---

## 2. README.md

- [ ] **`FINVOICE.md`를 `README.md`로 복사(또는 이름 변경)** — 내용은 완비됨
  - 서비스 개요, 아키텍처, 파이프라인, NCP 구성, 실행 방법, 환경변수 목록 포함
  - git 커밋 후 FinVoice.zip 재생성 필요

---

## 3. 데모 캡처 이미지

- [ ] **홈 화면** (`/`) — 티커바 + 브리핑 목록 캡처
  - 주소창 크롭 또는 마스킹 (서버 IP 노출 방지)
- [ ] **브리핑 상세** (`/briefing/{id}`) — 종목 카드 + 감성 배지 + 오디오 플레이어 캡처
- [ ] **온디맨드 검색 결과** (`POST /search`) — 검색 후 결과 화면
- [ ] **관심종목 편집** (`/watchlist/edit`) — 칩 UI 캡처 (로그인 상태)
- [ ] **로그인 화면** (`/login`)
- [ ] 캡처 파일을 `docs/screenshots/` 또는 PPT에 삽입
- 현재 존재하는 것: `claudedesign/증시 브리핑 화면 초안.html` (HTML 목업, 실제 서비스 화면 아님)

---

## 4. 테스트 결과

- [ ] **venv에서 pytest 실행 후 결과 저장**
  ```powershell
  .venv\Scripts\activate
  pytest -q | Tee-Object -FilePath docs/pytest_result.txt
  ```
  - `python -m pytest` 실행 시 `No module named pytest` 오류 — 글로벌 Python에 미설치
  - venv `.venv/` 활성화 후 실행 필요
- [ ] 결과 파일(`pytest_result.txt` 또는 터미널 캡처) ZIP·PPT에 포함

---

## 5. 민감정보 노출 — 즉시 조치 필요

> 아래 파일들은 **git untracked** 상태라 ZIP에 미포함이지만, 로컬 디스크에 존재함.
> 제출 전 내용 확인 및 안전한 방식으로 보관·삭제할 것.

### ⚠️ 심각 (비밀번호·키 직접 노출)

| 파일 | 노출 내용 | ZIP 포함 여부 |
|------|-----------|---------------|
| `scripts/_check_batch.py` | 서버 root 비밀번호 하드코딩 | ✕ 미포함 (untracked) |
| `scripts/_check_cron.py` | 서버 root 비밀번호 하드코딩 | ✕ 미포함 (untracked) |
| `scripts/_update_env.py` | 실제 CLOVA Studio API 키 하드코딩, 서버 IP | ✕ 미포함 (untracked) |
| `scripts/deploy.py` | 서버 IP 하드코딩 | ✕ 미포함 (untracked) |
| `scripts/_deploy_startup.py` | 서버 IP 하드코딩 | ✕ 미포함 (untracked) |
| `scripts/_check_server.py` | 서버 IP 하드코딩 | ✕ 미포함 (untracked) |
| `.env` | 실제 CLOVA Studio API 키 포함 | ✕ 미포함 (gitignored) |

- [ ] `scripts/_check_batch.py`, `scripts/_check_cron.py` — 비밀번호 삭제 또는 파일 삭제
- [ ] `scripts/_update_env.py` — 실제 API 키 값 제거 후 자리표시자로 교체
- [ ] **서버 비밀번호 노출됐으므로 서버 접속 비밀번호 교체 권고**
- [ ] **노출된 CLOVA API 키 교체(rotate) 권고** — 파일에서 삭제해도 이미 노출됨

### 주의 (ZIP 제외 확인됨, 기록 목적)

| 파일 | 노출 내용 | ZIP 포함 여부 |
|------|-----------|---------------|
| `_deploy_css.py` | 서버 IP `110.165.16.194` | ✕ ZIP에서 수동 제외됨 |

- [ ] `_deploy_css.py`를 `.gitignore`에 추가 (현재 tracked 상태 — git 이력에 IP 남음)

### 확인 완료 (안전)

- [x] `.env.example` — 자리표시자만 포함, 실제 값 없음
- [x] `SERVER_RUNBOOK.md` — 자리표시자만 사용
- [x] `app/`, `pipeline/`, `tests/` — 비밀값 하드코딩 없음

---

## 6. 제출 전 최종 체크리스트

```
[ ] README.md 생성 (FINVOICE.md 복사)
[ ] PPT 슬라이드 11 분리 완료
[ ] PPT 슬라이드 13 GitHub URL 실제 주소로 교체
[ ] 실서버 데모 캡처 최소 3장 이상 확보
[ ] .venv 활성화 후 pytest -q 실행 → green 확인
[ ] pytest 결과 저장 (docs/pytest_result.txt)
[ ] scripts/_check_batch.py, _check_cron.py 비밀번호 제거
[ ] scripts/_update_env.py 실제 API 키 제거
[ ] _deploy_css.py .gitignore 추가
[ ] 서버 root 비밀번호 교체
[ ] 노출된 CLOVA API 키 교체(rotate)
[ ] FinVoice.zip 재생성 (README.md 추가 후)
[ ] ZIP 내 _deploy_css.py 미포함 재확인
```

---

## 7. 파일 위치 요약

| 산출물 | 현재 위치 | 상태 |
|--------|-----------|------|
| 발표 PPT | `claudedesign/FinVoice — Day 8 발표.pdf` | △ 수정 필요 |
| 시스템 문서(README 역할) | `FINVOICE.md` | ✓ (파일명 변경 필요) |
| 실행 방법 | `FINVOICE.md` §9 | ✓ |
| 서버 운영 절차 | `SERVER_RUNBOOK.md` | ✓ |
| 기능 마일스톤 | `MILESTONE.md` | ✓ |
| 기능 테스트 계획 | `FUNCTION_TEST_PLAN.md` | ✓ |
| 오류 수정 기록 | `PPT_EVIDENCE.md` §7 | ✓ |
| 데모 캡처 이미지 | — | ✕ 없음 |
| pytest 실행 결과 | — | ✕ 없음 |
| 최종 ZIP | `../FinVoice.zip` (938.4 KB) | △ README 추가 후 재생성 |
