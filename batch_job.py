import logging
import sys
from datetime import date
from app import config, db
from pipeline import runner

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("batch")

def run_batch(conn, item_date: str) -> tuple[int, int]:
    cur = conn.cursor()
    briefing_id = db.insert_briefing(cur, item_date, market_summary=None, market_audio_url=None)
    ok = failed = 0
    for symbol, company in config.WATCHLIST:
        try:
            result = runner.process_symbol(symbol, company, item_date)
            item_id = db.insert_item(
                cur, briefing_id, symbol, company, result["summary_ko"],
                result["sentiment"], result["audio_url"], item_date, "batch")
            for art in result["articles"]:
                db.insert_article(cur, item_id, art)
            conn.commit()
            ok += 1
            log.info("처리 완료: %s", symbol)
        except Exception as e:
            failed += 1
            log.error("처리 실패 %s: %s", symbol, e)
    return ok, failed

def main():
    item_date = date.today().isoformat()
    conn = db.get_connection()
    try:
        ok, failed = run_batch(conn, item_date)
        log.info("배치 종료: 성공 %d, 실패 %d", ok, failed)
    finally:
        conn.close()

if __name__ == "__main__":
    sys.exit(main())
