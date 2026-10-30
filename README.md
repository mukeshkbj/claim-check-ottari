# Claim Check

Paste any viral post and an open-weight agent team pulls out each claim, gathers live sources,
re-runs the numbers and returns a cited verdict - all through [Otari](https://otari.ai).

Built for the Mozilla Otari Hackathon - Devs Wilding Online (DoraHacks), branch `otari-hackathon`.

**Live demo:** https://claim-check-tr4f.onrender.com (free tier - first load can take ~50 s to wake up)

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

## Otari features used
| Rubric feature | How Claim Check uses it | Where |
| --- | --- | --- |
| Open-weight models (x6) | Llama 3.1 8B, Qwen3 235B, gpt-oss-120b, Llama Guard 4, gpt-oss-safeguard-20b (+ gpt-oss-20b / DeepSeek V4 Flash as backups) | `claimcheck/config.py` |
| Multiple models, distinct roles | Extractor, Investigator, Judge, privacy guard, injection guard | `claimcheck/agents.py`, `claimcheck/guard.py` |
| Routing & fallbacks | Otari policies `cc-extractor` (Llama 3.1 8B -> gpt-oss-20b) and `cc-investigator` (Qwen3 235B -> DeepSeek V4 Flash); "Simulate provider failure" switch triggers a real failover; trace reads `Otari-Fallback`, `Otari-Model`, `Otari-Attempt-Count` | `claimcheck/otari.py` |
| Web search / fetch | `otari_web_search` + `otari_web_fetch` for every claim; evidence must come from retrieved pages | `claimcheck/agents.py` |
| MCP | Claim Check's own MCP server (Wayback Machine, Wikipedia, Wikidata) passed to Otari via `mcp_servers` | `claimcheck/mcp_tools.py` |
| Guardrails | Otari's `guardrails` hook (block mode) pointed at Claim Check's own guardrail service, backed by Llama Guard 4 (privacy/doxxing) and gpt-oss-safeguard-20b (prompt injection) | `claimcheck/guard.py`, `app.py` |
| Per-user budgets | Each volunteer has their own Otari key with its own monthly budget; `budget_exceeded` shown in the UI | `app.py`, Otari dashboard |
| Budgets | Workspace key budget caps total spend | Otari dashboard |
| Code execution | `otari_code_execution` re-runs the numbers in numeric claims (blocked on hosted Otari: `pricing_required`, see FEEDBACK.md) | `claimcheck/agents.py` |
