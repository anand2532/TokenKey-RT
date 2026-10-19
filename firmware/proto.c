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
         * core_mhz u16, max_payload u16, window u8, caps u32 = 15 bytes. */
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
        return reply(out, cap, f, pl, 15);
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
        /* Specified but not part of the skeleton. */
        return proto_build_error(out, cap, f->seq, f->cmd, ERR_UNKNOWN_CMD, ERR_DETAIL_NOT_IMPLEMENTED);
    default:
        return proto_build_error(out, cap, f->seq, f->cmd, ERR_UNKNOWN_CMD, 0);
    }
}
