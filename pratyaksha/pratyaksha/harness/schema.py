"""What every system returns for one bank entry, plus the per-step trace."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict


@dataclass
class Step:
    """One step in a system's pipeline: shown live in the demo trace."""
    name: str                 # e.g. "system1_gate", "retrieve", "llm"
    seconds: float
    tokens_in: int = 0
    tokens_out: int = 0
    bytes_out: int = 0        # bytes sent off the machine (data egress)
    local: bool = True
    note: str = ""


@dataclass
class Prediction:
    entry_id: str
    category: str
    party_id: str | None = None
    invoice_ids: list[str] = field(default_factory=list)
    needs_review: bool = False
    confidence: float = 1.0
    explanation: str = ""
    raw_output: str = ""      # model text, checked for restricted-field leaks
    retrieved_invoice_ids: list[str] = field(default_factory=list)  # in rank order, for error analysis
    retrieved_party_ids: list[str] = field(default_factory=list)    # in rank order: was the right party found?
    options: list[dict] = field(default_factory=list)  # R3+: computed answer options shown to the model
    signals: dict = field(default_factory=dict)        # R6: option probability, model flag, guardrail hits
    steps: list[Step] = field(default_factory=list)
    error: str = ""           # parse failure, timeout, ...

    def to_dict(self) -> dict:
        return asdict(self)
