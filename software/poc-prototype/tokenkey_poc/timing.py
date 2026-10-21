"""Request timing model + TTL-aware billing (used by the PM-defaults re-run, variant S).

NEITHER dataset has timestamps (the nebius SWE-agent trajectories carry no per-step times; the synthetic sessions
are generated without them). Gaps between consecutive requests of a conversation are therefore MODELLED
(assumption, deterministic per session id):
  * agent step (model reply + tool run): lognormal, median 20 s, sigma 0.8  (P(>5 min) ~ 0.03 %)
  * with probability 5 % per turn, an added human break, log-uniform between 2 and 120 minutes
    (so ~85 % of breaks exceed a 5-min TTL and ~17 % exceed a 1-hour TTL).
A third setting, 'always warm' (no breaks), corresponds to a fully automated agent run.
"""
from __future__ import annotations

import hashlib
import math
import random

from .costmodel import Bill, ntok
from .prices import PRICES

STEP_MEDIAN_S, STEP_SIGMA = 20.0, 0.8
BREAK_P, BREAK_MIN_S, BREAK_MAX_S = 0.05, 120.0, 7200.0


def request_times(session_id: str, n: int, breaks: bool = True) -> list[float]:
    rng = random.Random(int.from_bytes(hashlib.sha256(session_id.encode()).digest()[:8], "big"))
    t, out = 0.0, []
    for i in range(n):
        if i:
            g = rng.lognormvariate(math.log(STEP_MEDIAN_S), STEP_SIGMA)
            if breaks and rng.random() < BREAK_P:
                g += math.exp(rng.uniform(math.log(BREAK_MIN_S), math.log(BREAK_MAX_S)))
            t += g
        out.append(t)
    return out


def bill_session_timed(requests, outputs, times, model: str, ttl_s: float) -> tuple[Bill, int]:
    """Like costmodel.bill_session(caching=True) but the cache is cold when the gap since the previous request
    exceeds the TTL (lifetime measured from the start of the previous request, refreshed on every use).
    5-min TTL writes bill at 1.25x, 1-hour TTL writes at 2x base input [P1][P2]. Returns (bill, n_cold_starts)."""
    p = PRICES[model]
    total, prev, prev_t, cold = Bill(), None, None, 0
    for msgs, out, t in zip(requests, outputs, times):
        toks = [ntok(m) for m in msgs]
        T = sum(toks)
        b = Bill(out=ntok(out), requests=1)
        warm = prev is not None and (t - prev_t) <= ttl_s
        if prev is not None and not warm:
            cold += 1
        if T < p["min_cache"]:
            b.base_in = T
        else:
            lcp = 0
            if warm:
                for a, c, k in zip(prev, msgs, toks):
                    if a != c:
                        break
                    lcp += k
            if lcp < p["min_cache"]:
                lcp = 0
            b.cache_read, b.cache_write = lcp, T - lcp
        total.add(b)
        prev, prev_t = msgs, t
    return total, cold


def usd(b: Bill, model: str, ttl_s: float) -> float:
    p = PRICES[model]
    w = p["cache_write_1h"] if ttl_s > 300 else p["cache_write"]
    return (b.base_in * p["input"] + b.cache_read * p["cache_read"] + b.cache_write * w + b.out * p["output"]) / 1e6
