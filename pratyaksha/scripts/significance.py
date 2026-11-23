"""Are the differences between systems real, or luck? Paired tests on the same lines.

    python scripts/significance.py --split test
    python scripts/significance.py --split test --ref R7_claude-opus-5-5

For every system vs the reference (default: the no-AI R6 control), on the SAME lines:
  - fixes  = lines the system got right and the reference got wrong
  - breaks = lines the system got wrong and the reference got right
  - exact McNemar p-value (two-sided binomial test on fixes vs breaks): p < 0.05 means the
    difference is unlikely to be luck. Lines both got right/wrong say nothing about the difference.
  - 95% bootstrap interval for the accuracy difference (2,000 resamples of lines, seed 0).
Also: which options Laya actually chose (checks the "conflicting schema for 'match'" warning).
Writes runs/significance_<split>.json.
"""
import argparse, glob, json, random, sys
from collections import Counter
from math import comb
sys.path.insert(0, ".")
from pratyaksha.harness.scoring import is_correct

ap = argparse.ArgumentParser()
ap.add_argument("--split", default="test")
ap.add_argument("--ref", default="R6_control_first_option")
ap.add_argument("--boot", type=int, default=2000)
a = ap.parse_args()


def latest(name, cond):
    runs = sorted(p for p in glob.glob(f"runs/*_{name}_{a.split}_{cond}*/predictions.jsonl")
                  if "_check" not in p)
    return {r["entry"]["entry_id"]: r for r in map(json.loads, open(runs[-1]))} if runs else None


def mcnemar_p(b, c):
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def names(cond):
    out = set()
    for p in glob.glob(f"runs/*_{a.split}_{cond}*/predictions.jsonl"):
        if "_check" in p:
            continue
        run = p.split("/")[1]
        out.add(run.split("_", 1)[1].rsplit(f"_{a.split}_", 1)[0])
    return sorted(out)


report = {}
for cond in ("clean", "stress"):
    ref = latest(a.ref, cond)
    if not ref:
        print(f"no {a.ref} run for {a.split} {cond}"); continue
    print(f"\n== {a.split} · {cond} · reference {a.ref}")
    print(f"{'system':<28}{'n':>5}{'acc':>8}{'ref acc':>9}{'fixes':>7}{'breaks':>8}{'p':>8}   95% CI of difference")
    report[cond] = {}
    for n in names(cond):
        if n == a.ref:
            continue
        m = latest(n, cond)
        ids = sorted(k for k in m if k in ref)
        sm = [is_correct(m[k]["pred"], m[k]["gold"]) for k in ids]
        sr = [is_correct(ref[k]["pred"], ref[k]["gold"]) for k in ids]
        b = sum(x and not y for x, y in zip(sm, sr))
        c = sum(y and not x for x, y in zip(sm, sr))
        rng = random.Random(0)
        diffs = []
        for _ in range(a.boot):
            idx = [rng.randrange(len(ids)) for _ in ids]
            diffs.append(sum(sm[i] - sr[i] for i in idx) / len(ids))
        diffs.sort()
        lo, hi = diffs[int(0.025 * a.boot)], diffs[int(0.975 * a.boot) - 1]
        p = mcnemar_p(b, c)
        acc, racc = sum(sm) / len(ids), sum(sr) / len(ids)
        print(f"{n:<28}{len(ids):>5}{acc:>8.1%}{racc:>9.1%}{b:>7}{c:>8}{p:>8.3f}   [{lo:+.1%}, {hi:+.1%}]")
        report[cond][n] = {"n": len(ids), "acc": acc, "ref_acc": racc, "fixes": b, "breaks": c,
                           "mcnemar_p": p, "ci95_diff": [lo, hi]}

    laya = latest("R6_laya_laya_t1", cond)
    if laya:
        chosen = Counter(r["pred"]["raw_output"].split()[0].split("=", 1)[1] for r in laya.values()
                         if r["pred"].get("raw_output", "").startswith("match="))
        deep = [r for r in laya.values()
                if any(is_correct(o, r["gold"]) for o in (r["pred"].get("options") or [])[2:-1])]
        deep_ok = sum(is_correct(r["pred"], r["gold"]) for r in deep)
        print(f"  Laya chose: {dict(sorted(chosen.items()))}")
        print(f"  Laya on lines whose right answer is option 3 or later: {deep_ok}/{len(deep)} right")
        report[cond]["laya_choices"] = dict(chosen)
        report[cond]["laya_deep_option"] = [deep_ok, len(deep)]

json.dump(report, open(f"runs/significance_{a.split}_{a.ref}.json", "w"), indent=1)
print(f"\nwrote runs/significance_{a.split}_{a.ref}.json")
