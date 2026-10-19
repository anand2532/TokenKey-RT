/* TokenKey RT - USB frame protocol: CRC, builder, streaming parser, dispatcher. */
#include "proto.h"

#include <string.h>

/* ---- CRC-16/CCITT-FALSE, table-driven (check "123456789" -> 0x29B1) ------------------- */
static uint16_t s_crc_tab[256];
static bool s_crc_ready;

static void crc_table_init(void)
{
    for (uint32_t i = 0; i < 256; i++) {
        uint16_t c = (uint16_t)(i << 8);
        for (int b = 0; b < 8; b++) {
            c = (uint16_t)((c & 0x8000u) ? ((uint32_t)c << 1) ^ 0x1021u : ((uint32_t)c << 1));
        }
        s_crc_tab[i] = c;
    }
    s_crc_ready = true;
}

uint16_t proto_crc16_update(uint16_t crc, const uint8_t *d, size_t n)
{
    if (!s_crc_ready) {
        crc_table_init();
    }
    while (n--) {
        crc = (uint16_t)((crc << 8) ^ s_crc_tab[((crc >> 8) ^ *d++) & 0xFFu]);
    }
    return crc;
}

uint16_t proto_crc16(const uint8_t *d, size_t n) { return proto_crc16_update(0xFFFFu, d, n); }

uint8_t proto_mode_budget_pct(tk_mode_t m)
{
    static const uint8_t pct[MODE_COUNT] = {25, 50, 85};
    return (m < MODE_COUNT) ? pct[m] : 0;
}

const char *proto_mode_name(tk_mode_t m)
{
    static const char *const n[MODE_COUNT] = {"Economy", "Balanced", "Quality"};
    return (m < MODE_COUNT) ? n[m] : "?";
}

static void put16(uint8_t *p, uint16_t v) { p[0] = (uint8_t)v; p[1] = (uint8_t)(v >> 8); }
static void put32(uint8_t *p, uint32_t v) { put16(p, (uint16_t)v); put16(p + 2, (uint16_t)(v >> 16)); }
static uint16_t get16(const uint8_t *p) { return (uint16_t)(p[0] | (p[1] << 8)); }
static uint32_t get32(const uint8_t *p) { return (uint32_t)get16(p) | ((uint32_t)get16(p + 2) << 16); }

size_t proto_build(uint8_t *out, size_t cap, uint8_t cmd, uint8_t seq, const uint8_t *payload, uint16_t len)
{
    if (len > PROTO_MAX_PAYLOAD || cap < (size_t)len + PROTO_OVERHEAD) {
        return 0;
    }
    out[0] = PROTO_SOF;
    out[1] = PROTO_VERSION;
    out[2] = cmd;
    out[3] = seq;
    put16(&out[4], len);
    if (len && payload != &out[6]) {
        memmove(&out[6], payload, len);
    }
    put16(&out[6 + len], proto_crc16(&out[1], 5u + len));
    return (size_t)len + PROTO_OVERHEAD;
}

size_t proto_build_error(uint8_t *out, size_t cap, uint8_t seq, uint8_t orig_cmd, uint8_t code, uint16_t detail)
{
    uint8_t p[4] = {orig_cmd, code, (uint8_t)detail, (uint8_t)(detail >> 8)};
    return proto_build(out, cap, CMD_ERROR, seq, p, sizeof p);
}

/* ---- parser ---------------------------------------------------------------------------- */
enum { ST_SOF, ST_HDR, ST_PAYLOAD, ST_CRC0, ST_CRC1 };

void proto_parser_init(proto_parser_t *p)
{
    p->state = ST_SOF;
    p->pos = 0;
}

proto_parse_result_t proto_parser_feed(proto_parser_t *p, uint8_t b)
{
    switch (p->state) {
    case ST_SOF:
        if (b == PROTO_SOF) {
            p->state = ST_HDR;
            p->pos = 0;
        }
        return PARSE_NONE;
    case ST_HDR:
        p->hdr[p->pos++] = b;
        if (p->pos < 5) {
            return PARSE_NONE;
        }
        p->frame.ver = p->hdr[0];
        p->frame.cmd = p->hdr[1];
        p->frame.seq = p->hdr[2];
        p->frame.len = (uint16_t)(p->hdr[3] | (p->hdr[4] << 8));
        p->pos = 0;
        if (p->frame.len > PROTO_MAX_PAYLOAD) {
            p->state = ST_SOF;
            return PARSE_ERR_LEN;
        }
        p->state = p->frame.len ? ST_PAYLOAD : ST_CRC0;
        return PARSE_NONE;
    case ST_PAYLOAD:
        p->frame.payload[p->pos++] = b;
        if (p->pos == p->frame.len) {
            p->state = ST_CRC0;
        }
        return PARSE_NONE;
    case ST_CRC0:
        p->crc_rx = b;
        p->state = ST_CRC1;
        return PARSE_NONE;
    case ST_CRC1: {
        p->crc_rx |= (uint16_t)(b << 8);
        p->state = ST_SOF;
        uint16_t c = proto_crc16_update(0xFFFFu, p->hdr, 5);
        c = proto_crc16_update(c, p->frame.payload, p->frame.len);
        return (c == p->crc_rx) ? PARSE_FRAME : PARSE_ERR_CRC;
    }
    default:
        p->state = ST_SOF;
        return PARSE_NONE;
    }
}

/* ---- dispatcher ------------------------------------------------------------------------ */
static size_t reply(uint8_t *out, size_t cap, const proto_frame_t *f, const uint8_t *pl, uint16_t len)
{
    return proto_build(out, cap, (uint8_t)(f->cmd | PROTO_RESP_BIT), f->seq, pl, len);
}

static size_t tlv(uint8_t *p, uint8_t type, const void *v, uint8_t len)
{
    p[0] = type;
    p[1] = len;
    memcpy(&p[2], v, len);
    return 2u + len;
}

size_t proto_handle(proto_device_t *dev, proto_parse_result_t r, const proto_frame_t *f, uint8_t *out, size_t cap)
{
    switch (r) {
    case PARSE_NONE:
        return 0;
    case PARSE_ERR_CRC:
        return proto_build_error(out, cap, f->seq, f->cmd, ERR_BAD_CRC, 0);
    case PARSE_ERR_LEN:
        return proto_build_error(out, cap, f->seq, f->cmd, ERR_BAD_LEN, PROTO_MAX_PAYLOAD);
    case PARSE_FRAME:
        break;
    }

    if (f->ver != PROTO_VERSION) {
        return proto_build_error(out, cap, f->seq, f->cmd, ERR_BAD_VERSION, PROTO_VERSION);
    }

    uint8_t pl[64];
    switch (f->cmd) {
    case CMD_HELLO: {
        /* req: host_ver u8, host_max_payload u16. resp: proto_ver u8, fw_ver u32, part u8,
         * core_mhz u16, max_payload u16, window u8, caps u32 (= 15 bytes, v0.1) + proto_minor u8
         * (v0.2) = 16 bytes. */
        if (f->len < 3) {
            return proto_build_error(out, cap, f->seq, f->cmd, ERR_BAD_PARAM, 0);
        }
        pl[0] = PROTO_VERSION;
        put32(&pl[1], dev->fw_version);
        pl[5] = dev->part;
        put16(&pl[6], dev->core_mhz);
        put16(&pl[8], PROTO_MAX_PAYLOAD);
        pl[10] = PROTO_WINDOW;
        put32(&pl[11], dev->caps);
        pl[15] = PROTO_VERSION_MINOR;
        return reply(out, cap, f, pl, 16);
    }
    case CMD_PING:
        if (f->len > 64) {
            return proto_build_error(out, cap, f->seq, f->cmd, ERR_BAD_LEN, 64);
        }
        return reply(out, cap, f, f->payload, f->len);
    case CMD_GET_INFO: {
        size_t n = 0;
        uint8_t ser[8];
        uint32_t fs = dev->flash_size, up = dev->uptime_ms;
        uint8_t fsb[4], upb[4];
        for (int i = 0; i < 8; i++) {
            ser[i] = (uint8_t)(dev->serial >> (8 * i));
        }
        put32(fsb, fs);
        put32(upb, up);
        size_t bl = dev->build_id ? strlen(dev->build_id) : 0;
        if (bl > 32) {
            bl = 32;
        }
        n += tlv(&pl[n], TLV_SERIAL, ser, 8);
        n += tlv(&pl[n], TLV_BUILD_ID, dev->build_id, (uint8_t)bl);
        n += tlv(&pl[n], TLV_FLASH_SIZE, fsb, 4);
        n += tlv(&pl[n], TLV_UPTIME_MS, upb, 4);
        return reply(out, cap, f, pl, (uint16_t)n);
    }
    case CMD_SET_MODE:
        if (f->len < 1 || f->payload[0] >= MODE_COUNT) {
            return proto_build_error(out, cap, f->seq, f->cmd, ERR_BAD_PARAM, f->len ? f->payload[0] : 0);
        }
        if (dev->mode != (tk_mode_t)f->payload[0]) {
            dev->mode = (tk_mode_t)f->payload[0];
            dev->mode_changed = true;
        }
        pl[0] = (uint8_t)dev->mode;
        return reply(out, cap, f, pl, 1);
    case CMD_GET_MODE:
        pl[0] = (uint8_t)dev->mode;
        pl[1] = proto_mode_budget_pct(dev->mode);
        return reply(out, cap, f, pl, 2);
    case CMD_JOB_BEGIN:
    case CMD_JOB_DATA:
    case CMD_JOB_END:
    case CMD_RESULT_READ:
    case CMD_JOB_ABORT:
    case CMD_GET_STATS:
    case CMD_RESET_STATS:
    case CMD_ENTER_BOOTLOADER:
    case CMD_SET_POLICY:
    case CMD_GET_POLICY:
        /* Specified (v0.2 data model included) but not part of the skeleton. */
        return proto_build_error(out, cap, f->seq, f->cmd, ERR_UNKNOWN_CMD, ERR_DETAIL_NOT_IMPLEMENTED);
    default:
        return proto_build_error(out, cap, f->seq, f->cmd, ERR_UNKNOWN_CMD, 0);
    }
}

/* ---- v0.2: JOB_BEGIN -------------------------------------------------------------------- */
uint8_t proto_parse_job_begin(const uint8_t *p, uint16_t len, proto_job_begin_t *jb, uint16_t *detail)
{
    *detail = 0;
    memset(jb, 0, sizeof *jb);
    if (len < JOB_BEGIN_V01_LEN || (len > JOB_BEGIN_V01_LEN && len < JOB_BEGIN_V02_LEN)) {
        *detail = JB_DETAIL_SHORT;
        return ERR_BAD_PARAM;
    }
    jb->job_id = get16(&p[0]);
    jb->total_len = get32(&p[2]);
    jb->flags = p[6];
    jb->token_budget = get32(&p[7]);
    if (len == JOB_BEGIN_V01_LEN) { /* v0.1 host: stateless, FULL implied */
        jb->flags |= JOB_FLAG_FULL;
        return ERR_OK;
    }
    jb->v02 = true;
    jb->session_id = get32(&p[11]);
    jb->prefix_len = get32(&p[15]);
    jb->prefix_xxh = get32(&p[19]);
    uint8_t n = p[23];
    if (n > PROTO_MAX_SPANS) {
        *detail = PROTO_MAX_SPANS;
        return ERR_CTX_OVERFLOW;
    }
    if ((uint32_t)len < JOB_BEGIN_V02_LEN + (uint32_t)n * JOB_SPAN_WIRE_LEN) {
        *detail = JB_DETAIL_SPANS_TRUNCATED;
        return ERR_BAD_PARAM;
    }
    if (jb->session_id == PROTO_SESSION_NONE) {
        if (!(jb->flags & JOB_FLAG_FULL)) {
            *detail = JB_DETAIL_DELTA_NO_SESSION;
            return ERR_BAD_PARAM;
        }
    }
    if ((jb->flags & JOB_FLAG_FULL) && (jb->prefix_len || jb->prefix_xxh)) {
        *detail = JB_DETAIL_FULL_WITH_PREFIX;
        return ERR_BAD_PARAM;
    }
    uint32_t end_prev = 0;
    for (uint8_t i = 0; i < n; i++) {
        const uint8_t *q = &p[JOB_BEGIN_V02_LEN + (uint32_t)i * JOB_SPAN_WIRE_LEN];
        proto_span_t sp = {.offset = get32(&q[0]), .len = get32(&q[4]), .kind = q[8]};
        /* non-empty, inside total_len (overflow-safe), sorted, non-overlapping, known kind */
        if (sp.len == 0 || sp.offset > jb->total_len || sp.len > jb->total_len - sp.offset ||
            sp.offset < end_prev || sp.kind >= SPAN_KIND_COUNT) {
            *detail = (uint16_t)(JB_DETAIL_SPAN_BASE | i);
            return ERR_BAD_PARAM;
        }
        end_prev = sp.offset + sp.len;
        jb->spans[i] = sp;
    }
    jb->span_count = n;
    return ERR_OK;
}

size_t proto_put_job_begin(uint8_t *out, size_t cap, const proto_job_begin_t *jb)
{
    if (jb->span_count > PROTO_MAX_SPANS) {
        return 0;
    }
    size_t n = JOB_BEGIN_V02_LEN + (size_t)jb->span_count * JOB_SPAN_WIRE_LEN;
    if (cap < n) {
        return 0;
    }
    put16(&out[0], jb->job_id);
    put32(&out[2], jb->total_len);
    out[6] = jb->flags;
    put32(&out[7], jb->token_budget);
    put32(&out[11], jb->session_id);
    put32(&out[15], jb->prefix_len);
    put32(&out[19], jb->prefix_xxh);
    out[23] = jb->span_count;
    for (uint8_t i = 0; i < jb->span_count; i++) {
        uint8_t *q = &out[JOB_BEGIN_V02_LEN + (size_t)i * JOB_SPAN_WIRE_LEN];
        put32(&q[0], jb->spans[i].offset);
        put32(&q[4], jb->spans[i].len);
        q[8] = jb->spans[i].kind;
    }
    return n;
}

/* ---- v0.2: JOB_END result ---------------------------------------------------------------- */
size_t proto_put_job_result(uint8_t *out, size_t cap, const proto_job_result_t *r)
{
    if (cap < JOB_END_V02_LEN) {
        return 0;
    }
    put16(&out[0], r->job_id);
    put32(&out[2], r->est_tokens_in);
    put32(&out[6], r->est_tokens_out);
    put32(&out[10], r->out_len);
    put32(&out[14], r->cache_stable_len);
    put32(&out[18], r->cache_stable_xxh);
    put32(&out[22], r->protected_bytes);
    return JOB_END_V02_LEN;
}

uint8_t proto_parse_job_result(const uint8_t *p, uint16_t len, proto_job_result_t *r)
{
    memset(r, 0, sizeof *r);
    if (len < JOB_END_V01_LEN) {
        return ERR_BAD_LEN;
    }
    r->job_id = get16(&p[0]);
    r->est_tokens_in = get32(&p[2]);
    if (len < JOB_END_V02_LEN) { /* v0.1 device: no cache-stable report */
        return ERR_OK;
    }
    r->est_tokens_out = get32(&p[6]);
    r->out_len = get32(&p[10]);
    r->cache_stable_len = get32(&p[14]);
    r->cache_stable_xxh = get32(&p[18]);
    r->protected_bytes = get32(&p[22]);
    return ERR_OK;
}

/* ---- v0.2: policy ------------------------------------------------------------------------- */
void proto_policy_preset(tk_mode_t m, proto_policy_t *pol)
{
    /* keep-priority weights per segment type: TEXT, CODE, TOOL_OUTPUT, LOG */
    static const uint8_t w[MODE_COUNT][SEG_TYPE_COUNT] = {
        {40, 70, 30, 10}, /* Economy  */
        {60, 85, 50, 25}, /* Balanced */
        {85, 100, 75, 50}, /* Quality  */
    };
    if (m >= MODE_COUNT) {
        m = MODE_BALANCED;
    }
    pol->preset = (uint8_t)m;
    pol->budget_pct = proto_mode_budget_pct(m);
    pol->dedup = true;
    pol->cache_stable_prefix = POLICY_CACHE_PREFIX_ALL;
    memcpy(pol->type_weight, w[m], SEG_TYPE_COUNT);
}

static uint8_t policy_match_preset(const proto_policy_t *pol)
{
    for (int m = 0; m < MODE_COUNT; m++) {
        proto_policy_t ref;
        proto_policy_preset((tk_mode_t)m, &ref);
        if (ref.budget_pct == pol->budget_pct && ref.dedup == pol->dedup &&
            ref.cache_stable_prefix == pol->cache_stable_prefix &&
            memcmp(ref.type_weight, pol->type_weight, SEG_TYPE_COUNT) == 0) {
            return (uint8_t)m;
        }
    }
    return POLICY_PRESET_CUSTOM;
}

uint8_t proto_policy_parse(const uint8_t *p, uint16_t len, const proto_policy_t *cur, proto_policy_t *out,
                           uint16_t *detail)
{
    proto_policy_t pol;
    *detail = 0;
    if (len < 2) {
        *detail = POL_DETAIL_TRUNCATED;
        return ERR_POLICY_INVALID;
    }
    if (p[0] != POLICY_VERSION) {
        *detail = POL_DETAIL_VERSION;
        return ERR_POLICY_INVALID;
    }
    if (p[1] < MODE_COUNT) {
        proto_policy_preset((tk_mode_t)p[1], &pol);
    } else if (p[1] == POLICY_PRESET_CUSTOM) {
        pol = *cur;
    } else {
        *detail = POL_DETAIL_PRESET;
        return ERR_POLICY_INVALID;
    }
    uint16_t i = 2;
    while (i < len) {
        if (len - i < 2 || len - i - 2 < p[i + 1]) {
            *detail = POL_DETAIL_TRUNCATED;
            return ERR_POLICY_INVALID;
        }
        uint8_t t = p[i], l = p[i + 1];
        const uint8_t *v = &p[i + 2];
        switch (t) {
        case POL_TLV_BUDGET_PCT:
            if (l != 1) { *detail = (uint16_t)(POL_DETAIL_BAD_LEN | t); return ERR_POLICY_INVALID; }
            if (v[0] == 0 || v[0] > 100) { *detail = (uint16_t)(POL_DETAIL_BAD_VALUE | t); return ERR_POLICY_INVALID; }
            pol.budget_pct = v[0];
            break;
        case POL_TLV_DEDUP:
            if (l != 1) { *detail = (uint16_t)(POL_DETAIL_BAD_LEN | t); return ERR_POLICY_INVALID; }
            if (v[0] > 1) { *detail = (uint16_t)(POL_DETAIL_BAD_VALUE | t); return ERR_POLICY_INVALID; }
            pol.dedup = v[0] != 0;
            break;
        case POL_TLV_CACHE_STABLE_PREFIX:
            if (l != 4) { *detail = (uint16_t)(POL_DETAIL_BAD_LEN | t); return ERR_POLICY_INVALID; }
            pol.cache_stable_prefix = get32(v);
            break;
        case POL_TLV_TYPE_WEIGHT:
            if (l != 2) { *detail = (uint16_t)(POL_DETAIL_BAD_LEN | t); return ERR_POLICY_INVALID; }
            if (v[0] >= SEG_TYPE_COUNT || v[1] > 100) { *detail = (uint16_t)(POL_DETAIL_BAD_VALUE | t); return ERR_POLICY_INVALID; }
            pol.type_weight[v[0]] = v[1];
            break;
        default:
            if (!(t & POL_TLV_OPTIONAL)) {
                *detail = (uint16_t)(POL_DETAIL_UNKNOWN | t);
                return ERR_POLICY_INVALID;
            }
            break; /* unknown optional TLV: ignored */
        }
        i = (uint16_t)(i + 2u + l);
    }
    pol.preset = policy_match_preset(&pol);
    *out = pol;
    return ERR_OK;
}

size_t proto_policy_serialize(const proto_policy_t *pol, uint8_t *out, size_t cap)
{
    const size_t n = 2u + 3u + 3u + 6u + 4u * SEG_TYPE_COUNT; /* 30 bytes */
    if (cap < n) {
        return 0;
    }
    size_t i = 0;
    out[i++] = POLICY_VERSION;
    out[i++] = policy_match_preset(pol);
    out[i++] = POL_TLV_BUDGET_PCT; out[i++] = 1; out[i++] = pol->budget_pct;
    out[i++] = POL_TLV_DEDUP; out[i++] = 1; out[i++] = pol->dedup ? 1u : 0u;
    out[i++] = POL_TLV_CACHE_STABLE_PREFIX; out[i++] = 4; put32(&out[i], pol->cache_stable_prefix); i += 4;
    for (uint8_t t = 0; t < SEG_TYPE_COUNT; t++) {
        out[i++] = POL_TLV_TYPE_WEIGHT; out[i++] = 2; out[i++] = t; out[i++] = pol->type_weight[t];
    }
    return i;
}
