# DESIGN_HANDOFF.md — 증시 브리핑 화면 핸드오프

> 대상 산출물: `증시 브리핑 화면 초안.html` + `app.css` (+ `fonts/ChosunSg.ttf`)
> 근거 문서: `DESIGN_BRIEF.md`, `DESIGN_QA.md` (검토일 2026-06-06, 7개 항목 중 6개 통과 / 핸드오프 분류만 보완 필요)
> 목적: 디자인 초안을 프로덕션(서버 사이드 렌더링)으로 옮길 때의 채택·폐기·재요청 기준 정리
> 상태: **초안 승인 — 프로덕션 전환 준비 단계.** 본 문서 작성 시점에 프로젝트 코드는 수정하지 않음.

---

## 1. 반영할 화면

QA §1에서 6개 뷰 모두 통과. 프로덕션에서는 서버 라우트/템플릿으로 분리해 반영한다.

| 화면 | 초안 뷰 함수 | 프로덕션 매핑 | 비고 |
|------|-------------|---------------|------|
| 목록 페이지 | `viewList()` | `GET /` → `list.html` | 검색 폼 + 날짜별 브리핑 목록 |
| 온디맨드 검색 결과 | `viewResult()` | `POST /search` → `detail.html` 재사용 | 단일 종목 카드 |
| 날짜별 상세 | `viewDetail()` | `GET /briefing/{id}` → `detail.html` | 시장 요약(B) + 종목별 카드(A) |
| 로딩 | `viewLoading()` | 검색 처리 중 상태 | 스피너 + "요약 생성 중…" + 단계 표시 |
| 오류 | `viewError()` | 미지원 종목 / 파이프라인 실패 | §6 재요청 항목 참조 |
| 빈 상태 | `viewEmpty()` | 브리핑 없음 | §6 "404 분리" 확인 후 확정 |

**채택**: 6개 뷰의 레이아웃·정보 구조·읽기 흐름(브랜드 → 검색 → 카드 요약).
**비채택**: 이 뷰들을 묶는 JS 상태 머신(`S` 객체, `render()`)은 SSR로 대체 (§5).

---

## 2. 반영할 컴포넌트

QA "그대로 쓸 것" 분류를 그대로 채택한다. `app.css`의 아래 클래스는 마크업 이식 시 클래스명을 유지한다.

| 컴포넌트 | 클래스 | 채택 사유 |
|----------|--------|-----------|
| 감성 배지 | `.badge` + `.s-positive/.s-negative/.s-neutral` | 브리프 §8 색상 규칙과 동일 (변경 금지) |
| 결과 카드 | `.card`, `.card-top`, `.zone`, `.zone-label` | 요약·근거·다음 행동 영역 분리 구조 |
| 음성 플레이어 | `.player`, `.play-btn`(44×44) | 터치 크기·시각 계층 충족 — 단, JS 시뮬레이션은 실제 `<audio>`로 교체 (§5) |
| 로딩 | `.center-state`, `.spinner`, `.load-step` | 브리프 §7 로딩 스펙과 일치 |
| 출처(근거) 접이식 | `.sources`, `.source-list` (`rel="noopener noreferrer"` 포함) | 브리프 §5 결과 요건 충족 |
| 면책 푸터 | `.disclaimer` | "투자 조언 아님" 고정 요건 |
| 검색 폼 | `.search`, `.field`, `.btn-submit`, `.chip` | 시각 위계 1순위(48px 입력 + 흑색 제출 버튼) |
| 목록 항목 | `.list`, `.list-item`, `.today-tag` | 날짜·요약 1줄·진입 화살표 구조 |
| 모바일 반응형 | `.app.is-mobile { … }` 블록 | 제출 버튼 전폭·세로 쌓기·카드 단일 컬럼 전환 |

**채택할 레이아웃**: 결과 카드 **A(스택형)만**. B(분할형)·C(컴팩트형)은 폐기 (§4).

---

## 3. 유지할 색상 / 타이포 / 간격 기준

`app.css` `:root` 토큰을 단일 출처로 유지한다. 값 변경 금지.

### 색상 (변경 금지)
- 잉크/CTA: `--ink: #111111`, `--ink-active: #242424`
- 본문/보조: `--body: #374151`, `--muted: #6b7280`, `--faint: #898989`
- 면/선: `--canvas: #fff`, `--surface-soft: #f8f9fa`, `--hairline: #e5e7eb`
- **감성(브리프 §8 고정)**: `--s-positive: #0a0` · `--s-negative: #c00` · `--s-neutral: #888`
  - ⚠️ `#888` 중립 배지 명도 대비는 §6에서 재확인 대상.

### 타이포그래피
- 로고/헤드라인: **ChosunSg(조선신문체)** — `--font-head` (브랜드 마크 21px, 카드 타이틀 24px, 섹션 19px)
- 본문/UI: `--font-ui` = `system-ui` 스택 (브리프 §8 지정)
- 입력 심볼은 `text-transform: uppercase` + `letter-spacing: 1px`로 대문자 정규화 시각화

### 간격 / 형태
- 레이아웃 폭: ⚠️ 초안 `.wrap`은 `max-width: 680px` — 브리프 §8 기준은 **760px**. 프로덕션 전 통일 (§7).
- 라운드: 카드/입력 `--radius-md(8px)`, 카드 컨테이너 `--radius-lg(12px)`, 배지/칩 `--radius-pill`
- 그림자: `--shadow-xs/sm` (소프트, 저알파) — 강한 그림자 금지
- 터치 타깃: 재생 44×44, 제출/액션 버튼 48/44 높이 유지

---

## 4. 우선 반영할 디자인 요소 3개

프로덕션에서 가장 먼저 옮겨야 하는 핵심 3가지 (서비스 가치 직결 순).

1. **검색 폼 → 제출 위계** (`.search` + `.field` + `.btn-submit`)
   브리프 §9 1순위. 첫 화면에서 종목 입력→검색이 즉시 가능해야 함. 48px 입력 + 흑색 제출 버튼, 지원 종목 칩, 대문자 정규화 표시까지 한 단위로 이식.

2. **결과 카드의 3영역 분리** (`.zone` + `.zone-label`: 요약 · 근거 · 다음 행동)
   브리프 핵심 요건. 요약(읽기) → 근거(출처 접이식) → 다음 행동(버튼)이 시각적으로 분리돼야 함. 레이아웃 A 채택.

3. **감성 배지 시스템** (`.badge.s-*`)
   브리프 §8 변경 금지 색상. 긍정/중립/부정을 한눈에 구분시키는 신뢰 요소. 토큰값 그대로 유지.

---

## 5. 버릴 요소

QA "버릴 것" 분류를 그대로 적용. 모두 **리뷰 전용**이며 프로덕션 화면에는 넣지 않는다.

| 버릴 대상 | 이유 |
|-----------|------|
| 상단 툴바 전체 (화면/카드/뷰포트 세그먼트 스위처) | 디자인 리뷰용 크롬 |
| 기기 프레임 `<div class="device mobile/desktop">` + `.device-chrome` | 리뷰 전용 래퍼 |
| JS 상태 머신 (`S`, `render()`, `viewList/Result/Detail/...` 전부) | SSR(Jinja2)로 대체 |
| JS 음성 시뮬레이션 (`togglePlay`, `timers`, 진행바 타이머) | 실제 `<audio>`로 교체 |
| JS mock 상수 (`STOCKS`, `BRIEFINGS`, `SOURCES`, `SUPPORTED`) | 서버 템플릿 변수로 치환 |
| 결과 카드 레이아웃 **B(분할형)·C(컴팩트형)** | 단일 템플릿에 레이아웃 선택 불필요. A만 채택 |
| 하단 `caption` 안내문("모든 수치는 데모용 샘플…") | 리뷰 전용 설명, 프로덕션 노출 금지 |
| `데모`/`데모용 샘플` 배지·문구 | 실데이터 연결 시 제거 |

---

## 6. Claude Design에 다시 요청할 요소

QA "다시 요청할 것" + 본 검토 추가분. 프로덕션 마크업 작성 **전에** 디자인 확정 필요.

| 항목 | 요청 내용 |
|------|-----------|
| 오디오 없는 상태 처리 | TTS 실패/미생성 시 `.player` 영역 자체를 숨기는 조건부 UI. 현재는 플레이어가 항상 렌더됨 (브리프 §5 "mp3 있을 때만 표시"와 불일치) |
| "브리핑 없음(404)" 전용 화면 | 현재 오류는 `unsupported`·`pipeline` 2종뿐. 브리프 §7의 "아직 브리핑이 없습니다"가 빈 상태와 404 중 어디로 갈지 확정 — 별도 404 메시지 디자인 필요 여부 결정 |
| 중립 배지 명도 대비 | `--s-neutral: #888`은 흰 배경 대비 약 3.5:1로 WCAG AA(4.5:1) 미달. "변경 금지" 원칙과 충돌 → ① 텍스트만 더 진하게 + 칩 배경 유지 ② 보더/도트로 보강 등 대비 보강안 요청 |
| 레이아웃 폭 확정 | 680px(초안) vs 760px(브리프) 중 최종값 디자인 확인 (§7과 연동) |

---

## 7. 프로젝트 기존 CSS와 충돌할 수 있는 요소

이식 시 기존 `app/static` CSS와의 충돌 가능 지점.

| 충돌 가능 요소 | 위험 | 대응 |
|----------------|------|------|
| `.wrap { max-width: 680px }` vs 브리프 760px | 컨테이너 폭 불일치 | 한 값으로 통일 후 전 화면 회귀 확인 |
| 전역 셀렉터 `* { box-sizing }`, `.app`, `.card`, `.btn`, `.field` 등 짧은 클래스명 | 기존 전역 스타일과 이름 충돌 | 프로젝트 네임스페이스(예: `.brf-` 접두) 또는 스코프 래퍼 적용 검토 |
| `.app::-webkit-scrollbar` 커스텀 | 기존 스크롤 영역에 전파 | `.app` 한정 유지 확인 |
| `@font-face ChosunSg` `url("fonts/ChosunSg.ttf")` 상대경로 | 정적 경로 불일치 시 폰트 미로딩 | `app/static/fonts/ChosunSg.ttf`로 경로 확정 + 파일 존재 확인 |
| `backdrop-filter`(appbar/toolbar) | 구형 브라우저 미지원 | 프로덕션은 toolbar 제거되므로 appbar만, 폴백 배경색 유지 |
| `.fade-in` 등장 애니메이션 | SSR 초기 페인트 깜빡임 | `prefers-reduced-motion` 분기 이미 포함 — 유지 |
| `system-ui` 한글 폰트 | OS별 한글 글꼴 차이 | 폴백에 `"Apple SD Gothic Neo","Malgun Gothic"` 이미 포함 — 유지 |

---

## 8. 실제 구현 전 확인할 데이터 / API 상태

마크업 이식과 별개로 백엔드 계약 확정이 필요한 항목.

| 확인 항목 | 질문 |
|-----------|------|
| 지원 종목 출처 | `SUPPORTED`(AAPL/TSLA/NVDA/MSFT/AMZN/GOOGL)가 하드코딩인지 설정/DB값인지 |
| 종목 데이터 스키마 | `{ name, sym, sentiment(enum), summary, audio_url, sources[] }` 필드 확정 — 특히 `sentiment`는 positive/neutral/negative 3값 enum |
| 오디오 URL | `audio_url` nullable 여부 → §6 조건부 렌더와 직결 |
| 출처 구조 | `sources[]`의 `{ title, host, url }` 확정, 외부 링크 `rel="noopener noreferrer"` 강제 |
| 캐시 정책 | `POST /search` 당일 캐시 hit/miss 분기 — 미스 시 로딩 화면 노출 트리거 |
| 로딩 소요 시간 | 파이프라인 즉석 실행 실제 지연 → 단계 표시(수집/요약/합성) 타이밍 현실화 |
| 오류 분기 | 미지원 종목 / 파이프라인 실패 / 브리핑 없음 각각의 HTTP 상태·메시지 매핑 |
| 날짜 | `id` 포맷 `YYYY-MM-DD`, "오늘" 판정 기준(서버 타임존) |
| **보안 (브리프 §12 절대 금지)** | NCP/CLOVA/Object Storage 키·DB 접속·SSH·개인정보·실금융데이터는 코드·템플릿·더미 어디에도 미포함. 비밀값은 `.env`만, git 커밋 금지 |

---

## 9. Claude Code에게 전달할 최종 요청문

> **목표**: 승인된 디자인 초안(`증시 브리핑 화면 초안.html` + `app.css`)을 서버 사이드 렌더링 프로덕션 화면으로 이식한다. 디자인 토큰·컴포넌트는 유지하고, 리뷰 전용 요소는 제거한다.
>
> **작업**
> 1. `app.css`를 `app/static/style.css`로 복사한다. `:root` CSS 변수, `.badge.s-*`, `.card`/`.zone`, `.player`/`.play-btn`, `.center-state`/`.spinner`/`.load-step`, `.sources`/`.source-list`, `.disclaimer`, `.app.is-mobile` 반응형 블록을 **값 변경 없이** 유지한다. 단 `.wrap`의 `max-width`는 **760px로 통일**한다.
> 2. 단일 HTML을 `list.html`(`GET /`)과 `detail.html`(`GET /briefing/{id}` + `POST /search` 재사용)로 분리한다.
> 3. 검색 폼은 `<form method="POST" action="/search">`로 바꾸고 JS `preventDefault`를 제거한다.
> 4. JS mock(`STOCKS`/`BRIEFINGS`/`SOURCES`/`SUPPORTED`)과 상태 머신(`S`, `render()`, 모든 `view*()` 함수)을 제거하고 Jinja2 `{% for %}` 루프 + `{{ }}` 변수로 치환한다.
> 5. 음성 플레이어의 JS 시뮬레이션을 제거하고 실제 `<audio src="{{ item.audio_url }}">`로 교체한다. `{% if item.audio_url %}`로 **오디오가 있을 때만** 플레이어를 렌더한다.
> 6. **제거**: 상단 툴바, 기기 프레임(`.device`/`.device-chrome`), 하단 `caption`, 모든 `데모/샘플` 배지·문구, 결과 카드 레이아웃 **B·C** 클래스. 레이아웃 **A(스택형)만** 남긴다.
> 7. `@font-face`의 `ChosunSg.ttf` 경로를 `app/static/fonts/ChosunSg.ttf`로 맞추고 파일 존재를 확인한다.
> 8. 오류는 미지원 종목·파이프라인 실패·브리핑 없음을 분기 처리하고, 기술 스택트레이스·에러코드를 화면에 노출하지 않는다. 외부 링크는 `rel="noopener noreferrer"`를 유지한다.
>
> **금지(브리프 §12)**: NCP/CLOVA/Object Storage 키, DB 접속정보, SSH 키, 개인정보, 실제 금융 데이터를 코드·템플릿·더미 어디에도 넣지 않는다. 비밀값은 `.env`로만 관리하고 커밋하지 않는다.
>
> **선확정 필요(§6)**: 오디오 없는 상태 UI, 404 전용 화면 분리 여부, 중립 배지(`#888`) 명도 대비 보강안 — 이 3건은 디자인 확정 후 진행한다.

---

*본 문서는 핸드오프 기준 정리용이며, 프로젝트 코드 수정은 포함하지 않습니다.*
