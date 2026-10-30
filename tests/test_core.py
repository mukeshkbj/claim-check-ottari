"""Fast offline tests: no Otari calls."""
import time

from claimcheck import agents, memory
from claimcheck.otari import parse_json


def _mem(tmp_path, text, verdict="False"):
    m = memory.Memory(tmp_path / "m.json")
    m.items = [{"text": text, "emb": [1.0, 0.0], "verdict": {"verdict": verdict}, "research": {}, "ts": time.time()}]
    return m


def test_memory_reuses_same_wording(tmp_path):
    m = _mem(tmp_path, "The Eiffel Tower is in Berlin.")
    assert m.find("The Eiffel Tower is in Berlin", [1.0, 0.0])


def test_memory_never_reuses_different_place_or_negation(tmp_path):
    m = _mem(tmp_path, "The Eiffel Tower is in Berlin.")
    assert not m.find("The Eiffel Tower is in Paris.", [1.0, 0.0])
    assert not m.find("The Eiffel Tower is not in Berlin.", [1.0, 0.0])


def test_memory_never_reuses_different_numbers(tmp_path):
    m = _mem(tmp_path, "Apollo 11 landed on the Moon in 1969.")
    assert not m.find("Apollo 11 landed on the Moon in 1975.", [1.0, 0.0])


def test_memory_skips_old_entries(tmp_path):
    m = _mem(tmp_path, "The Eiffel Tower is in Berlin.")
    m.items[0]["ts"] -= 8 * 86400
    assert not m.find("The Eiffel Tower is in Berlin.", [1.0, 0.0])


def test_has_quantity():
    assert agents._has_quantity({"text": "Prices rose 40% last year"})
    assert not agents._has_quantity({"text": "The first Moon landing was in 1969."})


def test_parse_json_handles_fences():
    assert parse_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert parse_json('Sure! {"claims": []} hope that helps') == {"claims": []}


def test_memory_only_keeps_well_sourced_verdicts(tmp_path):
    m = memory.Memory(tmp_path / "m.json")
    one = {"evidence": [{"url": "https://a", "verified_url": True}]}
    two = {"evidence": [{"url": "https://a", "verified_url": True}, {"url": "https://b", "verified_url": True}]}
    m.add("Claim A", [1.0], {"verdict": "False"}, one)
    m.add("Claim B", [1.0], {"verdict": "Can't verify"}, two)
    assert m.items == []
    m.add("Claim C", [1.0], {"verdict": "False"}, two)
    assert len(m.items) == 1


def test_memory_ignores_a_file_that_is_not_a_list(tmp_path):
    p = tmp_path / "m.json"
    for content in ("{}", "42", '[{"text": "x"}, "junk"]'):
        p.write_text(content)
        m = memory.Memory(p)
        assert m.items == [] and m.find("anything", [1.0]) is None


def test_names_with_digits_are_not_quantities():
    for t in ("5G towers spread COVID", "COVID-19 came from a lab", "The G7 met in Italy", "Web3 is a scam"):
        assert not agents._has_quantity({"text": t, "figures": []}), t
    assert not agents._has_quantity({"text": "5G towers spread COVID", "figures": ["5G"]})
    assert agents._has_quantity({"text": "Crime in London is up 300% since 2019", "figures": ["300%", "2019"]})
