"""Thin async client for the Otari gateway that records a trace step per call."""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

from . import config


class OtariError(Exception):
    def __init__(self, status: int, detail: str, code: str | None = None):
        super().__init__(f"{status}: {detail}")
        self.status, self.detail, self.code = status, detail, code


@dataclass
class Step:
    role: str
    model_requested: str
    model_served: str = ""
    tools: list[str] = field(default_factory=list)
    tool_calls: list[dict] = field(default_factory=list)
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float | None = None
    seconds: float = 0.0
    error: str | None = None
    provider: str = ""
    upstream_model: str = ""
    attempts: int = 1
    otari_fallback: bool = False
    guardrails: list = field(default_factory=list)
    mcp: list[str] = field(default_factory=list)
    mcp_calls: list[dict] = field(default_factory=list)
    user: str | None = None

    @property
    def fell_back(self) -> bool:
        return self.otari_fallback or (bool(self.model_served) and self.model_served != self.model_requested
                                       and "/" in self.model_requested)

    def as_dict(self) -> dict:
        d = self.__dict__.copy()
        d["fell_back"] = self.fell_back
        return d


class Otari:
    def __init__(self, api_key: str | None = None, base_url: str | None = None, user: str | None = None):
        self.api_key = api_key or config.API_KEY
        self.base_url = (base_url or config.BASE_URL).rstrip("/")
        self.user = user
        self._http = httpx.AsyncClient(timeout=180)

    async def close(self) -> None:
        await self._http.aclose()

    async def chat(self, role: str, model: str, messages: list[dict], *, tools: list[dict] | None = None,
                   json_mode: bool = False, max_tokens: int = 1200, temperature: float = 0.2,
                   guardrails: list[dict] | None = None, mcp_servers: list[dict] | None = None,
                   reasoning_effort: str | None = None) -> tuple[str, Step]:
        body: dict[str, Any] = {"model": model, "messages": messages,
                                "max_tokens": max_tokens, "temperature": temperature}
        if tools:
            body["tools"] = tools
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        if guardrails:
            body["guardrails"] = guardrails
        if mcp_servers:
            body["mcp_servers"] = mcp_servers
        if reasoning_effort:
            body["reasoning_effort"] = reasoning_effort
        step = Step(role=role, model_requested=model, tools=[t.get("type", "") for t in tools or []],
                    mcp=[m["name"] for m in mcp_servers or []], user=self.user)
        t0 = time.perf_counter()
        r = await self._http.post(f"{self.base_url}/chat/completions", json=body,
                                  headers={"Authorization": f"Bearer {self.api_key}"})
        step.seconds = round(time.perf_counter() - t0, 2)
        if r.status_code >= 400:
            try:
                j = r.json()
                detail, code = j.get("detail") or j.get("error") or r.text, j.get("code")
            except ValueError:
                detail, code = r.text, None
            if json_mode and r.status_code == 400 and "response_format" in str(detail):
                # Some upstream providers reject JSON mode; the prompt already asks for JSON.
                return await self.chat(role, model, messages, tools=tools, json_mode=False,
                                       max_tokens=max_tokens, temperature=temperature,
                                       guardrails=guardrails, mcp_servers=mcp_servers,
                                       reasoning_effort=reasoning_effort)
            if isinstance(detail, dict):
                code = code or detail.get("code")
                detail = detail.get("message") or detail
            step.error = f"{r.status_code} {detail}"
            raise OtariError(r.status_code, str(detail), code)
        data = r.json()
        h = r.headers
        step.provider = h.get("otari-provider", "")
        step.upstream_model = h.get("otari-model", "")
        step.attempts = int(h.get("otari-attempt-count", "1") or 1)
        step.otari_fallback = h.get("otari-fallback", "false").lower() == "true"
        if h.get("otari-guardrails"):
            try:
                step.guardrails = json.loads(h["otari-guardrails"])
            except ValueError:
                pass
        step.model_served = data.get("model", "")
        usage = data.get("usage") or {}
        step.prompt_tokens = usage.get("prompt_tokens", 0) or 0
        step.completion_tokens = usage.get("completion_tokens", 0) or 0
        cost = usage.get("cost_usd") or usage.get("estimated_cost") or usage.get("cost")
        try:
            step.cost_usd = round(float(cost), 6) if cost is not None else None
        except (TypeError, ValueError):
            step.cost_usd = None
        step.tool_calls = data.get("otari_tool_calls") or []
        msg = (data.get("choices") or [{}])[0].get("message") or {}
        return msg.get("content") or "", step


def parse_json(text: str) -> Any:
    """Pull the first JSON object/array out of a model reply (handles ```json fences and <think> blocks)."""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, flags=re.S)
    if fence:
        text = fence.group(1).strip()
    try:
        return json.loads(text)
    except ValueError:
        pass
    for open_c, close_c in (("{", "}"), ("[", "]")):
        start, end = text.find(open_c), text.rfind(close_c)
        if start != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except ValueError:
                continue
    raise ValueError(f"No JSON found in model reply: {text[:200]}")
