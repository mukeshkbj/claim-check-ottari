"""Claim Check web app:  uvicorn app:app --port 8000   then open http://127.0.0.1:8000

Also serves, for the Otari gateway to call once deployed:
  /mcp/                    Claim Check's MCP server (Wayback Machine, Wikipedia, Wikidata)
  /guard/<token>/validate  guardrail service backed by open-weight safety models
"""
import asyncio
import collections
import contextlib
import hmac
import html
import json
import os
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, Response, StreamingResponse
from pydantic import BaseModel, Field

from claimcheck import agents, card, config, guard, reports
from claimcheck.otari import Otari, OtariError
from claimcheck.mcp_log import MCPRecorder
from claimcheck.mcp_tools import mcp
from claimcheck.pipeline import run


@contextlib.asynccontextmanager
async def lifespan(_app: FastAPI):
    async with mcp.session_manager.run():
        if config.GUARD_URL:
            _app.state.warmup = asyncio.create_task(guard.warm_up())  # keep a reference so it is not collected
        yield


app = FastAPI(title="Claim Check", lifespan=lifespan)
app.mount("/mcp", MCPRecorder(mcp.streamable_http_app()))
STATIC = Path(__file__).parent / "static"


# ---- Abuse limits: this is a public demo spending real money on every check
RATE_PER_HOUR = int(os.getenv("RATE_PER_HOUR", "12"))
MAX_CONCURRENT = int(os.getenv("MAX_CONCURRENT_CHECKS", "3"))
MAX_REQUEST_BYTES = config.MAX_IMAGE_CHARS + 20_000
_hits: dict[str, collections.deque] = collections.defaultdict(collections.deque)
_running = asyncio.Semaphore(MAX_CONCURRENT)


def _client_ip(request: Request) -> str:
    # Measured on Render: X-Forwarded-For is "<anything the client sent>, <client>, <Cloudflare>, <Render LB>",
    # so neither end of it identifies a visitor. Cloudflare sets CF-Connecting-IP itself and rejects requests
    # that try to supply it, so that is the visitor. Locally (no Cloudflare) fall back to the socket peer.
    for h in ("cf-connecting-ip", "true-client-ip"):
        if request.headers.get(h):
            return request.headers[h].strip()
    return request.client.host if request.client else "?"


def _rate_limited(ip: str, limit: int | None = None) -> bool:
    now, q = time.time(), _hits[ip]
    while q and now - q[0] > 3600:
        q.popleft()
    if len(q) >= (limit or RATE_PER_HOUR):
        return True
    q.append(now)
    if len(_hits) > 5000:  # forget idle clients
        for k in [k for k, v in _hits.items() if not v or now - v[-1] > 3600]:
            _hits.pop(k, None)
    return False


@app.middleware("http")
async def limit_body(request: Request, call_next):
    if request.method == "POST" and request.url.path == "/api/check":
        try:
            size = int(request.headers.get("content-length", "0"))
        except ValueError:
            size = 0
        if size > MAX_REQUEST_BYTES:
            from fastapi.responses import JSONResponse
            return JSONResponse({"detail": "Request too large (screenshots are resized in the browser to stay small)."},
                                status_code=413)
    return await call_next(request)


class CheckRequest(BaseModel):
    post: str = Field(default="", max_length=4000)
    image: str | None = Field(default=None, max_length=config.MAX_IMAGE_CHARS)  # data:image/...;base64 screenshot
    volunteer: str | None = None
    simulate_outage: bool = False


class GuardRequest(BaseModel):
    profile: str
    input_text: str = ""
    validate_kwargs: dict | None = None


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/r/{report_id}")
def shared_report(report_id: str, request: Request):
    """The page replays the saved report; link-preview tags (Open Graph / Twitter) point at the share card."""
    page = (STATIC / "index.html").read_text(encoding="utf-8")
    rep = reports.load(report_id)
    rows = reports.summarize(rep) if rep else []
    if rows:
        base = config.PUBLIC_URL or str(request.base_url).rstrip("/")
        title = f"Claim Check: {rows[0]['verdict']} - {rows[0]['text']}"[:150]
        desc = (rows[0].get("explanation") or "Verdicts with sources, checked by open-weight models through Otari.")[:300]
        e = lambda x: html.escape(x, quote=True)
        tags = (f'<meta property="og:type" content="article"><meta property="og:title" content="{e(title)}">'
                f'<meta property="og:description" content="{e(desc)}">'
                f'<meta property="og:image" content="{e(base)}/r/{report_id}/card.png">'
                f'<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">'
                f'<meta property="og:url" content="{e(base)}/r/{report_id}"><meta name="twitter:card" content="summary_large_image">'
                f'<meta name="twitter:title" content="{e(title)}"><meta name="twitter:description" content="{e(desc)}">'
                f'<meta name="twitter:image" content="{e(base)}/r/{report_id}/card.png">')
        page = page.replace("</head>", tags + "\n</head>", 1)
    return HTMLResponse(page)


@app.get("/r/{report_id}/card.png")
def share_card(report_id: str, request: Request):
    rep = reports.load(report_id)
    rows = reports.summarize(rep) if rep else []
    if not rows:
        raise HTTPException(status_code=404)
    host = (config.PUBLIC_URL or str(request.base_url)).split("://")[-1].rstrip("/")
    return Response(card.card_for(report_id, rows, host), media_type="image/png",
                    headers={"Cache-Control": "public, max-age=86400"})


class ReplyRequest(BaseModel):
    report_id: str = Field(max_length=32)


@app.post("/api/reply")
async def draft_reply(req: ReplyRequest, request: Request):
    """A calm, sourced reply someone could post under the original post. Cached per report."""
    rep = reports.load(req.report_id)
    rows = reports.summarize(rep) if rep else []
    if not rows:
        raise HTTPException(status_code=404, detail="Report not found.")
    if rep.get("reply"):
        return rep["reply"]
    if _rate_limited(_client_ip(request) + "#reply", limit=RATE_PER_HOUR * 2):
        raise HTTPException(status_code=429, detail="Too many replies drafted this hour. Try again later.")
    client = Otari(session=f"claimcheck-{req.report_id}")
    try:
        text, step = await agents.draft_reply(client, rows, rows[0].get("language", "English"))
    except OtariError as e:
        raise HTTPException(status_code=502, detail=f"Couldn't draft a reply: {e.detail}")
    finally:
        await client.close()
    out = {"reply": text, "step": step.as_dict()}
    reports.save_extra(req.report_id, "reply", out)
    return out


@app.get("/api/reports/{report_id}")
def get_report(report_id: str):
    rep = reports.load(report_id)
    if not rep:
        raise HTTPException(status_code=404, detail="Report not found (reports are kept while this server runs).")
    return rep


@app.get("/api/config")
def app_config():
    return {"models": config.MODELS, "volunteers": config.VOLUNTEERS,
            "guardrails": bool(config.GUARD_URL), "mcp": bool(config.MCP_URL)}


@app.post("/api/check")
async def check(req: CheckRequest, request: Request):
    if len(req.post.strip()) < 10 and not req.image:
        raise HTTPException(status_code=422, detail="Paste a post (10+ characters) or add a screenshot.")
    if req.image and not req.image.startswith(("data:image/png;base64,", "data:image/jpeg;base64,", "data:image/webp;base64,")):
        raise HTTPException(status_code=422, detail="Screenshot must be a PNG, JPEG or WebP image.")
    key, user = None, None
    if req.volunteer:
        if req.volunteer not in config.VOLUNTEER_KEYS:
            raise HTTPException(status_code=422, detail="Unknown volunteer.")
        key, user = config.VOLUNTEER_KEYS[req.volunteer], req.volunteer  # their own key + budget
    if _running.locked():  # check before counting, so a busy server doesn't use up the visitor's quota
        raise HTTPException(status_code=429, detail="The demo is busy with other checks right now. Try again in a minute.")
    if _rate_limited(_client_ip(request)):
        raise HTTPException(status_code=429, detail=f"Rate limit: {RATE_PER_HOUR} checks per hour per visitor on this demo.")

    async def events():
        async with _running:
            async for ev in run(req.post, api_key=key, user=user, simulate_outage=req.simulate_outage, image=req.image):
                if await request.is_disconnected():
                    break
                yield f"data: {json.dumps(ev)}\n\n"
    return StreamingResponse(events(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ---- Guardrail service for Otari (contract: POST /validate -> {profile, result:{valid, score, explanation}})
def _check_token(token: str) -> None:
    if not config.GUARD_TOKEN or not hmac.compare_digest(token.encode(), config.GUARD_TOKEN.encode()):
        raise HTTPException(status_code=404)


@app.get("/guard/{token}/profiles")
def guard_profiles(token: str):
    _check_token(token)
    return [{"name": "prompt-injection", "guardrail_name": "gpt-oss-safeguard-20b"},
            {"name": "privacy", "guardrail_name": "llama-guard-4-12b"}]


@app.post("/guard/{token}/validate")
@app.post("/guard/{token}")
async def guard_validate(token: str, req: GuardRequest):
    _check_token(token)
    result = await guard.validate(req.profile, req.input_text)
    return {"profile": req.profile, "result": result}


@app.get("/healthz")
def healthz():
    return {"ok": True}
