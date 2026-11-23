"""R1 retrieval: find which customers (or suppliers) a bank narration is about.

Two searches, combined:

* Keyword search (BM25) over character 3-grams of each party's names and aliases.
  Why 3-grams and not words: bank narrations cut names off ("SHREE GANESH TR"),
  drop spaces (UPI handles: "shreeganesh@ybl") and have typos. Word search fails
  on all three; overlapping 3-letter pieces still match.
* Meaning search (bge-m3 embeddings), optional. Why optional: it needs a GPU-
  sized model download; the tests run without it.

Combined with Reciprocal Rank Fusion (RRF): each list votes 1/(60 + rank).
Why RRF: the two scores are on different scales; ranks are comparable.
"""
from __future__ import annotations

import re

from rank_bm25 import BM25Okapi

_norm = lambda s: re.sub(r"[^a-z0-9]", "", s.lower())
NOISE = re.compile(r"\b(NEFT|RTGS|IMPS|UPI|P2A|CHQ|DEP|CLG|BY|TO|DR|PAYMENT|[A-Z]{4}N\d+|\d{6,})\b", re.I)


def grams(s: str, n: int = 3) -> list[str]:
    s = _norm(s)
    return [s[i:i + n] for i in range(max(1, len(s) - n + 1))] if s else []


def clean_query(narration: str) -> str:
    """Strip payment-rail noise (mode, UTR numbers, bank codes) before searching."""
    q = NOISE.sub(" ", narration)
    q = re.sub(r"WWI/\S+", " ", q)          # invoice refs are not names
    q = re.sub(r"@\w+", " ", q)             # UPI handle suffix
    return q


class PartyIndex:
    def __init__(self, parties: dict[str, dict], dense_model: str | None = None, device: str = "cuda"):
        """parties: id -> {"name": ..., "aliases": [...]}"""
        self.ids = list(parties)
        self.texts = [" | ".join([p["name"]] + list(p.get("aliases", []))) for p in parties.values()]
        self.bm25 = BM25Okapi([grams(t) for t in self.texts])
        self.dense = None
        if dense_model:
            from sentence_transformers import SentenceTransformer
            self.dense = SentenceTransformer(dense_model, device=device)
            self.emb = self.dense.encode(self.texts, normalize_embeddings=True, batch_size=64)

    def search(self, narration: str, k: int = 5) -> list[tuple[str, float]]:
        q = clean_query(narration)
        bm = self.bm25.get_scores(grams(q))
        lists = [sorted(range(len(self.ids)), key=lambda i: -bm[i])]
        if self.dense is not None:
            qe = self.dense.encode([q], normalize_embeddings=True)[0]
            sims = self.emb @ qe
            lists.append(sorted(range(len(self.ids)), key=lambda i: -sims[i]))
        fused = {}
        for lst in lists:
            for rank, i in enumerate(lst[:50]):
                fused[i] = fused.get(i, 0.0) + 1.0 / (60 + rank)
        top = sorted(fused, key=lambda i: -fused[i])[:k]
        return [(self.ids[i], fused[i]) for i in top]


def build_indexes(ledger, dense_model: str | None = None, device: str = "cuda"):
    cust = {cid: {"name": c["legal_name"], "aliases": c["aliases"]} for cid, c in ledger.customers.items()}
    sup = {sid: {"name": s["name"], "aliases": []} for sid, s in ledger.suppliers.items()}
    return PartyIndex(cust, dense_model, device), PartyIndex(sup, None, device)
