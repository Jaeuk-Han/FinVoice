from pipeline import summarize

ARTS = [
    {"title_ko": "사과 신고가", "body_ko": "실적 호조"},
    {"title_ko": "사과 신제품", "body_ko": "아이폰 출시"},
]

def test_build_prompt_includes_guardrail_and_articles():
    prompt = summarize.build_prompt("Apple", ARTS)
    assert "추측" in prompt  # "추측 금지" 가드레일
    assert "사과 신고가" in prompt

def test_summarize_symbol_parses_response(monkeypatch):
    fake = '{"summary": "애플은 실적 호조로 신고가를 기록했다.", "sentiment": "positive"}'
    monkeypatch.setattr(summarize, "_call_clova_studio", lambda prompt: fake)
    result = summarize.summarize_symbol("Apple", ARTS)
    assert result["summary_ko"].startswith("애플")
    assert result["sentiment"] == "positive"

def test_summarize_symbol_defaults_neutral_on_bad_sentiment(monkeypatch):
    fake = '{"summary": "요약", "sentiment": "weird"}'
    monkeypatch.setattr(summarize, "_call_clova_studio", lambda prompt: fake)
    result = summarize.summarize_symbol("Apple", ARTS)
    assert result["sentiment"] == "neutral"
