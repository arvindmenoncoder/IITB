"""WWI-IN: a generated, India-localised MSME world for bank reconciliation (task T1).

The world is modelled on Microsoft's Wide World Importers sample (a wholesale
distributor with customers, invoices and payments), localised to India:
rupees, GST 2.0 slabs (5% / 18%), GSTINs, Indian firm names, NEFT/RTGS/IMPS/UPI/
cheque narrations, TDS deductions and remittance e-mails.

Every gold answer is computed from the generator's own records, never written
by hand. Output (in --out):

    customers.csv   suppliers.csv   invoices.csv
    bank_statement.csv   remittances.jsonl   gold.jsonl   meta.json

Gold per bank entry:
    category, party_id, invoice_ids, tds_amount, residual, needs_review, explained
"""
from __future__ import annotations

import argparse
import csv
import json
import random
from dataclasses import dataclass, field, asdict
from datetime import date, timedelta
from pathlib import Path

from . import names as N
from .narration import make_narration

CATEGORIES = [
    "full_payment",      # one invoice, exact amount
    "clubbed_payment",   # 2+ invoices, exact sum
    "tds_deduction",     # 1+ invoices, sum minus TDS on taxable value
    "short_payment",     # 1 invoice, paid less, residual stays open
    "duplicate_credit",  # bank posted the same credit twice
    "unknown_party",     # payer not in customer master
    "bank_charges",      # debit: bank fee
    "interest_credit",   # credit: bank interest
    "supplier_payment",  # debit: payment to a known supplier
]
REVIEW_CATEGORIES = {"duplicate_credit", "unknown_party"}
COMPANY_STATE = "29"  # Karnataka
TDS_RATES = [0.001, 0.01, 0.02]  # 194Q, 194C (indiv.), 194C (others)


@dataclass
class Customer:
    customer_id: str
    legal_name: str
    aliases: list
    gstin: str
    state_code: str
    city: str
    habit: str
    tds_rate: float
    group_id: str
    bank: str
    account_no: str  # restricted field


@dataclass
class Invoice:
    invoice_id: str
    customer_id: str
    invoice_date: date
    due_date: date
    taxable_value: float
    gst_rate: float
    cgst: float
    sgst: float
    igst: float
    total: float


@dataclass
class BankEntry:
    entry_id: str
    value_date: date
    narration: str
    narration_stress: str
    credit: float
    debit: float
    balance: float = 0.0
    gold: dict = field(default_factory=dict)


def r2(x: float) -> float:
    return round(x + 1e-9, 2)


def gstin(rng: random.Random, state: str) -> str:
    L = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    pan = "".join(rng.choice(L) for _ in range(5)) + f"{rng.randint(0, 9999):04d}" + rng.choice(L)
    return f"{state}{pan}1Z{rng.choice(L + '0123456789')}"


def build_customers(rng: random.Random, n: int) -> list[Customer]:
    habits = (["prompt"] * 6 + ["clubber"] * 3 + ["tds_deductor"] * 4 +
              ["short_payer"] * 2 + ["upi_payer"] * 2 + ["late"] * 3)
    used, out = set(), []
    groups = 0
    for i in range(n):
        while True:
            base, suffix = rng.choice(N.FIRST), rng.choice(N.SUFFIX)
            legal = f"{base} {suffix}"
            if legal not in used:
                used.add(legal)
                break
        state, city = rng.choice(N.STATES)
        habit = rng.choice(habits)
        # every ~8th customer gets a sister firm that sometimes pays for it
        gid = f"G{i:03d}"
        if i > 0 and i % 8 == 0:
            gid = out[-1].group_id
            groups += 1
        out.append(Customer(
            customer_id=f"C{i + 1:03d}", legal_name=legal,
            aliases=N.aliases_for(rng, base, suffix), gstin=gstin(rng, state),
            state_code=state, city=city, habit=habit,
            tds_rate=rng.choice(TDS_RATES) if habit == "tds_deductor" else 0.0,
            group_id=gid, bank=rng.choice(N.BANKS),
            account_no=str(rng.randint(10 ** 10, 10 ** 12 - 1)),
        ))
    return out


def make_invoice(rng, k: int, c: Customer, d: date) -> Invoice:
    taxable = r2(rng.choice([rng.uniform(8_000, 60_000), rng.uniform(60_000, 4_00_000)]))
    taxable = float(round(taxable))  # whole rupees, as most MSME bills
    rate = rng.choice([0.05, 0.18, 0.18])
    if c.state_code == COMPANY_STATE:
        cgst = sgst = r2(taxable * rate / 2)
        igst = 0.0
    else:
        cgst = sgst = 0.0
        igst = r2(taxable * rate)
    return Invoice(f"WWI/26-27/{k:05d}", c.customer_id, d, d + timedelta(days=30),
                   taxable, rate, cgst, sgst, igst, r2(taxable + cgst + sgst + igst))


def generate(seed: int = 7, n_customers: int = 60, months: int = 6,
             start: date = date(2026, 4, 1)) -> dict:
    rng = random.Random(seed)
    customers = build_customers(rng, n_customers)
    cust = {c.customer_id: c for c in customers}
    suppliers = [{"supplier_id": f"S{i + 1:02d}", "name": nm, "bank": rng.choice(N.BANKS),
                  "account_no": str(rng.randint(10 ** 10, 10 ** 12 - 1))}
                 for i, nm in enumerate(N.SUPPLIERS)]
    end = start + timedelta(days=30 * months)

    # ---- invoices -------------------------------------------------------
    invoices, k, d = [], 1, start
    while d < end:
        for c in customers:
            if rng.random() < 0.13:  # ~4 invoices per customer per month
                invoices.append(make_invoice(rng, k, c, d))
                k += 1
        d += timedelta(days=1)

    # ---- payments (customer credits) -------------------------------------
    events = []  # (date, kind, payload)
    by_cust: dict[str, list[Invoice]] = {}
    for inv in invoices:
        by_cust.setdefault(inv.customer_id, []).append(inv)

    remit_id = 0
    remittances = []
    for cid, invs in by_cust.items():
        c = cust[cid]
        invs.sort(key=lambda x: x.invoice_date)
        i = 0
        while i < len(invs):
            inv = invs[i]
            lag = {"prompt": (5, 25), "late": (35, 70)}.get(c.habit, (10, 40))
            pay_date = inv.invoice_date + timedelta(days=rng.randint(*lag))
            if pay_date >= end or rng.random() < 0.06:  # stays open at period end
                i += 1
                continue
            group = [inv]
            if c.habit == "clubber" or rng.random() < 0.12:
                j = i + 1
                while (j < len(invs) and len(group) < rng.choice([2, 2, 3, 4])
                       and invs[j].invoice_date < pay_date - timedelta(days=2)):
                    group.append(invs[j])
                    j += 1
            i += len(group)
            total = r2(sum(g.total for g in group))
            taxable = sum(g.taxable_value for g in group)
            tds, residual, cat, reason = 0.0, 0.0, None, ""
            if c.tds_rate and rng.random() < 0.85:
                tds = float(round(taxable * c.tds_rate))  # TDS on value excl. GST, rounded
                amount, cat = r2(total - tds), "tds_deduction"
            elif c.habit == "short_payer" and len(group) == 1 and rng.random() < 0.6:
                pct = rng.choice([0.01, 0.02, 0.03, 0.05])
                residual = float(round(total * pct))
                amount, cat = r2(total - residual), "short_payment"
                reason = rng.choice(["cash discount", "rate difference", "damaged goods", ""])
            else:
                amount = total
                cat = "full_payment" if len(group) == 1 else "clubbed_payment"
            payer = c
            if rng.random() < 0.12:  # sister firm pays (GraphRAG probe case)
                sis = [x for x in customers if x.group_id == c.group_id and x.customer_id != cid]
                if sis:
                    payer = sis[0]
            mode = "UPI" if c.habit == "upi_payer" and amount < 1_00_000 else \
                rng.choice(["NEFT", "NEFT", "RTGS" if amount >= 2_00_000 else "NEFT", "IMPS", "CHQ"])
            ref_invoice = group[0].invoice_id if rng.random() < 0.45 else ""
            gold = {"category": cat, "party_id": cid,
                    "invoice_ids": [g.invoice_id for g in group],
                    "tds_amount": tds, "residual": residual,
                    "paid_by": payer.customer_id,
                    "explained": cat != "short_payment" or bool(reason),
                    "short_reason": reason}
            gold["needs_review"] = not gold["explained"]  # unexplained -> a person decides
            ev = {"date": pay_date, "kind": "customer", "amount": amount, "payer": payer,
                  "mode": mode, "ref_invoice": ref_invoice, "gold": gold}
            # remittance advice for ~55% of payments
            if rng.random() < 0.55:
                remit_id += 1
                bank_change = rng.random() < 0.03
                body = N.remittance_body(rng, c, group, amount, tds, reason, mode,
                                         bank_change=bank_change)
                remittances.append({"remittance_id": f"R{remit_id:04d}",
                                    "received": (pay_date - timedelta(days=rng.randint(0, 2))).isoformat(),
                                    "from": N.email_for(c), "body": body,
                                    "bank_detail_change": bank_change})
                gold["remittance_id"] = f"R{remit_id:04d}"
                gold["bank_detail_change"] = bank_change
                if bank_change:
                    gold["needs_review"] = True
            events.append(ev)

    # ---- duplicates, unknown parties, bank charges, interest, suppliers ----
    cust_events = [e for e in events if e["kind"] == "customer"]
    for e in rng.sample(cust_events, k=max(3, len(cust_events) // 60)):
        events.append({**e, "date": e["date"] + timedelta(days=rng.randint(0, 1)),
                       "kind": "duplicate", "of": e})
    for _ in range(max(4, len(cust_events) // 45)):
        nm = rng.choice(N.UNKNOWN_PAYERS)
        events.append({"date": start + timedelta(days=rng.randint(5, 30 * months - 1)),
                       "kind": "unknown", "amount": float(rng.randint(2_000, 90_000)),
                       "name": nm, "mode": rng.choice(["NEFT", "IMPS", "UPI"])})
    m = start
    while m < end:
        events.append({"date": m + timedelta(days=rng.randint(25, 28)), "kind": "charges",
                       "amount": float(rng.choice([118, 236, 354, 590]))})
        events.append({"date": m + timedelta(days=rng.randint(27, 29)), "kind": "interest",
                       "amount": r2(rng.uniform(300, 2500))})
        for s in rng.sample(suppliers, k=4):
            events.append({"date": m + timedelta(days=rng.randint(1, 28)), "kind": "supplier",
                           "amount": float(rng.randint(40_000, 6_00_000)), "supplier": s,
                           "mode": rng.choice(["NEFT", "RTGS"])})
        m += timedelta(days=30)

    events = [e for e in events if e["date"] < end]
    events.sort(key=lambda e: (e["date"], e.get("amount", 0)))

    # ---- bank statement -------------------------------------------------
    opening = 25_00_000.00
    bal, entries = opening, []
    orig_entry_of = {}
    for n, e in enumerate(events, 1):
        eid = f"B{n:05d}"
        kind = e["kind"]
        credit = debit = 0.0
        if kind in ("customer", "duplicate"):
            credit = e["amount"]
            narr, narr_s = make_narration(rng, e["mode"], e["payer"].legal_name,
                                          e["payer"].aliases, e["payer"].bank,
                                          e["ref_invoice"], e["date"])
            if kind == "customer":
                gold = dict(e["gold"])
                orig_entry_of[id(e)] = eid
            else:
                gold = {"category": "duplicate_credit", "party_id": e["gold"]["party_id"],
                        "invoice_ids": [], "tds_amount": 0.0, "residual": 0.0,
                        "duplicate_of": orig_entry_of.get(id(e["of"])),
                        "explained": False, "needs_review": True}
        elif kind == "unknown":
            credit = e["amount"]
            narr, narr_s = make_narration(rng, e["mode"], e["name"], [], rng.choice(N.BANKS), "", e["date"])
            gold = {"category": "unknown_party", "party_id": None, "invoice_ids": [],
                    "tds_amount": 0.0, "residual": 0.0, "explained": False, "needs_review": True}
        elif kind == "charges":
            debit = e["amount"]
            narr = narr_s = rng.choice(["SMS CHGS INCL GST", "NEFT CHGS INCL GST", "ACCT MAINT CHG+GST"])
            gold = {"category": "bank_charges", "party_id": None, "invoice_ids": [],
                    "tds_amount": 0.0, "residual": 0.0, "explained": True, "needs_review": False}
        elif kind == "interest":
            credit = e["amount"]
            narr = narr_s = "INT.PD:" + e["date"].strftime("%d-%m-%Y")
            gold = {"category": "interest_credit", "party_id": None, "invoice_ids": [],
                    "tds_amount": 0.0, "residual": 0.0, "explained": True, "needs_review": False}
        else:  # supplier
            debit = e["amount"]
            s = e["supplier"]
            narr, narr_s = make_narration(rng, e["mode"], s["name"], [], s["bank"], "", e["date"],
                                          outward=True)
            gold = {"category": "supplier_payment", "party_id": s["supplier_id"], "invoice_ids": [],
                    "tds_amount": 0.0, "residual": 0.0, "explained": True, "needs_review": False}
        bal = r2(bal + credit - debit)
        gold["entry_id"] = eid
        entries.append(BankEntry(eid, e["date"], narr, narr_s, credit, debit, bal, gold))

    month0 = start.month
    split_of = lambda d: ("test" if (d - start).days >= 30 * (months - 1)
                          else "dev" if (d - start).days >= 30 * (months - 2) else "train")
    meta = {"seed": seed, "start": start.isoformat(), "end": end.isoformat(),
            "opening_balance": opening, "closing_balance": bal,
            "company": "Wide World Importers India Pvt Ltd", "company_state": COMPANY_STATE,
            "categories": CATEGORIES,
            "counts": {"customers": len(customers), "suppliers": len(suppliers),
                       "invoices": len(invoices), "bank_entries": len(entries),
                       "remittances": len(remittances)}}
    return {"customers": customers, "suppliers": suppliers, "invoices": invoices,
            "entries": entries, "remittances": remittances, "meta": meta, "split_of": split_of}


def write(world: dict, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)

    def dump(name, rows, fields):
        with open(out / name, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            for r in rows:
                w.writerow({k: r[k] for k in fields})

    cust_rows = []
    for c in world["customers"]:
        d = asdict(c)
        d["aliases"] = "|".join(c.aliases)
        cust_rows.append(d)
    dump("customers.csv", cust_rows, list(cust_rows[0].keys()))
    dump("suppliers.csv", world["suppliers"], list(world["suppliers"][0].keys()))
    inv_rows = []
    for i in world["invoices"]:
        d = asdict(i)
        d["invoice_date"], d["due_date"] = i.invoice_date.isoformat(), i.due_date.isoformat()
        inv_rows.append(d)
    dump("invoices.csv", inv_rows, list(inv_rows[0].keys()))
    split_of = world["split_of"]
    rows = [{"entry_id": e.entry_id, "value_date": e.value_date.isoformat(),
             "narration": e.narration, "narration_stress": e.narration_stress,
             "credit": f"{e.credit:.2f}", "debit": f"{e.debit:.2f}", "balance": f"{e.balance:.2f}",
             "split": split_of(e.value_date)} for e in world["entries"]]
    dump("bank_statement.csv", rows, list(rows[0].keys()))
    with open(out / "remittances.jsonl", "w", encoding="utf-8") as f:
        for r in world["remittances"]:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(out / "gold.jsonl", "w", encoding="utf-8") as f:
        for e in world["entries"]:
            f.write(json.dumps({**e.gold, "split": split_of(e.value_date)}) + "\n")
    (out / "meta.json").write_text(json.dumps(world["meta"], indent=2))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--customers", type=int, default=60)
    ap.add_argument("--months", type=int, default=6)
    ap.add_argument("--out", default="data/wwi_in")
    a = ap.parse_args()
    w = generate(a.seed, a.customers, a.months)
    write(w, Path(a.out))
    print(json.dumps(w["meta"]["counts"]))


if __name__ == "__main__":
    main()
