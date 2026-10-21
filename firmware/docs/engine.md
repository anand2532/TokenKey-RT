# TokenKey RT — on-device context engine (v1.0)

`engine.c` / `jobs.c` are a byte-exact port of the TokenKey PoC reduction rules
(handoff `SPEC.md`, reference `tk_core.py` / `session_reducer.py` / `variants.py`), re-shaped so
that every piece of device state is bounded. Wire format: [usb_protocol.md](usb_protocol.md) §8–9.
Host side: `tools/tkhost.py` (also the reference client for the simulator).

## 1. Rules (SPEC §0–3, summary)
- **Scanner**, per message, lines split like Python `str.splitlines(keepends=True)`:
  CODE fence (```` ``` ```` / `~~~` after lstrip, until the matching fence), DIFF (`diff --git`
  or a `--- ` line followed by `+++ `, with its body prefixes), LOG (lines matching `_LOG_RE`),
  PROSE (up to 64 lines, split after a blank line).
- **Hash**: XXH32 seed 0 of the segment bytes. **Dupset**: 8192 slots, cap 6144 (75 %), linear
  probe, hash only, no eviction; when full, new hashes are not inserted (`set_full` counted).
  First occurrence kept, blank (whitespace-only) segments never dropped, no minimum length.
- **Score** = type weight (diff 400, code 300, log 200, prose 100) + recency
  `off·100 // total` + diff reference bonus `min(hits,10)·10` − 1000 if duplicate.
  **Greedy**: sort by `score·1024 // len` desc, then offset; keep while tokens (`len // 4`) fit.
- **S-protect (default) / Economy / Balanced / Quality**: position-based protection from the
  host's message flags (system, task, assistant, newest exempt); duplicates of non-newest messages
  dropped; candidates = older tool output; budget = `keep_pct` of the non-exempt tokens; the
  newest message is passed through and hashed into the dupset. The ratio only runs in a lapse
  (FULL) job; the dupset resets at each lapse.
- **Dedup-only (G)**: everything exempt, the newest deduped too, dupset never reset (TTL 0).
- **D (Economy as written, opt-in)**: `RULES V01`, whole job ranked against
  `(total//4)·keep_pct//100`, duplicates penalised (−1000) not dropped, stateless.
- Host-declared protected spans (incl. `ERROR`) keep every overlapping segment under all rules.
  No error auto-detection beyond the log weight.

## 2. Bounded design: SPEC §5.2 flags and the choice made for each

| # | Unbounded in the reference | v1.0 device choice | Bound |
|---|---|---|---|
| 1 | Global greedy needs all segments; reassembly needs the bytes | Segment **descriptor table** (20 B each) + **keep/drop records** to the host (RESULT_READ, 13 B per segment). The device never buffers content; the host assembles and inserts the placeholder. | 4096 segments (80 KB table); more → OVERFLOW, job forwarded unreduced |
| 2 | Recency needs `total_job_bytes` before scoring | `total_len` is in JOB_BEGIN (and per-message lengths in the message table) | — |
| 3 | Diff reference count = `joined.count(basename)` over the whole job | Only when it can matter (a candidate DIFF has a reference **and** candidates exceed the budget) the device answers JOB_END with `NEED_PASS2`; the host re-streams the same bytes and per-reference KMP matchers count non-overlapping hits (whole job and inside the diff itself, so `hits = all − own` exactly as the PoC) | 128 references per job, basename ≤ 128 B; beyond → OVERFLOW |
| 4 | Segment length unbounded, drop known only at segment end | Records, not bytes (see 1); hashes are streamed | none needed |
| 5 | Line buffer, one line lookahead, unanchored `_LOG_RE` | Two line buffers (current + one lookahead) of 2048 B; LOG regex implemented as a per-line matcher | 2048 B per line (observed max 664); longer → OVERFLOW |
| 6 | Exemption needs positions and the message count | Host sends `{len, role, flags}` per message (`MSGF_EXEMPT`, `MSGF_NEWEST`); the device does not infer roles | 256 messages per job (observed max 114) |
| 7 | CTX_OVERFLOW checked per message | Checked **per segment** as it is closed, and again at JOB_END | — |
| 8 | History, `n_prev`, `last_t`, lapse, TTL clock | **Host state** (`tkhost.Reducer`). The device only refuses a stale DELTA (`SESSION_MISMATCH` EXPIRED, policy TTL) as a safety net | — |
| 9 | Dupset | Fixed per session: 8192 × u32 + bitmap (~34 KB), 4 sessions + 1 scratch slot, LRU. Inserts of a job are deferred to JOB_END and logged (undo list) so an aborted pass 2 / JOB_ABORT rolls them back | 6144 hashes per session |

### Hash collisions
Dedup is hash-only (as in the PoC): two different segments with the same XXH32 would wrongly drop
the later one (probability ≈ n²/2³³, ~10⁻⁵ at the observed 255 entries). Guards:
- `tkhost.py run --verify-dups` byte-compares every DROP_DUP segment against the first
  occurrence the host has already seen and keeps it if they differ (counted as `collisions`).
- caps bit1 `PROTO_CAP_XXH64` is reserved for 64-bit segment hashes (not implemented in v1.0).

## 3. Memory (firmware, `.ocram_bss` in the 512 KB OCRAM2)
| object | size |
|---|---|
| 5 session slots (4 + scratch), dupset + session spans | 172,300 B (5 × ~34 KB) |
| engine: segment table, order/undo, refs + KMP tables, 2 line buffers | 137,932 B |
| jobs state (message table, spans, stats) | ~3 KB |
| **total** | 313,388 B (61 % of OCRAM2) |

## 4. Verification (host only; nothing verified on hardware)
- `test_engine.c`: unit tests of scanner, dupset, scoring, overflow and rollback (ASan/UBSan).
- `tests/test_corpus.py` (ctest `tkhost_corpus`): 68 PoC requests × 5 variants through tkhost →
  protocol → simulator (`libtksim.so`), output digests byte-exact against the PoC, metrics equal
  to `expected_metrics.json`. See `tests/corpus/README.md`.
- Out of tree (needs the full PoC corpus): the C engine was cross-checked byte-exact on 5,095
  full-corpus jobs.
