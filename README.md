# Claim Check

Paste any viral post and an open-weight agent team pulls out each claim, gathers live sources,
re-runs the numbers and returns a cited verdict - all through [Otari](https://otari.ai).

Built for the Mozilla Otari Hackathon - Devs Wilding Online (DoraHacks), branch `otari-hackathon`.

**Live demo:** https://claim-check-tr4f.onrender.com (free tier - first load can take ~50 s to wake up)

## What it can do
- **Paste a link.** Give it a news article or post URL: Otari's `otari_web_fetch` reads the page and the claims in it are checked.
- **Two independent judges.** Every verdict gets a second opinion from a different open-weight family (Mistral Small 3.2
  alongside gpt-oss-120b). When they disagree the report says so and lowers the confidence, and only verdicts both
  judges agree on go into the "already checked" memory.
- **Draft a calm reply.** One click writes a short, friendly reply with up to two sources that you could post under
  the original (Gemma 3 27B). It never invents links: they come from the evidence.
- **Link previews.** Every shared report has a share card image (`/r/<id>/card.png`) and Open Graph tags, so a pasted
  link shows the verdicts in chats and social apps.
- **Paste text or a screenshot.** Screenshots are read by open-weight **Gemma 3 27B** through Otari (paste with Ctrl+V or upload).
- **Any language.** Claims stay in the post's language and the verdict is explained in it; searches run in English and the local language.
- **"Already checked" memory.** Otari embeddings (`qwen3-embedding-0.6b`) spot a claim checked in the last 7 days and reuse its verdict
  in ~3 s instead of ~17 s. A match also needs near-identical words and the same numbers, so "...is in Paris" never reuses "...is in Berlin";
  the UI always shows which earlier claim matched.
- **Shareable reports** at `/r/<id>` and a "recent checks" list in your browser.
- **One Otari session per check** (`Otari-Conversation-Id`), so each check reads as a single session in Otari's Sessions view.
- **Accuracy:** on a 20-claim benchmark it answered 19 and got all 19 right; it abstained ("Can't verify") on 1.
  Median 18.6 s and $0.016 per claim, with both judges agreeing on 19 of 20 - see [BENCHMARK.md](BENCHMARK.md).

## Firefox extension
Select any claim on a web page (or right-click a link to an article) and choose **Check this claim with Claim Check**:
Firefox's sidebar opens next to the page and the verdicts stream in, with a link to the full report.
(In the web app itself, a `?q=` link only fills in the box; it never starts a paid check on its own.)
Load it from `about:debugging` > *This Firefox* > **Load Temporary Add-on** and pick `extension/firefox/manifest.json` (or `extension/claim-check-firefox.xpi`).
It can't read pages (permissions: `contextMenus`, `storage`, and the app's own address) and sends nothing until you choose the menu item. See [extension/firefox/README.md](extension/firefox/README.md).

## Live feature panel
The app shows which Otari features each check actually used, as tiles that light up from real response data: models served, routing
policy and fallback (`Otari-Fallback` header), web search calls (`otari_tool_calls`), MCP tools Otari really called on our server,
guardrail verdicts (`Otari-Guardrails` header), the volunteer's own key and budget, and metered spend.

## Limits and safety on the public demo
- Every check spends real money, so the demo allows 12 checks per hour per visitor and 3 at once (`RATE_PER_HOUR`,
  `MAX_CONCURRENT_CHECKS`). A shared or `?q=` link only fills in the box; it never starts a check by itself.
- Guardrails run in block mode with `on_unavailable: monitor`: if the guardrail service is down, checks continue and the
  trace says so, rather than the whole app failing.
- The guardrail endpoint lives behind a random token; Claim Check's MCP server only records calls for checks it started.
- Single process by design (rate limits, MCP call log and memory are in-process). Shared reports are kept on the server's disk,
  so on Render's free tier they last until the next restart.

## Tests
```bash
pip install pytest
pytest -q
```

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
| Page reader | `cc-investigator` policy: Qwen3-Next 80B | `otari_web_fetch` (when you paste a link) |
| Extractor | `cc-extractor` policy: Llama 3.1 8B (backup gpt-oss-20b) | guardrails |
| Investigator | `cc-investigator` policy: Qwen3-Next 80B (backup DeepSeek V4 Flash) | `otari_web_search` + Claim Check MCP |
| Numbers check | `cc-investigator` policy | `otari_code_execution` |
| Judge | `cc-judge` policy: gpt-oss-120b, tiers down to gpt-oss-20b at 80% of budget | - |
| Second judge | `mistralai/mistral-small-3.2-24b-instruct-2506` (picked over Llama 3.3 70B: same verdicts, 2.5 s vs 15 s) | - |
| Reply writer | `google/gemma-3-27b-it` | - |

Each claim is checked in parallel; every call's model, tools, tokens and cost stream to the trace panel.

## Otari features used
| Rubric feature | How Claim Check uses it | Where |
| --- | --- | --- |
| Open-weight models (x8) | Llama 3.1 8B, Qwen3-Next 80B, gpt-oss-120b, Mistral Small 3.2 24B, Gemma 3 27B, Llama Guard 4, gpt-oss-safeguard-20b, Qwen3 Embedding 0.6B (+ gpt-oss-20b / DeepSeek V4 Flash as backups) | `claimcheck/config.py` |
| Multiple models, distinct roles | Page reader, Extractor, Investigator, Judge, Second judge, Reply writer, Screenshot reader, privacy guard, injection guard | `claimcheck/agents.py`, `claimcheck/guard.py` |
| Routing & fallbacks | Otari policies `cc-extractor` (Llama 3.1 8B -> gpt-oss-20b) and `cc-investigator` (Qwen3-Next 80B -> DeepSeek V4 Flash) and a budget tier-down `cc-judge` (gpt-oss-120b, switching to gpt-oss-20b once a volunteer has used 80% of their budget); "Simulate provider failure" switch triggers a real failover; trace reads `Otari-Fallback`, `Otari-Model`, `Otari-Attempt-Count` | `claimcheck/otari.py` |
| Web search / fetch | `otari_web_search` for every claim (up to 2 searches); `otari_web_fetch` reads any article you paste as a link (and per claim with `USE_WEB_FETCH=1`, off by default for speed). Sources the model cites but Otari never retrieved are marked unverified | `claimcheck/agents.py` |
| MCP | Claim Check's own MCP server (Wayback Machine, Wikipedia, Wikidata) passed to Otari via `mcp_servers` | `claimcheck/mcp_tools.py` |
| Guardrails | Otari's `guardrails` hook (block mode) pointed at Claim Check's own guardrail service, backed by Llama Guard 4 (privacy/doxxing) and gpt-oss-safeguard-20b (prompt injection) | `claimcheck/guard.py`, `app.py` |
| Per-user budgets | Each volunteer has their own Otari key with its own monthly budget; `budget_exceeded` shown in the UI | `app.py`, Otari dashboard |
| Budgets | Workspace key budget caps total spend | Otari dashboard |
| Code execution | `otari_code_execution` re-runs the numbers in numeric claims (was blocked on hosted Otari by `pricing_required`, reported as mozilla-ai/otari#2719; working since 30 Oct) | `claimcheck/agents.py` |
| Sessions / traces | `Otari-Conversation-Id` per check, `User-Agent: claim-check/0.3` | `claimcheck/otari.py` |
| Embeddings | 'Already checked' memory with `qwen3-embedding-0.6b` | `claimcheck/memory.py` |
| Vision input | Screenshots read by Gemma 3 27B (inline image) | `claimcheck/agents.py` |
