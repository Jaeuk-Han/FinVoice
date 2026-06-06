import json
import uuid
import httpx
from app import config

CLOVA_URL = "https://clovastudio.stream.ntruss.com/v1/chat-completions/HCX-003"
VALID_SENTIMENT = {"positive", "neutral", "negative"}

def build_prompt(company: str, articles: list[dict]) -> str:
    bullets = "\n".join(f"- {a.get('title_ko','')}: {a.get('body_ko','')}" for a in articles)
    return (
        f"다음은 '{company}' 관련 최신 뉴스 기사들이다.\n{bullets}\n\n"
        "위 기사 내용에서만 근거하여 작성하라. 기사에 없는 내용은 추측하지 마라.\n"
        "핵심 이슈를 한국어 3~5문장으로 요약하고, 전반적 시장 감성을 "
        "positive/neutral/negative 중 하나로 판단하라.\n"
        '반드시 JSON 형식으로만 답하라: {"summary": "...", "sentiment": "..."}'
    )

def _call_clova_studio(prompt: str) -> str:
    """CLOVA Studio 호출. 테스트에서 mock 된다. 반환은 모델 답변 문자열."""
    headers = {
        "Authorization": f"Bearer {config.get_env('CLOVA_STUDIO_API_KEY')}",
        "X-NCP-CLOVASTUDIO-REQUEST-ID": uuid.uuid4().hex,
        "Content-Type": "application/json",
    }
    body = {
        "messages": [
            {"role": "system", "content": "너는 금융 뉴스 요약 도우미다. 제공된 내용만 사용한다."},
            {"role": "user", "content": prompt},
        ],
        "maxTokens": 500,
        "temperature": 0.3,
    }
    resp = httpx.post(CLOVA_URL, headers=headers, json=body, timeout=30.0)
    resp.raise_for_status()
    return resp.json()["result"]["message"]["content"]

def _extract_json(text: str) -> dict:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        return {"summary": text.strip(), "sentiment": "neutral"}
    try:
        return json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return {"summary": text.strip(), "sentiment": "neutral"}

def summarize_symbol(company: str, articles: list[dict]) -> dict:
    raw = _call_clova_studio(build_prompt(company, articles))
    parsed = _extract_json(raw)
    sentiment = parsed.get("sentiment", "neutral")
    if sentiment not in VALID_SENTIMENT:
        sentiment = "neutral"
    return {"summary_ko": parsed.get("summary", "").strip(), "sentiment": sentiment}
