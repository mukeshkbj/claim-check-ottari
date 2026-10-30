"""Claim Check web app:  uvicorn app:app --port 8000   then open http://127.0.0.1:8000

Also serves, for the Otari gateway to call once deployed:
  /mcp/                    Claim Check's MCP server (Wayback Machine, Wikipedia, Wikidata)
  /guard/<token>/validate  guardrail service backed by open-weight safety models
"""
import asyncio
import contextlib
import json
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

from claimcheck import config, guard
from claimcheck.mcp_tools import mcp
from claimcheck.pipeline import run


@contextlib.asynccontextmanager
async def lifespan(_app: FastAPI):
    async with mcp.session_manager.run():
        if config.GUARD_URL:
            asyncio.create_task(guard.warm_up())
        yield


app = FastAPI(title="Claim Check", lifespan=lifespan)
app.mount("/mcp", mcp.streamable_http_app())
STATIC = Path(__file__).parent / "static"


class CheckRequest(BaseModel):
    post: str = Field(min_length=10, max_length=4000)
    volunteer: str | None = None
    simulate_outage: bool = False


class GuardRequest(BaseModel):
    profile: str
    input_text: str = ""
    validate_kwargs: dict | None = None


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/config")
def app_config():
    return {"models": config.MODELS, "volunteers": config.VOLUNTEERS,
            "guardrails": bool(config.GUARD_URL), "mcp": bool(config.MCP_URL)}


@app.post("/api/check")
async def check(req: CheckRequest, request: Request):
    key, user = None, None
    if req.volunteer in config.VOLUNTEER_KEYS:
        key, user = config.VOLUNTEER_KEYS[req.volunteer], req.volunteer  # their own key + budget

    async def events():
        async for ev in run(req.post, api_key=key, user=user, simulate_outage=req.simulate_outage):
            if await request.is_disconnected():
                break
            yield f"data: {json.dumps(ev)}\n\n"
    return StreamingResponse(events(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ---- Guardrail service for Otari (contract: POST /validate -> {profile, result:{valid, score, explanation}})
def _check_token(token: str) -> None:
    if not config.GUARD_TOKEN or token != config.GUARD_TOKEN:
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
