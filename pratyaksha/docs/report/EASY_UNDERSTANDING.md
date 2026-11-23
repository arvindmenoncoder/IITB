# PRATYAKSHA — Project Report, Easy Understanding

Nov 23, 2026 · @Arvind

This is the plain-English companion to the main project report. It explains every idea, number and decision with examples, so you can explain the whole project yourself.

## The whole project in one minute

We built a computer helper that reads a small Indian business's bank statement and works out who paid and for which bills. We then tested which AI tricks actually make it better.

- **The job:** a bank line says "₹1,18,000 received from SHARMA TRD". Someone must work out that this is Sharma Traders paying bill INV-0412.
- **What we did:** we started with no AI. Then we added one AI technique at a time and measured each one the same way. Like a ladder, each step is one rung higher.
- **What we found:**
  1. Smart code that prepares the information did most of the work. It took accuracy from about 75% to about 90%.
  2. A small AI model, trained on this business's old records, added a little more (about 91%). It runs on an ordinary computer.
  3. The most powerful paid AI (Claude Opus 5.5) did not do better than our small trained model. It was slower, cost money per line, and needed the data sent over the internet.
  4. Safety rules written in code (for example, "always show a person any e-mail asking to change bank details") kept wrong automatic bookings at 0.
- **The one-line message:** a small business does not need to send its private bank data to a big cloud AI. A small model on its own computer, plus good engineering, does the job just as well.

## The business problem

Every day, a small business must match the money in its bank account to the bills (invoices) it sent. This is called **bank reconciliation**. It is slow, boring and easy to get wrong.

*All names and amounts in this document's examples are made up to explain the idea.*

**Example.** The business sent these bills:

| Bill | Customer | Amount |
| --- | --- | --- |
| INV-0412 | Sharma Traders | ₹1,18,000 |
| INV-0418 | Sharma Traders | ₹59,000 |
| INV-0420 | Gupta Steel | ₹2,36,000 |

Then the bank statement shows:

| Date | Narration (bank's description) | Credit |
| --- | --- | --- |
| 12 Sep | NEFT-SHARMA TRD-INV412 | ₹1,18,000 |
| 13 Sep | UPI/GUPTASTL/PAYMT | ₹2,32,000 |
| 14 Sep | NEFT-SHARMA TRD | ₹1,77,000 |

What a person must work out:

- **12 Sep:** easy. Sharma Traders paid bill INV-0412 exactly.
- **13 Sep:** Gupta Steel paid ₹4,000 less than the bill. The bill is ₹2,00,000 plus 18% GST. TDS (tax the customer keeps back) at 2% of ₹2,00,000 is exactly ₹4,000, so this is probably a TDS deduction, not a short payment.
- **14 Sep:** ₹1,77,000 = ₹1,18,000 + ₹59,000. Sharma paid two bills in one go (a "clubbed" payment). Nobody wrote the bill numbers.

**Why this is hard for a computer:**

- Bank narrations are short, cut off, misspelt, and use nicknames ("SHARMA TRD" instead of "Sharma Traders").
- Amounts often need adding or subtracting to make sense.
- Some lines are dangerous. For example, an e-mail saying "please send future payments to our new bank account" is a common fraud trick. A person must always see it.

**Why we care about where the AI runs:** these bank lines and e-mails contain private business data. A cloud AI (like Opus) means sending that data over the internet to another company. A small model on the business's own computer sends nothing.

## Words you must know

These are all the words used in the project, each with a simple meaning and an example. Come back to this table whenever a word is unclear.

**Business words**

| Word | Simple meaning | Example |
| --- | --- | --- |
| MSME | Micro, Small and Medium Enterprise: a small Indian business | a steel trader with 60 customers |
| Invoice / bill | A request for payment sent to a customer | INV-0412 for ₹1,18,000 |
| GST | Goods and Services Tax, added on top of the price | ₹1,00,000 + 18% GST = ₹1,18,000 |
| TDS | Tax Deducted at Source: the customer keeps back a small % of the price (before GST) and pays it to the government | 2% of ₹1,00,000 = ₹2,000 kept back, so ₹1,16,000 arrives |
| Narration | The short text the bank writes next to a payment | "NEFT-SHARMA TRD-INV412" |
| Remittance e-mail | An e-mail from the customer saying what they paid for | "Paid INV-0412 and INV-0418 today" |
| Full payment | One bill paid exactly | ₹1,18,000 for INV-0412 |
| Clubbed payment | Several bills paid in one amount | ₹1,77,000 = two bills |
| Short payment | Paid less than the bill, rest still owed | ₹1,10,000 paid against ₹1,18,000 |
| Duplicate credit | The bank posted the same payment twice by mistake | the same ₹59,000 appears two days in a row |
| Unknown party | Money from someone not in the customer list | a new customer's first payment |
| Bank-detail change | A request to send money to a new account; a common fraud trick | "Our bank changed, use account …" |
| Misbooked rupees | Money booked to the wrong bill without anyone checking | ₹590 on the test month for one system |

**AI and computer words**

| Word | Simple meaning | Example |
| --- | --- | --- |
| Model / LLM | A program trained on lots of text that reads text and writes an answer | Qwen3.5-2B |
| Parameters (0.8B, 2B) | The model's size: how many numbers it learned. B = billion | 0.8B = 800 million numbers |
| Token | A small piece of a word; models read and write in tokens | "reconciliation" ≈ 3–4 tokens |
| Prompt | The text we give the model to read | the bank line plus the options |
| Retrieval | Finding the right records to show the model, like a search engine | find "Sharma Traders" from "SHARMA TRD" |
| BM25 on 3-letter pieces | A search that breaks names into 3-letter chunks so typos still match | "SHA", "HAR", "ARM" match both "Sharma" and "Shrma" |
| Reranker | A second, smarter search that re-orders the first search's top results | takes the top 10 and keeps the best 3 |
| Context engineering | Preparing exactly the right information for the model, in the right shape | code works out "₹1,77,000 = INV-0412 + INV-0418" and shows it as option M1 |
| Option (M1, M2, D, U) | The ready-made answers we offer the model. M = match, D = duplicate, U = none of these | the model replies "M1" |
| Fine-tuning | Teaching an existing model our task with our own past examples | showing it 1,270 solved bank lines from months 1–4 |
| LoRA | Cheap fine-tuning: train a small add-on, keep the big model frozen | trains 1.25% of the 0.8B model |
| Full fine-tuning | Train every number in the model | trains 100%; needs a 3.4 GB copy |
| Epoch | One pass through all the training examples | 2 epochs = saw each example twice |
| Loss | How wrong the model is during training; lower is better | fell from 0.95 to 0.006 |
| Probability / confidence | How sure the model is of its answer, from 0 to 1 | 0.999 = almost certain |
| Threshold | The minimum confidence needed to act without a person | 0.9 means "below 90% sure, ask a person" |
| Calibration / ECE | Whether "90% sure" really means right 90% of the time. ECE measures the gap; lower is better | ECE 0.05 = off by about 5 points on average |
| Guardrail | A fixed safety rule written in code | any bank-change e-mail → a person |
| Gate | The final check that decides: book automatically, or send to a person | guardrail + forced reviews + threshold |
| Laya | A small (421M) decision model that picks from choices instead of writing text | picks "M1" and "no person needed" |
| Claude Opus 5.5 | Anthropic's most powerful public model, used over the internet; you pay per token | $4 per million tokens read, $20 per million written |
| API | The way a program talks to an online service | our code sends the prompt to Anthropic and gets an answer back |
| Colab / T4 | Google's online notebook with a rented graphics card (GPU) called T4 | where we trained the models |
| Latency, p50 / p95 | Time per line. p50 = a typical line, p95 = a slow line (95% are faster) | p50 0.34 s |
| Egress | Data leaving the computer | Opus: about 1.6 KB per line; local: 0 |
| Train / dev / test split | Months for learning, for tuning, and for the final exam | months 1–4 / 5 / 6 |
| Look-ahead | Cheating by using information from the future | seeing a bill created after the payment date |
| p-value | The chance a difference is just luck. Below 0.05 = probably real | p = 0.25: could easily be luck |
| McNemar test | A test comparing two systems on the same lines, counting only the lines where they disagree | 3 lines one wins, 0 the other wins |
| Bootstrap interval | Re-sample the lines many times to see the range the true difference could be in | +0.0 to +3.8 points |

## Our practice business (WWI-IN)

We could not use a real company's bank data, because it is private and nobody would have the "right answers" written down. So we wrote a program that **creates a pretend Indian business**, complete with customers, bills, bank lines and e-mails, and knows the right answer for every line.

- **Name:** WWI-IN, based on "Wide World Importers", a well-known Microsoft practice company, made Indian.
- **Size:** 60 customers, 8 suppliers, 1,361 bills, 997 bank lines and 501 e-mails over 6 months.
- **Seed 7:** the program uses a fixed random number (7), so it creates exactly the same business every time, on any computer.
  - Why: anyone can re-run our work and get the same numbers. We checked this: Colab gave the same results as our workspace.
- **Gold answers:** for every bank line, the program records the true customer, the bills, the category, and whether a person should check it. We call these the "gold" answers.
- **9 kinds of bank line:** full, clubbed, TDS, short, duplicate, unknown payer, bank charges, interest and supplier payments (see the glossary).

**Two versions of every bank line.** The same payment is written two ways:

| Condition | Example narration | Why |
| --- | --- | --- |
| Clean | NEFT-SHARMA TRADERS PVT LTD-INV0412 | an easy, tidy bank |
| Stress (messy) | NEFT-SHRMA TRD- | real banks cut text to 28–40 characters, use nicknames, make typos and drop bill numbers |

**Three time periods, like school:**

| Months | Name | Used for | School example |
| --- | --- | --- | --- |
| 1–4 | Train | teaching the models | the textbook |
| 5 | Dev (177 lines per condition) | trying ideas and choosing settings | practice tests |
| 6 | Test (185 lines per condition) | one final measurement, never looked at before | the final board exam |

- **Why split by time:** this is how a real business would use it, learning from the past and working on the next month.
- **No look-ahead rule:** when judging a payment made on 12 Sep, the system can only see bills that existed and were unpaid on 12 Sep. Otherwise it would be cheating.

## How we grade every system

Every system, from simple rules to Opus, is marked by the same examiner program (the "harness"), on the same lines, with the same rules. That is what makes the comparison fair.

**What the examiner measures, with examples:**

| Measure | Plain meaning | Example |
| --- | --- | --- |
| Strict accuracy | Customer, category AND the exact set of bills must all be right | right customer but one bill missing = wrong |
| Handled automatically | Lines the system booked without a person | 140 of 185 lines = 75.7% |
| Error rate on automatic | Of the lines booked alone, how many were wrong | 1 wrong out of 136 = 0.74% |
| Misbooked rupees | Total ₹ of those wrong automatic bookings | ₹590 |
| Latency p50 / p95 | Time per line, typical and slow | 0.34 s / 0.39 s |
| ₹ per 1,000 lines | Running cost: GPU rent or API fees | Laya about ₹1.4, Opus ₹479 |
| Data leaving the machine | Bytes sent over the internet | Opus about 300 KB per 185 lines; local 0 |
| Restricted-field leaks | Did account numbers appear in the answer? | 0 in every run |
| Party recall / option recall | Was the right customer, or the right answer, even shown to the model? | 93.8% on test |

**Important idea: sending a line to a person is not counted as an error.** A line marked "please check" is safe. The person will fix it. The dangerous mistakes are the wrong lines nobody looks at.

**The pass rules (the "acceptance bar"), fixed on 23 Nov before the final exam.** A system passes only if all five are true:

| # | Rule | Why, in plain words |
| --- | --- | --- |
| 1 | At most 1% of automatic bookings are wrong | wrong bookings nobody checks are the real danger |
| 2 | At most ₹1,000 booked wrongly | the cash total in the books must stay trustworthy |
| 3 | Every unexplained line goes to a person | nothing strange is booked quietly |
| 4 | Every bank-detail change goes to a person | the fraud trick must never be automated |
| 5 | At least 50% of lines handled automatically | otherwise "send everything to a person" would pass, and that saves no work |

**Example.** A system books 140 of 185 lines alone, 0 of them wrong, and sends all 7 bank-change lines to a person. Rules 1–5 all hold, so it passes. If it had missed one bank-change line, it would fail, even with 99% accuracy.

## Journey of one bank line

This is what happens to every bank line in the final system. Code does the searching, the maths and the safety checks; the model only makes one choice.

*(Diagram in the online report: bank line → search → code builds the menu → model picks one option → safety gate → booked automatically or sent to a person.)*

The highlighted box (step 4) is the only place the AI model is used. Everything else is ordinary code, which is why the no-AI control already scores about 90%.

## The ladder, rung by rung

We changed one thing at a time and measured each change. Think of cooking: if you add salt, chilli and lemon all at once, you never learn which one made it tasty.

1. **R-rules (no AI).** Plain code: find the customer by name, then look for a bill with exactly that amount.
   - Why: the honest starting point. If AI cannot beat this, the AI is not worth it.
2. **R0: small model, bank line only.** Give Qwen 0.8B just "NEFT-SHARMA TRD ₹1,77,000" and ask for the answer.
   - Why: "fail first". It shows what a model does knowing nothing about the business. It just guesses.
3. **R1: + retrieval.** Search finds the 5 most likely customers and their unpaid bills and puts them in the prompt.
   - Why: the model cannot know Sharma's bills unless we show them.
4. **R2: + reranking.** Find 10 customers, let a smarter reranker pick the best 3.
   - Why: a shorter, cleaner prompt.
5. **R3: + context engineering.** Code does all the maths and offers ready-made answers. For example: M1 = "INV-0412 + INV-0418 = ₹1,77,000", M2 = "INV-0418 only, short by ₹1,18,000", U = "none of these". It also adds the customer's e-mails. The model only replies "M1".
   - Why: small models are bad at maths but fine at choosing.
   - **R3 control:** the same options, but with no model; it always picks M1. This shows how much the model really adds beyond the code.
6. **R4: error analysis.** We sorted every mistake into types before deciding what to do next.
   - Why: you fix what you understand, not what you guess.
7. **R5: fine-tuning.** We taught the small models with 1,270 solved lines from months 1–4.
   - Why: the R3 models were either too careful or picked wrong; both are habits training can fix.
8. **R6: the safety gate.** Fixed rules in code decide whether a line goes to a person: the bank-change guardrail, forced checks for duplicates, unknown payers and short payments, and a confidence threshold.
   - Why: safety must not depend on the model remembering to be careful.
9. **Laya.** A tiny decision model that only picks an option (no writing), behind the same R6 gate.
   - Why: if you only need to choose, you do not need a model that writes, and choosing is much faster.
10. **R7: Claude Opus 5.5.** The most powerful paid model, given exactly the same information and the same R6 rules.
    - Why: a fair "best possible today" comparison, and a measure of the price in money, speed and privacy.

## Step 1 explained: the no-AI floor

Plain code with no AI got 80.8% right on clean lines and 59.9% on messy lines. It never booked anything wrongly by itself.

**How the rules work, with an example:**

1. The narration "NEFT-SHARMA TRD-INV412" is compared with every customer name and nickname, and "Sharma Traders" matches.
2. Among Sharma's unpaid bills, it looks for one of exactly ₹1,18,000 and finds INV-0412.
3. If it is unsure (no match, or several), it sends the line to a person.

**What we learned:**

- **The hard part is "who paid?", not "which bill?"** Most misses were the wrong customer: 30 on clean and 65 on messy. "SHRMA TRD-" is hard to match.
- **Messy text hurts badly:** TDS lines fell from 81% right on clean to 38% on messy.
- **It failed the pass rules for one reason:** it never reads e-mails, so it caught only 1 of 5 bank-change requests on clean (2 of 5 on messy).
- **Why this matters:** any AI must beat about 81% with zero wrong automatic bookings. That is a high bar, not an easy target.

**The bug that taught us the most:** the very first version scored only 23.7%. Short nicknames like "SG TRD" accidentally appeared inside other customers' narrations, so the code picked the wrong customer. We ignored nicknames shorter than 6 letters, removed spaces before comparing, and accuracy jumped to 80.8%.

## Step 2 explained: giving the model records

Showing the model the right customer and bills was not enough. Every model at this stage did far worse than the plain rules.

**R0, the model alone, was dangerous.** Asked about "NEFT-SHARMA TRD ₹1,77,000" with no records, it confidently made up an answer. It booked 67.5% of lines by itself and every one of those was wrong (₹34.9 lakh booked wrongly on 40 lines).

- Lesson: a confident wrong AI is worse than no AI.

**R1 and R2 found the right customer about 90% of the time,** yet the 0.8B model still scored about 0%.

- Why: we asked it to write the bill numbers itself. Instead of choosing, it listed every unpaid bill of the customer ("INV-0401, INV-0405, INV-0412, …") until it ran out of space. 77 of 177 answers were cut off and unreadable.

**The bigger 2B model reached 45%, but:**

- 70% right on simple single-bill payments, and **0% on clubbed, TDS and short payments.** Those need adding or subtracting, which small models cannot do reliably.
- It booked 84% of lines by itself and was wrong on 46% of those (₹1.39 crore booked wrongly).
- Lesson: never trust the model's own "I'm sure". We need checks we can measure.

**Why some customers can never be found by name search:** 11 of the 15 clean misses were cheque deposits whose narration has no name at all, and 4 were payments made by a sister company. No search can find a name that is not there; only the amount and e-mails can help.

**Reranker result:** it made the prompt 31% shorter and a little faster, but not more accurate.

**A rule we had to add:** R1/R2 "passed" rules 1–4 by sending every line to a person, since no automatic booking means no automatic error. That is useless, so we added rule 5: at least 50% must be handled automatically.

## Step 3 explained: code does the maths, the model chooses

This was the biggest jump in the whole project. The same 2B model went from 45% to 90% right, simply because we changed what we showed it.

**What the model now sees, for the ₹1,77,000 line (example):**

```
BANK LINE: 14 Sep  NEFT-SHARMA TRD  ₹1,77,000
MATCH OPTIONS (worked out by code):
  M1  Sharma Traders: INV-0412 + INV-0418 = ₹1,77,000 (exact, 2 bills)
  M2  Sharma Agencies: INV-0390 = ₹1,77,000 (exact, 1 bill)
  U   none of these
E-MAILS: "Paid INV-0412 and 0418 together. - Sharma Traders"
Reply with one option id and whether a person should check.
```

The model answers `{"option": "M1", "needs_review": false}`.

Why M1 and not M2? Both add up exactly, but the narration says "SHARMA TRD" and the e-mail from Sharma Traders names both bills. Choosing between options like this, using clues, is the model's job; the arithmetic is already done.

**What the code computes for the options:** exact one-bill matches; two- or three-bill sums (clubbed); TDS at 0.1%, 1% or 2% of the price before GST; short payments up to 6%; "D" when the same amount arrived in the last 2 days (a possible duplicate); and "U" always.

**Results:**

- **No model at all (the control) already got 89.8%** on clean and 88.1% on messy. On messy lines that is 28 points better than the rules, mostly because e-mails name the payer when the narration is garbled.
- **The 2B model also got 89.8%,** the same as the control, but by doing different things. It fixed 5 lines (it spotted duplicates and used e-mail clues) and broke 5 (it said "U" on some short payments).
- **The 2B model read the e-mails:** it caught 5 of 5 bank-change requests. The control caught 0, because picking M1 never reads the e-mail.
- **But it was far too careful:** it said "please check" on 74–80% of lines even when it was right, so it failed rule 5.
- **Nothing was booked wrongly by itself (0%).** Offering fixed options made the models safe.
- **The 4B model failed completely (0 of 177 readable).** It started "thinking out loud" ("Thinking Process: 1. Analyse …") and ran out of space before answering. We switched thinking off in Step 4.

**The ceiling idea.** On dev, the right answer was among the options for 94.4% of clean lines. If the right answer is not on the menu, no model can pick it, so 94.4% is the best any model could score here.

## Step 4 explained: finding mistakes and training the model

Training the small models on our own past lines took the 0.8B model from 63.8% to 93.8%. It also showed that training can quietly remove a safety habit.

**R4: sort every line into a bucket first.** Like a doctor diagnosing before giving medicine:

| Bucket | Meaning | Can training fix it? |
| --- | --- | --- |
| Correct + automatic | right and booked alone | already good |
| Correct + sent to a person | right, but too careful | yes: teach it when not to ask |
| Wrong, right option was offered | picked the wrong option | yes: teach better choices |
| Wrong, right option not offered | the menu did not include it | no: needs better options |
| Unreadable | broken answer | partly |

The 2B model was mostly "too careful" (113 lines). The 0.8B model was mostly "wrong choice" (51 lines). Both are teachable, so we decided to fine-tune.

**R5: how the training worked.**

- **Teaching material:** 1,270 solved lines from months 1–4 (clean and messy). Each one is the same R3 prompt plus the correct reply, for example `{"option": "M1", "needs_review": false}`.
- **When the right answer was not on the menu (102 lines),** the correct reply was "U" plus "a person should check". This teaches the model to say "I don't know" instead of guessing.
- **The model only learns from its answer, not from re-reading the prompt** ("loss on answer tokens only").
- **LoRA vs full:** LoRA trains a small add-on (1.25% of the 0.8B model); full trains everything.
- **Training took about 42–55 minutes per model on a Colab T4.** The loss (how wrong it is) fell from about 0.95 to almost 0 within about 20 steps, because choosing from options is easy to learn.

**Results on dev:**

- **0.8B: 63.8% → 93.8%** (+30 points), very close to the 94.4% ceiling.
- **2B: still 94.4%, but now handles 82% of lines alone instead of 26%.** The over-caution was cured, still with 0 wrong automatic bookings.
- **After training, size did not matter:** 0.8B and 2B scored about the same.
- **Faster:** 15-token answers instead of 42; 0.75 s → 0.35 s per line.
- **Full training gave no extra accuracy over LoRA,** and it needs a 3.4 GB copy of the model instead of a small add-on file.

**The warning sign.** Training reduced how many bank-change requests went to a person: 5/5 untrained → 4/5 (LoRA 2B) → 3/5 (LoRA 0.8B) → 0/5 (full 0.8B).

- Why: in 1,270 examples, "handle it yourself" was the answer most of the time, and bank changes were rare, so the model learned to ask less.
- Lesson: never let a safety rule depend on a learned habit. Put it in code. This led to Step 5.

**Bug found:** the trained 2B model did not stop after its answer. It kept writing an imaginary next question, which made it look slow (0.94 s). Telling it exactly where to stop fixed it: same accuracy, 0.38 s.

## Step 5 explained: the safety gate, Laya and Opus

Once safety rules were written in code, every system passed on dev, even the one with no AI. The question became how much more the AI adds, and at what cost.

**The R6 gate, like airport security with three checks.** A line is booked automatically only if it clears all three:

1. **Guardrail:** does any nearby e-mail ask to change bank details? If yes, it goes to a person. It reads all matching e-mails, not just the 3 shown to the model.
2. **Forced checks:** is it a possible duplicate, an unknown payer or a short payment? If yes, it goes to a person, always.
3. **Confidence threshold:** is the model sure enough of its option? If not, it goes to a person.

**How confidence is measured.** When the model writes "M1", we read how likely it thought each letter was. If it gave "M" 99.9% and "1" 99.8%, its confidence in "M1" is about 99.7%. We use this number and ignore the model's own written "needs\_review", which proved unreliable in Steps 2–4.

**The threshold knob.** We tried 12 settings (0, 0.5, 0.7, …, 0.9999) on dev and kept the lowest one that passed all five rules on both clean and messy. For every model, that was 0.

- Why 0 is not reckless: the guardrail and forced checks already stop the risky lines. The trained models were 99.9%+ sure on most lines and right about 97% of the time there, so raising the knob changed almost nothing.
- The untrained 2B model was different: 0.8 would remove its mistakes, but then it handled only 47.5% of messy lines (under 50%), so 0 was kept, with 0.74% wrong (still under the 1% limit).

**Laya, the tiny decision-maker.** Laya does not write sentences. It reads the bank line, options and e-mails and answers two questions:

- "Which option?" → M1, M2, D or U
- "Must a person check?" → yes or no
- **Training:** the same 1,270 past lines, 18.7 minutes on a T4. Options were shuffled during training. Why: the right answer is usually M1, and without shuffling Laya might just learn "always say M1".
- **Dev result:** 94.4% / 93.8%, equal to the best. Laya itself takes 0.065 s per line; with the search and menu-building steps every system needs, that is about 0.17 s, roughly 2× faster than the trained 0.8B (0.34 s).

**Opus 5.5, the expensive expert.** Exactly the same prompt, sent over the internet to Anthropic.

- **Dev result:** 94.4% / 93.8%. Whenever the right answer was on the menu, it picked it.
- **But:** 2.4 s per line, about ₹520 per 1,000 lines in fees, about 1.6 KB of business data sent out per line. It was also the most careful, handling only 67–71% alone.
- **Cost:** the 3-line check cost about $0.015 and the dev run $2.12. It "thinks" before answering, and that thinking is billed.

**On dev, every gated system passed**, including the no-AI control. So the AI must prove its worth on top of good code.

## The final exam: results and what "significant" means

On month 6, which no system had ever seen, the small trained models scored best (91.4% clean) and Opus scored 89.7%. But the gap is only 3 lines out of 185, too small to prove anything.

**The results in plain words** (185 lines per condition):

| System | Right (clean / messy) | Time per line | Cost per 1,000 lines | Data sent out | Passed? |
| --- | --- | --- | --- | --- | --- |
| Rules, no AI | 74.6% / 55.1% | 0.1 s | ₹1 | none | no |
| R6 control, no AI | 89.7% / 88.1% | 0.1 s | ₹1 | none | yes |
| Untrained Qwen 2B | 87.0% / 85.4% | 0.7 s | ₹6 | none | yes, with 1 wrong booking |
| Trained 0.8B (LoRA) | 91.4% / 89.2% | 0.34 s | ₹3 | none | yes |
| Trained 2B (LoRA) | 91.4% / 88.6% | 0.41 s | ₹3.5 | none | yes |
| Laya | 91.4% / 88.6% | about 0.17 s\* | about ₹1.4\* | none | yes |
| Claude Opus 5.5 | 89.7% / 87.6% | 2.3 s | ₹480–500 | about 300 KB | yes |
| Best possible (answer on the menu) | 92.4% / 90.3% | – | – | – | – |

\* Corrected on 23 Nov. We first logged Laya at 0.07 s, but that timed only Laya itself. Every other system's time also includes the search and menu building (about 0.10 s). Counting the same steps, Laya takes about 0.17 s. On your MacBook it measured 0.27–0.28 s (see Step 6).

**How to read it:**

- The trained models got within 1 point of the best possible.
- Opus was not better than the small trained model. On this month it picked a wrong option 5 times when the right one was on the menu; the trained models did that only 2–3 times.
- Laya matched the best on clean lines, at a fraction of the time and cost.
- The trained 0.8B without the gate (R5) missed 1 of 7 bank-change e-mails on messy lines and failed. The gate matters on new data too.
- The final exam was harder than practice: the right customer was found less often (93.8% vs 95.9%), so the best possible score fell.

**What "significant" means, with a coin example.** Toss a coin 4 times and get 3 heads. Is the coin unfair? Probably not, because that happens by luck quite often. Toss it 100 times and get 75 heads, and now you can be confident.

Our comparisons are like the 4-toss case:

- The trained 0.8B and the no-AI control disagreed on only 3 lines, and the trained model won all 3. The chance of 3-0 by pure luck is 25% (p = 0.25). Scientists want under 5% (p < 0.05) before calling it real.
- To reach p < 0.05 we would need about 6 one-sided wins. With one test month there simply are not enough lines where systems disagree.
- The only clearly real difference: the plain rules are worse than everything else (28 and 62 lines lost, p < 0.001).

**So the honest sentence for the report:** "The trained local models *matched* Opus 5.5 (the difference is not significant) while being on an ordinary MacBook about 3–9× faster and about 70–220× cheaper per line, and sending no data off the machine." Do not write "beat Opus".

## What went wrong and how we fixed it

Every problem below changed what we built next. Read in order, they explain how the project reached its final shape.

1. **The rules picked the wrong customer (23.7%).** Short nicknames like "SG TRD" matched inside other narrations. We ignored short nicknames and compared without spaces, which gave 80.8%.
   - Lesson: finding "who paid" is the first hard problem.
2. **Our own answer key failed our own pass rules.** Short payments with no reason were marked "safe to book". We fixed the generator.
   - Lesson: test the examiner before testing the students.
3. **Name search cannot find names that are not there** (cheques, sister firms). We accepted this as a limit for R1/R2 and used amounts and e-mails in R3.
4. **Small models listed every bill instead of choosing.** We switched to ready-made options (M1, M2, U) that the model picks from.
5. **"Send everything to a person" passed the rules.** We added rule 5: handle at least 50% alone.
6. **Small models could not add or subtract.** Code now does all the maths.
7. **The 4B model "thought out loud" and never answered.** We switched thinking off, and it became the first system to pass all rules.
8. **The 2B model was far too careful (asked a person 74–80% of the time).** Training fixed it: 82% handled alone, still 0 wrong.
9. **Colab's free GPU time ran out mid-run.** The trained add-ons were already saved, so we wrote a "resume" notebook and bought 100 Colab compute units.
10. **Resume errors ("No module named pratyaksha").** The setup cells had been skipped. Now every cell first moves to the project folder, and setup always runs first.
11. **The trained 2B model would not stop writing.** We told it exactly where to stop: same answers, 2.5× faster. This also showed that our earlier claim "0.8B is 2.7× faster" was wrong, so we withdrew it.
12. **Training removed the bank-change safety habit (down to 0/5).** We moved the rule into code (the guardrail): 5/5 on practice months and 7/7 on the final exam.
13. **The guardrail first caught 4/5.** The fraud e-mail was the 4th e-mail and was cut by the "show only 3" limit. The guardrail now reads all e-mails.
14. **R7 was briefly switched to a different model and Laya was left out,** which departed from the mid-sem plan. We restored the plan: Opus 5.5 and Laya.
15. **Opus cost 19% more than estimated,** because harder lines need more "thinking". Total spend was about $4.18 of $10.
16. **Laya's training printed warnings** (a calibration limit, "conflicting schema", some negative loss values). The results were fine, and we checked that the schema warning affected 0 test lines. The other causes are recorded as not yet explained.
17. **A small bug in an analysis script** (it cut "R6\_" off system names). Fixed; no result changed.
18. **One earlier claim was wrong:** "only the AI can catch bank changes". With the guardrail, plain code catches them too. We corrected it.

19) **Laya's speed was measured unfairly (found while preparing the Mac runs).** Its stopwatch started after the search and menu building, while every other system's stopwatch included them. Like timing one runner from the halfway mark. We fixed the code, added a test, and corrected every speed and cost claim: Laya is about 0.17 s per line, not 0.07 s. Its answers did not change.

## What we can and cannot claim

We can say what we measured on our pretend business. We cannot promise the same numbers for every real business.

| We CAN say | We CANNOT say | Why not |
| --- | --- | --- |
| Trained local models matched Opus 5.5 on accuracy | "Our model beats Opus" | the gap (3 lines) is not significant |
| Good engineering gave the big, proven jump over rules | "AI made it 15–33 points better" | most of that jump came from code, not the model |
| The local models sent 0 bytes outside the computer | "It is safe for any company" | tested on one pretend business |
| The guardrail caught 7/7 bank-change e-mails | "It catches every fraud e-mail" | it looks for our generator's wording; real e-mails vary |
| Laya is the fastest and cheapest | "Laya is the most accurate" | it tied on clean, 1 line behind on messy |
| Results hold on an unseen month | "Results hold for any month" | one test month, 185 lines per condition |

Other limits to mention honestly:

- Only 5–7 bank-change lines per month, so one line decides that rule.
- The pass-rule values come from the mid-sem report and were not reviewed by a chartered accountant.
- Colab times are measured 8 lines at a time; true one-at-a-time times come from the Mac in Step 6.
- Opus does not give confidence numbers, so its gate uses its own written "needs review" flag, with the same code rules.

## Step 6 explained: running it on your own Mac

We ran the finished systems on your MacBook Pro 2021 (Apple M1 Pro chip, 16 GB memory), one bank line at a time, like a real office would. Every single answer was the same as on Google's computer, all 1,480 of them.

**Why we did this:** the project's claim is that a small business can run this on a computer it owns. So the speed and cost must be measured on such a computer, not on a rented Google GPU.

**What "same answers" means and why it matters.** We ran 4 systems × 2 conditions × 185 lines = 1,480 answers. On the Mac each one matched Colab exactly.

- Example: if Colab said "line 47 = Sharma Traders, INV-0412, book automatically", the Mac said exactly the same.
- Why it matters: the results do not depend on special hardware. Anyone can reproduce them.

**Speed and cost on the Mac (per bank line):**

| System | Right (clean / messy) | Time per line | Cost per 1,000 lines | Data sent out |
| --- | --- | --- | --- | --- |
| Rules, no AI | 74.6% / 55.1% | 0.04–0.06 s | ₹0.3–0.5 | none |
| R6 control, no AI | 89.7% / 88.1% | 0.11 s | ₹0.9 | none |
| Laya | 91.4% / 88.6% | 0.28 s | ₹2.3 | none |
| Trained 0.8B | 91.4% / 89.2% | 0.86 s | ₹7.0 | none |
| Claude Opus 5.5 (internet) | 89.7% / 87.6% | 2.3–2.4 s | ₹479–501 | about 1.6 KB per line |

**How we worked out the Mac's cost, with an example:**

- **The laptop:** ₹1,75,000, used for about 6,000 working hours (3 years × 250 days × 8 hours), so about ₹29 per hour. Laya uses 0.28 s per line, so 1,000 lines take 280 s (about 0.08 h), which costs about ₹2.3.
- **Electricity:** we assumed the Mac uses 35 W. 1,000 Laya lines use about 0.003 units (kWh), which is under 3 paise. The laptop's price is 99% of the cost, so the exact wattage does not matter.

**What this tells us:**

1. Opus is about 3× slower than the trained 0.8B and 8–9× slower than Laya.
2. Opus costs about 70× (vs the 0.8B) to 200× (vs Laya) more per line, and it sends business data over the internet.
3. Laya can check about 12,900 bank lines an hour on the laptop, so a small business's whole month takes a few minutes.

**Problems we hit on the Mac and fixed:**

- The Mac's built-in Python was too old (3.9); we installed Python 3.12 with Homebrew.
- The Qwen model needed two picture-handling packages (Pillow, torchvision) that Colab has pre-installed; we added them.
- Qwen's two fast "turbo" add-ons only work on NVIDIA graphics cards, so on the Mac (as on Colab) the model ran on slower standard code. Its answers are the same; only speed is affected.

## What is left to do

All the experiments are finished, and the final exam numbers will not change. What remains is showing it on your own Mac and presenting it.

- [x] Mac runs: time Laya, the trained 0.8B and the no-AI control on your MacBook, one line at a time (done 23 Nov; see Step 6)
- [ ] **Demo app:** the same bank line answered side by side by each system; a meter showing data sent out (0 vs about 1.6 KB); a live step-by-step trace; and the threshold knob you can turn.
- [ ] **Final report:** the main report plus the demo.
- [ ] **Slides and rehearsal** for the final demo on Dec 5, 2026.

**Ideas for improvement** (tried only on practice months, never on the final exam):

1. Better search and option building, because 14–18 mistakes per condition happened when the right answer was not on the menu.
2. Show the e-mail with the exact amount first, before the 3-e-mail limit cuts anything.
3. Better short-payment options, the one choice every model still sometimes got wrong.

## Questions faculty may ask, with simple answers

These are the questions most likely to come up at the demo, each with a short answer you can say in your own words.

| Question | Simple answer |
| --- | --- |
| Why not use real bank data? | It is private, and there is no answer key. Our generator creates a realistic business and knows every right answer, and anyone can re-create it with seed 7. |
| If plain code gets 89.7%, why use AI at all? | The AI adds a little accuracy (3 lines out of 185), reads e-mails, spots duplicates and handles slightly more lines alone. We say honestly that this gain is small and not proven on one month. The big win is the engineering. |
| Why did a tiny 0.8B model match a giant like Opus? | We gave it a simple job, choosing from options the code already worked out, and trained it on this business's own history. A simple job does not need a giant brain. |
| Why not just trust the AI's "I'm sure"? | In Step 2 the model was "sure" and wrong 46% of the time. Safety decisions are made by code rules we can test. |
| What does fine-tuning actually change? | It shows the model 1,270 solved examples so it learns this task's habits. LoRA changes only a small add-on (about 1% of the model). |
| Why did fine-tuning make it less safe? | Most examples said "handle it yourself", so the model learned to ask less, including on rare fraud e-mails. That is why the fraud rule is in code. |
| What is Laya and why use it? | A small model that only chooses (it does not write). Choosing is all we need, so it is the fastest and cheapest (about 3× faster than the trained 0.8B on the Mac: 0.28 s vs 0.86 s per line), with the same accuracy on clean lines. |
| Why is the threshold 0? Is that unsafe? | The code rules already send risky lines to a person, and the trained models are almost always very confident. Raising the knob changed little. It was chosen on practice months by a fixed rule, never on the exam. |
| Is the difference between your model and Opus real? | Not proven: p = 0.25 means it could be luck. We claim "matched", plus the clear wins in speed, cost and privacy. |
| How do you know you didn't cheat on the test month? | The pass rules were frozen and every setting chosen before month 6 was run, once. Nothing was changed afterwards. |
| What was the hardest problem? | Finding who paid from messy, cut-off narrations. Most remaining errors happen because the right answer never reached the menu. |
| What would you do next? | Improve search and option building, which is where the remaining mistakes are, and test with a real business and an accountant. |
| How much did it cost? | About 100 Colab compute units for training and about $4.18 for Opus. Each trained model is a one-time cost of under an hour of T4 time. |
