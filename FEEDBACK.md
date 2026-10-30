# Otari feedback log

Note friction as it happens - this becomes the required feedback video + written answers.

| Date | What I was doing | What happened | Worked / friction / missing |
| --- | --- | --- | --- |
| 2026-10-30 | Signed up at otari.ai | | |

## Written answers (fill before 11 Nov)
1. When were you most tempted to skip Otari and call the provider directly? What happened?
2. What did you end up building yourself that Otari should have done for you?
3. If the rules hadn't required Otari, would you have continued using it? Why or why not?
| 2026-10-30 | First API call, following the hosted Quickstart | Quickstart says base URL `https://api.otari.ai/v1`. Real answer: 404 "Otari serves its API under /api/v1", then 421 "This API key belongs to eu.api.otari.ai". Working base URL: `https://eu.api.otari.ai/api/v1`. The error messages were excellent; the docs were wrong. | Friction (docs) - candidate GitHub issue |
| 2026-10-30 | First tool calls (web search, fetch, code exec) on a new hosted workspace | `GET /tools` lists all three as `available: true`, but calls return 403 "web search is not enabled for this workspace" and 402 `pricing_required` for code execution. Brand-new workspaces need web access turned on and a code-execution price set by hand. | Friction - `available: true` is misleading; a default price or a clearer onboarding step would help |
| 2026-10-30 | JSON mode with `meta/llama-3.1-8b-instruct` | 400 "'response_format' is not supported for bedrock". The gateway passes the upstream provider's limitation straight through; I had to add a retry without JSON mode. | Missing - gateway could emulate JSON mode, or the model catalogue could flag it |
| 2026-10-30 | Signing in to the dashboard to configure routing/budgets | The sign-in page defaults to the US region; signing in there silently created/opened a separate empty US account ($2 wallet, unused key) instead of my EU workspace. Nothing in the UI said "you have a workspace in EU". | Friction - detect the account's home region at sign-in, or warn when an account exists in another region |
| 2026-10-30 | Guardrails on hosted | `guardrails: [{profile: "prompt-injection"}]` returns 502 "no guardrails service is configured"; every catalogue guardrail needs a third-party vendor key. Worked around it by hosting my own open-weight guardrail service (Llama Guard 4 + gpt-oss-safeguard-20b) and passing its `url`. The /validate contract made that easy. | Worked well (contract) / Missing (a built-in open-weight guardrail on hosted) |
| 2026-10-30 | Per-user budgets | Sending `user` with a normal workspace key returns 403 "'user' field does not match the authenticated API key's user"; end users need a service key. Docs for creating one on hosted are thin. | Friction (docs) |
