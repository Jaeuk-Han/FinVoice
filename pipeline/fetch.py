import hashlib
import httpx
from app import config

NEWS_API_BASE = "https://finnhub.io/api/v1"

def _call_news_api(symbol: str) -> list[dict]:
    """외부 금융뉴스 API 호출. 격리되어 테스트에서 mock 된다."""
    key = config.get_env("NEWS_API_KEY")
    # 최근 뉴스 조회 (날짜 범위는 호출 측에서 고정 기간 사용)
    url = f"{NEWS_API_BASE}/company-news"
    params = {"symbol": symbol, "from": "2026-05-24", "to": "2026-05-31", "token": key}
    resp = httpx.get(url, params=params, timeout=10.0)
    resp.raise_for_status()
    return resp.json()

def parse_articles(raw: list[dict]) -> list[dict]:
    out = []
    for r in raw:
        url = r.get("url", "")
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
        if a["url_hash"] in seen:
            continue
        seen.add(a["url_hash"])
        out.append(a)
    return out

def fetch_symbol(symbol: str, limit: int = None) -> list[dict]:
    limit = limit or config.ARTICLES_PER_SYMBOL
    raw = _call_news_api(symbol)
    articles = dedupe(parse_articles(raw))
    return articles[:limit]
