"""Where does the model beat (or lose to) the no-LLM control on the same lines?

    python scripts/vs_control.py --model R3_Qwen3.5-2B --condition clean
"""
import argparse, glob, json, sys
sys.path.insert(0, ".")
from pratyaksha.harness.scoring import is_correct

ap = argparse.ArgumentParser()
ap.add_argument("--model", required=True)
ap.add_argument("--control", default="R3_control_first_option")
ap.add_argument("--condition", default="clean")
ap.add_argument("--split", default="dev")
a = ap.parse_args()


def latest(name):
    runs = sorted(glob.glob(f"runs/*_{name}_{a.split}_{a.condition}*/predictions.jsonl"))
    if not runs:
        sys.exit(f"no run found for {name} {a.split} {a.condition}")
    return {r["entry"]["entry_id"]: r for r in map(json.loads, open(runs[-1]))}

m, c = latest(a.model), latest(a.control)
both = [k for k in m if k in c]
win = [k for k in both if is_correct(m[k]["pred"], m[k]["gold"]) and not is_correct(c[k]["pred"], c[k]["gold"])]
lose = [k for k in both if not is_correct(m[k]["pred"], m[k]["gold"]) and is_correct(c[k]["pred"], c[k]["gold"])]
print(f"{a.model} vs {a.control} ({a.condition}, n={len(both)}): model fixes {len(win)}, model breaks {len(lose)}")
for title, ks in (("MODEL RIGHT, CONTROL WRONG", win), ("MODEL WRONG, CONTROL RIGHT", lose)):
    print(f"\n== {title} (first 5)")
    for k in ks[:5]:
        r = m[k]
        print(f"- {k} {r['gold']['category']:<16} {r['entry']['narration'][:55]!r}")
        print(f"    model said: {r['pred']['raw_output'][:120]!r}")
