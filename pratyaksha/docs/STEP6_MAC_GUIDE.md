# Step 6 — the same systems on your MacBook (owned-machine runs)

**Goal:** measure speed and cost on a computer a business could own, one bank line at a time.
**Nothing is tuned or changed:** same models, same rules, thresholds 0.0, same test month. The Mac answers
should match Colab; any line that differs is listed by the script, not hidden.

Systems run: rules (no AI), R6 control (no AI), R6 Laya, R6 LoRA 0.8B (optionally R6 LoRA 2B).
Opus is not re-run: its latency is a network call, already measured.

## A. In Colab: pack the trained models and the Colab runs (one cell, CPU runtime is enough)

```python
from google.colab import drive; drive.mount("/content/drive")
%cd "/content/drive/MyDrive/Colab Notebooks/pratyaksha"
!zip -r -q ../pratyaksha_for_mac.zip models/r5_lora_0.8b models/r5_lora_2b models/laya_t1 runs -x "runs/opus_cache.jsonl"
!ls -lh ../pratyaksha_for_mac.zip
```
- **Why:** the Mac needs the trained add-ons (LoRA), the trained Laya, and the Colab runs to compare against.
- The full fine-tuned model (3.4 GB) is left out: it is not part of the Mac runs.
- Then download `pratyaksha_for_mac.zip` from Google Drive (Colab Notebooks folder) to your Mac's Downloads.

## B. On the Mac: set up (Terminal)

```bash
python3 --version                 # must be 3.10 or newer
```
If it shows 3.9 or older: `brew install python@3.12`, then use `python3.12` instead of `python3` below.

```bash
mkdir -p ~/Projects && cd ~/Projects
unzip -o ~/Downloads/pratyaksha_step6.zip          # the code (from Claude)
cd pratyaksha
unzip -o ~/Downloads/pratyaksha_for_mac.zip        # models/ and runs/ from Colab
python3 -m venv .venv && source .venv/bin/activate
pip install -U pip && pip install -r requirements-mac.txt
python -m pratyaksha.world.generate --out data/wwi_in
python -m pytest -q
```
**Done when:** the world prints `"bank_entries": 997` and the tests say `38 passed`.
- **Why the world again:** the same seed (7) rebuilds exactly the same business on any machine.

## C. Smoke test: 5 lines per system (first run downloads about 4–5 GB of models)

```bash
SMOKE=1 HARDWARE_INR=<price of your Mac in rupees> bash scripts/mac_step6.sh
```
- **Why first:** checks that every model loads on the Mac's GPU before the long run.
- You may see `[device] cuda not available here; using mps` — that is expected (mps = the Mac's own GPU).
- **Send me the output if anything fails.**

## D. (Optional, 2 minutes) Measure the Mac's power use

While a model is running (during step C or E), open a **second** Terminal window:
```bash
sudo powermetrics --samplers cpu_power,gpu_power -i 1000 -n 10 | grep "Combined Power"
```
Note a typical value (e.g. `Combined Power (CPU + GPU + ANE): 18000 mW` = 18 W).
- **Why:** the electricity cost per 1,000 lines uses this number. If you skip it, 35 W is assumed and stated.

## E. The full run (about 20–40 minutes; plug in the charger, close other apps)

```bash
caffeinate -i env HARDWARE_INR=<price> OWNED_WATTS=<watts, or leave out> bash scripts/mac_step6.sh 2>&1 | tee mac_step6_log.txt
```
- `caffeinate` keeps the Mac awake. `tee` saves everything to `mac_step6_log.txt`.
- Re-running is safe: finished runs are skipped.
- Optional: add `WITH_2B=1` to include the 2B model.

## F. Send me

1. `mac_step6_log.txt`
2. `runs/mac_vs_colab_test.json`
3. Your Mac's model and memory (Apple menu → About This Mac), its price, and the watts you measured.
