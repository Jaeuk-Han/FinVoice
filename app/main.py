from datetime import date

from fastapi import FastAPI, Form, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import db, config
from pipeline import runner

app = FastAPI(title="증시 브리핑")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

_COMPANY = {sym: name for sym, name in config.WATCHLIST}
SUPPORTED = list(_COMPANY.keys())


def get_conn():
    conn = db.get_connection()
    try:
        yield conn
    finally:
        conn.close()


@app.exception_handler(StarletteHTTPException)
async def html_exception_handler(request: Request, exc: StarletteHTTPException):
    msg = exc.detail or "오류가 발생했습니다. 잠시 후 다시 시도해주세요."
    return templates.TemplateResponse(
        request, "list.html",
        {"briefings": [], "supported": SUPPORTED, "today": date.today().isoformat(), "error": msg},
        status_code=exc.status_code,
    )


@app.get("/", response_class=HTMLResponse)
def index(request: Request, conn=Depends(get_conn)):
    today = date.today().isoformat()
    cur = conn.cursor()
    briefings = db.list_briefings(cur)
    return templates.TemplateResponse(request, "list.html", {
        "briefings": briefings,
        "supported": SUPPORTED,
        "today": today,
        "error": None,
    })


@app.get("/briefing/{briefing_id}", response_class=HTMLResponse)
def briefing_detail(briefing_id: int, request: Request, conn=Depends(get_conn)):
    today = date.today().isoformat()
    cur = conn.cursor()
    briefing = db.get_briefing(cur, briefing_id)
    if not briefing:
        raise HTTPException(404, "브리핑을 찾을 수 없습니다")
    items = db.get_items_for_briefing(cur, briefing_id)
    for item in items:
        item["articles"] = db.get_articles_for_item(cur, item["id"])
    return templates.TemplateResponse(request, "detail.html", {
        "briefing": briefing,
        "items": items,
        "is_search": False,
        "supported": SUPPORTED,
        "today": today,
    })


@app.post("/search", response_class=HTMLResponse)
def search(request: Request, symbol: str = Form(...), conn=Depends(get_conn)):
    today = date.today().isoformat()
    symbol = symbol.strip().upper()
    cur = conn.cursor()

    if symbol not in _COMPANY:
        briefings = db.list_briefings(cur)
        return templates.TemplateResponse(
            request, "list.html",
            {
                "briefings": briefings,
                "supported": SUPPORTED,
                "today": today,
                "error": f"지원하지 않는 종목입니다. 지원 종목: {', '.join(SUPPORTED)}",
            },
            status_code=400,
        )

    item = db.find_cached_item(cur, symbol, today)
    if item:
        item = dict(item)
        if item.get("sentiment") not in {"positive", "neutral", "negative"}:
            item["sentiment"] = "neutral"
        item["articles"] = db.get_articles_for_item(cur, item["id"])
    else:
        try:
            result = runner.process_symbol(symbol, _COMPANY[symbol], today)
        except Exception:
            briefings = db.list_briefings(cur)
            return templates.TemplateResponse(
                request, "list.html",
                {
                    "briefings": briefings,
                    "supported": SUPPORTED,
                    "today": today,
                    "error": "요약 생성에 실패했습니다. 잠시 후 다시 시도해주세요.",
                },
                status_code=500,
            )
        item_id = db.insert_item(
            cur, None, symbol, _COMPANY[symbol],
            result["summary_ko"], result["sentiment"], result["audio_url"],
            today, "ondemand",
        )
        for art in result["articles"]:
            db.insert_article(cur, item_id, art)
        conn.commit()
        item = {**result, "id": item_id, "articles": result["articles"]}

    briefing = {"briefing_date": today, "market_summary": None}
    return templates.TemplateResponse(request, "detail.html", {
        "briefing": briefing,
        "items": [item],
        "is_search": True,
        "supported": SUPPORTED,
        "today": today,
    })
