"""Rungs R0, R1, R2 of the ladder. One change per rung.

R0  small model, NO retrieval. It sees only the bank line.
    Why: "fail first" -- shows the model cannot know the business's records.
R1  + retrieval: the top-k parties (BM25 3-grams, optionally + bge-m3) and their
    open invoices on that date (no look-ahead) go into the prompt.
    Why: the model can now see the books.
R2  + reranking: a cross-encoder re-orders R1's parties; we keep fewer, better ones.
    Why: if the right party is found but ranked low, the model gets confused by
    the wrong parties' invoices. Fewer, better candidates = shorter, cleaner prompt.

The language model never does arithmetic in our design; R3 will add computed
amount matches. In R1/R2 the model must match amounts itself -- a known weakness
we expect the error log to show.
"""
from __future__ import annotations

import json
import re
import time

from ..harness.schema import Prediction, Step
from ..world.names import inr

CATS = ["full_payment", "clubbed_payment", "tds_deduction", "short_payment", "duplicate_credit",
        "unknown_party", "bank_charges", "interest_credit", "supplier_payment"]
REVIEW_ALWAYS = {"duplicate_credit", "unknown_party"}

SYSTEM = ("You reconcile bank-statement lines for Wide World Importers India Pvt Ltd, a wholesaler. "
          "Answer with ONE JSON object and nothing else.")

CATEGORY_HELP = """CATEGORIES
full_payment: credit pays exactly one invoice
clubbed_payment: credit pays two or more invoices exactly
tds_deduction: credit = invoice total(s) minus TDS (0.1%, 1% or 2% of taxable value)
short_payment: credit pays one invoice partly (a little less than outstanding)
duplicate_credit: the same credit was posted twice
unknown_party: payer is not one of the listed parties
bank_charges: bank fee (debit)
interest_credit: interest paid by the bank
supplier_payment: payment to one of our suppliers (debit)"""

ANSWER_FMT = ('Reply as JSON: {"category": "<one category>", "party_id": "<id or null>", '
              '"invoice_ids": ["<id>", ...], "needs_review": true|false, "confidence": <0 to 1>}\n'
              "Set needs_review to true when you are not sure, and always for duplicate_credit, "
              "unknown_party, or a short_payment.")


def bank_line(e) -> str:
    amt = f"credit Rs {inr(e.credit)}" if e.credit else f"debit Rs {inr(e.debit)}"
    return f"BANK LINE\ndate: {e.value_date.isoformat()} | {amt} | narration: {e.narration}"


def parse_answer(text: str) -> tuple[dict | None, str]:
    """Pull the first JSON object out of model text. Returns (dict, error)."""
    text = re.sub(r"<think>.*?(</think>|$)", "", text, flags=re.S)   # drop any reasoning preamble
    if text.lstrip().startswith("Thinking Process") and "{" not in text:
        return None, "thinking_cutoff"     # 4B default: reasoning in plain text, cut off before the answer
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None, "no_json"
    blob = m.group(0)
    for cand in (blob, blob[: blob.rfind("}") + 1]):
        try:
            return json.loads(cand), ""
        except json.JSONDecodeError:
            pass
    # model sometimes writes two objects or trailing text: take the shortest valid prefix
    depth = 0
    for i, ch in enumerate(blob):
        depth += ch == "{"
        depth -= ch == "}"
        if depth == 0:
            try:
                return json.loads(blob[: i + 1]), ""
            except json.JSONDecodeError:
                break
    return None, "bad_json"


def to_prediction(e, ans: dict | None, err: str, allowed_parties: set, allowed_invoices: set) -> Prediction:
    p = Prediction(entry_id=e.entry_id, category="unknown_party", needs_review=True, confidence=0.0)
    if ans is None:
        p.error = err
        return p
    cat = str(ans.get("category", "")).strip().lower()
    p.category = cat if cat in CATS else "unknown_party"
    if cat not in CATS:
        p.error = f"bad_category:{cat[:30]}"
    pid = ans.get("party_id")
    p.party_id = pid if isinstance(pid, str) and pid in allowed_parties else None
    inv = ans.get("invoice_ids") or []
    if isinstance(inv, str):
        inv = [inv]
    # an invoice the system never showed the model is a hallucination: drop it
    p.invoice_ids = [i for i in inv if isinstance(i, str) and i in allowed_invoices]
    try:
        p.confidence = max(0.0, min(1.0, float(ans.get("confidence", 0.5))))
    except (TypeError, ValueError):
        p.confidence = 0.5
    p.needs_review = bool(ans.get("needs_review", True)) or p.category in REVIEW_ALWAYS \
        or p.category == "short_payment"
    return p


class LLMRung:
    """Shared machinery. Subclasses decide what goes into the prompt."""
    name = "llm"
    rung = "R?"

    def __init__(self, backend="hf", model="Qwen/Qwen3.5-0.8B", batch="8", base_url="",
                 api_key="none", max_new_tokens="160", dtype="float16", adapter="", **kw):
        from ..llm.backend import make_backend
        from ..llm.device import pick
        self.batch_size = int(batch)
        kw["device"] = pick(kw.get("device", "auto"))   # one device for model, reranker and dense search
        bk = {"hf": dict(model_id=model, dtype=dtype, max_new_tokens=int(max_new_tokens), adapter=adapter,
                         device=kw["device"]),
              "openai": dict(base_url=base_url or "http://127.0.0.1:8080/v1", model_id=model,
                             api_key=api_key, max_new_tokens=int(max_new_tokens),
                             **getattr(self, "_r7", {}),
                             local=not getattr(self, "_r7", None)),
              "fake": {},
              "anthropic": dict(model_id=model, max_new_tokens=int(max_new_tokens), **getattr(self, "_r7", {}))}[backend]
        self.backend = make_backend(backend, **bk)
        self.config = {"rung": self.rung, "backend": backend, "model": model, "batch": self.batch_size,
                       "adapter": adapter or "none", "device": kw["device"]}
        self.extra_init(**kw)
        self.name = f"{self.rung}_{model.split('/')[-1]}"

    def extra_init(self, **kw):
        pass

    # subclasses return (user_prompt, allowed_parties, allowed_invoices, steps, retrieved_parties, retrieved_invoices)
    def build(self, e, led):
        raise NotImplementedError

    def predict(self, e, led) -> Prediction:
        return self.predict_batch([e], led)[0]

    def predict_batch(self, entries, led) -> list[Prediction]:
        built = [self.build(e, led) for e in entries]
        msgs = [[{"role": "system", "content": SYSTEM}, {"role": "user", "content": b[0]}] for b in built]
        gens = self.backend.generate(msgs)
        preds = []
        for e, b, g in zip(entries, built, gens):
            ans, err = parse_answer(g.text)
            p = to_prediction(e, ans, err, b[1], b[2])
            p.raw_output = g.text
            p.steps = b[3] + [Step("llm", g.seconds, g.tokens_in, g.tokens_out, g.bytes_out, g.local,
                                   self.config["model"])]
            p.retrieved_party_ids, p.retrieved_invoice_ids = b[4], b[5]
            preds.append(p)
        return preds


class R0NoRetrieval(LLMRung):
    rung = "R0"

    def build(self, e, led):
        u = "\n\n".join([bank_line(e), "You have no access to our customer list or invoices.",
                         CATEGORY_HELP, ANSWER_FMT])
        return u, set(), set(), [], [], []


class R1RAG(LLMRung):
    rung = "R1"

    def extra_init(self, k="5", dense="", max_invoices="25", device="cuda", **kw):
        self.k, self.max_inv = int(k), int(max_invoices)
        self.dense_model = dense or None   # e.g. "BAAI/bge-m3"
        self.device = device
        self._idx = None
        self.config.update({"k": self.k, "dense": self.dense_model or "none", "max_invoices": self.max_inv})

    def indexes(self, led):
        if self._idx is None or self._idx[0] is not led:
            from ..retrieval.index import build_indexes
            self._idx = (led, *build_indexes(led, self.dense_model, self.device))
        return self._idx[1], self._idx[2]

    def candidate_parties(self, e, led) -> tuple[list[str], list[Step]]:
        cidx, sidx = self.indexes(led)
        t0 = time.perf_counter()
        hits = cidx.search(e.narration, self.k)
        if e.debit:
            hits = sidx.search(e.narration, min(3, self.k)) + hits[:2]
        return [h[0] for h in hits], [Step("retrieve", time.perf_counter() - t0, note=f"top{self.k}")]

    def build(self, e, led):
        parties, steps = self.candidate_parties(e, led)
        rows, invs = [], []
        for pid in parties:
            if pid in led.customers:
                c = led.customers[pid]
                rows.append(f"{pid} | {c['legal_name']} | {'; '.join(c['aliases'][1:])}")
            else:
                rows.append(f"{pid} | {led.suppliers[pid]['name']} | supplier")
        cust = [p for p in parties if p in led.customers]
        if e.credit and cust:
            rank = {p: i for i, p in enumerate(cust)}
            open_inv = sorted(led.open_invoices(e, cust),
                              key=lambda x: (rank[x["customer_id"]], x["invoice_date"]))[: self.max_inv]
            invs = [i["invoice_id"] for i in open_inv]
            inv_rows = [f"{i['invoice_id']} | {i['customer_id']} | {i['invoice_date'].isoformat()} | "
                        f"total {inr(i['total'])} | outstanding {inr(i['outstanding'])} | "
                        f"taxable {inr(i['taxable_value'])}" for i in open_inv]
        else:
            inv_rows = []
        parts = [bank_line(e),
                 "CANDIDATE PARTIES (id | name | also appears as)\n" + "\n".join(rows),
                 "OPEN INVOICES of these parties on that date (id | party | date | total | outstanding | taxable)\n"
                 + ("\n".join(inv_rows) if inv_rows else "(none)"),
                 CATEGORY_HELP, ANSWER_FMT]
        return "\n\n".join(parts), set(parties), set(invs), steps, parties, invs


class R2Rerank(R1RAG):
    rung = "R2"

    def extra_init(self, keep="3", reranker="BAAI/bge-reranker-v2-m3", **kw):
        kw.setdefault("k", "10")      # retrieve wider, then rerank and keep fewer
        super().extra_init(**kw)
        self.keep = int(keep)
        if reranker == "none":
            from ..retrieval.rerank import KeepOrderReranker
            self.rr = KeepOrderReranker()
        else:
            from ..retrieval.rerank import CrossEncoderReranker
            self.rr = CrossEncoderReranker(reranker, self.device)
        self.config.update({"keep": self.keep, "reranker": self.rr.model_id})

    def candidate_parties(self, e, led):
        parties, steps = super().candidate_parties(e, led)
        t0 = time.perf_counter()
        texts = []
        for pid in parties:
            if pid in led.customers:
                c = led.customers[pid]
                texts.append((pid, " | ".join([c["legal_name"]] + c["aliases"])))
            else:
                texts.append((pid, led.suppliers[pid]["name"]))
        ranked = self.rr.rerank(e.narration, texts)[: self.keep]
        steps.append(Step("rerank", time.perf_counter() - t0, note=f"keep{self.keep}"))
        return [pid for pid, _ in ranked], steps
