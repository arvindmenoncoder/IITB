# Step 3 in plain English (R3: the right information)

## Why this step exists
- Step 2: the AI could not add up invoices, so it listed all of them and its answers got cut off.
  - *Why it matters:* no amount of lookup helps if the AI cannot do the maths.

## What R3 gives the AI
- **Ready-made options**, worked out by code: "invoice 12 exactly", "invoices 12 + 15", "invoice 9 minus 1% TDS".
  - *Why:* the computer does the arithmetic perfectly; the AI only has to choose.
- **The payment e-mail** from the customer, if one arrived near that date.
  - *Why:* e-mails name the invoices and the payer when the bank line is cut off, and sometimes ask to change bank details.
- **An earlier identical credit**, if there was one in the last 2 days.
  - *Why:* so a duplicate posting can be spotted.
- The AI answers with just **one option id** ("M2").
  - *Why:* a short answer cannot be cut off, and it is faster.

## The fair test: the control
- Same options, no AI: always take the first option.
  - *Why:* the options alone already score 90% (clean) / 88% (messy). If the AI cannot beat that, the code did the work, not the AI.

## What to look at
- **Accuracy vs the control** — did the AI add anything?
- **Bank-detail changes to a person** — did the AI read the e-mail? The control cannot.
- **Error rate on automatic** — wrong answers it did not send to a person.
- `vs_control.py` output — the exact lines the AI fixed or broke.
