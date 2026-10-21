/*
 * TokenKey RT - on-device context engine, v1.0. Pure C, bounded state, no allocation.
 *
 * Byte-exact port of the TokenKey PoC reference (handoff SPEC.md; ref tk_core.py run_job,
 * scan_message, DupSet; session_reducer.py; variants.py) re-shaped for an MCU
 * (docs/engine.md, "bounded design"):
 *  - the job content streams through once (pass 1): a line scanner with ONE line of lookahead
 *    and a TK_LINE_CAP byte cap builds a segment table (offset, length, XXH32, type); bytes are
 *    not retained;
 *  - JOB_END: duplicate check against the session dupset (8192 slots, 75 % cap, hash only,
 *    first occurrence kept), scoring and the greedy keep decision;
 *  - the diff reference bonus needs whole-job substring counts: when (and only when) it can
 *    change a keep decision, the host streams the job a second time (pass 2) and per-diff
 *    KMP counters produce the counts;
 *  - the device returns a keep/drop record per segment; the host assembles the output
 *    (and applies the "[TokenKey: content omitted]" placeholder).
 * Positions/protection come from the host's per-message flags (MSGF_*): the device does not
 * guess roles. See usb_protocol.md 8.5.
 */
#ifndef TK_ENGINE_H
#define TK_ENGINE_H

#include <stdbool.h>
#include <stdint.h>

#include "proto.h"
#include "xxh32.h"

#define TK_ENGINE_MAX_SEGS 4096u   /* PoC MAX_SEGMENTS (observed max 348) */
#define TK_DUPSET_SLOTS 8192u      /* PoC DUPSET_SLOTS */
#define TK_DUPSET_CAP (TK_DUPSET_SLOTS * 75u / 100u)
#define TK_LINE_CAP 2048u          /* scanner line buffer (observed max 664 B) */
#define TK_MAX_DIFF_REFS 128u      /* diff segments with a file id per job */
#define TK_BASENAME_CAP 128u       /* basename bytes */
#define TK_PROSE_MAX_LINES 64u
#define TK_SEG_RECORD_LEN 13u      /* RESULT_READ record: off u32, len u32, action u8, xxh32 u32 */

/* per-message flags in JOB_BEGIN (host computes them from positions, SPEC 1.2) */
#define MSGF_EXEMPT 0x01u /* exempt from the keep ratio (system, task, assistant, newest) */
#define MSGF_NEWEST 0x02u /* emitted verbatim: never dropped, still hashed into the dupset */

enum { SEG_ACT_KEEP = 0, SEG_ACT_DROP_DUP = 1, SEG_ACT_DROP_BUDGET = 2 };
enum { ENG_DONE = 0, ENG_NEED_PASS2 = 1, ENG_OVERFLOW = 2 };
enum { OVF_NONE = 0, OVF_SEGMENTS = 1, OVF_LINE = 2, OVF_DIFF_REFS = 3, OVF_BASENAME = 4 };

typedef struct {
    uint32_t hash[TK_DUPSET_SLOTS];
    uint8_t used[TK_DUPSET_SLOTS / 8u];
    uint32_t count;
    uint32_t set_full;
} tk_dupset_t;

typedef struct {
    uint32_t len;
    uint8_t role, flags;
} tk_msg_t;

typedef struct {
    uint32_t off, len;
} tk_range_t;

typedef struct {
    uint32_t off, len, hash;
    uint16_t msg;
    int16_t score;
    uint8_t type;
    uint8_t flags;  /* SF_* */
    uint8_t ref;    /* diff ref index + 1, 0 = none */
    uint8_t act;    /* SEG_ACT_* */
} tk_seg_t;

typedef struct {
    uint8_t base[TK_BASENAME_CAP];
    uint8_t fail[TK_BASENAME_CAP];
    uint16_t blen;
    bool empty;             /* basename "" (file id ends in '/') */
    uint16_t seg;
    uint16_t st_all, st_own;
    uint32_t n_all, n_own;
} tk_diffref_t;

typedef struct {
    /* job description */
    const tk_msg_t *msgs;
    uint32_t nmsg;
    uint32_t total;
    const tk_range_t *prot;
    uint32_t nprot;
    proto_policy_t pol;
    uint32_t token_budget;
    /* pass 1 scanner state */
    uint32_t pos;           /* content bytes consumed */
    uint32_t msg, msg_end;  /* current message and its end offset */
    uint8_t line[2][TK_LINE_CAP];
    uint32_t llen[2], loff[2];
    uint8_t cur;            /* index of the complete line waiting for lookahead */
    bool have_cur, building, pending_cr, seg_blank;
    uint8_t st;             /* scanner state */
    uint8_t fence[3];
    uint32_t chunk_lines;
    uint32_t seg_start;
    tk_xxh32_t h;
    uint8_t seg_type;
    int cur_ref;
    uint32_t nseg, nref, nundo;
    uint32_t set_full0;
    uint8_t overflow;       /* OVF_* */
    /* pass 2 */
    uint32_t p2_pos, p2_seg;
    uint8_t phase;          /* 0 pass 1, 1 waiting/doing pass 2, 2 done */
    /* result */
    uint32_t dup_hits, kept_bytes, tok_in, tok_out, set_full;
    uint16_t seg_count[SEG_TYPE_COUNT];
    /* tables (not cleared per job; filled as used) - keep last, see tk_engine_begin */
    tk_seg_t seg[TK_ENGINE_MAX_SEGS];
    tk_diffref_t ref[TK_MAX_DIFF_REFS];
    uint16_t order[TK_ENGINE_MAX_SEGS];
    uint16_t undo[TK_ENGINE_MAX_SEGS]; /* dupset slots inserted by this job (abort rollback) */
} tk_engine_t;

void tk_dupset_reset(tk_dupset_t *d);
/* PoC DupSet.check_insert: true if present; insert if absent and below the cap. *slot gets
 * the inserted slot or -1. */
bool tk_dupset_check_insert(tk_dupset_t *d, uint32_t h, int *slot);

/* Start a job. msgs/prot must stay valid until the job ends. */
void tk_engine_begin(tk_engine_t *e, const tk_msg_t *msgs, uint32_t nmsg, uint32_t total, const tk_range_t *prot,
                     uint32_t nprot, const proto_policy_t *pol, uint32_t token_budget);
/* Pass 1: stream content bytes in order. */
void tk_engine_feed(tk_engine_t *e, const uint8_t *d, uint32_t n);
/* End of pass 1 (all `total` bytes fed): dedup + decisions. Returns ENG_*. */
uint8_t tk_engine_finish(tk_engine_t *e, tk_dupset_t *dup);
/* Pass 2 (only after ENG_NEED_PASS2): stream the same bytes again, then finish_pass2. */
void tk_engine_feed2(tk_engine_t *e, const uint8_t *d, uint32_t n);
uint8_t tk_engine_finish2(tk_engine_t *e);
/* Abort after tk_engine_finish returned NEED_PASS2: undo this job's dupset inserts. */
void tk_engine_rollback(tk_engine_t *e, tk_dupset_t *dup);
/* Segment record i (TK_SEG_RECORD_LEN bytes). */
void tk_engine_record(const tk_engine_t *e, uint32_t i, uint8_t *out);

/* scanner helpers, exposed for tests */
bool tk_engine_log_line(const uint8_t *b, uint32_t n);

#endif
