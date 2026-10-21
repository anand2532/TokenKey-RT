"""Host-side port of the TokenKey RT firmware context engine.

Source of truth: firmware/docs/firmware_architecture.md (draft v0.1) section 2.3
("Core: context processing") plus usb_protocol.md (JOB_BEGIN flags/budget,
CTX_OVERFLOW). Every behaviour that the firmware doc SPECIFIES is implemented
as written and marked [SPEC]. Every parameter the doc leaves open is a
prototype choice marked [CHOICE] and collected in UNSPECIFIED_CHOICES so the
report can list them. Integer math only in ranking/budget, as the doc requires.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import xxhash

# ---------------------------------------------------------------- [SPEC] constants
DUPSET_SLOTS = 8192            # [SPEC] fixed 8192 slots x 8 B (hash32 + chunk id)
DUPSET_LOAD_CAP_PCT = 75       # [SPEC] load cap 75 %
MAX_SEGMENTS = 4096            # [SPEC] max segments per job; exceeding -> CTX_OVERFLOW
MODE_KEEP_PCT = {"economy": 25, "balanced": 50, "quality": 85}   # [SPEC]
BYTES_PER_TOKEN = 4            # [SPEC] token estimate = bytes/4 (configurable)

# Segment types. [SPEC] ordering of weights: changed-file > fenced code > error log > prose
DIFF, CODE, LOG, PROSE = "diff", "code", "log", "prose"

# ---------------------------------------------------------------- [CHOICE] params
TYPE_WEIGHT = {DIFF: 400, CODE: 300, LOG: 200, PROSE: 100}   # [CHOICE] values; order is [SPEC]
RECENCY_MAX = 100              # [CHOICE] recency = offset*100//total_len
REF_PER_HIT, REF_MAX_HITS = 10, 10   # [CHOICE] reference count bonus for changed-file segments
DUP_PENALTY = 1000             # [CHOICE] large enough that duplicates rank below everything
PROSE_MAX_LINES = 64           # [CHOICE] prose paragraphs split at blank lines or 64 lines

UNSPECIFIED_CHOICES = {
    "segment granularity": "diff = one segment per changed file (diff --git / ---+++ header to end of diff lines); "
                           "fenced code = whole fence; log = contiguous log-looking lines incl. indented continuations; "
                           "prose = paragraph split at blank line or 64 lines; segments never cross message boundaries",
    "type weights": "diff 400, code 300, log 200, prose 100 (only the ORDER is specified)",
    "recency": "0..100, linear in byte offset within the job (later = higher)",
    "reference count": "changed-file segments: +10 per mention of the file basename elsewhere in the job, max +100; others 0",
    "dup penalty": "-1000; dedup key = XXH32 of the whole segment bytes (per-line hashes computed for stats only)",
    "greedy": "sort by score*1024//len descending (ties: earlier offset), first-fit: skip a segment that does not fit, keep scanning",
    "budget base": "est_tokens_in = total_len//4 (matches usb_protocol example 10000 B -> 2500)",
    "dupset scope": "'job' (cleared each job) or 'session' (persists across jobs; doc says 'never evicted mid-session' but does not define a session)",
    "CTX_OVERFLOW handling on host": "proxy forwards the original, unreduced request",
    "log detection regex": "Traceback/Error/Exception/FAILED/WARN/ERROR/timestamps/'File \"..\", line N'/pytest 'E   '",
}

_LOG_RE = re.compile(
    r"^(Traceback \(most recent call last\)|\s*File \".*\", line \d+|E\s{2,}|\w*(Error|Exception):|.*\b(FAILED|FAIL|"
    r"WARN(ING)?|ERROR|CRITICAL|panic|fatal)\b|\d{4}-\d\d-\d\d[ T]\d\d:\d\d|\[\s*\d+\.\d+\]|\s+at .+\(.+:\d+\))"
)
_DIFF_BODY_PREFIX = (" ", "+", "-", "@@", "index ", "diff ", "\\", "new file", "deleted file", "similarity",
                     "rename ", "old mode", "new mode", "Binary ")


@dataclass
class Segment:
    type: str
    msg: int          # message index (host-side bookkeeping; firmware has one flat stream)
    offset: int       # byte offset in the job stream
    data: bytes
    file_id: str | None = None
    hash: int = 0
    dup: bool = False
    score: int = 0

    @property
    def length(self) -> int:
        return len(self.data)


class DupSet:
    """[SPEC] open addressing, linear probe, fixed 8192 slots, 75 % load cap, no eviction."""

    def __init__(self, slots: int = DUPSET_SLOTS, load_cap_pct: int = DUPSET_LOAD_CAP_PCT):
        self.slots = slots
        self.cap = slots * load_cap_pct // 100
        self.table: list[tuple[int, int] | None] = [None] * slots
        self.count = 0
        self.set_full = 0

    def check_insert(self, h: int, chunk_id: int) -> bool:
        """Return True if h was already present (duplicate). Insert if absent and not full."""
        i = h & (self.slots - 1)
        while True:
            e = self.table[i]
            if e is None:
                break
            if e[0] == h:
                return True
            i = (i + 1) & (self.slots - 1)
        if self.count >= self.cap:
            self.set_full += 1          # [SPEC] when full, not deduped, counted in stats
            return False
        self.table[i] = (h, chunk_id)
        self.count += 1
        return False


@dataclass
class JobStats:
    bytes_in: int = 0
    bytes_out: int = 0
    tok_in: int = 0
    tok_out: int = 0
    dup_hits: int = 0
    seg_counts: dict = field(default_factory=lambda: {DIFF: 0, CODE: 0, LOG: 0, PROSE: 0})
    set_full: int = 0
    lines_hashed: int = 0
    overflow: bool = False


class CtxOverflow(Exception):
    pass


def _is_fence(line: str) -> str | None:
    s = line.lstrip()
    if s.startswith("```"):
        return "```"
    if s.startswith("~~~"):
        return "~~~"
    return None


def _diff_file_id(line: str) -> str | None:
    m = re.match(r"diff --git a/(\S+) b/(\S+)", line)
    if m:
        return m.group(2)
    m = re.match(r"\+\+\+ (?:b/)?(\S+)", line)
    if m:
        return m.group(1)
    return None


def scan_message(text: str, msg_idx: int, base_offset: int, diff_aware: bool = True) -> list[Segment]:
    """[SPEC] line-oriented scanner: diff headers, fenced code blocks, logs, prose."""
    lines = text.splitlines(keepends=True)
    segs: list[Segment] = []
    off = base_offset
    i = 0
    n = len(lines)

    def emit(kind, chunk, file_id=None):
        nonlocal off
        b = "".join(chunk).encode("utf-8", "surrogatepass")
        if b:
            segs.append(Segment(kind, msg_idx, off, b, file_id))
            off += len(b)

    while i < n:
        line = lines[i]
        fence = _is_fence(line)
        if fence:
            chunk = [line]
            i += 1
            while i < n:
                chunk.append(lines[i])
                i += 1
                if lines[i - 1].lstrip().startswith(fence):
                    break
            emit(CODE, chunk)
            continue
        is_git = diff_aware and line.startswith("diff --git ")
        is_uni = diff_aware and line.startswith("--- ") and i + 1 < n and lines[i + 1].startswith("+++ ")
        if is_git or is_uni:
            fid = _diff_file_id(line) if is_git else _diff_file_id(lines[i + 1])
            chunk = [line]
            i += 1
            while i < n:
                l2 = lines[i]
                if l2.startswith("diff --git "):
                    break
                if l2.strip() == "" or l2.startswith(_DIFF_BODY_PREFIX) or l2.startswith("+++") or l2.startswith("---"):
                    if l2.startswith("--- ") and i + 1 < n and lines[i + 1].startswith("+++ ") and len(chunk) > 2:
                        break   # next unified-diff file header
                    chunk.append(l2)
                    i += 1
                    continue
                break
            emit(DIFF, chunk, fid)
            continue
        if _LOG_RE.match(line):
            chunk = [line]
            i += 1
            while i < n and lines[i].strip() != "" and (_LOG_RE.match(lines[i]) or lines[i][:1] in (" ", "\t")) \
                    and not _is_fence(lines[i]):
                chunk.append(lines[i])
                i += 1
            emit(LOG, chunk)
            continue
        chunk = [line]
        i += 1
        if line.strip() != "":
            while i < n and len(chunk) < PROSE_MAX_LINES:
                l2 = lines[i]
                if _is_fence(l2) or (diff_aware and (l2.startswith("diff --git ") or
                                                      (l2.startswith("--- ") and i + 1 < n and lines[i + 1].startswith("+++ ")))) \
                        or _LOG_RE.match(l2):
                    break
                chunk.append(l2)
                i += 1
                if l2.strip() == "":
                    break
        emit(PROSE, chunk)
    return segs


def est_tokens(nbytes: int, bytes_per_token: int = BYTES_PER_TOKEN) -> int:
    return nbytes // bytes_per_token   # [SPEC] bytes/4


def run_job(messages: list[str], mode: str = "balanced", token_budget: int = 0, diff_aware: bool = True,
            dupset: DupSet | None = None, enforce_caps: bool = True, token_counter=None,
            exempt: list[bool] | None = None, drop_dups: bool = False) -> tuple[list[str], JobStats]:
    """Run one TokenKey job over a list of message texts. Returns reduced texts (same count) and stats.

    token_counter: None -> firmware bytes/4 estimator [SPEC]; or a callable(bytes)->int for the
    unconstrained-host variant.
    """
    st = JobStats()
    dupset = dupset if dupset is not None else DupSet()
    full0 = dupset.set_full
    segs: list[Segment] = []
    off = 0
    for mi, text in enumerate(messages):
        s = scan_message(text, mi, off, diff_aware)
        segs.extend(s)
        off += len(text.encode("utf-8", "surrogatepass"))
        if enforce_caps and len(segs) > MAX_SEGMENTS:
            st.overflow = True
            raise CtxOverflow(f"{len(segs)} segments > {MAX_SEGMENTS}")
    total = off
    st.bytes_in = total
    tok = token_counter or (lambda b: est_tokens(len(b)))
    st.tok_in = total // BYTES_PER_TOKEN if token_counter is None else sum(tok(s.data) for s in segs)

    joined_lower = None
    for cid, s in enumerate(segs):
        st.seg_counts[s.type] += 1
        st.lines_hashed += s.data.count(b"\n") or 1          # per-line XXH32 (stats only)
        s.hash = xxhash.xxh32_intdigest(s.data)
        s.dup = dupset.check_insert(s.hash, cid)
        if s.dup:
            st.dup_hits += 1
        ref = 0
        if s.type == DIFF and s.file_id:
            if joined_lower is None:
                joined_lower = b"".join(x.data for x in segs)
            base = s.file_id.rsplit("/", 1)[-1].encode()
            hits = max(0, joined_lower.count(base) - s.data.count(base))
            ref = min(hits, REF_MAX_HITS) * REF_PER_HIT
        recency = (s.offset * RECENCY_MAX) // total if total else 0
        s.score = TYPE_WEIGHT[s.type] + recency + ref - (DUP_PENALTY if s.dup else 0)
    st.set_full = dupset.set_full - full0

    if exempt is None and not drop_dups:
        # ---- original firmware v0.1 behaviour (unchanged)
        budget = token_budget if token_budget > 0 else st.tok_in * MODE_KEEP_PCT[mode] // 100   # [SPEC]
        order = sorted(range(len(segs)), key=lambda k: (-(segs[k].score * 1024 // max(segs[k].length, 1)), segs[k].offset))
        keep = [False] * len(segs)
        used = 0
        for k in order:
            t = tok(segs[k].data)
            if used + t <= budget:
                keep[k] = True
                used += t
    else:
        # ---- PM defaults 2026-10-19 (variant S): exact duplicates always dropped (drop_dups); segments of exempt
        # messages always kept otherwise; the mode keep ratio applies only to non-exempt messages, with the budget
        # = ratio x (non-exempt input tokens, counted before dedup). Greedy rule unchanged.
        ex = exempt if exempt is not None else [False] * len(messages)
        keep = [False] * len(segs)
        used = 0
        ratio_idx = []
        base = 0
        for k, sg in enumerate(segs):
            if drop_dups and sg.dup and sg.data.strip():
                continue
            if ex[sg.msg]:
                keep[k] = True
                used += tok(sg.data)
            else:
                ratio_idx.append(k)
        for k, sg in enumerate(segs):
            if not ex[sg.msg]:
                base += tok(sg.data)
        budget = token_budget if token_budget > 0 else base * MODE_KEEP_PCT[mode] // 100
        r_used = 0
        for k in sorted(ratio_idx, key=lambda k: (-(segs[k].score * 1024 // max(segs[k].length, 1)), segs[k].offset)):
            t = tok(segs[k].data)
            if r_used + t <= budget:
                keep[k] = True
                r_used += t
        used += r_used
    out = [b""] * len(messages)
    parts: list[list[bytes]] = [[] for _ in messages]
    for k, s in enumerate(segs):           # [SPEC] output keeps original order
        if keep[k]:
            parts[s.msg].append(s.data)
    out_txt = [b"".join(p).decode("utf-8", "surrogatepass") for p in parts]
    st.bytes_out = sum(len(b"".join(p)) for p in parts)
    st.tok_out = used
    return out_txt, st
