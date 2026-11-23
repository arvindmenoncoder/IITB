# Scorecard: R5_r5_lora_0.8b · dev · stress

Run `20261123-041237_R5_r5_lora_0.8b_dev_stress` · n = 177

| Metric | Value |
|---|---|
| Accuracy (strict) | 93.2% |
| Handled automatically | 81.9% |
| Error rate on automatic | 0.00% |
| Latency p50 / p95 | 352.6 ms / 398.1 ms |
| ₹ per 1,000 tasks (operating) | 3.0057 |
| ₹ per 1,000 tasks (hardware amortisation) | 0.0000 |
| Tokens in / out per task | 527 / 15 |
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
| Bank-detail changes to a person (60% of 5) | FAIL |
| Handles at least 50% by itself (82%) | PASS |
| **Overall** | **FAIL** |

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
| tds_deduction | 19 | 21 | 90.5% |
| unknown_party | 3 | 4 | 75.0% |

## Error types

| Type | Count |
|---|---|
| wrong_party | 11 |
| wrong_invoices | 1 |
