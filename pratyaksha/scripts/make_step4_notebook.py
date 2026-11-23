"""Builds notebooks/step4_R4_R5.ipynb. Each step: what we do, and why."""
import json
from pathlib import Path

ROOT = "/content/drive/MyDrive/Colab Notebooks"
cells = []
md = lambda s: cells.append({"cell_type": "markdown", "metadata": {}, "source": s.strip()})
code = lambda s: cells.append({"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": s.strip()})

md("""
# PRATYAKSHA · Step 4 — R4 (what errors are left?) and R5 (fine-tuning)

**What Step 3 showed:** with computed options, the 2B model is ~90% right and never wrong automatically,
but it sends ~75% of lines to a person. The 0.8B model is at ~63%.
**This notebook:** (R4) count which errors fine-tuning *could* fix, then (R5) teach the models on
months 1–4 of the business's own past reconciliations, and test on month 5 as before.

Runtime **T4 GPU**. Upload `pratyaksha_step4.zip` to *Colab Notebooks* first.
**Long notebook (about 2–2.5 h).** You can stop after any section: results and trained models are saved
to Drive. To continue in a new session, run cells 1–4 again, then jump to where you stopped.
""")
md("## 1. Connect Drive")
code("from google.colab import drive\ndrive.mount('/content/drive')")
md("## 2. Unpack Step 4 code\n**Why:** adds the fine-tuning code; earlier results stay.")
code(f'%cd "{ROOT}"\n!unzip -o -q pratyaksha_step4.zip\n%cd "{ROOT}/pratyaksha"\n!ls pratyaksha/finetune')
md("## 3. Install\n**Why:** `peft` adds LoRA; `bitsandbytes` gives the 8-bit optimiser that lets full fine-tuning fit on a T4.")
code("!pip install -q -U transformers accelerate sentence-transformers rank-bm25 pytest peft bitsandbytes")
md("## 4. Data and tests\n**Expect:** `29 passed`. New tests check that training data comes only from months 1–4 and that every target answer is correct.")
code("!python -m pratyaksha.world.generate --out data/wwi_in\n!python -m pytest -q")

md("""
## 5. R4 — what errors are left after R3? (no GPU work, reads Step 3 results)
**Why:** fine-tune only if the remaining errors are the kind training can fix (our report's rule).
- *correct + review* = right but sent to a person → training can teach it when **not** to ask
- *wrong, right answer WAS offered* = picked the wrong option → training can fix
- *wrong, right answer NOT offered* = our options missed it → training **cannot** fix
""")
code("""
!python scripts/error_analysis.py --model R3_Qwen3.5-2B
!python scripts/error_analysis.py --model R3_Qwen3.5-0.8B
""")

md("""
## 6. Re-run the 4B model with "thinking" switched off
**Why:** in Step 3 the 4B model wrote a long "Thinking Process" and was cut off on every line.
The code now turns thinking off. This checks the fix (clean lines only, ~8 min).
**Expect:** far fewer than 177 unusable answers.
""")
code("""
!python -m pratyaksha.harness.runner --system r3 --split dev --condition clean --cost-mode gpu \\
    --opt model=Qwen/Qwen3.5-4B --opt batch=4 --tag nothink
""")

md("""
## 7. Build the training data (months 1–4 only)
**What:** for each past bank line (clean and messy), the exact R3 prompt plus the correct short answer,
e.g. `{"option": "M2", "needs_review": false}`.
**Why:** the business's own history is the teacher; month 5 (dev) and month 6 (test) are never used.
**Expect:** about 1,270 examples.
""")
code("!python -m pratyaksha.finetune.build_sft --out data/sft/train.jsonl")

md("""
## 8. Dry run (5 training steps)
**Why:** catches memory or setup errors in 2 minutes instead of 20. **Expect:** a few loss values and "saved to".
""")
code("""
!python -m pratyaksha.finetune.train --model Qwen/Qwen3.5-0.8B --mode lora --out models/dryrun --max-steps 5
""")

md("""
## 9. R5a — LoRA fine-tune of the 0.8B model (~20–30 min), then test it
**What:** freeze the model; train small add-on layers (well under 5% of the weights).
**Why:** the main question of the project — how far can the smallest model get with training?
**Watch:** the loss should fall (roughly from >1 to <0.2).
""")
code("""
!python -m pratyaksha.finetune.train --model Qwen/Qwen3.5-0.8B --mode lora --out models/r5_lora_0.8b
for cond in ["clean", "stress"]:
    !python -m pratyaksha.harness.runner --system r5 --split dev --condition {cond} --cost-mode gpu \\
        --opt model=Qwen/Qwen3.5-0.8B --opt adapter=models/r5_lora_0.8b --opt batch=8
""")

md("""
## 10. R5b — LoRA fine-tune of the 2B model (~40–60 min), then test it
**Why:** the 2B model was already accurate but over-cautious. Does training teach it when it is safe
to act alone, without making automatic mistakes?
""")
code("""
!python -m pratyaksha.finetune.train --model Qwen/Qwen3.5-2B --mode lora --out models/r5_lora_2b
for cond in ["clean", "stress"]:
    !python -m pratyaksha.harness.runner --system r5 --split dev --condition {cond} --cost-mode gpu \\
        --opt model=Qwen/Qwen3.5-2B --opt adapter=models/r5_lora_2b --opt batch=8
""")

md("""
## 11. (Optional) R5c — FULL fine-tune of the 0.8B model (~30–45 min), then test it
**Why:** LoRA vs full fine-tuning is in the mid-sem plan. Full training changes every weight.
**Note:** saves ~3.5 GB to Drive. Skip if Drive space is low or time is short.
""")
code("""
!python -m pratyaksha.finetune.train --model Qwen/Qwen3.5-0.8B --mode full --out models/r5_full_0.8b
for cond in ["clean", "stress"]:
    !python -m pratyaksha.harness.runner --system r5 --split dev --condition {cond} --cost-mode gpu \\
        --opt model=models/r5_full_0.8b --opt batch=8
""")

md("## 12. Compare everything\n**Why:** this is the Step 4 result: R3 vs R5, model size, LoRA vs full, against the no-AI control.")
code("!python scripts/compare.py --split dev")
md("## 13. What is still wrong after fine-tuning?\n**Why:** shows whether training removed over-caution and wrong choices, and what is left for R6.")
code("""
!python scripts/error_analysis.py --model R5_r5_lora_0.8b
!python scripts/error_analysis.py --model R5_r5_lora_2b
!python scripts/error_analysis.py --model R5_r5_full_0.8b
""")
md("## 14. Training cost\n**Why:** fine-tuning is a one-time cost; we report it next to the per-task cost.")
code("""
import json, glob
for f in sorted(glob.glob("models/r5_*/train_log.json")):
    d = json.load(open(f))
    print(f"{f.split('/')[1]:<16} {d['mode']:<5} {d['train_seconds']/60:6.1f} min  steps {d['steps']:<4} "
          f"trainable {d['trainable_params']:,} of {d['total_params']:,}  loss {d['loss'][0]['loss']} -> {d['loss'][-1]['loss']}")
""")
md("## 15. Send back\n*File → Download → .ipynb* and send it.")

nb = {"cells": cells, "metadata": {"accelerator": "GPU", "colab": {"gpuType": "T4", "provenance": []},
      "kernelspec": {"name": "python3", "display_name": "Python 3"}, "language_info": {"name": "python"}},
      "nbformat": 4, "nbformat_minor": 0}
Path("notebooks/step4_R4_R5.ipynb").write_text(json.dumps(nb, indent=1))
print("wrote notebooks/step4_R4_R5.ipynb with", len(cells), "cells")
