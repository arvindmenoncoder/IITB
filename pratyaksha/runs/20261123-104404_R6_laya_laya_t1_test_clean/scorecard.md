# Scorecard: R6_laya_laya_t1 · test · clean

Run `20261123-104404_R6_laya_laya_t1_test_clean` · n = 185

| Metric | Value |
|---|---|
| Accuracy (strict) | 91.4% |
| Handled automatically | 75.7% |
| Error rate on automatic | 0.00% |
| Latency p50 / p95 | 67.7 ms / 93.5 ms |
| ₹ per 1,000 tasks (operating) | 0.5852 |
| ₹ per 1,000 tasks (hardware amortisation) | 0.0000 |
| Tokens in / out per task | 0 / 0 |
| Data leaving the machine | 0 bytes |
| Restricted-field leaks | 0 |
| Right party among retrieved | 93.8% |
| Model output unreadable (parse errors) | 0 |
| Right answer among computed options | 92.4% |

## Business acceptance bar

| Rule | Result |
|---|---|
| Automatic entries ≤ 1% wrong (0.00%) | PASS |
| Misbooked rupees ≤ ₹1,000 (₹0.00) | PASS |
| Every unexplained entry surfaced (100%, 0 silently matched) | PASS |
| Bank-detail changes to a person (100% of 7) | PASS |
| Handles at least 50% by itself (76%) | PASS |
| **Overall** | **PASS** |

## By category

| Category | Correct | n | Accuracy |
|---|---|---|---|
| bank_charges | 1 | 1 | 100.0% |
| clubbed_payment | 22 | 26 | 84.6% |
| full_payment | 112 | 118 | 94.9% |
| interest_credit | 1 | 1 | 100.0% |
| short_payment | 10 | 14 | 71.4% |
| supplier_payment | 4 | 4 | 100.0% |
| tds_deduction | 14 | 16 | 87.5% |
| unknown_party | 5 | 5 | 100.0% |

## Error types

| Type | Count |
|---|---|
| wrong_party | 14 |
| not_retrieved | 2 |
