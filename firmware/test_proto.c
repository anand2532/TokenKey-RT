/* Host unit test for proto.c: CRC-16/CCITT-FALSE check value, the frame parser/dispatcher and
 * the v0.2 data model (JOB_BEGIN sessions/spans, JOB_END result, policy TLV blob).
 * Build+run: cmake -S . -B build-host && cmake --build build-host && ctest --test-dir build-host */
#include <stdio.h>
#include <string.h>

#include "proto.h"

static int fails;
#define CHECK(c)                                                    \
    do {                                                            \
        if (!(c)) {                                                 \
            printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #c);     \
            fails++;                                                \
        }                                                           \
    } while (0)

static proto_parser_t P;
static proto_frame_t last;

/* Feed a buffer, return the last non-NONE result (and copy that frame). */
static proto_parse_result_t feed(const uint8_t *b, size_t n, int *count)
{
    proto_parse_result_t last_r = PARSE_NONE;
    for (size_t i = 0; i < n; i++) {
        proto_parse_result_t r = proto_parser_feed(&P, b[i]);
        if (r != PARSE_NONE) {
            last_r = r;
            last = P.frame;
            if (count) {
                (*count)++;
            }
        }
    }
    return last_r;
}

/* field-wise compares (structs have padding, so no memcmp) */
static int pol_eq(const proto_policy_t *a, const proto_policy_t *b)
{
    return a->preset == b->preset && a->keep_pct == b->keep_pct && a->dedup == b->dedup &&
           a->newest_dedup == b->newest_dedup && a->rules == b->rules && a->ttl_s == b->ttl_s &&
           memcmp(a->type_weight, b->type_weight, sizeof a->type_weight) == 0;
}

static int res_eq(const proto_job_result_t *a, const proto_job_result_t *b)
{
    return a->job_id == b->job_id && a->est_tokens_in == b->est_tokens_in && a->est_tokens_out == b->est_tokens_out &&
           a->status == b->status && a->seg_count == b->seg_count && a->kept_bytes == b->kept_bytes &&
           a->dup_hits == b->dup_hits && a->set_full == b->set_full;
}

static proto_device_t dev(void)
{
    proto_device_t d = {.mode = MODE_BALANCED, .part = 0, .core_mhz = 600, .fw_version = 0x000100,
                        .serial = 0x1122334455667788ull, .build_id = "test", .flash_size = 8u << 20,
                        .uptime_ms = 1234, .caps = PROTO_CAP_EVENTS};
    return d;
}

int main(void)
{
    /* 1. CRC check value */
    CHECK(proto_crc16((const uint8_t *)"123456789", 9) == 0x29B1);
    CHECK(proto_crc16((const uint8_t *)"", 0) == 0xFFFF);

    /* 2. build -> parse round trip, split in odd chunks, with leading garbage */
    uint8_t f[PROTO_MAX_FRAME], o[PROTO_MAX_FRAME];
    uint8_t pl[3] = {1, 0x00, 0x10};
    size_t n = proto_build(f, sizeof f, CMD_HELLO, 7, pl, 3);
    CHECK(n == 11);
    CHECK(f[0] == 0xA5 && f[1] == 1 && f[2] == CMD_HELLO && f[3] == 7 && f[4] == 3 && f[5] == 0);
    proto_parser_init(&P);
    uint8_t junk[] = {0x00, 0x13, 0x37};
    int cnt = 0;
    CHECK(feed(junk, sizeof junk, &cnt) == PARSE_NONE && cnt == 0);
    CHECK(feed(f, 4, &cnt) == PARSE_NONE);
    CHECK(feed(f + 4, n - 4, &cnt) == PARSE_FRAME && cnt == 1);
    CHECK(last.cmd == CMD_HELLO && last.seq == 7 && last.len == 3 && memcmp(last.payload, pl, 3) == 0);

    /* 3. HELLO reply */
    proto_device_t d = dev();
    size_t rn = proto_handle(&d, PARSE_FRAME, &last, o, sizeof o);
    CHECK(rn == 16 + PROTO_OVERHEAD);
    CHECK(o[2] == (CMD_HELLO | 0x80) && o[3] == 7 && o[4] == 16);
    CHECK(o[6] == 1 && o[7] == 0x00 && o[8] == 0x01 && o[11] == 0); /* proto 1, fw 0.1.0, DVL6B */
    CHECK(o[12] == 0x58 && o[13] == 0x02);                           /* 600 MHz */
    CHECK(o[14] == 0x00 && o[15] == 0x10 && o[16] == 4);             /* 4096, window 4 */
    CHECK(o[17] == PROTO_CAP_EVENTS && o[21] == PROTO_VERSION_MINOR); /* caps, minor */
    /* reply itself must parse */
    proto_parser_init(&P);
    CHECK(feed(o, rn, NULL) == PARSE_FRAME && last.cmd == 0x81);

    /* 4. bad CRC -> ERROR BAD_CRC with seq, then resync on the next good frame */
    n = proto_build(f, sizeof f, CMD_PING, 9, (const uint8_t *)"hi", 2);
    f[n - 1] ^= 0x55;
    proto_parser_init(&P);
    CHECK(feed(f, n, NULL) == PARSE_ERR_CRC && last.seq == 9);
    rn = proto_handle(&d, PARSE_ERR_CRC, &last, o, sizeof o);
    CHECK(o[2] == CMD_ERROR && o[3] == 9 && o[6] == CMD_PING && o[7] == ERR_BAD_CRC);
    n = proto_build(f, sizeof f, CMD_PING, 10, (const uint8_t *)"hi", 2);
    CHECK(feed(f, n, NULL) == PARSE_FRAME && last.seq == 10);
    rn = proto_handle(&d, PARSE_FRAME, &last, o, sizeof o);
    CHECK(rn == 10 && o[2] == 0x82 && o[6] == 'h' && o[7] == 'i');

    /* 5. oversize len -> BAD_LEN */
    uint8_t big[] = {0xA5, 1, CMD_PING, 3, 0x01, 0x10}; /* len 4097 */
    proto_parser_init(&P);
    CHECK(feed(big, sizeof big, NULL) == PARSE_ERR_LEN && last.seq == 3);

    /* 6. SET_MODE / GET_MODE / bad mode / unknown / bad version / not-implemented */
    uint8_t m = MODE_QUALITY;
    n = proto_build(f, sizeof f, CMD_SET_MODE, 1, &m, 1);
    proto_parser_init(&P);
    feed(f, n, NULL);
    rn = proto_handle(&d, PARSE_FRAME, &last, o, sizeof o);
    CHECK(d.mode == MODE_QUALITY && d.mode_changed && o[2] == 0x90 && o[6] == MODE_QUALITY);
    n = proto_build(f, sizeof f, CMD_GET_MODE, 2, NULL, 0);
    feed(f, n, NULL);
    rn = proto_handle(&d, PARSE_FRAME, &last, o, sizeof o);
    CHECK(o[2] == 0x91 && o[6] == MODE_QUALITY && o[7] == 85);
    m = 7;
    n = proto_build(f, sizeof f, CMD_SET_MODE, 3, &m, 1);
    feed(f, n, NULL);
    proto_handle(&d, PARSE_FRAME, &last, o, sizeof o);
    CHECK(o[2] == CMD_ERROR && o[7] == ERR_BAD_PARAM);
    n = proto_build(f, sizeof f, 0x55, 8, NULL, 0);
    feed(f, n, NULL);
    proto_handle(&d, PARSE_FRAME, &last, o, sizeof o);
    /* doc example: A5 01 FF 08 0400 55 04 0000 crc */
    CHECK(o[2] == 0xFF && o[3] == 8 && o[4] == 4 && o[5] == 0 && o[6] == 0x55 && o[7] == ERR_UNKNOWN_CMD &&
          o[8] == 0 && o[9] == 0);
    n = proto_build(f, sizeof f, CMD_JOB_BEGIN, 4, NULL, 0);
    feed(f, n, NULL);
    proto_handle(&d, PARSE_FRAME, &last, o, sizeof o);
    CHECK(o[7] == ERR_UNKNOWN_CMD && o[8] == ERR_DETAIL_NOT_IMPLEMENTED);
    n = proto_build(f, sizeof f, CMD_PING, 5, NULL, 0);
    f[1] = 2; /* wrong major, fix CRC */
    uint16_t c = proto_crc16(&f[1], 5);
    f[6] = (uint8_t)c;
    f[7] = (uint8_t)(c >> 8);
    feed(f, n, NULL);
    proto_handle(&d, PARSE_FRAME, &last, o, sizeof o);
    CHECK(o[2] == CMD_ERROR && o[7] == ERR_BAD_VERSION && o[8] == 1);

    /* 7. GET_INFO TLVs */
    n = proto_build(f, sizeof f, CMD_GET_INFO, 6, NULL, 0);
    feed(f, n, NULL);
    rn = proto_handle(&d, PARSE_FRAME, &last, o, sizeof o);
    CHECK(o[2] == 0x83 && o[6] == TLV_SERIAL && o[7] == 8 && o[8] == 0x88 && o[16] == TLV_BUILD_ID && o[17] == 4);

    /* 8. max-size payload frame round trip */
    static uint8_t maxpl[PROTO_MAX_PAYLOAD];
    for (unsigned i = 0; i < sizeof maxpl; i++) {
        maxpl[i] = (uint8_t)(i * 7);
    }
    n = proto_build(f, sizeof f, CMD_JOB_DATA, 11, maxpl, PROTO_MAX_PAYLOAD);
    CHECK(n == PROTO_MAX_FRAME);
    proto_parser_init(&P);
    CHECK(feed(f, n, NULL) == PARSE_FRAME && last.len == PROTO_MAX_PAYLOAD && memcmp(last.payload, maxpl, 4096) == 0);

    /* 9. v0.2: JOB_BEGIN with session + protected spans (round trip) */
    proto_job_begin_t jb = {.job_id = 7, .total_len = 1000, .flags = 0 /* DELTA */, .token_budget = 0,
                            .session_id = 0xC0FFEE01u, .prefix_len = 5000, .prefix_xxh = 0x12345678u,
                            .span_count = 2,
                            .spans = {{0, 100, SPAN_TASK}, {900, 100, SPAN_LATEST_TOOL_OUTPUT}}};
    uint8_t jbuf[JOB_BEGIN_V02_LEN + PROTO_MAX_SPANS * JOB_SPAN_WIRE_LEN + 1];
    proto_job_begin_t jr;
    uint16_t det;
    size_t jn = proto_put_job_begin(jbuf, sizeof jbuf, &jb);
    CHECK(jn == 24 + 2 * 9);
    CHECK(proto_parse_job_begin(jbuf, (uint16_t)jn, &jr, &det) == ERR_OK && det == 0);
    CHECK(jr.v02 && jr.session_id == 0xC0FFEE01u && jr.prefix_len == 5000 && jr.prefix_xxh == 0x12345678u);
    CHECK(!(jr.flags & JOB_FLAG_FULL) && jr.span_count == 2 && jr.spans[1].offset == 900 &&
          jr.spans[1].len == 100 && jr.spans[1].kind == SPAN_LATEST_TOOL_OUTPUT);
    /* v0.1 payload (first 11 bytes) still accepted, FULL implied, no session */
    CHECK(proto_parse_job_begin(jbuf, JOB_BEGIN_V01_LEN, &jr, &det) == ERR_OK && !jr.v02 &&
          (jr.flags & JOB_FLAG_FULL) && jr.session_id == 0);
    CHECK(proto_parse_job_begin(jbuf, 15, &jr, &det) == ERR_BAD_PARAM && det == JB_DETAIL_SHORT);
    CHECK(proto_parse_job_begin(jbuf, (uint16_t)(jn - 1), &jr, &det) == ERR_BAD_PARAM &&
          det == JB_DETAIL_SPANS_TRUNCATED);
    /* overlapping / out-of-range / bad kind / zero-length spans */
    proto_job_begin_t bad = jb;
    bad.spans[1].offset = 50;
    jn = proto_put_job_begin(jbuf, sizeof jbuf, &bad);
    CHECK(proto_parse_job_begin(jbuf, (uint16_t)jn, &jr, &det) == ERR_BAD_PARAM && det == (JB_DETAIL_SPAN_BASE | 1));
    bad = jb;
    bad.spans[1].len = 101;
    jn = proto_put_job_begin(jbuf, sizeof jbuf, &bad);
    CHECK(proto_parse_job_begin(jbuf, (uint16_t)jn, &jr, &det) == ERR_BAD_PARAM && det == (JB_DETAIL_SPAN_BASE | 1));
    bad = jb;
    bad.spans[0].kind = SPAN_KIND_COUNT;
    jn = proto_put_job_begin(jbuf, sizeof jbuf, &bad);
    CHECK(proto_parse_job_begin(jbuf, (uint16_t)jn, &jr, &det) == ERR_BAD_PARAM && det == JB_DETAIL_SPAN_BASE);
    bad = jb;
    bad.spans[0].len = 0;
    jn = proto_put_job_begin(jbuf, sizeof jbuf, &bad);
    CHECK(proto_parse_job_begin(jbuf, (uint16_t)jn, &jr, &det) == ERR_BAD_PARAM && det == JB_DETAIL_SPAN_BASE);
    /* offset near UINT32_MAX must not wrap */
    bad = jb;
    bad.spans[1].offset = 0xFFFFFFF0u;
    bad.spans[1].len = 0x20;
    jn = proto_put_job_begin(jbuf, sizeof jbuf, &bad);
    CHECK(proto_parse_job_begin(jbuf, (uint16_t)jn, &jr, &det) == ERR_BAD_PARAM);
    /* DELTA without session, FULL with prefix, too many spans */
    bad = jb;
    bad.session_id = PROTO_SESSION_NONE;
    jn = proto_put_job_begin(jbuf, sizeof jbuf, &bad);
    CHECK(proto_parse_job_begin(jbuf, (uint16_t)jn, &jr, &det) == ERR_BAD_PARAM && det == JB_DETAIL_DELTA_NO_SESSION);
    bad = jb;
    bad.flags = JOB_FLAG_FULL;
    jn = proto_put_job_begin(jbuf, sizeof jbuf, &bad);
    CHECK(proto_parse_job_begin(jbuf, (uint16_t)jn, &jr, &det) == ERR_BAD_PARAM && det == JB_DETAIL_FULL_WITH_PREFIX);
    bad.prefix_len = 0;
    bad.prefix_xxh = 0;
    jn = proto_put_job_begin(jbuf, sizeof jbuf, &bad);
    CHECK(proto_parse_job_begin(jbuf, (uint16_t)jn, &jr, &det) == ERR_OK && (jr.flags & JOB_FLAG_FULL));
    jbuf[23] = PROTO_MAX_SPANS + 1;
    CHECK(proto_parse_job_begin(jbuf, sizeof jbuf, &jr, &det) == ERR_CTX_OVERFLOW);

    /* 9b. SYSTEM_PROMPT (kind 3) parses in FULL, rejected in DELTA; kinds > 3 rejected */
    proto_job_begin_t full = {.job_id = 1, .total_len = 1000, .flags = JOB_FLAG_FULL, .session_id = 0xAB,
                              .span_count = 3,
                              .spans = {{0, 200, SPAN_SYSTEM_PROMPT}, {200, 50, SPAN_TASK},
                                        {900, 100, SPAN_LATEST_TOOL_OUTPUT}}};
    jn = proto_put_job_begin(jbuf, sizeof jbuf, &full);
    CHECK(SPAN_SYSTEM_PROMPT == 3 && SPAN_ERROR == 4 && SPAN_KIND_COUNT == 5);
    CHECK(proto_parse_job_begin(jbuf, (uint16_t)jn, &jr, &det) == ERR_OK && jr.spans[0].kind == SPAN_SYSTEM_PROMPT);
    bad = jb; /* DELTA */
    bad.spans[0].kind = SPAN_SYSTEM_PROMPT;
    jn = proto_put_job_begin(jbuf, sizeof jbuf, &bad);
    CHECK(proto_parse_job_begin(jbuf, (uint16_t)jn, &jr, &det) == ERR_BAD_PARAM && det == (JB_DETAIL_SYSPROMPT_DELTA | 0));
    for (unsigned k = SPAN_KIND_COUNT; k < 256; k += 25) {
        bad = full;
        bad.spans[1].kind = (uint8_t)k;
        jn = proto_put_job_begin(jbuf, sizeof jbuf, &bad);
        CHECK(proto_parse_job_begin(jbuf, (uint16_t)jn, &jr, &det) == ERR_BAD_PARAM && det == (JB_DETAIL_SPAN_BASE | 1));
    }
    bad = full;
    bad.spans[1].kind = 255;
    jn = proto_put_job_begin(jbuf, sizeof jbuf, &bad);
    CHECK(proto_parse_job_begin(jbuf, (uint16_t)jn, &jr, &det) == ERR_BAD_PARAM);

    /* 9c. session: SYSTEM_PROMPT from FULL persists across DELTA jobs */
    static proto_session_t S;
    proto_session_init(&S);
    CHECK(proto_session_begin_job(&S, &full, &det) == ERR_OK && S.session_id == 0xAB && S.span_count == 2);
    CHECK(proto_session_protected_kind(&S, 950, 10) == SPAN_LATEST_TOOL_OUTPUT); /* job-only, active now */
    proto_session_commit_job(&S, 1000, 0x1111u, 600, 0x2222u);
    CHECK(S.in_len == 1000 && proto_session_protected_kind(&S, 950, 10) == -1); /* ended with its job */
    CHECK(proto_session_protected_kind(&S, 0, 1) == SPAN_SYSTEM_PROMPT);
    proto_job_begin_t delta = {.job_id = 2, .total_len = 300, .flags = 0, .session_id = 0xAB, .prefix_len = 1000,
                               .prefix_xxh = 0x1111u, .span_count = 1, .spans = {{10, 20, SPAN_TASK}}};
    CHECK(proto_session_begin_job(&S, &delta, &det) == ERR_OK && S.span_count == 3);
    CHECK(proto_session_protected_kind(&S, 199, 1) == SPAN_SYSTEM_PROMPT); /* not re-sent, still protected */
    CHECK(proto_session_protected_kind(&S, 1015, 1) == SPAN_TASK && S.spans[2].offset == 1010);
    CHECK(proto_session_protected_kind(&S, 300, 600) == -1);
    proto_session_commit_job(&S, 300, 0x3333u, 700, 0x4444u);
    CHECK(S.in_len == 1300);
    /* second DELTA, no spans: SYSTEM_PROMPT still there */
    delta.job_id = 3; delta.total_len = 50; delta.prefix_len = 1300; delta.prefix_xxh = 0x3333u; delta.span_count = 0;
    CHECK(proto_session_begin_job(&S, &delta, &det) == ERR_OK && proto_session_protected_kind(&S, 100, 10) == SPAN_SYSTEM_PROMPT);
    proto_session_commit_job(&S, 50, 0x5555u, 720, 0x6666u);
    /* SESSION_MISMATCH leaves state untouched */
    proto_session_t before = S;
    delta.job_id = 4; delta.prefix_len = 1350; delta.prefix_xxh = 0xBADu;
    CHECK(proto_session_begin_job(&S, &delta, &det) == ERR_SESSION_MISMATCH && det == SESS_MM_PREFIX_XXH);
    CHECK(S.span_count == before.span_count && S.in_len == before.in_len && S.in_xxh == before.in_xxh &&
          proto_session_protected_kind(&S, 0, 1) == SPAN_SYSTEM_PROMPT);
    delta.prefix_len = 1349;
    CHECK(proto_session_begin_job(&S, &delta, &det) == ERR_SESSION_MISMATCH && det == SESS_MM_PREFIX_LEN);
    delta.session_id = 0xAC;
    CHECK(proto_session_begin_job(&S, &delta, &det) == ERR_SESSION_MISMATCH && det == SESS_MM_UNKNOWN);
    /* SYSTEM_PROMPT in a DELTA is refused by the session helper too */
    delta.session_id = 0xAB; delta.prefix_len = 1350; delta.prefix_xxh = 0x5555u; delta.span_count = 1;
    delta.spans[0] = (proto_span_t){0, 10, SPAN_SYSTEM_PROMPT};
    CHECK(proto_session_begin_job(&S, &delta, &det) == ERR_BAD_PARAM && det == JB_DETAIL_SYSPROMPT_DELTA);
    /* FULL reset drops the old SYSTEM_PROMPT; a FULL without one leaves nothing protected */
    proto_job_begin_t full2 = {.job_id = 5, .total_len = 400, .flags = JOB_FLAG_FULL, .session_id = 0xAB};
    CHECK(proto_session_begin_job(&S, &full2, &det) == ERR_OK && S.span_count == 0 && S.in_len == 0 &&
          proto_session_protected_kind(&S, 0, 400) == -1);
    /* stateless FULL: spans protect the job only, nothing recorded */
    proto_job_begin_t sl = full;
    sl.session_id = PROTO_SESSION_NONE;
    CHECK(proto_session_begin_job(&S, &sl, &det) == ERR_OK && S.span_count == 0 &&
          proto_session_protected_kind(&S, 0, 1) == SPAN_SYSTEM_PROMPT);
    proto_session_commit_job(&S, 1000, 0, 0, 0);
    CHECK(proto_session_protected_kind(&S, 0, 1) == -1);
    /* span table overflow -> CTX_OVERFLOW, state unchanged */
    proto_session_init(&S);
    proto_job_begin_t many = {.job_id = 6, .total_len = 4000, .flags = JOB_FLAG_FULL, .session_id = 7,
                              .span_count = PROTO_MAX_SPANS};
    for (unsigned i = 0; i < PROTO_MAX_SPANS; i++) {
        many.spans[i] = (proto_span_t){i * 10u, 5, SPAN_OTHER};
    }
    CHECK(proto_session_begin_job(&S, &many, &det) == ERR_OK);
    proto_session_commit_job(&S, 4000, 9, 0, 0);
    many.flags = 0; many.prefix_len = 4000; many.prefix_xxh = 9; many.job_id = 7;
    CHECK(proto_session_begin_job(&S, &many, &det) == ERR_OK && S.span_count == 32);
    proto_session_commit_job(&S, 4000, 10, 0, 0);
    many.prefix_len = 8000; many.prefix_xxh = 10; many.span_count = 1;
    CHECK(proto_session_begin_job(&S, &many, &det) == ERR_CTX_OVERFLOW && S.span_count == 32 && S.in_len == 8000);

    /* 10. v1.0: JOB_END result (keep/drop list summary) */
    proto_job_result_t res = {.job_id = 7, .status = JOB_STATUS_DONE, .seg_count = 348, .est_tokens_in = 2500,
                              .est_tokens_out = 1200, .kept_bytes = 4800, .dup_hits = 12, .set_full = 1};
    proto_job_result_t rr;
    uint8_t rbuf[JOB_END_V10_LEN];
    CHECK(proto_put_job_result(rbuf, sizeof rbuf, &res) == JOB_END_V10_LEN);
    CHECK(proto_parse_job_result(rbuf, JOB_END_V10_LEN, &rr) == ERR_OK && res_eq(&rr, &res));
    CHECK(proto_parse_job_result(rbuf, JOB_END_V01_LEN, &rr) == ERR_OK && rr.job_id == 7 && rr.seg_count == 0);
    CHECK(proto_parse_job_result(rbuf, 5, &rr) == ERR_BAD_LEN);

    /* 11. v1.0: policy presets, TLV parse/serialize, validation */
    proto_policy_t pb, pq, pp, ps, pg;
    proto_policy_preset(MODE_BALANCED, &pb);
    proto_policy_preset(MODE_QUALITY, &pq);
    proto_policy_preset(MODE_DEFAULT, &ps);
    proto_policy_preset(MODE_DEDUP_ONLY, &pg);
    CHECK(pb.keep_pct == 50 && pb.dedup && !pb.newest_dedup && pb.rules == POLICY_RULES_SESSION && pb.ttl_s == 300 &&
          pq.keep_pct == 85);
    CHECK(ps.preset == MODE_S_PROTECT && ps.keep_pct == 100 && !ps.newest_dedup && ps.ttl_s == 300);
    CHECK(pg.keep_pct == 100 && pg.newest_dedup && pg.ttl_s == POLICY_TTL_NEVER);
    CHECK(ps.type_weight[SEG_DIFF] == 400 && ps.type_weight[SEG_CODE] == 300 && ps.type_weight[SEG_LOG] == 200 &&
          ps.type_weight[SEG_PROSE] == 100);
    uint8_t blob[POLICY_BLOB_MAX];
    size_t bn = proto_policy_serialize(&pb, blob, sizeof blob);
    CHECK(bn == POLICY_BLOB_LEN && blob[0] == POLICY_VERSION && blob[1] == MODE_BALANCED);
    CHECK(proto_policy_parse(blob, (uint16_t)bn, &pq, &pp, &det) == ERR_OK && pol_eq(&pp, &pb));
    /* preset only = SET_MODE equivalent */
    uint8_t only_q[] = {POLICY_VERSION, MODE_QUALITY};
    CHECK(proto_policy_parse(only_q, 2, &pb, &pp, &det) == ERR_OK && pp.preset == MODE_QUALITY && pp.keep_pct == 85);
    /* custom on top of current: D as written (rules v0.1, keep 25), dedup off, CODE weight 350, TTL 3600, unknown optional TLV */
    uint8_t cust[] = {POLICY_VERSION, POLICY_PRESET_CUSTOM, POL_TLV_KEEP_PCT, 1, 25, POL_TLV_DEDUP, 1, 0,
                      POL_TLV_RULES, 1, POLICY_RULES_V01, POL_TLV_TTL_S, 4, 0x10, 0x0E, 0, 0,
                      POL_TLV_TYPE_WEIGHT, 3, SEG_CODE, 0x5E, 0x01, POL_TLV_NEWEST_DEDUP, 1, 1, 0x81, 3, 1, 2, 3};
    CHECK(proto_policy_parse(cust, sizeof cust, &pb, &pp, &det) == ERR_OK && pp.preset == POLICY_PRESET_CUSTOM &&
          pp.keep_pct == 25 && !pp.dedup && pp.rules == POLICY_RULES_V01 && pp.ttl_s == 3600 && pp.newest_dedup &&
          pp.type_weight[SEG_CODE] == 350 && pp.type_weight[SEG_PROSE] == pb.type_weight[SEG_PROSE]);
    bn = proto_policy_serialize(&pp, blob, sizeof blob);
    CHECK(blob[1] == POLICY_PRESET_CUSTOM);
    proto_policy_t pp2;
    CHECK(proto_policy_parse(blob, (uint16_t)bn, &pq, &pp2, &det) == ERR_OK && pol_eq(&pp2, &pp));
    uint8_t badv[] = {2, 0};
    CHECK(proto_policy_parse(badv, 2, &pb, &pp, &det) == ERR_POLICY_INVALID && det == POL_DETAIL_VERSION);
    uint8_t badp[] = {POLICY_VERSION, MODE_COUNT};
    CHECK(proto_policy_parse(badp, 2, &pb, &pp, &det) == ERR_POLICY_INVALID && det == POL_DETAIL_PRESET);
    uint8_t badb[] = {POLICY_VERSION, 0, POL_TLV_KEEP_PCT, 1, 101};
    CHECK(proto_policy_parse(badb, sizeof badb, &pb, &pp, &det) == ERR_POLICY_INVALID &&
          det == (POL_DETAIL_BAD_VALUE | POL_TLV_KEEP_PCT));
    uint8_t badl[] = {POLICY_VERSION, 0, POL_TLV_DEDUP, 2, 1, 1};
    CHECK(proto_policy_parse(badl, sizeof badl, &pb, &pp, &det) == ERR_POLICY_INVALID &&
          det == (POL_DETAIL_BAD_LEN | POL_TLV_DEDUP));
    uint8_t badt[] = {POLICY_VERSION, 0, POL_TLV_TTL_S, 4, 0};
    CHECK(proto_policy_parse(badt, sizeof badt, &pb, &pp, &det) == ERR_POLICY_INVALID && det == POL_DETAIL_TRUNCATED);
    uint8_t badu[] = {POLICY_VERSION, 0, 0x03, 4, 0, 0, 0, 0}; /* withdrawn v0.2 CACHE_STABLE_PREFIX */
    CHECK(proto_policy_parse(badu, sizeof badu, &pb, &pp, &det) == ERR_POLICY_INVALID && det == (POL_DETAIL_UNKNOWN | 3));
    uint8_t badw[] = {POLICY_VERSION, 0, POL_TLV_TYPE_WEIGHT, 3, SEG_TYPE_COUNT, 10, 0};
    CHECK(proto_policy_parse(badw, sizeof badw, &pb, &pp, &det) == ERR_POLICY_INVALID &&
          det == (POL_DETAIL_BAD_VALUE | POL_TLV_TYPE_WEIGHT));
    uint8_t badr[] = {POLICY_VERSION, 0, POL_TLV_RULES, 1, 2};
    CHECK(proto_policy_parse(badr, sizeof badr, &pb, &pp, &det) == ERR_POLICY_INVALID &&
          det == (POL_DETAIL_BAD_VALUE | POL_TLV_RULES));

    /* 11b. v1.0 message table in JOB_BEGIN */
    static proto_job_begin_t mj, mj2;
    memset(&mj, 0, sizeof mj);
    mj.job_id = 3; mj.total_len = 30; mj.flags = JOB_FLAG_FULL | JOB_FLAG_MESSAGES; mj.session_id = 5; mj.v02 = true;
    mj.has_msgs = true; mj.msg_count = 3;
    mj.msgs[0].len = 10; mj.msgs[0].role = ROLE_SYSTEM; mj.msgs[0].flags = 1;
    mj.msgs[1].len = 15; mj.msgs[1].role = ROLE_USER; mj.msgs[1].flags = 1;
    mj.msgs[2].len = 5; mj.msgs[2].role = ROLE_TOOL; mj.msgs[2].flags = 3;
    uint8_t mb[256];
    size_t ml = proto_put_job_begin(mb, sizeof mb, &mj);
    CHECK(ml == JOB_BEGIN_V02_LEN + 2 + 3 * JOB_MSG_WIRE_LEN);
    CHECK(proto_parse_job_begin(mb, (uint16_t)ml, &mj2, &det) == ERR_OK && mj2.has_msgs && mj2.msg_count == 3 &&
          mj2.msgs[1].len == 15 && mj2.msgs[2].flags == 3 && mj2.msgs[0].role == ROLE_SYSTEM);
    CHECK(proto_parse_job_begin(mb, (uint16_t)(ml - 1), &mj2, &det) == ERR_BAD_PARAM && det == JB_DETAIL_MSGS_TRUNCATED);
    mj.msgs[2].len = 6;
    ml = proto_put_job_begin(mb, sizeof mb, &mj);
    CHECK(proto_parse_job_begin(mb, (uint16_t)ml, &mj2, &det) == ERR_BAD_PARAM && det == JB_DETAIL_MSG_SUM);

    /* 12. without a job layer (dev.jobs == NULL) the v0.2 commands answer "not implemented" */
    n = proto_build(f, sizeof f, CMD_SET_POLICY, 12, only_q, 2);
    proto_parser_init(&P);
    feed(f, n, NULL);
    proto_handle(&d, PARSE_FRAME, &last, o, sizeof o);
    CHECK(o[2] == CMD_ERROR && o[6] == CMD_SET_POLICY && o[7] == ERR_UNKNOWN_CMD && o[8] == ERR_DETAIL_NOT_IMPLEMENTED);
    n = proto_build(f, sizeof f, CMD_GET_POLICY, 13, NULL, 0);
    feed(f, n, NULL);
    proto_handle(&d, PARSE_FRAME, &last, o, sizeof o);
    CHECK(o[2] == CMD_ERROR && o[6] == CMD_GET_POLICY && o[8] == ERR_DETAIL_NOT_IMPLEMENTED);
    CHECK(ERR_SESSION_MISMATCH == 0x0D && ERR_POLICY_INVALID == 0x0E && PROTO_CAP_SESSIONS == 0x8);

    if (fails) {
        printf("%d check(s) FAILED\n", fails);
        return 1;
    }
    printf("test_proto: all checks passed (CRC check 0x%04X)\n", proto_crc16((const uint8_t *)"123456789", 9));
    return 0;
}
