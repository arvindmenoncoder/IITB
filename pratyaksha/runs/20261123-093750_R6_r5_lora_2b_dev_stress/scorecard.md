# Scorecard: R6_r5_lora_2b · dev · stress

Run `20261123-093750_R6_r5_lora_2b_dev_stress` · n = 177

| Metric | Value |
|---|---|
| Accuracy (strict) | 93.2% |
| Handled automatically | 75.7% |
| Error rate on automatic | 0.00% |
| Latency p50 / p95 | 411.9 ms / 468.9 ms |
| ₹ per 1,000 tasks (operating) | 3.4981 |
| ₹ per 1,000 tasks (hardware amortisation) | 0.0000 |
| Tokens in / out per task | 527 / 14 |
| Data leaving the machine | 0 bytes |
| Restricted-field leaks | 0 |
| Right party among retrieved | 95.3% |
| Model output unreadable (parse errors) | 0 |
| Right answer among computed options | 93.8% |

## Business acceptance bar

| Rule | Result |
|---|---|
| Automatic entries ≤ 1% wrong (0.00%) | PASS |
| Misbooked rupees ≤ ₹1,000 (₹0.00) | PASS |
| Every unexplained entry surfaced (100%, 0 silently matched) | PASS |
| Bank-detail changes to a person (100% of 5) | PASS |
| Handles at least 50% by itself (76%) | PASS |
| **Overall** | **PASS** |

## By category

| Category | Correct | n | Accuracy |
|---|---|---|---|
| bank_charges | 1 | 1 | 100.0% |
| clubbed_payment | 21 | 24 | 87.5% |
| duplicate_credit | 4 | 4 | 100.0% |
| full_payment | 102 | 108 | 94.4% |
| interest_credit | 1 | 1 | 100.0% |
| short_payment | 10 | 10 | 100.0% |
| supplier_payment | 4 | 4 | 100.0% |
| tds_deduction | 18 | 21 | 85.7% |
| unknown_party | 4 | 4 | 100.0% |

## Error types

| Type | Count |
|---|---|
| wrong_party | 10 |
| not_retrieved | 2 |
