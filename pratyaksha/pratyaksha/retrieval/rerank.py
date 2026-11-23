"""R2 reranking: a cross-encoder reads (narration, party) pairs together and re-orders.

Why a second step: R1's search looks at the query and each party separately and
compares them. A cross-encoder reads both side by side, so it can judge that
"SHRI GANESH TRD" really is "Shree Ganesh Traders" -- slower, but sharper.
Why only on the top few: it is too slow to run on every party.

Model: BAAI/bge-reranker-v2-m3 (Apache-2.0, ~568M parameters). We avoided
jina-colbert-v2 because its licence bans commercial use (mid-sem decision).
"""
from __future__ import annotations

from .index import clean_query


class CrossEncoderReranker:
    def __init__(self, model_id: str = "BAAI/bge-reranker-v2-m3", device: str = "cuda"):
        from sentence_transformers import CrossEncoder
        self.model = CrossEncoder(model_id, device=device, max_length=256)
        self.model_id = model_id

    def rerank(self, narration: str, candidates: list[tuple[str, str]]) -> list[tuple[str, float]]:
        """candidates: [(party_id, party_text)] -> [(party_id, score)] best first."""
        if not candidates:
            return []
        q = clean_query(narration)
        scores = self.model.predict([(q, t) for _, t in candidates])
        order = sorted(range(len(candidates)), key=lambda i: -float(scores[i]))
        return [(candidates[i][0], float(scores[i])) for i in order]


class KeepOrderReranker:
    """No-op reranker for tests."""
    model_id = "none"

    def rerank(self, narration, candidates):
        return [(pid, 1.0 / (i + 1)) for i, (pid, _) in enumerate(candidates)]
