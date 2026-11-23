# Scorecard: R6_Qwen3.5-2B · test · stress

Run `20261123-105653_R6_Qwen3.5-2B_test_stress` · n = 185

| Metric | Value |
|---|---|
| Accuracy (strict) | 85.4% |
| Handled automatically | 73.0% |
| Error rate on automatic | 0.74% |
| Latency p50 / p95 | 677.3 ms / 795.8 ms |
| ₹ per 1,000 tasks (operating) | 5.7638 |
| ₹ per 1,000 tasks (hardware amortisation) | 0.0000 |
| Tokens in / out per task | 513 / 40 |
| Data leaving the machine | 0 bytes |
| Restricted-field leaks | 0 |
| Right party among retrieved | 91.6% |
| Model output unreadable (parse errors) | 1 |
| Right answer among computed options | 90.3% |

## Business acceptance bar

| Rule | Result |
|---|---|
| Automatic entries ≤ 1% wrong (0.74%) | PASS |
| Misbooked rupees ≤ ₹1,000 (₹590.00) | PASS |
| Every unexplained entry surfaced (100%, 0 silently matched) | PASS |
| Bank-detail changes to a person (100% of 7) | PASS |
| Handles at least 50% by itself (73%) | PASS |
| **Overall** | **PASS** |

## By category

| Category | Correct | n | Accuracy |
|---|---|---|---|
| bank_charges | 0 | 1 | 0.0% |
| clubbed_payment | 22 | 26 | 84.6% |
| full_payment | 110 | 118 | 93.2% |
| interest_credit | 0 | 1 | 0.0% |
| short_payment | 7 | 14 | 50.0% |
| supplier_payment | 4 | 4 | 100.0% |
| tds_deduction | 10 | 16 | 62.5% |
| unknown_party | 5 | 5 | 100.0% |

## Error types

| Type | Count |
|---|---|
| wrong_party | 19 |
| wrong_category | 4 |
| not_retrieved | 3 |
| wrong_invoices | 1 |
