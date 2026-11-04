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
                                                         "jury": {"agree": 3, "total": 3, "unanimous": True, "contested": False, "votes": []}}},
        {"type": "verdict", "claim_id": "c2", "result": {"verdict": "Opinion"}},
    ]}


def test_summarize_rows_and_safe_sources():
    rows = reports.summarize(_rep())
    assert [r["verdict"] for r in rows] == ["False", "Opinion"]
    assert rows[0]["sources"] == ["https://en.wikipedia.org/wiki/Eiffel_Tower"]
    assert rows[0]["jury"]["unanimous"] is True


def test_card_is_a_1200x630_png():
    from io import BytesIO
    from PIL import Image
    rows = reports.summarize(_rep()) * 3  # more than fits: must still render
    img = Image.open(BytesIO(card.render(rows, "claim-check.example")))
    assert img.size == (1200, 630) and img.format == "PNG"


def test_jury_summary_counts_dissent_and_names_labs():
    from claimcheck.otari import Step
    votes = [({"verdict": "False"}, Step(role="juror", model_requested="mistralai/mistral-small-3.2-24b-instruct-2506")),
             ({"verdict": "Misleading"}, Step(role="juror", model_requested="google/gemma-3-27b-it")),
             ({"verdict": "Misleading"}, Step(role="juror", model_requested="meta/llama-3.3-70b-turbo"))]
    j = agents.jury_summary({"verdict": "False"}, votes)
    assert [v["lab"] for v in j["votes"]] == ["Mistral AI", "Google", "Meta"]
    assert (j["agree"], j["total"], j["unanimous"], j["contested"]) == (1, 3, False, True)
    assert agents.jury_summary({"verdict": "False"}, votes[:1])["unanimous"] is True


def test_locate_finds_the_claim_in_the_post():
    post = "Breaking: UK inflation hit 11.1% in October 2022, and the Great Wall is visible from the Moon!"
    a, b = agents.locate(post, "the Great Wall is visible from the Moon")
    assert post[a:b] == "the Great Wall is visible from the Moon"
    a, b = agents.locate(post, "nothing like it", "UK INFLATION hit 11.1% in October 2022")
    assert post[a:b] == "UK inflation hit 11.1% in October 2022"
    assert agents.locate(post, "a paraphrase that isn't there") is None


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


def test_rewrite_never_drops_the_posts_numbers():
    said = "Apollo 11 landed the first humans on the Moon in 1975"
    assert agents.keep_numbers("Apollo 11 landed the first humans on the Moon", said) == said
    assert agents.keep_numbers("UK inflation hit 11.1% in October 2022", "UK inflation hit 11.1% in October 2022") \
        == "UK inflation hit 11.1% in October 2022"
    assert agents.keep_numbers("Crime rose", "300%") == "Crime rose (300)"


def test_sandbox_rerun_confirms_or_flags_the_agents_result():
    import asyncio
    from claimcheck.otari import Step

    class C:
        def __init__(self, stdout): self.stdout = stdout
        async def execute_code(self, code):
            return {"stdout": self.stdout, "return_code": 0}, Step(role="sandbox re-run", model_requested="otari_code_execution")
    nums = {"applicable": True, "code": "print((1648-412)/412*100)", "result": "300%"}
    assert asyncio.run(agents.rerun_numbers(C("300.0\n"), nums))[0]["matches"] is True
    assert asyncio.run(agents.rerun_numbers(C("1,234.5\n"), nums))[0]["matches"] is False
    assert asyncio.run(agents.rerun_numbers(C("x"), {"applicable": False}))[0] is None


def test_ledger_reconciles_priced_calls_and_counts_unpriced_ones():
    import asyncio
    from claimcheck import pipeline

    class C:
        bills = {"a": "0.010000", "b": "0.002000", "c": "0.010000"}
        async def receipt(self, rid): return {"cost_usd": self.bills[rid]}
    events = [{"type": "step", "step": {"request_id": "a", "cost_usd": 0.01}},
              {"type": "step", "step": {"request_id": "b", "cost_usd": 0.002}},
              {"type": "step", "step": {"request_id": "c", "cost_usd": None}}]   # e.g. a sandbox re-run
    led = asyncio.run(pipeline._ledger(C(), events))
    assert (led["found"], led["billed_usd"], led["streamed_usd"], led["unpriced_in_stream"], led["matches"]) == (3, 0.022, 0.012, 1, True)
