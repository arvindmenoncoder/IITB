# Step 5 in plain English (R6: who acts? Laya. Opus. Then the final exam.)

## R6 — the AI answers, the code decides who acts
- **Safety rule:** an e-mail asking to change bank details → always a person. *Why:* training made the AI miss these (full fine-tune: 0 of 5).
- **Risky types** (duplicate, unknown payer, short payment) → always a person.
- **Confidence gate:** act alone only if the model was at least X% sure. *Why:* its written "please review" flag was unreliable; its real probability can be measured.
- **The knob:** X can be moved. Higher X = safer, fewer lines done alone.

## The fair test
- **R6 control:** no AI, options + safety rule. It already passes the business rules. *Why it matters:* the AI must show what it adds on top.

## Laya — the System-1 model from the mid-sem plan
- A small (421M) model that does not write text: it reads the evidence and gives a probability for each option in one step.
- *Why:* if a non-generative model can choose as well as a generative one, it is faster and can never "ramble" or produce unreadable answers.
- It is near chance before training, so we fine-tune it on months 1–4, with the options shuffled so it cannot just learn "pick the first".

## R7 — Claude Opus 5.5, the frontier model
- Same evidence, every line. *Why:* shows the best case, its price, and how much business data leaves the building.

## The final exam (test month)
- Rules frozen on 23 Nov; thresholds picked on month 5; then every system runs once on month 6.
