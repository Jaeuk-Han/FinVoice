# FinVoice 개발 시행착오 기록

개발~배포 과정에서 실제로 겪은 트러블슈팅 로그.
같은 삽질을 반복하지 않기 위해 남긴다.

---

## 1. bcrypt 버전 충돌

**증상**: `passlib`로 비밀번호 해시 시 `AttributeError: module 'bcrypt' has no attribute '__about__'`

**원인**: `passlib==1.7.4`는 `bcrypt 4.x / 5.x`와 호환되지 않음. pip 최신 버전은 자동으로 bcrypt 5.x를 설치.

**해결**: `requirements.txt`에 버전 고정
```
passlib[bcrypt]==1.7.4
bcrypt==3.2.2
```

---

## 2. PowerShell 한국어 인코딩 오류

**증상**: paramiko로 서버 명령 출력을 print할 때 `UnicodeEncodeError: 'charmap' codec can't encode`

**원인**: Windows PowerShell 기본 인코딩(cp949)이 UTF-8 출력을 처리 못함.

**해결**: 출력 시 ASCII로 변환
```python
print(o.encode('ascii', errors='replace').decode())
```

---

## 3. python3-venv 패키지 이름 오류

**증상**: 서버에서 `apt-get install python3.12-venv` 실패

**원인**: Ubuntu 24.04에서 패키지명은 `python3.12-venv`가 아니라 `python3-venv`. 또한 `apt-get update` 없이 설치 시도하면 패키지를 못 찾음.

**해결**:
```bash
apt-get update -qq
apt-get install -y python3-venv python3-pip
```

---

## 4. 숨김 파일(.env.example) SFTP 업로드 누락

**증상**: 서버에 `.env.example`이 없어서 `.env` 생성 단계 실패

**원인**: deploy 스크립트에서 `.`으로 시작하는 파일을 일괄 제외했기 때문.

**해결**: `upload_dir` 함수의 일반 루프와 별도로 명시적으로 업로드
```python
sftp.put('.env.example', REMOTE + '/.env.example')
```

---

## 5. 마이그레이션 스크립트 서버 미전송

**증상**: 서버에서 `python scripts/migrate_auth.py` 실행 시 파일 없음 오류

**원인**: `EXCLUDE_FILES`에 `deploy.py`만 넣으려다 `scripts/` 전체가 빠짐. `migrate_auth.py`도 같이 누락.

**해결**: `EXCLUDE_FILES`를 파일명 단위로 정확히 지정하고, `scripts/` 디렉토리는 `EXCLUDE_DIRS`에서 제거.

---

## 6. 예외 핸들러에서 Jinja2 UndefinedError

**증상**: 존재하지 않는 URL 접근 시 500 Internal Server Error (원래 404여야 함)

**원인**: `html_exception_handler`가 `list.html`을 렌더링할 때 `user_email`, `watchlist_meta` 컨텍스트를 넘기지 않아 템플릿에서 변수 참조 오류 발생.

**해결**: 예외 핸들러에도 필수 컨텍스트 전달
```python
async def html_exception_handler(request, exc):
    return templates.TemplateResponse(request, "list.html", {
        "briefings": [], "supported": SUPPORTED, "today": ...,
        "error": msg,
        "user_email": request.session.get("user_email"),
        "watchlist_meta": list(templates.env.globals["WATCHLIST_META"]),
    }, status_code=exc.status_code)
```

---

## 7. 관심종목 커스텀 주가 미표시

**증상**: 사용자가 관심종목을 편집한 뒤 상단 티커바에 주가가 `—`로 표시됨

**원인**: `/api/quotes` 엔드포인트가 항상 고정 `SUPPORTED` 목록만 조회. 프론트에서 `?symbols=` 파라미터를 넘겼지만 서버가 무시.

**해결**: 엔드포인트에서 `symbols` 쿼리 파라미터 처리 추가
```python
@app.get("/api/quotes")
def api_quotes(symbols: str = ""):
    sym_list = [s.strip().upper() for s in symbols.split(",") if s.strip()] if symbols else SUPPORTED
```

---

## 8. 관심종목 저장 후 브리핑 히스토리 미기록

**증상**: 워치리스트 편집 후 백그라운드에서 리포트가 생성되어도 홈 히스토리 목록에 안 보임

**원인**: `_bg_generate_watchlist`에서 `briefing_id=None`으로 `insert_item`을 호출. `briefing` 테이블 레코드가 없어서 `list_briefings` 조회에 안 잡힘.

**해결**: 아이템 삽입 전 `insert_briefing`으로 briefing 레코드 먼저 생성
```python
briefing_id = db.insert_briefing(cur, today, None, None)
conn.commit()
# ... process_symbol ...
item_id = db.insert_item(cur, briefing_id, ...)
```

---

## 9. PowerShell에서 Python 인라인 실행 시 따옴표 충돌

**증상**: `python -c "..."` 안에 파이썬 문자열이 있으면 PowerShell이 따옴표를 잘못 파싱

**원인**: PowerShell here-string(`@'...'@`)도 Python 코드 안의 `<`, `>`, `*` 연산자를 예약어로 해석.

**해결**: 인라인 실행 대신 `.py` 파일로 저장 후 실행. 복잡한 스크립트는 반드시 파일로.

---

## 10. paramiko 미설치

**증상**: 배포 스크립트 실행 시 `ModuleNotFoundError: No module named 'paramiko'`

**원인**: 시스템 Python이 아닌 프로젝트 `.venv`에서 실행했는데 paramiko가 `requirements.txt`에 없음 (배포 전용 도구라 앱 의존성이 아님).

**해결**: 배포 시에만 별도 설치
```powershell
.venv\Scripts\pip install paramiko
```

---

## 11. 자격증명 스크립트 gitignore 누락

**증상**: `git status`에 `deploy.py`, `_update_env.py` 등이 untracked으로 표시 — 실수로 `git add .` 하면 API 키·DB 비밀번호가 그대로 올라갈 뻔.

**해결**: `.gitignore`에 명시적으로 추가
```
scripts/deploy.py
scripts/_*.py
```

---

## 12. SSH remote → HTTPS 전환

**증상**: `git push` 시 `Permission denied (publickey)` — GitHub에 SSH 키 미등록.

**해결**: remote URL을 HTTPS로 변경
```bash
git remote set-url origin https://github.com/Jaeuk-Han/FinVoice.git
```
