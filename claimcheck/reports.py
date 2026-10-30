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
