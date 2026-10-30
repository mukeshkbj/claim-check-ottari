"""'Already checked' memory: reuse a recent verdict for the same claim, found with Otari embeddings.

Embeddings alone rate "X is in Paris" and "X is in Berlin" as near-identical, so a match also needs
almost the same words and exactly the same numbers. The UI always shows which earlier claim matched.
"""
from __future__ import annotations

import json
import math
import re
import time
from pathlib import Path

from . import config

MAX_ITEMS = 500
MAX_AGE_S = 7 * 24 * 3600


# Words that may differ between two phrasings of the same claim. Negations and names never appear here,
# so "X is not in Paris" / "X is in Berlin" can never reuse "X is in Paris".
FILLER = {"a", "an", "the", "that", "this", "it", "its", "of", "and", "really", "actually", "just", "did", "you",
          "know", "breaking", "claim", "claims", "says", "said", "reportedly", "currently", "now", "today"}


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"\w+", text.lower()))


def _numbers(text: str) -> list[str]:
    return re.findall(r"\d+(?:[.,]\d+)?", text)


def _cos(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na, nb = math.sqrt(sum(x * x for x in a)), math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


class Memory:
    def __init__(self, path: Path | None = None):
        self.path = path or Path(config.DATA_DIR) / "memory.json"
        self.items: list[dict] = []
        try:
            parsed = json.loads(self.path.read_text(encoding="utf-8"))
            self.items = [i for i in parsed if isinstance(i, dict) and {"text", "emb", "ts"} <= i.keys()] \
                if isinstance(parsed, list) else []
        except (OSError, ValueError):
            self.items = []

    def _save(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self.items[-MAX_ITEMS:]), encoding="utf-8")
        except OSError:
            pass

    def find(self, text: str, emb: list[float]) -> dict | None:
        now, best, best_sim = time.time(), None, 0.0
        toks, nums = _tokens(text), _numbers(text)
        for it in self.items:
            if now - it["ts"] > MAX_AGE_S or _numbers(it["text"]) != nums:
                continue
            t2 = _tokens(it["text"])
            if (toks ^ t2) - FILLER:  # any meaningful word differs (a name, a negation, a place): not the same claim
                continue
            sim = _cos(emb, it["emb"])
            if sim >= config.MEMORY_MIN_SIMILARITY and sim > best_sim:
                best, best_sim = it, sim
        if best:
            return {**best, "similarity": round(best_sim, 3)}
        return None

    def add(self, text: str, emb: list[float], verdict: dict, research: dict) -> None:
        if not emb or verdict.get("verdict") in (None, "Can't verify", "Opinion", "Unsupported"):
            return
        # Only remember verdicts backed by at least two sources Otari actually retrieved
        if sum(1 for e in research.get("evidence", []) if e.get("verified_url")) < 2:
            return
        self.items.append({"text": text, "emb": emb, "verdict": verdict, "ts": time.time(),
                           "research": {"evidence": research.get("evidence", []),
                                        "summary": research.get("summary", "")}})
        self.items = self.items[-MAX_ITEMS:]
        self._save()


MEMORY = Memory()
