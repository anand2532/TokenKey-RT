/* Host unit test for proto.c: CRC-16/CCITT-FALSE check value and the frame parser/dispatcher.
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
    CHECK(rn == 15 + PROTO_OVERHEAD);
    CHECK(o[2] == (CMD_HELLO | 0x80) && o[3] == 7 && o[4] == 15);
    CHECK(o[6] == 1 && o[7] == 0x00 && o[8] == 0x01 && o[11] == 0); /* proto 1, fw 0.1.0, DVL6B */
    CHECK(o[12] == 0x58 && o[13] == 0x02);                           /* 600 MHz */
    CHECK(o[14] == 0x00 && o[15] == 0x10 && o[16] == 4);             /* 4096, window 4 */
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

    if (fails) {
        printf("%d check(s) FAILED\n", fails);
        return 1;
    }
    printf("test_proto: all checks passed (CRC check 0x%04X)\n", proto_crc16((const uint8_t *)"123456789", 9));
    return 0;
}
