# Scorecard: R1_Qwen3.5-2B · dev · stress

Run `20261122-171202_R1_Qwen3.5-2B_dev_stress` · n = 177

| Metric | Value |
|---|---|
| Accuracy (strict) | 40.7% |
| Handled automatically | 80.8% |
| Error rate on automatic | 50.35% |
| Latency p50 / p95 | 1949.8 ms / 2057.2 ms |
| ₹ per 1,000 tasks (operating) | 16.0134 |
| ₹ per 1,000 tasks (hardware amortisation) | 0.0000 |
| Tokens in / out per task | 1907 / 89 |
| Data leaving the machine | 0 bytes |
| Restricted-field leaks | 0 |
| Right party among retrieved | 88.3% |
| Model output unreadable (parse errors) | 21 |
| Right answer among computed options | n/a |

## Business acceptance bar

| Rule | Result |
|---|---|
| Automatic entries ≤ 1% wrong (50.35%) | FAIL |
| Misbooked rupees ≤ ₹1,000 (₹14,372,046.68) | FAIL |
| Every unexplained entry surfaced (54%, 6 silently matched) | FAIL |
| Bank-detail changes to a person (0% of 5) | FAIL |
| Handles at least 50% by itself (81%) | PASS |
| **Overall** | **FAIL** |

## By category

| Category | Correct | n | Accuracy |
|---|---|---|---|
| bank_charges | 0 | 1 | 0.0% |
| clubbed_payment | 0 | 24 | 0.0% |
| duplicate_credit | 0 | 4 | 0.0% |
| full_payment | 68 | 108 | 63.0% |
| interest_credit | 0 | 1 | 0.0% |
| short_payment | 0 | 10 | 0.0% |
| supplier_payment | 3 | 4 | 75.0% |
| tds_deduction | 0 | 21 | 0.0% |
| unknown_party | 1 | 4 | 25.0% |

## Error types

| Type | Count |
|---|---|
| wrong_invoices | 37 |
| wrong_party | 23 |
| system_error | 20 |
| wrong_category | 15 |
| ranked_too_low | 10 |
