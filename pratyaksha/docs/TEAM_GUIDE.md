# Team guide — what is here and how to see the final demo yourself

For: everyone in T-19. Read this first; it takes 10 minutes.

## 1. What we did, in five sentences

1. We built a pretend Indian business (60 customers, 1,361 invoices, 997 bank lines, 501 e-mails) whose right answers are known.
2. We built one examiner program that scores every system the same way, plus five pass rules a business would demand.
3. We climbed a ladder: rules with no AI → a small model alone → search → reranking → code that computes the options → fine-tuning → a safety gate in code → the Laya decision model → Claude Opus 5.5 as the frontier comparison.
4. We trained on months 1–4, chose settings on month 5, and ran month 6 once, as the final exam.
5. We ran the finished systems on a MacBook: same answers as Colab, measured speed and cost.

## 2. What is in this repository

| Path | What it is | Do you need to open it? |
|---|---|---|
| `README.md` | front page with the final results table | yes |
| `docs/TECHNICAL_OVERVIEW.md` | the whole project in two pages | yes, before the presentation |
| `docs/DEMO_GUIDE.md` | how to run and present the demo, with a 6-minute script | yes, if you present |
| `docs/FINDINGS_LOG.md` | every result of every step, with numbered findings | when someone asks "where is that number from?" |
| `docs/WHAT_DIDNT_WORK.md` | every failure, how it was found and fixed | for questions about problems |
| `docs/DECISIONS.md` | why each design choice was made | for "why did you…?" questions |
| `docs/ACCEPTANCE_BAR.md` | the five pass rules, frozen 23 Nov | |
| `docs/STEP*_GUIDE.md` | the step-by-step guides used while building | only to repeat a step |
| `pratyaksha/` | all the real code (Python) | only to read or change code |
| `notebooks/` | the Colab notebooks that trained and tested the models | to repeat training |
| `demo/` | the live demo web app | run it, see below |
| `runs/` | every recorded run (answers, scores, timings) | the demo reads it |
| `tests/` | 38 automatic checks | run them once |

Not in the repository (too large for GitHub): the trained models (`models/`, about 1.7 GB).
They are in the release download (see section 4). The data (`data/`) is not stored either: one command rebuilds it identically.

## 3. See the demo on your laptop (no models needed, 15 minutes)

This shows exactly what the final presentation shows, using the recorded answers.

1. Install Python 3.10 or newer (Mac: `brew install python@3.12`).
2. Get the code: `git clone https://github.com/arvindmenoncoder/IITB.git` and `cd IITB/pratyaksha`.
3. Set up:
   ```bash
   python3.12 -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   python -m pratyaksha.world.generate --out data/wwi_in      # rebuilds the data: "bank_entries": 997
   python -m pytest -q                                        # expect: 38 passed
   ```
4. Start the demo in replay mode (first time downloads the 2.3 GB reranker, so `--online`):
   ```bash
   python -m demo.server --replay --online
   ```
5. The browser opens at http://localhost:8765. Press `1`, then `R`. Then try `5` (the fraud-style e-mail) and the **Safety knob** and **Results** tabs.

Every card says *Recorded*: these are the real answers our systems gave on the test month.

## 4. Run it live, like the presenter (optional)

1. Download `models.zip` from the **Releases** page of https://github.com/arvindmenoncoder/IITB (release `pratyaksha-v1.0`) and unzip it into the `IITB/pratyaksha` folder, so that you have `models/laya_t1` and `models/r5_lora_0.8b`.
2. `python -m demo.server --online` (the first time; afterwards just `python -m demo.server`).
3. When the top right says *Ready*, the cards say *Live*: the models answer on your own laptop.

## 5. What each of us should do before 5 Dec

- [ ] Read `docs/TECHNICAL_OVERVIEW.md` and the results table in `README.md`.
- [ ] Run the demo once in replay mode (section 3).
- [ ] Read the "Questions faculty may ask" section of the easy-understanding report.
- [ ] Know the honest wording: we **matched** Opus (difference not significant), we did not "beat" it; the big proven gain is the engineering around the model.

## 6. If something does not work

| Problem | Fix |
|---|---|
| `python3.12: command not found` | install Python 3.12 (Mac: `brew install python@3.12`; Windows: python.org) |
| `No module named pratyaksha` | run the commands from inside the `IITB/pratyaksha` folder |
| SSL / certificate error while downloading | Mac python.org installer: run *Install Certificates.command* |
| Demo stuck on "Loading models…" | use `--replay`; live mode needs the models from Releases |
| Port in use | `python -m demo.server --replay --port 8766` |
