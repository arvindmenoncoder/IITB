# Scorecard: rules · dev · stress

Run `20261120-225647_rules_dev_stress` · n = 177

| Metric | Value |
|---|---|
| Accuracy (strict) | 59.9% |
| Handled automatically | 53.1% |
| Error rate on automatic | 0.00% |
| Latency p50 / p95 | 56.2 ms / 119.9 ms |
| ₹ per 1,000 tasks (operating) | 0.0046 |
| ₹ per 1,000 tasks (hardware amortisation) | 0.6556 |
| Tokens in / out per task | 0 / 0 |
| Data leaving the machine | 0 bytes |
| Restricted-field leaks | 0 |

## Business acceptance bar

| Rule | Result |
|---|---|
| Automatic entries ≤ 1% wrong (0.00%) | PASS |
| Misbooked rupees ≤ ₹1,000 (₹0.00) | PASS |
| Every unexplained entry surfaced (100%, 0 silently matched) | PASS |
| Bank-detail changes to a person (40% of 5) | FAIL |
| **Overall** | **FAIL** |

## By category

| Category | Correct | n | Accuracy |
|---|---|---|---|
| bank_charges | 1 | 1 | 100.0% |
| clubbed_payment | 14 | 24 | 58.3% |
| duplicate_credit | 1 | 4 | 25.0% |
| full_payment | 66 | 108 | 61.1% |
| interest_credit | 1 | 1 | 100.0% |
| short_payment | 7 | 10 | 70.0% |
| supplier_payment | 4 | 4 | 100.0% |
| tds_deduction | 8 | 21 | 38.1% |
| unknown_party | 4 | 4 | 100.0% |

## Error types

| Type | Count |
|---|---|
| wrong_party | 65 |
| wrong_category | 3 |
| wrong_invoices | 2 |
| ranked_too_low | 1 |
