import hashlib
from datetime import date, timedelta
import httpx
from app import config

NEWS_API_BASE = "https://finnhub.io/api/v1"

def _call_news_api(symbol: str) -> list[dict]:
    """외부 금융뉴스 API 호출. 격리되어 테스트에서 mock 된다."""
    key = config.get_env("NEWS_API_KEY")
    # 최근 뉴스 조회 (날짜 범위는 호출 측에서 고정 기간 사용)
    url = f"{NEWS_API_BASE}/company-news"
    today = date.today()
    params = {"symbol": symbol, "from": (today - timedelta(days=7)).isoformat(), "to": today.isoformat(), "token": key}
    resp = httpx.get(url, params=params, timeout=10.0)
    resp.raise_for_status()
    return resp.json()

def parse_articles(raw: list[dict]) -> list[dict]:
    out = []
    for r in raw:
        url = r.get("url", "")
        if not url.startswith(("http://", "https://")):
            url = ""
        out.append({
            "title_en": r.get("headline", ""),
            "url": url,
            "source_name": r.get("source", ""),
            "published_at": r.get("datetime"),
            "body_en": r.get("summary", ""),
            "url_hash": hashlib.sha256(url.encode()).hexdigest(),
        })
    return out

def dedupe(articles: list[dict]) -> list[dict]:
    seen = set()
    out = []
    for a in articles:
        if a.get("url_hash", "") in seen:
            continue
        seen.add(a.get("url_hash", ""))
        out.append(a)
    return out

def fetch_symbol(symbol: str, limit: int = None) -> list[dict]:
    if limit is None:
        limit = config.ARTICLES_PER_SYMBOL
    raw = _call_news_api(symbol)
    articles = dedupe(parse_articles(raw))
    return articles[:limit]


def get_quote(symbol: str) -> dict:
    """현재 주가 조회 (Finnhub /quote). 테스트에서 mock 된다."""
    key = config.get_env("NEWS_API_KEY")
    resp = httpx.get(f"{NEWS_API_BASE}/quote", params={"symbol": symbol, "token": key}, timeout=5.0)
    resp.raise_for_status()
    d = resp.json()
    return {"symbol": symbol, "price": d.get("c"), "change": d.get("d"), "change_pct": d.get("dp")}
