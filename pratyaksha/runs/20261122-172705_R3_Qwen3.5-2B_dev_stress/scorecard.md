# Scorecard: R3_Qwen3.5-2B · dev · stress

Run `20261122-172705_R3_Qwen3.5-2B_dev_stress` · n = 177

| Metric | Value |
|---|---|
| Accuracy (strict) | 88.7% |
| Handled automatically | 19.8% |
| Error rate on automatic | 0.00% |
| Latency p50 / p95 | 763.1 ms / 927.0 ms |
| ₹ per 1,000 tasks (operating) | 6.5652 |
| ₹ per 1,000 tasks (hardware amortisation) | 0.0000 |
| Tokens in / out per task | 527 / 41 |
| Data leaving the machine | 0 bytes |
| Restricted-field leaks | 0 |
| Right party among retrieved | 95.3% |
| Model output unreadable (parse errors) | 2 |
| Right answer among computed options | 93.8% |

## Business acceptance bar

| Rule | Result |
|---|---|
| Automatic entries ≤ 1% wrong (0.00%) | PASS |
| Misbooked rupees ≤ ₹1,000 (₹0.00) | PASS |
| Every unexplained entry surfaced (100%, 0 silently matched) | PASS |
| Bank-detail changes to a person (100% of 5) | PASS |
| Handles at least 50% by itself (20%) | FAIL |
| **Overall** | **FAIL** |

## By category

| Category | Correct | n | Accuracy |
|---|---|---|---|
| bank_charges | 0 | 1 | 0.0% |
| clubbed_payment | 21 | 24 | 87.5% |
| duplicate_credit | 1 | 4 | 25.0% |
| full_payment | 102 | 108 | 94.4% |
| interest_credit | 1 | 1 | 100.0% |
| short_payment | 7 | 10 | 70.0% |
| supplier_payment | 4 | 4 | 100.0% |
| tds_deduction | 18 | 21 | 85.7% |
| unknown_party | 3 | 4 | 75.0% |

## Error types

| Type | Count |
|---|---|
| wrong_party | 12 |
| wrong_category | 4 |
| system_error | 2 |
| wrong_invoices | 1 |
| not_retrieved | 1 |
