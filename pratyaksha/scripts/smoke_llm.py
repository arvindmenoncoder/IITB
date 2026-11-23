"""Load a model once and ask one tiny question. Checks the GPU setup before long runs.

    python scripts/smoke_llm.py --model Qwen/Qwen3.5-0.8B [--dtype float16]
"""
import argparse, sys, time
sys.path.insert(0, ".")
from pratyaksha.llm.backend import HFBackend

ap = argparse.ArgumentParser()
ap.add_argument("--model", default="Qwen/Qwen3.5-0.8B")
ap.add_argument("--dtype", default="float16")
a = ap.parse_args()
t0 = time.time()
b = HFBackend(a.model, a.dtype, max_new_tokens=40)
print(f"loaded in {time.time()-t0:.0f}s")
g = b.generate([[{"role": "user", "content": 'Reply with exactly this JSON: {"ok": true}'}]])[0]
print("model said:", repr(g.text))
print(f"tokens in/out {g.tokens_in}/{g.tokens_out}, {g.seconds:.2f}s, {g.tokens_out/max(g.seconds,1e-6):.1f} tokens/s")
print("PASS" if '"ok"' in g.text else "CHECK: output looks wrong; try --dtype float32")
