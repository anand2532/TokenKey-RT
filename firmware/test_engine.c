/* Host tests (C, run under ASan/UBSan in the sanitizer build): xxh32, dupset, scanner,
 * engine edge cases (line terminators, caps, pass 2, rollback) and the v1.0 job/session
 * flows through proto_handle. Corpus byte-equality is tests/test_corpus.py. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "engine.h"
#include "jobs.h"
#include "proto.h"
#include "xxh32.h"

static int fails, checks;
#define CHECK(c)                                                                \
    do {                                                                        \
        checks++;                                                               \
        if (!(c)) {                                                             \
            fails++;                                                            \
            fprintf(stderr, "%s:%d: CHECK(%s) failed\n", __FILE__, __LINE__, #c); \
        }                                                                       \
    } while (0)

static void put16(uint8_t *p, uint16_t v) { p[0] = (uint8_t)v; p[1] = (uint8_t)(v >> 8); }
static void put32(uint8_t *p, uint32_t v) { put16(p, (uint16_t)v); put16(p + 2, (uint16_t)(v >> 16)); }
static uint16_t get16(const uint8_t *p) { return (uint16_t)(p[0] | (p[1] << 8)); }
static uint32_t get32(const uint8_t *p) { return (uint32_t)get16(p) | ((uint32_t)get16(p + 2) << 16); }

static void test_xxh32(void)
{
    CHECK(tk_xxh32("", 0, 0) == 0x02CC5D05u);
    CHECK(tk_xxh32("a", 1, 0) == 0x550D7456u);
    CHECK(tk_xxh32("abc", 3, 0) == 0x32D153FFu);
    const char *s = "Nobody inspects the spammish repetition";
    CHECK(tk_xxh32(s, strlen(s), 0) == 0xE2293B2Fu);
    uint8_t b[300];
    for (int i = 0; i < 300; i++) {
        b[i] = (uint8_t)(i * 7 + 3);
    }
    for (uint32_t seed = 0; seed < 2; seed++) {
        uint32_t ref = tk_xxh32(b, sizeof b, seed);
        for (size_t cut = 0; cut <= sizeof b; cut += 13) {
            tk_xxh32_t st;
            tk_xxh32_reset(&st, seed);
            tk_xxh32_update(&st, b, cut);
            (void)tk_xxh32_digest(&st);
            for (size_t k = cut; k < sizeof b; k += 5) {
                tk_xxh32_update(&st, b + k, (sizeof b - k) < 5 ? sizeof b - k : 5);
            }
            CHECK(tk_xxh32_digest(&st) == ref);
        }
    }
}

static tk_dupset_t dup;

static void test_dupset(void)
{
    int slot;
    tk_dupset_reset(&dup);
    CHECK(!tk_dupset_check_insert(&dup, 5, &slot) && slot == 5);
    CHECK(tk_dupset_check_insert(&dup, 5, &slot) && slot == -1);
    CHECK(!tk_dupset_check_insert(&dup, 5 + TK_DUPSET_SLOTS, &slot) && slot == 6); /* linear probe */
    CHECK(!tk_dupset_check_insert(&dup, 0, &slot) && slot == 0);                    /* hash 0 is a valid key */
    CHECK(tk_dupset_check_insert(&dup, 0, &slot));
    for (uint32_t h = 100; dup.count < TK_DUPSET_CAP; h++) {
        tk_dupset_check_insert(&dup, h, &slot);
    }
    CHECK(dup.count == 6144);
    CHECK(!tk_dupset_check_insert(&dup, 0xABCDEF, &slot) && slot == -1 && dup.set_full == 1); /* full: no dedup */
    CHECK(!tk_dupset_check_insert(&dup, 0xABCDEF, &slot) && dup.set_full == 2);
    CHECK(tk_dupset_check_insert(&dup, 5, &slot)); /* lookups still work */
}

static bool L(const char *s) { return tk_engine_log_line((const uint8_t *)s, (uint32_t)strlen(s)); }

static void test_log_regex(void)
{
    CHECK(L("Traceback (most recent call last):\n"));
    CHECK(L("  File \"a.py\", line 12, in f\n"));
    CHECK(!L("  File \"a.py\", line x\n"));
    CHECK(L("E   assert 1 == 2\n"));
    CHECK(!L("E x\n"));
    CHECK(L("ValueError: bad\n"));
    CHECK(L("Error: x\n"));
    CHECK(!L("my Error: x\n")); /* \w*Error: must start the line; "Error" is not a \b token */
    CHECK(L("some FAILED test\n"));
    CHECK(!L("FAILEDX\n"));
    CHECK(L("x WARNING y\n") && L("panic\n") && L("x fatal\n") && !L("fatalism\n"));
    CHECK(L("2026-10-21 18:04 start\n") && L("2026-10-21T18:04:00\n"));
    CHECK(L("[ 12.345] usb 1-1: new\n") && !L("[12] x\n"));
    CHECK(L("    at Foo.bar (foo.js:12)\n") && !L("at Foo.bar (foo.js:12)\n") && !L("    at x (y)\n"));
    CHECK(!L("plain prose line\n"));
}

/* run the engine directly; acts[] per segment */
static tk_engine_t eng;
static uint32_t run_direct(const char *const *msgs, const uint8_t *flags, uint32_t n, const proto_policy_t *pol,
                           uint8_t *status, uint32_t chunk)
{
    static uint8_t content[65536];
    static tk_msg_t m[64];
    uint32_t total = 0;
    for (uint32_t i = 0; i < n; i++) {
        uint32_t l = (uint32_t)strlen(msgs[i]);
        memcpy(content + total, msgs[i], l);
        total += l;
        m[i].len = l;
        m[i].flags = flags[i];
        m[i].role = 0;
    }
    tk_engine_begin(&eng, m, n, total, NULL, 0, pol, 0);
    for (uint32_t o = 0; o < total; o += chunk) {
        tk_engine_feed(&eng, content + o, total - o < chunk ? total - o : chunk);
    }
    *status = tk_engine_finish(&eng, &dup);
    if (*status == ENG_NEED_PASS2) {
        for (uint32_t o = 0; o < total; o += chunk) {
            tk_engine_feed2(&eng, content + o, total - o < chunk ? total - o : chunk);
        }
        *status = tk_engine_finish2(&eng);
    }
    return eng.nseg;
}

static void test_engine(void)
{
    proto_policy_t pol;
    proto_policy_preset(MODE_S_PROTECT, &pol);
    uint8_t st;
    /* segmentation + all line terminators of Python str.splitlines, chunk sizes 1 and 7 */
    const char *m1[] = {"para one\r\nstill\rpara\x0bmore\xc2\x85u\xe2\x80\xa8v\n\n```c\nint x;\n```\nok\n"};
    uint8_t f1[] = {MSGF_EXEMPT};
    for (uint32_t ch = 1; ch <= 7; ch += 6) {
        tk_dupset_reset(&dup);
        uint32_t n = run_direct(m1, f1, 1, &pol, &st, ch);
        CHECK(st == ENG_DONE && n == 3); /* PoC scan_message: prose 34, code 16, prose 3 */
        CHECK(eng.seg[0].type == SEG_PROSE && eng.seg[0].len == strlen("para one\r\nstill\rpara\x0bmore\xc2\x85u\xe2\x80\xa8v\n\n"));
        CHECK(eng.seg[1].type == SEG_CODE && eng.seg[1].len == 16 && eng.seg[2].type == SEG_PROSE && eng.seg[2].len == 3);
    }
    /* dedup: second copy dropped, whitespace-only never dropped, newest kept verbatim but hashed */
    const char *m2[] = {"sys\n", "task text\n", "same block\n\n", "same block\n\n", "same block\n\n"};
    uint8_t f2[] = {MSGF_EXEMPT, MSGF_EXEMPT, MSGF_EXEMPT, MSGF_EXEMPT, MSGF_EXEMPT | MSGF_NEWEST};
    tk_dupset_reset(&dup);
    run_direct(m2, f2, 5, &pol, &st, 64);
    CHECK(st == ENG_DONE && eng.seg[2].act == SEG_ACT_KEEP && eng.seg[3].act == SEG_ACT_DROP_DUP &&
          eng.seg[4].act == SEG_ACT_KEEP && eng.dup_hits == 2);
    /* the newest's hash went into the dupset: a later job drops that block */
    const char *m3[] = {"same block\n\n", "new\n"};
    uint8_t f3[] = {MSGF_EXEMPT, MSGF_EXEMPT | MSGF_NEWEST};
    run_direct(m3, f3, 2, &pol, &st, 64);
    CHECK(eng.seg[0].act == SEG_ACT_DROP_DUP && eng.seg[1].act == SEG_ACT_KEEP);
    /* ratio on older tool output (Economy) with diffs -> pass 2 needed; rollback restores dupset */
    proto_policy_t eco;
    proto_policy_preset(MODE_ECONOMY, &eco);
    static char big[8192];
    int k = sprintf(big, "diff --git a/src/x.c b/src/x.c\n--- a/src/x.c\n+++ b/src/x.c\n@@ -1 +1 @@\n-a\n+b\n\n");
    for (int i = 0; i < 40; i++) {
        k += sprintf(big + k, "line %d of an older tool output mentioning x.c\n\n", i);
    }
    const char *m4[] = {"sys\n", "task x.c\n", "assistant\n", big, "assistant 2\n", "newest\n"};
    uint8_t f4[] = {MSGF_EXEMPT, MSGF_EXEMPT, MSGF_EXEMPT, 0, MSGF_EXEMPT, MSGF_EXEMPT | MSGF_NEWEST};
    tk_dupset_reset(&dup);
    run_direct(m4, f4, 6, &eco, &st, 100);
    CHECK(st == ENG_DONE && eng.nref == 1 && eng.ref[0].n_all >= 40);
    CHECK(eng.seg[3].type == SEG_DIFF && eng.seg[3].act == SEG_ACT_KEEP); /* diff + ref bonus ranks first */
    uint32_t kept = 0;
    for (uint32_t i = 0; i < eng.nseg; i++) {
        kept += eng.seg[i].act == SEG_ACT_KEEP;
    }
    CHECK(kept < eng.nseg);
    tk_dupset_reset(&dup);
    static tk_msg_t mm[6];
    uint32_t total = 0;
    for (int i = 0; i < 6; i++) {
        mm[i].len = (uint32_t)strlen(m4[i]);
        mm[i].flags = f4[i];
        total += mm[i].len;
    }
    tk_engine_begin(&eng, mm, 6, total, NULL, 0, &eco, 0);
    for (int i = 0; i < 6; i++) {
        tk_engine_feed(&eng, (const uint8_t *)m4[i], mm[i].len);
    }
    CHECK(tk_engine_finish(&eng, &dup) == ENG_NEED_PASS2 && dup.count > 0);
    tk_engine_rollback(&eng, &dup);
    uint32_t used = 0;
    for (uint32_t i = 0; i < sizeof dup.used; i++) {
        used += dup.used[i];
    }
    CHECK(dup.count == 0 && used == 0);
    /* line cap -> overflow (pass-through), dupset untouched */
    static char longl[TK_LINE_CAP + 10];
    memset(longl, 'x', sizeof longl - 2);
    longl[sizeof longl - 2] = '\n';
    longl[sizeof longl - 1] = 0;
    const char *m5[] = {longl};
    run_direct(m5, f1, 1, &pol, &st, 512);
    CHECK(st == ENG_OVERFLOW && eng.overflow == OVF_LINE && dup.count == 0);
    /* segment cap (checked per segment) */
    static char many[(TK_ENGINE_MAX_SEGS + 2) * 2 + 1];
    for (uint32_t i = 0; i < TK_ENGINE_MAX_SEGS + 2; i++) {
        many[2 * i] = '\n';
        many[2 * i + 1] = '\n';
    }
    const char *m6[] = {many};
    run_direct(m6, f1, 1, &pol, &st, 4096);
    CHECK(st == ENG_OVERFLOW && eng.overflow == OVF_SEGMENTS && dup.count == 0);
    /* empty messages and empty job */
    const char *m7[] = {"", "a\n", ""};
    uint8_t f7[] = {MSGF_EXEMPT, MSGF_EXEMPT, MSGF_EXEMPT};
    CHECK(run_direct(m7, f7, 3, &pol, &st, 3) == 1 && st == ENG_DONE && eng.seg[0].msg == 1);
    CHECK(run_direct(m7, f7, 1, &pol, &st, 3) == 0 && st == ENG_DONE);
}

/* ---- job flows through proto_handle ------------------------------------------------------- */
static tk_slot_t slots[TK_SLOTS];
static tk_engine_t jeng;
static tk_jobs_t jobs;
static proto_device_t dev;
static uint8_t seq;
static proto_frame_t rx;

static uint8_t xfer(uint8_t cmd, const uint8_t *pl, uint16_t len)
{
    static uint8_t fr[PROTO_MAX_FRAME], rep[PROTO_MAX_FRAME];
    static proto_parser_t p;
    size_t fl = proto_build(fr, sizeof fr, cmd, ++seq, pl, len);
    proto_parser_init(&p);
    proto_parse_result_t r = PARSE_NONE;
    for (size_t i = 0; i < fl; i++) {
        r = proto_parser_feed(&p, fr[i]);
    }
    CHECK(r == PARSE_FRAME);
    size_t rl = proto_handle(&dev, r, &p.frame, rep, sizeof rep);
    proto_parser_init(&p);
    r = PARSE_NONE;
    for (size_t i = 0; i < rl; i++) {
        r = proto_parser_feed(&p, rep[i]);
    }
    CHECK(r == PARSE_FRAME);
    rx = p.frame;
    CHECK(rx.seq == seq);
    if (rx.cmd == CMD_ERROR) {
        return rx.payload[1];
    }
    CHECK(rx.cmd == (cmd | PROTO_RESP_BIT));
    return ERR_OK;
}

static uint16_t err_detail(void) { return get16(rx.payload + 2); }

static uint8_t begin(uint16_t id, const char *const *m, const uint8_t *fl, uint8_t n, bool full, uint32_t sess,
                     uint32_t plen, uint32_t pxxh)
{
    static proto_job_begin_t jb;
    memset(&jb, 0, sizeof jb);
    jb.job_id = id;
    jb.flags = (uint8_t)((full ? JOB_FLAG_FULL : 0) | JOB_FLAG_MESSAGES);
    jb.session_id = sess;
    jb.prefix_len = plen;
    jb.prefix_xxh = pxxh;
    jb.v02 = jb.has_msgs = true;
    jb.msg_count = n;
    for (uint8_t i = 0; i < n; i++) {
        jb.msgs[i].len = (uint32_t)strlen(m[i]);
        jb.msgs[i].flags = fl[i];
        jb.total_len += jb.msgs[i].len;
    }
    uint8_t pl[2048];
    size_t l = proto_put_job_begin(pl, sizeof pl, &jb);
    CHECK(l > 0);
    return xfer(CMD_JOB_BEGIN, pl, (uint16_t)l);
}

static uint8_t data(uint16_t id, uint32_t off, const void *d, uint32_t n)
{
    static uint8_t pl[PROTO_MAX_PAYLOAD];
    put16(pl, id);
    put32(pl + 2, off);
    memcpy(pl + 6, d, n);
    return xfer(CMD_JOB_DATA, pl, (uint16_t)(6 + n));
}

static uint8_t end(uint16_t id, uint32_t xxh, proto_job_result_t *res)
{
    uint8_t pl[6];
    put16(pl, id);
    put32(pl + 2, xxh);
    uint8_t rc = xfer(CMD_JOB_END, pl, 6);
    if (rc == ERR_OK) {
        CHECK(rx.len == JOB_END_V10_LEN);
        proto_parse_job_result(rx.payload, rx.len, res);
    }
    return rc;
}

static char jcontent[16384];
static uint32_t join(const char *const *m, uint8_t n)
{
    uint32_t t = 0;
    for (uint8_t i = 0; i < n; i++) {
        size_t l = strlen(m[i]);
        memcpy(jcontent + t, m[i], l);
        t += (uint32_t)l;
    }
    return t;
}

static uint8_t run_job(uint16_t id, const char *const *m, const uint8_t *fl, uint8_t n, bool full, uint32_t sess,
                       uint32_t plen, uint32_t pxxh, proto_job_result_t *res)
{
    uint8_t rc = begin(id, m, fl, n, full, sess, plen, pxxh);
    if (rc != ERR_OK) {
        return rc;
    }
    uint32_t t = join(m, n), h = tk_xxh32(jcontent, t, 0);
    for (int pass = 0; pass < 2; pass++) {
        for (uint32_t o = 0; o < t; o += 1000) {
            uint32_t k = t - o < 1000 ? t - o : 1000;
            CHECK(data(id, (uint32_t)pass * t + o, jcontent + o, k) == ERR_OK);
        }
        rc = end(id, h, res);
        if (rc != ERR_OK || res->status != JOB_STATUS_NEED_PASS2) {
            return rc;
        }
    }
    return rc;
}

static void reset_dev(void)
{
    memset(&dev, 0, sizeof dev);
    dev.mode = MODE_DEFAULT;
    dev.caps = PROTO_CAP_EVENTS;
    dev.jobs = &jobs;
    tk_jobs_init(&jobs, slots, &jeng, dev.mode);
}

static void test_jobs(void)
{
    reset_dev();
    uint8_t pl[64];
    pl[0] = 1;
    put16(pl + 1, 4096);
    CHECK(xfer(CMD_HELLO, pl, 3) == ERR_OK && get32(rx.payload + 11) == (PROTO_CAP_EVENTS | PROTO_CAP_SESSIONS));
    CHECK(xfer(CMD_GET_MODE, NULL, 0) == ERR_OK && rx.payload[0] == MODE_S_PROTECT && rx.payload[1] == 100);

    const uint32_t S = 0xC0FFEE01u;
    const char *r1[] = {"system prompt\n", "the task\n", "assistant one\n", "tool out\n\nrepeated block\n\n"};
    uint8_t f1[] = {1, 1, 1, 3};
    proto_job_result_t res;
    CHECK(run_job(1, r1, f1, 4, true, S, 0, 0, &res) == ERR_OK && res.status == JOB_STATUS_DONE && res.seg_count == 5);
    /* records */
    put16(pl, 1);
    put32(pl + 2, 0);
    put16(pl + 6, 4000);
    CHECK(xfer(CMD_RESULT_READ, pl, 8) == ERR_OK && rx.payload[6] == 1 && rx.len == 7 + 5 * TK_SEG_RECORD_LEN);
    CHECK(get32(rx.payload + 7) == 0 && rx.payload[7 + 8] == SEG_ACT_KEEP);
    put16(pl + 6, 20); /* max smaller than two records: whole records only */
    CHECK(xfer(CMD_RESULT_READ, pl, 8) == ERR_OK && rx.len == 7 + TK_SEG_RECORD_LEN && rx.payload[6] == 0);
    put32(pl + 2, 5);
    CHECK(xfer(CMD_RESULT_READ, pl, 8) == ERR_BAD_OFFSET);
    uint32_t plen = join(r1, 4), pxxh = tk_xxh32(jcontent, plen, 0);

    /* warm DELTA: the repeated block in the new assistant message is dropped */
    const char *r2[] = {"repeated block\n\nnew words\n", "newest output\n"};
    uint8_t f2[] = {1, 3};
    dev.uptime_ms = 100000;
    CHECK(run_job(2, r2, f2, 2, false, S, plen, pxxh, &res) == ERR_OK && res.status == JOB_STATUS_DONE && res.dup_hits == 1);
    tk_xxh32_t hs;
    tk_xxh32_reset(&hs, 0);
    tk_xxh32_update(&hs, jcontent, join(r1, 4));
    uint32_t l2 = join(r2, 2);
    tk_xxh32_update(&hs, jcontent, l2);
    plen += l2;
    pxxh = tk_xxh32_digest(&hs);
    /* mismatches leave the session unchanged */
    CHECK(begin(3, r2, f2, 2, false, S, plen - 1, pxxh) == ERR_SESSION_MISMATCH && err_detail() == SESS_MM_PREFIX_LEN);
    CHECK(begin(3, r2, f2, 2, false, S, plen, pxxh ^ 1) == ERR_SESSION_MISMATCH && err_detail() == SESS_MM_PREFIX_XXH);
    CHECK(begin(3, r2, f2, 2, false, 0x1234, 0, 0) == ERR_SESSION_MISMATCH && err_detail() == SESS_MM_UNKNOWN);
    /* abort of a DELTA restores the session; BUSY / BAD_OFFSET / overflow / re-ack */
    CHECK(begin(4, r2, f2, 2, false, S, plen, pxxh) == ERR_OK);
    CHECK(begin(5, r2, f2, 2, true, 9, 0, 0) == ERR_BUSY);
    CHECK(data(4, 0, "repe", 4) == ERR_OK);
    CHECK(data(4, 0, "repe", 4) == ERR_OK && get32(rx.payload + 2) == 4);
    CHECK(data(4, 8, "xx", 2) == ERR_BAD_OFFSET);
    CHECK(end(4, 0, &res) == ERR_BAD_OFFSET);
    put16(pl, 4);
    CHECK(xfer(CMD_JOB_ABORT, pl, 2) == ERR_OK && xfer(CMD_JOB_ABORT, pl, 2) == ERR_NO_JOB);
    /* hash mismatch aborts; then a correct job still continues the session */
    CHECK(begin(6, r2, f2, 2, false, S, plen, pxxh) == ERR_OK);
    uint32_t t = join(r2, 2);
    CHECK(data(6, 0, jcontent, t) == ERR_OK && end(6, 1, &res) == ERR_HASH_MISMATCH);
    CHECK(run_job(7, r2, f2, 2, false, S, plen, pxxh, &res) == ERR_OK && res.dup_hits == 3);
    CHECK(end(7, tk_xxh32(jcontent, t, 0), &res) == ERR_OK); /* retried JOB_END */
    tk_xxh32_update(&hs, jcontent, t);
    plen += t;
    pxxh = tk_xxh32_digest(&hs);
    /* TTL: > 300 s since the last job -> EXPIRED */
    dev.uptime_ms = 100000 + 300001;
    CHECK(begin(8, r2, f2, 2, false, S, plen, pxxh) == ERR_SESSION_MISMATCH && err_detail() == SESS_MM_EXPIRED);
    /* stats */
    put16(pl, GET_STATS_LIFETIME);
    CHECK(xfer(CMD_GET_STATS, pl, 2) == ERR_OK && rx.len == GET_STATS_LEN && get32(rx.payload) > 0);
    put16(pl, 7);
    CHECK(xfer(CMD_GET_STATS, pl, 2) == ERR_OK && get32(rx.payload) == t);
    put16(pl, 2);
    CHECK(xfer(CMD_GET_STATS, pl, 2) == ERR_NO_JOB);
    CHECK(xfer(CMD_RESET_STATS, NULL, 0) == ERR_OK && rx.len == 0);
    /* LRU eviction after 4 other sessions */
    const char *one[] = {"hello\n"};
    uint8_t fo[] = {3};
    for (uint32_t k = 0; k < PROTO_MAX_SESSIONS; k++) {
        CHECK(run_job((uint16_t)(20 + k), one, fo, 1, true, 100 + k, 0, 0, &res) == ERR_OK);
    }
    CHECK(begin(30, r2, f2, 2, false, S, plen, pxxh) == ERR_SESSION_MISMATCH && err_detail() == SESS_MM_EVICTED);
    /* v0.1 JOB_BEGIN: one message, passed through */
    uint8_t v01[11];
    put16(v01, 40);
    put32(v01 + 2, 5);
    v01[6] = 0;
    put32(v01 + 7, 0);
    CHECK(xfer(CMD_JOB_BEGIN, v01, 11) == ERR_OK);
    CHECK(data(40, 0, "hi!!\n", 5) == ERR_OK);
    CHECK(end(40, tk_xxh32("hi!!\n", 5, 0), &res) == ERR_OK && res.seg_count == 1 && res.kept_bytes == 5);
    /* idle timeout */
    dev.uptime_ms = 1000;
    CHECK(begin(42, one, fo, 1, true, 78, 0, 0) == ERR_OK);
    CHECK(data(42, 0, "hel", 3) == ERR_OK && tk_jobs_progress(&jobs) == 49);
    CHECK(!tk_jobs_tick(&jobs, 2000) && tk_jobs_tick(&jobs, 1000 + TK_JOB_IDLE_TIMEOUT_MS + 1));
    CHECK(data(42, 3, "lo\n", 3) == ERR_NO_JOB);
    /* safe mode */
    dev.safe_mode = true;
    pl[0] = 1;
    put16(pl + 1, 4096);
    CHECK(xfer(CMD_HELLO, pl, 3) == ERR_OK && get32(rx.payload + 11) == PROTO_CAP_EVENTS);
    CHECK(begin(50, one, fo, 1, true, 1, 0, 0) == ERR_SAFE_MODE);
    CHECK(xfer(CMD_GET_POLICY, NULL, 0) == ERR_OK && rx.len == POLICY_BLOB_LEN);
    dev.safe_mode = false;
    dev.jobs = NULL;
    CHECK(begin(51, one, fo, 1, true, 1, 0, 0) == ERR_UNKNOWN_CMD && err_detail() == ERR_DETAIL_NOT_IMPLEMENTED);
}

int main(void)
{
    test_xxh32();
    test_dupset();
    test_log_regex();
    test_engine();
    test_jobs();
    printf("test_engine: %d checks, %d failures\n", checks, fails);
    return fails ? 1 : 0;
}
