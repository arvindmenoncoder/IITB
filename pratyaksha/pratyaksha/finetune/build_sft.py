"""R5 training data: the R3 prompt for each TRAIN-split line, and the answer we want.

    python -m pratyaksha.finetune.build_sft --out data/sft/train.jsonl [--reranker none]

Why the train split only (months 1-4): a business fine-tunes on its OWN PAST
reconciliations; dev (month 5) and test (month 6) are never seen in training.

Target answer is short: {"option": "M2", "needs_review": false}
  * option       = the option that matches the gold answer; "D" for a duplicate;
                   "U" when no option is right (teaches the model to abstain).
  * needs_review = the gold flag (false for ordinary payments). Why: the 2B model
                   flagged ~75% of lines although it was right -- we teach it when
                   NOT to ask, and keep forcing review for risky categories.
Both clean and stress narrations are used, so the model sees messy lines too.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from ..harness.scoring import is_correct
from ..systems.llm_ladder import SYSTEM
from ..systems.r3_context import R3FirstOption
from ..world.ledger import Ledger

FORCED_REVIEW = {"duplicate_credit", "unknown_party", "short_payment"}


def gold_option(gold: dict, ids: list, opts: list, dups: list) -> tuple[str, str]:
    """Return (option id, how) for the gold answer."""
    for oid, o in zip(ids, opts):
        if is_correct(o, gold):
            return oid, "offered"
    if gold["category"] == "duplicate_credit" and dups:
        return "D", "duplicate"
    if gold["category"] == "unknown_party":
        return "U", "unknown"
    return "U", "not_offered"      # right answer missing: the honest answer is "none of these"


def build(world: str, split: str = "train", reranker: str = "BAAI/bge-reranker-v2-m3",
          device: str = "cuda") -> tuple[list[dict], Counter]:
    sys = R3FirstOption(reranker=reranker, device=device)
    rows, stats = [], Counter()
    for cond in ("clean", "stress"):
        led = Ledger(world, cond)
        for e in led.split(split):
            u, *_, ids, opts, dups = sys.build(e, led)
            g = led.gold[e.entry_id]
            oid, how = gold_option(g, ids, opts, dups)
            review = bool(g.get("needs_review")) or g["category"] in FORCED_REVIEW or how == "not_offered"
            target = json.dumps({"option": oid, "needs_review": review})
            rows.append({"entry_id": e.entry_id, "condition": cond, "how": how,
                         "messages": [{"role": "system", "content": SYSTEM},
                                      {"role": "user", "content": u}],
                         "target": target})
            stats[how] += 1
            stats[f"review={review}"] += 1
    return rows, stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--world", default="data/wwi_in")
    ap.add_argument("--split", default="train")
    ap.add_argument("--out", default="data/sft/train.jsonl")
    ap.add_argument("--reranker", default="BAAI/bge-reranker-v2-m3")
    ap.add_argument("--device", default="cuda")
    a = ap.parse_args()
    assert a.split == "train", "never build training data from dev or test"
    rows, stats = build(a.world, a.split, a.reranker, a.device)
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"wrote {len(rows)} examples to {out}")
    print(json.dumps(dict(stats), indent=1))


if __name__ == "__main__":
    main()
