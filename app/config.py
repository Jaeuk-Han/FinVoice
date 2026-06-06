import os
from dotenv import load_dotenv

load_dotenv()

# 고정 관심종목 (symbol, 회사명)
WATCHLIST = [
    ("AAPL", "Apple"),
    ("TSLA", "Tesla"),
    ("NVDA", "NVIDIA"),
    ("MSFT", "Microsoft"),
    ("AMZN", "Amazon"),
    ("GOOGL", "Alphabet"),
]

# 종목별 로고 도메인 (Clearbit Logo API용)
LOGO_DOMAINS: dict[str, str] = {
    "AAPL": "apple.com",
    "TSLA": "tesla.com",
    "NVDA": "nvidia.com",
    "MSFT": "microsoft.com",
    "AMZN": "amazon.com",
    "GOOGL": "google.com",
}

# 수집 파라미터
ARTICLES_PER_SYMBOL = 5
MARKET_ARTICLE_COUNT = 8

def get_env(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise RuntimeError(f"환경변수 {key} 가 설정되지 않았거나 빈 값입니다. .env 를 확인하세요.")
    return value


def get_env_or(key: str, *fallback_keys: str) -> str:
    """key 를 우선 조회하고, 비어있으면 fallback_keys 순서로 조회한다.
    모두 비어있으면 에러. (예: 음성 전용 키가 없으면 공용 APIGW 키로 폴백)"""
    for k in (key, *fallback_keys):
        value = os.getenv(k)
        if value:
            return value
    tried = ", ".join((key, *fallback_keys))
    raise RuntimeError(f"환경변수 {tried} 중 설정된 값이 없습니다. .env 를 확인하세요.")
