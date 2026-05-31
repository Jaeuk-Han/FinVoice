import logging
from pipeline import fetch, translate, summarize, tts

log = logging.getLogger("pipeline")

def process_symbol(symbol: str, company: str, item_date: str) -> dict:
    """한 종목 처리. fetch/translate/summarize 실패는 예외 전파(호출측 skip),
    tts 실패는 audio_url=None 으로 graceful degradation."""
    articles = fetch.fetch_symbol(symbol)
    articles = translate.translate_articles(articles)
    summary = summarize.summarize_symbol(company, articles)

    audio_url = None
    try:
        key = f"audio/{item_date}/{symbol}.mp3"
        audio_url = tts.synthesize_and_upload(summary["summary_ko"], key)
    except Exception as e:  # TTS 실패는 비치명적
        log.warning("TTS 실패 %s: %s", symbol, e, exc_info=True)

    return {
        "symbol": symbol,
        "company": company,
        "summary_ko": summary["summary_ko"],
        "sentiment": summary["sentiment"],
        "audio_url": audio_url,
        "articles": articles,
    }
