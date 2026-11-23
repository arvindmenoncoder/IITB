"""PRATYAKSHA live demo — runs on the MacBook, opens in the browser.

    python -m demo.server                 # live: models answer on this Mac
    python -m demo.server --replay        # backup: every answer replayed from the recorded Mac runs

What it shows (all on the held-out test month, nothing re-tuned):
  * Live      — one bank line, answered side by side by Rules, Laya, the fine-tuned 0.8B and
                Claude Opus 5.5 (Opus is REPLAYED from its recorded test run, at its real speed:
                no internet and no API key needed in class). A live step trace, the menu the code
                built, the three safety checks, and a data-sent-out meter.
  * Safety knob — move the confidence threshold; see automation, wrong bookings, rupees and the
                business bar change (from the stored dev-month probabilities, as in Step 5).
  * Results   — the test-month and Mac numbers, with the significance result.

Honesty rules built in: every recorded answer is labelled "recorded"; if a live model fails to
load, its recorded Mac answer is used and labelled; the correct answer is hidden until revealed.
"""
from __future__ import annotations

import argparse
import copy
import glob
import json
import os
import random
import sys
import threading
import time
import traceback
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from pratyaksha.harness.scoring import error_type, is_correct, summarise  # noqa: E402
from pratyaksha.world.ledger import Ledger  # noqa: E402

STATIC = Path(__file__).resolve().parent / "static"
FORCED = {"duplicate_credit": "Possible duplicate credit", "unknown_party": "Payer not recognised",
          "short_payment": "Paid less than the bill"}
CATEGORY = {"full_payment": "Full payment", "clubbed_payment": "Several bills in one payment",
            "tds_deduction": "Payment with TDS deducted", "short_payment": "Short payment",
            "duplicate_credit": "Duplicate credit", "unknown_party": "Payer not recognised",
            "bank_charges": "Bank charges", "interest_credit": "Interest credit",
            "supplier_payment": "Payment to a supplier"}
STEP = {"retrieve": "Search customers", "rerank": "Rerank", "context": "Build the menu",
        "llm": "Model answers", "laya": "Laya decides", "rules": "Rules"}

SYSTEMS = {
    "rules": {"label": "Rules", "sub": "No AI", "where": "This Mac", "run": "rules"},
    "laya": {"label": "Laya", "sub": "421M decision model", "where": "This Mac", "run": "R6_laya_laya_t1"},
    "lora": {"label": "Qwen 0.8B, fine-tuned", "sub": "LoRA on months 1–4", "where": "This Mac",
             "run": "R6_r5_lora_0.8b"},
    "opus": {"label": "Claude Opus 5.5", "sub": "Frontier model", "where": "Cloud API", "run": "R7_claude-opus-5-5"},
}
KNOB_MODELS = {"lora": "R6_r5_lora_0.8b", "laya": "R6_laya_laya_t1", "qwen2b": "R6_Qwen3.5-2B"}
KNOB_GRID = [0.0, 0.5, 0.7, 0.8, 0.85, 0.9, 0.93, 0.95, 0.97, 0.98, 0.99, 0.995, 0.998, 0.999, 0.9995, 0.9999]


def latest_run(name: str, split: str, cond: str, tags=("mac", "")):
    for tag in tags:
        suffix = f"_{tag}" if tag else ""
        runs = sorted(p for p in glob.glob(f"runs/*_{name}_{split}_{cond}{suffix}/predictions.jsonl")
                      if os.path.exists(os.path.join(os.path.dirname(p), "summary.json")))
        if runs:
            return Path(runs[-1]).parent, tag
    return None, None


def load_rows(d: Path):
    return {r["entry"]["entry_id"]: r for r in map(json.loads, open(d / "predictions.jsonl"))}


class Engine:
    def __init__(self, data_root: str, replay: bool, no_reranker: bool):
        self.replay, self.no_reranker = replay, no_reranker
        self.led = {c: Ledger(data_root, c) for c in ("clean", "stress")}
        self.by_id = {c: {e.entry_id: e for e in self.led[c].entries} for c in self.led}
        self.test_ids = [e.entry_id for e in self.led["clean"].split("test")]
        self.lock = threading.Lock()
        self.sys: dict = {}
        self.status = {k: ("recorded" if (replay or k == "opus") else "waiting") for k in SYSTEMS}
        self.status["menu"] = "waiting"
        self.device = "–"
        self.recorded, self.summary, self.rec_tag = {}, {}, {}
        for k, meta in SYSTEMS.items():
            for c in ("clean", "stress"):
                d, tag = latest_run(meta["run"], "test", c)
                if d:
                    self.recorded[(k, c)] = load_rows(d)
                    self.summary[(k, c)] = json.load(open(d / "summary.json"))
                    self.rec_tag[(k, c)] = tag or "colab"
        self.scenarios = self._pick_scenarios()
        self._knob_cache = {}

    # ------------------------------------------------------------ loading
    def load(self):
        try:
            from pratyaksha.llm.device import pick
            self.device = pick("auto")
            from pratyaksha.systems.r3_context import R6Control
            rr = "none" if self.no_reranker else "BAAI/bge-reranker-v2-m3"
            self.status["menu"] = "loading"
            ctl = R6Control(reranker=rr, batch="1")
            self.sys["menu"] = ctl
            self.status["menu"] = "ready"
        except Exception:
            traceback.print_exc()
            self.status["menu"] = "failed"
            ctl = None
        if self.replay:
            return
        loaders = {
            "rules": lambda: __import__("pratyaksha.systems.rules_baseline", fromlist=["RulesBaseline"]).RulesBaseline(),
            "laya": lambda: self._share(__import__("pratyaksha.systems.laya_system", fromlist=["R6Laya"]).R6Laya(
                laya="models/laya_t1", threshold="0", reranker="none", batch="1"), ctl),
            "lora": lambda: self._share(__import__("pratyaksha.systems.r3_context", fromlist=["R6Gate"]).R6Gate(
                threshold="0", model="Qwen/Qwen3.5-0.8B", adapter="models/r5_lora_0.8b", reranker="none",
                batch="1"), ctl),
        }
        for k, make in loaders.items():
            self.status[k] = "loading"
            try:
                s = make()
                self.sys[k] = s
                warm = self.by_id["clean"][self.test_ids[0]]
                with self.lock:
                    self._predict(s, warm, self.led["clean"])       # warm-up: first answer is never slow in class
                self.status[k] = "live"
            except Exception:
                traceback.print_exc()
                self.status[k] = "recorded"
                print(f"[demo] {k}: live model unavailable, using its recorded Mac answers")

    @staticmethod
    def _share(s, ctl):
        """One reranker for every system (saves ~1 GB of memory per extra copy)."""
        if ctl is not None and hasattr(ctl, "rr"):
            s.rr = ctl.rr
            s.config["reranker"] = ctl.rr.model_id
        return s

    @staticmethod
    def _predict(s, e, led):
        if hasattr(s, "predict_batch"):
            return s.predict_batch([e], led)[0]
        return s.predict(e, led)

    # ------------------------------------------------------------ scenarios
    def _pick_scenarios(self):
        g = self.led["clean"].gold
        lo, op, ru = ({c: self.recorded.get((k, c), {}) for c in ("clean", "stress")} for k in ("lora", "opus", "rules"))

        def ok(rows, i):
            r = rows.get(i)
            return r is not None and is_correct(r["pred"], r["gold"])

        def auto(rows, i):
            r = rows.get(i)
            return r is not None and not r["pred"].get("needs_review")

        def offered(rows, i):
            r = rows.get(i)
            return r is not None and any(is_correct(o, r["gold"]) for o in r["pred"].get("options") or [])

        specs = [
            ("exact", "Exact payment", "One bill, paid in full", "clean",
             lambda i: g[i]["category"] == "full_payment" and ok(lo["clean"], i) and auto(lo["clean"], i) and ok(op["clean"], i)),
            ("clubbed", "Two bills, one payment", "The code adds the bills up", "clean",
             lambda i: g[i]["category"] == "clubbed_payment" and ok(lo["clean"], i) and auto(lo["clean"], i)),
            ("tds", "TDS deducted", "Customer kept back tax", "clean",
             lambda i: g[i]["category"] == "tds_deduction" and ok(lo["clean"], i) and auto(lo["clean"], i)),
            ("short", "Paid short", "Always sent to a person", "clean",
             lambda i: g[i]["category"] == "short_payment" and ok(lo["clean"], i)),
            ("fraud", "Bank-detail change", "A fraud-style e-mail", "clean",
             lambda i: bool(g[i].get("bank_detail_change")) and ok(lo["clean"], i)),
            ("unknown", "Unknown payer", "Not in the customer list", "clean",
             lambda i: g[i]["category"] == "unknown_party" and ok(lo["clean"], i)),
            ("messy", "Messy narration", "Rules fail, AI reads it", "stress",
             lambda i: g[i]["category"] in ("full_payment", "clubbed_payment") and ok(lo["stress"], i)
             and auto(lo["stress"], i) and not ok(ru["stress"], i)),
            ("opus", "Where Opus slipped", "Right answer was on the menu", "clean",
             lambda i: ok(lo["clean"], i) and not ok(op["clean"], i) and offered(op["clean"], i)),
            ("limit", "The honest limit", "Right answer never found", "clean",
             lambda i: bool(lo["clean"]) and i in lo["clean"] and not offered(lo["clean"], i) and g[i].get("party_id")),
        ]
        out = []
        for key, title, sub, cond, test in specs:
            hit = next((i for i in self.test_ids if test(i)), None)
            if hit is None:        # no recorded runs: fall back to the gold category alone
                cat = {"exact": "full_payment", "clubbed": "clubbed_payment", "tds": "tds_deduction",
                       "short": "short_payment", "unknown": "unknown_party", "messy": "full_payment"}.get(key)
                hit = next((i for i in self.test_ids if cat and g[i]["category"] == cat), None)
                if key == "fraud":
                    hit = next((i for i in self.test_ids if g[i].get("bank_detail_change")), None)
            if hit:
                out.append({"key": key, "title": title, "sub": sub, "cond": cond, "entry_id": hit})
        return out

    # ------------------------------------------------------------ helpers
    def party_name(self, led, pid):
        if not pid:
            return None
        if pid in led.customers:
            return led.customers[pid]["legal_name"]
        if pid in led.suppliers:
            return led.suppliers[pid]["name"]
        return pid

    def invoices(self, led, ids):
        return [{"id": i, "amount": led.invoices[i]["total"] if i in led.invoices else None} for i in ids or []]

    def menu(self, e, led):
        """The options the code computes for this line (identical for every R6 system)."""
        ctl = self.sys.get("menu")
        if ctl is None:
            return [], []
        from pratyaksha.systems.r3_context import BANK_CHANGE
        with self.lock:
            b = ctl.build(e, led)
        _, _, _, _, parties, _, ids, opts, dups = b
        items = []
        for oid, o in zip(ids, opts):
            items.append({"id": oid, "category": o["category"], "label": CATEGORY.get(o["category"], o["category"]),
                          "party": self.party_name(led, o["party_id"]), "party_id": o["party_id"],
                          "invoices": self.invoices(led, o["invoice_ids"]), "why": o.get("why", "")})
        if dups:
            items.append({"id": "D", "category": "duplicate_credit", "label": "Duplicate credit", "party": None,
                          "invoices": [], "why": f"Same amount already credited on {dups[-1].value_date.strftime('%d %b')}"})
        items.append({"id": "U", "category": "unknown_party", "label": "None of these", "party": None,
                      "invoices": [], "why": "Send to a person"})
        emails = [{"from": r["from"], "received": r["received"], "body": r["body"],
                   "bank_change": bool(BANK_CHANGE.search(r["body"]))}
                  for r in ctl._emails_of.get(e.entry_id, [])]
        return items, emails

    @staticmethod
    def option_id(pred, menu):
        key = (pred.get("category"), pred.get("party_id"), tuple(sorted(pred.get("invoice_ids") or [])))
        for m in menu:
            if (m["category"], m.get("party_id"), tuple(sorted(i["id"] for i in m["invoices"]))) == key:
                return m["id"]
        if pred.get("category") == "unknown_party" and not pred.get("party_id"):
            return "U"
        return None

    # ------------------------------------------------------------ API
    def line(self, entry_id, cond):
        led = self.led[cond]
        e = self.by_id[cond][entry_id]
        g = led.gold[entry_id]
        menu, emails = self.menu(e, led)
        return {"entry_id": entry_id, "cond": cond, "date": e.value_date.strftime("%d %b %Y"),
                "narration": e.narration, "amount": e.credit or e.debit,
                "direction": "credit" if e.credit else "debit", "menu": menu, "emails": emails,
                "gold": {"category": g["category"], "label": CATEGORY.get(g["category"], g["category"]),
                         "party": self.party_name(led, g.get("party_id")),
                         "invoices": self.invoices(led, g.get("invoice_ids")),
                         "needs_review": bool(g.get("needs_review")),
                         "bank_detail_change": bool(g.get("bank_detail_change"))}}

    def run(self, key, entry_id, cond):
        led = self.led[cond]
        e = self.by_id[cond][entry_id]
        g = led.gold[entry_id]
        mode = "live" if self.status.get(key) == "live" else "recorded"
        if mode == "live":
            with self.lock:
                t0 = time.perf_counter()
                p = self._predict(self.sys[key], e, led).to_dict()
                wall = time.perf_counter() - t0
            step_secs = sum(s["seconds"] for s in p["steps"])
            seconds = step_secs if step_secs > 0 else wall
        else:
            r = self.recorded.get((key, cond), {}).get(entry_id)
            if r is None:
                return {"system": key, "available": False}
            p, seconds = r["pred"], r["seconds"]
        menu, _ = self.menu(e, led)
        steps = [{"name": s["name"], "label": STEP.get(s["name"], s["name"]), "ms": round(s["seconds"] * 1000, 1),
                  "local": s.get("local", True), "bytes": s.get("bytes_out", 0)} for s in p.get("steps", [])]
        if key == "opus":
            for s in steps:
                if s["name"] == "llm":
                    s["label"] = "Sent to Anthropic, answer back"
        sig = p.get("signals") or {}
        summ = self.summary.get((key, cond), {})
        cost = (summ.get("inr_per_1000_operating", 0) + summ.get("inr_per_1000_amortisation", 0)) if summ else None
        return {
            "system": key, "available": True, "mode": mode,
            "recorded_on": self.rec_tag.get((key, cond)) if mode == "recorded" else "this Mac",
            "seconds": seconds, "steps": steps,
            "bytes_out": sum(s["bytes"] for s in steps if not s["local"]),
            "answer": {"category": p["category"], "label": CATEGORY.get(p["category"], p["category"]),
                       "party": self.party_name(led, p.get("party_id")),
                       "invoices": self.invoices(led, p.get("invoice_ids")),
                       "option_id": self.option_id(p, menu) if key != "rules" else None},
            "gate": {"kind": "rules" if key == "rules" else ("flag" if key == "opus" else "prob"),
                     "needs_review_recorded": bool(p.get("needs_review")),
                     "error": p.get("error") or "",
                     "forced": FORCED.get(p["category"]) if key != "rules" else None,
                     "bank_change_alert": bool(sig.get("bank_change_alert")),
                     "prob": sig.get("option_prob") if key not in ("rules", "opus") else None,
                     "model_flag": bool(sig.get("model_flag"))},
            "correct": is_correct(p, g), "error_type": error_type(p, g) or "",
            "cost_per_1000": cost,
        }

    def knob(self, model, cond):
        k = (model, cond)
        if k not in self._knob_cache:
            name = KNOB_MODELS[model]
            d, _ = latest_run(name, "dev", cond, tags=("",))
            if d is None:
                self._knob_cache[k] = {"available": False}
            else:
                rows = list(load_rows(d).values())
                pts = []
                for t in KNOB_GRID:
                    s = summarise(regate(rows, t))
                    pts.append({"t": t, "auto": s["auto_rate"], "err": s["auto_error_rate"], "cash": s["cash_gap_inr"],
                                "bank": s["bank_change_to_human"], "bank_n": s["bank_change_total"],
                                "acc": s["accuracy"], "pass": s["acceptance"]["passes"]})
                self._knob_cache[k] = {"available": True, "n": len(rows), "points": pts}
        return self._knob_cache[k]

    def results(self):
        out = []
        names = [("rules", "Rules (no AI)", "rules"), ("control", "Code only (no AI)", "R6_control_first_option"),
                 ("qwen2b", "Qwen 2B, untrained", "R6_Qwen3.5-2B"), ("lora", "Qwen 0.8B, fine-tuned", "R6_r5_lora_0.8b"),
                 ("laya", "Laya", "R6_laya_laya_t1"), ("opus", "Claude Opus 5.5", "R7_claude-opus-5-5")]
        for key, label, run in names:
            row = {"key": key, "label": label}
            for c in ("clean", "stress"):
                d, tag = latest_run(run, "test", c)
                if d is None:
                    continue
                s = json.load(open(d / "summary.json"))
                row[c] = {"acc": s["accuracy"], "auto": s["auto_rate"], "err": s["auto_error_rate"],
                          "p50": s["latency_p50_s"], "cost": s["inr_per_1000_operating"] + s["inr_per_1000_amortisation"],
                          "egress_per_line": s["egress_bytes_total"] / max(1, s["n"]), "pass": s["acceptance"]["passes"],
                          "where": "MacBook" if tag == "mac" else ("Anthropic API" if key == "opus" else "Colab T4")}
            out.append(row)
        sig = None
        f = Path("runs/significance_test_R6_control_first_option.json")
        if f.exists():
            sig = json.load(open(f))
        return {"systems": out, "significance": sig}


def regate(rows, t):
    out = []
    for r in rows:
        r = copy.deepcopy(r)
        p, sg = r["pred"], r["pred"].get("signals", {})
        prob = sg.get("option_prob")
        p["needs_review"] = (bool(p.get("error")) or p["category"] in FORCED or prob is None or prob < t
                             or bool(sg.get("bank_change_alert")))
        out.append(r)
    return out


ENGINE: Engine | None = None


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _json(self, obj, code=200):
        body = json.dumps(obj, default=str).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        try:
            if u.path in ("/", "/index.html"):
                body = (STATIC / "index.html").read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            elif u.path == "/api/status":
                self._json({"status": ENGINE.status, "device": ENGINE.device, "replay": ENGINE.replay,
                            "systems": SYSTEMS, "scenarios": ENGINE.scenarios})
            elif u.path == "/api/line":
                self._json(ENGINE.line(q["entry_id"], q.get("cond", "clean")))
            elif u.path == "/api/random":
                self._json({"entry_id": random.choice(ENGINE.test_ids)})
            elif u.path == "/api/run":
                self._json(ENGINE.run(q["system"], q["entry_id"], q.get("cond", "clean")))
            elif u.path == "/api/knob":
                self._json(ENGINE.knob(q.get("model", "lora"), q.get("cond", "clean")))
            elif u.path == "/api/results":
                self._json(ENGINE.results())
            else:
                self._json({"error": "not found"}, 404)
        except Exception as ex:
            traceback.print_exc()
            self._json({"error": f"{type(ex).__name__}: {ex}"}, 500)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--data", default="data/wwi_in")
    ap.add_argument("--replay", action="store_true", help="backup mode: replay recorded Mac answers, load no models")
    ap.add_argument("--no-reranker", action="store_true", help="testing only: skip the reranker model")
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--online", action="store_true", help="allow Hugging Face downloads (default: offline, cached models only)")
    a = ap.parse_args()
    global ENGINE
    os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    if not a.online:            # class Wi-Fi must not matter: use only the models already on this Mac
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    ENGINE = Engine(a.data, a.replay, a.no_reranker)
    threading.Thread(target=ENGINE.load, daemon=True).start()
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), Handler)
    url = f"http://localhost:{a.port}"
    print(f"\n  PRATYAKSHA demo → {url}   ({'replay' if a.replay else 'live'} mode; Ctrl+C to stop)\n")
    if not a.no_browser:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
