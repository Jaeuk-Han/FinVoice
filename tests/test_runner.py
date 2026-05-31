from pipeline import runner

def _patch_pipeline(monkeypatch, tts_raises=False):
    monkeypatch.setattr(runner.fetch, "fetch_symbol",
                        lambda symbol, limit=None: [{"title_en": "A", "body_en": "B", "url": "u",
                                                     "source_name": "Reuters", "url_hash": "h"}])
    monkeypatch.setattr(runner.translate, "translate_articles",
                        lambda arts: [dict(a, title_ko="가", body_ko="나") for a in arts])
    monkeypatch.setattr(runner.summarize, "summarize_symbol",
                        lambda company, arts: {"summary_ko": "요약", "sentiment": "positive"})
    if tts_raises:
        def boom(text, key): raise RuntimeError("tts down")
        monkeypatch.setattr(runner.tts, "synthesize_and_upload", boom)
    else:
        monkeypatch.setattr(runner.tts, "synthesize_and_upload",
                            lambda text, key: "https://cdn/a.mp3")

def test_process_symbol_full_success(monkeypatch):
    _patch_pipeline(monkeypatch)
    result = runner.process_symbol("AAPL", "Apple", "2026-05-31")
    assert result["summary_ko"] == "요약"
    assert result["sentiment"] == "positive"
    assert result["audio_url"] == "https://cdn/a.mp3"
    assert len(result["articles"]) == 1
    assert result["articles"][0]["title_ko"] == "가"

def test_process_symbol_tts_failure_is_graceful(monkeypatch):
    _patch_pipeline(monkeypatch, tts_raises=True)
    result = runner.process_symbol("AAPL", "Apple", "2026-05-31")
    assert result["audio_url"] is None      # 음성 없이도 결과 반환
    assert result["summary_ko"] == "요약"
