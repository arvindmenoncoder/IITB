# Findings log — the source for the final report

One entry per step, with the numbers that back it up. Every number points to a run
in `runs/index.csv` (or a script anyone can re-run). Updated after each step.

| Step | Date | Status |
|---|---|---|
| 1. Data, harness, no-AI baseline | 20–22 Nov 2026 | Done; reproduced on Colab |
| 2. R0 / R1 / R2 (lookup, reranking) | 22 Nov 2026 | Done (Colab T4) |
| 3. R3 context engineering | 22 Nov 2026 | Done (Colab T4); 4B failure fixed in Step 4 (thinking off) |
| 4. R4–R5 fine-tuning | 23 Nov 2026 | Done (Colab T4; finished with paid compute units) |
| 5. R6 gates, Laya, R7 Opus, test month | 23 Nov 2026 | Done (Colab T4 + Anthropic API); test month run once, results frozen |
| 6a. Mac owned-machine runs | 23 Nov 2026 | Done (MacBook Pro, mps); 1,480/1,480 answers identical to Colab |
| 6b. Demo, final report, deck | — | Not started |

---

## Step 1 — Test bed, examiner, and the no-AI floor

**Built**
- WWI-IN: generated Indian MSME world (seed 7). 60 customers, 8 suppliers, 1,361 GST invoices,
  997 bank entries, 501 remittance e-mails, six months of FY 2026-27. Gold answers computed, not typed.
- Clean and stress narrations; time-based splits (train months 1–4, dev month 5, test month 6 held out).
- One harness: strict accuracy, auto-rate, auto-error-rate, p50/p95, ₹ per 1,000 (operating vs
  amortisation), data egress, restricted-field leaks, business acceptance bar.
- 9 tests on the gold answers (balances replay, amounts add up, no look-ahead, each invoice settled once).

**Results (dev, n = 177)** — run on Colab 22 Nov 2026, identical to the workspace run

| System | Condition | Accuracy | Auto-handled | Auto error | p50 | Bar |
|---|---|---|---|---|---|---|
| Rules (no AI) | clean | 80.8% | 71.8% | 0.00% | ~0.13 s | FAIL |
| Rules (no AI) | stress | 59.9% | 53.1% | 0.00% | ~0.09 s | FAIL |

Breakdown that matters:
- Main error is **wrong party**: 30 (clean) and 65 (stress) of the misses. Name matching breaks
  on truncated, aliased and typo'd narrations.
- TDS payments drop from 81.0% (clean) to 38.1% (stress).
- Fails the bar only on **bank-detail changes**: 1/5 (clean) and 2/5 (stress) sent to a person,
  because rules never read remittance e-mails.
- Never books a wrong entry automatically (0%): when unsure it sends to a person.
- Data egress 0 bytes; cost close to ₹0.

**Findings**
1. A careful non-AI baseline already reaches 81% on clean data with zero automatic errors. Any AI
   rung must beat this, not a strawman.
2. Entity resolution (who paid?), not invoice matching, is the first bottleneck.
3. Two bugs found by testing the evaluator before any model (see WHAT_DIDNT_WORK.md): short aliases
   matched wrong customers (23.7% → 80.8% after fix); our own gold answers failed our own bar.

---

## Step 2 — Retrieval and reranking (R0, R1, R2)

**Built**
- R0: Qwen3.5-0.8B with only the bank line.
- R1: BM25 over character 3-grams of names/aliases (optional bge-m3 + RRF); top-5 parties and their
  open invoices on that date go in the prompt.
- R2: retrieve 10 → bge-reranker-v2-m3 → keep 3.
- Model output parsed as JSON; ids never shown to the model are dropped; duplicate / unknown / short
  payment forced to review. 22 tests pass.

**Measured before any model run (retrieval alone, dev, payments only, n = 163)**

| Top-k | Clean | Stress |
|---|---|---|
| 1 | 89.0% | 78.5% |
| 3 | 89.6% | 83.4% |
| 5 | 90.2% | 87.7% |
| 10 | 90.8% | 87.7% |

- All 15 clean misses at top-10 are structural: 11 cheque deposits with no name, 4 sister-firm payments.
- **Finding:** name retrieval caps R1/R2 at ~90% (clean) regardless of the model. Amount-based matching
  and e-mails (R3) and the GraphRAG probe are the only routes past it.

**Model results (dev, Colab T4, float16, batch 8)** — run 22 Nov 2026

| System | Cond | n | Accuracy | Auto | Auto error | p50 | Party found | Prompt tokens | Unusable output | Old bar |
|---|---|---|---|---|---|---|---|---|---|---|
| Rules (no AI) | clean | 177 | 80.8% | 71.8% | 0.0% | 0.13 s | – | – | – | FAIL |
| Rules (no AI) | stress | 177 | 59.9% | 53.1% | 0.0% | 0.09 s | – | – | – | FAIL |
| R0 Qwen3.5-0.8B | clean | 40 | 0.0% | 67.5% | 100% | 0.66 s | – | 320 | 0 | FAIL |
| R1 Qwen3.5-0.8B (top 5) | clean | 177 | 0.6% | 0.0% | – | 1.51 s | 90.6% | 1,929 | 77 | "PASS"* |
| R1 Qwen3.5-0.8B (top 5) | stress | 177 | 1.1% | 0.0% | – | 1.56 s | 88.3% | 1,907 | 73 | "PASS"* |
| R2 Qwen3.5-0.8B (10→3) | clean | 177 | 0.0% | 0.0% | – | 1.60 s | 90.6% | 1,340 | 34 | "PASS"* |
| R2 Qwen3.5-0.8B (10→3) | stress | 177 | 0.0% | 0.0% | – | 1.59 s | 86.0% | 1,291 | 27 | "PASS"* |
| R2 Qwen3.5-2B (10→3) | clean | 177 | 45.2% | 83.6% | 46.0% | 1.75 s | 90.6% | 1,340 | 23 | FAIL |
| R2 Qwen3.5-2B (10→3) | stress | 177 | 41.2% | 83.0% | 51.0% | 1.76 s | 86.0% | 1,291 | 22 | FAIL |

\* passed only because it sent every line to a person (auto 0%). The bar now also requires ≥ 50% handled
automatically, so these are FAIL under the revised bar.

R2 Qwen3.5-2B by category (clean): full_payment 70.4%, supplier_payment 100%, **clubbed 0%, TDS 0%,
short 0%**, duplicate 0%, unknown 0%. Bank-detail changes to a person: 0 of 5.

**Why the output was unusable (raw outputs checked):** all failures were `no_json`, and in every sample
the model had started a valid answer but listed *every* open invoice of the customer until the 160-token
limit cut it off (0.8B: 77/177, 2B: 23/177). It is not a formatting problem: the model cannot choose
invoices by amount, so it lists them all.

Latency note: Colab printed that two fast GPU kernels (causal_conv1d, flash-linear-attention) were not
installed, so the slower reference code ran. Colab latency is not the final number; owned-machine latency
is measured on the Mac.

**Findings**
1. **The model alone is useless and dangerous (R0):** 0% correct, yet it auto-handled 67.5% of lines
   with 100% of those wrong (₹34.9 lakh misbooked on 40 lines). A model that guesses confidently is worse
   than no model.
2. **Retrieval is necessary but not sufficient:** with the right customer in the prompt ~90% of the time,
   the 0.8B model still scored ~0%. It cannot use what it is given.
3. **Model size matters here:** same input, 0.8B → 2B took accuracy from 0% to 45% (clean) and 41% (stress).
4. **Small models cannot do the arithmetic:** 2B gets single exact payments (70%) but 0% on clubbed, TDS
   and short payments, which all need adding or subtracting. This supports the design rule that the
   language model never does arithmetic: R3 gives it computed amount matches.
5. **The model's own "needs review" is not trustworthy:** 2B auto-handled 84% and was wrong on 46% of
   those (₹1.39 crore misbooked on clean dev). R6 needs a gate that is checked against data, not the
   model's word.
6. **Reranking (R2 vs R1):** at 0.8B no accuracy difference can be seen (both ~0%). Keeping 3 candidates
   cut the prompt by 30% (1,929 → 1,340 tokens) with the same party recall on clean (90.6%) and slightly
   lower on stress (88.3% → 86.0%). R1 was not run at 2B, so R1 vs R2 at a size where the model works is
   still open.
7. **Every R1/R2/R2-2B run is far below the no-AI rules (80.8% / 59.9%).** At this rung, AI does not yet
   earn its place.

---

## Step 3 — Context engineering (R3)

**Built** (`pratyaksha/systems/r3_context.py`)
- Code computes **match options**: invoice sets of the candidate parties that explain the amount exactly
  (one / two / three invoices), minus TDS at 0.1 / 1 / 2% of taxable value, or a small short payment
  (≤ 6%). Up to 8 options, invoices named in the narration or an e-mail first.
- **Remittance e-mails** from the last 5 days: from candidate parties, or quoting this exact amount
  (max 3). An e-mail sender becomes a candidate party.
- **Identical earlier credit** within 2 days → a "D" (duplicate) option. "U" (none of these) always.
- The model answers with **one option id**; 80-token limit.
- **Control (no model):** same context, always pick M1 (else U). The model must beat this.
- Prompt size drops from ~1,300–1,900 tokens (R1/R2) to ~340.

**Control measured in the workspace (dev, keyword retrieval order, no reranker)**

| System | Cond | Accuracy | Auto | Auto error | Party found | Right answer among options |
|---|---|---|---|---|---|---|
| R3 control (no AI) | clean | 90.4% | 83.1% | 0.0% | 95.9% | 94.4% |
| R3 control (no AI) | stress | 88.1% | 80.8% | 0.0% | 93.6% | 92.1% |

**Findings so far**
1. **Computed context beats both the rules and every model so far, with no model at all:** +9.6 points
   (clean) and **+28.2 points (stress)** over the rules baseline. The stress gain comes mostly from the
   e-mails, which name the payer and the invoices when the narration does not (party found 87.7% → 93.6%).
2. The right answer is among the options for 94.4% / 92.1% of lines: this is the ceiling for any model
   at R3. A model's job is now the remaining judgment: choosing between options and reading e-mails.
3. Still fails the bar on bank-detail changes (0 of 5): picking an option does not read the e-mail's
   request. This is the clearest job left for the language model (or a guardrail at R6).

**Results (dev, Colab T4, real reranker)** — run 22 Nov 2026

| System | Cond | Accuracy | Auto | Auto error | p50 | Prompt tokens | Bank-detail → person | Unusable | Bar |
|---|---|---|---|---|---|---|---|---|---|
| Rules (Step 1) | clean | 80.8% | 71.8% | 0.0% | 0.13 s | – | 1/5 | – | FAIL |
| R1 2B (top 5) | clean | 45.8% | 81.9% | 45.5% | 1.92 s | 1,929 | 0/5 | 22 | FAIL |
| R1 2B (top 5) | stress | 40.7% | 80.8% | 50.3% | 1.95 s | 1,907 | 0/5 | 21 | FAIL |
| R2 2B (10→3) *(Step 2)* | clean | 45.2% | 83.6% | 46.0% | 1.75 s | 1,340 | 0/5 | 23 | FAIL |
| R2 2B (10→3) *(Step 2)* | stress | 41.2% | 83.0% | 51.0% | 1.76 s | 1,291 | 0/5 | 22 | FAIL |
| **R3 control (no AI)** | clean | **89.8%** | 82.5% | 0.0% | 0.10 s | 339 | 0/5 | 0 | FAIL |
| **R3 control (no AI)** | stress | **88.1%** | 80.8% | 0.0% | 0.11 s | 341 | 0/5 | 0 | FAIL |
| R3 0.8B | clean | 63.8% | 57.1% | 0.0% | 0.75 s | 526 | 1/5 | 4 | FAIL |
| R3 0.8B | stress | 61.6% | 55.4% | 0.0% | 0.78 s | 527 | 3/5 | 6 | FAIL |
| **R3 2B** | clean | **89.8%** | 26.0% | 0.0% | 0.73 s | 526 | **5/5** | 1 | FAIL (auto < 50%) |
| **R3 2B** | stress | **88.7%** | 19.8% | 0.0% | 0.76 s | 527 | **5/5** | 2 | FAIL (auto < 50%) |
| R3 4B | clean | 2.3% | 0.0% | – | 2.33 s | 524 | (all to review) | 177 | FAIL |
| R3 4B | stress | 2.3% | 0.0% | – | 2.34 s | 525 | (all to review) | 177 | FAIL |

(Workspace control numbers were 90.4% / 88.1% with keyword order; with the real reranker on Colab: 89.8% / 88.1%.
Prompt tokens differ between control and models because the control is counted by a rough estimate.)

R3 2B vs control, line by line (`vs_control.py`): clean — model fixes 5, breaks 5; stress — fixes 6, breaks 5.
- **Fixes:** duplicates (picks D; the control never can), clubbed/TDS when the right option was not first,
  and on stress a cheque deposit and a cut-off name resolved "via e-mail".
- **Breaks:** short payments answered "U, unknown party, confidence 0.1" although the payer's option was
  listed; a bank charge booked as a supplier payment.

**Findings**
1. **Reranking bought no accuracy at 2B** (R1 45.8% vs R2 45.2% clean; 40.7% vs 41.2% stress). It bought a
   31% shorter prompt (1,929 → 1,340 tokens) and ~9% lower latency (1.92 → 1.75 s). Its value here is speed,
   not quality.
2. **Context engineering is the largest jump in the ladder so far.** Same 2B model: R2 45.2% → R3 89.8%
   (clean), 41.2% → 88.7% (stress), with a prompt 2.5× shorter and latency 2.4× lower (1.75 → 0.73 s), ₹ per
   1,000 from 14.6 to 6.4 (Colab GPU rate).
3. **It also rescued the smallest model:** 0.8B went from 0% (R2) to 63.8% / 61.6%, with 0% automatic errors.
4. **The 2B model matches the no-AI control on accuracy (89.8% = 89.8%), but not by doing the same thing:**
   it fixes the cases that need judgment (duplicates, e-mail evidence) and breaks some easy ones.
5. **The language model's one clear win: reading e-mails.** It sent 5/5 bank-detail change requests to a person
   (control 0/5, rules 1/5). This is the only rule of the business bar the code alone cannot meet.
6. **The 2B model is over-cautious:** it flagged 74–80% of lines for review although it was right on almost
   all of them, so it fails the "handles ≥ 50% by itself" rule. Its own needs_review flag is not usable as the
   gate; R6 must decide from evidence (e.g. agreement with the computed option, calibrated confidence).
7. **No automatic errors at R3 for any model (0.0%).** The option design (ids it was shown, review forced for
   risky categories) kept every model safe; the remaining problem is usefulness, not safety.
8. **Qwen3.5-4B failed completely (177/177 unusable):** it used the full 80-token budget on every line and
   never produced JSON. Confirmed cause: 4B reasons by default ("Thinking Process: …" in plain text) and was cut
   off; 0.8B/2B answer directly. Thinking now disabled; 4B re-run in Step 4.
9. **No restricted-field leaks** in any run, although e-mails with bank-change requests contained account
   numbers and the model wrote a free-text reason.

---

## Step 4 — R4 error analysis and R5 fine-tuning

**R4 method** (`scripts/error_analysis.py`): every dev line is put in one bucket — correct + auto,
correct + review (over-caution), wrong though the right option was offered (choice error), wrong because the
right answer was not offered (options/retrieval gap), unusable output. Only the first error kinds can be fixed by
fine-tuning. Control (no AI), clean, workspace run: 147 correct+auto, 13 correct+review, 7 choice errors,
10 not offered → at most 11.3% fixable by training, 5.6% needs better options.

**Decision (R4 → R5):** fine-tune, because the Step 3 errors are mostly over-caution (2B: 74–80% of lines sent
to review while ~90% right) and wrong choices (0.8B: 48 wrong-party picks on clean), both teachable. The
options gap (~6%) is left to future work.

**Training data** (`pratyaksha/finetune/build_sft.py`): R3 prompts for the 635 train-split lines (months 1–4),
clean and stress = 1,270 examples. Target `{"option": …, "needs_review": …}`. Built in the workspace without the
reranker: offered 1,120 · duplicate 22 · unknown 22 · not offered 106 (taught to answer "U" and ask a person);
needs_review false 1,022 / true 248. Dev and test never used (test enforces it).

**Training** (`pratyaksha/finetune/train.py`): LoRA r=16 on all language-model linear layers (vision tower
excluded), lr 2e-4, 2 epochs, effective batch 8, loss on answer tokens only; full fine-tune for 0.8B with
8-bit AdamW and lr 1e-5. Training time and trainable parameters logged as one-time cost.

**R4 on Colab (Step 3 runs)**

| Model | Cond | Correct + auto | Correct + review (over-caution) | Wrong, right option offered | Right option not offered | Unusable | Fixable by training |
|---|---|---|---|---|---|---|---|
| R3 2B | clean | 46 (26.0%) | **113 (63.8%)** | 8 | 9 | 1 | 122 (68.9%) |
| R3 2B | stress | 35 (19.8%) | **122 (68.9%)** | 9 | 9 | 2 | 133 (75.1%) |
| R3 0.8B | clean | 101 (57.1%) | 12 | **51 (28.8%)** | 9 | 4 | 67 (37.9%) |
| R3 0.8B | stress | 98 (55.4%) | 11 | **53 (29.9%)** | 9 | 6 | 70 (39.5%) |

2B's problem is over-caution; 0.8B's problem is wrong choices (23 of them on plain full payments). Both are
fixable by training; only 9 lines (5.1%) need better options. **Decision: fine-tune.**

**Training data on Colab (with reranker):** 1,270 examples — offered 1,124, duplicate 22, unknown 22,
not offered 102; needs_review false 1,026 / true 244.

**Training (Colab T4, 2 epochs, 318 optimiser steps, 2,540 examples seen)**

| Run | Trainable parameters | Wall time | Loss: start → step 20 → end |
|---|---|---|---|
| LoRA 0.8B | 10.8 M of 864 M (1.25%) | 54.5 min | 0.95 → 0.0008 → 0.006 |
| LoRA 2B | 16.8 M of 2,230 M (0.75%) | 53.0 min | 0.90 → 0.0007 → 0.000 |
| Full 0.8B | 853 M of 853 M (100%) | 42.4 min | 0.95 → 0.008 → 0.016 |

Loss collapsed within ~20 steps (≈160 examples), with occasional spikes (0.17 at step 60). The task, given
the options, is easy to learn; the risk is memorising rather than learning, which is why dev/test are separate.

**R5 results (dev)**

| System | Cond | Accuracy | Auto | Auto error | p50 | Out tokens | Bank-detail → person | Bar |
|---|---|---|---|---|---|---|---|---|
| R3 control (no AI) | clean | 89.8% | 82.5% | 0.0% | 0.10 s | – | 0/5 | FAIL |
| R3 0.8B | clean | 63.8% | 57.1% | 0.0% | 0.75 s | 42 | 1/5 | FAIL |
| R3 2B | clean | 89.8% | 26.0% | 0.0% | 0.73 s | 40 | 5/5 | FAIL |
| **R3 4B, thinking off** | clean | 81.9% | 70.6% | 0.0% | 1.50 s | 41 | 5/5 | **PASS** |
| **R5 LoRA 0.8B** | clean | **93.8%** | 82.5% | 0.0% | **0.35 s** | 15 | 3/5 | FAIL |
| **R5 LoRA 0.8B** | stress | **93.2%** | 81.9% | 0.0% | 0.35 s | 15 | 3/5 | FAIL |
| **R5 LoRA 2B** | clean | **94.4%** | 81.9% | 0.0% | 0.94 s* | 73* | 4/5 | FAIL |
| **R5 LoRA 2B, stop fix** | clean | **94.4%** | 81.9% | 0.0% | **0.38 s** | **14** | 4/5 | FAIL |
| R5 full 0.8B | clean | 93.8% | 84.2% | 0.0% | 0.35 s | 14 | **0/5** | FAIL |
| R5 full 0.8B | stress | 93.2% | 83.6% | 0.0% | 0.33 s | 14 | **0/5** | FAIL |
| **R5 LoRA 2B** | stress | **93.2%** | 80.2% | 0.0% | 0.87 s* | 74* | **5/5** | **PASS** |

Option ceiling (right answer among options): 94.4% clean, 93.8% stress.
\* R5-2B latency and output tokens are inflated by the missing stop token (see finding 8); accuracy is not affected.

10. **R5-2B on messy lines passes every rule of the business bar** (93.2%, 80.2% handled alone, 0 automatic
    errors, 5/5 bank-detail changes to a person) — the second system to pass, after R3-4B. On clean lines the
    same model caught 4/5 bank changes, so it passes on one condition and fails on the other by a single line:
    with only 5 bank-change cases per condition, this rule is decided by one or two lines and is fragile.

**Findings**
1. **The 4B fix worked:** thinking off → 0 unusable answers (was 177/177), 81.9% accuracy. **R3-4B is the first
   system to pass every rule of the business bar** (0 automatic errors, 5/5 bank changes to a person, 71%
   handled alone). It is less accurate than R3-2B (89.8%) but far less over-cautious.
2. **Fine-tuning the smallest model is the biggest single gain for it:** 0.8B went from 63.8% (R3) to **93.8%**
   clean and 93.2% stress, +30 points, and now beats the no-AI control (+4.0 clean, +5.1 stress). It reaches
   99% of the option ceiling (93.8 of 94.4).
3. **Fine-tuning cured the over-caution without making it unsafe:** 2B handled 26.0% alone at R3 and 81.9% at R5,
   with 0.0% automatic errors in every R5 run.
4. **After fine-tuning, 0.8B ≈ 2B:** 93.8% vs 94.4% clean, 93.2% vs 93.2% stress. Model size stopped mattering
   once the model was trained on the task. (An earlier "2.7× faster" claim for 0.8B was wrong: it came from the
   2B stop-token bug. Corrected: 0.35 vs 0.38 s on Colab; true owned-machine speed to be measured on the Mac.)
5. **Fine-tuning made the system faster and cheaper:** 0.8B answers in 15 tokens (R3: 42) — latency 0.75 → 0.35 s,
   ₹6.3 → ₹3.0 per 1,000 (Colab rate).
6. **But fine-tuning weakened a safety behaviour:** bank-detail changes sent to a person fell from 5/5 (R3-2B) to
   4/5 (R5-2B) and 3/5 (R5-0.8B). Teaching "do not ask unless needed" from ~1,000 ordinary examples outweighed the
   few bank-change examples. A safety rule should not depend on a learned habit: R6 adds a code guardrail.
7. **Remaining errors are mostly not the model's:** R5-2B clean has 10 errors; 4 are "not retrieved" (the right
   answer was never offered). Better options/retrieval, not more training, is the next lever.
8. **Anomaly explained:** R5-2B produced ~73 output tokens per answer (0.8B: 15). Raw outputs show the right
   JSON followed by a made-up next turn until the token limit: generation had no explicit stop at `<|im_end|>`.
   **Fixed and verified:** with explicit stop tokens the same model gives the same 94.4% (167/177, identical
   accuracy, so only speed changed), 14 output tokens instead of 73, and latency 0.94 → **0.38 s (2.5× faster)**.
   After the fix 2B is about as fast as 0.8B (0.38 vs 0.35 s on Colab), so finding 4's speed gap was mostly this bug.
9. **Cost of training:** about 54 min of T4 time per model. At the ₹30/h rented-GPU assumption that is ≈ ₹27 per
   model, paid once.

**LoRA vs full fine-tuning (0.8B)**

| | LoRA | Full |
|---|---|---|
| Weights trained | 10.8 M (1.25%) | 853 M (100%) |
| Saved model size | adapter only (tens of MB) | whole model (~3.4 GB) |
| Training time (T4) | 54.5 min | 42.4 min |
| Accuracy clean / stress | 93.8% / 93.2% | 93.8% / 93.2% |
| Handled alone clean / stress | 82.5% / 81.9% | 84.2% / 83.6% |
| Bank-detail changes to a person | 3/5 | **0/5** |

11. **Full fine-tuning bought nothing in accuracy over LoRA** (identical 93.8% / 93.2%) and slightly more
    automation (+1.7 points), while needing a full 3.4 GB copy of the model instead of a small add-on.
12. **Full fine-tuning erased the safety behaviour completely:** 0/5 bank-detail changes sent to a person (LoRA
    3/5, untrained R3-2B 5/5). The more weights we change, the more of the base model's careful reading of
    e-mails is lost. Strongest evidence so far that safety must sit in code (R6 guardrail), not in the model.
13. **Full fine-tuning was faster to train than LoRA here** (42 vs 55 min) — unexpected; likely because LoRA
    ran the frozen weights in float16 with extra adapter layers and checkpointing overhead on a T4. Not
    investigated further; reported as observed.

**What is left after fine-tuning (R4 run again on R5 models, dev)**

| Model | Cond | Correct + auto | Correct + review | Wrong, option offered | Not offered |
|---|---|---|---|---|---|
| LoRA 0.8B | clean | 146 | 20 | 1 | 10 |
| LoRA 2B | clean | 145 | 22 | **0** | 10 |
| Full 0.8B | clean | 149 | 17 | 1 | 10 |
| LoRA 0.8B | stress | 145 | 20 | 1 | 11 |
| LoRA 2B | stress | 142 | 23 | 1 | 11 |
| Full 0.8B | stress | 148 | 17 | 1 | 11 |

14. **Fine-tuning removed almost every wrong choice** (0.8B: 51 → 1 clean). Most "correct + review" lines are
    the categories our rules force to a person (short payments 10, duplicates 4, unknown 4 = 18 on dev).
    **The model is no longer the bottleneck:** the remaining errors (10–11 lines, 5.6–6.2%) are answers our
    options never offered. Next gains come from retrieval/options, not from the model.

---

## Step 5 — R6 (gate + safety rule), R7 (frontier reference), test month

**Built**
- **Guardrail (code):** any e-mail near the payment (from a candidate payer, or quoting the exact amount)
  that asks to change bank details sends the line to a person. Checks **all** matching e-mails.
- **Forced reviews** for duplicate, unknown payer and short payment (as before).
- **System-1 gate:** the model's probability for the option id it wrote (product of the token probabilities
  spelling the id) must be ≥ a threshold. The model's own written `needs_review` is recorded, not used.
- **Threshold knob:** `scripts/threshold_sweep.py` re-applies the gate offline for 12 thresholds, prints
  automation / error / misbooked ₹ / bar, calibration and ECE, and picks the lowest threshold that passes the bar
  on both dev conditions. That threshold is used unchanged on the test month.
- **R6 control (no AI):** first option + guardrail + forced reviews.
- **R7:** Claude Opus 5.5 via the native Claude API, same R3 prompt, every dev and test line, key from Colab
  Secrets, answers cached, ≤ 30 requests/min; egress counted in bytes; routed through the same R6 rules.
- **Laya (System-1):** 421M non-generative decision model, typed-decisions checkpoint, fine-tuned with
  `laya-train` on 1,270 rows from months 1–4 (match + person questions, options shuffled), then gated like the
  Qwen models.
- **Acceptance bar frozen** (`docs/ACCEPTANCE_BAR.md`) before any test-month run.

**Measured in the workspace before Colab (dev, keyword order, no model)**

| Check | Clean | Stress |
|---|---|---|
| Guardrail catches bank-detail changes | 5/5 | 5/5 |
| Guardrail false alarms (ordinary lines sent to a person) | 7/177 (4.0%) | 7/177 (4.0%) |
| Payments whose right e-mail was found but cut by the 3-e-mail prompt limit | 0 | **3** |
| R6 control (no AI) — handled alone / error alone / bar | 77.4% / 0.0% / **PASS** | 75.1% / 0.0% / **PASS** |

**Findings so far**
1. **A safe no-AI system already passes the business bar** once a code guardrail reads the e-mails: R6 control
   handles ~75–77% alone with no automatic errors. The AI's case must be made on top of this: more lines handled
   correctly, at what extra cost.
2. **The guardrail fixes what fine-tuning broke, in code:** 5/5 on both conditions, independent of the model.
   Cost: ~4% of ordinary lines go to a person by false alarm.
3. **Context engineering hid evidence:** R3 shows the model at most 3 e-mails; on 3 messy dev lines the
   e-mail that named the payment was 4th and was cut. Ranking e-mails (exact amount first) is a cheap
   improvement left for future work; the prompt was kept unchanged so Steps 3–4 stay comparable.
4. **Limit of the guardrail:** a regular expression written against our own generated e-mail wording. Real
   e-mails vary; in practice it would need broader patterns or a classifier, and its misses must be measured.

**Results:** below (run 23 Nov 2026, `notebooks/step5b_laya_opus_test.ipynb`).

## Step 5b · cell 6a: Opus 5.5 cost check (23 Nov 2026)
- Run `20261123-100719_R7_claude-opus-5-5_dev_clean_check`: 3 dev lines (clean), all `full_payment`.
- 3/3 correct and 100% handled automatically. The bar passed, but n=3 is a smoke test, not a result.
- Latency p50 2,218 ms and p95 2,873 ms (network round trip plus thinking).
- 762 tokens in and 96 out per line, about $0.0050 per line; ₹437 per 1,000 tasks (operating cost).
- 5,175 bytes sent off the machine for 3 lines (about 1.7 KB per line); 0 restricted-field leaks.
- Projection: about $3.52 for all 708 dev+test lines, or about $1.76 for the 354 test lines.
- Caveat: these 3 easy lines probably use fewer tokens than clubbed, TDS or stress lines (longer prompts, more e-mails), so the real cost could be 20–40% higher.
- Decision (updated): the balance is $10, not $5, so we run in the planned order: 6b (full dev) → 7 (test) → 8. Worst case about $4.90, which leaves about $5 spare.
- HF Hub "unauthenticated requests" warning: harmless; it only affects download speed.
- Cell 6b actual cost: the Console balance went from $10.00 to $7.88, so $2.12 was spent (including the 3-line check, about $0.015). That is about $2.10 for 354 dev lines, or about $0.0059 per line, 19% above the 6a estimate. This fits the caveat that harder lines use more tokens. Test-month projection: about $2.10.

**R7 Opus 5.5, full dev (cell 6b)**

| System | Cond | Accuracy | Auto | Auto error | p50 / p95 | Tokens in/out | ₹/1,000 (operating) | Egress | Bank-detail → person | Bar |
|---|---|---|---|---|---|---|---|---|---|---|
| R7 Opus 5.5 | clean | 94.4% | 70.6% | 0.0% | 2.41 s / 4.94 s | 717 / 152 | 519.83 | 289,450 B | 5/5 | PASS |
| R7 Opus 5.5 | stress | 93.8% | 67.2% | 0.0% | 2.64 s / 4.83 s | 720 / 164 | 541.85 | 290,912 B | 5/5 | PASS |
| R5 LoRA 2B (for reference) | clean | 94.4% | 81.9% | 0.0% | 0.38 s | – / 14 | local | 0 B | 4/5 | FAIL |
| R5 LoRA 2B (for reference) | stress | 93.2% | 80.2% | 0.0% | 0.87 s* | – / 74* | local | 0 B | 5/5 | PASS |

Findings:
1. **Opus reaches the option ceiling exactly:** 94.4% = 94.4% on clean, 93.8% = 93.8% on stress. Whenever the right answer was among the computed options, Opus picked it. All 10 clean errors and 11 stress errors are upstream: wrong_party 6/7 (the right party was not among the retrieved parties, 95.9% / 95.3% party recall) and not_retrieved 4/4. A bigger model cannot fix these; only retrieval and option building can.
2. **The fine-tuned 2B equals Opus on clean (94.4%) and is 1 line behind on stress (93.2% vs 93.8%).** A 2B model running locally matches a frontier model at the same pipeline ceiling.
3. **Opus is more cautious:** it handles 70.6% / 67.2% automatically vs 81.9% / 80.2% for R5-2B, so about 11–13 points more lines go to a person. Its own "needs review" flag is conservative. That is safe (0.0% auto errors, all 5 bank changes to a person) but costs more review work.
4. **Costs of the frontier model:** about 6× slower at p50 (2.4 s vs 0.38 s), with a long tail (p95 about 4.9 s). It costs ₹520–542 per 1,000 lines in API fees, vs no API fee for local models. It sends about 1.64 KB of business data off the machine per line (289–291 KB per 177 lines); the restricted-field leak check stayed at 0.
5. Thinking adds output tokens: 152–164 out per line vs 96 on the 3 easy check lines. This is why the actual cost was 19% above the 6a estimate.
6. Weakest categories (both conditions): clubbed_payment 21/24 (87.5%) and tds_deduction 19/21 (90.5%), the same categories where the options are hardest to build.

**R6 gate on dev (cell 2): every model with the guardrail and forced reviews, threshold 0**

| System | Cond | Accuracy | Auto | Auto error | Misbooked ₹ | p50 | Bank-detail → person | Bar |
|---|---|---|---|---|---|---|---|---|
| R6 control (no AI) | clean | 89.8% | 75.7% | 0.00% | 0 | 0.10 s | 5/5 | PASS |
| R6 Qwen3.5-2B (not fine-tuned) | clean | 89.8% | 76.8% | 0.74% | 236 | 0.65 s | 5/5 | PASS |
| R6 LoRA 0.8B | clean | 93.8% | 77.4% | 0.00% | 0 | 0.34 s | 5/5 | PASS |
| R6 LoRA 2B | clean | 94.4% | 77.4% | 0.00% | 0 | 0.42 s | 5/5 | PASS |
| R6 full FT 0.8B | clean | 93.8% | 77.4% | 0.00% | 0 | 0.35 s | 5/5 | PASS |
| R6 Laya | clean | 94.4% | 77.4% | 0.00% | 0 | 0.065 s† | 5/5 | PASS |
| R6 control (no AI) | stress | 88.1% | 73.4% | 0.00% | 0 | 0.11 s | 5/5 | PASS |
| R6 Qwen3.5-2B (not fine-tuned) | stress | 88.7% | 75.7% | 0.75% | 236 | 0.70 s | 5/5 | PASS |
| R6 LoRA 0.8B | stress | 93.2% | 76.3% | 0.00% | 0 | 0.34 s | 5/5 | PASS |
| R6 LoRA 2B | stress | 93.2% | 75.7% | 0.00% | 0 | 0.41 s | 5/5 | PASS |
| R6 full FT 0.8B | stress | 93.2% | 76.3% | 0.00% | 0 | 0.34 s | 5/5 | PASS |
| R6 Laya | stress | 93.8% | 76.3% | 0.00% | 0 | 0.067 s† | 5/5 | PASS |

† Laya's own forward pass only; search, rerank and context (about 0.10 s, the R6 control's time) were not counted. Bug found 23 Nov, see the correction under finding 5 of the test month.

**Laya fine-tuning (cell 3)**
- Data: 1,270 past bank lines (months 1–4, clean + stress). Each line has 2 questions (`match`, `person`), giving 2,540 items: 2,286 for training and 254 for calibration.
- The right answer was among the options for 1,124 lines; 22 were duplicates, 22 unknown parties, and 102 lines had no right option (labelled U, i.e. a person must check). 244 lines need a person, 1,026 do not.
- Settings: typed-decisions base, 1,024-token input, option shuffling, effective batch 64, 144 optimizer updates over 4 epochs. Training took **18.7 min on a T4**.
- On the calibration slice (in-sample, not held out): accuracy 82.7% → 87.0%, ECE 0.174 → 0.110, Brier 0.348 → 0.233.
- Warnings, logged in WHAT_DIDNT_WORK: the `person` temperature stopped at the clamp limit (5); "conflicting schema for 'match'"; some per-step losses printed as negative.

**Threshold knob (cell 5). Rule: the lowest threshold that passes the bar on both dev conditions**

| Model | Chosen | Auto at 0.0 → 0.999 (clean) | ECE clean / stress | Lines with probability ≥ 0.999 (clean) and how many were right |
|---|---|---|---|---|
| Qwen3.5-2B (not fine-tuned) | 0.0 | 76.8% → 0.0% | 0.130 / 0.142 | none above 0.99 |
| LoRA 0.8B | 0.0 | 77.4% → 75.7% | 0.052 / 0.063 | 158, 96.8% right |
| LoRA 2B | 0.0 | 77.4% → 76.3% | 0.051 / 0.060 | 159, 96.9% right |
| Full FT 0.8B | 0.0 | 77.4% → 65.0% | 0.046 / 0.055 | 135, 96.3% right |
| Laya | 0.0 | 77.4% → 77.4% (flat) | 0.047 / 0.058 | 170, 97.1% right |

- For the base 2B model, 0.8 removes the automatic errors on clean dev, but stress then handles only 47.5% automatically (< 50%), so that threshold fails. The rule therefore keeps 0.0, accepting 0.74% wrong automatic entries (within the 1% bar).
- Without the guardrail and forced reviews ("no gate"), every model sends **0%** of bank-detail changes to a person, and automatic handling rises to 83–84%.

**THE TEST MONTH (cell 7): month 6, run once, thresholds from dev (all 0.0), n = 185 per condition**

| System | Cond | Accuracy | Auto | Auto error | Misbooked ₹ | p50 | ₹/1,000 (operating) | Egress | Bank-detail → person | Bar |
|---|---|---|---|---|---|---|---|---|---|---|
| Rules (no AI) | clean | 74.6% | 67.6% | 0.0% | 0 | 0.14 s | 1.12 | 0 | 2/7 | FAIL |
| R3 control (no AI, no guardrail) | clean | 89.7% | 81.6% | 0.0% | 0 | 0.10 s | 0.82 | 0 | 1/7 | FAIL |
| R6 control (no AI) | clean | 89.7% | 74.1% | 0.0% | 0 | 0.10 s | 0.84 | 0 | 7/7 | PASS |
| R5 LoRA 0.8B (no guardrail) | clean | 91.4% | 80.0% | 0.0% | 0 | 0.32 s | 2.89 | 0 | 7/7 | PASS |
| R6 Qwen3.5-2B (not fine-tuned) | clean | 87.0% | 73.5% | 0.74% | 590 | 0.68 s | 5.92 | 0 | 7/7 | PASS |
| **R6 LoRA 0.8B** | clean | **91.4%** | 75.7% | 0.0% | 0 | 0.34 s | 2.95 | 0 | 7/7 | PASS |
| **R6 LoRA 2B** | clean | **91.4%** | 75.7% | 0.0% | 0 | 0.41 s | 3.47 | 0 | 7/7 | PASS |
| **R6 full FT 0.8B** | clean | **91.4%** | 75.7% | 0.0% | 0 | 0.34 s | 2.91 | 0 | 7/7 | PASS |
| **R6 Laya** | clean | **91.4%** | 75.7% | 0.0% | 0 | **0.068 s†** | **0.59†** | 0 | 7/7 | PASS |
| R7 Opus 5.5 | clean | 89.7% | 71.9% | 0.0% | 0 | 2.27 s | 479.17 | 304,805 B | 7/7 | PASS |
| Rules (no AI) | stress | 55.1% | 49.2% | 0.0% | 0 | 0.09 s | 0.83 | 0 | 4/7 | FAIL |
| R3 control (no AI, no guardrail) | stress | 88.1% | 80.5% | 0.0% | 0 | 0.11 s | 0.90 | 0 | 1/7 | FAIL |
| R6 control (no AI) | stress | 88.1% | 74.1% | 0.0% | 0 | 0.11 s | 0.91 | 0 | 7/7 | PASS |
| R5 LoRA 0.8B (no guardrail) | stress | 89.2% | 78.9% | 0.0% | 0 | 0.34 s | 2.88 | 0 | **6/7** | **FAIL** |
| R6 Qwen3.5-2B (not fine-tuned) | stress | 85.4% | 73.0% | 0.74% | 590 | 0.68 s | 5.76 | 0 | 7/7 | PASS |
| **R6 LoRA 0.8B** | stress | **89.2%** | 75.1% | 0.0% | 0 | 0.34 s | 2.89 | 0 | 7/7 | PASS |
| R6 LoRA 2B | stress | 88.6% | 74.6% | 0.0% | 0 | 0.40 s | 3.45 | 0 | 7/7 | PASS |
| **R6 full FT 0.8B** | stress | **89.2%** | 75.1% | 0.0% | 0 | 0.33 s | 2.88 | 0 | 7/7 | PASS |
| R6 Laya | stress | 88.6% | 75.1% | 0.0% | 0 | **0.067 s†** | **0.59†** | 0 | 7/7 | PASS |
| R7 Opus 5.5 | stress | 87.6% | 65.4% | 0.0% | 0 | 2.44 s | 501.16 | 297,990 B | 7/7 | PASS |

Option ceiling on test (right answer among the options): **92.4% clean** (14 lines missing), **90.3% stress** (18 missing).
Party recall: 93.8% clean and 91.6% stress (dev: 95.9% / 95.3%).

R4-style error buckets on test (cell 8, `error_analysis.py`):

| System | Cond | Correct + auto | Correct + review | Wrong, right option offered | Right option not offered |
|---|---|---|---|---|---|
| R6 LoRA 0.8B | clean | 140 | 29 | 2 (short_payment 2) | 14 |
| R6 LoRA 2B | clean | 140 | 29 | 2 (short_payment 2) | 14 |
| R6 Laya | clean | 140 | 29 | 2 (short_payment 2) | 14 |
| R7 Opus 5.5 | clean | 133 | 33 | **5** (full_payment 3, short_payment 2) | 14 |
| R6 LoRA 0.8B | stress | 139 | 26 | 2 (short_payment 2) | 18 |
| R6 LoRA 2B | stress | 138 | 26 | 3 (supplier 1, short 2) | 18 |
| R6 Laya | stress | 139 | 25 | 3 (short_payment 3) | 18 |
| R7 Opus 5.5 | stress | 121 | 41 | **5** (full_payment 3, short_payment 2) | 18 |

Opus API spend on test: about $2.06, computed from tokens (185 × (723·$4 + 128·$20)/1M + 185 × (704·$4 + 144·$20)/1M). Total Opus spend for the project is about $4.18 of the $10 credit.

**Step 5 findings (test month = the headline numbers)**
1. **Every gated system (R6) and Opus passes the frozen business bar on the held-out month, clean and messy.** The rules baseline, the R3 control and R5 without the guardrail fail, each on the bank-detail rule.
2. **Best accuracy comes from the small fine-tuned local models:** 91.4% clean (LoRA 0.8B, LoRA 2B, full 0.8B and Laya all tie) and 89.2% stress (LoRA 0.8B, full 0.8B). That is 98.9% / 98.8% of the option ceiling, with 0 wrong automatic entries and 0 bytes leaving the machine.
3. **The frontier model did not beat them on test:** Opus 5.5 scored 89.7% clean and 87.6% stress. It made 5 wrong choices per condition where the right option was offered (the fine-tuned models made 2–3), and it handled the fewest lines automatically (71.9% / 65.4%). On dev it was exactly at the ceiling, so the gap is a handful of lines and must be checked for significance (`scripts/significance.py`).
4. **AI over the no-AI gated control is small on test:** +1.7 points clean (3 lines of 185) and +1.1 stress (2 lines), plus about 1.6 points more handled automatically. Most of the improvement from rules (74.6% / 55.1%) to about 90% comes from engineering: retrieval, computed options, forced reviews and the guardrail. The language model adds the last step. Significance is pending.
5. **Laya is the efficiency winner:** the same accuracy as the best clean model (1 line behind on stress), no tokens and no data leaving the machine. Training took 18.7 min.
   **Correction (23 Nov, found while preparing the Mac runs):** Laya's logged time (0.067–0.068 s, ₹0.59 per 1,000) counted only Laya's own forward pass. Every other system's time includes search, rerank and option building (about 0.10 s, the R6 control's time). Like for like, Laya is estimated at about **0.17 s per line end to end** (about 2× faster than LoRA 0.8B at 0.34 s and about 13× faster than Opus at 2.27 s) and about ₹1.4 per 1,000 lines at the Colab rate (about 340× cheaper than Opus). Laya *itself* is about 3.5× faster than the 0.8B model's generation step (0.068 s vs about 0.24 s). Code fixed (`laya_inputs` now returns the steps; test added); the Mac runs measure it end to end. Accuracy is not affected.
6. **The test month was harder for retrieval than dev:** party recall dropped by 2–4 points, so the ceiling fell from 94.4 to 92.4 (clean) and from 93.8 to 90.3 (stress). 14 of 16 clean errors and 18 of 20–21 stress errors are "right answer not offered", so **retrieval and option building is the next lever, not a bigger model.**
7. **The guardrail is essential:** the only fine-tuned system without it (R5 LoRA 0.8B) missed 1 of 7 bank-detail changes on test stress and failed. Without the gate, every model sends 0% of bank changes to a person.
8. **The probability threshold adds little once the rules exist:** for the fine-tuned models and Laya, automatic handling barely changes between 0.0 and 0.999, because most lines get probability ≥ 0.999 (and are right about 96–97% of the time). The forced reviews and the guardrail are what keep automatic errors at 0. All chosen thresholds were 0.0.
9. **The not-fine-tuned 2B model is the only system with automatic errors** (0.74%, ₹590 misbooked on test, within the bar). It also had 1 unusable output per condition. Fine-tuning removed both.
10. **short_payment is the remaining choice error for every model**, which points to the short-payment option (≤ 6% tolerance) as the place to improve.
11. Correction to Step 3 finding 5 ("the bank-detail rule is the only one code alone cannot meet"): with the R6 guardrail regex, the no-AI control also sends 7/7 to a person. The rule *is* met by code; the model's own flag is not needed for it.

**Significance on the test month (`scripts/significance.py`: paired exact McNemar test plus bootstrap 95% CI, 2,000 resamples)**

| Comparison | Clean: fixes / breaks, p, 95% CI | Stress: fixes / breaks, p, 95% CI |
|---|---|---|
| Fine-tuned (LoRA 0.8B / full 0.8B) vs no-AI R6 control | 3 / 0, p = 0.25, [+0.0, +3.8] | 2 / 0, p = 0.50, [+0.0, +2.7] |
| Laya vs no-AI R6 control | 3 / 0, p = 0.25, [+0.0, +3.8] | 2 / 1, p = 1.00, [−1.1, +2.2] |
| Opus 5.5 vs no-AI R6 control | 3 / 3, p = 1.00, [−2.7, +2.7] | 2 / 3, p = 1.00, [−2.7, +1.6] |
| Untrained Qwen 2B vs no-AI R6 control | 3 / 8, p = 0.23, [−5.9, +0.5] | 2 / 7, p = 0.18, [−5.9, +0.0] |
| Fine-tuned (LoRA 0.8B / full 0.8B) vs Opus 5.5 | 3 / 0, p = 0.25, [+0.0, +3.8] | 3 / 0, p = 0.25, [+0.0, +3.8] |
| Laya vs Opus 5.5 | 3 / 0, p = 0.25, [+0.0, +3.8] | 3 / 1, p = 0.63, [−1.1, +3.2] |
| Rules vs no-AI R6 control | 0 / 28, p < 0.001 | 1 / 62, p < 0.001 |

Laya's choices on test: M1 162, M2 3, U 20 (clean); M1 159, M2 2, U 24 (stress). It never chose D or M3+. The test month has no duplicate lines and no line whose right answer is option 3 or later (0/0), so the "conflicting schema" risk cannot show up on test; on dev Laya got 4/4 duplicates right.
Test category weak spot: short_payment 10/14 (71.4%) for Laya, Opus and the best models on clean; Opus 8/14 on stress.

Findings:
12. **On the held-out month, no AI system is statistically different from the no-AI gated control, or from each other.** Every p-value is ≥ 0.18 and every 95% interval includes 0. Only the rules baseline is significantly worse (p < 0.001).
13. **The direction is consistent:** every fine-tuned model fixes 2–3 lines and breaks 0–1 vs both the control and Opus. With so few lines where systems disagree, the test cannot reach significance: the smallest possible p with 3 disagreements is 0.25, and about 6 one-sided wins would be needed for p < 0.05. This is a limit of the sample size (185 lines, 7 bank changes), stated as such.
14. **Report wording:** "the fine-tuned local models *matched* Claude Opus 5.5 on accuracy (difference not significant) while being about 7–13× faster, about 160–340× cheaper per line and sending no data off the machine. (Ratios corrected 23 Nov after the Laya timing fix; final speed and cost come from the Mac.)" Do **not** write "beat Opus".
15. **Report wording on the AI's value:** the significant, large improvement (+15 to +33 points, p < 0.001) comes from the engineered pipeline (retrieval, computed options, forced reviews, guardrail) over rules. On top of that pipeline, the language model's extra accuracy is small and not statistically significant on one month of data.
16. **Untrained models need fine-tuning to be safe:** the untrained 2B is the only gated system with automatic errors and breaks 7–8 lines vs the control (not significant, but in the wrong direction).

---

## Step 6 — the owned machine (MacBook Pro 2021, Apple M1 Pro, 16 GB RAM; Apple GPU "mps"), 23 Nov 2026

Same frozen systems as the test month (thresholds 0.0, nothing retrained or re-tuned), run **one line at a time**
on the test month with `scripts/mac_step6.sh`. Laptop price ₹1,75,000 spread over 6,000 working hours (3 years × 250 days × 8 h);
power **assumed 35 W** (not measured); tariff ₹8/kWh. Run tag `mac`.

| System | Cond | Acc Colab | Acc Mac | Same answer as Colab | Mac p50 | Mac p95 | ₹/1,000 power | ₹/1,000 laptop | ₹/1,000 total |
|---|---|---|---|---|---|---|---|---|---|
| Rules (no AI) | clean | 74.6% | 74.6% | 185/185 | 0.059 s | 0.095 s | 0.005 | 0.47 | 0.48 |
| R6 control (no AI) | clean | 89.7% | 89.7% | 185/185 | 0.110 s | 0.123 s | 0.009 | 0.91 | 0.91 |
| R6 Laya | clean | 91.4% | 91.4% | 185/185 | 0.279 s | 0.361 s | 0.022 | 2.33 | 2.35 |
| R6 LoRA 0.8B | clean | 91.4% | 91.4% | 185/185 | 0.863 s | 0.981 s | 0.067 | 6.93 | 7.00 |
| Rules (no AI) | stress | 55.1% | 55.1% | 185/185 | 0.035 s | 0.079 s | 0.003 | 0.31 | 0.32 |
| R6 control (no AI) | stress | 88.1% | 88.1% | 185/185 | 0.106 s | 0.120 s | 0.008 | 0.87 | 0.88 |
| R6 Laya | stress | 88.6% | 88.6% | 185/185 | 0.271 s | 0.348 s | 0.021 | 2.24 | 2.26 |
| R6 LoRA 0.8B | stress | 89.2% | 89.2% | 185/185 | 0.854 s | 0.997 s | 0.067 | 6.93 | 7.00 |

All four systems: bar result identical to Colab (rules FAIL on the bank-detail rule; the three gated systems PASS with 7/7 bank changes to a person, 0.0% automatic errors), 0 bytes left the machine.
Reference: Opus 5.5 on test, p50 2.27 s (clean) / 2.44 s (stress), ₹479 / ₹501 per 1,000 in API fees, about 300 KB sent out per 185 lines.

Findings:
1. **The results reproduce exactly on a different machine:** 1,480 of 1,480 answers (4 systems × 2 conditions × 185 lines) are identical between the Colab T4 (CUDA) and the MacBook (Apple GPU). The test-month numbers do not depend on the hardware.
2. **Measured end-to-end speed on the owned machine:** Laya 0.27–0.28 s per line, fine-tuned 0.8B 0.85–0.86 s, no-AI control 0.11 s, rules 0.04–0.06 s. Laya is about **3.1× faster** than the 0.8B model end to end, and the model part alone is about 4.4× faster (about 0.17 s vs 0.75 s, after subtracting the control's 0.11 s of search and options).
3. **Laya's corrected Colab estimate (0.17 s) is confirmed in order of magnitude:** on the Mac it is 0.28 s, because the Apple GPU is slower than the T4 for the reranker and encoder.
4. **Opus vs the owned machine, like for like (all per line, end to end):** Opus is about **2.6–2.9× slower** than the fine-tuned 0.8B on the Mac and about **8–9× slower** than Laya. It costs about **70×** more per line than the 0.8B and about **200–220×** more than Laya, and it sends business data out while the local systems send nothing.
5. **On the owned machine the cost is the laptop, not the electricity:** 99% of the ₹/1,000 is the laptop's price spread over its life; the power cost is under ₹0.07 per 1,000 lines even at the assumed 35 W. So measuring watts would not change any conclusion; 35 W is stated as an assumption.
6. **Throughput:** at 0.28 s per line Laya can reconcile about 12,900 lines an hour on the laptop; the 0.8B model about 4,200. A business with a few hundred bank lines a month needs minutes, not hours.
7. **Speed limitation:** Qwen3.5's fast kernels (`causal_conv1d`, `flash-linear-attention`) are NVIDIA-only, so the 0.8B model ran on reference PyTorch code on the Mac (as on Colab). Its Mac speed is therefore a lower bound.

**Report wording (replaces the Colab-based ratios):** "On a ₹1.75 lakh MacBook Pro, the fine-tuned local models matched Claude Opus 5.5 on accuracy (difference not significant), gave identical answers to the Colab runs on all 1,480 lines, were about 3–9× faster and about 70–220× cheaper per line, and sent no data off the machine."
