# Step 2 in plain English (R0, R1, R2)

## What we are testing
- Can a **small AI model** match bank lines to invoices better than the no-AI code (80.8% / 59.9%)?
  - *Why:* this is the first time AI enters the project. Everything later builds on this.

## The three runs
- **R0 — AI with no lookup**
  - The model sees only the bank line.
  - *Why:* to prove the model cannot know our customers or invoices on its own. Near 0% is expected.
- **R1 — AI + lookup**
  - Search finds the 5 likeliest customers; the model gets them plus their unpaid invoices on that date.
  - *Why:* the model can now see the books. Never future invoices, so results are honest.
- **R2 — AI + lookup + reorder**
  - Search 10, a second model re-orders them, keep the best 3.
  - *Why:* fewer wrong candidates should mean fewer wrong answers and a shorter, faster prompt.

## What to look at in each scorecard
- **Accuracy** — right customer, category and exact invoices.
- **Right party among retrieved** — did the search even find the right customer?
  - *Why:* if search missed it, the model never had a chance. That is a search problem, not a model problem.
- **Error rate on automatic** — wrong answers the AI did *not* send to a person.
  - *Why:* this is the dangerous number for a business. The rules code had 0%.
- **Tokens in** — prompt size. *Why:* bigger prompt = slower and costlier.
- **Parse errors** — the model did not reply in readable JSON. *Why:* small models often break format; fine-tuning (R5) may fix this.

## What we expect (and why it is fine if AI loses)
- The model must add amounts itself in R1/R2. Small models are bad at arithmetic.
  - *Why it matters:* our design says the AI should never do arithmetic; R3 adds computed amount matches.
- If R1/R2 lose to the rules code, **that is a result**: it tells developers that lookup alone is not enough.
