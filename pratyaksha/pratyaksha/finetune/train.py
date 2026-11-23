"""R5 fine-tuning of Qwen3.5 on the R3 task. LoRA or full. Runs on a Colab T4.

    python -m pratyaksha.finetune.train --model Qwen/Qwen3.5-0.8B --mode lora --out models/r5_lora_0.8b
    python -m pratyaksha.finetune.train --model Qwen/Qwen3.5-0.8B --mode full --out models/r5_full_0.8b
    add --max-steps 5 for a quick dry run.

LoRA: freeze the model, train small add-on matrices (r=16) on every linear layer.
      Why: tiny memory and file size; the business keeps one base model and swaps adapters.
Full: train every weight (0.8B only; fits a T4 with 8-bit Adam + gradient checkpointing).
      Why: the mid-sem plan compares LoRA against full fine-tuning.

Loss is computed only on the answer tokens, not on the prompt. Why: we want the
model to learn to answer, not to memorise our prompts.

Writes <out>/train_log.json: steps, loss curve, wall time and trainable parameters,
so the one-time training cost is reported next to the per-task cost.
"""
from __future__ import annotations

import argparse
import json
import math
import random
import time
from pathlib import Path


def load(model_id: str, mode: str):
    import torch
    from transformers import AutoProcessor
    try:
        from transformers import AutoModelForMultimodalLM as AutoM
    except ImportError:
        from transformers import AutoModelForImageTextToText as AutoM
    proc = AutoProcessor.from_pretrained(model_id)
    dtype = torch.float16 if mode == "lora" else torch.float32   # full: fp32 master weights
    try:
        model = AutoM.from_pretrained(model_id, dtype=dtype, device_map="cuda")
    except TypeError:
        model = AutoM.from_pretrained(model_id, torch_dtype=dtype, device_map="cuda")
    model.config.use_cache = False
    model.gradient_checkpointing_enable()
    if mode == "lora":
        from peft import LoraConfig, get_peft_model
        model.enable_input_require_grads()
        cfg = LoraConfig(r=16, lora_alpha=32, lora_dropout=0.05, target_modules="all-linear",
                         exclude_modules=r".*visual.*", task_type="CAUSAL_LM")
        model = get_peft_model(model, cfg)
    return proc, model


def render_prompt(proc, messages):
    msgs = [{"role": m["role"], "content": [{"type": "text", "text": m["content"]}]} for m in messages]
    try:
        return proc.apply_chat_template(msgs, add_generation_prompt=True, tokenize=False, enable_thinking=False)
    except TypeError:
        return proc.apply_chat_template(msgs, add_generation_prompt=True, tokenize=False)


def encode(proc, row, max_len):
    tok = getattr(proc, "tokenizer", proc)
    p_ids = tok(render_prompt(proc, row["messages"]), add_special_tokens=False)["input_ids"]
    end = tok.eos_token or "<|im_end|>"
    a_ids = tok(row["target"] + end, add_special_tokens=False)["input_ids"]
    ids = (p_ids + a_ids)[-max_len:]
    labels = ([-100] * len(p_ids) + a_ids)[-max_len:]
    return ids, labels


def main():
    import torch
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="Qwen/Qwen3.5-0.8B")
    ap.add_argument("--data", default="data/sft/train.jsonl")
    ap.add_argument("--out", required=True)
    ap.add_argument("--mode", choices=["lora", "full"], default="lora")
    ap.add_argument("--epochs", type=float, default=2)
    ap.add_argument("--lr", type=float, default=None)
    ap.add_argument("--grad-accum", type=int, default=8)
    ap.add_argument("--max-len", type=int, default=1536)
    ap.add_argument("--max-steps", type=int, default=0)
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()
    lr = a.lr or (2e-4 if a.mode == "lora" else 1e-5)
    random.seed(a.seed)
    torch.manual_seed(a.seed)

    proc, model = load(a.model, a.mode)
    rows = [json.loads(l) for l in open(a.data)]
    data = [encode(proc, r, a.max_len) for r in rows]
    trunc = sum(1 for r in rows if len(encode(proc, r, 10**6)[0]) > a.max_len)
    params = [p for p in model.parameters() if p.requires_grad]
    n_train = sum(p.numel() for p in params)
    n_all = sum(p.numel() for p in model.parameters())
    if a.mode == "full":
        import bitsandbytes as bnb
        opt = bnb.optim.AdamW8bit(params, lr=lr, weight_decay=0.0)
    else:
        opt = torch.optim.AdamW(params, lr=lr, weight_decay=0.0)
    total = math.ceil(len(data) * a.epochs / a.grad_accum)
    if a.max_steps:
        total = min(total, a.max_steps)
    sched = torch.optim.lr_scheduler.LambdaLR(
        opt, lambda s: min(1.0, (s + 1) / max(1, total // 10)) * max(0.0, 1 - s / max(1, total)))
    scaler = torch.amp.GradScaler("cuda")
    print(f"examples {len(data)} (truncated {trunc}) | trainable {n_train:,} of {n_all:,} "
          f"({n_train/n_all:.2%}) | steps {total} | lr {lr}")

    model.train()
    order, step, micro, log, t0 = [], 0, 0, [], time.time()
    run_loss = 0.0
    while step < total:
        if not order:
            order = list(range(len(data)))
            random.shuffle(order)
        ids, labels = data[order.pop()]
        x = torch.tensor([ids], device="cuda")
        y = torch.tensor([labels], device="cuda")
        with torch.autocast("cuda", dtype=torch.float16):
            logits = model(input_ids=x, attention_mask=torch.ones_like(x)).logits
        # loss in fp32 on answer tokens only
        loss = torch.nn.functional.cross_entropy(logits[0, :-1].float(), y[0, 1:], ignore_index=-100)
        scaler.scale(loss / a.grad_accum).backward()
        run_loss += loss.item()
        micro += 1
        if micro % a.grad_accum == 0:
            scaler.unscale_(opt)
            torch.nn.utils.clip_grad_norm_(params, 1.0)
            scaler.step(opt)
            scaler.update()
            opt.zero_grad(set_to_none=True)
            sched.step()
            step += 1
            avg = run_loss / a.grad_accum
            run_loss = 0.0
            log.append({"step": step, "loss": round(avg, 4), "seconds": round(time.time() - t0, 1)})
            if step % 10 == 0 or step == total or step <= 3:
                print(f"  step {step}/{total} loss {avg:.4f} ({time.time()-t0:.0f}s)", flush=True)
    secs = time.time() - t0

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(out)
    proc.save_pretrained(out)
    info = {"base_model": a.model, "mode": a.mode, "examples": len(data), "truncated": trunc,
            "epochs": a.epochs, "steps": step, "lr": lr, "grad_accum": a.grad_accum,
            "trainable_params": n_train, "total_params": n_all, "train_seconds": round(secs, 1),
            "gpu": torch.cuda.get_device_name(0), "loss": log}
    (out / "train_log.json").write_text(json.dumps(info, indent=1))
    print(f"saved to {out} | {secs/60:.1f} min | final loss {log[-1]['loss'] if log else 'n/a'}")


if __name__ == "__main__":
    main()
