# What didn't work (kept from day one)

Failures are results. Each entry: what happened, how we found it, what we changed.

## 2026-11-20 — Short aliases matched the wrong customer

**What:** the first rules baseline scored 23.7% on *clean* data. Initials-style
aliases (e.g. "SG TRD") appeared inside unrelated narrations, so the matcher
picked the wrong customer, and every downstream invoice search failed.
**How found:** the error taxonomy showed 130 "not retrieved", which made no sense
for clean data. The taxonomy itself was hiding the cause because it checked
retrieval before checking the party, so we fixed that ordering too.
**Fix:** ignore aliases under 6 characters, compare with spaces removed (UPI
handles drop spaces), prefer the longest exact match, credit truncated prefixes.
Clean accuracy 23.7% → 80.8%.
**Lesson for developers:** entity resolution, not the AI model, is often the
first bottleneck in reconciliation.

## 2026-11-20 — Our own gold answers failed our own acceptance bar

**What:** a unit test that scores the gold answers against themselves failed the
acceptance bar. Short payments with no stated reason were marked as safe to
auto-book, contradicting the rule that every unexplained entry goes to a person.
**Fix:** `needs_review = not explained` in the generator; bank-detail changes got an
explicit gold flag instead of being inferred.
**Lesson:** test the evaluator before testing any model.

## 2026-11-22 — Retrieval cannot find payers that the narration does not name

**What:** keyword search (top 10) misses the right customer for ~9% of clean payments on dev.
**Why:** 11 of 15 misses are cheque deposits whose narration has no name; 4 are payments made by
a sister firm. No amount of better name search fixes these.
**What we do:** report it as the ceiling of R1/R2; R3 adds amount-based matching and remittance
e-mails, and the GraphRAG probe tests sister-firm links.

## 2026-11-22 — Our acceptance bar could be "passed" by doing nothing

**What:** R1 and R2 with Qwen3.5-0.8B scored 0–1% accuracy but PASSED the business bar, because every
line went to a person: no automatic entries means no automatic errors.
**Fix:** added a fifth rule: the system must handle at least 50% of lines by itself (provisional, to be
agreed with the CA). A system that hands everything back has not reconciled anything.
**Lesson:** safety rules need a usefulness rule beside them, or "refuse everything" wins.

## 2026-11-22 — Small models could not use the records we gave them

**What:** with retrieval, Qwen3.5-0.8B stayed at ~0%; 2B reached 45% but 0% on any payment that needs
adding or subtracting (clubbed, TDS, short).
**Next:** R3 computes the amount matches in code and gives them to the model, instead of asking it to add.

---

## 2026-11-22 — The bigger model (4B) produced nothing usable

**What:** Qwen3.5-4B at R3 returned no readable answer for all 177 lines (both conditions), always using the
full 80-token limit. Score 2.3% (only "unknown party" lines, by default).
**Cause (confirmed 23 Nov from raw outputs):** every answer began "Thinking Process: 1. Analyze the Request…"
in plain text and was cut off at 80 tokens before any JSON. Qwen3.5-4B reasons by default; 0.8B and 2B did not.
**Fix:** chat template called with `enable_thinking=False`; `<think>` text stripped; a plain-text
"Thinking Process" with no JSON is now reported as `thinking_cutoff` instead of `no_json`. Re-run 4B in Step 4.
**Lesson:** a bigger model in the same family is not a drop-in replacement; defaults can differ by size.

## 2026-11-22 — The 2B model sends too much to a person

**What:** at R3 the 2B model was right on ~90% of lines but marked 74–80% "needs review".
**Why it matters:** it fails the usefulness rule; an accountant would still check most lines by hand.
**Next:** R6 gate decides from evidence, not from the model's own flag.

## 2026-11-23 — Fine-tuning made the model ignore some bank-detail change requests

**What:** R5 models sent fewer bank-detail change requests to a person (0.8B: 3/5, 2B: 4/5) than R3-2B (5/5).
**Why:** training taught "handle ordinary payments yourself" from ~1,000 examples; bank-change examples are rare.
**Fix (Step 5, R6):** a code guardrail that always sends lines with a bank-detail request to a person,
independent of the model. **Lesson:** safety rules belong in code, not in learned behaviour.

## 2026-11-23 — Colab's free GPU limit stopped the run

**What:** after ~3 h of GPU time (4B re-run, two LoRA trainings of ~54 min each, evaluations) Colab stopped the
session during the R5-2B stress evaluation. Full fine-tuning of 0.8B did not run.
**Fix:** a short resume notebook that re-runs only what is missing; trained adapters were already saved to Drive.
**Lesson:** our time estimates were low (0.8B LoRA estimated 20–30 min, took 54.5); budget GPU time per day.

## 2026-11-23 — The fine-tuned 2B model did not stop after answering

**What:** R5-2B wrote ~73 tokens per answer although the answer is ~15. Raw outputs show the correct JSON,
then a made-up next turn ("user / BANK LINE / date … / assistant <think>") until the 80-token limit.
**Effect:** accuracy unaffected (only the first JSON is read), but **latency was inflated** (0.94 s reported).
**Cause:** generation was not given `<|im_end|>` as a stop token; the 0.8B model happened to stop, the 2B did not.
**Fix:** explicit stop-token list passed to `generate`. **Verified:** same 94.4%, 14 tokens, 0.94 → 0.38 s.
**Our own wrong claim it caused:** we reported "0.8B is 2.7× faster than 2B after fine-tuning". That came from
this bug and is withdrawn; corrected in FINDINGS_LOG.
**Lesson:** check raw outputs, not only scores: a correct answer can hide wasted work.

## 2026-11-23 — The guardrail first missed a bank-detail change: the e-mail was cut from the context

**What:** first version of the R6 guardrail caught 4/5 bank changes on messy dev lines.
**Cause:** it reused the R3 context, which keeps at most 3 e-mails; the one asking to change bank details was 4th.
**Fix:** the guardrail checks every matching e-mail; the model's prompt is unchanged. Now 5/5 on both conditions.
**Wider lesson:** the same cap hid the payment's own e-mail from the model on 3 messy lines — a context-engineering
limit that affected Steps 3–4 too.

# Engineering log (small failures and fixes, all steps)

Rule from 22 Nov: every failure and every success is recorded, however small.

| Date | Step | What happened | Found by | Fix / outcome |
|---|---|---|---|---|
| 20 Nov | 1 | Bank-change rule first counted short payments as bank-detail changes | Scorecard showed bank-change total > 5 | Explicit `bank_detail_change` flag in the gold answers |
| 20 Nov | 1 | Error taxonomy checked retrieval before party, hiding wrong-party errors as "not retrieved" | 130 "not retrieved" on clean data made no sense | Check wrong party first |
| 20 Nov | 1 | Setup guide written for the Mac only, though Step 1 needs no Mac | User asked why everything was on the Mac | 22 Nov: Colab for development and training, Mac for final measured runs and demo (DECISIONS.md) |
| 22 Nov | 1 | Step 1 reproduced on Colab | User's run | **Success:** identical numbers (80.8% / 59.9%), same seed gives same world on another machine |
| 22 Nov | 2 | Index file format changed (new columns) would have broken the old `runs/index.csv` | Code review before shipping | Old file kept as `index_step1.csv`, new file started |
| 22 Nov | 2 | Colab ran Qwen3.5 without two fast GPU kernels (causal_conv1d, flash-linear-attention) | Colab warnings | Not fixed: latency on Colab is not the reported number; final latency comes from the Mac |
| 22 Nov | 2 | Smoke test on Colab | User's run | **Success:** model loaded in 40 s, valid JSON, PASS; float16 works on T4 |
| 22 Nov | 2 | R1/R2 prompt let the model answer with a free list of invoice ids; small models listed all of them and were cut off at 160 tokens | Raw-output check (user ran the diagnostic cell) | R3 answers with one option id, 80 tokens |
| 22 Nov | 2 | Acceptance bar passed by a system that did nothing (sent all to review) | Reading the Step 2 table | Added "handles ≥ 50% by itself" rule |
| 22 Nov | 2 | R1 was not run at 2B, so R1 vs R2 could not be compared where the model works | Analysis of Step 2 table | R1-2B added to the Step 3 notebook |
| 22 Nov | 3 | R3's shorter answer limit was set after the model had already been created, so it would have had no effect | Code review before shipping | Set in the constructor before the backend is created |
| 22 Nov | 3 | Locally measured R3 control used keyword order (no reranker); Colab uses the real reranker | Noted when packaging | Colab numbers are the reported ones; local numbers marked as workspace-only in FINDINGS_LOG |
| 22 Nov | 3 | Step 3 notebook run end to end on Colab (incl. optional 4B) | User's run | **Success:** all cells ran; 27 tests later, control matched the workspace within 0.6 pt |
| 22 Nov | 3 | 4B run: 177/177 unusable, 80/80 tokens used every time | compare table | 23 Nov: cause confirmed (plain-text 'Thinking Process'); thinking disabled; re-run in Step 4 |
| 22 Nov | 3 | Control's prompt-token count is a rough character estimate (fake backend), not real tokens | Comparing 339 (control) vs 526 (models) | Noted in FINDINGS_LOG; real token counts come from model runs |
| 22 Nov | 3 | Model "breaks": short payments answered "U, unknown party" though payer option was listed; bank charge booked as supplier | `vs_control.py` | Candidate training signal for R5; noted for R6 gate |
| 22 Nov | 3 | Free Colab handled a 9.3 GB 4B download and run without disconnecting | User's run | **Success** |
| 23 Nov | 3 | 4B raw outputs checked | User ran diagnostic | Cause confirmed: plain-text "Thinking Process" (no `<think>` tags), so tag-stripping alone would not have caught it; parser now reports `thinking_cutoff` |
| 23 Nov | 4 | Training script cannot be run in the workspace (no GPU) | — | Encoding logic tested with a stand-in tokenizer (loss only on answer tokens; truncation keeps the answer); dry-run cell (5 steps) added before real training |
| 23 Nov | 4 | 106 of 1,270 training lines have no correct option (8.3%) | build_sft stats | Trained to answer "U" + review; options gap reported as future work |
| 23 Nov | 4 | 4B re-run with thinking off | User's run | **Success:** 0/177 unusable (was 177/177); first system to pass the full bar |
| 23 Nov | 4 | Dry run (5 steps) before training | User's run | **Success:** caught nothing; training started cleanly |
| 23 Nov | 4 | One "memory allocation failed with OOM" message during each LoRA training | Colab log | Allocator retried and training continued; no effect on results. Watch if batch or length grows |
| 23 Nov | 4 | Warning "lr_scheduler.step() before optimizer.step()" | Colab log | Expected with fp16: the gradient scaler skips the first step(s) when gradients overflow. Harmless; first LR value skipped |
| 23 Nov | 4 | Deprecation warnings (gradient_checkpointing_enable → activation_checkpointing_enable; torchao version) | Colab log | No effect now; update the call if transformers v6 is used |
| 23 Nov | 4 | Training-time estimates were too low (est. 20–30 min, actual 54.5 for 0.8B) | Colab log | Estimates in later notebooks based on measured times |
| 23 Nov | 4 | R5-2B writes ~73 tokens per answer vs ~15 expected | Scorecard | To check raw output in the resume notebook |
| 23 Nov | 4 | Colab GPU limit stopped the notebook during R5-2B stress eval | User | Resume notebook; adapters were saved |
| 23 Nov | 4 | Resume cell run without being in the project folder → `No module named 'pratyaksha'` | User's run | Every cell in future notebooks sets its own folder (`%cd`) first |
| 23 Nov | 4 | New Colab session: `peft` refused to load the adapter because of old `torchao` 0.10 (was only a warning before) | User's run | `pip install -U peft` and `pip uninstall torchao` (not used by the project) |
| 23 Nov | 4 | Bought 100 Colab compute units (pay-as-you-go) to finish without waiting for the free quota | User | Legitimate route; second Google account rejected (Colab lists it as a restricted activity) |
| 23 Nov | 4 | First resume attempt skipped Install/Data cells (user's own diagnosis) → errors; re-running sections 3–4 fixed them | User | Notebook instructions now say "run Install first" in every resume cell |
| 23 Nov | 4 | R5-2B stress run completed **before** the stop-token fix was applied (74 tokens/answer) | Scorecard | Accuracy valid; latency re-measured after the fix |
| 23 Nov | 4 | Only 5 bank-detail change cases per condition: one line flips the bar result (R5-2B clean 4/5 FAIL, stress 5/5 PASS) | Comparing runs | Reported as a limitation; R6 guardrail removes the dependence on the model |
| 23 Nov | 4 | Stop-token fix verified | Re-run | **Success:** identical accuracy, 73 → 14 tokens, 2.5× faster |
| 23 Nov | 4 | Earlier finding "0.8B 2.7× faster than 2B" was an artefact of the stop bug | Re-run | Withdrawn and corrected in FINDINGS_LOG |
| 23 Nov | 4 | compare.py shows 94.3% where the scorecard shows 94.4% (167/177 = 0.94350, rounding of a stored 4-digit value) | Comparing outputs | Display only; scorecards are the reference. Store more digits in index.csv |
| 23 Nov | 4 | Full fine-tune (8-bit AdamW, fp32 weights) ran on T4 without memory errors | User's run | **Success** |
| 23 Nov | 4 | Full fine-tuning trained faster (42 min) than LoRA (55 min) | Training logs | Unexpected; reported as observed, not investigated |
| 23 Nov | 4 | Full fine-tuned 0.8B sent 0/5 bank-detail changes to a person | Scorecard | Strong case for the R6 code guardrail |
| 23 Nov | 5 | Guardrail regex is tuned to our generated e-mail wording | Design review | Reported as a limitation in FINDINGS_LOG |
| 23 Nov | 5 | Process slip: R7 was switched to Gemini and Laya was dropped without agreeing it first, departing from the mid-sem plan | User review | Reversed the same day: Opus 5.5 restored for R7, Laya fine-tuned (DECISIONS.md) |
| 23 Nov | 5 | Option probability scoring cannot be run in the workspace (no GPU) | — | Logic tested with a stand-in tokenizer (product of option-token probabilities) |
| 23 Nov | 5 | Laya training and Opus calls cannot run in the workspace (no model downloads, no API key) | — | Laya input format checked against the laya 0.5.2 source (`items_from_rows`, `target_from_expected`); pipeline tested with a stub agent; a 3-line Opus cost check runs before the full run |
| 23 Nov | 5 | All 5 R6 systems + Laya passed the bar on dev, both conditions | Cell 2/4 | **Success** |
| 23 Nov | 5 | Laya fine-tune ran in 18.7 min on T4 with no memory errors; calibration slice accuracy 82.7% → 87.0% | Cell 3 | **Success** |
| 23 Nov | 5 | Laya warning: `person` (noul) calibration temperature fitted at the clamp edge (5 of [0.5, 5]) | Cell 3 log | The `person` probabilities may still be over-confident. Our gate does not use them for routing (it uses the flag ≥ 0.5 plus code rules); reported as a limitation |
| 23 Nov | 5 | Laya warning: "Conflicting schema for question 'match' across rows; keeping first seen definition" | Cell 3 log | Expected cause: the number of options differs per line (1–5). Risk: Laya could be unable to choose options missing from the first row's schema. Checked with `scripts/significance.py` (which options Laya chose, and its accuracy when the right answer is option 3 or later) |
| 23 Nov | 5 | Some per-step training losses printed as negative (e.g. −0.575), and mean loss did not fall steadily (1.08 → 1.31 → 1.25 → 1.15) | Cell 3 log | Not explained yet (the library's loss probably includes a calibration/auxiliary term). Results on dev and test are strong, so it is reported as observed, not claimed to be understood |
| 23 Nov | 5 | Laya is over-confident: 170/177 dev lines got probability ≥ 0.999 but 97.1% of those were right | Threshold sweep | The threshold knob does nothing for Laya (auto rate flat from 0.0 to 0.9999); safety comes from the code rules |
| 23 Nov | 5 | The probability threshold added little for any fine-tuned model; all five chosen thresholds were 0.0 | Threshold sweep | Reported as a finding: forced reviews + guardrail do the safety work. Lowering ECE (0.05) did not translate into a useful knob because most probabilities sit at ≥ 0.999 |
| 23 Nov | 5 | Base Qwen3.5-2B: a threshold of 0.8 would remove its automatic errors but drops stress auto rate to 47.5% (< 50% bar) | Threshold sweep | Kept 0.0 by the frozen rule → 0.74% auto errors on test, ₹590 misbooked (within bar) |
| 23 Nov | 5 | Opus 5.5 hit the option ceiling on dev but not on test: 5 wrong choices per condition with the right option offered (full_payment 3, short_payment 2) | Cell 8 | Reported as is; the frontier model did **not** beat the fine-tuned local models on the held-out month. Significance check added |
| 23 Nov | 5 | Opus handled the fewest lines automatically of all gated systems (71.9% / 65.4% test) | Cell 7 | Its own "needs review" flag is conservative; more work for the accountant |
| 23 Nov | 5 | Test month harder for retrieval: party recall 95.9 → 93.8% (clean), 95.3 → 91.6% (stress); ceiling 94.4 → 92.4%, 93.8 → 90.3% | Cell 7/8 | 14–18 errors per condition are "right answer not offered" — retrieval/option building is the clear next improvement |
| 23 Nov | 5 | R5 LoRA 0.8B without the guardrail sent only 6/7 bank-detail changes to a person on test stress → FAIL | Cell 7 | Confirms the R6 guardrail is needed, on unseen data |
| 23 Nov | 5 | Gain of the best model over the no-AI R6 control on test is only 3 lines (clean) / 2 lines (stress) of 185 | Cell 8 | Reported honestly; significance test (`scripts/significance.py`) to show whether it is more than luck |
| 23 Nov | 5 | Step 3 claim "bank-detail rule is the one code alone cannot meet" superseded: the R6 regex guardrail gives the no-AI control 7/7 | Cell 7 | Corrected in FINDINGS_LOG (finding 11) |
| 23 Nov | 5 | Opus actual cost 19% above the 3-line estimate (thinking tokens on harder lines) | Console balance | Total Opus spend ≈ $4.18 of $10; estimate method noted |
| 23 Nov | 5 | Bug in `scripts/same_lines.py`: run names were parsed with `split("_", 2)`, which dropped the "R6_"/"R7_" prefix | Testing the new significance script | Fixed (`split("_", 1)`); same_lines.py was only used in the abandoned Gemini plan, so no logged result is affected |
| 23 Nov | 5 | Significance check: no AI system is significantly better than the no-AI control or than Opus on test (all p ≥ 0.18) | `significance.py` | Reported honestly; claims worded as "matched", not "beat". Limitation: one test month, 185 lines per condition |
| 23 Nov | 5 | Laya "conflicting schema" risk could not be tested on test (0 lines with the right answer at option 3+, 0 duplicates) | `significance.py` | Stated as untested; dev duplicates 4/4 correct |
| 23 Nov | 5 | Significance script itself worked first time on real runs | Colab | **Success** |
| 23 Nov | 6 | **Laya's latency left out the pipeline:** `laya_inputs` dropped the search / rerank / context steps, so Laya's time (0.068 s, ₹0.59 per 1,000) counted only its own forward pass, unlike every other system | Reading the timing code while preparing the Mac runs | Fixed (`laya_inputs` returns the steps; test added). Claims corrected in FINDINGS_LOG and both reports: Laya ≈ 0.17 s end to end (estimated), "7–34× / 160–800×" → "about 7–13× / 160–340×". Accuracy unaffected. The Mac runs give the measured figure |
| 23 Nov | 6 | HF backend was hard-wired to CUDA (`device_map="cuda"`, `torch.cuda.synchronize`) and could not run on the Mac | Preparing Step 6 | `pratyaksha/llm/device.py`: cuda → mps (Apple GPU) → cpu, with the device used recorded in each run's config; tests added |
| 23 Nov | 6 | Mac smoke test: rules, R6 control and Laya ran (5/5 lines same answer as Colab), but the LoRA 0.8B run failed: `Qwen2VLImageProcessor requires the PIL library … Torchvision` | Smoke-test log | Qwen3.5 is a multimodal model and loads its image processor even for text-only use. Colab has Pillow and torchvision preinstalled; a clean Mac venv does not. Added both to `requirements-mac.txt` |
| 23 Nov | 6 | Mac smoke test success: Apple GPU (MPS) runs the reranker and Laya; 0 bytes left the machine | Smoke-test log | **Success** |
| 23 Nov | 6 | Mac smoke test passed for all 4 systems after the fix: 5/5 lines gave the same answer as Colab for rules, R6 control, Laya and LoRA 0.8B, in both conditions; 0 bytes left the machine | Smoke-test log | **Success**. LoRA 0.8B p50 ≈ 0.94–1.0 s on the M1 Pro (one line at a time, reference PyTorch kernels: the fast `causal_conv1d` / `flash-linear-attention` kernels are CUDA-only, same fallback as on Colab). The 5-line timings include warm-up, so the full 185-line run is the measurement |
| 23 Nov | 6 | Full Mac run: 1,480/1,480 answers identical to Colab across rules, R6 control, Laya and LoRA 0.8B, both conditions | `mac_vs_colab.py` | **Success** — results are hardware-independent |
| 23 Nov | 6 | Power was not measured with `powermetrics`; 35 W assumed | Run log | Stated as an assumption; power is under 1% of the owned-machine cost, so no conclusion depends on it |
| 23 Nov | 6 | Demo app ran live on the MacBook: all three local systems "Live" on the Apple GPU, offline; Opus replayed with its recorded answer (1.5 KB sent out on that line) | Screenshot from the user | **Success** |
| 23 Nov | 6 | Demo polish: a probability of 0.9999 displayed as "100% sure", which overstates certainty; card labels wrapped at the user's browser zoom | Screenshot | Probabilities ≥ 99.95% now read "over 99.9%"; card labels shortened and kept on one line |
| 24 Nov | 6 | Deck check: the "What worked" slide first said no gated system made a wrong automatic booking on the test month, but the untrained 2B model (gated) made 0.74% | Cross-checking every deck number against this log | Corrected to "no fine-tuned model, Laya or Opus" |
