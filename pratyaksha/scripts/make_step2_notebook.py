"""Builds notebooks/step2_R0_R1_R2.ipynb. Each step: what we do, and why."""
import json
from pathlib import Path

ROOT = "/content/drive/MyDrive/Colab Notebooks"
cells = []
md = lambda s: cells.append({"cell_type": "markdown", "metadata": {}, "source": s.strip()})
code = lambda s: cells.append({"cell_type": "code", "metadata": {}, "execution_count": None,
                               "outputs": [], "source": s.strip()})

md("""
# PRATYAKSHA · Step 2 — R0 (no lookup), R1 (lookup), R2 (lookup + reorder)

**Goal of this notebook:** find out what *retrieval* and *reranking* buy a small AI model on our
bank-reconciliation task, compared with the no-AI baseline (80.8% clean / 59.9% messy).

Run the cells **top to bottom**. Each cell says **what** it does and **why**.
Before starting: *Runtime → Change runtime type → T4 GPU*.
""")

md("""
## 1. Connect Google Drive
**Why:** the project and all results live in Drive, so nothing is lost when Colab resets.
""")
code(f"""
from google.colab import drive
drive.mount('/content/drive')
""")

md("""
## 2. Unpack the Step 2 code over the Step 1 folder
**What:** upload `pratyaksha_step2.zip` into your **Colab Notebooks** folder first, then run this.
**Why:** it adds the new code (retrieval, reranker, AI client) without touching your data or Step 1 results.
""")
code(f"""
%cd "{ROOT}"
!unzip -o -q pratyaksha_step2.zip
%cd "{ROOT}/pratyaksha"
!ls pratyaksha
""")

md("""
## 3. Install libraries
**Why:** `transformers` runs the Qwen model, `sentence-transformers` runs the reranker,
`rank-bm25` is the keyword search. Takes about 1–2 minutes.
""")
code("""
!pip install -q -U transformers accelerate sentence-transformers rank-bm25 pytest
import transformers, torch
print("transformers", transformers.__version__, "| torch", torch.__version__, "| GPU:", torch.cuda.get_device_name(0))
""")

md("""
## 4. Rebuild the data and run all tests
**Why:** the data folder is the same as Step 1 (same seed → same data). The tests (22) check the
answer key *and* the new retrieval/prompt code before we spend GPU time.
**Expect:** `22 passed`.
""")
code("""
!python -m pratyaksha.world.generate --out data/wwi_in
!python -m pytest -q
""")

md("""
## 5. Smoke test: can the model run at all?
**What:** loads **Qwen3.5-0.8B** (about 1.6 GB download) and asks one tiny question.
**Why:** catches setup problems in 1 minute instead of in the middle of a long run.
**Expect:** `PASS`. If it says `CHECK`, run the next line with `--dtype float32` instead.
""")
code("""
!python scripts/smoke_llm.py --model Qwen/Qwen3.5-0.8B
""")

md("""
## 6. R0 — the AI with NO lookup ("fail first")
**What:** the model sees only the bank line; it cannot see our customers or invoices.
**Why:** proves the model alone cannot do this job. We expect close to **0%** — that *is* the result.
We run only 40 lines because the outcome is obvious and GPU time is limited.
""")
code("""
!python -m pratyaksha.harness.runner --system r0 --split dev --condition clean --limit 40 --cost-mode gpu \\
    --opt model=Qwen/Qwen3.5-0.8B --opt batch=8
""")

md("""
## 7. R1 — add lookup (retrieval)
**What:** for each bank line, keyword search finds the **5 most likely customers**, and we give the
model those customers plus their **unpaid invoices on that date** (never future ones).
**Why:** the model can now see the books. We run both clean and messy lines.
**Watch:** *Accuracy*, and *Right party among retrieved* (how often the search found the right customer).
About 3–6 minutes each.
""")
code("""
for cond in ["clean", "stress"]:
    !python -m pratyaksha.harness.runner --system r1 --split dev --condition {cond} --cost-mode gpu \\
        --opt model=Qwen/Qwen3.5-0.8B --opt batch=8 --opt k=5
""")

md("""
## 8. R2 — add reranking
**What:** search wider (top 10), then a second model (**bge-reranker-v2-m3**, about 2.3 GB) reads the
bank line and each customer name side by side, re-orders them, and we keep only the **best 3**.
**Why:** fewer, better candidates → fewer wrong invoices in the prompt → fewer mistakes, and a shorter
prompt (faster). Does it actually help? That is what we measure.
""")
code("""
for cond in ["clean", "stress"]:
    !python -m pratyaksha.harness.runner --system r2 --split dev --condition {cond} --cost-mode gpu \\
        --opt model=Qwen/Qwen3.5-0.8B --opt batch=8 --opt keep=3
""")

md("""
## 9. Compare everything in one table
**Why:** this is the result of Step 2 — each rung next to the no-AI baseline.
Columns: accuracy, share handled automatically, error rate on those, speed (p50 seconds),
*party@k* = right customer found, *tok_in* = prompt size, parse errors, business bar.
""")
code("""
!python scripts/compare.py --split dev
""")

md("""
## 10. (Optional, if time) Same R2 with the bigger 2B model
**Why:** is the problem the *information* we give the model, or the *size* of the model?
If 2B is much better than 0.8B with the same input, model size matters here.
""")
code("""
for cond in ["clean", "stress"]:
    !python -m pratyaksha.harness.runner --system r2 --split dev --condition {cond} --cost-mode gpu \\
        --opt model=Qwen/Qwen3.5-2B --opt batch=8 --opt keep=3
!python scripts/compare.py --split dev
""")

md("""
## 11. Send results back
Download **`runs/index.csv`** from the Drive folder (or screenshot the table from cell 9/10) and send it.
Every run's full detail is in `runs/<run_id>/scorecard.md`.
""")

nb = {"cells": cells, "metadata": {"accelerator": "GPU", "colab": {"gpuType": "T4", "provenance": []},
                                   "kernelspec": {"name": "python3", "display_name": "Python 3"},
                                   "language_info": {"name": "python"}},
      "nbformat": 4, "nbformat_minor": 0}
Path("notebooks").mkdir(exist_ok=True)
Path("notebooks/step2_R0_R1_R2.ipynb").write_text(json.dumps(nb, indent=1))
print("wrote notebooks/step2_R0_R1_R2.ipynb with", len(cells), "cells")
