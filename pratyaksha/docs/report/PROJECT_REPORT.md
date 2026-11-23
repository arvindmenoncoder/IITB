# PRATYAKSHA — Project Report

Team T-19 · IIT Bombay ePGD AI & DS · Nov 23, 2026 · @Arvind

## Executive summary

On the held-out test month, small fine-tuned models running locally matched Claude Opus 5.5 on bank reconciliation (91.4% vs 89.7% clean, difference not significant). On a ₹1.75 lakh MacBook Pro they were about 3–9× faster and about 70–220× cheaper per line, gave identical answers to the Colab runs on all 1,480 lines, and sent no data off the machine.

- **What we built:** a reconciliation pipeline for an Indian MSME. It matches bank entries to customers and invoices and decides whether a person must check each one. We built it as a ladder of seven rungs (R0–R7) plus a fine-tuned System-1 model (Laya), all measured by one harness against a business acceptance bar frozen on 23 Nov 2026.
- **What passed:** every gated system (R6) and Opus passed the bar on the unseen month, in both clean and messy conditions, with 0 wrong automatic entries. The one exception is the untrained 2B model at 0.74%, which is within the 1% limit.
- **Where the gain comes from:** the large, significant improvement (+15 points clean, +33 messy over rules, p < 0.001) comes from the engineered pipeline: retrieval, computed match options, forced reviews and a bank-detail guardrail. The language model adds 2–3 lines out of 185 on top of that, which is consistent in direction but not statistically significant on one month.
- **Best efficiency:** Laya reached the same clean accuracy as the best model at 0.27–0.28 s per line and about ₹2.3 per 1,000 lines, measured on the MacBook.
- **Next lever:** 14–18 errors per condition happen because the right answer was never offered to the model. Better retrieval, not a bigger model, is the next improvement.

## Problem and goal

The question is what each AI technique buys an Indian MSME, in quality, latency, cost and data control, when the AI runs on hardware the business owns. We are measuring this, not building a product.

- **Task T1, bank reconciliation:** for every bank entry, decide who paid, which invoices it settles (including TDS deducted, short and clubbed payments), and whether a person must check it.
  - Why this task: it is daily work in every MSME, mistakes cost money directly, and it mixes reading messy text with arithmetic.
- **Why local models:** bank lines and remittance e-mails hold customer names, amounts and account details. A cloud model sees all of it; a local one sends nothing out.
- **Why a ladder:** we add one technique per rung and measure each with the same harness. This shows what each technique adds, instead of a single before/after number.
- **Why a frontier reference (Claude Opus 5.5):** it shows the best accuracy available today with the same evidence, and what it costs in money, latency and data sent off the machine.

## Test bed: the WWI-IN world

All systems are tested on WWI-IN, a generated Indian MSME world modelled on Microsoft's Wide World Importers (seed 7, fully reproducible). Every gold answer is computed from the generator's records, never typed by hand.

| Item | Count |
| --- | --- |
| Customers | 60 |
| Suppliers | 8 |
| GST invoices | 1,361 |
| Bank entries (6 months, FY 2026-27) | 997 |
| Remittance e-mails | 501 |

| Category | Meaning |
| --- | --- |
| full\_payment | one invoice, exact amount |
| clubbed\_payment | several invoices in one payment |
| tds\_deduction | invoice(s) minus TDS on the value before GST |
| short\_payment | paid less; the rest stays open |
| duplicate\_credit | the bank posted the same credit twice |
| unknown\_party | payer not in the customer master |
| bank\_charges, interest\_credit, supplier\_payment | non-receivable lines |

- **Two conditions:** clean narrations, and stress narrations (cut to 28–40 characters, aliases and initials, typos, dropped invoice references).
  - Why: real bank narrations are messy, so a system that only works on clean text is not usable.
- **Time-based splits:** train = months 1–4, dev = month 5 (177 lines per condition), test = month 6 (185 lines per condition, held out until the bar was frozen).
  - Why: it copies real use. A model is trained on the past and judged on a month it has never seen.
- **No look-ahead:** a system only sees invoices that existed and were unpaid on the entry's date.
- **9 gold-consistency tests** (balances replay, amounts add up, each invoice settled once) run before any model. The suite has grown to 35 tests.

## How we measure

Every run, from the rules baseline to Opus, is scored by one shared harness on the same gold answers, and judged against a business acceptance bar frozen on 23 Nov 2026 before the test month was run.

| Metric | What it tells the business |
| --- | --- |
| Strict accuracy | category, party and exact invoice set all right |
| Handled automatically | share of lines booked with no person involved |
| Error rate on automatic | wrong bookings nobody looks at (the real risk) |
| Misbooked rupees | money booked wrongly and automatically |
| p50 / p95 latency | typical and slow time per line |
| ₹ per 1,000 lines | operating cost (GPU time or API fees) and hardware amortisation |
| Data leaving the machine | bytes sent to an outside service |
| Restricted-field leaks | account numbers or similar appearing in output |
| Party recall, option recall | whether the right answer was even offered to the model |

**Acceptance bar.** A system is usable only if all five rules hold:

| # | Rule | Limit | Why |
| --- | --- | --- | --- |
| 1 | Error rate on automatic lines | ≤ 1% | unchecked wrong bookings are the main risk |
| 2 | Misbooked rupees | ≤ ₹1,000 | the cash position must stay trustworthy |
| 3 | Unexplained entries | 100% surfaced | nothing unexplained is booked quietly |
| 4 | Bank-detail change requests | 100% to a person | a classic payment-fraud route |
| 5 | Handled automatically | ≥ 50% | sending everything to a person must not pass |

Rules 1–4 come from the mid-sem report. Rule 5 was added on 22 Nov, after a system passed rules 1–4 by sending every line to a person (see the problems section). Thresholds are chosen on dev only and applied unchanged to test.

## The ladder

Each rung adds one technique on top of the one before, so each step's gain can be measured on its own.

| Rung | What it adds | Why |
| --- | --- | --- |
| R-rules | no AI: fuzzy name plus exact-amount search | the honest floor every AI rung must beat |
| R0 | Qwen3.5-0.8B with only the bank line | "fail first": what a model does with no context |
| R1 | BM25 retrieval over 3-letter pieces of names/aliases (top 5 parties and their open invoices) | gives the model the records it needs |
| R2 | retrieve 10, rerank with bge-reranker-v2-m3, keep 3 | a shorter, better-ordered prompt |
| R3 | context engineering: code computes match options (exact, clubbed, TDS at 0.1/1/2%, short ≤ 6%), adds up to 3 remittance e-mails and a duplicate option D, plus U "none of these"; the model answers with one option id | the model never does arithmetic, only chooses |
| R3 control | same context, always pick M1 (no model) | proves what the model adds beyond the code |
| R4 | error analysis: every dev line put in one bucket | decides what fine-tuning should fix |
| R5 | LoRA (r = 16) and full fine-tuning of Qwen3.5 0.8B / 2B on months 1–4; loss on answer tokens only | teaches the model the task's habits |
| R6 | gate: bank-detail guardrail over all e-mails, forced reviews (duplicate, unknown, short), option-probability threshold chosen on dev | safety decided by checkable rules, not the model's word |
| Laya | a 421M non-generative System-1 decision model (ModernBERT-large), fine-tuned to answer "which option" and "must a person check", routed through the same R6 gate | fast, cheap decisions without text generation |
| R7 | Claude Opus 5.5 via the API, with the same retrieval, options and e-mails, routed through the R6 rules | frontier reference, for comparison only |

## Step 1: the no-AI floor

A careful rules system reached 80.8% on clean dev and 59.9% on stress, with zero wrong automatic entries. It failed the bar only because it never reads e-mails, so it misses bank-detail changes.

| System | Cond | Accuracy | Auto | Auto error | p50 | Bank-detail → person | Bar |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Rules (no AI) | clean | 80.8% | 71.8% | 0.00% | \~0.13 s | 1/5 | FAIL |
| Rules (no AI) | stress | 59.9% | 53.1% | 0.00% | \~0.09 s | 2/5 | FAIL |

- **Main error, wrong party:** 30 misses on clean and 65 on stress. Name matching breaks on truncated, aliased and misspelt narrations.
- **TDS lines collapse under stress:** 81.0% → 38.1%.
- **Finding:** who paid (entity resolution) is the first bottleneck, not invoice matching. Any AI rung must beat 81% with zero automatic errors, not a strawman.

## Step 2: retrieval and reranking (R0–R2)

Giving a small model the right records was necessary but not enough. Every R0–R2 run scored far below the rules baseline.

**Retrieval alone** (dev, payments only, n = 163): the right party was in the top 5 for 90.2% of clean and 87.7% of stress lines. All 15 clean misses at top 10 are structural: 11 cheque deposits with no name and 4 payments by a sister firm.

| System | Cond | Accuracy | Auto | Auto error | p50 | Prompt tokens | Unusable output |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R0 Qwen3.5-0.8B (n = 40) | clean | 0.0% | 67.5% | 100% | 0.66 s | 320 | 0 |
| R1 0.8B (top 5) | clean | 0.6% | 0.0% | – | 1.51 s | 1,929 | 77 |
| R2 0.8B (10 → 3) | clean | 0.0% | 0.0% | – | 1.60 s | 1,340 | 34 |
| R1 2B (top 5) | clean | 45.8% | 81.9% | 45.5% | 1.92 s | 1,929 | 22 |
| R2 2B (10 → 3) | clean | 45.2% | 83.6% | 46.0% | 1.75 s | 1,340 | 23 |
| R2 2B (10 → 3) | stress | 41.2% | 83.0% | 51.0% | 1.76 s | 1,291 | 22 |

1. **A model alone is dangerous:** R0 booked 67.5% of lines automatically and all of them were wrong (₹34.9 lakh misbooked on 40 lines).
2. **Small models cannot do the arithmetic:** the 2B model got 70% of single exact payments but 0% of clubbed, TDS and short payments.
   - Why it matters: this set the design rule for R3, that code computes the amounts and the model only chooses.
3. **The model's own "needs review" flag is not trustworthy:** the 2B model booked 84% automatically and was wrong on 46% of those (₹1.39 crore misbooked on clean dev).
4. **Unusable output had one cause:** the model started a valid answer, then listed every open invoice until the token limit cut it off.
5. **Reranking bought speed, not accuracy:** 45.8% vs 45.2% at 2B, with a 31% shorter prompt and about 9% lower latency.

## Step 3: context engineering (R3)

Context engineering was the largest single jump in the ladder. The same 2B model went from 45.2% to 89.8% on clean (41.2% → 88.7% stress), with a prompt 2.5× shorter (about 1,300 → 526 tokens) and 2.4× lower latency.

| System | Cond | Accuracy | Auto | Auto error | p50 | Bank-detail → person | Unusable | Bar |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| R3 control (no AI) | clean | 89.8% | 82.5% | 0.0% | 0.10 s | 0/5 | 0 | FAIL |
| R3 control (no AI) | stress | 88.1% | 80.8% | 0.0% | 0.11 s | 0/5 | 0 | FAIL |
| R3 0.8B | clean | 63.8% | 57.1% | 0.0% | 0.75 s | 1/5 | 4 | FAIL |
| R3 2B | clean | 89.8% | 26.0% | 0.0% | 0.73 s | 5/5 | 1 | FAIL (auto < 50%) |
| R3 2B | stress | 88.7% | 19.8% | 0.0% | 0.76 s | 5/5 | 2 | FAIL (auto < 50%) |
| R3 4B (first run) | clean | 2.3% | 0.0% | – | 2.33 s | – | 177 | FAIL |

1. **Computed context alone beats the rules:** the no-AI control gained 9 points on clean and 28 on stress. The stress gain comes mostly from e-mails, which name the payer when the narration does not.
2. **The option ceiling:** the right answer was among the options for 94.4% (clean) and 92.1% (stress) of dev lines. No model at R3 can score above this.
3. **The 2B model tied the control on accuracy but did different things:** on clean it fixed 5 lines (duplicates, e-mail evidence) and broke 5 (short payments answered "U").
4. **The 2B model read the e-mails:** it sent 5/5 bank-detail changes to a person (control 0/5).
5. **It was over-cautious:** it sent 74–80% of lines to a person while being right on almost all of them, so it failed the ≥ 50% rule.
6. **No automatic errors at R3 for any model (0.0%), and no restricted-field leaks.** The option design made the models safe; usefulness was the remaining problem.
7. **The 4B model produced nothing usable** (177/177): it "thinks" by default and ran out of tokens. With thinking switched off, 0 of 177 outputs were unusable (see the problems section).

## Step 4: error analysis (R4) and fine-tuning (R5)

Fine-tuning took the 0.8B model from 63.8% to 93.8% on clean dev (+30 points), 99% of the option ceiling, with 0 automatic errors. It also weakened a safety behaviour, which is why safety moved into code at R6.

**R4, error analysis.** Every dev line was put in one bucket, to see which errors training could fix:

| Model | Cond | Correct + auto | Correct + review (over-caution) | Wrong, right option offered | Right option not offered | Unusable |
| --- | --- | --- | --- | --- | --- | --- |
| R3 2B | clean | 46 | **113** | 8 | 9 | 1 |
| R3 2B | stress | 35 | **122** | 9 | 9 | 2 |
| R3 0.8B | clean | 101 | 12 | **51** | 9 | 4 |
| R3 0.8B | stress | 98 | 11 | **53** | 9 | 6 |

- **Decision: fine-tune.** The 2B model's problem was over-caution and the 0.8B model's was wrong choices; both are teachable. Only 9 lines (5.1%) needed better options.
- **Training data:** 1,270 examples (months 1–4, clean + stress), target `{"option", "needs_review"}`. 102 lines had no right option and were taught to answer "U" and ask a person. Dev and test were never used, and a test enforces this.

**R5, training on a Colab T4 (2 epochs, 318 optimiser steps).**

| Run | Trainable parameters | Wall time | Loss start → end |
| --- | --- | --- | --- |
| LoRA 0.8B | 10.8 M of 864 M (1.25%) | 54.5 min | 0.95 → 0.006 |
| LoRA 2B | 16.8 M of 2,230 M (0.75%) | 53.0 min | 0.90 → 0.000 |
| Full 0.8B | 853 M (100%) | 42.4 min | 0.95 → 0.016 |

**R5 results (dev).**

| System | Cond | Accuracy | Auto | Auto error | p50 | Out tokens | Bank-detail → person | Bar |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| R3 4B, thinking off | clean | 81.9% | 70.6% | 0.0% | 1.50 s | 41 | 5/5 | PASS |
| R5 LoRA 0.8B | clean | 93.8% | 82.5% | 0.0% | 0.35 s | 15 | 3/5 | FAIL |
| R5 LoRA 0.8B | stress | 93.2% | 81.9% | 0.0% | 0.35 s | 15 | 3/5 | FAIL |
| R5 LoRA 2B (stop fix) | clean | 94.4% | 81.9% | 0.0% | 0.38 s | 14 | 4/5 | FAIL |
| R5 LoRA 2B | stress | 93.2% | 80.2% | 0.0% | 0.87 s\* | 74\* | 5/5 | PASS |
| R5 full 0.8B | clean | 93.8% | 84.2% | 0.0% | 0.35 s | 14 | 0/5 | FAIL |
| R5 full 0.8B | stress | 93.2% | 83.6% | 0.0% | 0.33 s | 14 | 0/5 | FAIL |

\* Run before the stop-token fix; accuracy is unaffected.

1. **After fine-tuning, model size stopped mattering:** 0.8B ≈ 2B (93.8% vs 94.4% clean, 93.2% vs 93.2% stress).
2. **Over-caution cured safely:** the 2B model handled 26.0% automatically at R3 and 81.9% at R5, with 0.0% automatic errors in every R5 run.
3. **Faster and cheaper:** 15 output tokens instead of 42; latency 0.75 → 0.35 s.
4. **Fine-tuning weakened a safety behaviour:** bank-detail changes sent to a person fell from 5/5 (untrained 2B) to 4/5 (LoRA 2B), 3/5 (LoRA 0.8B) and 0/5 (full 0.8B). The more weights change, the more of the base model's careful e-mail reading is lost.
   - Why it matters: safety must sit in code, not in a learned habit. This led directly to the R6 guardrail.
5. **Full fine-tuning bought no accuracy over LoRA** (identical 93.8% / 93.2%) and needs a 3.4 GB model copy instead of a small adapter.
6. **After fine-tuning, the model is no longer the bottleneck:** wrong choices fell from 51 to 1 (0.8B, clean). The remaining 10–11 errors are answers the options never offered.
7. **Training cost:** about 54 min of T4 time per model, roughly ₹27 at a ₹30/h rented-GPU rate, paid once.

## Step 5 on dev: the R6 gate, Laya and Opus 5.5

With a code guardrail and forced reviews, every system passed the bar on dev, including the no-AI control. Laya and Opus 5.5 both reached the option ceiling exactly.

**What R6 adds:**

- **Guardrail:** any e-mail near the payment that asks to change bank details sends the line to a person. It checks all matching e-mails, not only the 3 shown to the model. Before any model run it caught 5/5 per condition, with 7/177 (4.0%) false alarms.
- **Forced reviews:** duplicates, unknown payers and short payments always go to a person.
- **Threshold:** the model's probability for the option id it wrote must reach a threshold chosen on dev.

| System | Cond | Accuracy | Auto | Auto error | Misbooked ₹ | p50 | Bank-detail → person | Bar |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| R6 control (no AI) | clean | 89.8% | 75.7% | 0.00% | 0 | 0.10 s | 5/5 | PASS |
| R6 Qwen3.5-2B (untrained) | clean | 89.8% | 76.8% | 0.74% | 236 | 0.65 s | 5/5 | PASS |
| R6 LoRA 0.8B | clean | 93.8% | 77.4% | 0.00% | 0 | 0.34 s | 5/5 | PASS |
| R6 LoRA 2B | clean | 94.4% | 77.4% | 0.00% | 0 | 0.42 s | 5/5 | PASS |
| R6 full 0.8B | clean | 93.8% | 77.4% | 0.00% | 0 | 0.35 s | 5/5 | PASS |
| R6 Laya | clean | 94.4% | 77.4% | 0.00% | 0 | 0.065 s (Laya only†) | 5/5 | PASS |
| R7 Opus 5.5 | clean | 94.4% | 70.6% | 0.00% | 0 | 2.41 s | 5/5 | PASS |
| R6 control (no AI) | stress | 88.1% | 73.4% | 0.00% | 0 | 0.11 s | 5/5 | PASS |
| R6 Qwen3.5-2B (untrained) | stress | 88.7% | 75.7% | 0.75% | 236 | 0.70 s | 5/5 | PASS |
| R6 LoRA 0.8B | stress | 93.2% | 76.3% | 0.00% | 0 | 0.34 s | 5/5 | PASS |
| R6 LoRA 2B | stress | 93.2% | 75.7% | 0.00% | 0 | 0.41 s | 5/5 | PASS |
| R6 full 0.8B | stress | 93.2% | 76.3% | 0.00% | 0 | 0.34 s | 5/5 | PASS |
| R6 Laya | stress | 93.8% | 76.3% | 0.00% | 0 | 0.067 s (Laya only†) | 5/5 | PASS |
| R7 Opus 5.5 | stress | 93.8% | 67.2% | 0.00% | 0 | 2.64 s | 5/5 | PASS |

Dev option ceiling: 94.4% clean, 93.8% stress.

**Laya training.** 1,270 lines × 2 questions = 2,540 items (2,286 train, 254 calibration). Options were shuffled so Laya could not learn "always pick M1". 144 optimiser updates over 4 epochs took 18.7 min on a T4. On the calibration slice, accuracy rose from 82.7% to 87.0% and ECE fell from 0.174 to 0.110.

**Opus 5.5.** Same prompt, options and e-mails, through the native API, with answers cached. It used 717–720 input and 152–164 output tokens per line (thinking is billed as output). The dev run cost $2.12, 19% above the 3-line estimate.

**Threshold knob.** The rule picks the lowest threshold that passes the bar on both dev conditions; it chose 0.0 for all five models.

| Model | Auto at threshold 0.0 → 0.999 (clean) | ECE clean / stress | Lines at probability ≥ 0.999 (clean) and how many were right |
| --- | --- | --- | --- |
| Qwen3.5-2B (untrained) | 76.8% → 0.0% | 0.130 / 0.142 | none above 0.99 |
| LoRA 0.8B | 77.4% → 75.7% | 0.052 / 0.063 | 158, 96.8% right |
| LoRA 2B | 77.4% → 76.3% | 0.051 / 0.060 | 159, 96.9% right |
| Full 0.8B | 77.4% → 65.0% | 0.046 / 0.055 | 135, 96.3% right |
| Laya | 77.4% → 77.4% (flat) | 0.047 / 0.058 | 170, 97.1% right |

1. **A no-AI system passes the bar once code reads the e-mails.** The AI's value has to be shown on top of this.
2. **The guardrail repaired in code what fine-tuning broke:** 5/5 for every model, compared with 0–4/5 without it.
3. **The probability threshold adds little once the rules exist.** The fine-tuned models put most lines at ≥ 0.999 probability and are right about 96–97% of the time there. The forced reviews and the guardrail keep the automatic errors at 0.
4. **The untrained 2B model is the exception:** a threshold of 0.8 would remove its errors but drops stress automation to 47.5% (< 50%), so the rule keeps 0.0 and its 0.74% errors.
5. **Opus was the most cautious:** it handled 11–13 points fewer lines automatically than the fine-tuned models, at the same accuracy.

## Final test month results and significance

On the held-out month, all seven gated systems and Opus passed the frozen bar in both conditions. The fine-tuned local models scored highest (91.4% clean, 89.2% stress), but no difference between AI systems is statistically significant.

*(Chart in the online report: test-month accuracy per system, clean vs messy, with the best-possible lines at 92.4% and 90.3%. The same numbers are in the tables below.)*

Thresholds were taken from dev (all 0.0) and applied once. Nothing was changed after the test run.

| System | Auto clean / stress | Auto error | Misbooked ₹ | p50 | ₹ per 1,000 (operating) | Data sent out | Bank-detail → person (clean / stress) | Bar |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Rules (no AI) | 67.6% / 49.2% | 0.0% | 0 | 0.09–0.14 s | 0.8–1.1 | 0 | 2/7, 4/7 | FAIL |
| R3 control (no guardrail) | 81.6% / 80.5% | 0.0% | 0 | 0.10 s | 0.8–0.9 | 0 | 1/7, 1/7 | FAIL |
| R6 control (no AI) | 74.1% / 74.1% | 0.0% | 0 | 0.10 s | 0.8–0.9 | 0 | 7/7, 7/7 | PASS |
| R5 LoRA 0.8B (no guardrail) | 80.0% / 78.9% | 0.0% | 0 | 0.33 s | 2.9 | 0 | 7/7, **6/7** | PASS / **FAIL** |
| R6 Qwen 2B, untrained | 73.5% / 73.0% | 0.74% | 590 | 0.68 s | 5.8–5.9 | 0 | 7/7, 7/7 | PASS |
| R6 LoRA 0.8B | 75.7% / 75.1% | 0.0% | 0 | 0.34 s | 2.9 | 0 | 7/7, 7/7 | PASS |
| R6 LoRA 2B | 75.7% / 74.6% | 0.0% | 0 | 0.41 s | 3.5 | 0 | 7/7, 7/7 | PASS |
| R6 full FT 0.8B | 75.7% / 75.1% | 0.0% | 0 | 0.34 s | 2.9 | 0 | 7/7, 7/7 | PASS |
| R6 Laya | 75.7% / 75.1% | 0.0% | 0 | **\~0.17 s†** | **\~1.4†** | 0 | 7/7, 7/7 | PASS |
| R7 Claude Opus 5.5 | 71.9% / 65.4% | 0.0% | 0 | 2.3–2.4 s | 479–501 | 298–305 KB | 7/7, 7/7 | PASS |

† Corrected estimate. The logged Laya time (0.068 s, ₹0.59 per 1,000) counted only Laya's own forward pass. Every other system's time also includes search, reranking and option building, which take about 0.10 s (the no-AI control's time). Like for like, Laya is about 0.17 s per line. Laya itself is about 3.5× faster than the 0.8B model's answer step. The timing code is fixed. Measured end to end on the MacBook, Laya takes 0.27–0.28 s per line (Step 6). Accuracy is unaffected.

**Where the remaining errors are** (`error_analysis.py`, test):

| System | Cond | Wrong, right option offered | Right option not offered |
| --- | --- | --- | --- |
| Fine-tuned models and Laya | clean | 2 (short payments) | 14 |
| Fine-tuned models and Laya | stress | 2–3 | 18 |
| Claude Opus 5.5 | clean | 5 (3 full, 2 short payments) | 14 |
| Claude Opus 5.5 | stress | 5 | 18 |

**Is the difference real?** Paired exact McNemar test plus a bootstrap 95% interval, on the same 185 lines (`significance.py`). "Fixes" are lines one system got right and the other wrong.

| Comparison | Clean: fixes / breaks, p | Stress: fixes / breaks, p |
| --- | --- | --- |
| Fine-tuned 0.8B vs no-AI control | 3 / 0, p = 0.25 | 2 / 0, p = 0.50 |
| Laya vs no-AI control | 3 / 0, p = 0.25 | 2 / 1, p = 1.00 |
| Opus 5.5 vs no-AI control | 3 / 3, p = 1.00 | 2 / 3, p = 1.00 |
| Fine-tuned 0.8B vs Opus 5.5 | 3 / 0, p = 0.25 | 3 / 0, p = 0.25 |
| Untrained 2B vs no-AI control | 3 / 8, p = 0.23 | 2 / 7, p = 0.18 |
| Rules vs no-AI control | 0 / 28, p < 0.001 | 1 / 62, p < 0.001 |

1. **Local fine-tuned models matched the frontier model.** Same accuracy within noise; on the owned MacBook about 3–9× faster and about 70–220× cheaper per line, and no data sent out.
2. **The engineered pipeline makes the big, significant gain** (+15 points clean, +33 stress over rules). The language model's extra 2–3 lines are consistent in direction but not significant.
   - Why the test cannot decide: with only 3 lines of disagreement, the smallest possible p is 0.25. About 6 one-sided wins would be needed for p < 0.05.
3. **The guardrail proved itself on unseen data:** the one fine-tuned system without it missed a bank-detail change and failed.
4. **Laya was the efficiency winner:** best-model accuracy on clean (1 line behind on stress) at 0.27–0.28 s per line and about ₹2.3 per 1,000 lines on the MacBook (about 3× faster than the fine-tuned 0.8B there). It chose M1 on 159–162 lines, M2 on 2–3 and U on 20–24.
5. **The test month was harder for retrieval:** party recall fell from 95.9% to 93.8% (clean) and 95.3% to 91.6% (stress), so the ceiling fell to 92.4% / 90.3%. Most remaining errors are answers never offered.
6. **Opus API spend for the project:** about $4.18 (3-line check, dev and test).

## Problems, failures and fixes

We recorded every failure as a result. Each failure below changed the design that followed, and together they explain how we reached the final pipeline. The full engineering log (about 70 entries) is in `docs/WHAT_DIDNT_WORK.md`.

| Date | Step | What went wrong | How we found it | What we changed | Result |
| --- | --- | --- | --- | --- | --- |
| 20 Nov | 1 | Short initials-style aliases (e.g. "SG TRD") matched the wrong customer; rules scored 23.7% on clean data | 130 "not retrieved" errors on clean data made no sense | Ignore aliases under 6 characters, compare without spaces, credit truncated prefixes; check wrong party before retrieval in the error taxonomy | 23.7% → 80.8% |
| 20 Nov | 1 | Our own gold answers failed our own bar (unexplained short payments marked safe) | A test scoring gold against itself | `needs_review = not explained`; an explicit bank-detail-change flag | Evaluator tested before any model |
| 22 Nov | 2 | Retrieval cannot find payers the narration does not name (cheques, sister firms) | Top-10 miss analysis | Reported as the R1/R2 ceiling; R3 adds amount matching and e-mails | Stress party recall 87.7% → 93.6% at R3 |
| 22 Nov | 2 | Small models listed every open invoice and were cut off (77/177 unusable at 0.8B) | Raw-output check | R3: the model answers with one option id, 80-token limit | Unusable outputs fell to 0–6 per run |
| 22 Nov | 2 | The bar was "passed" by a system that sent every line to a person | Reading the Step 2 table | Added rule 5: ≥ 50% handled automatically | No do-nothing system can pass |
| 22 Nov | 2 | Models could not add or subtract (0% on clubbed, TDS, short) | Category breakdown | Code computes the amounts; the model only chooses | 2B: 45.2% → 89.8% |
| 22 Nov | 3 | Qwen3.5-4B produced nothing usable (177/177) | Raw outputs: plain-text "Thinking Process" | `enable_thinking=False`; parser reports `thinking_cutoff` | 0/177 unusable, 81.9%, first full PASS |
| 22 Nov | 3 | The 2B model sent 74–80% of lines to a person while \~90% right | R4 buckets | Fine-tuning (R5) and a gate decided by evidence (R6) | Automatic handling 26% → 82% |
| 23 Nov | 4 | Free Colab GPU quota stopped the R5 evaluation | Session stopped | Resume notebook (adapters already saved to Drive); bought 100 Colab compute units | All R5 runs completed |
| 23 Nov | 4 | Resume errors: `No module named pratyaksha`, torchao/peft import error | User's own diagnosis (setup cells skipped) | Every notebook cell now sets its own folder; setup always runs first | Resolved |
| 23 Nov | 4 | Fine-tuned 2B did not stop after answering (73 tokens instead of 14) | Output-token count in the scorecard | Explicit stop tokens \`< | im\_end |
| 23 Nov | 4 | Fine-tuning weakened bank-change detection (5/5 → 3/5; full fine-tune 0/5) | Scorecards | R6 code guardrail independent of the model | 5/5 dev, 7/7 test for every gated system |
| 23 Nov | 5 | The guardrail first caught 4/5: the e-mail was 4th and cut by the 3-e-mail limit | Workspace check before Colab | Guardrail scans all matching e-mails; prompt unchanged | 5/5 both conditions |
| 23 Nov | 5 | R7 was briefly switched to another model and Laya dropped, departing from the mid-sem plan | Team review | Restored to the plan: Claude Opus 5.5 for R7, Laya fine-tuned | Plan followed in full |
| 23 Nov | 5 | Opus cost 19% above the 3-line estimate (thinking tokens on harder lines) | Console balance | Run order kept budget safe | Total spend about $4.18 |
| 23 Nov | 5 | Laya training warnings: calibration temperature at its clamp, "conflicting schema", some negative step losses | Training log | Recorded; schema risk checked on test (0 lines affected) | Results unaffected; causes not yet explained |
| 23 Nov | 5 | Run-name parsing bug in `same_lines.py` | Testing the new significance script | `split("_", 1)` | No logged result affected |
| 23 Nov | 5 | Step 3 claim "only the model can catch bank changes" proved wrong | R6 control 7/7 on test | Corrected in the findings log | Code meets the rule alone |

**Found on 23 Nov while preparing Step 6:** Laya's logged time counted only its own forward pass, not the search and option-building steps that every other system's time includes. We found it by reading the timing code, fixed it, added a test, and corrected every speed and cost ratio in this report (marked †). Accuracy was not affected.

**Lessons we would pass on:**

1. Test the evaluator before any model.
2. Read raw outputs, not only scores: a correct answer can hide wasted work.
3. Safety rules belong in code, not in learned behaviour.
4. A safety bar needs a usefulness rule beside it, or "refuse everything" wins.
5. Defaults can differ by model size, so a bigger model is not a drop-in replacement.

## Key design decisions

Each decision below was made for a stated reason, and the full dated log is in `docs/DECISIONS.md`.

| Decision | Why |
| --- | --- |
| One deep task (T1, reconciliation), not three shallow ones | Depth over breadth; each technique's effect can only be measured cleanly on one task |
| A no-AI rules baseline, and a no-AI control at R3 and R6 | Otherwise gains made by code would be credited to the model |
| Time-based splits; test month held out until the bar was frozen | Copies real use and keeps the final numbers honest |
| Character 3-gram BM25 instead of word search | Narrations are truncated, lose spaces (UPI) and have typos; word search fails on all three |
| Code computes the amounts; the model picks one option id | Step 2 showed small models cannot add; an id it was never shown counts as a hallucination |
| Duplicates, unknown payers and short payments always go to a person | A business rule enforced in code, not left to the model |
| Fine-tune on months 1–4 of the same business; target = option id + needs\_review | A business learns from its own past reconciliations; a short answer is faster |
| "U" as the target when the right answer is not offered | Teaches the model to abstain rather than guess |
| LoRA on 0.8B and 2B, full fine-tune on 0.8B; 4B evaluated at R3 | After fine-tuning, 0.8B matched 2B, so a larger adapter would add memory cost without an expected gain; the T4 holds a full fine-tune only at 0.8B |
| The safety rule lives in code (regex over all matching e-mails) | Fine-tuning erased the model's own bank-change detection |
| Gate on token probability, not the model's written flag; threshold = lowest passing on both dev conditions | The written flag was over-cautious, then unlearned; probability can be measured and calibrated |
| Opus 5.5 through the same R6 rules, gated on its written flag | The API gives no token probability; like-for-like safety rules still apply |
| Laya trained with shuffled options | The right answer is usually M1; shuffling stops it learning "always pick the first" |
| Colab T4 for development and training; the MacBook for final latency and the demo | The "owned machine" claim needs speed measured on owned hardware |
| A paired significance test on the test month | The gaps between systems are 2–5 lines out of 185 |

## Limitations

The results hold for one generated business, one held-out month and one task. These limits bound what can be claimed.

- **Generated data:** WWI-IN is realistic but synthetic. Real narrations and e-mails vary more than our generator.
- **One test month, 185 lines per condition:** too few disagreements between systems for significance on gaps of 2–5 lines.
- **Few bank-detail changes:** 5 per condition on dev and 7 on test, so one line decides rule 4.
- **The guardrail is a regular expression written against our own e-mail wording.** Real use would need broader patterns or a classifier, with its misses measured.
- **The acceptance bar values are provisional,** taken from the mid-sem report and not reviewed by a chartered accountant.
- **The 3-e-mail prompt limit hid the payment's own e-mail on 3 messy dev lines.** The prompt was kept unchanged so that Steps 3–5 stay comparable.
- **Laya training warnings** (calibration clamp, schema conflict, negative step losses) are recorded but not yet explained. The schema risk did not arise on test (0 lines with the right answer at option 3 or later, 0 duplicates).
- **Qwen3.5's two fast kernels are NVIDIA-only, so the 0.8B model ran on slower reference code on both Colab and the Mac; its speed is a lower bound. Mac power was assumed (35 W), not measured; it is under 1% of the owned-machine cost.**
- **Opus 5.5 gives no token probability,** so its gate uses its written flag. This is a different gate from the local models, though the code rules are the same.

## Step 6: the owned machine (MacBook Pro)

On a MacBook Pro 2021 (Apple M1 Pro, 16 GB RAM) bought for ₹1,75,000, the same frozen systems gave identical answers to Colab on all 1,480 lines (4 systems × 2 conditions × 185), with speed and cost measured one line at a time. Nothing was retrained or re-tuned.

| System | Cond | Accuracy (Colab = Mac) | Same answer as Colab | p50 / p95 | ₹ per 1,000 (power + laptop) | Data sent out | Bar |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Rules (no AI) | clean | 74.6% | 185/185 | 0.059 / 0.095 s | 0.48 | 0 | FAIL |
| R6 control (no AI) | clean | 89.7% | 185/185 | 0.110 / 0.123 s | 0.91 | 0 | PASS |
| R6 Laya | clean | 91.4% | 185/185 | 0.279 / 0.361 s | 2.35 | 0 | PASS |
| R6 LoRA 0.8B | clean | 91.4% | 185/185 | 0.863 / 0.981 s | 7.00 | 0 | PASS |
| Rules (no AI) | stress | 55.1% | 185/185 | 0.035 / 0.079 s | 0.32 | 0 | FAIL |
| R6 control (no AI) | stress | 88.1% | 185/185 | 0.106 / 0.120 s | 0.88 | 0 | PASS |
| R6 Laya | stress | 88.6% | 185/185 | 0.271 / 0.348 s | 2.26 | 0 | PASS |
| R6 LoRA 0.8B | stress | 89.2% | 185/185 | 0.854 / 0.997 s | 7.00 | 0 | PASS |
| R7 Opus 5.5 (API, reference) | clean / stress | 89.7% / 87.6% | – | 2.27 / 2.44 s (p50) | 479 / 501 | about 1.6 KB per line | PASS |

Cost assumptions: the laptop's ₹1,75,000 is spread over 6,000 working hours (3 years × 250 days × 8 h); power is assumed at 35 W and ₹8/kWh.

1. **The results do not depend on the hardware:** every answer on the Mac's Apple GPU matched Colab's NVIDIA GPU.
2. **Measured speed:** Laya takes 0.27–0.28 s per line, about 3× faster than the fine-tuned 0.8B (0.85–0.86 s). Search and option building take 0.11 s of each.
3. **Against Opus, like for like:** Opus is about 2.6–2.9× slower than the fine-tuned 0.8B and 8–9× slower than Laya. It costs about 70× (vs the 0.8B) to 200–220× (vs Laya) more per line, and it is the only system that sends data out.
4. **The owned-machine cost is the laptop, not electricity:** power is under 1% of the cost, so the assumed wattage changes no conclusion.
5. **Throughput:** Laya handles about 12,900 lines an hour on the laptop and the 0.8B model about 4,200, so a small business's monthly statement takes minutes.

## What remains: Step 6

Steps 1–5 are complete and the test-month numbers are final. Step 6 adds owned-machine measurements and the demo; it does not change any result above.

- [x] Mac M1 Pro runs: one-line-at-a-time latency and ₹ per 1,000 for Laya, the fine-tuned 0.8B and the no-AI control (done 23 Nov, see Step 6)
- [ ] Demo: side-by-side answers, data-sent-out meter, live step trace, threshold knob
- [ ] Final report: this document plus the demo
- [ ] Final deck and rehearsal for the demo on Dec 5, 2026

Identified improvements, measured on dev only so that the test month stays untouched:

1. Better retrieval and option building, the source of 14–18 errors per condition.
2. Ranking e-mails by exact amount before the 3-e-mail limit.
3. Short-payment options, the remaining wrong-choice category for every model.

## Appendix: reproducibility, files and costs

Every number in this report comes from a run folder under `runs/` (predictions, summary, scorecard, config) and a line in `runs/index.csv`, and can be re-run from the same seed.

| Item | Where |
| --- | --- |
| World generator (seed 7) | `pratyaksha/world/` |
| Harness, scoring, acceptance bar | `pratyaksha/harness/`, `docs/ACCEPTANCE_BAR.md` |
| Systems R-rules to R7, Laya | `pratyaksha/systems/` |
| Retrieval and reranker | `pratyaksha/retrieval/` |
| Model backends (Hugging Face, OpenAI-compatible, Anthropic) | `pratyaksha/llm/backend.py` |
| Fine-tuning data and training | `pratyaksha/finetune/` |
| Analysis scripts | `scripts/compare.py`, `error_analysis.py`, `vs_control.py`, `threshold_sweep.py`, `significance.py` |
| Colab notebooks | `step2_R0_R1_R2`, `step3_R3`, `step4_R4_R5`, `step4_resume`, `step5_R6_R7_test`, `step5b_laya_opus_test` |
| Tests | 35 passing (`tests/`) |
| Logs | `docs/FINDINGS_LOG.md`, `docs/WHAT_DIDNT_WORK.md`, `docs/DECISIONS.md` |

| Model | Source | Licence |
| --- | --- | --- |
| Qwen3.5-0.8B / 2B / 4B | Alibaba Qwen team | Apache-2.0 |
| bge-reranker-v2-m3 | BAAI | Apache-2.0 |
| Laya (typed-decisions, 421M) | convaiinnovations/laya | Apache-2.0 |
| Claude Opus 5.5 | Anthropic API, $4 / $20 per million input / output tokens | commercial API |

| Spend | Amount |
| --- | --- |
| Colab compute units (pay-as-you-go) | 100 units (\~1.96 units per T4 hour) |
| Opus 5.5 API: 3-line check + dev (354 lines) + test (370 lines) | about $4.18 |
| Training, one-time per model (T4) | 18.7 min (Laya) to 54.5 min (LoRA 0.8B) |
