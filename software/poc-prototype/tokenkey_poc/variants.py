"""Variants replayed against each session (see docs/ and the PoC plan, section 3)."""
from __future__ import annotations

import time

from . import tk_core as tk
from .costmodel import ntok

PLACEHOLDER = "[TokenKey: content omitted]"   # API rejects empty messages; [CHOICE]


def _fill(xs):
    return [x if x.strip() else PLACEHOLDER for x in xs]


def run_raw(reqs):
    return [list(r) for r in reqs], [], {"overflow": 0}


def run_full_request(reqs, mode, enforce_caps=True, token_counter=None):
    """Variant D: firmware job over the WHOLE request every turn (as the firmware doc describes a job),
    job-scoped dupset."""
    sent, lat, ov = [], [], 0
    for r in reqs:
        t0 = time.perf_counter()
        try:
            out, _ = tk.run_job(r, mode, enforce_caps=enforce_caps, token_counter=token_counter)
            out = _fill(out)
        except tk.CtxOverflow:
            out, ov = list(r), ov + 1          # host passes the original through
        lat.append((time.perf_counter() - t0) * 1000)
        sent.append(out)
    return sent, lat, {"overflow": ov}


def run_tail_only(reqs, mode, enforce_caps=True, token_counter=None):
    """Variant C: cache-preserving. Only messages new since the previous request are sent to the device;
    earlier (already reduced) messages are reused verbatim so the cached prefix stays byte-identical.
    Session-scoped dupset (doc: 'never evicted mid-session')."""
    sent, lat, ov = [], [], 0
    dup = tk.DupSet()
    hist: list[str] = []
    n_prev = 0
    set_full = 0
    for r in reqs:
        tail = r[n_prev:]
        t0 = time.perf_counter()
        try:
            out, st = tk.run_job(tail, mode, dupset=dup, enforce_caps=enforce_caps, token_counter=token_counter)
            out = _fill(out)
            set_full += st.set_full
        except tk.CtxOverflow:
            out, ov = list(tail), ov + 1
        lat.append((time.perf_counter() - t0) * 1000)
        hist = hist + out
        n_prev = len(r)
        sent.append(list(hist))
    return sent, lat, {"overflow": ov, "set_full": set_full}


def run_llmtrim(reqs, preset="agent", markers=True):
    """markers=True: cache_control breakpoints as a coding agent sends them (llmtrim then freezes the cached
    prefix). markers=False: no breakpoints, so llmtrim may rewrite the whole history."""
    import json
    import llmtrim
    from .anthropic_body import from_body, to_body
    sent, lat = [], []
    for r in reqs:
        b = to_body(r)
        if not markers:
            b["system"][0].pop("cache_control", None)
            b["messages"][-1]["content"][-1].pop("cache_control", None)
        body = json.dumps(b)
        t0 = time.perf_counter()
        o = llmtrim.compress(body, llmtrim.Provider.ANTHROPIC, preset)
        lat.append((time.perf_counter() - t0) * 1000)
        sent.append(from_body(o.request_json))
    return sent, lat, {"overflow": 0}


def retained(orig: str, sent: str) -> bool:
    a = ntok(orig)
    return a == 0 or ntok(sent) >= 0.9 * a


def diagnostics(reqs, sent):
    """Required-context PROXY (not G2): is the newest message (the observation/user turn the model must
    answer) kept >=90 % of tokens; is the original task statement (first user message) kept >=90 %."""
    n = len(reqs)
    last_ok = sum(retained(r[-1], s[-1]) for r, s in zip(reqs, sent))
    task_ok = sum(retained(r[1], s[1]) for r, s in zip(reqs, sent) if len(r) > 1)
    return {"newest_msg_kept_pct": 100 * last_ok / n if n else 0, "task_kept_pct": 100 * task_ok / n if n else 0}


def run_dedup_only_tail(reqs):
    """Variant G (prototype EXTENSION, not a firmware mode): cache-preserving, drop only segments that are exact
    XXH32 duplicates of earlier session content; keep every unique segment. Lossless w.r.t. unique content."""
    import xxhash
    sent, lat = [], []
    dup = tk.DupSet()
    hist: list[str] = []
    n_prev = 0
    for r in reqs:
        t0 = time.perf_counter()
        out = []
        for mi, m in enumerate(r[n_prev:]):
            keep = []
            for seg in tk.scan_message(m, mi, 0):
                if dup.check_insert(xxhash.xxh32_intdigest(seg.data), 0) and seg.data.strip():
                    continue
                keep.append(seg.data)
            out.append(b"".join(keep).decode("utf-8", "surrogatepass"))
        lat.append((time.perf_counter() - t0) * 1000)
        hist = hist + _fill(out)
        n_prev = len(r)
        sent.append(list(hist))
    return sent, lat, {"overflow": 0}
