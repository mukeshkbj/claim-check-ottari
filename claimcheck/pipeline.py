"""Runs the agent team and yields events as it goes, so the UI can stream them."""
from __future__ import annotations

import asyncio
import time
import uuid
from typing import AsyncIterator

from . import agents, config, mcp_log, reports
from .memory import MEMORY
from .otari import Otari, OtariError


def _step_event(step, claim_id=None):
    return {"type": "step", "claim_id": claim_id, "step": step.as_dict()} if step else None


def _budget_or_error(e: OtariError, claim_id=None) -> dict:
    kind = "budget" if (e.status in (402, 429) and "pricing" not in e.detail.lower()) or "budget" in e.detail.lower() \
        else "error"
    return {"type": kind, "claim_id": claim_id, "status": e.status, "code": e.code, "message": e.detail}


async def _check_claim(client: Otari, claim: dict, q: asyncio.Queue, run_id: str, emb: list[float] | None) -> None:
    cid = claim["id"]
    rid = f"{run_id}-{cid}"
    try:
        if not claim.get("checkable", True):
            await q.put({"type": "verdict", "claim_id": cid, "result": {
                "verdict": "Opinion", "confidence": "n/a",
                "explanation": "This is an opinion or prediction, not a checkable fact."}})
            return
        hit = MEMORY.find(claim["text"], emb) if emb else None
        if hit:  # same claim checked recently: reuse it, and say exactly what matched
            age_h = round((time.time() - hit["ts"]) / 3600, 1)
            await q.put({"type": "evidence", "claim_id": cid, "research": hit["research"], "cached": True})
            await q.put({"type": "verdict", "claim_id": cid, "result": hit["verdict"], "cached": {
                "matched": hit["text"], "similarity": hit["similarity"], "age_hours": age_h}})
            return
        await q.put({"type": "status", "claim_id": cid, "message": "Searching for sources"})
        research, step = await agents.investigate(client, claim, rid)
        step.mcp_calls = mcp_log.pop(rid)  # MCP tools Otari actually called for this claim
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
        if emb:
            MEMORY.add(claim["text"], emb, verdict, research)
    except OtariError as e:
        await q.put(_budget_or_error(e, cid))
    except Exception as e:  # keep other claims running
        await q.put({"type": "error", "claim_id": cid, "message": f"{type(e).__name__}: {e}"})


async def run(post: str, api_key: str | None = None, user: str | None = None,
              simulate_outage: bool = False, image: str | None = None) -> AsyncIterator[dict]:
    run_id = uuid.uuid4().hex[:16]
    session = f"claimcheck-{run_id}"
    client = Otari(api_key=api_key, user=user, session=session)
    events: list[dict] = []

    def emit(ev):
        if ev:
            events.append(ev)
        return ev

    try:
        yield emit({"type": "session", "id": session})
        if user:
            yield emit({"type": "user", "user": user})
        if image:
            yield {"type": "status", "message": "Reading the screenshot (Gemma 3 27B)"}
            try:
                text, step = await agents.read_image(client, image)
            except OtariError as e:
                yield emit(_budget_or_error(e))
                return
            yield emit(_step_event(step))
            yield emit({"type": "transcript", "text": text})
            post = "\n".join(p for p in (post.strip(), text) if p)
            if not post:
                yield emit({"type": "error", "message": "No post text found in the screenshot."})
                return
        yield {"type": "status", "message": "Running safety checks (Llama Guard 4, gpt-oss-safeguard) and pulling out the claims"
               if config.GUARD_URL else "Pulling out the claims"}
        try:
            claims, step = await agents.extract(client, post, simulate_outage)
        except OtariError as e:
            if e.code == "guardrail_violation" or (e.status == 403 and "guardrail" in e.detail.lower()):
                yield emit({"type": "blocked", "message": e.detail})
            else:
                yield emit(_budget_or_error(e))
            return
        yield emit(_step_event(step))
        yield emit({"type": "claims", "claims": claims})

        # 'Already checked' memory: one embeddings call for every checkable claim
        embs: dict[str, list[float]] = {}
        checkable = [c for c in claims if c.get("checkable", True)]
        if checkable:
            try:
                vecs, estep = await client.embed([c["text"] for c in checkable], config.MODELS["embedder"])
                embs = {c["id"]: v for c, v in zip(checkable, vecs)}
                yield emit(_step_event(estep))
            except OtariError:
                pass  # memory is optional

        q: asyncio.Queue = asyncio.Queue()
        tasks = [asyncio.create_task(_check_claim(client, c, q, run_id, embs.get(c["id"]))) for c in claims]
        done = asyncio.gather(*tasks)
        while not (done.done() and q.empty()):
            try:
                ev = await asyncio.wait_for(q.get(), timeout=0.25)
            except asyncio.TimeoutError:
                continue
            if ev:
                yield emit(ev)
        yield emit({"type": "done"})
        reports.save(run_id, post, events)
        yield {"type": "report", "id": run_id}
    finally:
        await client.close()
