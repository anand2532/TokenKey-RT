/*
 * TokenKey RT - USB frame protocol (firmware/docs/usb_protocol.md, draft v0.1)
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
#define PROTO_VERSION      1u
#define PROTO_MAX_PAYLOAD  4096u
#define PROTO_OVERHEAD     8u /* SOF + ver + cmd + seq + len16 + crc16 */
#define PROTO_MAX_FRAME    (PROTO_MAX_PAYLOAD + PROTO_OVERHEAD)
#define PROTO_WINDOW       4u
#define PROTO_RESP_BIT     0x80u

enum {
    CMD_HELLO = 0x01, CMD_PING = 0x02, CMD_GET_INFO = 0x03,
    CMD_SET_MODE = 0x10, CMD_GET_MODE = 0x11,
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
    ERR_SAFE_MODE = 0x0C, ERR_INTERNAL = 0x7F,
};

/* ERROR detail used for commands that are defined in the spec but not implemented yet. */
#define ERR_DETAIL_NOT_IMPLEMENTED 0x0001u

/* GET_INFO TLV types */
enum { TLV_SERIAL = 0x01, TLV_BUILD_ID = 0x02, TLV_FLASH_SIZE = 0x03, TLV_UPTIME_MS = 0x04 };

typedef enum { MODE_ECONOMY = 0, MODE_BALANCED = 1, MODE_QUALITY = 2, MODE_COUNT } tk_mode_t;

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
} proto_device_t;

#define PROTO_CAP_EVENTS 0x00000001u

/* Handle one parse result and write the reply frame into out. Returns reply length (0 = no
 * reply). */
size_t proto_handle(proto_device_t *dev, proto_parse_result_t r, const proto_frame_t *f, uint8_t *out, size_t out_cap);

size_t proto_build_error(uint8_t *out, size_t cap, uint8_t seq, uint8_t orig_cmd, uint8_t code, uint16_t detail);

#endif
