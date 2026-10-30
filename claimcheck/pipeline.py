"""Runs the agent team and yields events as it goes, so the UI can stream them."""
from __future__ import annotations

import asyncio
import re
import time
import uuid
from typing import AsyncIterator

from . import agents, config, mcp_log, reports
from .memory import MEMORY
from .otari import Otari, OtariError


URL_RE = re.compile(r"https?://[^\s<>\"']+", re.I)


def link_in(post: str) -> str | None:
    """The URL to read when the input is essentially just a link (optionally with a few words around it)."""
    urls = URL_RE.findall(post or "")
    if len(urls) != 1:
        return None
    rest = URL_RE.sub("", post).strip()
    return urls[0].rstrip(".,;:!?)]") if len(rest) < 60 else None


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
        mcp_log.issue(rid)  # only MCP calls carrying an rid we handed out get recorded
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
        await q.put({"type": "status", "claim_id": cid, "message": "Judging (two independent judges)"
                     if config.SECOND_OPINION else "Judging"})
        main = agents.judge(client, claim, research, numbers)
        if config.SECOND_OPINION and research.get("evidence"):
            second = asyncio.wait_for(agents.second_opinion(client, claim, research, numbers), timeout=25)
            (verdict, jstep), other = await _both(main, second)
        else:
            (verdict, jstep), other = await main, None
        await q.put(_step_event(jstep, cid))
        if other:
            v2, s2 = other
            await q.put(_step_event(s2, cid))
            verdict["second_opinion"] = agents.compare(verdict, v2, s2.upstream_model or s2.model_served
                                                       or s2.model_requested)
            if not verdict["second_opinion"]["agree"] and verdict.get("confidence") == "high":
                verdict["confidence"] = "medium"  # two model families disagree: say so
        await q.put({"type": "verdict", "claim_id": cid, "result": verdict})
        if emb and (not other or verdict["second_opinion"]["agree"]):
            MEMORY.add(claim["text"], emb, verdict, research)  # only remember verdicts both judges agree on
    except OtariError as e:
        await q.put(_budget_or_error(e, cid))
    except Exception as e:  # keep other claims running
        await q.put({"type": "error", "claim_id": cid, "message": f"{type(e).__name__}: {e}"})


async def _both(main, second):
    """Primary verdict is required; the second opinion is best-effort (errors or a slow model are skipped)."""
    res = await asyncio.gather(main, second, return_exceptions=True)
    if isinstance(res[0], BaseException):
        raise res[0]
    return res[0], (None if isinstance(res[1], BaseException) else res[1])


async def run(post: str, api_key: str | None = None, user: str | None = None,
              simulate_outage: bool = False, image: str | None = None) -> AsyncIterator[dict]:
    run_id = uuid.uuid4().hex[:16]
    session = f"claimcheck-{run_id}"
    client = Otari(api_key=api_key, user=user, session=session)
    events: list[dict] = []
    tasks: list[asyncio.Task] = []
    saved_post: str | None = None

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
        url = link_in(post) if not image else None
        if url:
            yield {"type": "status", "message": "Reading the page (Otari web fetch)"}
            try:
                page, step = await agents.fetch_page(client, url)
            except OtariError as e:
                yield emit(_budget_or_error(e))
                return
            yield emit(_step_event(step))
            if not page:
                yield emit({"type": "error", "message": "Couldn't read that page (it may block automated readers "
                                                        "or need a login). Paste the post's text instead."})
                return
            yield emit({"type": "page", "url": page["url"], "title": page["title"], "excerpt": page["text"][:700]})
            saved_post = post  # the shared report shows the link the user gave, not the whole article
            post = f"{page['title']}\n\n{page['text'][:3500]}"  # the lead of an article carries its main claims
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
        except Exception as e:  # unparseable model output etc.: tell the user instead of dropping the stream
            yield emit({"type": "error", "message": f"Couldn't pull out the claims ({type(e).__name__}). Please try again."})
            return
        yield emit(_step_event(step))
        yield emit({"type": "claims", "claims": claims})
        if not claims:
            yield emit({"type": "error", "message": "I couldn't find a claim to check in this post. Try pasting the exact sentence."})
            return

        # 'Already checked' memory: one embeddings call for every checkable claim
        embs: dict[str, list[float]] = {}
        checkable = [c for c in claims if c.get("checkable", True)]
        if checkable:
            try:
                vecs, estep = await client.embed([c["text"] for c in checkable], config.MODELS["embedder"])
                embs = {c["id"]: v for c, v in zip(checkable, vecs)}
                yield emit(_step_event(estep))
            except Exception:  # API error or unexpected payload: memory is optional
                embs = {}

        q: asyncio.Queue = asyncio.Queue()
        tasks[:] = [asyncio.create_task(_check_claim(client, c, q, run_id, embs.get(c["id"]))) for c in claims]
        done = asyncio.gather(*tasks)
        while not (done.done() and q.empty()):
            try:
                ev = await asyncio.wait_for(q.get(), timeout=0.25)
            except asyncio.TimeoutError:
                continue
            if ev:
                yield emit(ev)
        yield emit({"type": "done"})
        reports.save(run_id, saved_post or post, events)
        yield {"type": "report", "id": run_id}
    finally:
        for t in tasks:  # the browser went away mid-check: stop spending on it
            if not t.done():
                t.cancel()
        await client.close()
