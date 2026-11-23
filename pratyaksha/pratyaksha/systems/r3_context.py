"""R3 -- context engineering: give the model the RIGHT information, computed, not more of it.

What R2 measured: small models list every invoice instead of choosing, because
they cannot add or subtract (0% on clubbed / TDS / short payments; answers so
long they were cut off). So R3 changes WHAT the model sees and WHAT it must say:

1. Computed match options. Code (not the model) finds invoice sets that explain
   the amount exactly: one invoice, several invoices, invoices minus TDS at
   0.1/1/2% of taxable value, or a small short payment. Design rule from the
   mid-sem report: the language model never does arithmetic.
2. Remittance e-mails near the date, from the candidate parties or quoting this
   exact amount. They name invoices, explain deductions and sometimes ask to
   change bank details (which must go to a person).
3. Recent identical credits, so a duplicate posting can be recognised.
4. The model answers with ONE option id (e.g. "M2") instead of a list of ids:
   a short answer that cannot be cut off.

The model still does the judgment: which payer, which option, whether the
e-mail changes things, and whether a person must look.
"""
from __future__ import annotations

import re
import time
from itertools import combinations
from types import SimpleNamespace

from ..harness.schema import Prediction, Step
from ..world.names import email_for, inr
from .llm_ladder import R2Rerank, SYSTEM, bank_line, parse_answer

TDS_RATES = (0.001, 0.01, 0.02)
POOL = 12          # newest-unpaid invoices per party considered for combinations
MAX_OPTIONS = 8
RS = re.compile(r"Rs\.?\s*([\d,]+\.\d{2})")
INV = re.compile(r"WWI/\d{2}-\d{2}/\d{5}")

ANSWER_FMT_R3 = (
    'Reply as JSON: {"option": "<one option id from MATCH OPTIONS>", "needs_review": true|false, '
    '"confidence": <0 to 1>, "reason": "<at most 12 words>"}\n'
    "Rules: pick the option the evidence supports (payer name, e-mail, invoice numbers). "
    "Set needs_review to true if you are unsure, for any duplicate, unknown payer or short payment, "
    "and ALWAYS if an e-mail asks to change bank account details. Never copy account numbers.")


def _amt(x: float) -> int:
    return int(round(x * 100))


class R3Context(R2Rerank):
    rung = "R3"

    def __init__(self, max_new_tokens="80", **kw):
        super().__init__(max_new_tokens=max_new_tokens, **kw)   # one option id: a short answer

    def extra_init(self, emails="1", dup="1", **kw):
        super().extra_init(**kw)
        self.use_emails, self.use_dup = emails != "0", dup != "0"
        self.score_option = False
        self._emails_of = {}
        self.config.update({"emails": self.use_emails, "duplicates": self.use_dup,
                            "pool": POOL, "max_options": MAX_OPTIONS})

    # ---------------------------------------------------------------- context
    def _emails(self, e, led, parties):
        addr = {email_for(SimpleNamespace(legal_name=led.customers[p]["legal_name"])): p
                for p in parties if p in led.customers}
        out = []
        for r in led.remittances_near(e, days=5):
            amounts = {_amt(float(a.replace(",", ""))) for a in RS.findall(r["body"])}
            if r["from"] in addr or (e.credit and _amt(e.credit) in amounts):
                out.append(r)
        return out   # caller shows the first 3 to the model; the R6 guardrail checks all

    def _sender_parties(self, emails, led):
        by_addr = {email_for(SimpleNamespace(legal_name=c["legal_name"])): cid for cid, c in led.customers.items()}
        return [by_addr[r["from"]] for r in emails if r["from"] in by_addr]

    def _duplicates(self, e, led):
        if not e.credit:
            return []
        i = led._index[e.entry_id]
        return [p for p in led.entries[max(0, i - 40):i]
                if p.credit == e.credit and 0 <= (e.value_date - p.value_date).days <= 2]

    # ---------------------------------------------------------------- options
    def options(self, e, led, parties, mentioned):
        opts = []
        if e.debit:
            if re.search(r"CHG|CHARGE|MAINT", e.narration, re.I):
                opts.append({"category": "bank_charges", "party_id": None, "invoice_ids": [], "why": "bank fee"})
            for p in parties:
                if p in led.suppliers:
                    opts.append({"category": "supplier_payment", "party_id": p, "invoice_ids": [],
                                 "why": f"payment to {led.suppliers[p]['name']}"})
            if not opts:
                opts.append({"category": "bank_charges", "party_id": None, "invoice_ids": [], "why": "bank fee"})
            return opts
        if re.match(r"INT", e.narration):
            opts.append({"category": "interest_credit", "party_id": None, "invoice_ids": [], "why": "bank interest"})
        target = _amt(e.credit)
        for p in parties:
            if p not in led.customers:
                continue
            open_inv = sorted(led.open_invoices(e, [p]), key=lambda x: x["invoice_date"])
            pool = open_inv[-POOL:]
            pool += [i for i in open_inv if i["invoice_id"] in mentioned and i not in pool]
            found = []
            for k in (1, 2, 3):
                for combo in combinations(pool, k):
                    ids = [c["invoice_id"] for c in combo]
                    tot = sum(_amt(c["outstanding"]) for c in combo)
                    if tot == target:
                        found.append({"category": "full_payment" if k == 1 else "clubbed_payment",
                                      "party_id": p, "invoice_ids": ids, "why": "exact amount"})
                    taxable = sum(c["taxable_value"] for c in combo)
                    for r in TDS_RATES:
                        tds = round(taxable * r)
                        if tds and tot - tds * 100 == target:
                            found.append({"category": "tds_deduction", "party_id": p, "invoice_ids": ids,
                                          "why": f"minus TDS Rs {inr(tds)} ({r*100:g}% of taxable)"})
            shorts = [c for c in pool if 0.94 * _amt(c["outstanding"]) <= target < _amt(c["outstanding"])]
            shorts.sort(key=lambda c: _amt(c["outstanding"]) - target)
            for c in shorts[:2]:
                found.append({"category": "short_payment", "party_id": p, "invoice_ids": [c["invoice_id"]],
                              "why": f"Rs {inr(c['outstanding'] - e.credit)} less than outstanding"})
            # invoices named in narration/e-mail first, then fewer invoices first
            found.sort(key=lambda o: (-len(set(o["invoice_ids"]) & mentioned), len(o["invoice_ids"])))
            opts += found
        seen, uniq = set(), []
        for o in opts:
            key = (o["category"], o["party_id"], tuple(sorted(o["invoice_ids"])))
            if key not in seen:
                seen.add(key)
                uniq.append(o)
        return uniq[:MAX_OPTIONS]

    # ---------------------------------------------------------------- prompt
    def build(self, e, led):
        parties, steps = self.candidate_parties(e, led)
        t0 = time.perf_counter()
        all_emails = self._emails(e, led, parties) if self.use_emails else []
        emails = all_emails[:3]   # unchanged from Step 3: the prompt shows at most 3 e-mails
        for p in self._sender_parties(emails, led):
            if p not in parties:
                parties.append(p)          # an e-mail sender is a candidate payer too
        self._emails_of[e.entry_id] = all_emails
        mentioned = set(INV.findall(e.narration))
        for r in emails:
            mentioned |= set(INV.findall(r["body"]))
        opts = self.options(e, led, parties, mentioned)
        dups = self._duplicates(e, led) if self.use_dup else []
        ids = [f"M{i + 1}" for i in range(len(opts))]
        if dups:
            ids.append("D")
        ids.append("U")
        steps.append(Step("context", time.perf_counter() - t0, note=f"{len(opts)} options"))

        rows = []
        for pid in parties:
            if pid in led.customers:
                c = led.customers[pid]
                rows.append(f"{pid} | {c['legal_name']} | {'; '.join(c['aliases'][1:])}")
            elif pid in led.suppliers:
                rows.append(f"{pid} | {led.suppliers[pid]['name']} | supplier")
        opt_rows = []
        for oid, o in zip(ids, opts):
            inv = ", ".join(o["invoice_ids"]) or "-"
            opt_rows.append(f"{oid} | {o['category']} | {o['party_id'] or '-'} | {inv} | {o['why']}")
        if dups:
            d = dups[-1]
            opt_rows.append(f"D | duplicate_credit | - | - | same amount already credited on "
                            f"{d.value_date.isoformat()} ({d.narration[:60]})")
        opt_rows.append("U | unknown_party | - | - | none of the above explains this line")
        parts = [bank_line(e),
                 "CANDIDATE PARTIES (id | name | also appears as)\n" + ("\n".join(rows) or "(none)")]
        if emails:
            parts.append("REMITTANCE E-MAILS received near this date\n" + "\n\n".join(
                f"[from {r['from']} on {r['received']}]\n{r['body']}" for r in emails))
        parts += ["MATCH OPTIONS computed by our accounting system (id | category | party | invoices | why)\n"
                  + "\n".join(opt_rows), ANSWER_FMT_R3]
        self._last = {"ids": ids, "opts": opts, "dups": dups}
        allowed_inv = {i for o in opts for i in o["invoice_ids"]}
        return ("\n\n".join(parts), set(parties), allowed_inv, steps, parties,
                [i for o in opts for i in o["invoice_ids"]], ids, opts, dups)

    def predict_batch(self, entries, led):
        built = [self.build(e, led) for e in entries]
        msgs = [[{"role": "system", "content": SYSTEM}, {"role": "user", "content": b[0]}] for b in built]
        gens = self.backend.generate(msgs, score_option=self.score_option)
        preds = []
        for e, b, g in zip(entries, built, gens):
            _, _, _, steps, parties, inv_ids, ids, opts, dups = b
            ans, err = parse_answer(g.text)
            p = Prediction(entry_id=e.entry_id, category="unknown_party", needs_review=True, confidence=0.0)
            if ans is None:
                p.error = err
            else:
                oid = str(ans.get("option", "")).strip().upper()
                if oid in ids[:len(opts)]:
                    o = opts[ids.index(oid)]
                    p.category, p.party_id, p.invoice_ids = o["category"], o["party_id"], list(o["invoice_ids"])
                elif oid == "D" and dups:
                    p.category = "duplicate_credit"
                elif oid == "U":
                    p.category = "unknown_party"
                else:
                    p.error = f"bad_option:{oid[:10]}"
                try:
                    p.confidence = max(0.0, min(1.0, float(ans.get("confidence", 0.5))))
                except (TypeError, ValueError):
                    p.confidence = 0.5
                p.explanation = str(ans.get("reason", ""))[:200]
                p.needs_review = (bool(ans.get("needs_review", True)) or p.category in
                                  ("duplicate_credit", "unknown_party", "short_payment"))
            p.raw_output = g.text
            p.steps = steps + [Step("llm", g.seconds, g.tokens_in, g.tokens_out, g.bytes_out, g.local,
                                    self.config["model"])]
            p.retrieved_party_ids, p.retrieved_invoice_ids = parties, inv_ids
            p.options = [{"category": o["category"], "party_id": o["party_id"], "invoice_ids": o["invoice_ids"]}
                         for o in opts] + ([{"category": "duplicate_credit", "party_id": None, "invoice_ids": []}]
                                           if dups else []) + [{"category": "unknown_party", "party_id": None,
                                                                "invoice_ids": []}]
            p.signals = {"model_flag": p.needs_review, "option_prob": g.option_prob}
            self.post(e, p)
            preds.append(p)
        return preds

    def post(self, e, p):
        """Hook for R6: change the routing after the model has answered."""


class R3FirstOption(R3Context):
    """Control with NO language model: same R3 context, always pick the first option.

    Why it exists: R3's computed options do part of the work themselves. The model
    only earns its place if it beats this simple rule on the same inputs.
    """
    rung = "R3-control"

    def __init__(self, **kw):
        kw["backend"] = "fake"
        kw.setdefault("model", "first-option")
        super().__init__(**kw)
        self.name = "R3_control_first_option"
        self.config["note"] = "no LLM: picks M1, else U"


class R5FineTuned(R3Context):
    """R5: the R3 prompt, answered by a fine-tuned model.

    LoRA:  --opt model=Qwen/Qwen3.5-0.8B --opt adapter=models/r5_lora_0.8b
    Full:  --opt model=models/r5_full_0.8b
    One change from R3: the weights. Same retrieval, options, e-mails and prompt.
    """
    rung = "R5"

    def __init__(self, **kw):
        super().__init__(**kw)
        tag = (kw.get("adapter") or kw.get("model", "")).rstrip("/").split("/")[-1]
        self.name = f"R5_{tag}"



# ---------------------------------------------------------------------------- R6
BANK_CHANGE = re.compile(r"(new|change[ds]?|updated?)\s+(our\s+)?bank|bank\s+(account|details)\s+(have\s+)?chang|"
                         r"new\s+(a/c|account)|update\s+your\s+records", re.I)
FORCED = {"duplicate_credit", "unknown_party", "short_payment"}


class R6Gate(R5FineTuned):
    """R6: bounded autonomy. The model answers; CODE decides who acts.

    A line is handled automatically only if ALL hold:
      1. guardrail: no e-mail near this payment asks to change bank details (always a person);
      2. the category is not one our rules always send to a person (duplicate, unknown, short);
      3. System-1 gate: the model's probability for the option it chose >= threshold.
    The model's own "needs_review" text flag is recorded but NOT used (mode=prob), or
    also respected (mode=prob+flag).

    Why: Step 4 showed fine-tuning taught the model to stop asking, and with it to miss
    bank-detail changes (full fine-tune: 0/5). Safety cannot depend on learned habit.
    The threshold is the live "knob": higher = safer, fewer lines handled alone.
    """
    rung = "R6"

    def __init__(self, threshold="0.9", mode="prob", guardrail="1", **kw):
        super().__init__(**kw)
        self.score_option = True
        self.threshold, self.mode, self.guardrail = float(threshold), mode, guardrail != "0"
        self.config.update({"threshold": self.threshold, "gate_mode": self.mode, "guardrail": self.guardrail})
        tag = (kw.get("adapter") or kw.get("model", "")).rstrip("/").split("/")[-1]
        self.name = f"R6_{tag}"

    def post(self, e, p):
        emails = self._emails_of.get(e.entry_id, [])
        alert = any(BANK_CHANGE.search(r["body"]) for r in emails)
        prob = p.signals.get("option_prob")
        p.signals.update({"bank_change_alert": alert, "threshold": self.threshold})
        if p.error:
            p.needs_review = True
            return
        review = p.category in FORCED
        if self.guardrail and alert:
            review = True
        if prob is None or prob < self.threshold:
            review = True
        if self.mode == "prob+flag" and p.signals.get("model_flag"):
            review = True
        p.needs_review = review
        p.confidence = prob if prob is not None else 0.0


# ---------------------------------------------------------------------------- R7
class R7Frontier(R6Gate):
    """R7: Claude Opus 5.5 with the SAME retrieval, options and e-mails as R3 (comparison only).

    Shows the ceiling, its price and the data that leaves the business (egress meter).
    Routed through the same R6 rules (guardrail, forced reviews), so it is compared like for like;
    there is no token probability from the API, so its gate uses its own written needs_review flag.
    Key from the ANTHROPIC_API_KEY environment variable (Colab Secrets); never on the command line.
    Answers cached in runs/opus_cache.jsonl, so a re-run never pays twice.
    """
    rung = "R7"

    def __init__(self, model="claude-opus-5-5", rpm="30", **kw):
        kw.update(backend="anthropic", model=model, max_new_tokens=kw.get("max_new_tokens", "4096"),
                  threshold="0", mode="prob+flag")
        self._r7 = {"api_key_env": "ANTHROPIC_API_KEY", "rpm": float(rpm), "cache": "runs/opus_cache.jsonl"}
        super().__init__(**kw)
        self.score_option = False
        self.name = f"R7_{model}"
        self.config.update({"rpm": float(rpm), "frontier": True})

    def post(self, e, p):
        p.signals["option_prob"] = 1.0      # no probability from the API: gate on the flag only
        super().post(e, p)


class R6Control(R6Gate):
    """No-LLM control at R6: R3 options (pick the first) + the same guardrail and forced reviews.

    No probability gate (threshold 0): there is no model probability to gate on.
    Why: if this already passes the business bar, the AI must show what it adds on top.
    """
    rung = "R6-control"

    def __init__(self, **kw):
        kw.update(backend="fake", threshold="0")
        kw.setdefault("model", "first-option")
        super().__init__(**kw)
        self.name = "R6_control_first_option"
        self.config["note"] = "no LLM: picks M1, else U; guardrail + forced reviews only"
