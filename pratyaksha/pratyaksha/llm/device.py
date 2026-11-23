"""Pick where a model runs: NVIDIA GPU (Colab), Apple GPU (Mac, "mps") or CPU.

Why: the same code must run on the Colab T4 for training and on the MacBook for the
owned-machine measurements. Asking for "cuda" on a Mac falls back to the Mac's own GPU,
and the device actually used is printed and stored in each run's config.
"""
from __future__ import annotations


def pick(requested: str = "auto") -> str:
    requested = (requested or "auto").lower()
    try:
        import torch
    except ImportError:
        return "cpu"
    has_cuda = torch.cuda.is_available()
    has_mps = getattr(torch.backends, "mps", None) is not None and torch.backends.mps.is_available()
    if requested == "cpu":
        return "cpu"
    if requested == "mps":
        return "mps" if has_mps else "cpu"
    if requested in ("auto", "cuda"):
        if has_cuda:
            return "cuda"
        chosen = "mps" if has_mps else "cpu"
        if requested == "cuda":
            print(f"[device] cuda not available here; using {chosen}")
        return chosen
    return requested


def synchronize(device: str) -> None:
    """Wait for the GPU to finish, so timings measure the real work."""
    import torch
    if device == "cuda":
        torch.cuda.synchronize()
    elif device == "mps":
        torch.mps.synchronize()
