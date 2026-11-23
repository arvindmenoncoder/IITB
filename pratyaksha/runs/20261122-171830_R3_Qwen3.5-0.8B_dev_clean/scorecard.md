# Scorecard: R3_Qwen3.5-0.8B · dev · clean

Run `20261122-171830_R3_Qwen3.5-0.8B_dev_clean` · n = 177

| Metric | Value |
|---|---|
| Accuracy (strict) | 63.8% |
| Handled automatically | 57.1% |
| Error rate on automatic | 0.00% |
| Latency p50 / p95 | 751.2 ms / 892.3 ms |
| ₹ per 1,000 tasks (operating) | 6.2698 |
| ₹ per 1,000 tasks (hardware amortisation) | 0.0000 |
| Tokens in / out per task | 526 / 42 |
| Data leaving the machine | 0 bytes |
| Restricted-field leaks | 0 |
| Right party among retrieved | 95.9% |
| Model output unreadable (parse errors) | 4 |
| Right answer among computed options | 94.4% |

## Business acceptance bar

| Rule | Result |
|---|---|
| Automatic entries ≤ 1% wrong (0.00%) | PASS |
| Misbooked rupees ≤ ₹1,000 (₹0.00) | PASS |
| Every unexplained entry surfaced (100%, 0 silently matched) | PASS |
| Bank-detail changes to a person (20% of 5) | FAIL |
| Handles at least 50% by itself (57%) | PASS |
| **Overall** | **FAIL** |

## By category

| Category | Correct | n | Accuracy |
|---|---|---|---|
| bank_charges | 0 | 1 | 0.0% |
| clubbed_payment | 10 | 24 | 41.7% |
| duplicate_credit | 3 | 4 | 75.0% |
| full_payment | 80 | 108 | 74.1% |
| interest_credit | 0 | 1 | 0.0% |
| short_payment | 2 | 10 | 20.0% |
| supplier_payment | 4 | 4 | 100.0% |
| tds_deduction | 11 | 21 | 52.4% |
| unknown_party | 3 | 4 | 75.0% |

## Error types

| Type | Count |
|---|---|
| wrong_party | 48 |
| wrong_invoices | 4 |
| system_error | 4 |
| not_retrieved | 4 |
| wrong_category | 4 |
