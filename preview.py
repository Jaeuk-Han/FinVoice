"""DB·API 없이 템플릿 레이아웃을 확인하는 프리뷰 서버. 포트 8001.

새 템플릿 계약(list.html / detail.html)에 맞춘 컨텍스트를 넘긴다.
- list.html  : briefings, supported, today, error
- detail.html: briefing, items, is_search, supported, today

데모 상태 확인용 쿼리:
  GET /                  목록(브리핑 있음)
  GET /?empty=1          빈 상태(브리핑 없음)
  GET /?error=msg        오류 배너
  GET /briefing/{id}     날짜별 상세(시장요약 + 종목 카드)
  POST /search           검색 결과(단일 카드, is_search=True)
                         미지원 종목이면 오류 배너로 목록 재렌더
"""
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI()
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

TODAY = "2026-06-06"
SUPPORTED = ["AAPL", "TSLA", "NVDA", "MSFT", "AMZN", "GOOGL"]

# 프리뷰 음성 플레이어 확인용 데모 오디오 (실제 TTS 결과물 아님).
_SAMPLE_AUDIO = "/static/sample-briefing.wav"

_BRIEFINGS = [
    {"id": 1, "briefing_date": "2026-06-06",
     "market_summary": "오늘 시장은 기술주를 중심으로 강보합세를 보였습니다. 반도체·플랫폼 업종이 상대적 강세를, 일부 리테일 업종이 약세를 나타냈습니다."},
    {"id": 2, "briefing_date": "2026-06-05",
     "market_summary": "전일 시장은 보합권에서 등락을 반복했습니다. 실적 발표를 앞둔 종목들의 관망세가 짙었습니다."},
    {"id": 3, "briefing_date": "2026-06-04",
     "market_summary": "이틀 전 시장은 소폭 조정 흐름을 보였습니다. 차익 실현 매물이 출회되며 변동성이 다소 확대됐습니다."},
]

_ARTICLES = {
    "AAPL": [
        {"url": "https://example.com/1", "title_ko": "애플, 2분기 실적 시장 예상 상회", "title_en": None, "source_name": "Reuters"},
        {"url": "https://example.com/2", "title_ko": "애플 CEO, AI 전략 발표 예고", "title_en": None, "source_name": "Bloomberg"},
    ],
    "TSLA": [
        {"url": "https://example.com/3", "title_ko": "테슬라, 유럽 판매량 전월 대비 12% 감소", "title_en": None, "source_name": "WSJ"},
    ],
    "NVDA": [
        {"url": "https://example.com/4", "title_ko": "엔비디아 데이터센터 매출 전년 대비 3배 성장", "title_en": None, "source_name": "CNBC"},
        {"url": "https://example.com/5", "title_ko": "엔비디아, 블랙웰 GPU 공급 확대 발표", "title_en": None, "source_name": "Reuters"},
    ],
    "MSFT": [
        {"url": "https://example.com/6", "title_ko": "마이크로소프트 애저 클라우드 점유율 확대", "title_en": None, "source_name": "Forbes"},
    ],
    "AMZN": [
        {"url": "https://example.com/7", "title_ko": "아마존, 물류 자동화 투자 확대 발표", "title_en": None, "source_name": "Bloomberg"},
    ],
    "GOOGL": [
        {"url": "https://example.com/8", "title_ko": "구글, 광고 수익 회복세…유튜브 성장 견인", "title_en": None, "source_name": "FT"},
    ],
}

_ITEMS = [
    {"id": 1, "symbol": "AAPL", "company": "Apple Inc.", "sentiment": "positive",
     "summary_ko": "애플은 이번 2분기 시장 예상치를 상회하는 실적을 기록했습니다. 서비스 부문 매출이 전년 대비 두 자릿수 성장하며 전체 실적을 견인했고, 다음 달 AI 전략 발표를 예고했습니다.",
     "audio_url": _SAMPLE_AUDIO, "articles": _ARTICLES["AAPL"]},
    {"id": 2, "symbol": "TSLA", "company": "Tesla Inc.", "sentiment": "negative",
     "summary_ko": "테슬라의 유럽 시장 판매량이 전월 대비 12% 감소한 것으로 나타났습니다. 현지 경쟁 심화와 보조금 축소가 주요 원인으로 분석됩니다.",
     "audio_url": None, "articles": _ARTICLES["TSLA"]},  # 오디오 없음(플레이어 숨김) 상태 확인용
    {"id": 3, "symbol": "NVDA", "company": "NVIDIA Corp.", "sentiment": "positive",
     "summary_ko": "엔비디아의 데이터센터 부문 매출이 전년 동기 대비 크게 성장했습니다. 차세대 GPU 공급 확대 발표와 함께 AI 인프라 투자 수요가 지속되고 있습니다.",
     "audio_url": _SAMPLE_AUDIO, "articles": _ARTICLES["NVDA"]},
    {"id": 4, "symbol": "MSFT", "company": "Microsoft Corp.", "sentiment": "neutral",
     "summary_ko": "마이크로소프트 애저의 클라우드 점유율이 소폭 확대됐습니다. 기업용 AI 구독 전환이 순조롭게 진행 중이나 단기 설비 투자 확대로 마진 압박 우려도 제기됩니다.",
     "audio_url": None, "articles": _ARTICLES["MSFT"]},  # 오디오 없음(플레이어 숨김) 상태 확인용
    {"id": 5, "symbol": "AMZN", "company": "Amazon.com Inc.", "sentiment": "positive",
     "summary_ko": "아마존이 물류 자동화 인프라에 대규모 투자를 발표했습니다. 클라우드 성장세 지속과 함께 광고 부문도 호조를 보이며 실적 개선 기대감이 높아지고 있습니다.",
     "audio_url": _SAMPLE_AUDIO, "articles": _ARTICLES["AMZN"]},
    {"id": 6, "symbol": "GOOGL", "company": "Alphabet Inc.", "sentiment": "positive",
     "summary_ko": "구글의 광고 수익이 회복세로 전환됐습니다. 동영상 광고 매출이 견조하게 증가했으며, AI 통합 검색 서비스 확대가 장기 성장 동력으로 평가받고 있습니다.",
     "audio_url": _SAMPLE_AUDIO, "articles": _ARTICLES["GOOGL"]},
]

_COMPANY = {
    "AAPL": "Apple Inc.", "TSLA": "Tesla Inc.", "NVDA": "NVIDIA Corp.",
    "MSFT": "Microsoft Corp.", "AMZN": "Amazon.com Inc.", "GOOGL": "Alphabet Inc.",
}


def _list_ctx(briefings, error=None):
    return {"briefings": briefings, "supported": SUPPORTED, "today": TODAY, "error": error}


@app.get("/", response_class=HTMLResponse)
def index(request: Request, empty: int = 0, error: str | None = None):
    briefings = [] if empty else _BRIEFINGS
    return templates.TemplateResponse(request, "list.html", _list_ctx(briefings, error))


@app.get("/briefing/{briefing_id}", response_class=HTMLResponse)
def briefing_detail(briefing_id: int, request: Request):
    briefing = next((b for b in _BRIEFINGS if b["id"] == briefing_id), _BRIEFINGS[0])
    return templates.TemplateResponse(request, "detail.html", {
        "briefing": briefing, "items": _ITEMS,
        "is_search": False, "supported": SUPPORTED, "today": TODAY,
    })


@app.post("/search", response_class=HTMLResponse)
def search(request: Request, symbol: str = Form(...)):
    symbol = symbol.strip().upper()
    if symbol not in _COMPANY:
        return templates.TemplateResponse(
            request, "list.html",
            _list_ctx(_BRIEFINGS, f"지원하지 않는 종목입니다. 지원 종목: {', '.join(SUPPORTED)}"),
            status_code=400,
        )
    item = next((i for i in _ITEMS if i["symbol"] == symbol), _ITEMS[0])
    briefing = {"briefing_date": TODAY, "market_summary": None}
    return templates.TemplateResponse(request, "detail.html", {
        "briefing": briefing, "items": [item],
        "is_search": True, "supported": SUPPORTED, "today": TODAY,
    })


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("preview:app", host="0.0.0.0", port=8001, reload=True)
