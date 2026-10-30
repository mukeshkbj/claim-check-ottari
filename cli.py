"""Run a check from the terminal:  python cli.py "post text"   (or pipe text in)."""
import asyncio
import json
import sys

from claimcheck.pipeline import run


async def main(post: str) -> None:
    async for ev in run(post):
        t = ev["type"]
        if t == "step":
            s = ev["step"]
            fb = "  (FALLBACK)" if s["fell_back"] else ""
            err = f"  ERROR {s['error']}" if s["error"] else ""
            print(f"  [{s['role']:<12}] {s['model_served'] or s['model_requested']}{fb} "
                  f"{s['seconds']}s tok={s['prompt_tokens']}+{s['completion_tokens']} tools={s['tools']}{err}")
        elif t == "claims":
            for c in ev["claims"]:
                print(f"CLAIM {c['id']} ({c['kind']}): {c['text']}")
        elif t == "evidence":
            for e in ev["research"].get("evidence", []):
                print(f"  {ev['claim_id']} source [{e.get('stance')}]: {e.get('url')}")
        elif t == "numbers":
            print(f"  {ev['claim_id']} numbers: {json.dumps(ev['numbers'])[:300]}")
        elif t == "verdict":
            r = ev["result"]
            print(f"VERDICT {ev['claim_id']}: {r.get('verdict')} ({r.get('confidence')}) - {r.get('explanation')}")
        elif t == "error":
            print("ERROR", ev)
        elif t == "status":
            pass


if __name__ == "__main__":
    text = " ".join(sys.argv[1:]) or sys.stdin.read()
    asyncio.run(main(text))
