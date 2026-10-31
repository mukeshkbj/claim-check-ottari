# Claim Check accuracy benchmark

Run on 2026-10-31 against hosted Otari (EU), with the 'already checked' memory turned off so every
claim was researched from scratch. 20 well-established claims: 10 true, 10 false.
Mapping: Supported = true; False or Misleading = false; Unsupported or Can't verify = abstained.

| Result | Value |
| --- | --- |
| Accuracy on answered claims | **19/19** (100%) |
| Abstained | 1/20 |
| Median time per claim | 18.6 s (4 run in parallel) |
| Average cost per claim | $0.0157 |
| Total cost | $0.3137 |
| Second judge (Mistral Small 3.2) on its own | answered 20/20, 19 correct |
| Both judges gave the same verdict | 19/20 claims |

The verdict shown to users is the primary judge's (gpt-oss-120b via `cc-judge`); when the second judge disagrees the
app says so and lowers the confidence. The one disagreement shows why: on "the UK voted to remain", gpt-oss-120b
abstained while Mistral Small wrongly said Supported, so the second opinion flags doubt rather than overriding. Run locally, so the deployed-only guardrail and MCP hooks were not attached.

| Claim | Truth | Verdict | Second judge | | Time | Cost |
| --- | --- | --- | --- | --- | --- | --- |
| The Eiffel Tower is in Paris. | true | Supported | Supported | ✓ | 16.3 s | $0.0112 |
| Mount Everest is the highest mountain on Earth above sea level. | true | Supported | Supported | ✓ | 15.7 s | $0.0112 |
| At sea level, water boils at 100 degrees Celsius. | true | Supported | Supported | ✓ | 18.8 s | $0.0113 |
| The United Kingdom voted to leave the European Union in a 2016 referendum. | true | Supported | Supported | ✓ | 25.7 s | $0.0224 |
| UK CPI inflation reached 11.1% in the 12 months to October 2022. | true | Supported | Supported | ✓ | 20.1 s | $0.0114 |
| Canberra is the capital city of Australia. | true | Supported | Supported | ✓ | 17.1 s | $0.0111 |
| Apollo 11 landed the first humans on the Moon in 1969. | true | Supported | Supported | ✓ | 20.6 s | $0.0114 |
| The Amazon is the largest tropical rainforest in the world. | true | Supported | Supported | ✓ | 14.5 s | $0.0111 |
| Mozilla released Firefox 1.0 in 2004. | true | Supported | Supported | ✓ | 15.7 s | $0.0110 |
| The Pacific is the largest ocean on Earth. | true | Supported | Supported | ✓ | 16.6 s | $0.0112 |
| The Eiffel Tower is in Berlin. | false | False | False | ✓ | 14.7 s | $0.0112 |
| The Great Wall of China is visible from the Moon with the naked eye. | false | False | False | ✓ | 21.2 s | $0.0225 |
| Sydney is the capital city of Australia. | false | False | False | ✓ | 12.8 s | $0.0111 |
| Humans only use 10% of their brains. | false | False | False | ✓ | 25.2 s | $0.0224 |
| Apollo 11 landed the first humans on the Moon in 1975. | false | False | False | ✓ | 20.7 s | $0.0115 |
| At sea level, water boils at 50 degrees Celsius. | false | False | False | ✓ | 20.7 s | $0.0224 |
| The United Kingdom voted to remain in the European Union in the 2016 referendum. | false | Can't verify | Supported | abstained | 20.5 s | $0.0334 |
| Mount Kilimanjaro is the highest mountain on Earth above sea level. | false | False | False | ✓ | 19.9 s | $0.0225 |
| Lightning never strikes the same place twice. | false | False | False | ✓ | 15.5 s | $0.0112 |
| The Pacific is the smallest ocean on Earth. | false | False | False | ✓ | 18.4 s | $0.0222 |

Re-run with `python scripts/benchmark.py`.
