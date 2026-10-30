"""Shareable reports: each finished check is saved as its event stream and replayed at /r/<id>."""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

from . import config

DIR = Path(config.DATA_DIR) / "reports"
_ID = re.compile(r"^[a-f0-9]{8,32}$")


def save(report_id: str, post: str, events: list[dict]) -> None:
    try:
        DIR.mkdir(parents=True, exist_ok=True)
        (DIR / f"{report_id}.json").write_text(json.dumps({"id": report_id, "post": post, "created": time.time(),
                                                            "events": events}), encoding="utf-8")
    except OSError:
        pass


def load(report_id: str) -> dict | None:
    if not _ID.match(report_id):
        return None
    try:
        return json.loads((DIR / f"{report_id}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def summarize(rep: dict) -> list[dict]:
    """One row per claim: text, verdict, explanation, source URLs and the second opinion, from the saved events."""
    rows: dict[str, dict] = {}
    for ev in rep.get("events", []):
        t, cid = ev.get("type"), ev.get("claim_id")
        if t == "claims":
            for c in ev.get("claims", []):
                rows[c["id"]] = {"id": c["id"], "text": c.get("text", ""), "language": c.get("language", "English"),
                                 "verdict": None, "sources": []}
        elif t == "evidence" and cid in rows:
            ev_list = [e for e in ev.get("research", {}).get("evidence", [])
                       if str(e.get("url", "")).startswith(("http://", "https://"))]
            ev_list.sort(key=lambda e: not e.get("verified_url"))  # sources Otari actually retrieved first
            rows[cid]["sources"] = [e["url"] for e in ev_list]
        elif t == "verdict" and cid in rows:
            r = ev.get("result", {})
            rows[cid].update(verdict=r.get("verdict"), confidence=r.get("confidence"),
                             explanation=r.get("explanation", ""), second=r.get("second_opinion"))
    return [r for r in rows.values() if r["verdict"]]


def save_extra(report_id: str, key: str, value) -> None:
    rep = load(report_id)
    if not rep:
        return
    rep[key] = value
    try:
        (DIR / f"{report_id}.json").write_text(json.dumps(rep), encoding="utf-8")
    except OSError:
        pass
