"""R-rules: what a careful developer writes without any AI.

Uses only the narration and the amount: fuzzy-match the payer name, then search
for an exact amount among that party's open invoices (single, sums of 2-3, and
standard TDS rates). It never reads remittance e-mails. This is the bar every
AI rung has to beat -- if it can't, that is a finding.
"""
from __future__ import annotations

import re
import time
from difflib import SequenceMatcher
from itertools import combinations

from ..harness.schema import Prediction, Step
from ..world.ledger import Entry, Ledger

TDS_RATES = (0.001, 0.01, 0.02)
CHARGES = re.compile(r"\b(CHGS?|CHARGES?|MAINT)\b")
INTEREST = re.compile(r"^INT\.?PD")
_norm = lambda s: re.sub(r"[^A-Z0-9 ]", " ", s.upper())


class RulesBaseline:
    name = "rules"

    def __init__(self, name_threshold: str | float = 0.72, max_combo: str | int = 3):
        self.th, self.max_combo = float(name_threshold), int(max_combo)
        self.config = {"name_threshold": self.th, "max_combo": self.max_combo}

    # -- name matching ------------------------------------------------------
    @staticmethod
    def _score(narr: str, name: str) -> float:
        # compare with spaces removed: UPI handles and IMPS fields drop them
        n = _norm(narr).replace(" ", "")
        t = _norm(name).replace(" ", "")
        if len(t) < 6:            # initials like "SG TRD" match too much by accident
            return 0.0
        if t in n:
            return 1.0 + len(t) / 1000   # longer exact match wins ties
        L, best = len(t), 0.0
        for i in range(0, max(1, len(n) - L + 1)):
            best = max(best, SequenceMatcher(None, n[i:i + L], t).ratio())
        # a truncated narration may hold only the start of the name
        for k in range(8, L):
            if n.endswith(t[:k]):
                best = max(best, 0.75 + 0.2 * k / L)
        return best

    def _party(self, narr: str, parties: dict) -> tuple[str | None, float]:
        best, bid = 0.0, None
        for pid, p in parties.items():
            names = [p.get("legal_name") or p.get("name")] + p.get("aliases", [])
            sc = max(self._score(narr, nm) for nm in names if nm)
            if sc > best:
                best, bid = sc, pid
        return (bid, best) if best >= self.th else (None, best)

    # -- main ---------------------------------------------------------------
    def predict(self, e: Entry, led: Ledger) -> Prediction:
        t0 = time.perf_counter()
        p = Prediction(entry_id=e.entry_id, category="unknown_party", needs_review=True)
        narr = e.narration
        if e.debit:
            if CHARGES.search(narr):
                p.category, p.needs_review = "bank_charges", False
            else:
                sid, sc = self._party(narr, led.suppliers)
                if sid:
                    p.category, p.party_id, p.needs_review, p.confidence = "supplier_payment", sid, False, sc
        elif INTEREST.search(narr):
            p.category, p.needs_review = "interest_credit", False
        else:
            cid, sc = self._party(narr, led.customers)
            p.confidence = sc
            if cid:
                p.party_id = cid
                if self._is_duplicate(e, led, cid):
                    p.category, p.party_id, p.needs_review = "duplicate_credit", cid, True
                else:
                    self._match(e, led, cid, p)
        p.steps.append(Step("rules", time.perf_counter() - t0))
        return p

    def _is_duplicate(self, e: Entry, led: Ledger, cid: str) -> bool:
        i = led._index[e.entry_id]
        for prev in led.entries[max(0, i - 40):i]:
            if (prev.credit == e.credit and (e.value_date - prev.value_date).days <= 2
                    and self._party(prev.narration, {cid: led.customers[cid]})[0] == cid):
                return True
        return False

    def _match(self, e: Entry, led: Ledger, cid: str, p: Prediction):
        amt = e.credit
        open_inv = sorted(led.open_invoices(e, [cid]), key=lambda x: x["invoice_date"])
        p.retrieved_invoice_ids = [i["invoice_id"] for i in open_inv]
        ref = next((i for i in open_inv if i["invoice_id"] in e.narration), None)
        if ref and abs(ref["outstanding"] - amt) < 0.01:
            p.category, p.invoice_ids, p.needs_review = "full_payment", [ref["invoice_id"]], False
            return
        cand = open_inv[:14]
        for k in range(1, self.max_combo + 1):
            for combo in combinations(cand, k):
                tot = round(sum(c["outstanding"] for c in combo), 2)
                if abs(tot - amt) < 0.01:
                    p.category = "full_payment" if k == 1 else "clubbed_payment"
                    p.invoice_ids, p.needs_review = [c["invoice_id"] for c in combo], False
                    return
                taxable = sum(c["taxable_value"] for c in combo)
                for r in TDS_RATES:
                    if abs(tot - round(taxable * r) - amt) < 0.01:
                        p.category, p.invoice_ids, p.needs_review = "tds_deduction", [c["invoice_id"] for c in combo], False
                        return
        # a single invoice paid a little short -> flag, don't auto-book
        for c in (([ref] if ref else []) + cand):
            if 0.94 * c["outstanding"] <= amt < c["outstanding"]:
                p.category, p.invoice_ids, p.needs_review = "short_payment", [c["invoice_id"]], True
                return
        p.category, p.needs_review = "unknown_party", True
