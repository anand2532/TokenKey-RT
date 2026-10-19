# TokenKey RT — USB Protocol (draft v0.1)

## 1. Transport
- USB OTG1 device, VID/PID TBD (dev: NXP test 0x1FC9/xxxx). Class 0xFF vendor, 1 interface, bulk OUT 0x01, bulk IN 0x81, MPS 512 (HS) / 64 (FS).
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
| 0x01 | HELLO | host_ver u8, host_max_payload u16 | proto_ver u8, fw_ver u32, part u8 (0=DVL6B,1=CVL5B), core_mhz u16, max_payload u16, window u8, caps u32 |
| 0x02 | PING | any ≤ 64 B | echo |
| 0x03 | GET_INFO | – | TLV: serial, build id, flash size, uptime |
| 0x10 | SET_MODE | mode u8 (0 Eco 25%,1 Bal 50%,2 Qual 85%) | mode u8 |
| 0x11 | GET_MODE | – | mode u8, budget_pct u8 |
| 0x20 | JOB_BEGIN | job_id u16, total_len u32, flags u8 (bit0 diff-aware), token_budget u32 (0=use mode) | job_id u16 |
| 0x21 | JOB_DATA | job_id u16, offset u32, data[] | job_id, acked_offset u32 |
| 0x22 | JOB_END | job_id u16, xxh32 u32 of whole input | job_id, est_tokens_in u32 |
| 0x23 | RESULT_READ | job_id u16, offset u32, max u16 | job_id, offset u32, last u8, data[] |
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
| 0x7F | INTERNAL |

## 5. Flow control and chunking
- Window: host may have up to `window` (default 4) unacknowledged requests in flight; seq increments mod 256.
- JOB_DATA chunks ≤ max_payload−6, strictly sequential offsets; device acks acked_offset only after data is in the ring. On BUSY host backs off 5 ms and resends same seq/offset (idempotent: duplicate offsets already acked are re-acked, not re-processed).
- Timeout: host 500 ms per response; 3 retries then JOB_ABORT. Device aborts a job idle > 5 s.
- One active job at a time (v1). Result held until next JOB_BEGIN or abort.

## 6. Versioning
- Frame `ver` = protocol major (1). HELLO negotiates; device rejects other majors with BAD_VERSION (payload detail = supported major).
- Minor features advertised via `caps` bits (bit0 events, bit1 xxh64, bit2 multi-job…). New commands only added; unknown → UNKNOWN_CMD. Payload fields only appended; receivers ignore trailing bytes.

## 7. Example exchanges
```
H→D A5 01 01 00 0200 01 0010 crc      HELLO host_ver=1 max=4096
D→H A5 01 81 00 0E00 01 00010000 00 5802 0010 04 01000000 crc   proto1 fw0.1.0 DVL6B 600MHz max4096 win4 caps=events

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

## 8. Open
VID/PID; HS vs FS-only; whether result streams as events instead of polling; authentication/pairing; WinUSB need.
