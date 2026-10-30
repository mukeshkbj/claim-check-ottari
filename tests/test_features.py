from claimcheck import agents, card, reports
from claimcheck.pipeline import link_in


def test_link_mode_only_for_a_bare_link():
    assert link_in("https://www.bbc.co.uk/news/articles/abc123") == "https://www.bbc.co.uk/news/articles/abc123"
    assert link_in("Is this true? https://example.com/story.") == "https://example.com/story"
    assert link_in("Crime is up 300% and the Eiffel Tower is in Berlin, see https://x.com/a/status/1 for the thread "
                   "my uncle shared yesterday") is None  # a real post that happens to contain a link
    assert link_in("two links https://a.com https://b.com") is None
    assert link_in("no link at all") is None


def _rep():
    return {"events": [
        {"type": "claims", "claims": [{"id": "c1", "text": "The Eiffel Tower is in Berlin", "language": "English"},
                                      {"id": "c2", "text": "It is the best monument"}]},
        {"type": "evidence", "claim_id": "c1", "research": {"evidence": [
            {"url": "https://en.wikipedia.org/wiki/Eiffel_Tower"}, {"url": "javascript:alert(1)"}]}},
        {"type": "verdict", "claim_id": "c1", "result": {"verdict": "False", "confidence": "high", "explanation": "Paris.",
                                                         "second_opinion": {"agree": True, "verdict": "False"}}},
        {"type": "verdict", "claim_id": "c2", "result": {"verdict": "Opinion"}},
    ]}


def test_summarize_rows_and_safe_sources():
    rows = reports.summarize(_rep())
    assert [r["verdict"] for r in rows] == ["False", "Opinion"]
    assert rows[0]["sources"] == ["https://en.wikipedia.org/wiki/Eiffel_Tower"]
    assert rows[0]["second"]["agree"] is True


def test_card_is_a_1200x630_png():
    from io import BytesIO
    from PIL import Image
    rows = reports.summarize(_rep()) * 3  # more than fits: must still render
    img = Image.open(BytesIO(card.render(rows, "claim-check.example")))
    assert img.size == (1200, 630) and img.format == "PNG"


def test_compare_flags_disagreement():
    assert agents.compare({"verdict": "False"}, {"verdict": "False"}, "m")["agree"] is True
    assert agents.compare({"verdict": "False"}, {"verdict": "Misleading"}, "m")["agree"] is False


def test_reply_uses_only_chosen_links_and_skips_opinions():
    import asyncio, json
    seen = {}

    class C:
        async def chat(self, role, model, messages, **k):
            seen["payload"] = json.loads(messages[1]["content"])
            return ("**Vaccines** don't cause autism: https://www.cdc.gov/a. --- Here's a fact check: https://junk.example/x "
                    "and more info: https://junk.example/y"), None

    rows = [{"text": "Vaccines cause autism", "verdict": "False", "sources": ["https://www.cdc.gov/a", "https://b"]},
            {"text": "5G spreads COVID", "verdict": "False", "sources": ["https://who.int/5g"]},
            {"text": "Best government ever", "verdict": "Opinion", "sources": []}]
    text, _ = asyncio.run(agents.draft_reply(C(), rows, "English"))
    assert seen["payload"]["links_you_may_use"] == ["https://www.cdc.gov/a", "https://who.int/5g"]
    assert [c["claim"] for c in seen["payload"]["claims"]] == ["Vaccines cause autism", "5G spreads COVID"]
    assert "junk.example" not in text and "---" not in text and "**" not in text
    assert "https://www.cdc.gov/a" in text and not text.rstrip().endswith(":")
    print(text)
