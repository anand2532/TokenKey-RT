"""Token counting + prompt-caching cost model.

Tokenizer: tiktoken o200k_base is used as a PROXY for provider token counts (Anthropic's tokenizer
is not public; exact counts need the count_tokens API with a key). Savings percentages are
ratios of counts from the same tokenizer, so the proxy mostly cancels out, but absolute $ are approximate.

Caching model (caching-on baseline and all reducers): automatic prompt caching with a breakpoint at
the end of every request, all turns assumed within the cache TTL. A request reads from cache the
longest common prefix of WHOLE MESSAGES with the previous request of the same session (message
granularity is a conservative stand-in for block-level breakpoints), if that prefix reaches the
model's minimum cacheable length; everything after it is billed as a cache write (1.25x).
Requests shorter than the minimum are billed at the base input rate. Output tokens are taken from the
recorded assistant reply and assumed IDENTICAL across variants (a real A/B needs live API calls).
Per-message framing tokens are ignored.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

import tiktoken

from .prices import PRICES

_enc = tiktoken.get_encoding("o200k_base")
_cache: dict[bytes, int] = {}


def ntok(text: str) -> int:
    k = hashlib.blake2b(text.encode("utf-8", "surrogatepass"), digest_size=16).digest()
    v = _cache.get(k)
    if v is None:
        v = len(_enc.encode(text, disallowed_special=()))
        _cache[k] = v
    return v


@dataclass
class Bill:
    base_in: int = 0
    cache_read: int = 0
    cache_write: int = 0
    out: int = 0
    requests: int = 0

    def add(self, o: "Bill"):
        self.base_in += o.base_in; self.cache_read += o.cache_read
        self.cache_write += o.cache_write; self.out += o.out; self.requests += o.requests

    @property
    def input_total(self):
        return self.base_in + self.cache_read + self.cache_write

    def usd(self, model: str) -> float:
        p = PRICES[model]
        return (self.base_in * p["input"] + self.cache_read * p["cache_read"] +
                self.cache_write * p["cache_write"] + self.out * p["output"]) / 1e6


def bill_session(requests: list[list[str]], outputs: list[str], model: str, caching: bool) -> Bill:
    """requests[i] = list of message texts actually sent (system first). outputs[i] = assistant reply."""
    p = PRICES[model]
    total = Bill()
    prev: list[str] | None = None
    for msgs, out in zip(requests, outputs):
        toks = [ntok(m) for m in msgs]
        T = sum(toks)
        b = Bill(out=ntok(out), requests=1)
        if not caching or T < p["min_cache"]:
            b.base_in = T
        else:
            lcp = 0
            if prev is not None:
                for a, c, t in zip(prev, msgs, toks):
                    if a != c:
                        break
                    lcp += t
            if lcp < p["min_cache"]:
                lcp = 0
            b.cache_read = lcp
            b.cache_write = T - lcp
        total.add(b)
        prev = msgs
    return total
