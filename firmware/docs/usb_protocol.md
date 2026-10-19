# TokenKey RT — USB Protocol (draft v0.2)

v0.2 (issue #27) adds sessions and incremental (DELTA) jobs, protected spans, a pluggable
reduction policy (SET_POLICY/GET_POLICY), and a cache-stable prefix report in the job result,
so the host can keep the LLM provider's prompt cache prefix stable instead of re-reducing the
whole request every turn. Frame format and major version are unchanged (minor 1 → 2, caps bit3).
Data model only: the firmware skeleton still answers JOB_*, SET_POLICY and GET_POLICY with
`ERROR UNKNOWN_CMD`, detail `0x0001` (not implemented), and does not set caps bit3 yet.
C definitions: `firmware/proto.h` (parsers/encoders in `proto.c`, covered by `test_proto.c`).

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
| 0x01 | HELLO | host_ver u8, host_max_payload u16 | proto_ver u8, fw_ver u32, part u8 (0=DVL6B,1=CVL5B), core_mhz u16, max_payload u16, window u8, caps u32, **proto_minor u8 (v0.2)** — 16 B |
| 0x02 | PING | any ≤ 64 B | echo |
| 0x03 | GET_INFO | – | TLV: serial, build id, flash size, uptime |
| 0x10 | SET_MODE | mode u8 (0 Eco 25%,1 Bal 50%,2 Qual 85%) | mode u8 |
| 0x11 | GET_MODE | – | mode u8, budget_pct u8 |
| 0x12 | SET_POLICY | policy blob (§9) | policy blob, fully expanded (as GET_POLICY) |
| 0x13 | GET_POLICY | – | policy blob, fully expanded (§9.3) |
| 0x20 | JOB_BEGIN | job_id u16, total_len u32, flags u8 (bit0 diff-aware, **bit1 FULL**), token_budget u32 (0=use policy); **v0.2:** session_id u32, prefix_len u32, prefix_xxh u32, span_count u8, spans[span_count] {offset u32, len u32, kind u8} (§8) | job_id u16 |
| 0x21 | JOB_DATA | job_id u16, offset u32, data[] | job_id, acked_offset u32 |
| 0x22 | JOB_END | job_id u16, xxh32 u32 of this job's input | job_id, est_tokens_in u32; **v0.2:** est_tokens_out u32, out_len u32, cache_stable_len u32, cache_stable_xxh u32, protected_bytes u32 — 26 B (§8.4) |
| 0x23 | RESULT_READ | job_id u16, offset u32, max u16 | job_id, offset u32, last u8, data[] (offsets in full session-output space; host may start at cache_stable_len) |
| 0x24 | JOB_ABORT | job_id u16 | job_id |
| 0x30 | GET_STATS | job_id u16 (0xFFFF=lifetime) | bytes_in/out u32, tok_in/out u32, dup_hits u32, seg counts u16[4], set_full u32, cycles u32 |
| 0x31 | RESET_STATS | – | – |
| 0x40 | ENTER_BOOTLOADER | magic u32 0x544B424C | – (device resets) |
| 0x60 | EVT_PROGRESS | (dev→host) job_id, pct u8 | |
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
| 0x09 | CTX_OVERFLOW (segment/ring cap hit) |
| 0x0A | HASH_MISMATCH (JOB_END xxh32) |
| 0x0B | TIMEOUT |
| 0x0C | SAFE_MODE (feature unavailable) |
| 0x0D | SESSION_MISMATCH (v0.2: unknown/evicted session or prefix_len/prefix_xxh disagree; host resends FULL). detail: 1 unknown, 2 prefix_len, 3 prefix_xxh, 4 evicted |
| 0x0E | POLICY_INVALID (v0.2: bad policy blob). detail: 0x01 version, 0x02 truncated, 0x03 preset; `0x01tt` bad length, `0x02tt` bad value, `0x03tt` unknown mandatory TLV (tt = TLV type) |
| 0x7F | INTERNAL |

## 5. Flow control and chunking
- Window: host may have up to `window` (default 4) unacknowledged requests in flight; seq increments mod 256.
- JOB_DATA chunks ≤ max_payload−6, strictly sequential offsets; device acks acked_offset only after data is in the ring. On BUSY host backs off 5 ms and resends same seq/offset (idempotent: duplicate offsets already acked are re-acked, not re-processed).
- Timeout: host 500 ms per response; 3 retries then JOB_ABORT. Device aborts a job idle > 5 s.
- One active job at a time (v1). Result held until next JOB_BEGIN or abort.
- v0.2: up to 4 sessions (`PROTO_MAX_SESSIONS`) are held device-side, LRU-evicted; one job is
  active at a time across all sessions.

## 6. Versioning
- Frame `ver` = protocol major (1). HELLO negotiates; device rejects other majors with BAD_VERSION (payload detail = supported major).
- Protocol minor (v0.2 → 2) is the last byte of the HELLO reply (`PROTO_VERSION_MINOR`). A
  15-byte HELLO reply means minor 1 (v0.1).
- Features advertised via `caps` bits:

| bit | name | meaning |
|---|---|---|
| 0 | `PROTO_CAP_EVENTS` | unsolicited EVT_* frames |
| 1 | `PROTO_CAP_XXH64` | reserved: xxh64 hashes |
| 2 | `PROTO_CAP_MULTI_JOB` | reserved: more than one active job |
| 3 | `PROTO_CAP_SESSIONS` | **v0.2:** sessions, DELTA jobs, protected spans, SET/GET_POLICY, v0.2 JOB_END result. The host must not send v0.2 JOB_BEGIN fields or SET/GET_POLICY unless this bit is set. |

- New commands only added; unknown → UNKNOWN_CMD. Payload fields only appended; receivers ignore trailing bytes.
- v0.1 interop: an 11-byte JOB_BEGIN is a v0.1 request (stateless, FULL implied); a 6-byte
  JOB_END reply is a v0.1 device (no cache-stable report).

## 7. Example exchanges
```
H→D A5 01 01 00 0200 01 0010 crc      HELLO host_ver=1 max=4096
D→H A5 01 81 00 1000 01 00010000 00 5802 0010 04 01000000 02 crc   proto1 fw0.1.0 DVL6B 600MHz max4096 win4 caps=events minor2

H→D A5 01 10 01 0100 01 crc           SET_MODE Balanced
D→H A5 01 90 01 0100 01 crc

H→D JOB_BEGIN  seq2 job=7 total=10000 flags=1 budget=0
D→H JOB_BEGIN|80 seq2 job=7
H→D JOB_DATA seq3 job=7 off=0 [4090 B]; seq4 off=4090; seq5 off=8180 [1820 B]
D→H acks acked_offset=4090, 8180, 10000
H→D JOB_END seq6 job=7 xxh32=…
D→H JOB_END|80 seq6 tok_in=2500;  D→H EVT_PROGRESS 100%
H→D RESULT_READ seq7 job=7 off=0 max=4096
D→H RESULT_READ|80 seq7 off=0 last=1 [~5000 B in two reads if >max]

Error: H→D cmd 0x55 seq8 → D→H A5 01 FF 08 0400 55 04 0000 crc  (UNKNOWN_CMD)
```
CRC bytes shown as `crc`; generate with reference implementation in `proto/crc16.c` (table-driven, test vector 0x29B1).

## 8. Sessions, DELTA jobs and protected spans (v0.2)

### 8.1 Session model
- `session_id` u32 is chosen by the host (e.g. one per conversation); `0` = stateless.
- Device keeps per-session state within fixed limits: input prefix length + running xxh32 of
  everything received since the last FULL, the segment table (offsets, types, dedup hashes),
  persistent protected spans, and length + xxh32 of the previous result.
- Limits: 4 sessions (LRU), session input ≤ the job ring size; exceeding either evicts the
  session and the next DELTA gets SESSION_MISMATCH (detail 4) or CTX_OVERFLOW.

### 8.2 FULL vs DELTA (JOB_BEGIN flags bit1)
- **DELTA (bit1 = 0, default):** the job input is only the new messages since the last job of
  this session. `prefix_len` = session input bytes the host believes the device already holds,
  `prefix_xxh` = xxh32 (seed 0) of those bytes. If the session is unknown/evicted or either value
  differs from the device's, the device replies `ERROR SESSION_MISMATCH` and the host resends the
  whole request as FULL. DELTA with `session_id = 0` → BAD_PARAM.
- **FULL (bit1 = 1):** the job input is the whole request; it resets (or creates) the session.
  `prefix_len` and `prefix_xxh` must be 0. A v0.1 11-byte JOB_BEGIN is treated as FULL, stateless.
- `total_len` and all offsets in JOB_DATA/spans refer to this job's input (the delta for DELTA).

### 8.3 Protected spans
- `span_count` ≤ 16 (`PROTO_MAX_SPANS`, more → CTX_OVERFLOW). Each span {offset u32, len u32,
  kind u8}: len > 0, inside `total_len`, sorted by offset, non-overlapping (else BAD_PARAM,
  detail `0x0100 | span index`).
- kinds: `0 TASK`, `1 LATEST_TOOL_OUTPUT`, `2 OTHER`, `3 SYSTEM_PROMPT`. Kinds 4..255 are
  reserved for later minors (advertised by a caps bit); this version rejects them with
  BAD_PARAM, detail `0x0100 | span index`.
- Protected bytes are **never reduced**: the output contains each span byte-exact and in
  order. TASK and OTHER spans stay protected for the rest of the session; a
  LATEST_TOOL_OUTPUT span is protected only in the job that declares it (in later jobs it is
  ordinary tool output, subject to the policy and the cache-stable prefix rule).

#### 8.3.1 SYSTEM_PROMPT (kind 3): session-persistent
- Declared **only in a FULL job** (it is part of the request that starts the session). A
  SYSTEM_PROMPT span in a DELTA job → BAD_PARAM, detail `0x0200 | span index`.
- The device records every persistent span (TASK, OTHER, SYSTEM_PROMPT) in the session's
  protected-span table (`proto_session_span_t`, ≤ 32 per session; more → CTX_OVERFLOW) in
  **session coordinates**: offset in the concatenated session input since the last FULL
  (`in_len_at_job_start + span.offset`).
- Later DELTA jobs do not re-send the system prompt (it lies inside the already-sent,
  cache-stable prefix), but it **stays protected**: it is never reduced, even when the policy's
  `CACHE_STABLE_PREFIX` is smaller than the span's end and older history may be re-reduced.
- **FULL reset:** a FULL job drops the whole span table, SYSTEM_PROMPT included, before
  recording the new job's spans. The host must declare SYSTEM_PROMPT again in every FULL.
- **SESSION_MISMATCH:** the rejected DELTA changes nothing (span table, prefix, previous
  result stay as they were). The host's recovery is a FULL resend, which per the rule above
  must re-declare SYSTEM_PROMPT. An evicted session (detail 4) has lost its table.
- Stateless jobs (`session_id = 0`) protect their spans for that job only.
- Reference: `proto_session_begin_job()` / `proto_session_commit_job()` /
  `proto_session_protected_kind()` in `proto.c` (host-tested).

### 8.4 Result and cache-stable prefix (JOB_END v0.2 reply)
| field | meaning |
|---|---|
| est_tokens_in u32 | estimated tokens of the session input (v0.1 field) |
| est_tokens_out u32 | estimated tokens of the reduced output |
| out_len u32 | bytes of the full reduced session output (RESULT_READ offset space) |
| cache_stable_len u32 | leading output bytes byte-identical to this session's previous result (0 after FULL / stateless) |
| cache_stable_xxh u32 | xxh32 (seed 0) of those bytes, so the host can verify against its copy |
| protected_bytes u32 | bytes passed through untouched because of protected spans |

The host reuses its copy of the first `cache_stable_len` bytes (unchanged, so the provider's
prompt cache still matches) and only RESULT_READs from `offset = cache_stable_len`. How much of
the already-sent output the device must keep untouched is set by the policy's
`CACHE_STABLE_PREFIX` (§9).

## 9. Reduction policy (v0.2): SET_POLICY / GET_POLICY

### 9.1 Blob
```
| policy_ver u8 (=1) | preset u8 | TLV* |       TLV = | type u8 | len u8 | value[len] |
```
- `preset` 0 Economy / 1 Balanced / 2 Quality: start from that preset, then apply the TLVs.
  `0xFF` = custom: start from the device's current policy. Anything else → POLICY_INVALID.
- Economy/Balanced/Quality are **presets only**: names for a set of values. Behaviour is
  driven by the fields. `SET_MODE m` equals `SET_POLICY {1, m}` with no TLVs.
- Unknown TLV type with bit7 set: ignored; without bit7: POLICY_INVALID `0x03tt`.
- The policy is device-global and applies from the next JOB_BEGIN. Size ≤ 64 B.

### 9.2 TLVs
| type | name | len | value |
|---|---|---|---|
| 0x01 | BUDGET_PCT | 1 | target output size, % of input tokens, 1..100 |
| 0x02 | DEDUP | 1 | 0 off / 1 on (dedup repeated segments) |
| 0x03 | CACHE_STABLE_PREFIX | 4 | bytes of already-sent output never re-reduced; `0xFFFFFFFF` = all |
| 0x04 | TYPE_WEIGHT | 2 | {seg_type u8, weight u8 0..100} keep priority per segment type; repeatable. seg_type 0 TEXT, 1 CODE, 2 TOOL_OUTPUT, 3 LOG |

### 9.3 Presets and GET_POLICY
| preset | BUDGET_PCT | DEDUP | CACHE_STABLE_PREFIX | weights TEXT/CODE/TOOL_OUTPUT/LOG |
|---|---|---|---|---|
| 0 Economy | 25 | 1 | all | 40 / 70 / 30 / 10 |
| 1 Balanced | 50 | 1 | all | 60 / 85 / 50 / 25 |
| 2 Quality | 85 | 1 | all | 85 / 100 / 75 / 50 |

GET_POLICY (and the SET_POLICY reply) returns the fully expanded blob, 30 bytes: version,
preset (0..2 if the values equal that preset exactly, else 0xFF), BUDGET_PCT, DEDUP,
CACHE_STABLE_PREFIX, then TYPE_WEIGHT for all four types.

### 9.4 Example (v0.2)
```
H→D HELLO …; D→H … caps=0x09 (events|sessions) minor=2
H→D SET_POLICY  01 FF 01 01 28 04 02 01 5A      custom: budget 40 %, CODE weight 90
D→H SET_POLICY|80 [30 B expanded blob, preset FF]
H→D JOB_BEGIN job=1 flags=FULL session=0xC0FFEE01 prefix=0/0 spans=[{0,120,TASK}]  total=18000
… JOB_DATA / JOB_END → cache_stable_len=0, out_len=9100
H→D JOB_BEGIN job=2 flags=DELTA session=0xC0FFEE01 prefix_len=18000 prefix_xxh=<xxh32 of the 18000 B>
             spans=[{2100,900,LATEST_TOOL_OUTPUT}] total=3000
… JOB_END → out_len=11400 cache_stable_len=9100 cache_stable_xxh=…  → RESULT_READ from 9100
(if the device lost the session: ERROR SESSION_MISMATCH detail 1 → host resends job 2 as FULL)
```

## 10. Open
VID/PID; HS vs FS-only; whether result streams as events instead of polling; authentication/pairing; WinUSB need.
