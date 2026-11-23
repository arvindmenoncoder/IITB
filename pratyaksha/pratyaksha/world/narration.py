"""Bank-statement narrations in the styles Indian banks actually print.

Each call returns (clean, stress). The stress version applies the damage real
statements show: truncation, alias or initials instead of the legal name,
dropped invoice references and stray typos.
"""
from __future__ import annotations

import random


def _utr(rng, ifsc_prefix: str) -> str:
    return f"{ifsc_prefix[:4]}N{rng.randint(10**11, 10**12 - 1)}"


def _typo(rng, s: str) -> str:
    if len(s) < 6:
        return s
    i = rng.randrange(1, len(s) - 1)
    op = rng.choice(["drop", "swap", "dup"])
    if op == "drop":
        return s[:i] + s[i + 1:]
    if op == "swap":
        return s[:i] + s[i + 1] + s[i] + s[i + 2:]
    return s[:i] + s[i] + s[i:]


def _fmt(rng, mode, name, bank, ref, d, outward):
    bank_name, ifsc = bank
    direction = "TO" if outward else "BY"
    if mode == "NEFT":
        s = f"NEFT-{_utr(rng, ifsc)}-{name}"
        if ref:
            s += f"-{ref}"
        return ("DR-" + s) if outward else s
    if mode == "RTGS":
        return f"RTGS {direction} {name}-{ifsc}{rng.randint(1000, 9999)}-{_utr(rng, ifsc)}" + (f" {ref}" if ref else "")
    if mode == "IMPS":
        short = name.replace(" ", "")[:12]
        return f"IMPS/P2A/{rng.randint(10**11, 10**12 - 1)}/{short}/{bank_name}" + (f"/{ref}" if ref else "")
    if mode == "UPI":
        handle = name.replace(" ", "").lower()[:12] + rng.choice(["@okhdfcbank", "@oksbi", "@ybl", "@paytm"])
        return f"UPI/{rng.randint(10**11, 10**12 - 1)}/{handle}/" + (ref if ref else "Payment")
    # cheque deposit: name often absent
    return f"CHQ DEP {rng.randint(100000, 999999)} {bank_name} CLG" + (f" {name[:10]}" if rng.random() < 0.5 else "")


def make_narration(rng: random.Random, mode: str, legal_name: str, aliases: list,
                   bank, ref: str, d, outward: bool = False) -> tuple[str, str]:
    clean = _fmt(rng, mode, legal_name.upper(), bank, ref, d, outward)
    name = rng.choice(aliases) if aliases and rng.random() < 0.7 else legal_name.upper()
    if rng.random() < 0.25:
        name = _typo(rng, name)
    sref = ref if rng.random() < 0.5 else ""
    stress = _fmt(rng, mode, name, bank, sref, d, outward)
    if rng.random() < 0.35:
        stress = stress[: rng.randint(28, 40)]  # many banks cut narrations at 30-40 chars
    return clean, stress
