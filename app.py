"""Claim Check web app:  uvicorn app:app --port 8000   then open http://127.0.0.1:8000

Also serves, for the Otari gateway to call once deployed:
  /mcp/                    Claim Check's MCP server (Wayback Machine, Wikipedia, Wikidata)
  /guard/<token>/validate  guardrail service backed by open-weight safety models
"""
import asyncio
import collections
import contextlib
import hmac
import json
import os
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

from claimcheck import config, guard, reports
from claimcheck.mcp_log import MCPRecorder
from claimcheck.mcp_tools import mcp
from claimcheck.pipeline import run


@contextlib.asynccontextmanager
async def lifespan(_app: FastAPI):
    async with mcp.session_manager.run():
        if config.GUARD_URL:
            asyncio.create_task(guard.warm_up())
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
    # The client controls the start of X-Forwarded-For; Render's proxy appends the real address last.
    fwd = [p.strip() for p in request.headers.get("x-forwarded-for", "").split(",") if p.strip()]
    return fwd[-1] if fwd else (request.client.host if request.client else "?")


def _rate_limited(ip: str) -> bool:
    now, q = time.time(), _hits[ip]
    while q and now - q[0] > 3600:
        q.popleft()
    if len(q) >= RATE_PER_HOUR:
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
def shared_report(report_id: str):
    return FileResponse(STATIC / "index.html")  # the page replays the saved report


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


@app.get("/api/_fwd")  # TEMP: check how Render fills X-Forwarded-For
def _fwd(request: Request):
    return {k: request.headers.get(k) for k in ("x-forwarded-for", "true-client-ip", "cf-connecting-ip", "x-real-ip")} | {
        "peer": request.client.host if request.client else None, "used": _client_ip(request)}


@app.get("/healthz")
def healthz():
    return {"ok": True}
