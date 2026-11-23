"""R4: what errors are left after R3, and are they the kind fine-tuning can fix?

    python scripts/error_analysis.py --model R3_Qwen3.5-2B

Splits every line into:
  correct+auto      right and handled automatically (good)
  correct+review    right but sent to a person      (over-caution -> fine-tuning target)
  wrong, in options right answer was offered, model chose wrong (choice -> fine-tuning target)
  wrong, not offered right answer not among options  (retrieval/options -> NOT fixable by fine-tuning)
"""
import argparse, glob, json, sys
from collections import Counter
sys.path.insert(0, ".")
from pratyaksha.harness.scoring import is_correct

ap = argparse.ArgumentParser()
ap.add_argument("--model", default="R3_Qwen3.5-2B")
ap.add_argument("--split", default="dev")
a = ap.parse_args()
for cond in ("clean", "stress"):
    runs = sorted(glob.glob(f"runs/*_{a.model}_{a.split}_{cond}*/predictions.jsonl"))
    if not runs:
        print(f"no run for {a.model} {cond}"); continue
    rows = [json.loads(l) for l in open(runs[-1])]
    buckets, wrong_cat = Counter(), Counter()
    for r in rows:
        ok = is_correct(r["pred"], r["gold"])
        offered = any(is_correct(o, r["gold"]) for o in r["pred"].get("options", []))
        if ok:
            buckets["correct+review" if r["pred"]["needs_review"] else "correct+auto"] += 1
        elif r["pred"].get("error"):
            buckets["unusable output"] += 1
        elif offered:
            buckets["wrong, right answer WAS offered"] += 1
            wrong_cat[r["gold"]["category"]] += 1
        else:
            buckets["wrong, right answer NOT offered"] += 1
    n = len(rows)
    print(f"\n== {a.model} · {cond} · n={n}")
    for k in ["correct+auto", "correct+review", "wrong, right answer WAS offered",
              "wrong, right answer NOT offered", "unusable output"]:
        print(f"  {k:<34}{buckets[k]:>5}  {buckets[k]/n:6.1%}")
    fixable = buckets["correct+review"] + buckets["wrong, right answer WAS offered"] + buckets["unusable output"]
    print(f"  -> fine-tuning could fix up to {fixable} lines ({fixable/n:.1%}); "
          f"options/retrieval must fix {buckets['wrong, right answer NOT offered']}")
    print(f"  wrong choices by category: {dict(wrong_cat)}")
