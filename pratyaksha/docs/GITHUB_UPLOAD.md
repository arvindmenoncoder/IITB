# Uploading the project to GitHub (for Arvind)

## What goes where

| Item | Where it goes | Size |
|---|---|---|
| Code, docs, notebooks, tests, demo (`pratyaksha_final.zip`) | the repository | < 1 MB |
| `runs/` (every recorded run, from your Mac) | the repository: the demo and every number in the report come from it | about 20–40 MB |
| Executed notebooks with outputs (from Google Drive → Colab Notebooks) | the repository, in `notebooks/executed/` | a few MB |
| The two reports and the deck, as PDF (download from each artifact) | the repository, in `docs/report/` | a few MB |
| Trained models (`models/laya_t1`, `models/r5_lora_0.8b`, `models/r5_lora_2b`) | **GitHub Release** attachment `models.zip` (git refuses files over 100 MB) | about 1.7 GB |

**Never upload:** `.venv/`, `data/`, `models/` inside git, any `.env` file, your Anthropic API key,
`runs/opus_cache.jsonl`. The `.gitignore` already keeps these out; check with `git status` before committing.

## Steps on the Mac

1. Put the final code in your project folder (keeps your `models`, `runs` and `.venv`):
   ```bash
   cd ~/Documents/Arvind/IIT/Project/AIML/mac
   unzip -o ~/Downloads/pratyaksha_final.zip
   cd pratyaksha
   mkdir -p notebooks/executed docs/report
   ```
   Copy the executed `.ipynb` files from Google Drive into `notebooks/executed/`, and the report and deck PDFs into `docs/report/`.
2. Make the models zip for the Release:
   ```bash
   zip -r ../models.zip models/laya_t1 models/r5_lora_0.8b models/r5_lora_2b
   ```
3. Create the repository: github.com → **New repository** → name `pratyaksha` → Private (add teammates later under Settings → Collaborators) → **do not** add a README → Create.
4. Upload with **GitHub Desktop** (easiest): File → Add Local Repository → choose the `pratyaksha` folder → "create a repository here" → check the file list (no `.venv`, `data`, `models`) → Commit to main → Publish repository.
   Or in Terminal:
   ```bash
   git init && git add . && git status          # check: no .venv, data, models
   git commit -m "PRATYAKSHA final: code, results, docs, demo"
   git branch -M main
   git remote add origin https://github.com/<your-username>/pratyaksha.git
   git push -u origin main                       # password = a GitHub personal access token
   ```
5. Attach the models: repository page → **Releases** → Draft a new release → tag `v1.0` → title "Final demo models" → attach `models.zip` → Publish.
6. Check from a teammate's view: open the repository page, read `README.md`, and follow `docs/TEAM_GUIDE.md` section 3.
