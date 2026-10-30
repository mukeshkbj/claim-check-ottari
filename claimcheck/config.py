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
}

MAX_CLAIMS = int(os.getenv("MAX_CLAIMS", "4"))
SEARCHES_PER_CLAIM = int(os.getenv("SEARCHES_PER_CLAIM", "2"))
