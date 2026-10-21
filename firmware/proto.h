/*
 * TokenKey RT - USB frame protocol (firmware/docs/usb_protocol.md, v1.0)
 *
 *   | 0xA5 | ver u8 | cmd u8 | seq u8 | len u16 LE | payload[len] | crc u16 LE |
 *   CRC-16/CCITT-FALSE (poly 0x1021, init 0xFFFF, no reflection, xorout 0) over ver..payload.
 *
 * Pure C, no hardware or RTOS dependencies: compiled into the firmware and into the host
 * unit test (test_proto.c).
 */
#ifndef TK_PROTO_H
#define TK_PROTO_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#define PROTO_SOF          0xA5u
#define PROTO_VERSION      1u /* major: frame `ver` byte */
#define PROTO_VERSION_MINOR 3u /* minor: reported in HELLO (2 = v0.2 data model, 3 = v1.0 wire: message table, keep/drop records) */
#define PROTO_MAX_PAYLOAD  4096u
#define PROTO_OVERHEAD     8u /* SOF + ver + cmd + seq + len16 + crc16 */
#define PROTO_MAX_FRAME    (PROTO_MAX_PAYLOAD + PROTO_OVERHEAD)
#define PROTO_WINDOW       4u
#define PROTO_RESP_BIT     0x80u

enum {
    CMD_HELLO = 0x01, CMD_PING = 0x02, CMD_GET_INFO = 0x03,
    CMD_SET_MODE = 0x10, CMD_GET_MODE = 0x11, CMD_SET_POLICY = 0x12, CMD_GET_POLICY = 0x13,
    CMD_JOB_BEGIN = 0x20, CMD_JOB_DATA = 0x21, CMD_JOB_END = 0x22, CMD_RESULT_READ = 0x23, CMD_JOB_ABORT = 0x24,
    CMD_GET_STATS = 0x30, CMD_RESET_STATS = 0x31,
    CMD_ENTER_BOOTLOADER = 0x40,
    EVT_PROGRESS = 0x60, EVT_BUTTON = 0x61, EVT_MODE = 0x62,
    CMD_ERROR = 0xFF,
};

enum {
    ERR_OK = 0x00, ERR_BAD_CRC = 0x01, ERR_BAD_LEN = 0x02, ERR_BAD_VERSION = 0x03,
    ERR_UNKNOWN_CMD = 0x04, ERR_BAD_PARAM = 0x05, ERR_BUSY = 0x06, ERR_NO_JOB = 0x07,
    ERR_BAD_OFFSET = 0x08, ERR_CTX_OVERFLOW = 0x09, ERR_HASH_MISMATCH = 0x0A, ERR_TIMEOUT = 0x0B,
    ERR_SAFE_MODE = 0x0C, ERR_SESSION_MISMATCH = 0x0D, ERR_POLICY_INVALID = 0x0E, ERR_INTERNAL = 0x7F,
};

/* ERROR detail used for commands that are defined in the spec but not implemented yet. */
#define ERR_DETAIL_NOT_IMPLEMENTED 0x0001u

/* GET_INFO TLV types */
enum { TLV_SERIAL = 0x01, TLV_BUILD_ID = 0x02, TLV_FLASH_SIZE = 0x03, TLV_UPTIME_MS = 0x04 };

/* Reduction presets (SET_MODE / policy preset). S-protect is the v1.0 default; Economy,
 * Balanced and Quality are explicit opt-in keep ratios for OLDER tool output only. */
typedef enum {
    MODE_ECONOMY = 0, MODE_BALANCED = 1, MODE_QUALITY = 2, MODE_S_PROTECT = 3, MODE_DEDUP_ONLY = 4, MODE_COUNT
} tk_mode_t;
#define MODE_DEFAULT MODE_S_PROTECT

uint16_t proto_crc16(const uint8_t *data, size_t len);
uint16_t proto_crc16_update(uint16_t crc, const uint8_t *data, size_t len);
uint8_t proto_mode_budget_pct(tk_mode_t m);
const char *proto_mode_name(tk_mode_t m);

/* Build a frame into out (must hold len + PROTO_OVERHEAD). Returns total length or 0. */
size_t proto_build(uint8_t *out, size_t out_cap, uint8_t cmd, uint8_t seq, const uint8_t *payload, uint16_t len);

/* ---- streaming parser ------------------------------------------------------------------ */
typedef struct {
    uint8_t ver, cmd, seq;
    uint16_t len;
    uint8_t payload[PROTO_MAX_PAYLOAD];
} proto_frame_t;

typedef enum {
    PARSE_NONE = 0,   /* need more bytes */
    PARSE_FRAME,      /* complete, CRC-valid frame in parser->frame */
    PARSE_ERR_CRC,    /* bad CRC; header fields of the bad frame in parser->frame */
    PARSE_ERR_LEN,    /* len > PROTO_MAX_PAYLOAD; header fields in parser->frame */
} proto_parse_result_t;

typedef struct {
    uint8_t state;
    uint8_t hdr[5];
    uint16_t pos;
    uint16_t crc_rx;
    proto_frame_t frame;
} proto_parser_t;

void proto_parser_init(proto_parser_t *p);
/* Feed one byte. After any result other than PARSE_NONE the parser is already re-armed and
 * hunting for the next 0xA5 (resync). */
proto_parse_result_t proto_parser_feed(proto_parser_t *p, uint8_t b);

/* ---- command dispatch ------------------------------------------------------------------ */
/* Device state the dispatcher reads / updates. Owned by usb_task. */
typedef struct {
    tk_mode_t mode;
    uint8_t part;          /* 0 = DVL6B, 1 = CVL5B */
    uint16_t core_mhz;
    uint32_t fw_version;   /* major << 16 | minor << 8 | patch */
    uint64_t serial;
    const char *build_id;
    uint32_t flash_size;
    uint32_t uptime_ms;    /* refreshed by the caller before dispatch */
    uint32_t caps;
    bool mode_changed;     /* set by dispatch when SET_MODE changed the mode */
    struct tk_jobs *jobs;  /* v0.2 job engine (jobs.h); NULL = JOB, POLICY and STATS commands not implemented */
    bool safe_mode;        /* watchdog safe mode: JOB_* and SET_POLICY answer ERR_SAFE_MODE */
} proto_device_t;

#define PROTO_CAP_EVENTS    0x00000001u /* bit0: unsolicited EVT_* frames */
#define PROTO_CAP_XXH64     0x00000002u /* bit1: reserved (xxh64 hashes) */
#define PROTO_CAP_MULTI_JOB 0x00000004u /* bit2: reserved (more than one active job) */
#define PROTO_CAP_SESSIONS  0x00000008u /* bit3: v0.2 sessions, DELTA jobs, protected spans,
                                         * SET/GET_POLICY, JOB_END v0.2 result. Added to the
                                         * HELLO caps by proto_handle when dev->jobs is set
                                         * and the device is not in safe mode. */

/* ---- v0.2 data model: sessions, delta jobs, protected spans ------------------------------ */
#define JOB_FLAG_DIFF_AWARE   0x01u /* v0.1 bit0 */
#define JOB_FLAG_FULL         0x02u /* 1 = FULL request (resets the session); 0 = DELTA (default) */
#define JOB_FLAG_MESSAGES     0x04u /* v1.0: a message table follows the spans in JOB_BEGIN */
/* Message roles (usb_protocol.md 8.5) */
enum { ROLE_SYSTEM = 0, ROLE_USER = 1, ROLE_ASSISTANT = 2, ROLE_TOOL = 3, ROLE_COUNT };
#define PROTO_SESSION_NONE    0u    /* session_id 0 = stateless, FULL implied */
#define PROTO_MAX_SPANS       16u   /* protected spans per JOB_BEGIN */
#define PROTO_MAX_SESSIONS    4u    /* device-side session slots (LRU) */
#define JOB_BEGIN_V01_LEN     11u   /* job_id u16, total_len u32, flags u8, token_budget u32 */
#define JOB_BEGIN_V02_LEN     24u   /* + session_id u32, prefix_len u32, prefix_xxh u32, span_count u8 */
#define JOB_SPAN_WIRE_LEN     9u    /* offset u32, len u32, kind u8 */
#define PROTO_MAX_MSGS        256u  /* v1.0 message table entries per JOB_BEGIN (PoC max 114) */
#define JOB_MSG_WIRE_LEN      6u    /* len u32, role u8, flags u8 */

/* Span kinds (usb_protocol.md 8.3). 5..255 are reserved for future minors and rejected
 * (BAD_PARAM) by this version (4 = ERROR since v1.0). Persistence: TASK, OTHER and SYSTEM_PROMPT spans stay
 * protected for the whole session; LATEST_TOOL_OUTPUT only in the job that declares it.
 * SYSTEM_PROMPT may only be declared in a FULL job. */
typedef enum {
    SPAN_TASK = 0,
    SPAN_LATEST_TOOL_OUTPUT = 1,
    SPAN_OTHER = 2,
    SPAN_SYSTEM_PROMPT = 3,
    SPAN_ERROR = 4, /* v1.0: host-declared error text; protected in the declaring job only */
    SPAN_KIND_COUNT
} proto_span_kind_t;
#define PROTO_SPAN_KIND_PERSISTS(k) ((k) == SPAN_TASK || (k) == SPAN_OTHER || (k) == SPAN_SYSTEM_PROMPT)

typedef struct {
    uint32_t offset; /* relative to this job's input (the delta for DELTA jobs) */
    uint32_t len;    /* > 0 */
    uint8_t kind;    /* proto_span_kind_t */
} proto_span_t;

typedef struct {
    uint16_t job_id;
    uint32_t total_len;
    uint8_t flags;
    uint32_t token_budget;
    uint32_t session_id;
    uint32_t prefix_len; /* DELTA: session input bytes the host believes the device holds */
    uint32_t prefix_xxh; /* DELTA: xxh32 (seed 0) of those bytes */
    uint8_t span_count;
    proto_span_t spans[PROTO_MAX_SPANS];
    bool v02;            /* v0.2 fields were present */
    bool has_msgs;       /* v1.0 message table present (after the spans) */
    uint16_t msg_count;
    struct {
        uint32_t len;    /* content bytes of the message; sum == total_len */
        uint8_t role;    /* ROLE_* (informational; protection comes from flags) */
        uint8_t flags;   /* MSGF_* (engine.h): EXEMPT, NEWEST */
    } msgs[PROTO_MAX_MSGS];
} proto_job_begin_t;

/* ERROR detail for SESSION_MISMATCH: host must resend the job with JOB_FLAG_FULL. */
enum { SESS_MM_UNKNOWN = 1, SESS_MM_PREFIX_LEN = 2, SESS_MM_PREFIX_XXH = 3, SESS_MM_EVICTED = 4, SESS_MM_EXPIRED = 5 };
/* ERROR detail for BAD_PARAM from JOB_BEGIN parsing */
enum {
    JB_DETAIL_SHORT = 1,          /* neither v0.1 (11 B) nor >= v0.2 (24 B + spans) */
    JB_DETAIL_DELTA_NO_SESSION,   /* DELTA requested with session_id 0 */
    JB_DETAIL_FULL_WITH_PREFIX,   /* FULL with non-zero prefix_len/prefix_xxh */
    JB_DETAIL_SPANS_TRUNCATED,    /* span_count larger than the payload */
    JB_DETAIL_MSGS_TRUNCATED,     /* v1.0 message table shorter than msg_count */
    JB_DETAIL_MSG_SUM,            /* v1.0 message lengths do not add up to total_len */
    JB_DETAIL_SPAN_BASE = 0x100,  /* | span index: zero len, out of range, overlap/unsorted, bad kind */
    JB_DETAIL_SYSPROMPT_DELTA = 0x200, /* | span index: SYSTEM_PROMPT declared in a DELTA job */
};

/* Parse a JOB_BEGIN payload (v0.1 or v0.2). Returns ERR_OK, ERR_BAD_PARAM or ERR_CTX_OVERFLOW
 * (span_count > PROTO_MAX_SPANS); *detail gets the ERROR detail. Session-state checks
 * (SESSION_MISMATCH) are done by the job engine, not here. */
uint8_t proto_parse_job_begin(const uint8_t *p, uint16_t len, proto_job_begin_t *jb, uint16_t *detail);
/* Encode a v0.2 JOB_BEGIN payload (host side / tests). Returns length or 0. */
size_t proto_put_job_begin(uint8_t *out, size_t cap, const proto_job_begin_t *jb);

/* ---- per-session state (device side; pure C so the host test can drive it) -------------- */
#define PROTO_MAX_SESSION_SPANS 32u /* persistent protected spans per session */

/* A protected span recorded for the session, in SESSION input coordinates (byte offset in
 * the concatenated input since the last FULL), so it stays valid while later DELTA jobs only
 * send new bytes and the span itself sits in the cache-stable prefix and is never re-sent. */
typedef struct {
    uint32_t offset;
    uint32_t len;
    uint8_t kind;      /* SPAN_TASK, SPAN_OTHER or SPAN_SYSTEM_PROMPT */
    uint16_t job_id;   /* job that declared it */
} proto_session_span_t;

typedef struct {
    uint32_t session_id;   /* PROTO_SESSION_NONE = free slot */
    uint32_t in_len;       /* session input bytes received since the last FULL */
    uint32_t in_xxh;       /* xxh32 (seed 0) of those bytes, maintained by the job engine */
    uint32_t prev_out_len; /* previous result of this session (cache-stable report) */
    uint32_t prev_out_xxh;
    uint8_t span_count;
    proto_session_span_t spans[PROTO_MAX_SESSION_SPANS]; /* sorted by offset */
    /* job in progress (between proto_session_begin_job and _commit_job) */
    uint32_t job_base;     /* session offset of this job's byte 0 */
    uint8_t job_span_count;
    proto_span_t job_spans[PROTO_MAX_SPANS]; /* this job's spans incl. LATEST_TOOL_OUTPUT */
} proto_session_t;

void proto_session_init(proto_session_t *s);
/* Validate a parsed JOB_BEGIN against the session and apply it atomically:
 *  - FULL: (re)starts the session: drops ALL recorded spans, in_len = 0, then records the
 *    job's persistent spans (incl. SYSTEM_PROMPT).
 *  - DELTA: session_id must match and prefix_len/prefix_xxh must equal in_len/in_xxh, else
 *    ERR_SESSION_MISMATCH (detail SESS_MM_*) and *s is left unchanged. Recorded spans
 *    (incl. SYSTEM_PROMPT) are kept; the job's persistent spans are appended at
 *    in_len + offset.
 * Returns ERR_OK, ERR_SESSION_MISMATCH, ERR_BAD_PARAM or ERR_CTX_OVERFLOW (span table or
 * 32-bit session offset overflow). */
uint8_t proto_session_begin_job(proto_session_t *s, const proto_job_begin_t *jb, uint16_t *detail);
/* After JOB_END: the job's input becomes part of the session prefix. */
void proto_session_commit_job(proto_session_t *s, uint32_t job_len, uint32_t new_in_xxh,
                              uint32_t out_len, uint32_t out_xxh);
/* Is any byte of [offset, offset+len) in session coordinates protected (recorded spans or
 * spans of the job in progress)? Returns the kind of the first hit, or -1. */
int proto_session_protected_kind(const proto_session_t *s, uint32_t offset, uint32_t len);

/* JOB_END response, v1.0 (usb_protocol.md 8.6). The reduced output is not sent back as
 * bytes: RESULT_READ returns one TK_SEG_RECORD_LEN record per segment (keep/drop list). */
enum { JOB_STATUS_DONE = 0, JOB_STATUS_NEED_PASS2 = 1, JOB_STATUS_OVERFLOW = 2 };
typedef struct {
    uint16_t job_id;
    uint8_t status;          /* JOB_STATUS_* */
    uint32_t seg_count;      /* records available via RESULT_READ (0 unless DONE) */
    uint32_t est_tokens_in;  /* job content bytes / 4 */
    uint32_t est_tokens_out; /* sum over kept segments of len / 4 */
    uint32_t kept_bytes;
    uint32_t dup_hits;
    uint32_t set_full;
} proto_job_result_t;
#define JOB_END_V01_LEN 6u
#define JOB_END_V10_LEN 27u
size_t proto_put_job_result(uint8_t *out, size_t cap, const proto_job_result_t *r);
uint8_t proto_parse_job_result(const uint8_t *p, uint16_t len, proto_job_result_t *r);

/* ---- reduction policy (SET_POLICY / GET_POLICY blob), v1.0 --------------------------------- */
#define POLICY_VERSION          1u
#define POLICY_PRESET_CUSTOM    0xFFu /* SET: base on current policy; GET: matches no preset */
#define POLICY_BLOB_MAX         64u
#define POLICY_TTL_NEVER        0u    /* ttl_s = 0: the session never expires (dedup-only) */
/* Segment types of the context engine scanner (stats order). */
enum { SEG_PROSE = 0, SEG_CODE = 1, SEG_DIFF = 2, SEG_LOG = 3, SEG_TYPE_COUNT };
#define SEG_TEXT SEG_PROSE
enum {
    POLICY_RULES_V01 = 0,     /* v0.1: rank the whole job, keep_pct of all job tokens (PoC variant D) */
    POLICY_RULES_SESSION = 1, /* v1.0 PM rules: exemptions, ratio on older tool output only (PoC variant S) */
};
enum {
    POL_TLV_KEEP_PCT = 0x01,     /* u8 1..100: keep ratio (older tool output; whole job under RULES_V01) */
    POL_TLV_DEDUP = 0x02,        /* u8 0/1: exact-duplicate segment removal */
    /* 0x03 (v0.2 CACHE_STABLE_PREFIX) is withdrawn: the cached prefix is never rewritten */
    POL_TLV_TYPE_WEIGHT = 0x04,  /* {seg_type u8, weight u16 LE 0..1000}, repeatable */
    POL_TLV_NEWEST_DEDUP = 0x05, /* u8 0/1: 1 = newest message also subject to cross-message dedup */
    POL_TLV_RULES = 0x06,        /* u8 POLICY_RULES_* */
    POL_TLV_TTL_S = 0x07,        /* u32 seconds: session idle TTL (provider cache), 0 = never */
    POL_TLV_OPTIONAL = 0x80,     /* type bit7: receiver may ignore if unknown */
};
#define POL_TLV_BUDGET_PCT POL_TLV_KEEP_PCT
/* POLICY_INVALID detail: header problems < 0x100, TLV problems = reason << 8 | tlv type */
enum {
    POL_DETAIL_VERSION = 0x01, POL_DETAIL_TRUNCATED = 0x02, POL_DETAIL_PRESET = 0x03,
    POL_DETAIL_BAD_LEN = 0x100, POL_DETAIL_BAD_VALUE = 0x200, POL_DETAIL_UNKNOWN = 0x300,
};

typedef struct {
    uint8_t preset;                       /* tk_mode_t or POLICY_PRESET_CUSTOM */
    uint8_t keep_pct;                     /* 1..100 */
    bool dedup;
    bool newest_dedup;
    uint8_t rules;                        /* POLICY_RULES_* */
    uint32_t ttl_s;                       /* 0 = never expires */
    uint16_t type_weight[SEG_TYPE_COUNT]; /* rank weight per segment type */
} proto_policy_t;
#define POLICY_BLOB_LEN 40u

void proto_policy_preset(tk_mode_t m, proto_policy_t *pol);
/* Parse a SET_POLICY blob on top of *cur (used when preset = CUSTOM). On success *out is the
 * new policy and ERR_OK is returned; otherwise ERR_POLICY_INVALID and *detail, *out untouched. */
uint8_t proto_policy_parse(const uint8_t *p, uint16_t len, const proto_policy_t *cur, proto_policy_t *out,
                           uint16_t *detail);
/* Serialize the fully expanded policy (GET_POLICY response). Returns length or 0. */
size_t proto_policy_serialize(const proto_policy_t *pol, uint8_t *out, size_t cap);

/* Handle one parse result and write the reply frame into out. Returns reply length (0 = no
 * reply). */
size_t proto_handle(proto_device_t *dev, proto_parse_result_t r, const proto_frame_t *f, uint8_t *out, size_t out_cap);

size_t proto_build_error(uint8_t *out, size_t cap, uint8_t seq, uint8_t orig_cmd, uint8_t code, uint16_t detail);

#endif
