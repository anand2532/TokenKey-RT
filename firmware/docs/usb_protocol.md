# TokenKey RT — USB Protocol (v1.0)

v1.0 (issue #65) makes the v0.2 data model (issue #27: sessions, DELTA jobs, protected spans,
SET/GET_POLICY) real, end to end, and replaces the v0.2 "reduced bytes" result with a
**keep/drop list**: the device returns one record per segment and the host assembles the output.
The reduction rules are a byte-exact port of the TokenKey PoC (handoff `SPEC.md`; see
[engine.md](engine.md)), and positions/protection come from a per-message table the host sends in
JOB_BEGIN. Frame format and major version are unchanged; HELLO minor = **3** (caps bit3).
C definitions: `firmware/proto.h`, `jobs.h`, `engine.h` (host-tested by `test_proto.c`,
`test_engine.c` and `tests/test_corpus.py`). Host reference: `firmware/tools/tkhost.py`.

## 1. Transport
- USB OTG1 device, VID/PID TBD (dev values: `TK_USB_VID`/`TK_USB_PID` in `firmware/usb_vendor.c`). Class 0xFF vendor, 1 interface, bulk OUT 0x01, bulk IN 0x81, MPS 512 (HS) / 64 (FS).
- Optional MS OS 2.0 descriptor → WinUSB; Linux via libusb, udev rule for non-root.
- Frames may span multiple USB packets; host ends a transfer with a short/ZLP packet.

## 2. Frame
```
| 0xA5 | ver u8 | cmd u8 | seq u8 | len u16 LE | payload[len] | crc u16 LE |
```
- len ≤ 4096 (MAX_PAYLOAD, reported by HELLO).
- CRC-16/CCITT-FALSE (poly 0x1021, init 0xFFFF, no reflect, xorout 0) over ver..payload (excludes 0xA5). Check value "123456789" → 0x29B1.
- Responses: same cmd with bit7 set (cmd|0x80), echo seq. Errors: cmd 0xFF ERROR with payload {orig_cmd u8, code u8, detail u16}.
- Device events (unsolicited): cmd 0x60–0x6F, seq from device counter.
- Resync: on bad CRC/len, device scans for next 0xA5 and replies ERROR BAD_CRC/BAD_LEN with seq of the bad frame if parsed.

## 3. Commands
| cmd | name | payload (req) | response payload |
|---|---|---|---|
| 0x01 | HELLO | host_ver u8, host_max_payload u16 | proto_ver u8, fw_ver u32, part u8 (0=DVL6B,1=CVL5B), core_mhz u16, max_payload u16, window u8, caps u32, proto_minor u8 (3 = v1.0) — 16 B |
| 0x02 | PING | any ≤ 64 B | echo |
| 0x03 | GET_INFO | – | TLV: serial, build id, flash size, uptime |
| 0x10 | SET_MODE | mode u8 (0 Economy, 1 Balanced, 2 Quality, 3 S-protect (default), 4 Dedup-only; §9.3) | mode u8 |
| 0x11 | GET_MODE | – | mode u8, budget_pct u8 |
| 0x12 | SET_POLICY | policy blob (§9) | policy blob, fully expanded (as GET_POLICY) |
| 0x13 | GET_POLICY | – | policy blob, fully expanded (§9.3) |
| 0x20 | JOB_BEGIN | job_id u16, total_len u32, flags u8 (bit0 diff-aware, bit1 FULL, **bit2 MESSAGES**), token_budget u32 (0=use policy); session_id u32, prefix_len u32, prefix_xxh u32, span_count u8, spans[span_count] {offset u32, len u32, kind u8}; **if MESSAGES:** msg_count u16, msgs[msg_count] {len u32, role u8, flags u8} (§8) | job_id u16 |
| 0x21 | JOB_DATA | job_id u16, offset u32, data[] (pass 1: offsets 0..total_len; pass 2: total_len..2·total_len, §8.6) | job_id, acked_offset u32 |
| 0x22 | JOB_END | job_id u16, xxh32 u32 of this job's input (both passes) | job_id u16, status u8, seg_count u32, est_tokens_in u32, est_tokens_out u32, kept_bytes u32, dup_hits u32, set_full u32 — 27 B (§8.6) |
| 0x23 | RESULT_READ | job_id u16, offset u32, max u16 | job_id, offset u32, last u8, records[] — 13-byte segment records, offset/max in bytes of the record array, whole records only (§8.6) |
| 0x24 | JOB_ABORT | job_id u16 | job_id |
| 0x30 | GET_STATS | job_id u16 (0xFFFF=lifetime; else the last finished job) | bytes_in/out u32, tok_in/out u32, dup_hits u32, seg counts u16[4] (prose, code, diff, log), set_full u32, cycles u32 — 36 B |
| 0x31 | RESET_STATS | – | – |
| 0x40 | ENTER_BOOTLOADER | magic u32 0x544B424C | – (device resets). **Not implemented in v1.0** (UNKNOWN_CMD, detail 1); use the BOOT_MODE pins / SDP |
| 0x60 | EVT_PROGRESS | (dev→host) job_id u16, pct u8 (every ≥10 % and at 100 %; pass 2 counts as the second half) | |
| 0x61 | EVT_BUTTON | (dev→host) key u8, action u8 | |
| 0x62 | EVT_MODE | (dev→host) mode u8 (changed on device) | |

## 4. Error codes
| code | name |
|---|---|
| 0x00 | OK |
| 0x01 | BAD_CRC |
| 0x02 | BAD_LEN |
| 0x03 | BAD_VERSION |
| 0x04 | UNKNOWN_CMD |
| 0x05 | BAD_PARAM |
| 0x06 | BUSY (job active / window full) |
| 0x07 | NO_JOB / bad job_id |
| 0x08 | BAD_OFFSET (gap or overlap) |
| 0x09 | CTX_OVERFLOW (span/message/session table cap, or JOB_DATA past total_len) |
| 0x0A | HASH_MISMATCH (JOB_END xxh32) |
| 0x0B | TIMEOUT |
| 0x0C | SAFE_MODE (feature unavailable: JOB_* and SET_POLICY after ≥3 consecutive watchdog resets) |
| 0x0D | SESSION_MISMATCH (unknown/evicted/expired session or prefix_len/prefix_xxh disagree; host resends FULL). detail: 1 unknown, 2 prefix_len, 3 prefix_xxh, 4 evicted, **5 expired (TTL, v1.0)** |
| 0x0E | POLICY_INVALID (v0.2: bad policy blob). detail: 0x01 version, 0x02 truncated, 0x03 preset; `0x01tt` bad length, `0x02tt` bad value, `0x03tt` unknown mandatory TLV (tt = TLV type) |
| 0x7F | INTERNAL |

## 5. Flow control and chunking
- Window: host may have up to `window` (default 4) unacknowledged requests in flight; seq increments mod 256.
- JOB_DATA chunks ≤ max_payload−6, strictly sequential offsets; device acks acked_offset only after data is in the ring. On BUSY host backs off 5 ms and resends same seq/offset (idempotent: duplicate offsets already acked are re-acked, not re-processed).
- Timeout: host 500 ms per response; 3 retries then JOB_ABORT. Device aborts a job idle > 5 s.
- One active job at a time. Result records held until the next JOB_BEGIN or abort.
- Up to 4 sessions (`PROTO_MAX_SESSIONS`) are held device-side, LRU-evicted; one job is
  active at a time across all sessions.

## 6. Versioning
- Frame `ver` = protocol major (1). HELLO negotiates; device rejects other majors with BAD_VERSION (payload detail = supported major).
- Protocol minor is the last byte of the HELLO reply (`PROTO_VERSION_MINOR`): 1 = v0.1 (15-byte
  reply), 2 = v0.2 data model, **3 = v1.0** (message table, keep/drop records). A host must not
  run v1.0 jobs against minor < 3.
- Features advertised via `caps` bits:

| bit | name | meaning |
|---|---|---|
| 0 | `PROTO_CAP_EVENTS` | unsolicited EVT_* frames |
| 1 | `PROTO_CAP_XXH64` | reserved: xxh64 hashes |
| 2 | `PROTO_CAP_MULTI_JOB` | reserved: more than one active job |
| 3 | `PROTO_CAP_SESSIONS` | sessions, DELTA jobs, protected spans, SET/GET_POLICY, JOB_END/RESULT_READ v1.0. Cleared in safe mode. The host must not send v0.2+ JOB_BEGIN fields or SET/GET_POLICY unless this bit is set. |

- New commands only added; unknown → UNKNOWN_CMD. Payload fields only appended; receivers ignore trailing bytes.
- v0.1/v0.2 interop: an 11-byte JOB_BEGIN is a v0.1 request (stateless, FULL implied); a JOB_BEGIN
  without the MESSAGES flag is treated as one message, the newest (passed through, still hashed
  into the session dupset).

## 7. Example exchanges
```
H→D A5 01 01 00 0200 01 0010 crc      HELLO host_ver=1 max=4096
D→H A5 01 81 00 1000 01 00000100 00 5802 0010 04 09000000 03 crc   proto1 fw1.0.0 DVL6B 600MHz max4096 win4 caps=events|sessions minor3

H→D A5 01 10 01 0100 01 crc           SET_MODE Balanced
D→H A5 01 90 01 0100 01 crc

H→D JOB_BEGIN  seq2 job=7 total=10000 flags=FULL|MESSAGES budget=0 session=… msgs=[…]
D→H JOB_BEGIN|80 seq2 job=7
H→D JOB_DATA seq3 job=7 off=0 [4090 B]; seq4 off=4090; seq5 off=8180 [1820 B]
D→H acks acked_offset=4090, 8180, 10000   (+ EVT_PROGRESS 40 %, 81 % …)
H→D JOB_END seq6 job=7 xxh32=…
D→H JOB_END|80 seq6 status=DONE seg_count=120 tok_in=2500 …;  D→H EVT_PROGRESS 100%
H→D RESULT_READ seq7 job=7 off=0 max=4089
D→H RESULT_READ|80 seq7 off=0 last=1 [120 × 13 B records]

Error: H→D cmd 0x55 seq8 → D→H A5 01 FF 08 0400 55 04 0000 crc  (UNKNOWN_CMD)
```
CRC bytes shown as `crc`; generate with reference implementation in `proto/crc16.c` (table-driven, test vector 0x29B1).

## 8. Sessions, messages and jobs (v1.0)

### 8.1 Session model
- `session_id` u32 is chosen by the host (one per conversation); `0` = stateless (FULL implied,
  scratch slot, nothing kept).
- Per session the device keeps: input length + running xxh32 since the last FULL, persistent
  protected spans (§8.3), the time of the last job (TTL) and the **dupset** (XXH32 hashes of every
  segment seen since the last FULL: 8192 slots, 6144 cap, ~34 KB).
- 4 sessions, LRU-evicted. A DELTA for an evicted session → SESSION_MISMATCH detail 4.

### 8.2 FULL vs DELTA, lapse (JOB_BEGIN flags bit1)
- **FULL (bit1 = 1):** the job is the whole request; it (re)starts the session and **resets the
  dupset**. `prefix_len` / `prefix_xxh` must be 0.
- **DELTA (bit1 = 0):** the job is only the messages appended since the last job.
  `prefix_len`/`prefix_xxh` = the session input the host believes the device holds; on any
  disagreement → SESSION_MISMATCH (detail 1–3) and nothing changes.
- **Lapse (SPEC §1.1)** is decided by the host: first request, more than `TTL_S` (300 s) since the
  previous request, or fewer messages than last time (history rewritten). On a lapse the host sends
  FULL; otherwise DELTA. Older tool output is only trimmed in a lapse (FULL) job; warm DELTA jobs
  only dedup. As a safety net the device also refuses a DELTA whose session has been idle longer
  than the policy TTL (SESSION_MISMATCH detail 5 EXPIRED); the host resends FULL.
- `tkhost.py` keeps the host state (history, message count, last time) and falls back to FULL on
  any SESSION_MISMATCH.

### 8.3 Protected spans
- `span_count` ≤ 16; each {offset u32, len u32, kind u8} inside `total_len`, len > 0, sorted,
  non-overlapping (else BAD_PARAM `0x0100 | index`; too many → CTX_OVERFLOW).
- Kinds: `0 TASK`, `1 LATEST_TOOL_OUTPUT`, `2 OTHER`, `3 SYSTEM_PROMPT` (FULL jobs only, else
  BAD_PARAM `0x0200 | index`), **`4 ERROR` (v1.0)**: host-declared error text, protected in the
  declaring job only. 5..255 → BAD_PARAM.
- Every segment that overlaps a span of the job is **kept**, under every rule set. TASK / OTHER /
  SYSTEM_PROMPT are recorded in the session (session coordinates) for the host's bookkeeping.
- The device does **not** auto-detect errors: apart from the type weights (log 200 vs prose 100,
  SPEC §2.3) error text is protected only when the host declares an ERROR span.

### 8.4 Message table (flags bit2 MESSAGES)
After the spans: `msg_count u16` (1..256, `PROTO_MAX_MSGS`) then per message `{len u32, role u8,
flags u8}`. The lengths must add up to `total_len` (BAD_PARAM detail 6; truncated table → detail 5).
The job content is the messages' bytes concatenated, in order (no separators).

| role | value | | flag | bit | meaning |
|---|---|---|---|---|---|
| SYSTEM | 0 | | `MSGF_EXEMPT` | 0x01 | exempt from the keep ratio (never budget-dropped; still deduped) |
| USER | 1 | | `MSGF_NEWEST` | 0x02 | the newest message: kept verbatim (unless policy NEWEST_DEDUP), its blocks still enter the dupset |
| ASSISTANT | 2 | | | | |
| TOOL | 3 | | | | |

Roles are informational; **protection is by position** and is computed by the host (SPEC §1.2):
message 0 (system) and 1 (task) and every assistant message are exempt, the newest message is
NEWEST (+EXEMPT), only older tool output (`g ≥ 3`, odd, not newest) is subject to the ratio.
Without MESSAGES the job is a single NEWEST message.

### 8.5 Engine (summary, details in [engine.md](engine.md))
Each message is split into segments (CODE fences, DIFF, LOG, PROSE). Each segment gets an XXH32
(seed 0); a hash already in the session dupset is a duplicate (first occurrence kept, blank
segments never dropped). Duplicates of non-newest messages are dropped when DEDUP is on; then
candidates (non-exempt, non-protected, non-dup) are ranked by `score·1024/len` and kept greedily
until `keep_pct` of the non-exempt tokens (`len/4`) is used. Under `RULES = V01` (PoC variant D)
the whole job is ranked against `keep_pct` of all job tokens and dups are only penalised.

### 8.6 JOB_END, pass 2 and result records
JOB_END reply (27 B): `job_id u16, status u8, seg_count u32, est_tokens_in u32,
est_tokens_out u32, kept_bytes u32, dup_hits u32, set_full u32`.

| status | meaning | host action |
|---|---|---|
| 0 DONE | decision made, `seg_count` records ready | RESULT_READ, assemble |
| 1 NEED_PASS2 | the diff reference bonus (SPEC §2.3) can change a keep decision | re-send the same bytes with JOB_DATA offsets `total_len..2·total_len`, then JOB_END again with the same xxh32 |
| 2 OVERFLOW | > 4096 segments or a line > 2048 B | forward the job unreduced (the session still advances) |

Pass 2 happens only when some candidate DIFF has a file reference *and* the candidates do not all
fit the budget (corpus: 30 of 340 D-Economy jobs, ≤ 2 for S-protect).

RESULT_READ returns 13-byte records, one per segment in input order:
`off u32` (offset in the job content), `len u32`, `action u8` (0 KEEP, 1 DROP_DUP, 2 DROP_BUDGET),
`xxh32 u32` (segment hash). The host copies kept segments, replaces each run of dropped segments
inside a message by `[TokenKey: content omitted]` (SPEC §3), and may byte-compare a dropped
duplicate with its first occurrence (`tkhost.py --verify-dups`, guards against XXH32 collisions).

## 9. Reduction policy (v1.0): SET_POLICY / GET_POLICY

### 9.1 Blob
```
| policy_ver u8 (=1) | preset u8 | TLV* |       TLV = | type u8 | len u8 | value[len] |
```
- `preset` 0..4 = start from that mode (§9.3), `0xFF` = custom (start from the current policy);
  anything else → POLICY_INVALID detail 3. `SET_MODE m` = `SET_POLICY {1, m}`.
- Unknown TLV with bit7 set is ignored; without bit7 → POLICY_INVALID `0x03tt`.
- Device-global, applies from the next JOB_BEGIN. Blob ≤ 64 B.

### 9.2 TLVs
| type | name | len | value |
|---|---|---|---|
| 0x01 | KEEP_PCT | 1 | 1..100: kept share of older tool output tokens (of all job tokens under RULES V01) |
| 0x02 | DEDUP | 1 | 0/1: drop exact duplicate segments |
| 0x03 | — | | withdrawn (v0.2 CACHE_STABLE_PREFIX): the cached prefix is never rewritten |
| 0x04 | TYPE_WEIGHT | 3 | {seg_type u8 (0 prose, 1 code, 2 diff, 3 log), weight u16 LE ≤ 1000}, repeatable |
| 0x05 | NEWEST_DEDUP | 1 | 0/1: the newest message is deduped too (PoC G) |
| 0x06 | RULES | 1 | 0 V01 (whole-job ranking, PoC D), 1 SESSION (PoC S rules) |
| 0x07 | TTL_S | 4 | u32 session idle TTL in seconds, 0 = never |

### 9.3 Modes / presets
| mode | KEEP_PCT | DEDUP | NEWEST_DEDUP | RULES | TTL_S | weights prose/code/diff/log |
|---|---|---|---|---|---|---|
| 0 Economy | 25 | 1 | 0 | SESSION | 300 | 100 / 300 / 400 / 200 |
| 1 Balanced | 50 | 1 | 0 | SESSION | 300 | same |
| 2 Quality | 85 | 1 | 0 | SESSION | 300 | same |
| **3 S-protect (default)** | 100 | 1 | 0 | SESSION | 300 | same |
| 4 Dedup-only | 100 | 1 | 1 | SESSION | 0 | same |

PoC "D Economy (firmware as written)" = custom `{RULES 0, KEEP_PCT 25}`, stateless jobs, no
message flags. GET_POLICY returns the expanded 40-byte blob: version, preset (0..4 if it matches a
mode exactly, else 0xFF), KEEP_PCT, DEDUP, NEWEST_DEDUP, RULES, TTL_S, 4 × TYPE_WEIGHT.

### 9.4 Example
```
H→D HELLO …; D→H … caps=0x09 (events|sessions) minor=3
H→D SET_MODE 03                                  S-protect
H→D JOB_BEGIN job=1 FULL|MESSAGES session=0x544B0001 prefix=0/0 spans=0
             msgs=[{812,SYSTEM,EXEMPT},{230,USER,EXEMPT},{90,ASSISTANT,EXEMPT},{5120,TOOL,EXEMPT|NEWEST}]
… JOB_DATA … JOB_END → DONE seg_count=41 → RESULT_READ 41 records
H→D JOB_BEGIN job=2 MESSAGES (DELTA) prefix_len=6252 prefix_xxh=…
             msgs=[{120,ASSISTANT,EXEMPT},{3000,TOOL,EXEMPT|NEWEST}]
… JOB_END → DONE, dup_hits=3 (the repeated blocks of the earlier tool output are marked DROP_DUP)
(device lost the session or it expired: ERROR SESSION_MISMATCH detail 4/5 → host resends job 2 as FULL)
```

## 10. Open
VID/PID; HS vs FS-only; ENTER_BOOTLOADER; xxh64 segment hashes (caps bit1, reserved for collision
resistance); authentication/pairing; WinUSB need.
