/*
 * TokenKey RT - host simulator library: the device protocol + job layer + context engine
 * (proto.c, jobs.c, engine.c, xxh32.c: the same sources the firmware links) behind a byte
 * pipe, for tools/tkhost.py --sim (ctypes) and the host tests. Time is supplied by the
 * caller (virtual clock), so TTL behaviour is deterministic.
 */
#include <stdint.h>
#include <string.h>

#include "jobs.h"
#include "proto.h"

static tk_slot_t s_slots[TK_SLOTS];
static tk_engine_t s_eng;
static tk_jobs_t s_jobs;
static proto_parser_t s_parser;
static proto_device_t s_dev;
static uint8_t s_tx[PROTO_MAX_FRAME];

#ifndef TK_FW_VERSION
#define TK_FW_VERSION 0
#endif
#ifndef TK_BUILD_ID
#define TK_BUILD_ID "host"
#endif

/* safe_mode: 0/1; part: 0 DVL6B, 1 CVL5B */
void tksim_init(int safe_mode, int part)
{
    memset(&s_dev, 0, sizeof s_dev);
    s_dev.mode = MODE_DEFAULT;
    s_dev.part = (uint8_t)(part ? 1 : 0);
    s_dev.core_mhz = part ? 528 : 600;
    s_dev.fw_version = TK_FW_VERSION;
    s_dev.serial = 0x53494D0000000001ull;
    s_dev.build_id = "sim-" TK_BUILD_ID;
    s_dev.flash_size = 8u * 1024u * 1024u;
    s_dev.caps = PROTO_CAP_EVENTS;
    s_dev.jobs = &s_jobs;
    s_dev.safe_mode = safe_mode != 0;
    tk_jobs_init(&s_jobs, s_slots, &s_eng, s_dev.mode);
    proto_parser_init(&s_parser);
}

/* Feed host->device bytes at virtual time now_ms; device->host bytes go to out.
 * Returns bytes written, or -1 if out is too small. */
int tksim_xfer(const uint8_t *in, uint32_t len, uint32_t now_ms, uint8_t *out, uint32_t cap)
{
    uint32_t o = 0;
    for (uint32_t i = 0; i < len; i++) {
        proto_parse_result_t r = proto_parser_feed(&s_parser, in[i]);
        if (r == PARSE_NONE) {
            continue;
        }
        s_dev.uptime_ms = now_ms;
        tk_jobs_tick(&s_jobs, now_ms);
        size_t n = proto_handle(&s_dev, r, &s_parser.frame, s_tx, sizeof s_tx);
        if (o + n > cap) {
            return -1;
        }
        memcpy(out + o, s_tx, n);
        o += (uint32_t)n;
    }
    return (int)o;
}

uint32_t tksim_mode(void) { return (uint32_t)s_dev.mode; }
