# Setup on the MacBook Pro (M1 Pro, 16 GB)

Run each block in Terminal. Each step ends with a **Done when** check.

## 1. Python environment

```bash
cd ~/Projects            # or wherever you keep code
unzip ~/Downloads/pratyaksha_step1.zip
cd pratyaksha
python3 --version        # need 3.10 or newer
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
```

**Done when:** `pip list | grep rank` shows `rank-bm25`.

## 2. Build the world and run the tests

```bash
python -m pratyaksha.world.generate --out data/wwi_in
python -m pytest -q
```

**Done when:** you see `{"customers": 60, ..., "bank_entries": 997, ...}` and `9 passed`.
(The same seed gives the same world on every machine; the counts must match.)

## 3. Run the no-AI baseline

```bash
python -m pratyaksha.harness.runner --system rules --split dev --condition clean
python -m pratyaksha.harness.runner --system rules --split dev --condition stress
cat runs/index.csv
```

**Done when:** accuracy is 80.8% (clean) and 59.9% (stress). Send me the
`runs/index.csv` output.

## 4. Git (local repo now, GitHub when you're ready)

```bash
git init -b main && git add -A && git commit -m "Step 1: WWI-IN world, harness, rules baseline"
# create an empty repo on github.com (e.g. pratyaksha-t19), then:
# git remote add origin https://github.com/<you>/pratyaksha-t19.git && git push -u origin main
```

## 5. Get ready for Step 2 (models) — can run overnight

```bash
pip install -U mlx-lm "huggingface_hub[cli]"
# small models first (~0.6 GB and ~1.4 GB)
huggingface-cli download mlx-community/Qwen3.5-0.8B-MLX-4bit
huggingface-cli download mlx-community/Qwen3.5-2B-MLX-4bit   # if "not found", search huggingface.co/mlx-community for "Qwen3.5-2B" 4bit
# smoke test
mlx_lm.generate --model mlx-community/Qwen3.5-0.8B-MLX-4bit --prompt "Reply with OK" --max-tokens 5
```

**Done when:** the last command prints a reply. If it fails with a model-type
error (these conversions are made with mlx-vlm), copy the error to me; the
fallback is `pip install mlx-vlm` and `mlx_vlm.server`, which the harness can use
the same way.

## 6. Two things only you can do (5 minutes each)

1. **BenchRec:** on kaggle.com search "BenchRec" (the ICAIF 2023 cash-reconciliation
   competition data). Download it and tell me the file names and sizes.
2. **Gemini API key** (for R7): aistudio.google.com → Get API key. Keep it in
   `~/.pratyaksha.env` as `GEMINI_API_KEY=...`, never in the repo.
