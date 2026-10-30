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

| 2026-10-30 | Code execution after reporting #2719 | Re-tested the same evening: `otari_code_execution` now runs on hosted EU (computed (1648-412)/412*100 = 300 correctly). Fast turnaround. | Worked well (support) |
| 2026-10-30 | Screenshots via Otari Files | Upload works (`POST /files` returns an id), but an image referenced by `file_id` reaches the model as "[Unprocessable document attachment omitted]" for Gemma 3 27B, Qwen2.5-VL and Qwen3-VL. Inline `image_url` data URLs work for Gemma 3 27B and Qwen3-VL (not Qwen2.5-VL). So I send screenshots inline. | Friction - Files + images on hosted |
| 2026-10-30 | Rerank | `POST /rerank` returns 400 "Provider doesn't support rerank." for every embedding model in the workspace catalogue; no rerank-capable model is offered on hosted. | Missing |
| 2026-10-30 | Smart router (knn) | Creating a Smart router policy is possible in the dashboard, but teaching it needs `POST /api/v1/routing/preferences/rank`, which a workspace key can't call ("Invalid master key"). So a hosted user's smart router never learns and always serves its default. Same for `/routing/status` and `/organizations/me/aliases`. | Missing - tenant-level access to routing preferences |
| 2026-10-30 | Sessions | `Otari-Conversation-Id` groups every call of one check into a session with no other changes - easy. | Worked well |
| 2026-10-30 | Embeddings | `POST /embeddings` with `qwen3-embedding-0.6b` just worked and is cheap. | Worked well |

## Issues / PRs opened on mozilla-ai/otari
| # | Type | Title | Link |
| --- | --- | --- | --- |
| #2720 | PR (docs) | docs: name the EU host for otari.ai accounts in the EU region | https://github.com/mozilla-ai/otari/pull/2720 |
| #2719 | Bug | Hosted Otari.ai: otari_code_execution always returns 402 pricing_required, and workspaces can't set the price | https://github.com/mozilla-ai/otari/issues/2719 |
| #2721 | Bug | Hosted otari.ai: signing in on the default US region silently creates an empty second account for an EU user | https://github.com/mozilla-ai/otari/issues/2721 |
| #2722 | Feature | A keyless, open-weight guardrail on hosted otari.ai (Llama Guard 4 / gpt-oss-safeguard via /validate) | https://github.com/mozilla-ai/otari/issues/2722 |
| #2725 | Bug | Hosted otari.ai: an image uploaded to /files and referenced by file_id reaches the model as 'unprocessable attachment' | https://github.com/mozilla-ai/otari/issues/2725 |
| #2726 | Feature | Let a workspace key teach and read its own smart-router memory (routing/preferences, routing/status) on hosted otari.ai | https://github.com/mozilla-ai/otari/issues/2726 |
| #2719 | Comment | Thank-you: code execution confirmed working on hosted after the fix | https://github.com/mozilla-ai/otari/issues/2719#issuecomment-6529196072 |
| #2691 | Comment | Added code-execution repro to the existing "/api/v1/tools reports web tools as available" bug | https://github.com/mozilla-ai/otari/issues/2691#issuecomment-6526674319 |

Not filed separately (kept for the written feedback):
- Rerank: `POST /rerank` returns "Provider doesn't support rerank." for every model in the hosted catalogue - a catalogue gap rather than a bug.
- Llama 3.1 8B on Bedrock rejects `response_format` (JSON mode) and the 400 is passed straight through - belongs to any-llm per CONTRIBUTING.
- `user` field must match the key's owner; end-user budgets need a service key that personal hosted accounts can't create - docs gap.
- A key's budget dropdown can attach one key to another key's budget (Bob's key ended up on Alice's budget) - may have been a mis-click; noting as UX friction.
