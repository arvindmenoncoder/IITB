"""Builds notebooks/step4_resume.ipynb: only what the Colab limit cut off."""
import json
from pathlib import Path

ROOT = "/content/drive/MyDrive/Colab Notebooks"
cells = []
md = lambda s: cells.append({"cell_type": "markdown", "metadata": {}, "source": s.strip()})
code = lambda s: cells.append({"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": s.strip()})

md("""
# PRATYAKSHA · Step 4 (resume) — finish what the Colab limit stopped
The trained models (`models/r5_lora_0.8b`, `models/r5_lora_2b`) are already in Drive, so nothing is retrained.
No new zip needed. Runtime **T4 GPU**. Total ~15 min (+~45 min if you run the optional full fine-tune).
""")
md("## 1. Connect Drive and go to the project")
code(f'from google.colab import drive\ndrive.mount("/content/drive")\n%cd "{ROOT}/pratyaksha"\n!ls models')
md("## 2. Install\n**Why:** a new session starts empty.")
code("!pip install -q -U transformers accelerate sentence-transformers rank-bm25 pytest peft bitsandbytes")
md("## 3. Rebuild data (same seed, same data)")
code("!python -m pratyaksha.world.generate --out data/wwi_in")
md("## 4. The missing run: R5 LoRA 2B on messy lines (~6 min)")
code("""
!python -m pratyaksha.harness.runner --system r5 --split dev --condition stress --cost-mode gpu \\
    --opt model=Qwen/Qwen3.5-2B --opt adapter=models/r5_lora_2b --opt batch=8
""")
md("""
## 5. Why does the 2B model write ~73 tokens when the answer is ~15?
**Why:** extra tokens cost time. This prints what it actually wrote (no GPU needed).
""")
code("""
import json, glob
run = sorted(glob.glob("runs/*R5_r5_lora_2b_dev_clean/predictions.jsonl"))[-1]
for r in [json.loads(l) for l in open(run)][:3]:
    print("-----"); print(repr(r["pred"]["raw_output"][:400]))
""")
md("""
## 6. (Optional) Full fine-tune of 0.8B (~45–60 min) and test
**Why:** LoRA vs full, from the mid-sem plan. Saves ~3.5 GB to Drive. Skip if short on time or GPU quota.
""")
code("""
!python -m pratyaksha.finetune.train --model Qwen/Qwen3.5-0.8B --mode full --out models/r5_full_0.8b
for cond in ["clean", "stress"]:
    !python -m pratyaksha.harness.runner --system r5 --split dev --condition {cond} --cost-mode gpu \\
        --opt model=models/r5_full_0.8b --opt batch=8
""")
md("## 7. Compare everything")
code("!python scripts/compare.py --split dev")
md("## 8. What is still wrong after fine-tuning?")
code("""
!python scripts/error_analysis.py --model R5_r5_lora_0.8b
!python scripts/error_analysis.py --model R5_r5_lora_2b
!python scripts/error_analysis.py --model R5_r5_full_0.8b
""")
md("## 9. Training cost")
code("""
import json, glob
for f in sorted(glob.glob("models/r5_*/train_log.json")):
    d = json.load(open(f))
    print(f"{f.split('/')[1]:<16} {d['mode']:<5} {d['train_seconds']/60:6.1f} min  steps {d['steps']:<4} "
          f"trainable {d['trainable_params']:,} of {d['total_params']:,}  loss {d['loss'][0]['loss']} -> {d['loss'][-1]['loss']}")
""")
md("## 10. Send back\n*File → Download → .ipynb*.")

nb = {"cells": cells, "metadata": {"accelerator": "GPU", "colab": {"gpuType": "T4", "provenance": []},
      "kernelspec": {"name": "python3", "display_name": "Python 3"}, "language_info": {"name": "python"}},
      "nbformat": 4, "nbformat_minor": 0}
Path("notebooks/step4_resume.ipynb").write_text(json.dumps(nb, indent=1))
print("ok")
