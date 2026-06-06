import os
import time
from datetime import date

from fastapi import FastAPI, Form, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.sessions import SessionMiddleware

from app import db, auth, config
from pipeline import runner
from pipeline import fetch as _fetch_module
from pipeline.fetch import get_quote

app = FastAPI(title="FinVoice")
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET", "dev-secret-change-in-prod"),
)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

_COMPANY = {sym: name for sym, name in config.WATCHLIST}
SUPPORTED = list(_COMPANY.keys())

templates.env.globals["LOGO_DOMAINS"] = config.LOGO_DOMAINS
templates.env.globals["WATCHLIST_META"] = [
    {"sym": sym, "company": name, "domain": config.LOGO_DOMAINS.get(sym, "")}
    for sym, name in config.WATCHLIST
]

_quote_cache: dict = {}
_CACHE_TTL = 60


def get_conn():
    conn = db.get_connection()
    try:
        yield conn
    finally:
        conn.close()


def _current_user_id(request: Request):
    return request.session.get("user_id")


@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return templates.TemplateResponse(request, "register.html", {"error": None})


@app.post("/register", response_class=HTMLResponse)
def register(request: Request, email: str = Form(...), password: str = Form(...), conn=Depends(get_conn)):
    cur = conn.cursor()
    if db.get_user_by_email(cur, email):
        return templates.TemplateResponse(request, "register.html", {"error": "이미 사용 중인 이메일입니다."}, status_code=400)
    db.create_user(cur, email, auth.hash_password(password))
    conn.commit()
    return RedirectResponse("/login", status_code=303)


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html", {"error": None})


@app.post("/login", response_class=HTMLResponse)
def login(request: Request, email: str = Form(...), password: str = Form(...), conn=Depends(get_conn)):
    cur = conn.cursor()
    user = db.get_user_by_email(cur, email)
    if not user or not auth.verify_password(password, user["password_hash"]):
        return templates.TemplateResponse(request, "login.html", {"error": "이메일 또는 비밀번호가 올바르지 않습니다."}, status_code=401)
    request.session["user_id"] = user["id"]
    request.session["user_email"] = user["email"]
    return RedirectResponse("/", status_code=303)


@app.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=303)


@app.get("/watchlist/edit", response_class=HTMLResponse)
def watchlist_edit_page(request: Request, conn=Depends(get_conn)):
    user_id = _current_user_id(request)
    if not user_id:
        return RedirectResponse("/login", status_code=303)
    cur = conn.cursor()
    watchlist = db.get_watchlist(cur, user_id)
    return templates.TemplateResponse(request, "watchlist_edit.html", {
        "watchlist": watchlist,
        "user_email": request.session.get("user_email"),
        "error": None,
    })


@app.post("/watchlist/edit", response_class=HTMLResponse)
def watchlist_edit_save(request: Request, symbols: str = Form(default=""), conn=Depends(get_conn)):
    user_id = _current_user_id(request)
    if not user_id:
        return RedirectResponse("/login", status_code=303)

    raw = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    raw = list(dict.fromkeys(raw))[:5]

    pairs = []
    errors = []
    for sym in raw:
        if sym in _COMPANY:
            pairs.append((sym, _COMPANY[sym]))
        else:
            name = _fetch_module.lookup_company(sym)
            if name:
                pairs.append((sym, name))
            else:
                errors.append(sym)

    if errors:
        cur = conn.cursor()
        watchlist = db.get_watchlist(cur, user_id)
        return templates.TemplateResponse(request, "watchlist_edit.html", {
            "watchlist": watchlist,
            "user_email": request.session.get("user_email"),
            "error": f"존재하지 않는 종목: {', '.join(errors)}",
        }, status_code=400)

    cur = conn.cursor()
    db.save_watchlist(cur, user_id, pairs)
    conn.commit()
    return RedirectResponse("/", status_code=303)


@app.exception_handler(StarletteHTTPException)
async def html_exception_handler(request: Request, exc: StarletteHTTPException):
    msg = exc.detail or "오류가 발생했습니다. 잠시 후 다시 시도해주세요."
    return templates.TemplateResponse(
        request, "list.html",
        {
            "briefings": [], "supported": SUPPORTED, "today": date.today().isoformat(),
            "error": msg,
            "user_email": request.session.get("user_email"),
            "watchlist_meta": list(templates.env.globals["WATCHLIST_META"]),
        },
        status_code=exc.status_code,
    )


@app.get("/api/quotes")
def api_quotes(symbols: str = ""):
    sym_list = [s.strip().upper() for s in symbols.split(",") if s.strip()] if symbols else SUPPORTED
    now = time.time()
    results = []
    for sym in sym_list:
        cached = _quote_cache.get(sym)
        if cached and now - cached["ts"] < _CACHE_TTL:
            results.append(cached["data"])
            continue
        try:
            q = get_quote(sym)
            _quote_cache[sym] = {"ts": now, "data": q}
            results.append(q)
        except Exception:
            results.append({"symbol": sym, "price": None, "change": None, "change_pct": None})
    return JSONResponse(results)


@app.get("/", response_class=HTMLResponse)
def index(request: Request, conn=Depends(get_conn)):
    today = date.today().isoformat()
    cur = conn.cursor()
    briefings = db.list_briefings(cur)
    user_id = _current_user_id(request)
    if user_id:
        rows = db.get_watchlist(cur, user_id)
        watchlist_meta = [
            {"sym": r["symbol"], "company": r["company"],
             "domain": config.LOGO_DOMAINS.get(r["symbol"], "")}
            for r in rows
        ] or list(templates.env.globals["WATCHLIST_META"])
    else:
        watchlist_meta = list(templates.env.globals["WATCHLIST_META"])
    return templates.TemplateResponse(request, "list.html", {
        "briefings": briefings,
        "supported": SUPPORTED,
        "today": today,
        "error": None,
        "user_email": request.session.get("user_email"),
        "watchlist_meta": watchlist_meta,
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
        "user_email": request.session.get("user_email"),
    })


@app.post("/search", response_class=HTMLResponse)
def search(request: Request, symbol: str = Form(...), conn=Depends(get_conn)):
    today = date.today().isoformat()
    symbol = symbol.strip().upper()
    cur = conn.cursor()
    user_id = _current_user_id(request)
    user_email = request.session.get("user_email")
    default_wl = list(templates.env.globals["WATCHLIST_META"])

    # 심볼 유효성: 비로그인 → WATCHLIST만, 로그인 → Finnhub profile 조회
    if symbol in _COMPANY:
        company_name = _COMPANY[symbol]
    elif user_id:
        company_name = _fetch_module.lookup_company(symbol)
        if not company_name:
            briefings = db.list_briefings(cur)
            return templates.TemplateResponse(request, "list.html", {
                "briefings": briefings, "supported": SUPPORTED, "today": today,
                "error": f"존재하지 않는 종목입니다: {symbol}",
                "user_email": user_email, "watchlist_meta": default_wl,
            }, status_code=400)
    else:
        briefings = db.list_briefings(cur)
        return templates.TemplateResponse(request, "list.html", {
            "briefings": briefings, "supported": SUPPORTED, "today": today,
            "error": f"지원하지 않는 종목입니다. 지원 종목: {', '.join(SUPPORTED)}",
            "user_email": user_email, "watchlist_meta": default_wl,
        }, status_code=400)

    item = db.find_cached_item(cur, symbol, today)
    if item:
        item = dict(item)
        if item.get("sentiment") not in {"positive", "neutral", "negative"}:
            item["sentiment"] = "neutral"
        item["articles"] = db.get_articles_for_item(cur, item["id"])
    else:
        try:
            result = runner.process_symbol(symbol, company_name, today)
        except Exception:
            briefings = db.list_briefings(cur)
            return templates.TemplateResponse(request, "list.html", {
                "briefings": briefings, "supported": SUPPORTED, "today": today,
                "error": "요약 생성에 실패했습니다. 잠시 후 다시 시도해주세요.",
                "user_email": user_email, "watchlist_meta": default_wl,
            }, status_code=500)
        item_id = db.insert_item(
            cur, None, symbol, company_name,
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
        "user_email": user_email,
    })
