from datetime import datetime

from app import db


class FakeCursor:
    def __init__(self, fetchone_result=None, fetchall_result=None, lastrowid=42):
        self.executed = []
        self._one = fetchone_result
        self._all = fetchall_result or []
        self.lastrowid = lastrowid

    def execute(self, sql, params=None):
        self.executed.append((sql, params))

    def fetchone(self):
        return self._one

    def fetchall(self):
        return self._all


def test_insert_item_returns_lastrowid():
    cur = FakeCursor()
    new_id = db.insert_item(cur, briefing_id=1, symbol="AAPL", company="Apple",
                            summary_ko="요약", sentiment="positive",
                            audio_url="http://a", item_date="2026-05-31", source="batch")
    assert new_id == 42
    assert "INSERT INTO briefing_item" in cur.executed[0][0]


def test_find_cached_item_returns_row():
    row = {"id": 7, "symbol": "AAPL", "summary_ko": "요약"}
    cur = FakeCursor(fetchone_result=row)
    result = db.find_cached_item(cur, "AAPL", "2026-05-31")
    assert result == row
    assert "WHERE symbol" in cur.executed[0][0]


# --- TDD: insert_article published_at ---

def test_insert_article_persists_published_at():
    art = {
        "item_id": None,
        "title_en": "T",
        "title_ko": "ㅌ",
        "url": "u",
        "source_name": "Reuters",
        "published_at": 1717000000,
        "url_hash": "h",
    }
    cur = FakeCursor()
    db.insert_article(cur, item_id=5, art=art)
    sql, params = cur.executed[0]
    assert "published_at" in sql
    # The epoch must have been converted to a datetime, not passed as a raw int
    assert any(isinstance(p, datetime) for p in params), (
        f"Expected a datetime in params, got: {params}"
    )


# --- TDD: insert_briefing lastrowid=0 fallback ---

def test_insert_briefing_returns_lastrowid():
    cur = FakeCursor(lastrowid=42)
    result = db.insert_briefing(cur, "2026-05-31", None, None)
    assert result == 42
    assert "ON DUPLICATE KEY" in cur.executed[0][0]


def test_insert_briefing_falls_back_when_lastrowid_zero():
    cur = FakeCursor(fetchone_result={"id": 77}, lastrowid=0)
    result = db.insert_briefing(cur, "2026-05-31", None, None)
    assert result == 77
    # A SELECT against briefing must have been issued as fallback
    selects = [sql for sql, _ in cur.executed if sql.strip().upper().startswith("SELECT")]
    assert selects, "Expected a SELECT fallback query when lastrowid is 0"
    assert "briefing" in selects[0]
