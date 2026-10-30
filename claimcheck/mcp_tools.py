"""Claim Check's own MCP server (streamable HTTP). Otari calls these tools during research.

Tools hit free public APIs only: the Wayback Machine, Wikipedia and Wikidata.
"""
from __future__ import annotations

import os
import re
from urllib.parse import quote

import httpx
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

# Public server: allow our deployed hostname (DNS-rebinding protection is for localhost servers).
_host = (os.getenv("RENDER_EXTERNAL_HOSTNAME") or "").strip()
_security = TransportSecuritySettings(
    enable_dns_rebinding_protection=bool(_host),
    allowed_hosts=[_host, f"{_host}:*", "127.0.0.1:*", "localhost:*"] if _host else [],
    allowed_origins=[f"https://{_host}"] if _host else [],
)
mcp = FastMCP("claim-check-tools", stateless_http=True, json_response=True, transport_security=_security)
mcp.settings.streamable_http_path = "/"
UA = {"User-Agent": "ClaimCheck/0.1 (Mozilla Otari hackathon; https://github.com/mukeshkbj/claim-check-ottari)"}


@mcp.tool()
async def wayback_snapshot(url: str, timestamp: str = "") -> dict:
    """Find the archived Wayback Machine copy of a URL closest to a date.

    Use it to see what a page originally said, or whether a cited page ever existed.
    timestamp: optional YYYYMMDD (closest snapshot to that date)."""
    params = {"url": url}
    if timestamp:
        params["timestamp"] = timestamp
    async with httpx.AsyncClient(timeout=20, headers=UA) as c:
        r = await c.get("https://archive.org/wayback/available", params=params)
    snap = (r.json().get("archived_snapshots") or {}).get("closest")
    if not snap:
        return {"found": False, "url": url}
    return {"found": True, "archived_url": snap.get("url"), "timestamp": snap.get("timestamp"),
            "status": snap.get("status")}


@mcp.tool()
async def wikipedia_summary(title: str, lang: str = "en") -> dict:
    """Get the lead summary of a Wikipedia article (background facts, dates, places)."""
    if not re.fullmatch(r"[a-z]{2,3}(-[a-z]{2,8})?", lang or ""):
        lang = "en"  # the language code becomes part of the hostname: never let it be anything else
    async with httpx.AsyncClient(timeout=20, headers=UA, follow_redirects=True) as c:
        s = await c.get(f"https://{lang}.wikipedia.org/w/api.php", params={
            "action": "query", "list": "search", "srsearch": title, "srlimit": 1, "format": "json"})
        hits = s.json().get("query", {}).get("search", [])
        if not hits:
            return {"found": False, "query": title}
        page = hits[0]["title"]
        r = await c.get(f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{quote(page.replace(' ', '_'), safe='')}")
    j = r.json()
    return {"found": True, "title": j.get("title"), "extract": j.get("extract"),
            "url": (j.get("content_urls") or {}).get("desktop", {}).get("page")}


@mcp.tool()
async def wikidata_facts(entity: str) -> dict:
    """Look up an entity on Wikidata and return its description and key facts
    (country, population, inception date, coordinates) where available."""
    props = {"P17": "country", "P1082": "population", "P571": "inception", "P131": "located_in",
             "P625": "coordinates", "P569": "date_of_birth"}
    async with httpx.AsyncClient(timeout=20, headers=UA) as c:
        s = await c.get("https://www.wikidata.org/w/api.php", params={
            "action": "wbsearchentities", "search": entity, "language": "en", "limit": 1, "format": "json"})
        hits = s.json().get("search", [])
        if not hits:
            return {"found": False, "query": entity}
        qid = hits[0]["id"]
        e = (await c.get(f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json")).json()["entities"][qid]
    facts = {}
    for pid, name in props.items():
        for claim in (e.get("claims", {}).get(pid) or [])[:1]:
            v = claim.get("mainsnak", {}).get("datavalue", {}).get("value")
            if isinstance(v, dict):
                v = v.get("amount") or v.get("time") or v.get("id") or \
                    (f"{v.get('latitude')},{v.get('longitude')}" if "latitude" in v else str(v))
            facts[name] = v
    return {"found": True, "id": qid, "label": hits[0].get("label"), "description": hits[0].get("description"),
            "facts": facts, "url": f"https://www.wikidata.org/wiki/{qid}"}
