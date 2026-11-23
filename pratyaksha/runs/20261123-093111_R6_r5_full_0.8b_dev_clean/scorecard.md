# Scorecard: R6_r5_full_0.8b · dev · clean

Run `20261123-093111_R6_r5_full_0.8b_dev_clean` · n = 177

| Metric | Value |
|---|---|
| Accuracy (strict) | 93.8% |
| Handled automatically | 77.4% |
| Error rate on automatic | 0.00% |
| Latency p50 / p95 | 347.0 ms / 403.2 ms |
| ₹ per 1,000 tasks (operating) | 2.9423 |
| ₹ per 1,000 tasks (hardware amortisation) | 0.0000 |
| Tokens in / out per task | 526 / 14 |
| Data leaving the machine | 0 bytes |
| Restricted-field leaks | 0 |
| Right party among retrieved | 95.9% |
| Model output unreadable (parse errors) | 0 |
| Right answer among computed options | 94.4% |

## Business acceptance bar

| Rule | Result |
|---|---|
| Automatic entries ≤ 1% wrong (0.00%) | PASS |
| Misbooked rupees ≤ ₹1,000 (₹0.00) | PASS |
| Every unexplained entry surfaced (100%, 0 silently matched) | PASS |
| Bank-detail changes to a person (100% of 5) | PASS |
| Handles at least 50% by itself (77%) | PASS |
| **Overall** | **PASS** |

## By category

| Category | Correct | n | Accuracy |
|---|---|---|---|
| bank_charges | 1 | 1 | 100.0% |
| clubbed_payment | 21 | 24 | 87.5% |
| duplicate_credit | 4 | 4 | 100.0% |
| full_payment | 103 | 108 | 95.4% |
| interest_credit | 1 | 1 | 100.0% |
| short_payment | 10 | 10 | 100.0% |
| supplier_payment | 4 | 4 | 100.0% |
| tds_deduction | 19 | 21 | 90.5% |
| unknown_party | 3 | 4 | 75.0% |

## Error types

| Type | Count |
|---|---|
| wrong_party | 8 |
| not_retrieved | 2 |
| wrong_invoices | 1 |
