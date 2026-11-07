# Claim Check

Check a viral post before you share it. Paste a post, a link or a screenshot: open-weight models pull out each
claim, gather live sources, re-run the numbers, and then **a jury of models from four different labs votes on the
verdict**, so no single AI company decides what's true. Every step runs through [Otari](https://otari.ai), and the
page shows each claim marked up in the post in its verdict's colour, next to a live view of how Otari routed the check.

Built for the Mozilla Otari Hackathon - Devs Wilding Online (DoraHacks), branch `otari-hackathon`.

**Live demo:** https://claim-check-tr4f.onrender.com (free tier - first load can take ~50 s to wake up)

## What it can do
- **Paste a link.** Give it a news article or post URL: Otari's direct fetch (`POST /fetch`, about 1 s, no model) reads
  the page, menus are stripped, and the claims in it are checked. If the direct fetch fails, a model with the
  `otari_web_fetch` tool reads it instead.
- **A jury from four labs.** gpt-oss-120b (OpenAI) presides; Qwen3 30B (Alibaba), Nemotron Nano 9B (NVIDIA) and
  Gemma 4 26B (Google) weigh exactly the same evidence in parallel. A unanimous jury is shown as such; dissent is
  shown with each juror's reason, a contested verdict drops to low confidence, and only unanimous verdicts go into the
  "already checked" memory. A juror that is slow or fails is listed as "didn't vote" rather than hidden.
- **The post, marked up.** Each claim is highlighted where it appears in the post (or the article you linked), in the
  colour of its verdict, and links to its evidence.
- **A rewrite can't change the claim.** The small extractor sometimes "tidies" a claim: it once dropped "in 1975", and
  once turned "visible from the Moon" into "visible from space". If a rewrite loses a number, date or name from the
  post's own words, the claim falls back to those words, and the judges always see them.
- **Receipts from Otari's ledger.** Every call is tagged with `metadata` (app, check, role). When a check ends, the
  app looks up each request's billed cost with `GET /usage/requests/{id}` and shows whether Otari's ledger matches
  what streamed, to the micro-dollar.
- **Numbers re-run twice.** The numbers agent computes with `otari_code_execution`; then its own code is run again
  through `POST /code/execute`, with no model in the loop, to confirm it prints the result the agent reported.
- **How Otari runs the check.** A live route beside the results lights up each step from Otari's real responses:
  guardrails, the routing policy and the model it served, web searches and MCP tools called, the code sandbox, the
  jury and the metered spend, with a count of the rubric's Otari features used.
- **Draft a calm reply.** One click writes a short, friendly reply with up to two sources that you could post under
  the original (Gemma 3 27B). It never invents links: they come from the evidence.
- **Link previews.** Every shared report has a share card image (`/r/<id>/card.png`) and Open Graph tags, so a pasted
  link shows the verdicts in chats and social apps.
- **Paste text or a screenshot.** Screenshots are uploaded to Otari's Files API and read by open-weight **Gemma 3 27B**
  (paste with Ctrl+V or upload); sending the image inline is the fallback.
- **Any language.** Claims stay in the post's language and the verdict is explained in it; searches run in English and the local language.
- **"Already checked" memory.** Otari embeddings (`qwen3-embedding-0.6b`) spot a claim checked in the last 7 days and reuse its verdict
  in ~3 s instead of ~17 s. A match also needs near-identical words and the same numbers, so "...is in Paris" never reuses "...is in Berlin";
  the UI always shows which earlier claim matched.
- **Shareable reports** at `/r/<id>` and a "recent checks" list in your browser.
- **One Otari session per check** (`Otari-Conversation-Id`), so each check reads as a single session in Otari's Sessions view.
- **Accuracy:** 20 of 20 correct on a 20-claim benchmark (10 true, 10 false), with the four-lab jury unanimous on
  all 20, at a median 17.1 s and $0.016 per claim - see [BENCHMARK.md](BENCHMARK.md). The benchmark caught one real bug
  on the way: the small extractor once rewrote "Apollo 11 landed ... in 1975" without the year, so every judge saw a
  true sentence. A rewritten claim now can't drop a number or date that the post states.

## Firefox extension
Fact-check what you're reading without leaving the page: right-click selected text, a link or anywhere on a page
and choose **Check ... with Claim Check**, or type a claim into the sidebar. Firefox's sidebar shows each verdict
with its top sources and how the jury voted, then offers **Draft a calm reply** and the full report.
<kbd>Alt</kbd>+<kbd>Shift</kbd>+<kbd>K</kbd> opens the sidebar. (In the web app itself, a `?q=` link only fills in
the box; it never starts a paid check on its own.)
Load it from `about:debugging` > *This Firefox* > **Load Temporary Add-on** and pick `extension/firefox/manifest.json` (or `extension/claim-check-firefox.xpi`).
It can't read pages (permissions: `contextMenus`, `storage`, and the app's own address) and sends nothing until you ask for a check.
See [extension/firefox/README.md](extension/firefox/README.md).

## How Otari runs the check (live panel)
Beside the results, each step lights up from real response data as the check runs: the guardrail verdicts
(`Otari-Guardrails` header), the routing policy and the model it actually served (`Otari-Model`, `Otari-Fallback`),
web searches and fetches (`otari_tool_calls`), the MCP tools Otari called on Claim Check's server, the code sandbox,
the jury's labs, and the spend Otari metered on the demo key or a volunteer's own key. Underneath, a counter shows how
many of the hackathon rubric's eight Otari features this check used, and "Every call through Otari" lists each call.

## Limits and safety on the public demo
- Every check spends real money, so the demo allows 12 checks per hour per visitor and 3 at once (`RATE_PER_HOUR`,
  `MAX_CONCURRENT_CHECKS`). A shared or `?q=` link only fills in the box; it never starts a check by itself.
- Guardrails run in block mode with `on_unavailable: monitor`: if the guardrail service is down, checks continue and the
  trace says so, rather than the whole app failing.
- The guardrail endpoint lives behind a random token; Claim Check's MCP server only records calls for checks it started.
- Visitors check on the demo's own key by default; picking a volunteer (Alice or Bob) switches to that person's own Otari key and budget.
- Render's free tier sleeps after ~15 idle minutes, so the first visit can take ~50 s. A keep-warm job
  (`.github/workflows/keep-warm.yml`, disabled by default) or any uptime monitor pinging `/healthz` every 10 minutes avoids that.
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
| Jury | `alibaba/qwen3-30b-a3b`, `nvidia/nemotron-nano-9b-v2`, `google/gemma-4-26b-a4b-it` (picked for steady 1-6 s answers; Mistral Small and Llama 3.3 70B varied from 7 to 100 s on hosted providers) | - |
| Reply writer | `google/gemma-3-27b-it` | - |

Each claim is checked in parallel; every call's model, tools, tokens and cost stream to the trace panel.

## Otari features used
| Rubric feature | How Claim Check uses it | Where |
| --- | --- | --- |
| Open-weight models (x11) | Llama 3.1 8B, Qwen3-Next 80B, gpt-oss-120b, Qwen3 30B, Nemotron Nano 9B, Gemma 4 26B, Gemma 3 27B, Llama Guard 4, gpt-oss-safeguard-20b, Qwen3 Embedding 0.6B, gpt-oss-20b (+ DeepSeek V4 Flash as a backup) | `claimcheck/config.py` |
| Multiple models, distinct roles | Page reader, extractor, investigator, numbers check, presiding judge, three jurors from other labs, reply writer, screenshot reader, privacy guard, injection guard | `claimcheck/agents.py`, `claimcheck/guard.py` |
| Routing & fallbacks | Otari policies `cc-extractor` (Llama 3.1 8B -> gpt-oss-20b) and `cc-investigator` (Qwen3-Next 80B -> DeepSeek V4 Flash) and a budget tier-down `cc-judge` (gpt-oss-120b, switching to gpt-oss-20b once a volunteer has used 80% of their budget); "Simulate provider failure" switch triggers a real failover; trace reads `Otari-Fallback`, `Otari-Model`, `Otari-Attempt-Count` | `claimcheck/otari.py` |
| Web search / fetch | `otari_web_search` for every claim (up to 2 searches); `otari_web_fetch` reads any article you paste as a link (and per claim with `USE_WEB_FETCH=1`, off by default for speed). Sources the model cites but Otari never retrieved are marked unverified | `claimcheck/agents.py` |
| MCP | Claim Check's own MCP server (Wayback Machine, Wikipedia, Wikidata) passed to Otari via `mcp_servers` | `claimcheck/mcp_tools.py` |
| Guardrails | Otari's `guardrails` hook (block mode) pointed at Claim Check's own guardrail service, backed by Llama Guard 4 (privacy/doxxing) and gpt-oss-safeguard-20b (prompt injection) | `claimcheck/guard.py`, `app.py` |
| Per-user budgets | Each volunteer has their own Otari key with its own monthly budget. The picker shows what each key has left, read with that key from Otari's `GET /key/budget` (added in [#2928](https://github.com/mozilla-ai/otari/pull/2928) after our [#2863](https://github.com/mozilla-ai/otari/issues/2863)); each check reads it before and after, and the drop matches what the ledger billed; `budget_exceeded` shown in the UI | `app.py`, `claimcheck/pipeline.py`, Otari dashboard |
| Budgets | Workspace key budget caps total spend | Otari dashboard |
| Code execution | `otari_code_execution` re-runs the numbers in numeric claims (was blocked on hosted Otari by `pricing_required`, reported as mozilla-ai/otari#2719; working since 30 Oct) | `claimcheck/agents.py` |
| Sessions / traces | `Otari-Conversation-Id` per check, `User-Agent: claim-check/0.3` | `claimcheck/otari.py` |
| Embeddings | 'Already checked' memory with `qwen3-embedding-0.6b` | `claimcheck/memory.py` |
| Vision input | Screenshots read by Gemma 3 27B (inline image) | `claimcheck/agents.py` |
