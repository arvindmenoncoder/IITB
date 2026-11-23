# Scorecard: R6_laya_laya_t1 · test · stress

Run `20261123-203433_R6_laya_laya_t1_test_stress_mac` · n = 185

| Metric | Value |
|---|---|
| Accuracy (strict) | 88.6% |
| Handled automatically | 75.1% |
| Error rate on automatic | 0.00% |
| Latency p50 / p95 | 271.3 ms / 346.4 ms |
| ₹ per 1,000 tasks (operating) | 0.0215 |
| ₹ per 1,000 tasks (hardware amortisation) | 2.2380 |
| Tokens in / out per task | 0 / 0 |
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
| Bank-detail changes to a person (100% of 7) | PASS |
| Handles at least 50% by itself (75%) | PASS |
| **Overall** | **PASS** |

## By category

| Category | Correct | n | Accuracy |
|---|---|---|---|
| bank_charges | 1 | 1 | 100.0% |
| clubbed_payment | 22 | 26 | 84.6% |
| full_payment | 110 | 118 | 93.2% |
| interest_credit | 1 | 1 | 100.0% |
| short_payment | 8 | 14 | 57.1% |
| supplier_payment | 4 | 4 | 100.0% |
| tds_deduction | 13 | 16 | 81.2% |
| unknown_party | 5 | 5 | 100.0% |

## Error types

| Type | Count |
|---|---|
| wrong_party | 16 |
| not_retrieved | 4 |
| wrong_invoices | 1 |
