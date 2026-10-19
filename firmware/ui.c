/*
 * TokenKey RT - ui_task: OLED screens and local mode selection.
 *
 * Inputs (q_ui): input events from input_task, mode/USB state from usb_task.
 * Outputs: mode changes + button events to usb_task (q_usb).
 *
 * Controls: rotate encoder = move the highlighted mode, ENC_SW = apply it,
 * BTN1 = cycle mode immediately, BTN2 = cancel the highlight (back).
 */
#include <string.h>

#include "FreeRTOS.h"
#include "task.h"

#include "app.h"
#include "board.h"
#include "oled.h"
#include "proto.h"

#define SPLASH_MS 1500u

typedef struct {
    tk_mode_t mode;     /* applied mode */
    tk_mode_t cursor;   /* highlighted mode (== mode when not browsing) */
    bool usb_mounted;
    uint32_t frames_ok, frames_bad;
    char last_input[12];
} ui_state_t;

static void u32_to_str(char *b, uint32_t v)
{
    char t[11];
    int n = 0;
    do {
        t[n++] = (char)('0' + v % 10u);
        v /= 10u;
    } while (v && n < 10);
    while (n) {
        *b++ = t[--n];
    }
    *b = 0;
}

static void draw_splash(void)
{
    const tk_clock_info_t *c = board_clock_info();
    oled_clear();
    oled_text(4, 4, "TokenKey RT", 2, false);
    oled_text(4, 26, "fw " TK_FW_VERSION_STR, 1, false);
    oled_text(4, 38, c->part == TK_PART_ID_DVL6B ? "DVL6B 600 MHz" : "CVL5B 528 MHz", 1, false);
    if (c->fell_back) {
        oled_text(4, 50, "fuse fallback 528", 1, false);
    }
    (void)oled_flush();
}

static void draw_mode(const ui_state_t *s)
{
    char line[24];
    oled_clear();
    oled_text(0, 0, "MODE", 1, false);
    oled_text(80, 0, s->usb_mounted ? "USB ok" : "USB --", 1, s->usb_mounted);

    for (int m = 0; m < MODE_COUNT; m++) {
        int y = 12 + m * 10;
        bool sel = (m == (int)s->cursor);
        if (sel) {
            oled_fill_rect(0, y - 1, OLED_W, 10, true);
        }
        strcpy(line, m == (int)s->mode ? "> " : "  ");
        strcat(line, proto_mode_name((tk_mode_t)m));
        oled_text(2, y, line, 1, sel);
        char pct[6];
        u32_to_str(pct, proto_mode_budget_pct((tk_mode_t)m));
        strcat(pct, "%");
        oled_text(100, y, pct, 1, sel);
    }

    strcpy(line, "rx ");
    u32_to_str(line + strlen(line), s->frames_ok);
    strcat(line, " err ");
    u32_to_str(line + strlen(line), s->frames_bad);
    oled_text(0, 46, line, 1, false);
    oled_text(0, 56, s->last_input, 1, false);
    (void)oled_flush();
}

static void apply_mode(const tk_app_t *app, ui_state_t *s, tk_mode_t m)
{
    s->mode = m;
    s->cursor = m;
    tk_usb_msg_t u = {.type = USB_MSG_MODE_FROM_DEVICE};
    u.u.mode = (uint8_t)m;
    (void)xQueueSend(app->q_usb, &u, 0);
}

static void on_input(const tk_app_t *app, ui_state_t *s, tk_input_event_t e)
{
    static const char *const keys[] = {"ENC", "ENC_SW", "BTN1", "BTN2"};
    static const char *const acts[] = {"down", "up", "long", "+", "-"};
    if (e.key < 4 && e.action < 5) {
        strcpy(s->last_input, keys[e.key]);
        strcat(s->last_input, " ");
        strcat(s->last_input, acts[e.action]);
    }

    if (e.key == KEY_ENCODER) {
        int c = (int)s->cursor + (e.action == ACT_CW ? 1 : -1);
        s->cursor = (tk_mode_t)((c + MODE_COUNT) % MODE_COUNT);
        return;
    }
    if (e.action == ACT_PRESS) {
        tk_usb_msg_t u = {.type = USB_MSG_BUTTON, .u.input = e};
        (void)xQueueSend(app->q_usb, &u, 0); /* EVT_BUTTON to the host if connected */
        if (e.key == KEY_ENC_SW && s->cursor != s->mode) {
            apply_mode(app, s, s->cursor);
        } else if (e.key == KEY_BTN1) {
            apply_mode(app, s, (tk_mode_t)((s->mode + 1) % MODE_COUNT));
        } else if (e.key == KEY_BTN2) {
            s->cursor = s->mode;
        }
    }
}

void ui_task(void *arg)
{
    const tk_app_t *app = arg;
    ui_state_t s = {.mode = MODE_BALANCED, .cursor = MODE_BALANCED};
    strcpy(s.last_input, "-");

    if (!oled_init()) {
        board_uart_puts("oled: no ACK at 0x3C, running headless\r\n");
    }
    draw_splash();
    TickType_t splash_end = xTaskGetTickCount() + pdMS_TO_TICKS(SPLASH_MS);
    bool splash = true, dirty = true;

    for (;;) {
        tk_ui_msg_t m;
        if (xQueueReceive(app->q_ui, &m, pdMS_TO_TICKS(100)) == pdPASS) {
            switch (m.type) {
            case UI_MSG_INPUT:
                on_input(app, &s, m.u.input);
                break;
            case UI_MSG_MODE_FROM_HOST:
                if (m.u.mode < MODE_COUNT) {
                    s.mode = s.cursor = (tk_mode_t)m.u.mode;
                }
                break;
            case UI_MSG_USB_STATE:
                s.usb_mounted = m.u.usb.mounted;
                s.frames_ok = m.u.usb.frames_ok;
                s.frames_bad = m.u.usb.frames_bad;
                break;
            default:
                break;
            }
            dirty = true;
        }
        if (splash && (int32_t)(xTaskGetTickCount() - splash_end) >= 0) {
            splash = false;
            dirty = true;
        }
        if (!splash && dirty && uxQueueMessagesWaiting(app->q_ui) == 0) {
            draw_mode(&s); /* ~25 ms worst case for a full 1 KB flush at ~365 kHz */
            dirty = false;
        }
        xEventGroupSetBits(app->wd, WD_BIT_UI);
    }
}
