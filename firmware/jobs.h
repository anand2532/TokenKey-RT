/*
 * TokenKey RT - v1.0 job layer: sessions (FULL/DELTA, LRU, TTL), the JOB_* state machine
 * (two-pass when the engine needs it), device-global policy and statistics. Pure C, bounded,
 * no allocation; the firmware (usb_task) and the host simulator link the same code.
 * usb_protocol.md 3, 5, 8, 9; docs/engine.md.
 */
#ifndef TK_JOBS_H
#define TK_JOBS_H

#include <stdbool.h>
#include <stdint.h>

#include "engine.h"
#include "proto.h"
#include "xxh32.h"

#define TK_SLOTS (PROTO_MAX_SESSIONS + 1u) /* + one scratch slot for stateless jobs */
#define TK_EVICTED_RING 8u
#define TK_JOB_IDLE_TIMEOUT_MS 5000u
#define GET_STATS_LEN 36u
#define GET_STATS_LIFETIME 0xFFFFu

typedef enum { JOB_IDLE = 0, JOB_PASS1, JOB_PASS2, JOB_DONE } tk_job_state_t;

typedef struct {
    uint32_t bytes_in, bytes_out, tok_in, tok_out, dup_hits, set_full, cycles;
    uint16_t seg[SEG_TYPE_COUNT];
} tk_stats_t;

typedef struct {
    proto_session_t s;
    tk_xxh32_t in_state;  /* running xxh32 of the session input since FULL */
    uint32_t lru;
    uint32_t last_ms;     /* JOB_BEGIN time of the last job (TTL) */
    tk_dupset_t dup;
} tk_slot_t;

typedef struct tk_jobs {
    tk_slot_t *slots;     /* TK_SLOTS entries (caller-provided storage) */
    tk_engine_t *eng;     /* one engine: one active job */
    proto_policy_t policy;
    uint32_t lru_clock;
    uint32_t evicted[TK_EVICTED_RING];
    uint8_t evicted_pos;
    /* active job */
    tk_job_state_t state;
    uint16_t job_id;
    uint8_t slot;
    uint32_t total_len, rx_len, now_begin;
    bool job_full;
    tk_xxh32_t job_h;     /* this pass's xxh32 (JOB_END check) */
    tk_xxh32_t sess_h;    /* session running hash incl. this job */
    uint32_t job_xxh;     /* pass-1 hash, pass 2 must match */
    tk_msg_t msgs[PROTO_MAX_MSGS];
    tk_range_t prot[PROTO_MAX_SPANS];
    proto_session_t backup;
    tk_xxh32_t backup_state;
    proto_job_result_t result;
    /* stats */
    tk_stats_t lifetime, last;
    uint16_t last_job_id;
    uint8_t last_savings_pct;
    uint32_t jobs_done;
    uint32_t (*cycles)(void);
    uint32_t t0_cycles;
} tk_jobs_t;

void tk_jobs_init(tk_jobs_t *j, tk_slot_t *slots, tk_engine_t *eng, tk_mode_t mode);
void tk_jobs_set_mode(tk_jobs_t *j, tk_mode_t mode);
bool tk_jobs_tick(tk_jobs_t *j, uint32_t now_ms);
uint8_t tk_jobs_progress(const tk_jobs_t *j);
/* Abort the active job (device-side cancel, e.g. BTN2): session restored as on timeout. */
bool tk_jobs_cancel(tk_jobs_t *j);
size_t tk_jobs_handle(tk_jobs_t *j, const proto_frame_t *f, uint32_t now_ms, uint8_t *out, size_t cap);

#endif
