"""Compare systems on exactly the lines another (smaller) run covered, e.g. the R7 Gemini slice.

    python scripts/same_lines.py --ref R7_gemini-3.8-flash --split dev --condition clean
"""
import argparse, glob, json, sys
sys.path.insert(0, ".")
from pratyaksha.harness.scoring import is_correct

ap = argparse.ArgumentParser()
ap.add_argument("--ref", required=True)
ap.add_argument("--split", default="dev")
ap.add_argument("--condition", default="clean")
a = ap.parse_args()


def latest(pattern):
    r = sorted(glob.glob(pattern))
    return [json.loads(l) for l in open(r[-1])] if r else None

ref = latest(f"runs/*_{a.ref}_{a.split}_{a.condition}*/predictions.jsonl")
if not ref:
    sys.exit("no reference run")
ids = {r["entry"]["entry_id"] for r in ref}
names = sorted({p.split("/")[1].split("_", 1)[1].rsplit(f"_{a.split}_", 1)[0]
                for p in glob.glob(f"runs/*_{a.split}_{a.condition}*/predictions.jsonl")})
print(f"{len(ids)} lines covered by {a.ref} ({a.split}, {a.condition})")
print(f"{'system':<30}{'right':>7}{'alone':>7}{'wrong alone':>12}{'bank->person':>14}{'egress bytes':>14}")
for n in names:
    rows = latest(f"runs/*_{n}_{a.split}_{a.condition}*/predictions.jsonl")
    rows = [r for r in rows if r["entry"]["entry_id"] in ids]
    if len(rows) != len(ids):
        continue
    right = sum(is_correct(r["pred"], r["gold"]) for r in rows)
    alone = [r for r in rows if not r["pred"]["needs_review"]]
    wrong_alone = sum(1 for r in alone if not is_correct(r["pred"], r["gold"]))
    bc = [r for r in rows if r["gold"].get("bank_detail_change")]
    bc_ok = sum(1 for r in bc if r["pred"]["needs_review"])
    egress = sum(s.get("bytes_out", 0) for r in rows for s in r["pred"]["steps"] if not s.get("local", True))
    print(f"{n:<30}{right:>4}/{len(rows):<3}{len(alone):>6}{wrong_alone:>12}{f'{bc_ok}/{len(bc)}':>14}{egress:>14,}")
