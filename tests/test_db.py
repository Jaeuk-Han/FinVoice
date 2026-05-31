from app import db


class FakeCursor:
    def __init__(self, fetchone_result=None, fetchall_result=None):
        self.executed = []
        self._one = fetchone_result
        self._all = fetchall_result or []
        self.lastrowid = 42

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
