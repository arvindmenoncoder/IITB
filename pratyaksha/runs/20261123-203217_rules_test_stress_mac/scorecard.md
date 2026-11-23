# Scorecard: rules · test · stress

Run `20261123-203217_rules_test_stress_mac` · n = 185

| Metric | Value |
|---|---|
| Accuracy (strict) | 55.1% |
| Handled automatically | 49.2% |
| Error rate on automatic | 0.00% |
| Latency p50 / p95 | 35.5 ms / 79.0 ms |
| ₹ per 1,000 tasks (operating) | 0.0030 |
| ₹ per 1,000 tasks (hardware amortisation) | 0.3145 |
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
| Bank-detail changes to a person (57% of 7) | FAIL |
| Handles at least 50% by itself (49%) | FAIL |
| **Overall** | **FAIL** |

## By category

| Category | Correct | n | Accuracy |
|---|---|---|---|
| bank_charges | 1 | 1 | 100.0% |
| clubbed_payment | 12 | 26 | 46.2% |
| full_payment | 64 | 118 | 54.2% |
| interest_credit | 1 | 1 | 100.0% |
| short_payment | 6 | 14 | 42.9% |
| supplier_payment | 4 | 4 | 100.0% |
| tds_deduction | 9 | 16 | 56.2% |
| unknown_party | 5 | 5 | 100.0% |

## Error types

| Type | Count |
|---|---|
| wrong_party | 79 |
| wrong_invoices | 2 |
| ranked_too_low | 2 |
