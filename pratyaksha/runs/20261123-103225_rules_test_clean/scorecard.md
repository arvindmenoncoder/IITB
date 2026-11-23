# Scorecard: rules · test · clean

Run `20261123-103225_rules_test_clean` · n = 185

| Metric | Value |
|---|---|
| Accuracy (strict) | 74.6% |
| Handled automatically | 67.6% |
| Error rate on automatic | 0.00% |
| Latency p50 / p95 | 135.1 ms / 268.0 ms |
| ₹ per 1,000 tasks (operating) | 1.1197 |
| ₹ per 1,000 tasks (hardware amortisation) | 0.0000 |
| Tokens in / out per task | 0 / 0 |
| Data leaving the machine | 0 bytes |
| Restricted-field leaks | 0 |
| Right party among retrieved | n/a |
| Model output unreadable (parse errors) | 0 |
| Right answer among computed options | n/a |

## Business acceptance bar

| Rule | Result |
|---|---|
| Automatic entries ≤ 1% wrong (0.00%) | PASS |
| Misbooked rupees ≤ ₹1,000 (₹0.00) | PASS |
| Every unexplained entry surfaced (100%, 0 silently matched) | PASS |
| Bank-detail changes to a person (29% of 7) | FAIL |
| Handles at least 50% by itself (68%) | PASS |
| **Overall** | **FAIL** |

## By category

| Category | Correct | n | Accuracy |
|---|---|---|---|
| bank_charges | 1 | 1 | 100.0% |
| clubbed_payment | 19 | 26 | 73.1% |
| full_payment | 86 | 118 | 72.9% |
| interest_credit | 1 | 1 | 100.0% |
| short_payment | 8 | 14 | 57.1% |
| supplier_payment | 4 | 4 | 100.0% |
| tds_deduction | 14 | 16 | 87.5% |
| unknown_party | 5 | 5 | 100.0% |

## Error types

| Type | Count |
|---|---|
| wrong_party | 43 |
| wrong_invoices | 2 |
| ranked_too_low | 2 |
