import httpx
from app import config

PAPAGO_URL = "https://naveropenapi.apigw.ntruss.com/nmt/v1/translation"

def _call_papago(text: str) -> str:
    """Papago 번역 호출. 테스트에서 mock 된다."""
    headers = {
        "X-NCP-APIGW-API-KEY-ID": config.get_env("NCP_APIGW_KEY_ID"),
        "X-NCP-APIGW-API-KEY": config.get_env("NCP_APIGW_KEY"),
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {"source": "en", "target": "ko", "text": text[:4500]}  # 글자 수 제한 보호
    resp = httpx.post(PAPAGO_URL, headers=headers, data=data, timeout=10.0)
    resp.raise_for_status()
    return resp.json()["message"]["result"]["translatedText"]

def translate_text(text: str) -> str:
    if not text or not text.strip():
        return text
    return _call_papago(text)

def translate_articles(articles: list[dict]) -> list[dict]:
    """각 dict를 제자리에서 변경(in-place mutation)하고 동일 리스트를 반환한다."""
    for a in articles:
        a["title_ko"] = translate_text(a.get("title_en", ""))
        a["body_ko"] = translate_text(a.get("body_en", ""))
    return articles
