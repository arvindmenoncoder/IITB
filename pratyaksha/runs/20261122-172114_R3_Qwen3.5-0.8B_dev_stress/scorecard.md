# Scorecard: R3_Qwen3.5-0.8B · dev · stress

Run `20261122-172114_R3_Qwen3.5-0.8B_dev_stress` · n = 177

| Metric | Value |
|---|---|
| Accuracy (strict) | 61.6% |
| Handled automatically | 55.4% |
| Error rate on automatic | 0.00% |
| Latency p50 / p95 | 782.1 ms / 939.5 ms |
| ₹ per 1,000 tasks (operating) | 6.4687 |
| ₹ per 1,000 tasks (hardware amortisation) | 0.0000 |
| Tokens in / out per task | 527 / 43 |
| Data leaving the machine | 0 bytes |
| Restricted-field leaks | 0 |
| Right party among retrieved | 95.3% |
| Model output unreadable (parse errors) | 6 |
| Right answer among computed options | 93.8% |

## Business acceptance bar

| Rule | Result |
|---|---|
| Automatic entries ≤ 1% wrong (0.00%) | PASS |
| Misbooked rupees ≤ ₹1,000 (₹0.00) | PASS |
| Every unexplained entry surfaced (100%, 0 silently matched) | PASS |
| Bank-detail changes to a person (60% of 5) | FAIL |
| Handles at least 50% by itself (55%) | PASS |
| **Overall** | **FAIL** |

## By category

| Category | Correct | n | Accuracy |
|---|---|---|---|
| bank_charges | 0 | 1 | 0.0% |
| clubbed_payment | 9 | 24 | 37.5% |
| duplicate_credit | 1 | 4 | 25.0% |
| full_payment | 79 | 108 | 73.1% |
| interest_credit | 0 | 1 | 0.0% |
| short_payment | 1 | 10 | 10.0% |
| supplier_payment | 4 | 4 | 100.0% |
| tds_deduction | 12 | 21 | 57.1% |
| unknown_party | 3 | 4 | 75.0% |

## Error types

| Type | Count |
|---|---|
| wrong_party | 49 |
| wrong_category | 7 |
| system_error | 6 |
| wrong_invoices | 3 |
| not_retrieved | 3 |
