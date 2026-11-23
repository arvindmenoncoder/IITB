# Scorecard: R3_control_first_option · dev · stress

Run `20261122-170433_R3_control_first_option_dev_stress` · n = 177

| Metric | Value |
|---|---|
| Accuracy (strict) | 88.1% |
| Handled automatically | 80.8% |
| Error rate on automatic | 0.00% |
| Latency p50 / p95 | 105.7 ms / 114.2 ms |
| ₹ per 1,000 tasks (operating) | 0.8803 |
| ₹ per 1,000 tasks (hardware amortisation) | 0.0000 |
| Tokens in / out per task | 341 / 25 |
| Data leaving the machine | 0 bytes |
| Restricted-field leaks | 0 |
| Right party among retrieved | 95.3% |
| Model output unreadable (parse errors) | 0 |
| Right answer among computed options | 93.8% |

## Business acceptance bar

| Rule | Result |
|---|---|
| Automatic entries ≤ 1% wrong (0.00%) | PASS |
| Misbooked rupees ≤ ₹1,000 (₹0.00) | PASS |
| Every unexplained entry surfaced (100%, 0 silently matched) | PASS |
| Bank-detail changes to a person (0% of 5) | FAIL |
| Handles at least 50% by itself (81%) | PASS |
| **Overall** | **FAIL** |

## By category

| Category | Correct | n | Accuracy |
|---|---|---|---|
| bank_charges | 1 | 1 | 100.0% |
| clubbed_payment | 20 | 24 | 83.3% |
| duplicate_credit | 0 | 4 | 0.0% |
| full_payment | 100 | 108 | 92.6% |
| interest_credit | 1 | 1 | 100.0% |
| short_payment | 10 | 10 | 100.0% |
| supplier_payment | 4 | 4 | 100.0% |
| tds_deduction | 17 | 21 | 81.0% |
| unknown_party | 3 | 4 | 75.0% |

## Error types

| Type | Count |
|---|---|
| wrong_party | 15 |
| wrong_category | 4 |
| wrong_invoices | 2 |
