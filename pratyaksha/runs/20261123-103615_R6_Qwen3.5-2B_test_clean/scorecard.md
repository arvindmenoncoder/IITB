# Scorecard: R6_Qwen3.5-2B · test · clean

Run `20261123-103615_R6_Qwen3.5-2B_test_clean` · n = 185

| Metric | Value |
|---|---|
| Accuracy (strict) | 87.0% |
| Handled automatically | 73.5% |
| Error rate on automatic | 0.74% |
| Latency p50 / p95 | 684.1 ms / 776.8 ms |
| ₹ per 1,000 tasks (operating) | 5.9202 |
| ₹ per 1,000 tasks (hardware amortisation) | 0.0000 |
| Tokens in / out per task | 530 / 40 |
| Data leaving the machine | 0 bytes |
| Restricted-field leaks | 0 |
| Right party among retrieved | 93.8% |
| Model output unreadable (parse errors) | 1 |
| Right answer among computed options | 92.4% |

## Business acceptance bar

| Rule | Result |
|---|---|
| Automatic entries ≤ 1% wrong (0.74%) | PASS |
| Misbooked rupees ≤ ₹1,000 (₹590.00) | PASS |
| Every unexplained entry surfaced (100%, 0 silently matched) | PASS |
| Bank-detail changes to a person (100% of 7) | PASS |
| Handles at least 50% by itself (74%) | PASS |
| **Overall** | **PASS** |

## By category

| Category | Correct | n | Accuracy |
|---|---|---|---|
| bank_charges | 0 | 1 | 0.0% |
| clubbed_payment | 22 | 26 | 84.6% |
| full_payment | 112 | 118 | 94.9% |
| interest_credit | 0 | 1 | 0.0% |
| short_payment | 7 | 14 | 50.0% |
| supplier_payment | 4 | 4 | 100.0% |
| tds_deduction | 11 | 16 | 68.8% |
| unknown_party | 5 | 5 | 100.0% |

## Error types

| Type | Count |
|---|---|
| wrong_party | 17 |
| wrong_category | 5 |
| system_error | 1 |
| wrong_invoices | 1 |
