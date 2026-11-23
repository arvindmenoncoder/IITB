# Scorecard: rules · dev · clean

Run `20261120-225629_rules_dev_clean` · n = 177

| Metric | Value |
|---|---|
| Accuracy (strict) | 80.8% |
| Handled automatically | 71.8% |
| Error rate on automatic | 0.00% |
| Latency p50 / p95 | 95.8 ms / 188.0 ms |
| ₹ per 1,000 tasks (operating) | 0.0076 |
| ₹ per 1,000 tasks (hardware amortisation) | 1.0794 |
| Tokens in / out per task | 0 / 0 |
| Data leaving the machine | 0 bytes |
| Restricted-field leaks | 0 |

## Business acceptance bar

| Rule | Result |
|---|---|
| Automatic entries ≤ 1% wrong (0.00%) | PASS |
| Misbooked rupees ≤ ₹1,000 (₹0.00) | PASS |
| Every unexplained entry surfaced (100%, 0 silently matched) | PASS |
| Bank-detail changes to a person (20% of 5) | FAIL |
| **Overall** | **FAIL** |

## By category

| Category | Correct | n | Accuracy |
|---|---|---|---|
| bank_charges | 1 | 1 | 100.0% |
| clubbed_payment | 18 | 24 | 75.0% |
| duplicate_credit | 3 | 4 | 75.0% |
| full_payment | 86 | 108 | 79.6% |
| interest_credit | 1 | 1 | 100.0% |
| short_payment | 9 | 10 | 90.0% |
| supplier_payment | 4 | 4 | 100.0% |
| tds_deduction | 17 | 21 | 81.0% |
| unknown_party | 4 | 4 | 100.0% |

## Error types

| Type | Count |
|---|---|
| wrong_party | 30 |
| wrong_invoices | 2 |
| wrong_category | 1 |
| ranked_too_low | 1 |
