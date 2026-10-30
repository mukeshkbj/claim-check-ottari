"""Runs the agent team and yields events as it goes, so the UI can stream them."""
from __future__ import annotations

import asyncio
from typing import AsyncIterator

from . import agents
from .otari import Otari, OtariError


def _step_event(step, claim_id=None):
    return {"type": "step", "claim_id": claim_id, "step": step.as_dict()} if step else None


async def _check_claim(client: Otari, claim: dict, q: asyncio.Queue) -> None:
    cid = claim["id"]
    try:
        if not claim.get("checkable", True):
            await q.put({"type": "verdict", "claim_id": cid, "result": {
                "verdict": "Opinion", "confidence": "n/a",
                "explanation": "This is an opinion or prediction, not a checkable fact."}})
            return
        await q.put({"type": "status", "claim_id": cid, "message": "Searching for sources"})
        research, step = await agents.investigate(client, claim)
        await q.put(_step_event(step, cid))
        await q.put({"type": "evidence", "claim_id": cid, "research": research})
        if claim.get("kind") == "numeric" and research.get("evidence"):
            await q.put({"type": "status", "claim_id": cid, "message": "Re-running the numbers"})
        numbers, nstep = await agents.check_numbers(client, claim, research)
        if nstep:
            await q.put(_step_event(nstep, cid))
        if numbers:
            await q.put({"type": "numbers", "claim_id": cid, "numbers": numbers})
        await q.put({"type": "status", "claim_id": cid, "message": "Judging"})
        verdict, jstep = await agents.judge(client, claim, research, numbers)
        await q.put(_step_event(jstep, cid))
        await q.put({"type": "verdict", "claim_id": cid, "result": verdict})
    except OtariError as e:
        await q.put({"type": "error", "claim_id": cid, "status": e.status, "code": e.code, "message": e.detail})
    except Exception as e:  # keep other claims running
        await q.put({"type": "error", "claim_id": cid, "message": f"{type(e).__name__}: {e}"})


async def run(post: str, api_key: str | None = None, user: str | None = None) -> AsyncIterator[dict]:
    client = Otari(api_key=api_key, user=user)
    try:
        yield {"type": "status", "message": "Pulling out the claims"}
        try:
            claims, step = await agents.extract(client, post)
        except OtariError as e:
            yield {"type": "error", "status": e.status, "code": e.code, "message": e.detail}
            return
        yield _step_event(step)
        yield {"type": "claims", "claims": claims}
        q: asyncio.Queue = asyncio.Queue()
        tasks = [asyncio.create_task(_check_claim(client, c, q)) for c in claims]
        done = asyncio.gather(*tasks)
        while not (done.done() and q.empty()):
            try:
                ev = await asyncio.wait_for(q.get(), timeout=0.25)
            except asyncio.TimeoutError:
                continue
            if ev:
                yield ev
        yield {"type": "done"}
    finally:
        await client.close()
