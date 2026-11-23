# PRATYAKSHA — what each AI technique buys a small business

Team T-19 · IIT Bombay ePGD AI & DS · AI/ML in Practice capstone · final demo 5 Dec 2026

**Result in one line:** on bank reconciliation for an Indian MSME, small models fine-tuned on the
business's own history and running on a ₹1.75 lakh MacBook **matched Claude Opus 5.5 on accuracy**
(not significantly different), were **about 3–9× faster and 70–220× cheaper per line**, and
**sent no data off the machine**. The large, proven gain came from engineering the context and the
safety rules around the model.

| Start here | For |
|---|---|
| [`docs/TEAM_GUIDE.md`](docs/TEAM_GUIDE.md) | teammates: what is in this repo and how to see the demo yourself |
| [`docs/TECHNICAL_OVERVIEW.md`](docs/TECHNICAL_OVERVIEW.md) | the whole project in two pages: data, code, models, results |
| [`docs/DEMO_GUIDE.md`](docs/DEMO_GUIDE.md) | running and presenting the live demo |
| [`docs/FINDINGS_LOG.md`](docs/FINDINGS_LOG.md) | every number from every run, step by step |
| [`docs/WHAT_DIDNT_WORK.md`](docs/WHAT_DIDNT_WORK.md) | every failure and fix, dated |
| [`docs/DECISIONS.md`](docs/DECISIONS.md) | every design decision and its reason |

## Final results — test month (held out, run once), 185 bank lines per condition

| System | Right, clean | Right, messy | Wrong, unchecked | Time per line* | ₹ per 1,000 lines* | Data sent out | Business bar |
|---|---|---|---|---|---|---|---|
| Rules (no AI) | 74.6% | 55.1% | 0% | 0.04–0.06 s | 0.3–0.5 | 0 | Fail |
| Code only (R6 control, no AI) | 89.7% | 88.1% | 0% | 0.11 s | 0.9 | 0 | Pass |
| Qwen3.5 0.8B, fine-tuned (LoRA) | **91.4%** | **89.2%** | 0% | 0.86 s | 7.0 | 0 | Pass |
| Laya (421M decision model) | **91.4%** | 88.6% | 0% | **0.28 s** | **2.3** | 0 | Pass |
| Claude Opus 5.5 (API) | 89.7% | 87.6% | 0% | 2.3–2.4 s | 479–501 | ≈ 1.6 KB per line | Pass |

\* Local systems measured on a MacBook Pro 2021 (Apple M1 Pro, 16 GB), one line at a time; their
answers matched the Colab runs on all 1,480 lines. Opus measured through the Anthropic API.
Best possible on this month (right answer among the computed options): 92.4% clean, 90.3% messy.

## How it works

```
bank line ──► search customers (BM25 on 3-letter pieces) ──► rerank (bge-reranker-v2-m3)
          ──► code computes the match options (exact / two-three bills / TDS / short / duplicate / none)
          ──► model picks ONE option id (fine-tuned Qwen 0.8B, Laya, or Opus)
          ──► safety gate in code: bank-change e-mail? forced-review case? confidence?
          ──► booked automatically, or sent to a person
```

## Run it

```bash
git clone https://github.com/arvindmenoncoder/IITB.git && cd IITB/pratyaksha
python -m pip install -r requirements.txt          # Mac, Windows or Linux
python -m pratyaksha.world.generate --out data/wwi_in
python -m pytest -q                                 # 38 tests
python -m demo.server --replay --online             # the demo, from the recorded results
```
Trained models are not in git (too large): download `models.zip` from this repository's Releases (`pratyaksha-v1.0`) for live mode; see `docs/TEAM_GUIDE.md`.

## Repository map

| Folder | What |
|---|---|
| `pratyaksha/world` | the data generator (WWI-IN, seed 7) and ledger with the no-look-ahead rule |
| `pratyaksha/harness` | the one shared evaluator: scoring, costs, acceptance bar, runner |
| `pratyaksha/retrieval` | BM25 party search and the reranker |
| `pratyaksha/systems` | every rung: rules, R0–R3, R5, R6 gate, Laya, R7 Opus |
| `pratyaksha/llm` | model backends (Hugging Face on CUDA/Apple GPU, Anthropic, OpenAI-compatible) |
| `pratyaksha/finetune` | training data builders and LoRA / full fine-tuning |
| `scripts` | analysis: compare, error analysis, threshold sweep, significance, Mac runs |
| `notebooks` | the Colab notebooks for Steps 2–5 |
| `demo` | the live demo web app |
| `runs` | every recorded run: predictions, summary, scorecard, config |
| `tests` | 38 tests (data consistency, harness, systems) |

Models used: Qwen3.5-0.8B / 2B / 4B (Alibaba Qwen team, Apache-2.0), BAAI bge-reranker-v2-m3 (Apache-2.0),
Laya typed-decisions (convaiinnovations, Apache-2.0), Claude Opus 5.5 (Anthropic API, comparison only).
