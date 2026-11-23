"""Print one comparison table of all runs: python scripts/compare.py [--split dev]"""
import argparse
import csv
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--runs", default="runs")
ap.add_argument("--split", default="")
a = ap.parse_args()
rows = []
for f in sorted(Path(a.runs).glob("index*.csv")):
    rows += list(csv.DictReader(open(f)))
rows = [r for r in rows if not a.split or r["split"] == a.split]
print(f"{'system':<28}{'cond':<8}{'n':>5}{'acc':>8}{'auto':>8}{'autoErr':>9}{'p50 s':>8}{'party@k':>9}{'tok_in':>8}{'parseErr':>9}{'bar':>6}")
for r in rows:
    pr = r.get("party_recall") or ""
    print(f"{r['system']:<28}{r['condition']:<8}{r['n']:>5}{float(r['accuracy']):>8.1%}{float(r['auto_rate']):>8.1%}"
          f"{float(r['auto_error_rate']):>9.1%}{float(r['p50_s']):>8.2f}{(f'{float(pr):.1%}' if pr else '-'):>9}"
          f"{r.get('tokens_in','-') or '-':>8}{r.get('parse_errors','-') or '-':>9}{('PASS' if r['passes_bar']=='True' else 'FAIL'):>6}")
