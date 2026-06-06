# SERVER_RUNBOOK.md — FinVoice NCP 서버 반영 런북

**FinVoice**(해외 금융뉴스 음성 브리핑 서비스)를 **NCP Server(VM, Ubuntu)** 에 배포·운영하는 절차서.

> ⚠️ **이 문서에는 실제 값(서버 주소·계정명·키 경로·비밀번호·API 키)을 절대 적지 않는다.**
> 모두 `<자리표시자>`로만 둔다. 실제 비밀값은 서버의 `.env` 파일에만 존재한다. (CLAUDE.md §7·§8)

---

## 0. 사전 점검 (반영 전 매번)

- [ ] 로컬에서 `pytest -q` green.
- [ ] 비밀값 노출 검사: 커밋·코드·이 문서에 실제 키/비밀번호/서버정보가 없는지 확인.
- [ ] `.env`가 `.gitignore`에 있고 커밋되지 않았는지 확인.
- [ ] 발표 데모 흐름 확인: 목록(`/`) → 검색(`/search`) → 상세(`/briefing/{id}`) → 음성 재생.
- [ ] 서버에서 실행할 명령을 사용자에게 먼저 설명(무엇을·왜).

---

## 1. 실행 환경 (값은 자리표시자)

| 항목 | 값 |
|------|-----|
| 클라우드 | NCP Server (VM, Ubuntu) |
| 접속 | `ssh <계정명>@<서버-공인IP>` (키 경로·비밀번호는 로컬에서만 관리) |
| 배포 경로 | `<배포경로>` (예: `/srv/stock-briefing`) |
| 파이썬 | Python 3.13 + 가상환경 `<배포경로>/.venv` |
| 웹앱 포트 | `8000` (uvicorn) |
| 외부 노출 | `<도메인-or-공인IP>:8000` — **NCP ACG(보안그룹)** 에서 인바운드 허용 필요 |
| 역프록시 | (선택) nginx 80→8000, 시간 여유 시 도입 |

---

## 2. 환경변수 (이름만 — 값은 서버 `.env`에서 채움)

`.env.example`을 복사해 서버에서 채운다. 키 목록:

```
NEWS_API_KEY
NCP_APIGW_KEY_ID            # 파파고 앱 Client ID (음성 1앱 통합 시 음성도 이 키 사용)
NCP_APIGW_KEY              # 파파고 앱 Client Secret
NCP_VOICE_KEY_ID          # (선택) CLOVA Voice 를 별도 앱으로 등록한 경우만, 없으면 APIGW 키로 폴백
NCP_VOICE_KEY             # (선택) 위와 동일
CLOVA_STUDIO_API_KEY      # CLOVA Studio nv- Bearer 키 (별도 콘솔)
NCP_OS_ACCESS_KEY
NCP_OS_SECRET_KEY
NCP_OS_ENDPOINT
NCP_OS_BUCKET
DB_HOST / DB_PORT / DB_USER / DB_PASSWORD / DB_NAME
```

```bash
cd <배포경로>
cp .env.example .env
# 편집기로 실제 값 입력 (이 문서에는 적지 않음)
chmod 600 .env          # 소유자만 읽기
```

---

## 3. 최초 배포

```bash
# 1) 코드 가져오기
git clone <레포-URL> <배포경로>
cd <배포경로>

# 2) 가상환경 + 의존성
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3) 환경변수 (2번 참고)
cp .env.example .env   # 값 입력

# 4) DB 초기화 (Cloud DB for MySQL)
mysql -h <DB_HOST> -u <DB_USER> -p <DB_NAME> < scripts/init_db.sql

# 5) 수동 기동 확인 (systemd 등록 전 동작 점검)
uvicorn app.main:app --host 0.0.0.0 --port 8000
# 브라우저로 http://<공인IP>:8000 확인 후 Ctrl+C
```

NCP 콘솔에서 **ACG 인바운드 규칙**에 8000(또는 nginx 사용 시 80/443) 포트를 허용한다.

---

## 4. 웹앱 운영 — systemd

`/etc/systemd/system/stock-briefing.service` 생성 (값은 자리표시자):

```ini
[Unit]
Description=Stock News Briefing (FastAPI/uvicorn)
After=network.target

[Service]
User=<계정명>
WorkingDirectory=<배포경로>
EnvironmentFile=<배포경로>/.env
ExecStart=<배포경로>/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now stock-briefing   # 재부팅 후 자동 기동
sudo systemctl status stock-briefing          # 상태 확인
journalctl -u stock-briefing -f               # 로그 확인
```

---

## 5. 배치 운영 — crontab

매일 1회 정기 브리핑 생성 (`batch_job.py`는 cron 진입점).

```bash
crontab -e
```
```cron
# 매일 07:00 (서버 타임존 확인 — date 로 점검). 가상환경 파이썬으로 실행, 로그 적재.
0 7 * * * cd <배포경로> && <배포경로>/.venv/bin/python batch_job.py >> <배포경로>/logs/cron.log 2>&1
```

- `batch_job.py`는 실패 종목이 있으면 종료코드 1을 반환(부분 성공 허용). 로그로 성공/실패 종목 확인.
- 단계별 로그는 `logs/batch_YYYYMMDD.log` 형식(설계 기준).

---

## 6. 업데이트 반영

```bash
cd <배포경로>
git pull
source .venv/bin/activate
pip install -r requirements.txt          # requirements 변경 시
# DB 스키마 변경이 있으면 마이그레이션 (사용자 확인 후)
sudo systemctl restart stock-briefing
sudo systemctl status stock-briefing      # 정상 기동 확인
```

---

## 7. 롤백

```bash
cd <배포경로>
git log --oneline -5                      # 직전 정상 커밋 확인
git checkout <직전-정상-커밋-해시>          # 또는 git revert <문제-커밋>
source .venv/bin/activate
pip install -r requirements.txt           # 의존성 동기화
sudo systemctl restart stock-briefing
sudo systemctl status stock-briefing
```

- 롤백 후 데모 흐름(0번 체크리스트)을 다시 확인한다.
- 되돌리기 어려운 작업(DB 마이그레이션 등)은 **사용자 확인 후** 진행하고 결과 로그를 증거로 남긴다.

---

## 8. 점검 명령 모음

```bash
sudo systemctl status stock-briefing       # 웹앱 살아있는지
journalctl -u stock-briefing -n 100        # 최근 웹앱 로그
crontab -l                                 # 배치 등록 확인
curl -I http://localhost:8000/             # 로컬 응답 확인
tail -n 50 <배포경로>/logs/cron.log         # 배치 실행 로그
```
