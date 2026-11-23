"""Builds notebooks/step5_R6_R7_test.ipynb."""
import json
from pathlib import Path

ROOT = "/content/drive/MyDrive/Colab Notebooks"
cells = []
md = lambda s: cells.append({"cell_type": "markdown", "metadata": {}, "source": s.strip()})
code = lambda s: cells.append({"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": s.strip()})
GO = f'%cd "{ROOT}/pratyaksha"'

md("""
# PRATYAKSHA · Step 5 — R6 (gate + safety rule), R7 (Gemini reference), and the final test month

**R6 — who acts?** The model answers; *code* decides whether it may act alone:
1. a **safety rule**: any e-mail near the payment asking to change bank details → always a person;
2. risky categories (duplicate, unknown payer, short payment) → always a person;
3. a **System-1 gate**: act alone only if the model's own probability for its answer ≥ a threshold (the *knob*).

**R7 — the ceiling.** Gemini (a frontier cloud model) gets the same options and e-mails. Shows the best case,
its price, and the data that leaves the business.

**Test month.** The acceptance bar was frozen on 23 Nov (`docs/ACCEPTANCE_BAR.md`). Thresholds are chosen on the
dev month; then every main system is run **once** on the held-out month 6.

Runtime **T4 GPU**. Upload `pratyaksha_step5.zip` to *Colab Notebooks* first. ~1–1.5 h of GPU in total.
Every cell starts by going to the project folder, so you can re-run any cell after a reconnect
(but always run cell 1 first in a new session).
""")

md("## 1. Setup (always run first in a new session)\n**Why:** Drive, the new code, libraries and the data. **Expect:** `33 passed`.")
code(f"""
from google.colab import drive
drive.mount("/content/drive")
%cd "{ROOT}"
!unzip -o -q pratyaksha_step5.zip
{GO}
!pip install -q -U transformers accelerate sentence-transformers rank-bm25 pytest peft bitsandbytes
!pip uninstall -y -q torchao
!python -m pratyaksha.world.generate --out data/wwi_in
!python -m pytest -q
!ls models
""")

md("""
## 2. R6 on the dev month (~25 min)
Each system is run once with threshold 0, which stores every line's probability; the knob is then moved
offline in cell 3 (no extra GPU).
- **R6 control** — no AI: first option + safety rule + forced reviews. *Why:* does a safe no-AI system already pass?
- **R6 on the untrained 2B** — *why:* can a gate fix over-caution without any fine-tuning?
- **R6 on LoRA 0.8B, LoRA 2B, full 0.8B** — *why:* does the safety rule restore what fine-tuning broke?
""")
code(f"""
{GO}
for cond in ["clean", "stress"]:
    !python -m pratyaksha.harness.runner --system r6_control --split dev --condition {{cond}} --cost-mode gpu
    !python -m pratyaksha.harness.runner --system r6 --split dev --condition {{cond}} --cost-mode gpu --opt threshold=0 \\
        --opt model=Qwen/Qwen3.5-2B --opt batch=8
    !python -m pratyaksha.harness.runner --system r6 --split dev --condition {{cond}} --cost-mode gpu --opt threshold=0 \\
        --opt model=Qwen/Qwen3.5-0.8B --opt adapter=models/r5_lora_0.8b --opt batch=8
    !python -m pratyaksha.harness.runner --system r6 --split dev --condition {{cond}} --cost-mode gpu --opt threshold=0 \\
        --opt model=Qwen/Qwen3.5-2B --opt adapter=models/r5_lora_2b --opt batch=8
    !python -m pratyaksha.harness.runner --system r6 --split dev --condition {{cond}} --cost-mode gpu --opt threshold=0 \\
        --opt model=models/r5_full_0.8b --opt batch=8
""")

md("""
## 3. The threshold knob (no GPU)
**What:** for each model, move the threshold from 0 to 0.9999 and show: share handled alone, error rate on those,
misbooked rupees, and whether the business bar passes. Also **calibration**: when the model says 97%, is it right 97%
of the time? **Then** the recommended threshold = the lowest that passes the bar on both clean and messy dev lines.
**Why:** this is the live knob for the demo, and the threshold for the test month is chosen here, never on test.
""")
code(f"""
{GO}
for m in ["R6_Qwen3.5-2B", "R6_r5_lora_0.8b", "R6_r5_lora_2b", "R6_r5_full_0.8b"]:
    !python scripts/threshold_sweep.py --model {{m}}
""")

md("""
## 4. R7 — Gemini (cloud) with the same context
**Before running:** in Colab's left sidebar click the **key icon (Secrets)** → *Add new secret* → name
`GEMINI_API_KEY`, value = your key → switch **Notebook access** on.
*Why:* the key is never typed into the notebook, saved to Drive, or sent to me.

**Free-tier limits are small** (requests per day can be as low as ~20 and change often), so we run a small fixed slice
of 20 lines. Answers are cached: if the quota runs out midway, re-run tomorrow and it continues where it stopped.
Free-tier data may be used by Google to improve its products; we send only generated (fake) business data,
and the egress meter records every byte.
""")
code(f"""
{GO}
import os, json, urllib.request
from google.colab import userdata
os.environ["GEMINI_API_KEY"] = userdata.get("GEMINI_API_KEY")
req = urllib.request.Request("https://generativelanguage.googleapis.com/v1beta/openai/models",
                             headers={{"Authorization": "Bearer " + os.environ["GEMINI_API_KEY"]}})
names = [m["id"] for m in json.loads(urllib.request.urlopen(req).read())["data"]]
print([n for n in names if "flash" in n])
""")
md("**Pick the model:** copy one *flash* name from the list above into `GEMINI_MODEL` (keep the default if it is listed).")
code(f"""
{GO}
GEMINI_MODEL = "gemini-3.8-flash"     # change if not in the list above (drop any "models/" prefix)
!python -m pratyaksha.harness.runner --system r7 --split dev --condition clean --limit 20 --cost-mode api \\
    --opt model={{GEMINI_MODEL}} --opt rpm=8 --opt reranker=BAAI/bge-reranker-v2-m3
!python scripts/same_lines.py --ref R7_{{GEMINI_MODEL}} --split dev --condition clean
""")

md("""
## 5. The final test month (held out until now) — ~30 min
**What:** every main system once on month 6, clean and messy, with the thresholds chosen in cell 3.
**Why:** dev numbers were used to make decisions; only test numbers are unbiased. This table goes in the report.
""")
code(f"""
{GO}
import json, os
def thr(m):
    f = f"runs/threshold_{{m}}.json"
    t = json.load(open(f))["threshold"] if os.path.exists(f) else None
    return 0.999 if t is None else t      # no passing threshold on dev -> strictest gate, reported as such
T08, T2, TF = thr("R6_r5_lora_0.8b"), thr("R6_r5_lora_2b"), thr("R6_r5_full_0.8b")
print("thresholds from dev:", T08, T2, TF)
for cond in ["clean", "stress"]:
    !python -m pratyaksha.harness.runner --system rules --split test --condition {{cond}}
    !python -m pratyaksha.harness.runner --system r3_control --split test --condition {{cond}} --cost-mode gpu
    !python -m pratyaksha.harness.runner --system r6_control --split test --condition {{cond}} --cost-mode gpu
    !python -m pratyaksha.harness.runner --system r5 --split test --condition {{cond}} --cost-mode gpu \\
        --opt model=Qwen/Qwen3.5-0.8B --opt adapter=models/r5_lora_0.8b --opt batch=8
    !python -m pratyaksha.harness.runner --system r6 --split test --condition {{cond}} --cost-mode gpu --opt threshold={{T08}} \\
        --opt model=Qwen/Qwen3.5-0.8B --opt adapter=models/r5_lora_0.8b --opt batch=8
    !python -m pratyaksha.harness.runner --system r6 --split test --condition {{cond}} --cost-mode gpu --opt threshold={{T2}} \\
        --opt model=Qwen/Qwen3.5-2B --opt adapter=models/r5_lora_2b --opt batch=8
    !python -m pratyaksha.harness.runner --system r6 --split test --condition {{cond}} --cost-mode gpu --opt threshold={{TF}} \\
        --opt model=models/r5_full_0.8b --opt batch=8
""")
md("## 6. The test-month table\n**Why:** the headline result of the project.")
code(f"""
{GO}
!python scripts/compare.py --split test
!python scripts/error_analysis.py --model R6_r5_lora_0.8b --split test
!python scripts/error_analysis.py --model R6_r5_lora_2b --split test
""")
md("""
## 7. (Optional, if Gemini quota allows) R7 on 20 test-month lines
**Why:** the frontier reference on the same held-out month. Uses the same cache; costs up to 20 requests.
""")
code(f"""
{GO}
import os
from google.colab import userdata
os.environ["GEMINI_API_KEY"] = userdata.get("GEMINI_API_KEY")
!python -m pratyaksha.harness.runner --system r7 --split test --condition clean --limit 20 --cost-mode api \\
    --opt model={{GEMINI_MODEL}} --opt rpm=8 --opt reranker=BAAI/bge-reranker-v2-m3
!python scripts/same_lines.py --ref R7_{{GEMINI_MODEL}} --split test --condition clean
""")
md("## 8. Send back\n*File → Download → .ipynb*, then *Runtime → Disconnect and delete runtime* (stops using units).")

nb = {"cells": cells, "metadata": {"accelerator": "GPU", "colab": {"gpuType": "T4", "provenance": []},
      "kernelspec": {"name": "python3", "display_name": "Python 3"}, "language_info": {"name": "python"}},
      "nbformat": 4, "nbformat_minor": 0}
Path("notebooks/step5_R6_R7_test.ipynb").write_text(json.dumps(nb, indent=1))
print("ok", len(cells))
