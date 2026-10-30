"""Claim Check web app:  uvicorn app:app --reload   then open http://127.0.0.1:8000"""
import json
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

from claimcheck import config
from claimcheck.pipeline import run

app = FastAPI(title="Claim Check")
STATIC = Path(__file__).parent / "static"


class CheckRequest(BaseModel):
    post: str = Field(min_length=10, max_length=4000)


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/models")
def models():
    return config.MODELS


@app.post("/api/check")
async def check(req: CheckRequest, request: Request):
    async def events():
        async for ev in run(req.post):
            if await request.is_disconnected():
                break
            yield f"data: {json.dumps(ev)}\n\n"
    return StreamingResponse(events(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
