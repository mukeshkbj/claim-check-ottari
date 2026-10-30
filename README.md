# Claim Check

Paste any viral post and an open-weight agent team pulls out each claim, gathers live sources,
re-runs the numbers and returns a cited verdict - all through [Otari](https://otari.ai).

Built for the Mozilla Otari Hackathon - Devs Wilding Online (DoraHacks), branch `otari-hackathon`.

## Quick start
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env      # macOS/Linux: cp .env.example .env
# edit .env and paste your Otari key
python otari_hello.py          # first Otari call + list your models
python cli.py "paste a post"   # run a check in the terminal
uvicorn app:app --port 8000    # web app at http://127.0.0.1:8000
```

> Hosted Otari: use `OTARI_BASE_URL=https://eu.api.otari.ai/api/v1` (or your workspace's region).
> In the dashboard, turn on Tools -> Web search and Tools -> Code execution, and set a code-execution price.

## How it works
| Role | Open-weight model | Otari features |
| --- | --- | --- |
| Extractor | `meta/llama-3.1-8b-instruct` | - |
| Investigator | `alibaba/qwen3-235b-a22b-instruct-2507` | `otari_web_search`, `otari_web_fetch` |
| Numbers check | `alibaba/qwen3-235b-a22b-instruct-2507` | `otari_code_execution` |
| Judge | `openai/gpt-oss-120b` | - |

Each claim is checked in parallel; every call's model, tools, tokens and cost stream to the trace panel.

## Otari features used (planned)
- Multiple open-weight models in distinct roles (Extractor, Investigator, Judge)
- Routing + fallback
- Web search / web fetch (`otari_web_search`, `otari_web_fetch`)
- Code execution (`otari_code_execution`)
- MCP tools (Wayback Machine, Wikipedia)
- Guardrails
- Workspace budget + per-user budgets
