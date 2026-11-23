"""Same frozen systems, two machines: do the Mac answers match Colab, and how fast and cheap is the Mac?

    python scripts/mac_vs_colab.py --split test

For each system with a run tagged "mac" (one line at a time on the MacBook) and an untagged Colab run:
  - accuracy on both, and on how many lines the two machines gave the SAME answer
    (different hardware does float16 maths slightly differently, so a few lines may differ;
    every difference is listed, nothing is hidden)
  - p50 / p95 seconds per line, end to end (search + reranker + model + gate)
  - rupees per 1,000 lines on the Mac: electricity (operating) and the laptop's price spread over
    its working life (amortisation), shown separately
Writes runs/mac_vs_colab_<split>.json.
"""
import argparse, glob, json, statistics, sys
sys.path.insert(0, ".")
from pratyaksha.harness.scoring import is_correct

ap = argparse.ArgumentParser()
ap.add_argument("--split", default="test")
ap.add_argument("--tag", default="mac")
a = ap.parse_args()


def load(pattern):
    runs = sorted(glob.glob(pattern))
    if not runs:
        return None, None
    d = runs[-1].rsplit("/", 1)[0]
    rows = [json.loads(l) for l in open(runs[-1])]
    return {r["entry"]["entry_id"]: r for r in rows}, json.load(open(d + "/summary.json"))


def pct(xs, q):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(q * len(xs)))] if xs else float("nan")


out = {}
for cond in ("clean", "stress"):
    mac_runs = sorted(glob.glob(f"runs/*_{a.split}_{cond}_{a.tag}/predictions.jsonl"))
    names = sorted({p.split("/")[1].split("_", 1)[1].rsplit(f"_{a.split}_", 1)[0] for p in mac_runs})
    print(f"\n== {a.split} · {cond}")
    print(f"{'system':<26}{'acc Colab':>10}{'acc Mac':>9}{'same answer':>13}{'Mac p50 s':>11}{'Mac p95 s':>11}"
          f"{'₹/1k power':>12}{'₹/1k laptop':>13}")
    out[cond] = {}
    for n in names:
        mac, _ = load(f"runs/*_{n}_{a.split}_{cond}_{a.tag}/predictions.jsonl")
        col, _ = load(f"runs/*_{n}_{a.split}_{cond}/predictions.jsonl")
        ids = sorted(mac)
        acc_m = sum(is_correct(mac[k]["pred"], mac[k]["gold"]) for k in ids) / len(ids)
        secs = [mac[k]["seconds"] for k in ids]
        op = 1000 * statistics.mean(mac[k]["cost"]["operating_inr"] for k in ids)
        am = 1000 * statistics.mean(mac[k]["cost"]["amortisation_inr"] for k in ids)
        row = {"n": len(ids), "acc_mac": acc_m, "p50_s": pct(secs, 0.5), "p95_s": pct(secs, 0.95),
               "inr_per_1000_operating": op, "inr_per_1000_amortisation": am}
        same_txt, acc_c_txt = "-", "-"
        if col:
            both = [k for k in ids if k in col]
            key = lambda r: (r["pred"].get("category"), r["pred"].get("party_id"),
                             tuple(sorted(r["pred"].get("invoice_ids") or [])), bool(r["pred"].get("needs_review")))
            same = [k for k in both if key(mac[k]) == key(col[k])]
            acc_c = sum(is_correct(col[k]["pred"], col[k]["gold"]) for k in both) / len(both)
            row.update(acc_colab=acc_c, same_answer=len(same), compared=len(both),
                       differ=[k for k in both if k not in same])
            same_txt, acc_c_txt = f"{len(same)}/{len(both)}", f"{acc_c:.1%}"
        out[cond][n] = row
        print(f"{n:<26}{acc_c_txt:>10}{acc_m:>9.1%}{same_txt:>13}{row['p50_s']:>11.3f}{row['p95_s']:>11.3f}"
              f"{op:>12.3f}{am:>13.2f}")
        for k in row.get("differ", [])[:5]:
            print(f"    differs: {k}  Colab={col[k]['pred'].get('raw_output', '')[:60]!r}  Mac={mac[k]['pred'].get('raw_output', '')[:60]!r}")

json.dump(out, open(f"runs/mac_vs_colab_{a.split}.json", "w"), indent=1)
print(f"\nwrote runs/mac_vs_colab_{a.split}.json")
