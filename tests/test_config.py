from app import config

def test_watchlist_is_fixed_nonempty_list():
    assert isinstance(config.WATCHLIST, list)
    assert 5 <= len(config.WATCHLIST) <= 8
    # 각 항목은 (symbol, company) 튜플
    for symbol, company in config.WATCHLIST:
        assert symbol and company

def test_env_helper_reads_value(monkeypatch):
    monkeypatch.setenv("NEWS_API_KEY", "abc123")
    assert config.get_env("NEWS_API_KEY") == "abc123"

def test_env_helper_raises_when_missing(monkeypatch):
    monkeypatch.delenv("DEFINITELY_MISSING", raising=False)
    import pytest
    with pytest.raises(RuntimeError):
        config.get_env("DEFINITELY_MISSING")
