import pymysql
from app import config


def get_connection():
    """MySQL 연결 생성. 테스트에서는 호출하지 않는다."""
    return pymysql.connect(
        host=config.get_env("DB_HOST"),
        port=int(config.get_env("DB_PORT")),
        user=config.get_env("DB_USER"),
        password=config.get_env("DB_PASSWORD"),
        database=config.get_env("DB_NAME"),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )


def insert_briefing(cur, briefing_date, market_summary, market_audio_url) -> int:
    cur.execute(
        "INSERT INTO briefing (briefing_date, market_summary, market_audio_url) "
        "VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE "
        "market_summary=VALUES(market_summary), market_audio_url=VALUES(market_audio_url)",
        (briefing_date, market_summary, market_audio_url),
    )
    return cur.lastrowid


def insert_item(cur, briefing_id, symbol, company, summary_ko, sentiment,
                audio_url, item_date, source) -> int:
    cur.execute(
        "INSERT INTO briefing_item (briefing_id, symbol, company, summary_ko, "
        "sentiment, audio_url, item_date, source) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
        (briefing_id, symbol, company, summary_ko, sentiment, audio_url, item_date, source),
    )
    return cur.lastrowid


def insert_article(cur, item_id, art: dict):
    cur.execute(
        "INSERT INTO article (item_id, title_en, title_ko, url, source_name, url_hash) "
        "VALUES (%s,%s,%s,%s,%s,%s)",
        (item_id, art.get("title_en"), art.get("title_ko"), art.get("url"),
         art.get("source_name"), art.get("url_hash")),
    )


def find_cached_item(cur, symbol, item_date):
    cur.execute(
        "SELECT * FROM briefing_item WHERE symbol=%s AND item_date=%s LIMIT 1",
        (symbol, item_date),
    )
    return cur.fetchone()


def list_briefings(cur, limit=30):
    cur.execute("SELECT * FROM briefing ORDER BY briefing_date DESC LIMIT %s", (limit,))
    return cur.fetchall()


def get_briefing(cur, briefing_id):
    cur.execute("SELECT * FROM briefing WHERE id=%s", (briefing_id,))
    return cur.fetchone()


def get_items_for_briefing(cur, briefing_id):
    cur.execute("SELECT * FROM briefing_item WHERE briefing_id=%s ORDER BY symbol", (briefing_id,))
    return cur.fetchall()


def get_articles_for_item(cur, item_id):
    cur.execute("SELECT * FROM article WHERE item_id=%s", (item_id,))
    return cur.fetchall()
