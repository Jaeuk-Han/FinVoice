from pipeline import fetch

RAW = [
    {"headline": "Apple hits record", "url": "http://x.com/a", "source": "Reuters", "datetime": 1717000000, "summary": "body a"},
    {"headline": "Apple hits record", "url": "http://x.com/a", "source": "Reuters", "datetime": 1717000000, "summary": "body a"},  # 중복
    {"headline": "Apple new chip", "url": "http://x.com/b", "source": "CNBC", "datetime": 1717000100, "summary": "body b"},
]

def test_parse_articles_maps_fields():
    parsed = fetch.parse_articles(RAW)
    assert parsed[0]["title_en"] == "Apple hits record"
    assert parsed[0]["url"] == "http://x.com/a"
    assert parsed[0]["source_name"] == "Reuters"
    assert "url_hash" in parsed[0]

def test_dedupe_removes_same_url():
    parsed = fetch.parse_articles(RAW)
    deduped = fetch.dedupe(parsed)
    assert len(deduped) == 2

def test_fetch_symbol_uses_api_and_limits(monkeypatch):
    monkeypatch.setattr(fetch, "_call_news_api", lambda symbol: RAW)
    result = fetch.fetch_symbol("AAPL", limit=1)
    assert len(result) == 1
    assert result[0]["title_en"]
