# Business acceptance bar — FROZEN 23 Nov 2026, before any test-month run

A system counts as usable for task T1 only if, on a run, ALL hold:

| # | Rule | Value | Why |
|---|---|---|---|
| 1 | Error rate on lines handled automatically | ≤ 1% | Wrong bookings nobody looks at are the real business risk |
| 2 | Misbooked rupees (wrong AND automatic) | ≤ ₹1,000 | The cash position must stay trustworthy |
| 3 | Unexplained entries | 100% surfaced, 0 silently matched | Mid-sem rule: nothing unexplained is booked quietly |
| 4 | Bank-detail change requests | 100% sent to a person | Classic payment-fraud route; never automated |
| 5 | Handled automatically | ≥ 50% | Added 22 Nov: "send everything to a person" must not pass |

Rules 1–4 are from the mid-sem report (provisional bar). Rule 5 was added during development after a
system passed by doing nothing (WHAT_DIDNT_WORK.md, 22 Nov).

**Honest limits.** The values were not reviewed by the chartered accountant before freezing (time). Rule 4
rests on 5 cases per month-condition, so one line decides it. R6 thresholds are chosen on the dev month
only and applied unchanged to the test month.
