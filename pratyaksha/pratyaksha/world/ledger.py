"""Read-only view of a generated world, with the no-look-ahead rule built in.

`Ledger.open_invoices(entry)` returns only invoices that existed on the entry's
date and were not yet settled by an *earlier* bank entry. A system can never
see the future, so results are not flattered by hindsight.
"""
from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path


@dataclass(frozen=True)
class Entry:
    entry_id: str
    value_date: date
    narration: str
    credit: float
    debit: float
    split: str

    @property
    def amount(self) -> float:
        return self.credit if self.credit else -self.debit

    def as_dict(self) -> dict:
        return {"entry_id": self.entry_id, "value_date": self.value_date.isoformat(),
                "narration": self.narration, "credit": self.credit, "debit": self.debit}


class Ledger:
    def __init__(self, root: str | Path, condition: str = "clean"):
        root = Path(root)
        assert condition in ("clean", "stress")
        self.root, self.condition = root, condition
        self.meta = json.loads((root / "meta.json").read_text())
        self.customers = {r["customer_id"]: {**r, "aliases": r["aliases"].split("|"),
                                             "tds_rate": float(r["tds_rate"])}
                          for r in _csv(root / "customers.csv")}
        self.suppliers = {r["supplier_id"]: r for r in _csv(root / "suppliers.csv")}
        self.invoices = {}
        for r in _csv(root / "invoices.csv"):
            for k in ("taxable_value", "gst_rate", "cgst", "sgst", "igst", "total"):
                r[k] = float(r[k])
            r["invoice_date"] = date.fromisoformat(r["invoice_date"])
            self.invoices[r["invoice_id"]] = r
        col = "narration" if condition == "clean" else "narration_stress"
        self.entries = [Entry(r["entry_id"], date.fromisoformat(r["value_date"]), r[col],
                              float(r["credit"]), float(r["debit"]), r["split"])
                        for r in _csv(root / "bank_statement.csv")]
        self.gold = {g["entry_id"]: g for g in map(json.loads, open(root / "gold.jsonl"))}
        self.remittances = [json.loads(l) for l in open(root / "remittances.jsonl")]
        self._remit_by_id = {r["remittance_id"]: r for r in self.remittances}
        self._index = {e.entry_id: i for i, e in enumerate(self.entries)}
        self._settle_log = self._build_settlements()

    # -- settlement history (what the books knew before each entry) --------
    def _build_settlements(self):
        """For each entry index, the outstanding amount of every invoice touched up to it."""
        log = []
        for e in self.entries:
            g = self.gold[e.entry_id]
            if g["category"] in ("full_payment", "clubbed_payment", "tds_deduction"):
                log.append((e.value_date, e.entry_id, {i: 0.0 for i in g["invoice_ids"]}))
            elif g["category"] == "short_payment":
                log.append((e.value_date, e.entry_id, {g["invoice_ids"][0]: g["residual"]}))
            else:
                log.append((e.value_date, e.entry_id, {}))
        return log

    def outstanding_before(self, entry: Entry) -> dict[str, float]:
        """Outstanding amount per invoice using only entries strictly before this one."""
        out = {}
        stop = self._index[entry.entry_id]
        for _, _, changes in self._settle_log[:stop]:
            out.update(changes)
        return out

    def open_invoices(self, entry: Entry, customer_ids: list[str] | None = None) -> list[dict]:
        paid = self.outstanding_before(entry)
        res = []
        for inv in self.invoices.values():
            if inv["invoice_date"] > entry.value_date:
                continue
            if customer_ids is not None and inv["customer_id"] not in customer_ids:
                continue
            outstanding = paid.get(inv["invoice_id"], inv["total"])
            if outstanding <= 0.005:
                continue
            res.append({**inv, "outstanding": outstanding})
        return res

    def remittances_near(self, entry: Entry, days: int = 5) -> list[dict]:
        """Remittance e-mails received within `days` before (or on) the entry date."""
        out = []
        for r in self.remittances:
            d = date.fromisoformat(r["received"])
            if 0 <= (entry.value_date - d).days <= days:
                out.append(r)
        return out

    def split(self, name: str) -> list[Entry]:
        return [e for e in self.entries if e.split == name]

    def restricted_values(self) -> set[str]:
        """Bank account numbers: must never appear in a system's output."""
        vals = {c["account_no"] for c in self.customers.values()}
        vals |= {s["account_no"] for s in self.suppliers.values()}
        return vals


def _csv(p: Path) -> list[dict]:
    with open(p, encoding="utf-8") as f:
        return list(csv.DictReader(f))
