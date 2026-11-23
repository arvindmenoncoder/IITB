"""Laya (System-1 decision model) on task T1 — the mid-sem plan's "System-1 models, fine-tuned per task".

Laya is a 421M non-generative encoder (ModernBERT-large). It reads a *state* and answers typed
questions in one forward pass with a probability per option — no text generation, nothing to parse.

We ask it, for each bank line, the same two decisions the generative models make:
  match  (choice): which computed option explains this line?  M1 … M8, D (duplicate), U (none)
  person (noul):   must a person check this line?
The state is the R3 evidence in compact form: bank line, candidate parties, up to 3 e-mails.
Options are exactly the R3 options (computed by code), so Laya is compared like for like.

The same function builds training rows (months 1-4) and the inputs at evaluation, so the two
can never drift apart.
"""
from __future__ import annotations

import time

from ..harness.schema import Prediction, Step
from ..world.names import inr
from .r3_context import FORCED, R6Gate, R3FirstOption

EMAIL_CHARS = 500


def laya_inputs(sys, e, led):
    """Return (state, questions, ids, opts, dups, parties, steps). `sys` is any R3-family system.

    `steps` = the timed search / rerank / context steps, so Laya's latency is end to end like every
    other system's (fixed 23 Nov: they were dropped, so Laya's time counted only its own forward pass).
    """
    u, parties_set, inv, steps, parties, inv_ids, ids, opts, dups = sys.build(e, led)
    emails = sys._emails_of.get(e.entry_id, [])[:3]
    amount = f"credit Rs {inr(e.credit)}" if e.credit else f"debit Rs {inr(e.debit)}"
    party_txt = []
    for pid in parties:
        if pid in led.customers:
            c = led.customers[pid]
            party_txt.append(f"{pid} {c['legal_name']} (also: {'; '.join(c['aliases'][1:3])})")
        elif pid in led.suppliers:
            party_txt.append(f"{pid} {led.suppliers[pid]['name']} (supplier)")
    state = {"bank_line": f"{e.value_date.isoformat()} | {amount} | {e.narration}",
             "candidate_parties": party_txt,
             "emails": [r["body"][:EMAIL_CHARS] for r in emails]}
    crit = {}
    for oid, o in zip(ids, opts):
        crit[oid] = f"{o['category']} | {o['party_id'] or '-'} | {', '.join(o['invoice_ids']) or '-'} | {o['why']}"
    if dups:
        d = dups[-1]
        crit["D"] = f"duplicate_credit | same amount already credited on {d.value_date.isoformat()}"
    crit["U"] = "unknown_party | none of the other options explains this line"
    questions = {
        "match": {"type": "choice",
                  "instructions": "Which option explains this bank line? Use the payer name, e-mails and invoice numbers.",
                  "criteria": crit},
        "person": {"type": "noul",
                   "instructions": "Must a person check this line (unsure, duplicate, unknown payer, short "
                                   "payment, or an e-mail asking to change bank details)?"},
    }
    return state, questions, ids, opts, dups, parties, steps


class R6Laya(R6Gate):
    """Laya answers; the same R6 code rules decide who acts (guardrail, forced reviews, threshold).

    --opt laya=models/laya_t1   (the fine-tuned checkpoint)
    The gate uses Laya's probability for its chosen option, as for the Qwen models.
    """
    rung = "R6-Laya"

    def __init__(self, laya="models/laya_t1", device="cuda", **kw):
        kw.update(backend="fake", model="laya")
        super().__init__(device=device, **kw)
        from ..llm.device import pick
        self.laya_path, self.laya_device = laya, pick(device)
        self.agent = None
        self.name = "R6_laya_" + laya.rstrip("/").split("/")[-1]
        self.config.update({"laya": laya})

    def _agent(self):
        if self.agent is None:
            import laya
            self.agent = laya.load(self.laya_path, device=self.laya_device)
        return self.agent

    def predict_batch(self, entries, led):
        agent = self._agent()
        preds = []
        for e in entries:
            state, questions, ids, opts, dups, parties, steps = laya_inputs(self, e, led)
            t0 = time.perf_counter()
            ans = agent.predict(state, questions)
            ans = ans.get("answers", ans)
            dt = time.perf_counter() - t0
            m, person = ans["match"], ans["person"]
            choice = m["choice"]
            p = Prediction(entry_id=e.entry_id, category="unknown_party", needs_review=True)
            if choice in ids[:len(opts)]:
                o = opts[ids.index(choice)]
                p.category, p.party_id, p.invoice_ids = o["category"], o["party_id"], list(o["invoice_ids"])
            elif choice == "D":
                p.category = "duplicate_credit"
            p.raw_output = f"match={choice} p={m['probabilities'].get(choice)} person={person['noul']}"
            p.steps = steps + [Step("laya", dt, note="one forward pass")]
            p.retrieved_party_ids = parties
            p.retrieved_invoice_ids = [i for o in opts for i in o["invoice_ids"]]
            p.options = [{"category": o["category"], "party_id": o["party_id"], "invoice_ids": o["invoice_ids"]}
                         for o in opts] + ([{"category": "duplicate_credit", "party_id": None, "invoice_ids": []}]
                                           if dups else []) + [{"category": "unknown_party", "party_id": None,
                                                                "invoice_ids": []}]
            p.signals = {"model_flag": float(person["noul"]) >= 0.5,
                         "option_prob": float(m["probabilities"].get(choice, 0.0)),
                         "person_prob": float(person["noul"])}
            self.post(e, p)
            preds.append(p)
        return preds
