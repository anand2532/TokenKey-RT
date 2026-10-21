"""Variant S: TokenKey PM defaults (2026-10-19).

1. A job is only the messages new since the last turn; the already-sent (cached) prefix is never rewritten.
2. System prompt, task statement (first user message) and newest tool output are exempt from keep ratios.
   Ratios apply only to OLDER tool output. Assistant messages are not tool output, so they are not ratio-reduced
   either [interpretation]. Consequence: on a warm turn the new messages are [assistant, newest tool output],
   both exempt, so ratios do nothing; ratios only act at a session (re)start.
3. Session = one conversation while the provider cache is warm (gap <= TTL). On a lapse (or the first request)
   a new session starts: fresh dupset and ONE full-request reduction (allowed because the cache is cold anyway).
4. Exact-duplicate removal is on in every mode, including inside exempt messages [interpretation: rule 2 exempts
   from ratios only].
Message roles follow the session format: idx 0 system, idx 1 task, then assistant (even idx) / tool output (odd idx).
"""
from __future__ import annotations

import time

from . import tk_core as tk

PLACEHOLDER = "[TokenKey: content omitted]"


def _exempt(global_idx: list[int], n_total: int) -> list[bool]:
    out = []
    for g in global_idx:
        older_tool_output = g >= 3 and g % 2 == 1 and g != n_total - 1
        out.append(not older_tool_output)
    return out


def collapse_repeats(text: str, min_run: int = 4) -> str:
    """PM decision 2026-10-19 (variant S-collapse), newest tool output only: a run of more than 3 consecutive,
    exactly identical lines is replaced by its first line, a "[repeated N×]" marker and its last line, where N is
    the total number of lines in the run [interpretation]. Lines inside the FIRST traceback/error block (first LOG
    segment found by the firmware scanner) are never touched. Blank lines are not collapsed [choice]."""
    lines = text.splitlines(keepends=True)
    prot = (0, 0)
    off = 0
    for seg in tk.scan_message(text, 0, 0):
        if seg.type == tk.LOG:
            a = text.encode("utf-8", "surrogatepass")[:seg.offset].decode("utf-8", "surrogatepass").count("\n")
            prot = (a, a + seg.data.decode("utf-8", "surrogatepass").count("\n") + 1)
            break
    out, i, n = [], 0, len(lines)
    while i < n:
        j = i
        while j + 1 < n and lines[j + 1] == lines[i]:
            j += 1
        run = j - i + 1
        in_prot = not (j < prot[0] or i >= prot[1])
        if run >= min_run and lines[i].strip() and not in_prot:
            nl = "" if lines[i].endswith("\n") else "\n"
            out += [lines[i] + nl, f"[repeated {run}×]\n", lines[j]]
        else:
            out += lines[i:j + 1]
        i = j + 1
    return "".join(out)


class SessionReducer:
    def __init__(self, mode: str, ttl_s: float, dedup_newest: bool = True, newest_policy: str | None = None):
        # newest_policy: "dedup" (cross-message dedup applies), "protect" (exempt from dedup),
        # "collapse" (exempt from dedup, then collapse_repeats inside the newest output)
        self.newest_policy = newest_policy or ("dedup" if dedup_newest else "protect")
        self.dedup_newest = self.newest_policy == "dedup"
        self.mode, self.ttl = mode, ttl_s
        self.dup = None
        self.hist: list[str] = []
        self.n_prev = 0
        self.last_t = None
        self.stats = {"full_reductions": 0, "warm_jobs": 0, "overflow": 0}

    def process(self, msgs: list[str], t: float) -> list[str]:
        lapse = (self.last_t is None or t - self.last_t > self.ttl or len(msgs) < self.n_prev)
        if lapse:
            self.dup = tk.DupSet()
            idx = list(range(len(msgs)))
            try:
                out, _ = tk.run_job(msgs, self.mode, dupset=self.dup, exempt=_exempt(idx, len(msgs)), drop_dups=True)
            except tk.CtxOverflow:
                out = list(msgs); self.stats["overflow"] += 1
            if not self.dedup_newest:
                out[-1] = collapse_repeats(msgs[-1]) if self.newest_policy == "collapse" and len(msgs) > 2 else msgs[-1]
            self.hist = [x if x.strip() else PLACEHOLDER for x in out]
            self.stats["full_reductions"] += 1
        else:
            tail = msgs[self.n_prev:]
            idx = list(range(self.n_prev, len(msgs)))
            try:
                out, _ = tk.run_job(tail, self.mode, dupset=self.dup, exempt=_exempt(idx, len(msgs)), drop_dups=True)
            except tk.CtxOverflow:
                out = list(tail); self.stats["overflow"] += 1
            if not self.dedup_newest:
                out[-1] = collapse_repeats(tail[-1]) if self.newest_policy == "collapse" else tail[-1]
            self.hist = self.hist + [x if x.strip() else PLACEHOLDER for x in out]
            self.stats["warm_jobs"] += 1
        self.n_prev, self.last_t = len(msgs), t
        return list(self.hist)


def run_session(reqs, times, mode, ttl_s, dedup_newest=True, newest_policy=None):
    r = SessionReducer(mode, ttl_s, dedup_newest, newest_policy)
    sent, lat, lat_full = [], [], []
    for m, t in zip(reqs, times):
        before = r.stats["full_reductions"]
        t0 = time.perf_counter()
        sent.append(r.process(m, t))
        dt = (time.perf_counter() - t0) * 1000
        lat.append(dt)
        if r.stats["full_reductions"] > before:
            lat_full.append(dt)
    return sent, lat, lat_full, r.stats
