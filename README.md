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
python otari_hello.py
```

## Otari features used (planned)
- Multiple open-weight models in distinct roles (Extractor, Investigator, Judge)
- Routing + fallback
- Web search / web fetch (`otari_web_search`, `otari_web_fetch`)
- Code execution (`otari_code_execution`)
- MCP tools (Wayback Machine, Wikipedia)
- Guardrails
- Workspace budget + per-user budgets
