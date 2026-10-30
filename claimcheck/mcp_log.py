"""Records which MCP tools Otari actually called, per check, so the UI shows real usage (not just 'attached').

Each check passes its own ?rid=<id> on the MCP server URL it gives Otari; this ASGI wrapper reads tools/call
requests for that rid before handing them to the MCP server unchanged.
"""
from __future__ import annotations

import json
import time
from urllib.parse import parse_qs

_calls: dict[str, list[dict]] = {}
_issued: dict[str, float] = {}
_TTL_S = 600
MAX_BODY = 1_000_000


def issue(rid: str) -> None:
    """Called by the pipeline before it hands Otari an MCP URL carrying this rid."""
    now = time.time()
    for k in [k for k, t in _issued.items() if now - t > _TTL_S]:
        _issued.pop(k, None)
    _issued[rid] = now


def record(rid: str, tool: str, args: dict | None) -> None:
    if rid not in _issued:
        return
    now = time.time()
    for k in [k for k, v in _calls.items() if v and now - v[-1]["t"] > _TTL_S]:
        _calls.pop(k, None)
    _calls.setdefault(rid, []).append({"tool": tool, "args": args or {}, "t": now})


def pop(rid: str) -> list[dict]:
    _issued.pop(rid, None)
    return [{"tool": c["tool"], "args": c["args"]} for c in _calls.pop(rid, [])]


class MCPRecorder:
    """ASGI wrapper: note tools/call requests tagged with ?rid=, then pass the request through untouched."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope.get("method") != "POST":
            return await self.app(scope, receive, send)
        rid = (parse_qs(scope.get("query_string", b"").decode()).get("rid") or [None])[0]
        if not rid:
            return await self.app(scope, receive, send)
        body, more = b"", True
        while more:
            msg = await receive()
            body += msg.get("body", b"")
            more = msg.get("more_body", False)
            if len(body) > MAX_BODY:  # not a real MCP call from Otari
                await send({"type": "http.response.start", "status": 413, "headers": []})
                await send({"type": "http.response.body", "body": b""})
                return
        try:
            data = json.loads(body or b"null")
            for item in data if isinstance(data, list) else [data]:
                if isinstance(item, dict) and item.get("method") == "tools/call":
                    p = item.get("params") or {}
                    record(rid, str(p.get("name")), p.get("arguments"))
        except (ValueError, TypeError):
            pass
        replayed = False

        async def replay():
            nonlocal replayed
            if not replayed:
                replayed = True
                return {"type": "http.request", "body": body, "more_body": False}
            return await receive()

        await self.app(scope, replay, send)
