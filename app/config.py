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

# 수집 파라미터
ARTICLES_PER_SYMBOL = 5
MARKET_ARTICLE_COUNT = 8

def get_env(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise RuntimeError(f"환경변수 {key} 가 설정되지 않았습니다. .env 를 확인하세요.")
    return value
