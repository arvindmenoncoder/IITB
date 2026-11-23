# Scorecard: R6_Qwen3.5-2B · dev · clean

Run `20261123-092314_R6_Qwen3.5-2B_dev_clean` · n = 177

| Metric | Value |
|---|---|
| Accuracy (strict) | 89.8% |
| Handled automatically | 76.8% |
| Error rate on automatic | 0.74% |
| Latency p50 / p95 | 654.3 ms / 859.4 ms |
| ₹ per 1,000 tasks (operating) | 5.7953 |
| ₹ per 1,000 tasks (hardware amortisation) | 0.0000 |
| Tokens in / out per task | 526 / 39 |
| Data leaving the machine | 0 bytes |
| Restricted-field leaks | 0 |
| Right party among retrieved | 95.9% |
| Model output unreadable (parse errors) | 1 |
| Right answer among computed options | 94.4% |

## Business acceptance bar

| Rule | Result |
|---|---|
| Automatic entries ≤ 1% wrong (0.74%) | PASS |
| Misbooked rupees ≤ ₹1,000 (₹236.00) | PASS |
| Every unexplained entry surfaced (100%, 0 silently matched) | PASS |
| Bank-detail changes to a person (100% of 5) | PASS |
| Handles at least 50% by itself (77%) | PASS |
| **Overall** | **PASS** |

## By category

| Category | Correct | n | Accuracy |
|---|---|---|---|
| bank_charges | 0 | 1 | 0.0% |
| clubbed_payment | 21 | 24 | 87.5% |
| duplicate_credit | 2 | 4 | 50.0% |
| full_payment | 103 | 108 | 95.4% |
| interest_credit | 1 | 1 | 100.0% |
| short_payment | 7 | 10 | 70.0% |
| supplier_payment | 4 | 4 | 100.0% |
| tds_deduction | 18 | 21 | 85.7% |
| unknown_party | 3 | 4 | 75.0% |

## Error types

| Type | Count |
|---|---|
| wrong_party | 11 |
| wrong_category | 3 |
| not_retrieved | 2 |
| system_error | 1 |
| wrong_invoices | 1 |
