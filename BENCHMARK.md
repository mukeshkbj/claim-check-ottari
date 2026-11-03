# Claim Check accuracy benchmark

Run on 2026-11-03 against hosted Otari (EU), with the 'already checked' memory turned off so every
claim was researched from scratch. 20 well-established claims: 10 true, 10 false.
Mapping: Supported = true; False or Misleading = false; Unsupported or Can't verify = abstained.

| Result | Value |
| --- | --- |
| Accuracy on answered claims | **20/20** (100%) |
| Abstained | 0/20 |
| Median time per claim | 17.1 s (4 run in parallel) |
| Average cost per claim | $0.0159 |
| Total cost | $0.3186 |
| Jury unanimous (all four labs agree) | 20/20 claims |
| Contested (most jurors disagree with the presiding judge) | 0/20 claims |

The verdict shown is the presiding judge's (gpt-oss-120b via `cc-judge`, OpenAI). Jurors from Alibaba (Qwen3 30B),
NVIDIA (Nemotron Nano 9B) and Google (Gemma 4 26B) weigh the same evidence; when they disagree the app says so and
lowers the confidence. Run locally, so the deployed-only guardrail and MCP hooks were not attached.

| Claim | Truth | Verdict | Jury votes | | Time | Cost |
| --- | --- | --- | --- | --- | --- | --- |
| The Eiffel Tower is in Paris. | true | Supported | Alibaba: Supported, NVIDIA: Supported, Google: Supported | ✓ | 21.4 s | $0.0114 |
| Mount Everest is the highest mountain on Earth above sea level. | true | Supported | Alibaba: Supported, Google: Supported | ✓ | 23.6 s | $0.0116 |
| At sea level, water boils at 100 degrees Celsius. | true | Supported | Alibaba: Supported, Google: Supported | ✓ | 24.6 s | $0.0114 |
| The United Kingdom voted to leave the European Union in a 2016 referendum. | true | Supported | Alibaba: Supported, Google: Supported | ✓ | 22.0 s | $0.0113 |
| UK CPI inflation reached 11.1% in the 12 months to October 2022. | true | Supported | Alibaba: Supported, NVIDIA: Supported, Google: Supported | ✓ | 29.7 s | $0.0233 |
| Canberra is the capital city of Australia. | true | Supported | Alibaba: Supported, NVIDIA: Supported, Google: Supported | ✓ | 24.1 s | $0.0114 |
| Apollo 11 landed the first humans on the Moon in 1969. | true | Supported | Alibaba: Supported, NVIDIA: Supported, Google: Supported | ✓ | 25.1 s | $0.0228 |
| The Amazon is the largest tropical rainforest in the world. | true | Supported | Alibaba: Supported, NVIDIA: Supported, Google: Supported | ✓ | 26.4 s | $0.0227 |
| Mozilla released Firefox 1.0 in 2004. | true | Supported | Alibaba: Supported, NVIDIA: Supported, Google: Supported | ✓ | 19.9 s | $0.0216 |
| The Pacific is the largest ocean on Earth. | true | Supported | Alibaba: Supported, NVIDIA: Supported, Google: Supported | ✓ | 15.5 s | $0.0225 |
| The Eiffel Tower is in Berlin. | false | False | Alibaba: False, NVIDIA: False, Google: False | ✓ | 14.6 s | $0.0115 |
| The Great Wall of China is visible from the Moon with the naked eye. | false | False | Alibaba: False, NVIDIA: False, Google: False | ✓ | 15.1 s | $0.0226 |
| Sydney is the capital city of Australia. | false | False | Alibaba: False, NVIDIA: False, Google: False | ✓ | 14.2 s | $0.0113 |
| Humans only use 10% of their brains. | false | False | Alibaba: False, NVIDIA: False, Google: False | ✓ | 16.7 s | $0.0119 |
| Apollo 11 landed the first humans on the Moon in 1975. | false | False | Alibaba: False, NVIDIA: False, Google: False | ✓ | 15.8 s | $0.0119 |
| At sea level, water boils at 50 degrees Celsius. | false | False | Alibaba: False, NVIDIA: False, Google: False | ✓ | 14.1 s | $0.0116 |
| The United Kingdom voted to remain in the European Union in the 2016 referendum. | false | False | Alibaba: False, NVIDIA: False, Google: False | ✓ | 17.5 s | $0.0229 |
| Mount Kilimanjaro is the highest mountain on Earth above sea level. | false | False | Alibaba: False, NVIDIA: False, Google: False | ✓ | 15.7 s | $0.0225 |
| Lightning never strikes the same place twice. | false | False | Alibaba: False, NVIDIA: False, Google: False | ✓ | 13.8 s | $0.0114 |
| The Pacific is the smallest ocean on Earth. | false | False | Alibaba: False, NVIDIA: False, Google: False | ✓ | 10.7 s | $0.0111 |

Re-run with `python scripts/benchmark.py`.
