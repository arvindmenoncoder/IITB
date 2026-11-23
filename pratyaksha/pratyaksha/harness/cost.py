"""Rupee cost of a run, with every assumption visible and overridable.

Owned hardware: operating cost (power x time) is reported separately from
hardware amortisation, so the capital cost is never hidden inside a per-query
number. Rented GPU and API costs use observed time / tokens.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict


@dataclass
class CostAssumptions:
    # owned laptop (MacBook Pro M1 Pro) -- edit to match your machine
    owned_watts: float = 35.0            # package power under LLM load (measure with `sudo powermetrics`)
    inr_per_kwh: float = 8.0             # typical Indian commercial tariff; edit to your bill
    hardware_inr: float = 2_40_000.0     # purchase price
    hardware_life_hours: float = 3 * 250 * 8   # 3 years x 250 days x 8 h
    # rented GPU (Colab / cloud T4)
    gpu_inr_per_hour: float = 30.0       # set from what you actually pay; free Colab = 0
    # API (frontier reference), USD per 1M tokens
    api_usd_in_per_m: float = 0.75
    api_usd_out_per_m: float = 3.75
    usd_inr: float = 88.0                # check the day's rate before final numbers

    def as_dict(self):
        return asdict(self)


def per_task_inr(seconds: float, tokens_in: int, tokens_out: int, mode: str,
                 a: CostAssumptions) -> dict:
    """mode: 'owned' | 'gpu' | 'api'. Returns operating and amortisation in ₹."""
    if mode == "owned":
        op = a.owned_watts * seconds / 3.6e6 * a.inr_per_kwh
        amort = a.hardware_inr / a.hardware_life_hours * seconds / 3600
    elif mode == "gpu":
        op, amort = a.gpu_inr_per_hour * seconds / 3600, 0.0
    elif mode == "api":
        op = (tokens_in * a.api_usd_in_per_m + tokens_out * a.api_usd_out_per_m) / 1e6 * a.usd_inr
        amort = 0.0
    else:
        raise ValueError(mode)
    return {"operating_inr": op, "amortisation_inr": amort}
