"""The one shared harness: one system, one split, one condition per run.

    python -m pratyaksha.harness.runner --system rules --split test --condition clean

Writes runs/<run_id>/{predictions.jsonl, summary.json, scorecard.md, config.json}
and appends a line to runs/index.csv so every run, failed ones included, is logged.
"""
from __future__ import annotations

import argparse
import csv
import importlib
import json
import platform
import time
from datetime import datetime
from pathlib import Path

from ..world.ledger import Ledger
from .cost import CostAssumptions, per_task_inr
from .scoring import summarise

SYSTEMS = {
    "rules": "pratyaksha.systems.rules_baseline:RulesBaseline",
    "r0": "pratyaksha.systems.llm_ladder:R0NoRetrieval",
    "r1": "pratyaksha.systems.llm_ladder:R1RAG",
    "r2": "pratyaksha.systems.llm_ladder:R2Rerank",
    "r3": "pratyaksha.systems.r3_context:R3Context",
    "r3_control": "pratyaksha.systems.r3_context:R3FirstOption",
    "r5": "pratyaksha.systems.r3_context:R5FineTuned",
    "r6": "pratyaksha.systems.r3_context:R6Gate",
    "r6_control": "pratyaksha.systems.r3_context:R6Control",
    "r7": "pratyaksha.systems.r3_context:R7Frontier",
    "r6_laya": "pratyaksha.systems.laya_system:R6Laya",
}


def load_system(spec: str, **kw):
    path = SYSTEMS.get(spec, spec)
    mod, cls = path.split(":")
    return getattr(importlib.import_module(mod), cls)(**kw)


def run(system, ledger: Ledger, split: str, limit: int | None = None,
        cost_mode: str = "owned", out_dir: Path = Path("runs"), tag: str = "",
        assumptions: CostAssumptions | None = None, verbose: bool = True) -> dict:
    a = assumptions or CostAssumptions()
    entries = ledger.split(split)[: limit or None]
    run_id = datetime.now().strftime("%Y%m%d-%H%M%S") + f"_{system.name}_{split}_{ledger.condition}" + (f"_{tag}" if tag else "")
    d = out_dir / run_id
    d.mkdir(parents=True, exist_ok=True)
    rows = []
    bs = getattr(system, "batch_size", 1) if hasattr(system, "predict_batch") else 1
    with open(d / "predictions.jsonl", "w", encoding="utf-8") as f:
        for start in range(0, len(entries), bs):
            chunk = entries[start:start + bs]
            t0 = time.perf_counter()
            try:
                preds = (system.predict_batch(chunk, ledger) if hasattr(system, "predict_batch")
                         else [system.predict(chunk[0], ledger)])
            except Exception as ex:  # a crash is a result too
                from .schema import Prediction
                preds = [Prediction(entry_id=e.entry_id, category="unknown_party", needs_review=True,
                                    error=f"{type(ex).__name__}: {ex}") for e in chunk]
            wall = (time.perf_counter() - t0) / len(chunk)
            for e, p in zip(chunk, preds):
                pd = p.to_dict()
                # per-item time: sum of the item's own steps if it has them, else wall time share
                step_secs = sum(s["seconds"] for s in pd["steps"])
                secs = step_secs if step_secs > 0 else wall
                tin = sum(s["tokens_in"] for s in pd["steps"])
                tout = sum(s["tokens_out"] for s in pd["steps"])
                cost = per_task_inr(secs, tin, tout, cost_mode, a)
                row = {"entry": e.as_dict(), "gold": ledger.gold[e.entry_id], "pred": pd,
                       "seconds": secs, "cost": cost}
                rows.append(row)
                f.write(json.dumps(row, default=str) + "\n")
            i = len(rows)
            if verbose and (i % 25 < bs or i == len(entries)):
                acc = sum(1 for r in rows if _ok(r)) / len(rows)
                print(f"  [{i}/{len(entries)}] running accuracy {acc:.3f}", flush=True)
    s = summarise(rows, ledger.restricted_values())
    cfg = {"run_id": run_id, "system": system.name, "system_config": getattr(system, "config", {}),
           "split": split, "condition": ledger.condition, "limit": limit, "cost_mode": cost_mode,
           "cost_assumptions": a.as_dict(), "world_meta": ledger.meta,
           "machine": platform.platform(), "python": platform.python_version()}
    (d / "config.json").write_text(json.dumps(cfg, indent=2, default=str))
    (d / "summary.json").write_text(json.dumps(s, indent=2))
    (d / "scorecard.md").write_text(scorecard_md(cfg, s))
    _append_index(out_dir, cfg, s)
    return {"run_dir": str(d), "summary": s}


def _ok(r):
    from .scoring import is_correct
    return is_correct(r["pred"], r["gold"])


def _append_index(out_dir: Path, cfg: dict, s: dict):
    idx = out_dir / "index.csv"
    if idx.exists() and "party_recall" not in idx.read_text().splitlines()[0]:
        idx.rename(out_dir / "index_step1.csv")   # older header: keep it, start a new file
    new = not idx.exists()
    with open(idx, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["run_id", "system", "split", "condition", "n", "accuracy", "auto_rate",
                        "auto_error_rate", "p50_s", "p95_s", "inr_per_1000", "egress_bytes", "passes_bar",
                        "party_recall", "tokens_in", "parse_errors"])
        w.writerow([cfg["run_id"], cfg["system"], cfg["split"], cfg["condition"], s["n"],
                    f"{s['accuracy']:.6f}", f"{s['auto_rate']:.4f}", f"{s['auto_error_rate']:.4f}",
                    f"{s['latency_p50_s']:.3f}", f"{s['latency_p95_s']:.3f}",
                    f"{s['inr_per_1000_operating']:.4f}", s["egress_bytes_total"],
                    s["acceptance"]["passes"],
                    "" if s.get("party_recall") is None else f"{s['party_recall']:.4f}",
                    f"{s['tokens_in_per_task']:.0f}", s["parse_errors"]])


def scorecard_md(cfg: dict, s: dict) -> str:
    tick = lambda b: "PASS" if b else "FAIL"
    acc = s["acceptance"]
    lines = [f"# Scorecard: {cfg['system']} · {cfg['split']} · {cfg['condition']}", "",
             f"Run `{cfg['run_id']}` · n = {s['n']}", "",
             "| Metric | Value |", "|---|---|",
             f"| Accuracy (strict) | {s['accuracy']:.1%} |",
             f"| Handled automatically | {s['auto_rate']:.1%} |",
             f"| Error rate on automatic | {s['auto_error_rate']:.2%} |",
             f"| Latency p50 / p95 | {s['latency_p50_s']*1000:.1f} ms / {s['latency_p95_s']*1000:.1f} ms |",
             f"| ₹ per 1,000 tasks (operating) | {s['inr_per_1000_operating']:.4f} |",
             f"| ₹ per 1,000 tasks (hardware amortisation) | {s['inr_per_1000_amortisation']:.4f} |",
             f"| Tokens in / out per task | {s['tokens_in_per_task']:.0f} / {s['tokens_out_per_task']:.0f} |",
             f"| Data leaving the machine | {s['egress_bytes_total']:,} bytes |",
             f"| Restricted-field leaks | {s['restricted_leaks']} |",
             f"| Right party among retrieved | {s['party_recall']:.1%} |" if s.get('party_recall') is not None else "| Right party among retrieved | n/a |",
             f"| Model output unreadable (parse errors) | {s['parse_errors']} |",
             f"| Right answer among computed options | {s['option_recall']:.1%} |" if s.get('option_recall') is not None else "| Right answer among computed options | n/a |", "",
             "## Business acceptance bar", "", "| Rule | Result |", "|---|---|",
             f"| Automatic entries ≤ 1% wrong ({s['auto_error_rate']:.2%}) | {tick(acc['auto_error_ok'])} |",
             f"| Misbooked rupees ≤ ₹1,000 (₹{s['cash_gap_inr']:,.2f}) | {tick(acc['cash_ok'])} |",
             f"| Every unexplained entry surfaced ({s['unexplained_surfaced']:.0%}, {s['unexplained_silently_matched']} silently matched) | {tick(acc['unexplained_ok'])} |",
             f"| Bank-detail changes to a person ({s['bank_change_to_human']:.0%} of {s['bank_change_total']}) | {tick(acc['bank_change_ok'])} |",
             f"| Handles at least 50% by itself ({s['auto_rate']:.0%}) | {tick(acc['useful_ok'])} |",
             f"| **Overall** | **{tick(acc['passes'])}** |", "",
             "## By category", "", "| Category | Correct | n | Accuracy |", "|---|---|---|---|"]
    for k, v in s["by_category"].items():
        lines.append(f"| {k} | {v['correct']} | {v['n']} | {v['acc']:.1%} |")
    lines += ["", "## Error types", "", "| Type | Count |", "|---|---|"]
    lines += [f"| {k} | {v} |" for k, v in s["errors"].items()] or ["| none | 0 |"]
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--system", default="rules")
    ap.add_argument("--world", default="data/wwi_in")
    ap.add_argument("--split", default="dev", choices=["train", "dev", "test"])
    ap.add_argument("--condition", default="clean", choices=["clean", "stress"])
    ap.add_argument("--limit", type=int)
    ap.add_argument("--cost-mode", default="owned", choices=["owned", "gpu", "api"])
    ap.add_argument("--tag", default="")
    ap.add_argument("--api-usd-in", type=float, default=None, help="USD per 1M input tokens (R7); check the price page")
    ap.add_argument("--api-usd-out", type=float, default=None, help="USD per 1M output tokens (R7)")
    ap.add_argument("--opt", action="append", default=[], help="system option key=value (repeatable)")
    ap.add_argument("--owned-watts", type=float, default=None, help="Mac power under load (sudo powermetrics)")
    ap.add_argument("--hardware-inr", type=float, default=None, help="what the Mac cost, in rupees")
    ap.add_argument("--inr-per-kwh", type=float, default=None, help="electricity tariff")
    a = ap.parse_args()
    opts = dict(o.split("=", 1) for o in a.opt)
    system = load_system(a.system, **opts)
    led = Ledger(a.world, a.condition)
    ca = CostAssumptions()
    if a.api_usd_in is not None:
        ca.api_usd_in_per_m = a.api_usd_in
    if a.api_usd_out is not None:
        ca.api_usd_out_per_m = a.api_usd_out
    for flag, field in (("owned_watts", "owned_watts"), ("hardware_inr", "hardware_inr"),
                        ("inr_per_kwh", "inr_per_kwh")):
        if getattr(a, flag) is not None:
            setattr(ca, field, getattr(a, flag))
    res = run(system, led, a.split, a.limit, a.cost_mode, tag=a.tag, assumptions=ca)
    print(open(Path(res["run_dir"]) / "scorecard.md").read())


if __name__ == "__main__":
    main()
