# Scorecard: R1_Qwen3.5-2B · dev · clean

Run `20261122-170615_R1_Qwen3.5-2B_dev_clean` · n = 177

| Metric | Value |
|---|---|
| Accuracy (strict) | 45.8% |
| Handled automatically | 81.9% |
| Error rate on automatic | 45.52% |
| Latency p50 / p95 | 1915.3 ms / 2007.6 ms |
| ₹ per 1,000 tasks (operating) | 15.1697 |
| ₹ per 1,000 tasks (hardware amortisation) | 0.0000 |
| Tokens in / out per task | 1929 / 87 |
| Data leaving the machine | 0 bytes |
| Restricted-field leaks | 0 |
| Right party among retrieved | 90.6% |
| Model output unreadable (parse errors) | 22 |
| Right answer among computed options | n/a |

## Business acceptance bar

| Rule | Result |
|---|---|
| Automatic entries ≤ 1% wrong (45.52%) | FAIL |
| Misbooked rupees ≤ ₹1,000 (₹12,487,557.88) | FAIL |
| Every unexplained entry surfaced (54%, 6 silently matched) | FAIL |
| Bank-detail changes to a person (0% of 5) | FAIL |
| Handles at least 50% by itself (82%) | PASS |
| **Overall** | **FAIL** |

## By category

| Category | Correct | n | Accuracy |
|---|---|---|---|
| bank_charges | 0 | 1 | 0.0% |
| clubbed_payment | 0 | 24 | 0.0% |
| duplicate_credit | 0 | 4 | 0.0% |
| full_payment | 76 | 108 | 70.4% |
| interest_credit | 0 | 1 | 0.0% |
| short_payment | 0 | 10 | 0.0% |
| supplier_payment | 3 | 4 | 75.0% |
| tds_deduction | 0 | 21 | 0.0% |
| unknown_party | 2 | 4 | 50.0% |

## Error types

| Type | Count |
|---|---|
| wrong_invoices | 38 |
| system_error | 20 |
| wrong_category | 19 |
| wrong_party | 13 |
| ranked_too_low | 6 |
