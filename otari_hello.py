"""First Otari call for Claim Check.

Run:  python otari_hello.py
It (1) lists the models your workspace can use, flagging likely open-weight ones,
and (2) sends one chat completion through Otari.
"""
import os
import httpx
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
BASE_URL = os.getenv("OTARI_BASE_URL", "https://eu.api.otari.ai/api/v1")
API_KEY = os.environ["OTARI_API_KEY"]
MODEL = os.getenv("OTARI_MODEL", "deepseek/deepseek-v4-pro-0813")

OPEN_WEIGHT_HINTS = ("llama", "qwen", "deepseek", "mistral", "mixtral", "gemma",
                     "gpt-oss", "phi", "olmo", "kimi", "glm", "nemotron")


def list_models() -> None:
    """Try the likely model-list endpoints; never fatal."""
    root = BASE_URL.rsplit("/api/v1", 1)[0]
    for url in (f"{BASE_URL}/models", f"{root}/api/v1/catalog/models"):
        try:
            r = httpx.get(url, headers={"Authorization": f"Bearer {API_KEY}"}, timeout=30)
        except httpx.HTTPError as e:
            print("  ", url, "->", type(e).__name__)
            continue
        print("  ", url, "->", r.status_code)
        if r.status_code != 200:
            continue
        body = r.json()
        items = body.get("data", body) if isinstance(body, dict) else body
        ids = sorted({(m.get("id") or m.get("name") or "") if isinstance(m, dict) else str(m) for m in items})
        print(f"{len(ids)} models available. Likely open-weight:")
        for mid in ids:
            if any(h in mid.lower() for h in OPEN_WEIGHT_HINTS):
                print("  ", mid)
        return
    print("Could not list models via API - check the Models tab on otari.ai.")


def hello() -> None:
    client = OpenAI(base_url=BASE_URL, api_key=API_KEY)
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user",
                   "content": "In one sentence: why should claims in viral posts be fact-checked?"}],
    )
    print("\nServed by:", resp.model)
    print(resp.choices[0].message.content)


if __name__ == "__main__":
    list_models()
    hello()
