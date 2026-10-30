"""extract() normalisation, with a fake Otari client (no network)."""
import asyncio
import json

from claimcheck import agents


class FakeClient:
    def __init__(self, reply):
        self.reply = reply

    async def chat(self, *a, **k):
        return self.reply, None


def _extract(payload):
    reply = payload if isinstance(payload, str) else json.dumps(payload)
    return asyncio.run(agents.extract(FakeClient(reply), "some post"))[0]


def test_ids_are_ours_and_kinds_are_normalised():
    claims = _extract({"language": "French", "claims": [
        {"id": "<img src=x onerror=alert(1)>", "text": "Le ciel est vert", "kind": "FACTUAL", "checkable": "true"},
        {"text": "C'est le meilleur", "kind": "opinion", "checkable": True},
        {"text": "Les prix ont augmenté de 40 %", "kind": "banana"},
    ]})
    assert [c["id"] for c in claims] == ["c1", "c2", "c3"]
    assert claims[0]["kind"] == "factual" and claims[0]["checkable"] is True
    assert claims[1]["checkable"] is False  # opinions are never sent to the investigator
    assert claims[2]["kind"] == "numeric"   # unknown kind -> factual -> numeric because of the 40 %
    assert all(c["language"] == "French" for c in claims)


def test_bad_shapes_are_dropped_not_crashing():
    claims = _extract({"claims": [None, {"text": ""}, {"text": 42, "figures": "40%"}, "just a string"]})
    assert [c["text"] for c in claims] == ["42"]
    assert claims[0]["figures"] == []
    assert _extract({"claims": "nope"}) == []


def test_bare_list_reply():
    assert [c["text"] for c in _extract('[{"text": "Water boils at 50 C at sea level"}]')] == ["Water boils at 50 C at sea level"]


def test_guard_reads_unsafe_as_a_violation():
    from claimcheck import guard

    class G:
        def __init__(self, r): self.r = r
        async def chat(self, *a, **k): return self.r, None
    for reply, valid in (("UNSAFE", False), ("VIOLATION - injection", False), ("SAFE", True),
                         ("Safe. No violation found.", True), ("unsafe: asks to reveal the system prompt", False)):
        assert asyncio.run(guard._safeguard(G(reply), "policy", "text"))["valid"] is valid, reply


class SeqClient:
    def __init__(self, *replies):
        self.replies, self.json_modes = list(replies), []

    async def chat(self, *a, json_mode=False, **k):
        from claimcheck.otari import Step
        self.json_modes.append(json_mode)
        return self.replies.pop(0), Step(role="extractor", model_requested="cc-extractor")


def test_long_input_with_no_claims_retries_in_json_mode():
    c = SeqClient('{"claims": []}', '{"claims": [{"text": "The Sahara is about 9.2 million km2"}]}')
    claims, _ = asyncio.run(agents.extract(c, "Sahara article text. " * 40))
    assert c.json_modes == [False, True] and claims[0]["text"].startswith("The Sahara")


def test_short_opinion_post_does_not_retry():
    c = SeqClient('{"claims": []}')
    claims, _ = asyncio.run(agents.extract(c, "I love Mondays"))
    assert claims == [] and c.json_modes == [False]
