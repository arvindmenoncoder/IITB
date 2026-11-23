# Scorecard: R5_r5_lora_0.8b · test · stress

Run `20261123-105510_R5_r5_lora_0.8b_test_stress` · n = 185

| Metric | Value |
|---|---|
| Accuracy (strict) | 89.2% |
| Handled automatically | 78.9% |
| Error rate on automatic | 0.00% |
| Latency p50 / p95 | 338.5 ms / 387.7 ms |
| ₹ per 1,000 tasks (operating) | 2.8814 |
| ₹ per 1,000 tasks (hardware amortisation) | 0.0000 |
| Tokens in / out per task | 513 / 14 |
| Data leaving the machine | 0 bytes |
| Restricted-field leaks | 0 |
| Right party among retrieved | 91.6% |
| Model output unreadable (parse errors) | 0 |
| Right answer among computed options | 90.3% |

## Business acceptance bar

| Rule | Result |
|---|---|
| Automatic entries ≤ 1% wrong (0.00%) | PASS |
| Misbooked rupees ≤ ₹1,000 (₹0.00) | PASS |
| Every unexplained entry surfaced (100%, 0 silently matched) | PASS |
| Bank-detail changes to a person (86% of 7) | FAIL |
| Handles at least 50% by itself (79%) | PASS |
| **Overall** | **FAIL** |

## By category

| Category | Correct | n | Accuracy |
|---|---|---|---|
| bank_charges | 1 | 1 | 100.0% |
| clubbed_payment | 22 | 26 | 84.6% |
| full_payment | 110 | 118 | 93.2% |
| interest_credit | 1 | 1 | 100.0% |
| short_payment | 9 | 14 | 64.3% |
| supplier_payment | 4 | 4 | 100.0% |
| tds_deduction | 13 | 16 | 81.2% |
| unknown_party | 5 | 5 | 100.0% |

## Error types

| Type | Count |
|---|---|
| wrong_party | 19 |
| wrong_invoices | 1 |
