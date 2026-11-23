"""Scoring rules and the business acceptance bar for T1 (bank reconciliation).

An entry is correct only if the category is right, the party is right (where
there is one) and the matched invoice set is exactly right -- the same strict
rule we use on BenchRec ("every invoice it is matched to is right").
"""
from __future__ import annotations

import statistics
from collections import Counter, defaultdict

INVOICE_CATS = {"full_payment", "clubbed_payment", "tds_deduction", "short_payment"}
PARTY_CATS = INVOICE_CATS | {"supplier_payment"}

# Provisional acceptance bar (mid-sem report, section 3). Freeze before the test run.
ACCEPTANCE = {
    "max_auto_error_rate": 0.01,       # auto-handled entries: <= 1% wrong
    "cash_tolerance_inr": 1_000.0,     # collected-receivables position within ₹1,000
    "unexplained_surfaced": 1.0,       # every unexplained entry goes to a person
    "bank_change_to_human": 1.0,       # every bank-detail change goes to a person
    "min_auto_rate": 0.50,             # must handle at least half by itself (added 22 Nov: see WHAT_DIDNT_WORK)
}


def is_correct(pred: dict, gold: dict) -> bool:
    if pred.get("category") != gold["category"]:
        return False
    if gold["category"] in PARTY_CATS and pred.get("party_id") != gold["party_id"]:
        return False
    return set(pred.get("invoice_ids") or []) == set(gold["invoice_ids"])


def error_type(pred: dict, gold: dict) -> str | None:
    """Error taxonomy agreed at mid-sem."""
    if is_correct(pred, gold):
        return None
    if pred.get("error"):
        return "system_error"            # parse failure / timeout
    gold_inv = set(gold["invoice_ids"])
    retrieved = pred.get("retrieved_invoice_ids") or []
    if gold["category"] in PARTY_CATS and pred.get("party_id") not in (None, gold["party_id"]):
        return "wrong_party"
    if gold_inv and retrieved:
        if not gold_inv <= set(retrieved):
            return "not_retrieved"       # right record not found
        if not gold_inv <= set(retrieved[:5]):
            return "ranked_too_low"      # found but ranked too low
    if gold["category"] in PARTY_CATS and pred.get("party_id") != gold["party_id"]:
        return "wrong_party"
    if set(pred.get("invoice_ids") or []) != gold_inv:
        return "wrong_invoices"          # right evidence, wrong final answer
    return "wrong_category"


def pct(xs, q):
    if not xs:
        return 0.0
    xs = sorted(xs)
    k = (len(xs) - 1) * q
    lo, hi = int(k), min(int(k) + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


def summarise(rows: list[dict], restricted: set[str] | None = None) -> dict:
    """rows: [{'pred': {...}, 'gold': {...}, 'entry': {...}, 'seconds': float, 'cost': {...}}]"""
    n = len(rows)
    correct = [is_correct(r["pred"], r["gold"]) for r in rows]
    auto = [not r["pred"].get("needs_review") for r in rows]
    auto_n = sum(auto)
    auto_wrong = sum(1 for c, a in zip(correct, auto) if a and not c)

    unexplained = [r for r in rows if not r["gold"]["explained"]]
    surfaced = sum(1 for r in unexplained if r["pred"].get("needs_review"))
    silent = sum(1 for r in unexplained
                 if not r["pred"].get("needs_review") and r["pred"].get("invoice_ids"))
    bank_change = [r for r in rows if r["gold"].get("bank_detail_change")]
    bank_change_ok = sum(1 for r in bank_change if r["pred"].get("needs_review"))

    # Cash gap: rupees the system booked wrongly *without* a person seeing them.
    # Entries sent to review are pending, not wrong, so they do not count.
    cash_gap = sum(abs(r["entry"]["credit"] or r["entry"]["debit"])
                   for r, c, a in zip(rows, correct, auto) if a and not c)

    secs = [r["seconds"] for r in rows]
    op = sum(r["cost"]["operating_inr"] for r in rows)
    am = sum(r["cost"]["amortisation_inr"] for r in rows)
    egress = sum(s.get("bytes_out", 0) for r in rows for s in r["pred"].get("steps", []) if not s.get("local", True))
    tin = sum(s.get("tokens_in", 0) for r in rows for s in r["pred"].get("steps", []))
    tout = sum(s.get("tokens_out", 0) for r in rows for s in r["pred"].get("steps", []))

    leaks = 0
    if restricted:
        for r in rows:
            txt = (r["pred"].get("raw_output") or "") + (r["pred"].get("explanation") or "")
            leaks += sum(1 for v in restricted if v in txt)

    by_cat = defaultdict(lambda: [0, 0])
    for r, c in zip(rows, correct):
        by_cat[r["gold"]["category"]][0] += c
        by_cat[r["gold"]["category"]][1] += 1
    errors = Counter(e for e in (error_type(r["pred"], r["gold"]) for r in rows) if e)

    with_party = [r for r in rows if r["gold"].get("party_id") and r["pred"].get("retrieved_party_ids")]
    party_recall = (sum(1 for r in with_party if r["gold"]["party_id"] in r["pred"]["retrieved_party_ids"])
                    / len(with_party)) if with_party else None
    parse_errors = sum(1 for r in rows if r["pred"].get("error"))
    with_opts = [r for r in rows if r["pred"].get("options")]
    option_recall = (sum(1 for r in with_opts if any(is_correct(o, r["gold"]) for o in r["pred"]["options"]))
                     / len(with_opts)) if with_opts else None

    auto_err = auto_wrong / auto_n if auto_n else 0.0
    s = {
        "n": n,
        "accuracy": sum(correct) / n if n else 0.0,
        "auto_rate": auto_n / n if n else 0.0,
        "auto_error_rate": auto_err,
        "unexplained_total": len(unexplained),
        "unexplained_surfaced": surfaced / len(unexplained) if unexplained else 1.0,
        "unexplained_silently_matched": silent,
        "bank_change_total": len(bank_change),
        "bank_change_to_human": bank_change_ok / len(bank_change) if bank_change else 1.0,
        "cash_gap_inr": round(cash_gap, 2),
        "latency_p50_s": pct(secs, 0.5),
        "latency_p95_s": pct(secs, 0.95),
        "inr_per_1000_operating": op / n * 1000 if n else 0.0,
        "inr_per_1000_amortisation": am / n * 1000 if n else 0.0,
        "tokens_in_per_task": tin / n if n else 0.0,
        "tokens_out_per_task": tout / n if n else 0.0,
        "egress_bytes_total": egress,
        "restricted_leaks": leaks,
        "party_recall": party_recall,
        "parse_errors": parse_errors,
        "option_recall": option_recall,
        "by_category": {k: {"correct": v[0], "n": v[1], "acc": v[0] / v[1]} for k, v in sorted(by_cat.items())},
        "errors": dict(errors.most_common()),
    }
    s["acceptance"] = {
        "auto_error_ok": auto_err <= ACCEPTANCE["max_auto_error_rate"],
        "cash_ok": cash_gap <= ACCEPTANCE["cash_tolerance_inr"],
        "unexplained_ok": s["unexplained_surfaced"] >= ACCEPTANCE["unexplained_surfaced"] and silent == 0,
        "bank_change_ok": s["bank_change_to_human"] >= ACCEPTANCE["bank_change_to_human"],
        "useful_ok": s["auto_rate"] >= ACCEPTANCE["min_auto_rate"],
    }
    s["acceptance"]["passes"] = all(s["acceptance"].values())
    return s
