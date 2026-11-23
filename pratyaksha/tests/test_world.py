"""Gold answers must be provably consistent with the records they came from."""
import json
from pathlib import Path

import pytest

from pratyaksha.world.generate import generate, write, CATEGORIES
from pratyaksha.world.ledger import Ledger
from pratyaksha.harness.scoring import is_correct, summarise


@pytest.fixture(scope="module")
def led(tmp_path_factory):
    d = tmp_path_factory.mktemp("w")
    write(generate(seed=11, n_customers=30, months=3), d)
    return Ledger(d)


def test_deterministic(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    write(generate(seed=3, n_customers=10, months=2), a)
    write(generate(seed=3, n_customers=10, months=2), b)
    for f in ("gold.jsonl", "bank_statement.csv", "invoices.csv"):
        assert (a / f).read_text() == (b / f).read_text()


def test_balance_replays(led):
    bal = led.meta["opening_balance"]
    for e in led.entries:
        bal = round(bal + e.credit - e.debit, 2)
    assert abs(bal - led.meta["closing_balance"]) < 0.01


def test_gold_amounts_add_up(led):
    for e in led.entries:
        g = led.gold[e.entry_id]
        assert g["category"] in CATEGORIES
        inv = [led.invoices[i] for i in g["invoice_ids"]]
        total = round(sum(i["total"] for i in inv), 2)
        if g["category"] in ("full_payment", "clubbed_payment"):
            assert abs(total - e.credit) < 0.01
            assert len(inv) == (1 if g["category"] == "full_payment" else len(inv)) and len(inv) >= 1
        elif g["category"] == "tds_deduction":
            assert abs(total - g["tds_amount"] - e.credit) < 0.01 and g["tds_amount"] > 0
        elif g["category"] == "short_payment":
            assert abs(total - g["residual"] - e.credit) < 0.01 and g["residual"] > 0
        else:
            assert not g["invoice_ids"]


def test_invoices_belong_to_party_and_predate_payment(led):
    for e in led.entries:
        g = led.gold[e.entry_id]
        for i in g["invoice_ids"]:
            inv = led.invoices[i]
            assert inv["customer_id"] == g["party_id"]
            assert inv["invoice_date"] <= e.value_date


def test_no_look_ahead(led):
    """Gold invoices must be visible (open) to a system at the entry's date."""
    for e in led.entries:
        g = led.gold[e.entry_id]
        if g["invoice_ids"]:
            open_ids = {i["invoice_id"] for i in led.open_invoices(e, [g["party_id"]])}
            assert set(g["invoice_ids"]) <= open_ids, e.entry_id
        for inv in led.open_invoices(e):
            assert inv["invoice_date"] <= e.value_date


def test_each_invoice_settled_at_most_once(led):
    seen = {}
    for e in led.entries:
        g = led.gold[e.entry_id]
        if g["category"] in ("full_payment", "clubbed_payment", "tds_deduction", "short_payment"):
            for i in g["invoice_ids"]:
                assert i not in seen, (i, seen.get(i), e.entry_id)
                seen[i] = e.entry_id


def test_review_flags(led):
    for g in led.gold.values():
        if g["category"] in ("duplicate_credit", "unknown_party"):
            assert g["needs_review"] and not g["explained"]


def test_gold_scores_perfectly(led):
    rows = [{"pred": {**g, "steps": []}, "gold": g, "entry": e.as_dict(), "seconds": 0.0,
             "cost": {"operating_inr": 0.0, "amortisation_inr": 0.0}}
            for e in led.entries for g in [led.gold[e.entry_id]]]
    s = summarise(rows, led.restricted_values())
    assert s["accuracy"] == 1.0 and s["acceptance"]["passes"]


def test_strict_scoring():
    g = {"category": "clubbed_payment", "party_id": "C1", "invoice_ids": ["a", "b"]}
    assert is_correct({"category": "clubbed_payment", "party_id": "C1", "invoice_ids": ["b", "a"]}, g)
    assert not is_correct({"category": "clubbed_payment", "party_id": "C1", "invoice_ids": ["a"]}, g)
    assert not is_correct({"category": "full_payment", "party_id": "C1", "invoice_ids": ["a", "b"]}, g)
