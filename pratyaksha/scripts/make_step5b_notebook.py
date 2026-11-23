"""Builds notebooks/step5b_laya_opus_test.ipynb."""
import json
from pathlib import Path

ROOT = "/content/drive/MyDrive/Colab Notebooks"
cells = []
md = lambda s: cells.append({"cell_type": "markdown", "metadata": {}, "source": s.strip()})
code = lambda s: cells.append({"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": s.strip()})
GO = f'%cd "{ROOT}/pratyaksha"'
HELP = '''
import glob, os, json
def done(name, split, cond):
    """True if a finished run already exists (so re-running this cell never repeats GPU or API work)."""
    return any(os.path.exists(os.path.join(os.path.dirname(p), "summary.json"))
               for p in glob.glob(f"runs/*_{name}_{split}_{cond}*/predictions.jsonl"))
'''

md("""
# PRATYAKSHA · Step 5b — Laya (System-1), Claude Opus 5.5 (R7), and the final test month

This replaces cells 4–7 of the Step 5 notebook. As in the mid-sem plan:
- **Laya** (421M, non-generative System-1 decision model) is fine-tuned on months 1–4 to choose the match and
  decide "alone or a person", then routed through the same R6 rules.
- **Claude Opus 5.5** is the frontier reference, on **every** dev and test line, with the same evidence.
- Then **every system runs once on the held-out test month**.

Before you start: Colab **Secrets** (key icon, left sidebar) must contain `ANTHROPIC_API_KEY` with *Notebook access* on.
Upload `pratyaksha_step5b.zip` to *Colab Notebooks*. Runtime **T4 GPU**. About 2.5–3 h in total; every cell can be
re-run safely after a reconnect (finished runs are skipped). Always run cell 1 first in a new session.
""")

md("## 1. Setup\n**Why:** Drive, the new code, libraries (now including `laya`), data. **Expect:** `35 passed`.")
code(f"""
from google.colab import drive
drive.mount("/content/drive")
%cd "{ROOT}"
!unzip -o -q pratyaksha_step5b.zip
{GO}
!pip install -q -U transformers accelerate sentence-transformers rank-bm25 pytest peft bitsandbytes laya
!pip uninstall -y -q torchao
!python -m pratyaksha.world.generate --out data/wwi_in
!python -m pytest -q
!ls models
""")

md("""
## 2. R6 on the dev month (skips anything already run in Step 5)
**Why:** the gate needs each model's per-line probability on dev, to choose thresholds there and never on test.
""")
code(f"""
{GO}
{HELP}
jobs = [("R6_control_first_option", "--system r6_control"),
        ("R6_Qwen3.5-2B", "--system r6 --opt threshold=0 --opt model=Qwen/Qwen3.5-2B --opt batch=8"),
        ("R6_r5_lora_0.8b", "--system r6 --opt threshold=0 --opt model=Qwen/Qwen3.5-0.8B --opt adapter=models/r5_lora_0.8b --opt batch=8"),
        ("R6_r5_lora_2b", "--system r6 --opt threshold=0 --opt model=Qwen/Qwen3.5-2B --opt adapter=models/r5_lora_2b --opt batch=8"),
        ("R6_r5_full_0.8b", "--system r6 --opt threshold=0 --opt model=models/r5_full_0.8b --opt batch=8")]
for cond in ["clean", "stress"]:
    for name, args in jobs:
        if done(name, "dev", cond):
            print("already done:", name, cond); continue
        !python -m pratyaksha.harness.runner {{args}} --split dev --condition {{cond}} --cost-mode gpu
""")

md("""
## 3. Laya — build training data and fine-tune (~30–60 min)
**What:** for each past bank line (months 1–4, clean + messy): the evidence (bank line, candidate parties, e-mails), the
computed options, the right option, and whether a person had to check it. Then fine-tune Laya's
*typed-decisions* checkpoint (1,024-token input) with **option shuffling**.
**Why shuffling:** the right answer is usually option M1; without shuffling Laya could learn "always pick the first",
which is just our no-AI control again.
**Why its own page matters here:** Laya is near chance before fine-tuning and ships over-confident; the trainer fits
calibration temperatures at the end, which we then check in cell 5.
""")
code(f"""
{GO}
import time, json
!python -m pratyaksha.finetune.build_laya --out data/laya/train.jsonl
!laya-train --data data/laya/train.jsonl --base typed-decisions --out models/laya_t1 --max-len 1024 --shuffle-options --device cuda --micro-batch 4 --grad-accum 16 --dry-run
t0 = time.time()
!laya-train --data data/laya/train.jsonl --base typed-decisions --out models/laya_t1 --max-len 1024 --shuffle-options --device cuda --micro-batch 4 --grad-accum 16
json.dump({{"train_seconds": round(time.time() - t0, 1)}}, open("models/laya_t1/train_time.json", "w"))
print("Laya training minutes:", round((time.time() - t0) / 60, 1))
""")

md("## 4. Laya on the dev month (threshold 0, so every probability is stored)")
code(f"""
{GO}
{HELP}
for cond in ["clean", "stress"]:
    if not done("R6_laya_laya_t1", "dev", cond):
        !python -m pratyaksha.harness.runner --system r6_laya --split dev --condition {{cond}} --cost-mode gpu --opt threshold=0 --opt laya=models/laya_t1
""")

md("""
## 5. The threshold knob for every model (no GPU)
**Why:** picks each model's threshold on dev (lowest that passes the business bar on clean and messy), and shows
calibration: when a model says 97%, is it right 97% of the time?
""")
code(f"""
{GO}
for m in ["R6_Qwen3.5-2B", "R6_r5_lora_0.8b", "R6_r5_lora_2b", "R6_r5_full_0.8b", "R6_laya_laya_t1"]:
    !python scripts/threshold_sweep.py --model {{m}}
""")

md("""
## 6. R7 — Claude Opus 5.5 on the dev month
**First a 3-line check** that prints the real cost per line, then the full run (177 clean + 177 messy).
Price: $4 per million input tokens, $20 per million output tokens; Opus always thinks, and thinking is billed as output.
Answers are cached in `runs/opus_cache.jsonl`, so a re-run never pays twice. The egress meter counts every byte sent.
""")
code(f"""
{GO}
import os, json, glob
from google.colab import userdata
os.environ["ANTHROPIC_API_KEY"] = userdata.get("ANTHROPIC_API_KEY")
!python -m pratyaksha.harness.runner --system r7 --split dev --condition clean --limit 3 --cost-mode api --api-usd-in 4 --api-usd-out 20 --tag check
s = json.load(open(sorted(glob.glob("runs/*R7_claude-opus-5-5_dev_clean_check/summary.json"))[-1]))
per_line_usd = (s["tokens_in_per_task"] * 4 + s["tokens_out_per_task"] * 20) / 1e6
print(f"tokens in/out per line: {{s['tokens_in_per_task']:.0f}} / {{s['tokens_out_per_task']:.0f}}")
print(f"cost per line ≈ ${{per_line_usd:.4f}};  all 708 dev+test lines ≈ ${{per_line_usd*708:.2f}}")
""")
md("**Check the estimate above.** If it fits your credit, run the next cell (about 30–60 min; it needs no GPU work except the reranker).")
code(f"""
{GO}
{HELP}
import os
from google.colab import userdata
os.environ["ANTHROPIC_API_KEY"] = userdata.get("ANTHROPIC_API_KEY")
for cond in ["clean", "stress"]:
    if not done("R7_claude-opus-5-5", "dev", cond + "_full"):
        !python -m pratyaksha.harness.runner --system r7 --split dev --condition {{cond}} --cost-mode api --api-usd-in 4 --api-usd-out 20 --tag full
""")

md("""
## 7. THE FINAL TEST MONTH — every system once (~60–90 min)
**Why:** the acceptance bar was frozen on 23 Nov and every threshold was chosen on dev. Month 6 has never been used,
so these are the honest numbers for the report. Nothing is changed after this cell runs.
""")
code(f"""
{GO}
{HELP}
import os
from google.colab import userdata
os.environ["ANTHROPIC_API_KEY"] = userdata.get("ANTHROPIC_API_KEY")
def thr(m):
    f = f"runs/threshold_{{m}}.json"
    t = json.load(open(f))["threshold"] if os.path.exists(f) else None
    return 0.999 if t is None else t
T = {{m: thr(m) for m in ["R6_Qwen3.5-2B", "R6_r5_lora_0.8b", "R6_r5_lora_2b", "R6_r5_full_0.8b", "R6_laya_laya_t1"]}}
print("thresholds chosen on dev:", T)
json.dump(T, open("runs/thresholds_used_on_test.json", "w"), indent=1)
jobs = [("rules", "--system rules"),
        ("R3_control_first_option", "--system r3_control"),
        ("R6_control_first_option", "--system r6_control"),
        ("R5_r5_lora_0.8b", "--system r5 --opt model=Qwen/Qwen3.5-0.8B --opt adapter=models/r5_lora_0.8b --opt batch=8"),
        ("R6_Qwen3.5-2B", f"--system r6 --opt threshold={{T['R6_Qwen3.5-2B']}} --opt model=Qwen/Qwen3.5-2B --opt batch=8"),
        ("R6_r5_lora_0.8b", f"--system r6 --opt threshold={{T['R6_r5_lora_0.8b']}} --opt model=Qwen/Qwen3.5-0.8B --opt adapter=models/r5_lora_0.8b --opt batch=8"),
        ("R6_r5_lora_2b", f"--system r6 --opt threshold={{T['R6_r5_lora_2b']}} --opt model=Qwen/Qwen3.5-2B --opt adapter=models/r5_lora_2b --opt batch=8"),
        ("R6_r5_full_0.8b", f"--system r6 --opt threshold={{T['R6_r5_full_0.8b']}} --opt model=models/r5_full_0.8b --opt batch=8"),
        ("R6_laya_laya_t1", f"--system r6_laya --opt threshold={{T['R6_laya_laya_t1']}} --opt laya=models/laya_t1"),
        ("R7_claude-opus-5-5", "--system r7 --cost-mode api --api-usd-in 4 --api-usd-out 20")]
for cond in ["clean", "stress"]:
    for name, args in jobs:
        if done(name, "test", cond):
            print("already done:", name, cond); continue
        mode = "" if "--cost-mode" in args else "--cost-mode gpu"
        !python -m pratyaksha.harness.runner {{args}} {{mode}} --split test --condition {{cond}}
""")

md("## 8. The results table\n**Why:** the headline result of the project — test month, every system.")
code(f"""
{GO}
!python scripts/compare.py --split test
for m in ["R6_r5_lora_0.8b", "R6_r5_lora_2b", "R6_laya_laya_t1", "R7_claude-opus-5-5"]:
    !python scripts/error_analysis.py --model {{m}} --split test
""")
md("## 9. Send back\n*File → Download → .ipynb*, send it, then *Runtime → Disconnect and delete runtime*.")

nb = {"cells": cells, "metadata": {"accelerator": "GPU", "colab": {"gpuType": "T4", "provenance": []},
      "kernelspec": {"name": "python3", "display_name": "Python 3"}, "language_info": {"name": "python"}},
      "nbformat": 4, "nbformat_minor": 0}
Path("notebooks/step5b_laya_opus_test.ipynb").write_text(json.dumps(nb, indent=1))
print("ok", len(cells))
