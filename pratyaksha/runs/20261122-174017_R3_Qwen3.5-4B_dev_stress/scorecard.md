# Scorecard: R3_Qwen3.5-4B · dev · stress

Run `20261122-174017_R3_Qwen3.5-4B_dev_stress` · n = 177

| Metric | Value |
|---|---|
| Accuracy (strict) | 2.3% |
| Handled automatically | 0.0% |
| Error rate on automatic | 0.00% |
| Latency p50 / p95 | 2342.5 ms / 2542.1 ms |
| ₹ per 1,000 tasks (operating) | 19.6748 |
| ₹ per 1,000 tasks (hardware amortisation) | 0.0000 |
| Tokens in / out per task | 525 / 80 |
| Data leaving the machine | 0 bytes |
| Restricted-field leaks | 0 |
| Right party among retrieved | 95.3% |
| Model output unreadable (parse errors) | 177 |
| Right answer among computed options | 93.8% |

## Business acceptance bar

| Rule | Result |
|---|---|
| Automatic entries ≤ 1% wrong (0.00%) | PASS |
| Misbooked rupees ≤ ₹1,000 (₹0.00) | PASS |
| Every unexplained entry surfaced (100%, 0 silently matched) | PASS |
| Bank-detail changes to a person (100% of 5) | PASS |
| Handles at least 50% by itself (0%) | FAIL |
| **Overall** | **FAIL** |

## By category

| Category | Correct | n | Accuracy |
|---|---|---|---|
| bank_charges | 0 | 1 | 0.0% |
| clubbed_payment | 0 | 24 | 0.0% |
| duplicate_credit | 0 | 4 | 0.0% |
| full_payment | 0 | 108 | 0.0% |
| interest_credit | 0 | 1 | 0.0% |
| short_payment | 0 | 10 | 0.0% |
| supplier_payment | 0 | 4 | 0.0% |
| tds_deduction | 0 | 21 | 0.0% |
| unknown_party | 4 | 4 | 100.0% |

## Error types

| Type | Count |
|---|---|
| system_error | 173 |
