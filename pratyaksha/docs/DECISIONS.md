# Decisions log

Each entry: what we decided, why, and what it costs us. Dated.

## 2026-11-20 — Scope for the final demo (one person, 15 days)

| Mid-sem plan | Final scope | Why |
|---|---|---|
| T1 deep + T2, T3 transfer tests | T1 deep; T2/T3 as future work (thin T2 only if time) | Depth over breadth; the faculty question "one deep use case or more?" |
| Qwen3.8-27B local | Dropped | ~16 GB+ of weights at 4-bit; does not fit a 16 GB M1 Pro with a KV cache |
| Claude Opus 5.5 as frontier reference | Gemini Flash on Google's free API tier | No Claude API key. Only generated data is sent, so the data-egress meter stays honest; free-tier data may be used by Google, which the egress meter makes visible |
| PostgreSQL 17 + pg_textsearch + bge-m3 | In-process BM25 + bge-m3 first; Postgres as optional backend | Fewer moving parts for one person; same retrieval method |
| LoRA vs full fine-tune on 0.8B–9B | LoRA on 0.8B/2B/4B; full fine-tune on 0.8B only | T4 / M1 memory |
| GraphRAG probe | One time-boxed run on sister-firm payments, or reported as skipped | Its indexing cost is the finding either way |

## 2026-11-20 — Added a no-AI rules baseline (R-rules)

A fair experiment needs a non-AI floor. If a rung cannot beat fuzzy name matching
plus an exact-amount search, that is a finding we report.

## 2026-11-20 — Cash-position rule made concrete

"Cash position within tolerance" is scored as *misbooked rupees*: the sum of
amounts on entries handled automatically **and** wrong. Entries sent to a person
are pending, not wrong. Tolerance ₹1,000 (provisional).

## 2026-11-20 — Test split held out

All development on dev (month 5). The test split (month 6) is run once per rung
after the acceptance bar is frozen.

## 2026-11-22 — Where things run

Colab (T4) for development runs and all training; the MacBook only for the final measured runs
and the live demo. Why: the "owned machine" claim needs speed and ₹ measured on owned hardware,
but repeated experiments and training are faster on Colab's GPU.

## 2026-11-22 — Step 2 choices

| Choice | Why |
|---|---|
| Qwen3.5-0.8B first, 2B optional | Smallest first: if retrieval helps a 0.8B model, that is the strongest owned-AI story |
| Keyword search on 3-letter pieces (BM25), not words | Narrations are truncated, lose spaces (UPI) and have typos; word search fails on all three |
| bge-m3 meaning search optional (`--opt dense=BAAI/bge-m3`) | Party names are proper nouns; meaning search adds less here. Measured, not assumed |
| Reranker bge-reranker-v2-m3 (Apache-2.0), retrieve 10 → keep 3 | Licence allows commercial use; keeping 3 shortens the prompt |
| Model must answer in JSON; ids it was never shown are dropped | An invoice the system never showed is a hallucination, not an answer |
| duplicate / unknown / short payment always go to review | Business rule from the acceptance bar, enforced in code, not left to the model |
| Colab latency is batched (8 at a time) | Development speed. True one-at-a-time latency is measured on the Mac at the end |

## 2026-11-22 — R3 design: code computes, the model chooses

| Choice | Why |
|---|---|
| Code computes amount matches; model picks one option id | Step 2: models listed all invoices because they cannot add; the report's rule says the LLM never does arithmetic |
| E-mails filtered to candidate parties or the exact amount, max 3 | The right information, not more: ~14 e-mails arrive in any 5-day window |
| A no-LLM control on the same context | Otherwise R3's gain would be credited to the model when the code did it |
| Acceptance bar: added "handles ≥ 50% by itself" | A system that sends everything to a person "passed" in Step 2 |

## 2026-11-23 — R5 fine-tuning design

| Choice | Why |
|---|---|
| Train on months 1–4 of the same business | A business fine-tunes on its own past reconciliations; dev/test months never seen |
| Same R3 prompt as input | One change per rung: only the weights change between R3 and R5 |
| Short target (option id + needs_review) | Shorter answers are faster; confidence for the R6 gate will come from token probabilities, not text |
| Target needs_review = gold flag | Fixes the measured over-caution while risky categories stay forced to review in code |
| "U" as the target when the right answer is not among options | Teach the model to abstain rather than guess |
| Clean + stress versions of each line | So the model learns messy narrations too |
| LoRA on 0.8B and 2B; full fine-tune on 0.8B only | T4 memory; LoRA vs full comparison from the mid-sem plan |
| 4B re-run with thinking off, clean only | Verify the fix cheaply before spending more GPU time |
| Laya System-1 model moved to Step 5 (R6) | Time; the gate decision is where a System-1 model belongs |

## 2026-11-23 — R6 / R7 / test-month design

| Choice | Why |
|---|---|
| Safety rule in code (regex over all matching e-mails), not in the model | Step 4: fine-tuning erased the behaviour (full FT 0/5) |
| Gate on the model's token probability, not its written flag | The written flag was over-cautious (R3-2B) and unlearned by training (R5); token probability is measurable and can be calibrated |
| Threshold chosen on dev = lowest passing the bar on both conditions | Most automation that still meets the rules; never tuned on test |
| R6 control (no AI) as a system | Otherwise the guardrail's effect would be credited to the model |
| Acceptance bar frozen 23 Nov before the test month | Results on test must not influence the rules |
| Test month: rules, R3 control, R6 control, R5 LoRA 0.8B, R6 on LoRA 0.8B / LoRA 2B / full 0.8B | The main rungs once each, clean and messy |

## 2026-11-23 — Back to the mid-sem plan: Claude Opus 5.5 for R7, and Laya as the System-1 model

Earlier the same day R7 had been switched to Gemini (no Claude API key at the time) and Laya had been left out.
Both departed from the plan presented at mid-sem and were reversed:

| Choice | Why |
|---|---|
| R7 = Claude Opus 5.5 (native Claude API), on **every** dev and test line | As planned at mid-sem; ~$4–8 for 708 lines at $4 / $20 per million tokens, so no slice is needed |
| Opus goes through the same R6 rules; gate on its written flag | The API gives no token probability; guardrail and forced reviews still apply, like for like |
| Laya (typed-decisions checkpoint, 421M, 1,024 tokens) fine-tuned with `laya-train` on months 1–4 | As planned: "System-1 decision models, fine-tuned per task"; zero-shot Laya is near chance by its own model card |
| Laya answers two questions: `match` (choice among the computed options) and `person` (must a person check?) | The same two decisions the generative models make, on the same evidence |
| `--shuffle-options` when training Laya | The right option is usually M1; shuffling stops Laya learning "always pick the first" |
| Laya gated by its probability for the chosen option, with the same guardrail and forced reviews | Like for like with the Qwen models |
| Test month only after Laya and Opus are ready | Every system faces the final exam at once; nothing changed after seeing test results |
| R7 API budget (checked 23 Nov 2026): Claude Console balance was $0.00, with no free credit; the minimum purchase is $5 | Opus 5.5 is only available through the paid API. A Claude Pro subscription does not include API use. The $5 is enough to run the test month (estimated $2–4) after a 3-line cost check (cell 6a) |
| Thresholds for the test month: the lowest threshold on the grid that passes the bar on both dev conditions (all five came out 0.0) | Chosen on dev only, by a rule written before seeing test, so the test result is honest |
| Test month (month 6) was run once, on 23 Nov 2026, and nothing will be changed in response to it | The test month is the final exam; any later improvement (e.g. better retrieval) is reported as future work or measured on dev only |
| Add a paired significance check (`scripts/significance.py`: exact McNemar plus a bootstrap 95% interval) | The gaps between systems on test are 2–5 lines of 185; the report must say whether they are real or could be luck |
| Demo: local web app (`python -m demo.server`), standard-library HTTP server, one HTML page; Opus replayed from its recorded test run at its recorded speed; models load from the Mac with Hugging Face offline mode | Runs with no internet or API key in class; nothing new to install; every recorded answer is labelled, so the demo cannot overstate anything |
| Demo backup: `--replay` mode serves the recorded Mac answers for every system | If a model fails to load in class, the demo still runs with real, labelled results |
