"""Accuracy benchmark: 20 well-established claims (10 true, 10 false) through the full Claim Check pipeline.

Run:  MEMORY_MIN_SIMILARITY=2 python scripts/benchmark.py   (memory off, so every claim is researched)
Writes BENCHMARK.md. Verdict mapping: Supported -> true; False/Misleading -> false; Unsupported/Can't verify -> abstain.
"""
import asyncio
import os
import statistics
import sys
import time
from pathlib import Path

os.environ.setdefault("MEMORY_MIN_SIMILARITY", "2")  # disable 'already checked' reuse for a fair benchmark
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from claimcheck.pipeline import run  # noqa: E402

CLAIMS = [
    ("The Eiffel Tower is in Paris.", True),
    ("Mount Everest is the highest mountain on Earth above sea level.", True),
    ("At sea level, water boils at 100 degrees Celsius.", True),
    ("The United Kingdom voted to leave the European Union in a 2016 referendum.", True),
    ("UK CPI inflation reached 11.1% in the 12 months to October 2022.", True),
    ("Canberra is the capital city of Australia.", True),
    ("Apollo 11 landed the first humans on the Moon in 1969.", True),
    ("The Amazon is the largest tropical rainforest in the world.", True),
    ("Mozilla released Firefox 1.0 in 2004.", True),
    ("The Pacific is the largest ocean on Earth.", True),
    ("The Eiffel Tower is in Berlin.", False),
    ("The Great Wall of China is visible from the Moon with the naked eye.", False),
    ("Sydney is the capital city of Australia.", False),
    ("Humans only use 10% of their brains.", False),
    ("Apollo 11 landed the first humans on the Moon in 1975.", False),
    ("At sea level, water boils at 50 degrees Celsius.", False),
    ("The United Kingdom voted to remain in the European Union in the 2016 referendum.", False),
    ("Mount Kilimanjaro is the highest mountain on Earth above sea level.", False),
    ("Lightning never strikes the same place twice.", False),
    ("The Pacific is the smallest ocean on Earth.", False),
]


async def one(claim: str, sem: asyncio.Semaphore) -> dict:
    async with sem:
        t0, cost, verdicts = time.time(), 0.0, []
        async for ev in run(claim):
            if ev["type"] == "step" and ev["step"].get("cost_usd"):
                cost += ev["step"]["cost_usd"]
            if ev["type"] == "verdict":
                verdicts.append(ev["result"].get("verdict", ""))
        return {"claim": claim, "verdict": verdicts[0] if verdicts else "(none)", "seconds": round(time.time() - t0, 1),
                "cost": cost}


def mapped(verdict: str):
    v = verdict.lower()
    if v.startswith("supported"):
        return True
    if v.startswith("false") or v.startswith("misleading"):
        return False
    return None


async def main() -> None:
    sem = asyncio.Semaphore(4)
    results = await asyncio.gather(*(one(c, sem) for c, _ in CLAIMS))
    rows, correct, answered = [], 0, 0
    for (claim, truth), r in zip(CLAIMS, results):
        pred = mapped(r["verdict"])
        ok = "abstained" if pred is None else ("✓" if pred == truth else "✗")
        answered += pred is not None
        correct += pred is not None and pred == truth
        rows.append(f"| {claim} | {'true' if truth else 'false'} | {r['verdict']} | {ok} | {r['seconds']} s | ${r['cost']:.4f} |")
    secs = [r["seconds"] for r in results]
    costs = [r["cost"] for r in results]
    md = f"""# Claim Check accuracy benchmark

Run on {time.strftime('%Y-%m-%d')} against hosted Otari (EU), with the 'already checked' memory turned off so every
claim was researched from scratch. 20 well-established claims: 10 true, 10 false.
Mapping: Supported = true; False or Misleading = false; Unsupported or Can't verify = abstained.

| Result | Value |
| --- | --- |
| Accuracy on answered claims | **{correct}/{answered}** ({(100 * correct / answered if answered else 0):.0f}%) |
| Abstained | {len(CLAIMS) - answered}/{len(CLAIMS)} |
| Median time per claim | {statistics.median(secs):.1f} s (4 run in parallel) |
| Average cost per claim | ${statistics.mean(costs):.4f} |
| Total cost | ${sum(costs):.4f} |

| Claim | Truth | Verdict | | Time | Cost |
| --- | --- | --- | --- | --- | --- |
""" + "\n".join(rows) + "\n\nRe-run with `python scripts/benchmark.py`.\n"
    Path(__file__).resolve().parents[1].joinpath("BENCHMARK.md").write_text(md, encoding="utf-8")
    print(md)


if __name__ == "__main__":
    asyncio.run(main())
