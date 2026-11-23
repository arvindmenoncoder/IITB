"""R6 threshold knob: move the System-1 threshold and watch automation, errors and rupees change.

    python scripts/threshold_sweep.py --model R6_r5_lora_0.8b

Reads ONE R6 run per condition (dev) and re-applies the gate offline for many thresholds
(no GPU needed: each line's option probability is already stored). Prints:
  * the knob table: threshold -> handled alone, error rate on those, misbooked rupees, bar
  * calibration: when the model is X% sure, how often is it right?
  * the recommended threshold: the lowest one that passes the business bar on dev
    (most automation without breaking the rules). Saved to runs/threshold_<model>.json
    and used unchanged on the held-out test month.
"""
import argparse, copy, glob, json, sys
sys.path.insert(0, ".")
from pratyaksha.harness.scoring import is_correct, summarise

FORCED = {"duplicate_credit", "unknown_party", "short_payment"}
GRID = [0.0, 0.5, 0.7, 0.8, 0.9, 0.95, 0.97, 0.98, 0.99, 0.995, 0.999, 0.9999]


def regate(rows, t, mode="prob", guardrail=True):
    out = []
    for r in rows:
        r = copy.deepcopy(r)
        p, sg = r["pred"], r["pred"].get("signals", {})
        prob = sg.get("option_prob")
        review = bool(p.get("error")) or p["category"] in FORCED or prob is None or prob < t
        if guardrail and sg.get("bank_change_alert"):
            review = True
        if mode == "prob+flag" and sg.get("model_flag"):
            review = True
        p["needs_review"] = review
        out.append(r)
    return out


def load(model, split, cond):
    runs = sorted(glob.glob(f"runs/*_{model}_{split}_{cond}*/predictions.jsonl"))
    return [json.loads(l) for l in open(runs[-1])] if runs else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--split", default="dev")
    a = ap.parse_args()
    data = {c: load(a.model, a.split, c) for c in ("clean", "stress")}
    data = {c: v for c, v in data.items() if v}
    if not data:
        sys.exit(f"no R6 runs for {a.model}")
    passing = {}
    for cond, rows in data.items():
        print(f"\n== {a.model} · {a.split} · {cond} · n={len(rows)}  (accuracy {sum(is_correct(r['pred'], r['gold']) for r in rows)/len(rows):.1%})")
        print(f"{'threshold':>10}{'alone':>8}{'err alone':>11}{'misbooked Rs':>14}{'bank->person':>14}{'bar':>6}")
        knob = []
        for t in GRID:
            s = summarise(regate(rows, t))
            ok = s["acceptance"]["passes"]
            knob.append({"threshold": t, "auto_rate": s["auto_rate"], "auto_error_rate": s["auto_error_rate"],
                         "cash_gap_inr": s["cash_gap_inr"], "passes": ok})
            print(f"{t:>10}{s['auto_rate']:>8.1%}{s['auto_error_rate']:>11.2%}{s['cash_gap_inr']:>14,.0f}"
                  f"{s['bank_change_to_human']:>14.0%}{('PASS' if ok else 'FAIL'):>6}")
            passing.setdefault(t, []).append(ok)
        # what the model's own text flag would have done
        s = summarise(regate(rows, 0.0, mode="prob+flag"))
        print(f"  model's own needs_review flag (+ guardrail): alone {s['auto_rate']:.1%}, err {s['auto_error_rate']:.2%}")
        s = summarise(regate(rows, 0.0, guardrail=False))
        print(f"  no gate, no guardrail: alone {s['auto_rate']:.1%}, err {s['auto_error_rate']:.2%}, "
              f"bank->person {s['bank_change_to_human']:.0%}")
        # calibration
        bins = [(0, .5), (.5, .8), (.8, .9), (.9, .95), (.95, .99), (.99, .999), (.999, 1.0001)]
        print("  calibration (model's probability vs how often it was right):")
        ece, n_all = 0.0, 0
        for lo, hi in bins:
            b = [r for r in rows if r["pred"]["signals"].get("option_prob") is not None
                 and lo <= r["pred"]["signals"]["option_prob"] < hi]
            if not b:
                continue
            conf = sum(r["pred"]["signals"]["option_prob"] for r in b) / len(b)
            acc = sum(is_correct(r["pred"], r["gold"]) for r in b) / len(b)
            ece += len(b) * abs(conf - acc)
            n_all += len(b)
            print(f"    {lo:>5.3f}-{min(hi,1):<5.3f} n={len(b):>3}  says {conf:6.1%}  right {acc:6.1%}")
        if n_all:
            print(f"  expected calibration error (lower is better): {ece/n_all:.3f}")
        json.dump(knob, open(f"runs/knob_{a.model}_{a.split}_{cond}.json", "w"), indent=1)
    ok_all = [t for t in GRID if all(passing.get(t, [False]))]
    rec = min(ok_all) if ok_all else None
    json.dump({"model": a.model, "chosen_on": a.split, "threshold": rec,
               "rule": "lowest threshold that passes the business bar on every condition"},
              open(f"runs/threshold_{a.model}.json", "w"), indent=1)
    print(f"\nRECOMMENDED threshold for {a.model}: {rec}  (saved to runs/threshold_{a.model}.json)")


if __name__ == "__main__":
    main()
