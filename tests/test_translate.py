from pipeline import translate

def test_translate_text_returns_translation(monkeypatch):
    monkeypatch.setattr(translate, "_call_papago", lambda text: "사과 주가 사상 최고")
    assert translate.translate_text("Apple hits record") == "사과 주가 사상 최고"

def test_translate_text_skips_empty(monkeypatch):
    called = {"n": 0}
    def fake(text):
        called["n"] += 1
        return "x"
    monkeypatch.setattr(translate, "_call_papago", fake)
    assert translate.translate_text("") == ""
    assert translate.translate_text("   ") == "   "
    assert called["n"] == 0

def test_translate_articles_fills_title_ko(monkeypatch):
    monkeypatch.setattr(translate, "_call_papago", lambda text: "번역됨")
    arts = [{"title_en": "A", "body_en": "B"}]
    out = translate.translate_articles(arts)
    assert out[0]["title_ko"] == "번역됨"
    assert out[0]["body_ko"] == "번역됨"
