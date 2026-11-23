"""Three ways to call a language model, one interface.

    backend.generate(list_of_message_lists) -> list[Generation]

* HFBackend      -- loads a Hugging Face model on the GPU (Colab) and batches.
* OpenAIBackend  -- any OpenAI-compatible server: mlx_lm.server on the Mac,
                    vLLM, or a cloud API (R7). Measures bytes sent off-machine.
* FakeBackend    -- no model; used by the tests so the pipeline is checked on CPU.

Why one interface: every rung uses the same code; only the backend changes, so
"what changed" between two runs is exactly one thing.
"""
from __future__ import annotations

import json
import time
import urllib.request
from dataclasses import dataclass


@dataclass
class Generation:
    text: str
    tokens_in: int
    tokens_out: int
    seconds: float           # wall time for this item (batch time split evenly)
    bytes_out: int = 0       # bytes that left the machine
    local: bool = True
    option_prob: float | None = None   # R6: model's probability for the option id it wrote


class HFBackend:
    """Hugging Face transformers on a GPU: CUDA (Colab T4) or Apple MPS (MacBook).

    Qwen3.5 is published as an image-text-to-text model; we send text only.
    T4 has no fast bfloat16, so we load float16.
    """

    def __init__(self, model_id: str = "Qwen/Qwen3.5-0.8B", dtype: str = "float16",
                 max_new_tokens: int = 160, adapter: str = "", device: str = "auto"):
        import torch
        from .device import pick
        self.device = pick(device)   # "cuda" on Colab, "mps" (Apple GPU) on the Mac
        from transformers import AutoProcessor
        try:
            from transformers import AutoModelForMultimodalLM as AutoM
        except ImportError:  # older transformers
            from transformers import AutoModelForImageTextToText as AutoM
        self.torch = torch
        self.model_id, self.max_new_tokens = model_id, max_new_tokens
        self.processor = AutoProcessor.from_pretrained(model_id)
        self.tok = getattr(self.processor, "tokenizer", self.processor)
        self.tok.padding_side = "left"
        if self.tok.pad_token is None:
            self.tok.pad_token = self.tok.eos_token
        try:
            self.model = AutoM.from_pretrained(model_id, dtype=getattr(torch, dtype))
        except TypeError:  # transformers < 4.56 calls it torch_dtype
            self.model = AutoM.from_pretrained(model_id, torch_dtype=getattr(torch, dtype))
        self.model.to(self.device)
        # Explicit stop signals. Why: the fine-tuned 2B model answered, then kept writing a fake next
        # turn ("user / BANK LINE ...") until the token limit, because generation did not stop at <|im_end|>.
        stop = {self.tok.eos_token_id}
        for t in ("<|im_end|>", "<|endoftext|>"):
            i = self.tok.convert_tokens_to_ids(t)
            if isinstance(i, int) and i != getattr(self.tok, "unk_token_id", None):
                stop.add(i)
        self.stop_ids = sorted(i for i in stop if i is not None)
        if adapter:   # R5 LoRA: load the trained add-on and fold it into the weights (no speed cost)
            from peft import PeftModel
            self.model = PeftModel.from_pretrained(self.model, adapter).merge_and_unload()
        self.model.eval()

    def _render(self, messages: list[dict]) -> str:
        msgs = [{"role": m["role"], "content": [{"type": "text", "text": m["content"]}]} for m in messages]
        try:  # Qwen3.x: answer directly, no "thinking" preamble (confirmed 23 Nov: 4B wrote 'Thinking Process:' until the token limit)
            return self.processor.apply_chat_template(msgs, add_generation_prompt=True, tokenize=False,
                                                      enable_thinking=False)
        except TypeError:
            return self.processor.apply_chat_template(msgs, add_generation_prompt=True, tokenize=False)

    def generate(self, batch: list[list[dict]], score_option: bool = False) -> list[Generation]:
        torch = self.torch
        texts = [self._render(m) for m in batch]
        enc = self.tok(texts, return_tensors="pt", padding=True).to(self.model.device)
        from .device import synchronize
        synchronize(self.device)
        t0 = time.perf_counter()
        with torch.no_grad():
            res = self.model.generate(**enc, max_new_tokens=self.max_new_tokens, do_sample=False,
                                      pad_token_id=self.tok.pad_token_id, eos_token_id=self.stop_ids,
                                      output_scores=score_option, return_dict_in_generate=True)
        synchronize(self.device)
        dt = (time.perf_counter() - t0) / len(batch)
        out = res.sequences
        new = out[:, enc["input_ids"].shape[1]:]
        out_list = []
        probs = None
        if score_option:   # softmax per generation step: (steps, batch, vocab) -> chosen-token probabilities
            probs = [torch.softmax(sc.float(), dim=-1) for sc in res.scores]
        for i in range(len(batch)):
            n_in = int(enc["attention_mask"][i].sum())
            ids = new[i]
            n_out = int((ids != self.tok.pad_token_id).sum())   # tokens actually generated (before padding)
            text = self.tok.decode(ids, skip_special_tokens=True)
            g = Generation(text, n_in, n_out, dt)
            if probs is not None:
                g.option_prob = option_probability(self.tok, ids.tolist(), [p[i] for p in probs])
            out_list.append(g)
        return out_list


def option_probability(tok, ids: list[int], step_probs) -> float | None:
    """Probability the model gave to the option id it wrote, e.g. "M2" in {"option": "M2", ...}.

    Product of the probabilities of the tokens that spell the option value. Why: this is
    the model's real confidence (System-1 signal), unlike a "confidence" it writes as text.
    """
    import re
    pieces, text = [], ""
    for k in range(len(ids)):
        nxt = tok.decode(ids[:k + 1], skip_special_tokens=True)
        pieces.append((len(text), len(nxt)))
        text = nxt
    m = re.search(r'"option"\s*:\s*"', text)
    if not m:
        return None
    start, end = m.end(), text.find('"', m.end())
    if end <= start:
        return None
    p = 1.0
    used = False
    for k, (a, b) in enumerate(pieces):
        if k < len(step_probs) and b > start and a < end:
            p *= float(step_probs[k][ids[k]])
            used = True
    return p if used else None


class OpenAIBackend:
    """OpenAI-compatible /v1/chat/completions: mlx_lm.server on the Mac, or a cloud API (R7).

    One request per item (true latency). For cloud use (local=False):
      * every byte sent is counted as data leaving the business (egress meter);
      * the key is read from an environment variable, never passed on the command line or saved;
      * answers are cached on disk by prompt hash, so a re-run never spends free-tier quota twice;
      * requests are spaced to stay under a requests-per-minute limit, with retries on HTTP 429.
    """

    def __init__(self, base_url: str = "http://127.0.0.1:8080/v1", model_id: str = "default",
                 api_key: str = "none", max_new_tokens: int = 160, local: bool = True,
                 api_key_env: str = "", reasoning_effort: str = "", rpm: float = 0,
                 cache: str = ""):
        import os
        self.url = base_url.rstrip("/") + "/chat/completions"
        self.model_id, self.max_new_tokens, self.local = model_id, max_new_tokens, local
        self.key = os.environ.get(api_key_env, "") if api_key_env else api_key
        if api_key_env and not self.key:
            raise RuntimeError(f"set the {api_key_env} environment variable (see notebook)")
        self.reasoning_effort, self.rpm = reasoning_effort, float(rpm or 0)
        self.cache_path = cache
        self.cache = {}
        if cache and os.path.exists(cache):
            for line in open(cache):
                d = json.loads(line)
                self.cache[d["key"]] = d
        self._last_call = 0.0

    def _post(self, body: bytes) -> dict:
        import urllib.error
        for attempt in range(6):
            if self.rpm:
                wait = 60.0 / self.rpm - (time.time() - self._last_call)
                if wait > 0:
                    time.sleep(wait)
            self._last_call = time.time()
            req = urllib.request.Request(self.url, data=body, headers={
                "Content-Type": "application/json", "Authorization": f"Bearer {self.key}"})
            try:
                with urllib.request.urlopen(req, timeout=300) as r:
                    return json.loads(r.read())
            except urllib.error.HTTPError as e:
                if e.code in (429, 500, 503) and attempt < 5:
                    time.sleep(min(60, 5 * 2 ** attempt))   # back off and retry
                    continue
                raise RuntimeError(f"HTTP {e.code}: {e.read()[:300]!r}") from None
        raise RuntimeError("too many retries")

    def generate(self, batch: list[list[dict]], score_option: bool = False) -> list[Generation]:
        import hashlib
        res = []
        for messages in batch:
            payload = {"model": self.model_id, "messages": messages, "temperature": 0,
                       "max_tokens": self.max_new_tokens}
            if self.reasoning_effort:
                payload["reasoning_effort"] = self.reasoning_effort
            body = json.dumps(payload).encode()
            key = hashlib.sha256(body).hexdigest()
            if key in self.cache:
                c = self.cache[key]
                res.append(Generation(c["text"], c["tin"], c["tout"], c["seconds"],
                                      bytes_out=0 if self.local else len(body), local=self.local))
                continue
            t0 = time.perf_counter()
            data = self._post(body)
            dt = time.perf_counter() - t0
            u = data.get("usage", {}) or {}
            text = (data["choices"][0]["message"].get("content") or "")
            g = Generation(text, u.get("prompt_tokens", 0), u.get("completion_tokens", 0), dt,
                           bytes_out=0 if self.local else len(body), local=self.local)
            res.append(g)
            if self.cache_path:
                rec = {"key": key, "text": text, "tin": g.tokens_in, "tout": g.tokens_out, "seconds": dt}
                self.cache[key] = rec
                with open(self.cache_path, "a") as f:
                    f.write(json.dumps(rec) + "\n")
        return res


class AnthropicBackend(OpenAIBackend):
    """Claude API, native Messages endpoint (R7 frontier reference: Claude Opus 5.5).

    Why native and not the OpenAI-compatible layer: Opus 5.5 always thinks, and thinking is
    billed as output; the native response separates thinking blocks from the answer text,
    and reports exact input/output token counts for the cost meter.
    Inherits caching, retries, request spacing and the egress meter from OpenAIBackend.
    """

    def __init__(self, model_id: str = "claude-opus-5-5", max_new_tokens: int = 4096,
                 api_key_env: str = "ANTHROPIC_API_KEY", rpm: float = 30, cache: str = "", **kw):
        super().__init__(base_url="https://api.anthropic.com/v1", model_id=model_id,
                         max_new_tokens=max_new_tokens, local=False, api_key_env=api_key_env,
                         rpm=rpm, cache=cache)
        self.url = "https://api.anthropic.com/v1/messages"

    def _post(self, body: bytes) -> dict:
        import urllib.error
        for attempt in range(6):
            if self.rpm:
                wait = 60.0 / self.rpm - (time.time() - self._last_call)
                if wait > 0:
                    time.sleep(wait)
            self._last_call = time.time()
            req = urllib.request.Request(self.url, data=body, headers={
                "content-type": "application/json", "x-api-key": self.key,
                "anthropic-version": "2023-06-01"})
            try:
                with urllib.request.urlopen(req, timeout=600) as r:
                    return json.loads(r.read())
            except urllib.error.HTTPError as e:
                if e.code in (429, 500, 529) and attempt < 5:
                    time.sleep(min(60, 5 * 2 ** attempt))
                    continue
                raise RuntimeError(f"HTTP {e.code}: {e.read()[:300]!r}") from None
        raise RuntimeError("too many retries")

    def generate(self, batch: list[list[dict]], score_option: bool = False) -> list[Generation]:
        import hashlib
        res = []
        for messages in batch:
            system = "\n".join(m["content"] for m in messages if m["role"] == "system")
            payload = {"model": self.model_id, "max_tokens": self.max_new_tokens,
                       "messages": [m for m in messages if m["role"] != "system"]}
            if system:
                payload["system"] = system
            body = json.dumps(payload).encode()
            key = hashlib.sha256(body).hexdigest()
            if key in self.cache:
                c = self.cache[key]
                res.append(Generation(c["text"], c["tin"], c["tout"], c["seconds"],
                                      bytes_out=len(body), local=False))
                continue
            t0 = time.perf_counter()
            data = self._post(body)
            dt = time.perf_counter() - t0
            text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
            u = data.get("usage", {}) or {}
            g = Generation(text, u.get("input_tokens", 0), u.get("output_tokens", 0), dt,
                           bytes_out=len(body), local=False)
            res.append(g)
            if self.cache_path:
                rec = {"key": key, "text": text, "tin": g.tokens_in, "tout": g.tokens_out, "seconds": dt}
                self.cache[key] = rec
                with open(self.cache_path, "a") as f:
                    f.write(json.dumps(rec) + "\n")
        return res


class FakeBackend:
    """Deterministic stand-in: picks the first listed invoice. Used only by tests."""

    def generate(self, batch: list[list[dict]], score_option: bool = False) -> list[Generation]:
        import re
        out = []
        for messages in batch:
            u = messages[-1]["content"]
            if "MATCH OPTIONS" in u:   # R3: pick the first computed option
                oid = "M1" if re.search(r"^M1 \|", u, re.M) else "U"
                out.append(Generation(json.dumps({"option": oid, "needs_review": oid == "U",
                                                  "confidence": 0.8, "reason": "first option"}),
                                      len(u) // 4, 25, 0.001,
                                      option_prob=(0.97 if oid == "M1" else 0.5) if score_option else None))
                continue
            inv = re.search(r"^(WWI/\S+) \| (C\d+)", u, re.M)
            if inv:
                ans = {"category": "full_payment", "party_id": inv.group(2), "invoice_ids": [inv.group(1)],
                       "needs_review": False, "confidence": 0.9}
            else:
                ans = {"category": "unknown_party", "party_id": None, "invoice_ids": [],
                       "needs_review": True, "confidence": 0.2}
            out.append(Generation("```json\n" + json.dumps(ans) + "\n```", len(u) // 4, 40, 0.001))
        return out


def make_backend(kind: str = "hf", **kw):
    if kind == "hf":
        return HFBackend(**kw)
    if kind == "openai":
        return OpenAIBackend(**kw)
    if kind == "fake":
        return FakeBackend()
    if kind == "anthropic":
        return AnthropicBackend(**kw)
    raise ValueError(kind)
