# Scorecard: R3_Qwen3.5-4B · dev · clean

Run `20261123-030720_R3_Qwen3.5-4B_dev_clean_nothink` · n = 177

| Metric | Value |
|---|---|
| Accuracy (strict) | 81.9% |
| Handled automatically | 70.6% |
| Error rate on automatic | 0.00% |
| Latency p50 / p95 | 1499.2 ms / 1879.4 ms |
| ₹ per 1,000 tasks (operating) | 12.8473 |
| ₹ per 1,000 tasks (hardware amortisation) | 0.0000 |
| Tokens in / out per task | 526 / 41 |
| Data leaving the machine | 0 bytes |
| Restricted-field leaks | 0 |
| Right party among retrieved | 95.9% |
| Model output unreadable (parse errors) | 0 |
| Right answer among computed options | 94.4% |

## Business acceptance bar

| Rule | Result |
|---|---|
| Automatic entries ≤ 1% wrong (0.00%) | PASS |
| Misbooked rupees ≤ ₹1,000 (₹0.00) | PASS |
| Every unexplained entry surfaced (100%, 0 silently matched) | PASS |
| Bank-detail changes to a person (100% of 5) | PASS |
| Handles at least 50% by itself (71%) | PASS |
| **Overall** | **PASS** |

## By category

| Category | Correct | n | Accuracy |
|---|---|---|---|
| bank_charges | 0 | 1 | 0.0% |
| clubbed_payment | 20 | 24 | 83.3% |
| duplicate_credit | 2 | 4 | 50.0% |
| full_payment | 91 | 108 | 84.3% |
| interest_credit | 0 | 1 | 0.0% |
| short_payment | 10 | 10 | 100.0% |
| supplier_payment | 3 | 4 | 75.0% |
| tds_deduction | 16 | 21 | 76.2% |
| unknown_party | 3 | 4 | 75.0% |

## Error types

| Type | Count |
|---|---|
| wrong_party | 22 |
| wrong_invoices | 5 |
| wrong_category | 4 |
| not_retrieved | 1 |
