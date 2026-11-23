"""Laya training data from months 1-4 (same rule as R5: never dev or test).

    python -m pratyaksha.finetune.build_laya --out data/laya/train.jsonl

Row format is the one `laya-train` reads: {"state", "questions", "expected"}.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from ..systems.laya_system import laya_inputs
from ..systems.r3_context import R3FirstOption
from ..world.ledger import Ledger
from .build_sft import FORCED_REVIEW, gold_option


def build(world, split="train", reranker="BAAI/bge-reranker-v2-m3", device="cuda"):
    sys = R3FirstOption(reranker=reranker, device=device)
    rows, stats = [], Counter()
    for cond in ("clean", "stress"):
        led = Ledger(world, cond)
        for e in led.split(split):
            state, questions, ids, opts, dups, _, _ = laya_inputs(sys, e, led)
            g = led.gold[e.entry_id]
            oid, how = gold_option(g, ids, opts, dups)
            person = bool(g.get("needs_review")) or g["category"] in FORCED_REVIEW or how == "not_offered"
            rows.append({"state": state, "questions": questions,
                         "expected": {"match": oid, "person": person},
                         "_meta": {"entry_id": e.entry_id, "condition": cond, "how": how}})
            stats[how] += 1
            stats[f"person={person}"] += 1
            stats[f"options={len(questions['match']['criteria'])}"] += 1
    return rows, stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--world", default="data/wwi_in")
    ap.add_argument("--out", default="data/laya/train.jsonl")
    ap.add_argument("--reranker", default="BAAI/bge-reranker-v2-m3")
    ap.add_argument("--device", default="cuda")
    a = ap.parse_args()
    rows, stats = build(a.world, "train", a.reranker, a.device)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    # laya-train gets only the fields it reads; ids for tracing go to a side file
    with open(a.out, "w", encoding="utf-8") as f, open(a.out + ".meta.jsonl", "w") as m:
        for r in rows:
            m.write(json.dumps(r.pop("_meta")) + "\n")
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"wrote {len(rows)} rows to {a.out}")
    print(json.dumps(dict(sorted(stats.items())), indent=1))


if __name__ == "__main__":
    main()
