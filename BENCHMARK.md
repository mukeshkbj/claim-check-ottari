# Claim Check accuracy benchmark

Run on 2026-10-30 against hosted Otari (EU), with the 'already checked' memory turned off so every
claim was researched from scratch. 20 well-established claims: 10 true, 10 false.
Mapping: Supported = true; False or Misleading = false; Unsupported or Can't verify = abstained.

| Result | Value |
| --- | --- |
| Accuracy on answered claims | **19/19** (100%) |
| Abstained | 1/20 |
| Median time per claim | 22.8 s (4 run in parallel) |
| Average cost per claim | $0.0237 |
| Total cost | $0.4744 |

| Claim | Truth | Verdict | | Time | Cost |
| --- | --- | --- | --- | --- | --- |
| The Eiffel Tower is in Paris. | true | Supported | ✓ | 17.1 s | $0.0108 |
| Mount Everest is the highest mountain on Earth above sea level. | true | Supported | ✓ | 27.9 s | $0.0212 |
| At sea level, water boils at 100 degrees Celsius. | true | Supported | ✓ | 23.2 s | $0.0215 |
| The United Kingdom voted to leave the European Union in a 2016 referendum. | true | Supported | ✓ | 28.8 s | $0.0430 |
| UK CPI inflation reached 11.1% in the 12 months to October 2022. | true | Supported | ✓ | 22.2 s | $0.0216 |
| Canberra is the capital city of Australia. | true | Supported | ✓ | 17.8 s | $0.0220 |
| Apollo 11 landed the first humans on the Moon in 1969. | true | Supported | ✓ | 29.9 s | $0.0432 |
| The Amazon is the largest tropical rainforest in the world. | true | Supported | ✓ | 24.3 s | $0.0216 |
| Mozilla released Firefox 1.0 in 2004. | true | Supported | ✓ | 24.2 s | $0.0438 |
| The Pacific is the largest ocean on Earth. | true | Supported | ✓ | 22.5 s | $0.0211 |
| The Eiffel Tower is in Berlin. | false | False | ✓ | 19.1 s | $0.0110 |
| The Great Wall of China is visible from the Moon with the naked eye. | false | False | ✓ | 20.5 s | $0.0107 |
| Sydney is the capital city of Australia. | false | False | ✓ | 24.4 s | $0.0214 |
| Humans only use 10% of their brains. | false | False | ✓ | 25.1 s | $0.0215 |
| Apollo 11 landed the first humans on the Moon in 1975. | false | Can't verify | abstained | 18.8 s | $0.0426 |
| At sea level, water boils at 50 degrees Celsius. | false | False | ✓ | 19.6 s | $0.0111 |
| The United Kingdom voted to remain in the European Union in the 2016 referendum. | false | False | ✓ | 26.2 s | $0.0215 |
| Mount Kilimanjaro is the highest mountain on Earth above sea level. | false | False | ✓ | 23.0 s | $0.0217 |
| Lightning never strikes the same place twice. | false | False | ✓ | 22.5 s | $0.0219 |
| The Pacific is the smallest ocean on Earth. | false | False | ✓ | 22.2 s | $0.0214 |

Re-run with `python scripts/benchmark.py`.
