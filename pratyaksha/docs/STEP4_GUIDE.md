# Step 4 in plain English (R4: what's left? R5: teach the model)

## R4 — look at the mistakes first
- Every line goes into one bucket: right and done alone / right but sent to a person / wrong though the right option was there / wrong because our options missed it.
  - *Why:* training can only fix the first kinds. If most errors were "options missed it", training would be wasted money.
- Step 3 result: the 2B model was right ~90% of the time but asked a person ~75% of the time; the 0.8B model often picked the wrong option. Both are teachable, so we train.

## R5 — fine-tuning
- **Teacher:** months 1–4 of the business's own past bank lines, with the right answers (1,270 examples, clean and messy).
  - *Why:* a real business would train on its own history. Month 5 (our test) is never shown.
- **What it learns:** pick the right option, and only ask a person when it should.
- **LoRA:** the model is frozen; small add-on layers learn (a few % of the weights, a file of tens of MB).
  - *Why:* cheap, fast, and one base model can carry several add-ons.
- **Full fine-tuning (0.8B only, optional):** every weight changes.
  - *Why:* the mid-sem plan compares the two.

## What to look at
- **Accuracy and "handled by itself"** — did it stop over-asking without becoming wrong?
- **Error rate on automatic** — must stay near 0%; this is the safety number.
- **Training minutes** — the one-time cost.
- **Loss** — should fall; if it does not, the model did not learn.
