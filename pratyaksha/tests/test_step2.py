"""Step 2 pipeline checks on CPU (no real model): retrieval, prompts, parsing, runner."""
import json

import pytest

from pratyaksha.world.generate import generate, write
from pratyaksha.world.ledger import Ledger
from pratyaksha.retrieval.index import build_indexes, clean_query, grams
from pratyaksha.systems.llm_ladder import (R0NoRetrieval, R1RAG, R2Rerank, parse_answer, to_prediction)
from pratyaksha.harness.runner import run


@pytest.fixture(scope="module")
def led(tmp_path_factory):
    d = tmp_path_factory.mktemp("w2")
    write(generate(seed=11, n_customers=30, months=3), d)
    return Ledger(d)


def test_clean_query_strips_rail_noise():
    q = clean_query("NEFT-HDFCN123456789012-SHREE GANESH TRADERS-WWI/26-27/00011")
    assert "SHREE GANESH TRADERS" in q and "WWI" not in q and "HDFCN" not in q


def test_grams_survive_missing_spaces():
    assert set(grams("shree ganesh")) & set(grams("shreeganesh@ybl"))


def test_bm25_finds_payer_on_clean_data(led):
    cidx, _ = build_indexes(led)
    hits = total = 0
    for e in led.entries:
        g = led.gold[e.entry_id]
        if g["category"] in ("full_payment", "clubbed_payment", "tds_deduction", "short_payment") \
                and g.get("paid_by") == g["party_id"]:
            total += 1
            hits += g["party_id"] in [p for p, _ in cidx.search(e.narration, 5)]
    assert hits / total > 0.9, hits / total


@pytest.mark.parametrize("text,ok", [
    ('{"category": "full_payment", "party_id": "C001", "invoice_ids": ["X"]}', True),
    ('Sure!\n```json\n{"category": "tds_deduction"}\n```', True),
    ('{"category": "a"} {"category": "b"}', True),
    ("no json here", False),
])
def test_parse_answer(text, ok):
    ans, err = parse_answer(text)
    assert (ans is not None) == ok


def test_hallucinated_ids_are_dropped(led):
    e = led.entries[0]
    p = to_prediction(e, {"category": "full_payment", "party_id": "C999", "invoice_ids": ["FAKE"],
                          "needs_review": False, "confidence": 0.9}, "", {"C001"}, {"REAL"})
    assert p.party_id is None and p.invoice_ids == []


def test_review_forced_for_risky_categories(led):
    e = led.entries[0]
    p = to_prediction(e, {"category": "unknown_party", "needs_review": False}, "", set(), set())
    assert p.needs_review


def test_r1_prompt_has_no_future_invoices(led):
    sys = R1RAG(backend="fake", k="5")
    for e in led.entries[:200]:
        u, parties, invs, *_ = sys.build(e, led)
        for i in invs:
            assert led.invoices[i]["invoice_date"] <= e.value_date


@pytest.mark.parametrize("cls,kw", [(R0NoRetrieval, {}), (R1RAG, {"k": "5"}),
                                    (R2Rerank, {"reranker": "none", "keep": "3"})])
def test_runner_end_to_end_with_fake_model(led, tmp_path, cls, kw):
    sys = cls(backend="fake", batch="4", **kw)
    res = run(sys, led, "dev", limit=30, cost_mode="gpu", out_dir=tmp_path, verbose=False)
    s = res["summary"]
    assert s["n"] == 30 and s["egress_bytes_total"] == 0
    rows = [json.loads(l) for l in open(f"{res['run_dir']}/predictions.jsonl")]
    assert all(r["pred"]["steps"] for r in rows)
    if cls is not R0NoRetrieval:
        assert s["party_recall"] is not None


# ---------------- Step 3 (R3) ----------------
from pratyaksha.systems.r3_context import R3Context, R3FirstOption
from pratyaksha.harness.scoring import is_correct


def test_r3_options_explain_amount_exactly(led):
    sys = R3Context(backend="fake", reranker="none")
    for e in led.entries[:300]:
        *_, ids, opts, dups = sys.build(e, led)
        for o in opts:
            if o["category"] in ("full_payment", "clubbed_payment"):
                tot = round(sum(led.invoices[i]["total"] for i in o["invoice_ids"]), 2)
                # outstanding may be less than total only after a short payment; never more
                assert tot + 0.01 >= e.credit


def test_r3_options_never_include_future_invoices(led):
    sys = R3Context(backend="fake", reranker="none")
    for e in led.entries[:300]:
        *_, ids, opts, dups = sys.build(e, led)
        for o in opts:
            for i in o["invoice_ids"]:
                assert led.invoices[i]["invoice_date"] <= e.value_date


def test_r3_prompt_hides_account_numbers_from_answer_format(led):
    sys = R3Context(backend="fake", reranker="none")
    u = sys.build(led.entries[50], led)[0]
    assert "Never copy account numbers" in u


def test_r3_control_runs_and_beats_nothing(led, tmp_path):
    res = run(R3FirstOption(reranker="none"), led, "dev", limit=60, out_dir=tmp_path, verbose=False)
    s = res["summary"]
    assert s["option_recall"] is not None and s["accuracy"] > 0.5


def test_parse_ignores_thinking_preamble():
    ans, err = parse_answer('<think>The amount is 1,234 so maybe M2...</think>\n{"option": "M2"}')
    assert ans == {"option": "M2"}
    ans, err = parse_answer('<think>still thinking when the limit hit')
    assert ans is None


# ---------------- Step 4 (R5 data) ----------------
from pratyaksha.finetune.build_sft import build as build_sft, gold_option


def test_sft_targets_match_gold(led, tmp_path):
    d = led.root
    rows, stats = build_sft(str(d), "train", reranker="none", device="cpu")
    assert rows and stats["offered"] > 0.7 * len(rows)
    sys = R3FirstOption(reranker="none")
    by_id = {(r["entry_id"], r["condition"]): r for r in rows}
    for e in led.split("train")[:80]:
        r = by_id[(e.entry_id, "clean")]
        t = json.loads(r["target"])
        *_, ids, opts, dups = sys.build(e, led)
        g = led.gold[e.entry_id]
        if t["option"].startswith("M"):
            assert is_correct(opts[ids.index(t["option"])], g)
        if g["category"] in ("duplicate_credit", "unknown_party", "short_payment"):
            assert t["needs_review"]


def test_sft_never_uses_dev_or_test(led):
    rows, _ = build_sft(str(led.root), "train", reranker="none", device="cpu")
    train_ids = {e.entry_id for e in led.split("train")}
    assert {r["entry_id"] for r in rows} <= train_ids


# ---------------- Step 5 (R6 gate, R7) ----------------
from pratyaksha.systems.r3_context import R6Gate, R7Frontier, BANK_CHANGE
from pratyaksha.llm.backend import option_probability


def test_guardrail_flags_every_bank_change_line(led, tmp_path):
    sys = R6Gate(backend="fake", reranker="none", threshold="0.5")
    res = run(sys, led, "dev", out_dir=tmp_path, verbose=False)
    rows = [json.loads(l) for l in open(f"{res['run_dir']}/predictions.jsonl")]
    for r in rows:
        if r["gold"].get("bank_detail_change"):
            assert r["pred"]["signals"]["bank_change_alert"] and r["pred"]["needs_review"]
    assert res["summary"]["bank_change_to_human"] == 1.0


def test_threshold_controls_automation(led, tmp_path):
    lo = run(R6Gate(backend="fake", reranker="none", threshold="0.5"), led, "dev", limit=60,
             out_dir=tmp_path, verbose=False)["summary"]
    hi = run(R6Gate(backend="fake", reranker="none", threshold="0.99"), led, "dev", limit=60,
             out_dir=tmp_path, verbose=False)["summary"]
    assert hi["auto_rate"] <= lo["auto_rate"] and hi["auto_rate"] == 0.0


def test_option_probability_multiplies_option_tokens():
    class Tok:
        def decode(self, ids, skip_special_tokens=True):
            return "".join(chr(i) for i in ids)
    text = '{"option": "M2", "needs_review": false}'
    ids = [ord(c) for c in text]
    steps = []
    for c in ids:
        row = {c: 0.5 if chr(c) in "M2" else 1.0}
        steps.append(row)
    # 'M' and '2' inside the value -> 0.5 * 0.5
    assert abs(option_probability(Tok(), ids, steps) - 0.25) < 1e-9
    assert option_probability(Tok(), [ord(c) for c in "no json"], steps) is None


def test_r7_refuses_without_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(RuntimeError):
        R7Frontier(reranker="none")


# ---------------- Step 5b (Laya, Opus) ----------------
from pratyaksha.systems.laya_system import R6Laya, laya_inputs
from pratyaksha.finetune.build_laya import build as build_laya


def test_laya_rows_are_valid(led):
    rows, stats = build_laya(str(led.root), "train", reranker="none", device="cpu")
    assert rows and {e.entry_id for e in led.split("train")} >= {r["_meta"]["entry_id"] for r in rows}
    for r in rows:
        crit = r["questions"]["match"]["criteria"]
        assert r["expected"]["match"] in crit
        assert len(set(crit.values())) == len(crit)          # every option reads differently
        assert isinstance(r["expected"]["person"], bool)


class _StubAgent:
    """Picks M1 when offered (like the control) with probability 0.9."""
    def predict(self, state, questions):
        keys = list(questions["match"]["criteria"])
        ch = "M1" if "M1" in keys else "U"
        return {"answers": {"match": {"choice": ch, "probabilities": {k: (0.9 if k == ch else 0.1 / max(1, len(keys) - 1)) for k in keys}},
                            "person": {"noul": 0.1}}}


def test_r6_laya_pipeline_with_stub(led, tmp_path):
    sys = R6Laya(reranker="none", threshold="0.5", device="cpu")
    sys.agent = _StubAgent()
    s = run(sys, led, "dev", out_dir=tmp_path, verbose=False)["summary"]
    assert s["bank_change_to_human"] == 1.0 and s["auto_error_rate"] <= 0.01 and s["accuracy"] > 0.6


def test_r6_laya_latency_is_end_to_end(led, tmp_path):
    """Laya's time must include search, rerank and context, like every other system (bug fixed 23 Nov)."""
    sys = R6Laya(reranker="none", threshold="0.5", device="cpu")
    sys.agent = _StubAgent()
    res = run(sys, led, "dev", limit=5, out_dir=tmp_path, verbose=False)
    import json as _j
    rows = [_j.loads(l) for l in open(f"{res['run_dir']}/predictions.jsonl")]
    names = {s["name"] for r in rows for s in r["pred"]["steps"]}
    assert "laya" in names and len(names) > 1


# ---------------- Step 6 (Mac) ----------------
from pratyaksha.llm.device import pick
from pratyaksha.harness.cost import CostAssumptions, per_task_inr


def test_device_pick_never_returns_unavailable_gpu():
    d = pick("cuda")
    assert d in ("cuda", "mps", "cpu")
    assert pick("cpu") == "cpu"


def test_owned_cost_split():
    a = CostAssumptions(owned_watts=30, inr_per_kwh=8, hardware_inr=200000, hardware_life_hours=6000)
    c = per_task_inr(0.5, 0, 0, "owned", a)
    assert abs(c["operating_inr"] - 30 * 0.5 / 3.6e6 * 8) < 1e-12
    assert abs(c["amortisation_inr"] - 200000 / 6000 * 0.5 / 3600) < 1e-12
