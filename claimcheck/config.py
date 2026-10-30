import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("OTARI_BASE_URL", "https://eu.api.otari.ai/api/v1")
API_KEY = os.getenv("OTARI_API_KEY", "")

# One open-weight model per role (override any of them in .env)
MODELS = {
    "extractor": os.getenv("MODEL_EXTRACTOR", "cc-extractor"),        # Otari policy: Llama 3.1 8B -> gpt-oss-20b
    "investigator": os.getenv("MODEL_INVESTIGATOR", "cc-investigator"),  # Otari policy: Qwen3-Next 80B -> DeepSeek V4 Flash
    "numbers": os.getenv("MODEL_NUMBERS", "cc-investigator"),
    "judge": os.getenv("MODEL_JUDGE", "cc-judge"),  # Otari budget tier-down: gpt-oss-120b, gpt-oss-20b once 80% of budget used
    "guard_privacy": os.getenv("MODEL_GUARD_PRIVACY", "meta/llama-guard-4-12b"),
    "guard_injection": os.getenv("MODEL_GUARD_INJECTION", "openai/gpt-oss-safeguard-20b"),
    "reader": os.getenv("MODEL_READER", "google/gemma-3-27b-it"),        # reads screenshots of posts
    "embedder": os.getenv("MODEL_EMBEDDER", "alibaba/qwen3-embedding-0.6b"),  # 'already checked' memory
    "judge2": os.getenv("MODEL_JUDGE2", "mistralai/mistral-small-3.2-24b-instruct-2506"),  # second opinion, other family (2.5 s vs 15 s for Llama 3.3 70B)
    "fetcher": os.getenv("MODEL_FETCHER", "cc-investigator"),            # reads a linked article via web fetch
    "replier": os.getenv("MODEL_REPLIER", "google/gemma-3-27b-it"),  # drafts a calm reply
}
SECOND_OPINION = os.getenv("SECOND_OPINION", "1") == "1"

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
USE_WEB_FETCH = os.getenv("USE_WEB_FETCH", "0") == "1"

DATA_DIR = os.getenv("DATA_DIR", "data")
MEMORY_MIN_SIMILARITY = float(os.getenv("MEMORY_MIN_SIMILARITY", "0.93"))
MEMORY_MIN_OVERLAP = float(os.getenv("MEMORY_MIN_OVERLAP", "0.8"))
MAX_IMAGE_CHARS = 4_000_000  # ~6 MB image as a data URL
