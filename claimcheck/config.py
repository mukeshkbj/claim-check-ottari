import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("OTARI_BASE_URL", "https://eu.api.otari.ai/api/v1")
API_KEY = os.getenv("OTARI_API_KEY", "")

# One open-weight model per role (override any of them in .env)
MODELS = {
    "extractor": os.getenv("MODEL_EXTRACTOR", "meta/llama-3.1-8b-instruct"),
    "investigator": os.getenv("MODEL_INVESTIGATOR", "alibaba/qwen3-235b-a22b-instruct-2507"),
    "numbers": os.getenv("MODEL_NUMBERS", "alibaba/qwen3-235b-a22b-instruct-2507"),
    "judge": os.getenv("MODEL_JUDGE", "openai/gpt-oss-120b"),
    "guard_privacy": os.getenv("MODEL_GUARD_PRIVACY", "meta/llama-guard-4-12b"),
    "guard_injection": os.getenv("MODEL_GUARD_INJECTION", "openai/gpt-oss-safeguard-20b"),
}

# Public URL of this app once deployed (Render). Enables Otari -> our MCP server and guardrail service.
PUBLIC_URL = os.getenv("PUBLIC_URL", "").rstrip("/")
GUARD_TOKEN = os.getenv("GUARD_TOKEN", "")
MCP_URL = os.getenv("MCP_URL", f"{PUBLIC_URL}/mcp/" if PUBLIC_URL else "")
GUARD_URL = os.getenv("GUARD_URL", f"{PUBLIC_URL}/guard/{GUARD_TOKEN}" if PUBLIC_URL and GUARD_TOKEN else "")

# Per-volunteer budgets: a service key may act for end users named in the request's `user` field.
SERVICE_KEY = os.getenv("OTARI_SERVICE_KEY", "")
VOLUNTEERS = [v.strip() for v in os.getenv("VOLUNTEERS", "alice,bob").split(",") if v.strip()]

MAX_CLAIMS = int(os.getenv("MAX_CLAIMS", "4"))
SEARCHES_PER_CLAIM = int(os.getenv("SEARCHES_PER_CLAIM", "2"))
