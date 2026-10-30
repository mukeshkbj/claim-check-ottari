import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("OTARI_BASE_URL", "https://eu.api.otari.ai/api/v1")
API_KEY = os.getenv("OTARI_API_KEY", "")

# One open-weight model per role (override any of them in .env)
MODELS = {
    "extractor": os.getenv("MODEL_EXTRACTOR", "cc-extractor"),        # Otari policy: Llama 3.1 8B -> gpt-oss-20b
    "investigator": os.getenv("MODEL_INVESTIGATOR", "cc-investigator"),  # Otari policy: Qwen3 235B -> DeepSeek V4 Flash
    "numbers": os.getenv("MODEL_NUMBERS", "cc-investigator"),
    "judge": os.getenv("MODEL_JUDGE", "openai/gpt-oss-120b"),
    "guard_privacy": os.getenv("MODEL_GUARD_PRIVACY", "meta/llama-guard-4-12b"),
    "guard_injection": os.getenv("MODEL_GUARD_INJECTION", "openai/gpt-oss-safeguard-20b"),
}

# Public URL of this app once deployed (Render). Enables Otari -> our MCP server and guardrail service.
# Render sets RENDER_EXTERNAL_URL automatically; PUBLIC_URL overrides it elsewhere.
PUBLIC_URL = (os.getenv("RENDER_EXTERNAL_URL") or os.getenv("PUBLIC_URL", "")).rstrip("/")
GUARD_TOKEN = os.getenv("GUARD_TOKEN", "")
MCP_URL = os.getenv("MCP_URL", f"{PUBLIC_URL}/mcp/" if PUBLIC_URL else "")
GUARD_URL = os.getenv("GUARD_URL", f"{PUBLIC_URL}/guard/{GUARD_TOKEN}" if PUBLIC_URL and GUARD_TOKEN else "")

# Per-volunteer budgets: each volunteer has their own Otari key with its own monthly budget
# (set in the dashboard). Put them in .env as VOLUNTEER_KEY_<NAME>=otk_...
VOLUNTEER_KEYS = {k[len("VOLUNTEER_KEY_"):].lower(): v for k, v in os.environ.items()
                  if k.startswith("VOLUNTEER_KEY_") and v.startswith("otk_")}
VOLUNTEERS = sorted(VOLUNTEER_KEYS)

MAX_CLAIMS = int(os.getenv("MAX_CLAIMS", "4"))
SEARCHES_PER_CLAIM = int(os.getenv("SEARCHES_PER_CLAIM", "2"))
