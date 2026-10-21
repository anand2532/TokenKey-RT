/* TokenKey RT - v1.0 job layer (see jobs.h). */
#include "jobs.h"

#include <string.h>

static void put16(uint8_t *p, uint16_t v) { p[0] = (uint8_t)v; p[1] = (uint8_t)(v >> 8); }
static void put32(uint8_t *p, uint32_t v) { put16(p, (uint16_t)v); put16(p + 2, (uint16_t)(v >> 16)); }
static uint16_t get16(const uint8_t *p) { return (uint16_t)(p[0] | (p[1] << 8)); }
static uint32_t get32(const uint8_t *p) { return (uint32_t)get16(p) | ((uint32_t)get16(p + 2) << 16); }

#define SCRATCH (TK_SLOTS - 1u)

static void slot_free(tk_slot_t *sl)
{
    proto_session_init(&sl->s);
    tk_xxh32_reset(&sl->in_state, 0);
    sl->lru = 0;
    sl->last_ms = 0;
    tk_dupset_reset(&sl->dup);
}

void tk_jobs_init(tk_jobs_t *j, tk_slot_t *slots, tk_engine_t *eng, tk_mode_t mode)
{
    memset(j, 0, sizeof *j);
    j->slots = slots;
    j->eng = eng;
    for (uint32_t i = 0; i < TK_SLOTS; i++) {
        slot_free(&slots[i]);
    }
    proto_policy_preset(mode, &j->policy);
}

void tk_jobs_set_mode(tk_jobs_t *j, tk_mode_t mode) { proto_policy_preset(mode, &j->policy); }

static void remember_evicted(tk_jobs_t *j, uint32_t id)
{
    if (id != PROTO_SESSION_NONE) {
        j->evicted[j->evicted_pos] = id;
        j->evicted_pos = (uint8_t)((j->evicted_pos + 1u) % TK_EVICTED_RING);
    }
}

static bool was_evicted(const tk_jobs_t *j, uint32_t id)
{
    for (uint32_t i = 0; i < TK_EVICTED_RING; i++) {
        if (j->evicted[i] == id) {
            return true;
        }
    }
    return false;
}

static void forget_evicted(tk_jobs_t *j, uint32_t id)
{
    for (uint32_t i = 0; i < TK_EVICTED_RING; i++) {
        if (j->evicted[i] == id) {
            j->evicted[i] = PROTO_SESSION_NONE;
        }
    }
}

static int find_slot(const tk_jobs_t *j, uint32_t id)
{
    for (uint32_t i = 0; i < PROTO_MAX_SESSIONS; i++) {
        if (j->slots[i].s.session_id == id) {
            return (int)i;
        }
    }
    return -1;
}

static void job_abort(tk_jobs_t *j)
{
    if (j->state == JOB_PASS1 || j->state == JOB_PASS2) {
        tk_slot_t *sl = &j->slots[j->slot];
        if (j->state == JOB_PASS2) {
            tk_engine_rollback(j->eng, &sl->dup); /* undo this job's dupset inserts */
        }
        if (j->job_full) {
            /* FULL reset the slot's dupset at JOB_BEGIN: the old session is gone */
            remember_evicted(j, sl->s.session_id);
            slot_free(sl);
        } else {
            sl->s = j->backup;
            sl->in_state = j->backup_state;
        }
    }
    j->state = JOB_IDLE;
}

bool tk_jobs_tick(tk_jobs_t *j, uint32_t now_ms)
{
    if ((j->state == JOB_PASS1 || j->state == JOB_PASS2) &&
        (uint32_t)(now_ms - j->now_begin) > TK_JOB_IDLE_TIMEOUT_MS) {
        job_abort(j);
        return true;
    }
    return false;
}

bool tk_jobs_cancel(tk_jobs_t *j)
{
    bool active = (j->state == JOB_PASS1 || j->state == JOB_PASS2);
    job_abort(j);
    return active;
}

uint8_t tk_jobs_progress(const tk_jobs_t *j)
{
    if (j->state == JOB_DONE) {
        return 100;
    }
    if ((j->state != JOB_PASS1 && j->state != JOB_PASS2) || j->total_len == 0) {
        return 0;
    }
    uint64_t done = j->rx_len + (j->state == JOB_PASS2 ? j->total_len : 0u);
    uint64_t all = (uint64_t)j->total_len * (j->state == JOB_PASS2 ? 2u : 1u);
    return (uint8_t)((done * 99u) / all);
}

static size_t rep(uint8_t *out, size_t cap, const proto_frame_t *f, const uint8_t *pl, uint16_t len)
{
    return proto_build(out, cap, (uint8_t)(f->cmd | PROTO_RESP_BIT), f->seq, pl, len);
}

static size_t err(uint8_t *out, size_t cap, const proto_frame_t *f, uint8_t code, uint16_t detail)
{
    return proto_build_error(out, cap, f->seq, f->cmd, code, detail);
}

/* ---- JOB_BEGIN ---------------------------------------------------------------------------- */
static size_t h_begin(tk_jobs_t *j, const proto_frame_t *f, uint32_t now, uint8_t *out, size_t cap)
{
    static proto_job_begin_t jb; /* 1.7 KB: kept off the task stack */
    static proto_session_t tmp;
    uint16_t detail = 0;
    uint8_t rc = proto_parse_job_begin(f->payload, f->len, &jb, &detail);
    if (rc != ERR_OK) {
        return err(out, cap, f, rc, detail);
    }
    uint8_t pl[2];
    put16(pl, jb.job_id);
    if (j->state == JOB_PASS1 || j->state == JOB_PASS2) {
        if (jb.job_id == j->job_id && jb.total_len == j->total_len && j->rx_len == 0 && j->state == JOB_PASS1) {
            j->now_begin = now;
            return rep(out, cap, f, pl, 2); /* retried JOB_BEGIN: re-ack */
        }
        return err(out, cap, f, ERR_BUSY, j->job_id);
    }
    if (jb.session_id == PROTO_SESSION_NONE) {
        jb.flags |= JOB_FLAG_FULL;
    }
    const bool full = (jb.flags & JOB_FLAG_FULL) != 0;
    int idx;
    if (jb.session_id == PROTO_SESSION_NONE) {
        idx = (int)SCRATCH;
    } else {
        idx = find_slot(j, jb.session_id);
        if (idx < 0 && !full) {
            return err(out, cap, f, ERR_SESSION_MISMATCH, was_evicted(j, jb.session_id) ? SESS_MM_EVICTED : SESS_MM_UNKNOWN);
        }
        if (idx >= 0 && !full && j->policy.ttl_s &&
            (uint32_t)(now - j->slots[idx].last_ms) > j->policy.ttl_s * 1000u) {
            /* provider cache is cold: SPEC 1.1 lapse, the host must start over with FULL */
            return err(out, cap, f, ERR_SESSION_MISMATCH, SESS_MM_EXPIRED);
        }
        if (idx < 0) {
            idx = find_slot(j, PROTO_SESSION_NONE);
            if (idx < 0) {
                idx = 0;
                for (uint32_t i = 1; i < PROTO_MAX_SESSIONS; i++) {
                    if (j->slots[i].lru < j->slots[idx].lru) {
                        idx = (int)i;
                    }
                }
            }
        }
    }
    tk_slot_t *sl = &j->slots[idx];
    tmp = sl->s;
    if (full && tmp.session_id != jb.session_id) {
        proto_session_init(&tmp);
    }
    rc = proto_session_begin_job(&tmp, &jb, &detail);
    if (rc != ERR_OK) {
        return err(out, cap, f, rc, detail); /* rejected: nothing changed */
    }
    /* commit */
    if (full && sl->s.session_id != PROTO_SESSION_NONE && sl->s.session_id != jb.session_id) {
        remember_evicted(j, sl->s.session_id); /* LRU victim */
    }
    j->backup = sl->s;
    j->backup_state = sl->in_state;
    sl->s = tmp;
    if (full) {
        tk_xxh32_reset(&sl->in_state, 0);
        tk_dupset_reset(&sl->dup); /* lapse: fresh dupset (SPEC 1.1) */
        forget_evicted(j, jb.session_id);
    }
    sl->lru = ++j->lru_clock;
    sl->last_ms = now;
    uint32_t nm;
    if (jb.has_msgs) {
        nm = jb.msg_count;
        for (uint32_t i = 0; i < nm; i++) {
            j->msgs[i].len = jb.msgs[i].len;
            j->msgs[i].role = jb.msgs[i].role;
            j->msgs[i].flags = jb.msgs[i].flags;
        }
    } else { /* v0.1/v0.2 host: one message, the newest: passed through, still hashed */
        nm = 1;
        j->msgs[0].len = jb.total_len;
        j->msgs[0].role = ROLE_TOOL;
        j->msgs[0].flags = MSGF_EXEMPT | MSGF_NEWEST;
    }
    for (uint32_t i = 0; i < jb.span_count; i++) {
        j->prot[i].off = jb.spans[i].offset;
        j->prot[i].len = jb.spans[i].len;
    }
    tk_engine_begin(j->eng, j->msgs, nm, jb.total_len, j->prot, jb.span_count, &j->policy, jb.token_budget);
    j->state = JOB_PASS1;
    j->job_id = jb.job_id;
    j->slot = (uint8_t)idx;
    j->total_len = jb.total_len;
    j->rx_len = 0;
    j->job_full = full;
    j->now_begin = now;
    tk_xxh32_reset(&j->job_h, 0);
    j->sess_h = sl->in_state;
    j->t0_cycles = j->cycles ? j->cycles() : 0u;
    return rep(out, cap, f, pl, 2);
}

/* ---- JOB_DATA (pass 1: offsets 0..total, pass 2: total..2*total) ----------------------------- */
static size_t h_data(tk_jobs_t *j, const proto_frame_t *f, uint32_t now, uint8_t *out, size_t cap)
{
    if (f->len < 6) {
        return err(out, cap, f, ERR_BAD_LEN, 6);
    }
    uint16_t id = get16(f->payload);
    uint32_t off = get32(f->payload + 2);
    uint32_t n = f->len - 6u;
    if ((j->state != JOB_PASS1 && j->state != JOB_PASS2) || id != j->job_id) {
        return err(out, cap, f, ERR_NO_JOB, id);
    }
    const uint32_t base = j->state == JOB_PASS2 ? j->total_len : 0u;
    uint8_t pl[6];
    put16(pl, id);
    if (off >= base && off - base < j->rx_len && off - base + n <= j->rx_len) { /* duplicate: re-ack */
        put32(pl + 2, off + n);
        j->now_begin = now;
        return rep(out, cap, f, pl, 6);
    }
    if (off < base || off - base != j->rx_len) {
        return err(out, cap, f, ERR_BAD_OFFSET, 0);
    }
    if (n > j->total_len - j->rx_len) {
        return err(out, cap, f, ERR_CTX_OVERFLOW, 1);
    }
    const uint8_t *d = f->payload + 6;
    tk_xxh32_update(&j->job_h, d, n);
    if (j->state == JOB_PASS1) {
        tk_xxh32_update(&j->sess_h, d, n);
        tk_engine_feed(j->eng, d, n);
    } else {
        tk_engine_feed2(j->eng, d, n);
    }
    j->rx_len += n;
    j->now_begin = now;
    put32(pl + 2, base + j->rx_len);
    return rep(out, cap, f, pl, 6);
}

static void job_commit(tk_jobs_t *j)
{
    tk_slot_t *sl = &j->slots[j->slot];
    tk_engine_t *e = j->eng;
    sl->in_state = j->sess_h;
    proto_session_commit_job(&sl->s, j->total_len, tk_xxh32_digest(&sl->in_state), e->kept_bytes, 0);
    uint32_t t1 = j->cycles ? j->cycles() : 0u;
    tk_stats_t *l = &j->last;
    memset(l, 0, sizeof *l);
    l->bytes_in = j->total_len;
    l->bytes_out = j->result.status == JOB_STATUS_DONE ? e->kept_bytes : j->total_len;
    l->tok_in = e->tok_in;
    l->tok_out = j->result.status == JOB_STATUS_DONE ? e->tok_out : e->tok_in;
    l->dup_hits = e->dup_hits;
    l->set_full = e->set_full;
    l->cycles = t1 - j->t0_cycles;
    memcpy(l->seg, e->seg_count, sizeof l->seg);
    tk_stats_t *g = &j->lifetime;
    g->bytes_in += l->bytes_in;
    g->bytes_out += l->bytes_out;
    g->tok_in += l->tok_in;
    g->tok_out += l->tok_out;
    g->dup_hits += l->dup_hits;
    g->set_full += l->set_full;
    g->cycles += l->cycles;
    for (uint32_t i = 0; i < SEG_TYPE_COUNT; i++) {
        uint32_t s = (uint32_t)g->seg[i] + l->seg[i];
        g->seg[i] = (uint16_t)(s > 0xFFFFu ? 0xFFFFu : s);
    }
    j->last_job_id = j->job_id;
    j->last_savings_pct =
        l->bytes_in ? (uint8_t)(100u - (uint32_t)(((uint64_t)l->bytes_out * 100u) / l->bytes_in)) : 0u;
    j->jobs_done++;
    j->state = JOB_DONE;
}

/* ---- JOB_END ------------------------------------------------------------------------------ */
static size_t h_end(tk_jobs_t *j, const proto_frame_t *f, uint8_t *out, size_t cap)
{
    if (f->len < 6) {
        return err(out, cap, f, ERR_BAD_LEN, 6);
    }
    uint16_t id = get16(f->payload);
    uint32_t want = get32(f->payload + 2);
    uint8_t pl[JOB_END_V10_LEN];
    if (j->state == JOB_DONE && id == j->job_id) { /* retried JOB_END: same answer */
        return rep(out, cap, f, pl, (uint16_t)proto_put_job_result(pl, sizeof pl, &j->result));
    }
    if ((j->state != JOB_PASS1 && j->state != JOB_PASS2) || id != j->job_id) {
        return err(out, cap, f, ERR_NO_JOB, id);
    }
    if (j->rx_len != j->total_len) {
        if (j->state == JOB_PASS2 && j->rx_len == 0) { /* retried pass-1 JOB_END */
            return rep(out, cap, f, pl, (uint16_t)proto_put_job_result(pl, sizeof pl, &j->result));
        }
        return err(out, cap, f, ERR_BAD_OFFSET, 2); /* job stays open */
    }
    uint32_t got = tk_xxh32_digest(&j->job_h);
    if (got != want || (j->state == JOB_PASS2 && got != j->job_xxh)) {
        job_abort(j);
        return err(out, cap, f, ERR_HASH_MISMATCH, 0);
    }
    tk_engine_t *e = j->eng;
    uint8_t st;
    if (j->state == JOB_PASS1) {
        j->job_xxh = got;
        st = tk_engine_finish(e, &j->slots[j->slot].dup);
    } else {
        st = tk_engine_finish2(e);
    }
    proto_job_result_t *r = &j->result;
    memset(r, 0, sizeof *r);
    r->job_id = id;
    r->est_tokens_in = e->tok_in;
    r->dup_hits = e->dup_hits;
    r->set_full = e->set_full;
    if (st == ENG_NEED_PASS2) {
        r->status = JOB_STATUS_NEED_PASS2;
        j->state = JOB_PASS2;
        j->rx_len = 0;
        tk_xxh32_reset(&j->job_h, 0);
    } else {
        r->status = st == ENG_DONE ? JOB_STATUS_DONE : JOB_STATUS_OVERFLOW;
        r->seg_count = st == ENG_DONE ? e->nseg : 0u;
        r->est_tokens_out = st == ENG_DONE ? e->tok_out : e->tok_in;
        r->kept_bytes = st == ENG_DONE ? e->kept_bytes : j->total_len;
        job_commit(j); /* OVERFLOW too: the host forwards the job unreduced, session advances */
    }
    return rep(out, cap, f, pl, (uint16_t)proto_put_job_result(pl, sizeof pl, r));
}

/* ---- RESULT_READ: segment records -------------------------------------------------------- */
static size_t h_read(tk_jobs_t *j, const proto_frame_t *f, uint8_t *out, size_t cap)
{
    if (f->len < 8) {
        return err(out, cap, f, ERR_BAD_LEN, 8);
    }
    uint16_t id = get16(f->payload);
    uint32_t off = get32(f->payload + 2);
    uint32_t max = get16(f->payload + 6);
    if (j->state != JOB_DONE || id != j->job_id) {
        return err(out, cap, f, ERR_NO_JOB, id);
    }
    const uint32_t total = j->result.seg_count * TK_SEG_RECORD_LEN;
    if (off > total || off % TK_SEG_RECORD_LEN) {
        return err(out, cap, f, ERR_BAD_OFFSET, 0);
    }
    if (max > PROTO_MAX_PAYLOAD - 7u) {
        max = PROTO_MAX_PAYLOAD - 7u;
    }
    uint32_t n = total - off;
    if (n > max) {
        n = max;
    }
    n -= n % TK_SEG_RECORD_LEN; /* whole records only */
    static uint8_t pl[PROTO_MAX_PAYLOAD];
    put16(pl, id);
    put32(pl + 2, off);
    pl[6] = (off + n == total) ? 1u : 0u;
    for (uint32_t k = 0; k < n; k += TK_SEG_RECORD_LEN) {
        tk_engine_record(j->eng, (off + k) / TK_SEG_RECORD_LEN, pl + 7 + k);
    }
    return rep(out, cap, f, pl, (uint16_t)(7u + n));
}

static size_t h_stats(tk_jobs_t *j, const proto_frame_t *f, uint8_t *out, size_t cap)
{
    uint16_t id = f->len >= 2 ? get16(f->payload) : GET_STATS_LIFETIME;
    const tk_stats_t *s;
    if (id == GET_STATS_LIFETIME) {
        s = &j->lifetime;
    } else if (j->jobs_done && id == j->last_job_id) {
        s = &j->last;
    } else {
        return err(out, cap, f, ERR_NO_JOB, id);
    }
    uint8_t pl[GET_STATS_LEN];
    put32(pl + 0, s->bytes_in);
    put32(pl + 4, s->bytes_out);
    put32(pl + 8, s->tok_in);
    put32(pl + 12, s->tok_out);
    put32(pl + 16, s->dup_hits);
    for (uint32_t i = 0; i < SEG_TYPE_COUNT; i++) {
        put16(pl + 20 + 2 * i, s->seg[i]);
    }
    put32(pl + 28, s->set_full);
    put32(pl + 32, s->cycles);
    return rep(out, cap, f, pl, GET_STATS_LEN);
}

size_t tk_jobs_handle(tk_jobs_t *j, const proto_frame_t *f, uint32_t now_ms, uint8_t *out, size_t cap)
{
    uint8_t pl[POLICY_BLOB_MAX];
    switch (f->cmd) {
    case CMD_JOB_BEGIN:
        return h_begin(j, f, now_ms, out, cap);
    case CMD_JOB_DATA:
        return h_data(j, f, now_ms, out, cap);
    case CMD_JOB_END:
        return h_end(j, f, out, cap);
    case CMD_RESULT_READ:
        return h_read(j, f, out, cap);
    case CMD_JOB_ABORT: {
        if (f->len < 2) {
            return err(out, cap, f, ERR_BAD_LEN, 2);
        }
        uint16_t id = get16(f->payload);
        if (j->state == JOB_IDLE || id != j->job_id) {
            return err(out, cap, f, ERR_NO_JOB, id);
        }
        job_abort(j);
        put16(pl, id);
        return rep(out, cap, f, pl, 2);
    }
    case CMD_GET_STATS:
        return h_stats(j, f, out, cap);
    case CMD_RESET_STATS:
        memset(&j->lifetime, 0, sizeof j->lifetime);
        memset(&j->last, 0, sizeof j->last);
        j->jobs_done = 0;
        j->last_savings_pct = 0;
        return rep(out, cap, f, NULL, 0);
    case CMD_SET_POLICY: {
        proto_policy_t np;
        uint16_t detail = 0;
        uint8_t rc = proto_policy_parse(f->payload, f->len, &j->policy, &np, &detail);
        if (rc != ERR_OK) {
            return err(out, cap, f, rc, detail);
        }
        j->policy = np; /* applies from the next JOB_BEGIN */
        return rep(out, cap, f, pl, (uint16_t)proto_policy_serialize(&j->policy, pl, sizeof pl));
    }
    case CMD_GET_POLICY:
        return rep(out, cap, f, pl, (uint16_t)proto_policy_serialize(&j->policy, pl, sizeof pl));
    default:
        return err(out, cap, f, ERR_UNKNOWN_CMD, 0);
    }
}
