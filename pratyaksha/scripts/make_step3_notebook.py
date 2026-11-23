"""Builds notebooks/step3_R3.ipynb. Each step: what we do, and why."""
import json
from pathlib import Path

ROOT = "/content/drive/MyDrive/Colab Notebooks"
cells = []
md = lambda s: cells.append({"cell_type": "markdown", "metadata": {}, "source": s.strip()})
code = lambda s: cells.append({"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": s.strip()})

md("""
# PRATYAKSHA · Step 3 — R3: give the AI the right information, computed

**What Step 2 showed:** small models cannot add or subtract, so they listed every invoice instead of choosing.
**What R3 changes:** code computes which invoices explain the amount (exactly, minus TDS, or slightly short),
adds the payment e-mails and any identical earlier credit, and the AI just **picks one option**.

**The fair test:** a no-AI *control* gets the same options and always picks the first one.
The AI earns its place only if it beats that control.

Run top to bottom. Runtime: **T4 GPU**. Upload `pratyaksha_step3.zip` to *Colab Notebooks* first.
""")
md("## 1. Connect Drive\n**Why:** code and results live in Drive.")
code("from google.colab import drive\ndrive.mount('/content/drive')")
md("## 2. Unpack Step 3 code\n**Why:** adds R3 without touching earlier results.")
code(f'%cd "{ROOT}"\n!unzip -o -q pratyaksha_step3.zip\n%cd "{ROOT}/pratyaksha"\n!ls pratyaksha/systems')
md("## 3. Install\n**Why:** a new Colab session starts empty.")
code("!pip install -q -U transformers accelerate sentence-transformers rank-bm25 pytest")
md("## 4. Data and tests\n**Expect:** `26 passed`. **Why:** checks that the computed options never use future invoices and always add up.")
code("!python -m pratyaksha.world.generate --out data/wwi_in\n!python -m pytest -q")
md("""
## 5. The no-AI control (R3 context, always pick the first option)
**Why:** this is the bar the AI must beat. It uses the real reranker (GPU), but no language model. ~2 min.
**Watch:** *Right answer among computed options* = the best any model could do with these options.
""")
code("""
for cond in ["clean", "stress"]:
    !python -m pratyaksha.harness.runner --system r3_control --split dev --condition {cond} --cost-mode gpu
""")
md("""
## 6. R1 with the 2B model (fair R1 vs R2 comparison)
**Why:** in Step 2 the 0.8B model scored ~0% in both R1 and R2, so we could not tell whether reranking helps.
2B works, so we run R1 at 2B and compare with the R2-2B result from Step 2. ~6 min each.
""")
code("""
for cond in ["clean", "stress"]:
    !python -m pratyaksha.harness.runner --system r1 --split dev --condition {cond} --cost-mode gpu \\
        --opt model=Qwen/Qwen3.5-2B --opt batch=8 --opt k=5
""")
md("## 7. R3 with the 0.8B model\n**Why:** with the maths done for it, can even the smallest model now work?")
code("""
for cond in ["clean", "stress"]:
    !python -m pratyaksha.harness.runner --system r3 --split dev --condition {cond} --cost-mode gpu \\
        --opt model=Qwen/Qwen3.5-0.8B --opt batch=8
""")
md("## 8. R3 with the 2B model\n**Why:** same question at the size that worked in Step 2.")
code("""
for cond in ["clean", "stress"]:
    !python -m pratyaksha.harness.runner --system r3 --split dev --condition {cond} --cost-mode gpu \\
        --opt model=Qwen/Qwen3.5-2B --opt batch=8
""")
md("""
## 9. (Optional) R3 with the 4B model
**Why:** does a bigger model read the e-mails better (bank-detail changes, which invoices)? ~8 GB download.
Batch 4 to fit memory.
""")
code("""
for cond in ["clean", "stress"]:
    !python -m pratyaksha.harness.runner --system r3 --split dev --condition {cond} --cost-mode gpu \\
        --opt model=Qwen/Qwen3.5-4B --opt batch=4
""")
md("## 10. Compare all runs\n**Why:** this table is the Step 3 result.")
code("!python scripts/compare.py --split dev")
md("""
## 11. What did the AI add over the control?
**Why:** shows the exact lines where the AI fixed or broke the control's answer. This is the evidence
for "what the model buys". (Edit `R3_Qwen3.5-2B` to `R3_Qwen3.5-4B` if you ran cell 9.)
""")
code("""
for cond in ["clean", "stress"]:
    !python scripts/vs_control.py --model R3_Qwen3.5-2B --condition {cond}
""")
md("## 12. Send back\nDownload the notebook (*File → Download → .ipynb*) and send it, as you did for Step 2.")

nb = {"cells": cells, "metadata": {"accelerator": "GPU", "colab": {"gpuType": "T4", "provenance": []},
      "kernelspec": {"name": "python3", "display_name": "Python 3"}, "language_info": {"name": "python"}},
      "nbformat": 4, "nbformat_minor": 0}
Path("notebooks/step3_R3.ipynb").write_text(json.dumps(nb, indent=1))
print("wrote notebooks/step3_R3.ipynb with", len(cells), "cells")
