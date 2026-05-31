from pipeline import tts

def test_synthesize_and_upload_returns_url(monkeypatch):
    monkeypatch.setattr(tts, "_call_clova_voice", lambda text: b"FAKE_MP3")
    captured = {}
    def fake_upload(data, key):
        captured["data"] = data
        captured["key"] = key
        return f"https://cdn/{key}"
    monkeypatch.setattr(tts, "_upload_to_storage", fake_upload)
    url = tts.synthesize_and_upload("안녕하세요", "audio/2026-05-31/AAPL.mp3")
    assert url == "https://cdn/audio/2026-05-31/AAPL.mp3"
    assert captured["data"] == b"FAKE_MP3"

def test_synthesize_skips_empty(monkeypatch):
    monkeypatch.setattr(tts, "_call_clova_voice", lambda text: b"X")
    assert tts.synthesize_and_upload("", "k") is None
