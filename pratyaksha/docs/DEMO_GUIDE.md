# PRATYAKSHA demo — how to run and present it

## Start it (MacBook, Terminal)

```bash
cd ~/Documents/Arvind/IIT/Project/AIML/mac/pratyaksha
source .venv/bin/activate
python -m demo.server
```
- The browser opens at **http://localhost:8765**. Press **Ctrl+Cmd+F** for full screen.
- Top right shows **Loading models…** (about 20–40 s), then **Ready · Apple GPU · offline**.
  Start presenting only after it says Ready: every model has then answered one warm-up line.
- No internet is needed. Models load from the Mac; Opus is replayed from its recorded test run.

**Backup (if anything goes wrong in class):**
```bash
python -m demo.server --replay
```
Loads no models; every answer comes from the recorded Mac runs (same answers, same timings), and each card says *Recorded*.

## Keys

| Key | Does |
|---|---|
| 1–9 | pick a prepared bank line (in the order shown on screen) |
| R or Enter | Reconcile (run all four systems) |
| A | show / hide the correct answer |
| M | switch clean / messy narration |

## The three views

| View | What it shows | Why it matters |
|---|---|---|
| **Live** | one bank line answered side by side by Rules, Laya, the fine-tuned Qwen 0.8B and Claude Opus 5.5; the e-mails found; the menu the code built (with who chose what); a step-by-step time bar; the three safety checks; the data-sent-out strip | the whole pipeline, in one picture |
| **Safety knob** | slide the confidence threshold; see lines handled alone, errors, misbooked rupees, bank changes and the business bar change (dev month) | why the threshold is 0 and safety sits in code |
| **Results** | the final-exam numbers with speed and cost from this Mac | the headline claim, honestly worded |

## Suggested 6-minute flow

1. **Exact payment → R.** "Same evidence to four systems. Three answered on this Mac with 0 bytes sent; Opus needed about 1.6 KB of business data sent to the cloud and took about 2 seconds."
2. **Click the Qwen card.** Show the time bar: search and menu building are milliseconds; the model is most of the time. "The code did the maths; the model only picked M1."
3. **Two bills, one payment → R.** Point at the menu: M1 is two invoices adding up exactly. "Small models cannot add; our code does."
4. **Bank-detail change → R.** The red e-mail. Laya, Qwen and Opus all say *Sent to a person*; Rules (which read no e-mails) may book it. Open the trace: the failed check is the guardrail. "Safety is a rule in code, not a habit the model learned. Training actually weakened that habit."
5. **Messy narration** (switches to messy) **→ R, then A.** Rules get it wrong; the fine-tuned Qwen gets it right from the same evidence.
6. **Where Opus slipped → R, then A** (if shown). The right answer was on the menu; the small fine-tuned model picked it, Opus did not. "On the whole month this difference is not significant, so we say *matched*, not *beat*."
7. **The honest limit → R, then A.** Nobody gets it: the right answer was never on the menu. "That is our next improvement: search, not a bigger model."
8. **Safety knob.** Choose **Untrained 2B** and drag the slider right: automation falls below 50% and the bar fails. Then choose **Qwen 0.8B**: the line is almost flat. "After training the model is almost always sure, so the threshold changes little; we chose 0 on the practice month and let the code rules do the safety."
9. **Results.** "Matched Opus on accuracy, not significantly different. On this ₹1.75 lakh Mac: 3–9× faster, 70–220× cheaper, nothing leaves the machine."

## Honesty built in

- Opus is **replayed** from its recorded test-month answer at its real recorded speed, and labelled *Recorded run*.
- If a local model fails to load, its card switches to its recorded Mac answer and says *Recorded on Mac*.
- The correct answer stays hidden until you press **A**, so the audience sees the systems decide first.
- The prepared lines are picked automatically from the test month to show each case (a case with no example is left out); *Random line* picks any test line.

## If something looks wrong

| Problem | Fix |
|---|---|
| Stuck on "Loading models…" for more than 2 minutes | Ctrl+C in Terminal, then `python -m demo.server --replay` |
| "Address already in use" | another copy is running: close it, or `python -m demo.server --port 8766` |
| A card says "No answer recorded for this line" | only for *Random line* when a recorded run is missing; pick a prepared line |
| Browser did not open | open http://localhost:8765 yourself |
