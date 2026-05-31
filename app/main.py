from datetime import date
from fastapi import FastAPI, Form, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app import db, config
from pipeline import runner

app = FastAPI(title="증시 브리핑")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

def get_conn():
    conn = db.get_connection()
    try:
        yield conn
    finally:
        conn.close()

# WATCHLIST 심볼 -> 회사명 매핑 (온디맨드 검증/회사명 조회용)
_COMPANY = {sym: name for sym, name in config.WATCHLIST}

@app.get("/", response_class=HTMLResponse)
def index(request: Request, conn=Depends(get_conn)):
    cur = conn.cursor()
    briefings = db.list_briefings(cur)
    return templates.TemplateResponse(request, "list.html", {"briefings": briefings})

@app.get("/briefing/{briefing_id}", response_class=HTMLResponse)
def briefing_detail(briefing_id: int, request: Request, conn=Depends(get_conn)):
    cur = conn.cursor()
    briefing = db.get_briefing(cur, briefing_id)
    if not briefing:
        raise HTTPException(404, "브리핑을 찾을 수 없습니다")
    items = db.get_items_for_briefing(cur, briefing_id)
    for item in items:
        item["articles"] = db.get_articles_for_item(cur, item["id"])
    return templates.TemplateResponse(request, "detail.html",
                                      {"briefing": briefing, "items": items})

@app.post("/search", response_class=HTMLResponse)
def search(request: Request, symbol: str = Form(...), conn=Depends(get_conn)):
    symbol = symbol.strip().upper()
    if symbol not in _COMPANY:
        raise HTTPException(400, f"지원하지 않는 종목입니다. 가능: {', '.join(_COMPANY)}")
    today = date.today().isoformat()
    cur = conn.cursor()

    item = db.find_cached_item(cur, symbol, today)
    if item:
        item = dict(item)
        if item.get("sentiment") not in {"positive", "neutral", "negative"}:
            item["sentiment"] = "neutral"
        item["articles"] = db.get_articles_for_item(cur, item["id"])
    else:
        result = runner.process_symbol(symbol, _COMPANY[symbol], today)
        item_id = db.insert_item(cur, None, symbol, _COMPANY[symbol], result["summary_ko"],
                                 result["sentiment"], result["audio_url"], today, "ondemand")
        for art in result["articles"]:
            db.insert_article(cur, item_id, art)
        conn.commit()
        item = {**result, "id": item_id, "articles": result["articles"]}

    briefing = {"briefing_date": f"{today} (검색: {symbol})"}
    return templates.TemplateResponse(request, "detail.html",
                                      {"briefing": briefing, "items": [item]})
