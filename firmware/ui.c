/*
 * TokenKey RT - ui_task: OLED screens and local mode selection.
 *
 * Inputs (q_ui): input events from input_task; mode, USB state and job progress from usb_task.
 * Outputs (q_usb): mode changes, button events (EVT_BUTTON) and job cancel to usb_task.
 *
 * Screens (encoder rotates through them):  HOME -> STATS -> INFO -> HOME ...
 *   HOME   mode, last job savings, job progress bar, USB state, SAFE MODE banner
 *   STATS  lifetime jobs / tokens in / out / saved %, dedup hits, frames
 *   INFO   fw version, part + core clock, reset cause, consecutive watchdog resets
 *   MODES  (ENC_SW from HOME) list of the 5 modes; rotate = highlight, ENC_SW = apply
 * Buttons: BTN1 = cycle mode immediately (any screen)
 *          BTN2 = cancel the running job if any, else back (MODES -> HOME, others -> HOME)
 */
#include <string.h>

#include "FreeRTOS.h"
#include "task.h"

#include "app.h"
#include "board.h"
#include "oled.h"
#include "proto.h"

#define SPLASH_MS 1500u

typedef enum { SCR_HOME = 0, SCR_STATS, SCR_INFO, SCR_ROTATING, SCR_MODES = SCR_ROTATING } ui_screen_t;

typedef struct {
    ui_screen_t screen;
    tk_mode_t mode;     /* applied mode */
    tk_mode_t cursor;   /* highlighted mode on the MODES screen */
    bool usb_mounted;
    uint32_t frames_ok, frames_bad;
    uint8_t job_state;  /* tk_ui_job_state_t */
    uint8_t progress, savings_pct;
    uint16_t job_id;
    uint32_t jobs_done, tok_in, tok_out, dup_hits;
} ui_state_t;

static char *u32_to_str(char *b, uint32_t v)
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
    return b;
}

static void line_kv(int y, const char *k, uint32_t v, const char *suffix)
{
    char l[24];
    strcpy(l, k);
    char *e = u32_to_str(l + strlen(l), v);
    if (suffix) {
        strcpy(e, suffix);
    }
    oled_text(0, y, l, 1, false);
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

static void header(const ui_state_t *s, const char *title)
{
    oled_text(0, 0, title, 1, false);
    oled_text(80, 0, s->usb_mounted ? "USB ok" : "USB --", 1, s->usb_mounted);
}

static void draw_home(const ui_state_t *s)
{
    header(s, "TokenKey");
    oled_text(0, 12, proto_mode_name(s->mode), 2, false);
    if (s->jobs_done) {
        line_kv(32, "saved ", s->savings_pct, "% last job");
    } else {
        oled_text(0, 32, "no jobs yet", 1, false);
    }
    if (s->job_state == UI_JOB_RUNNING) {
        oled_fill_rect(0, 44, OLED_W, 8, false);
        oled_fill_rect(0, 44, (OLED_W * s->progress) / 100, 8, true);
    } else if (s->job_state == UI_JOB_ABORTED) {
        oled_text(0, 44, "job aborted", 1, false);
    }
    if (board_boot_info()->safe_mode) {
        oled_fill_rect(0, 54, OLED_W, 10, true);
        oled_text(2, 55, "SAFE MODE: no jobs", 1, true);
    }
}

static void draw_stats(const ui_state_t *s)
{
    header(s, "STATS");
    line_kv(12, "jobs ", s->jobs_done, NULL);
    line_kv(22, "tok in  ", s->tok_in, NULL);
    line_kv(32, "tok out ", s->tok_out, NULL);
    uint32_t pct = s->tok_in ? (uint32_t)(100u - (uint64_t)s->tok_out * 100u / s->tok_in) : 0u;
    line_kv(42, "saved ", pct, "%");
    line_kv(52, "dups ", s->dup_hits, NULL);
    char l[24];
    char *e = u32_to_str(l, s->frames_ok);
    *e++ = '/';
    (void)u32_to_str(e, s->frames_bad);
    oled_text(70, 52, l, 1, false);
}

static void draw_info(const ui_state_t *s)
{
    const tk_clock_info_t *c = board_clock_info();
    const tk_boot_info_t *b = board_boot_info();
    header(s, "INFO");
    oled_text(0, 12, "fw " TK_FW_VERSION_STR, 1, false);
    oled_text(0, 22, c->part == TK_PART_ID_DVL6B ? "DVL6B 600 MHz" : "CVL5B 528 MHz", 1, false);
    oled_text(0, 32, "reset:", 1, false);
    oled_text(40, 32, board_reset_cause_name(b->cause), 1, false);
    line_kv(42, "wdog resets ", b->wdog_count, NULL);
    oled_text(0, 52, b->safe_mode ? "SAFE MODE" : TK_BUILD_ID, 1, false);
}

static void draw_modes(const ui_state_t *s)
{
    header(s, "MODE");
    for (int m = 0; m < MODE_COUNT; m++) {
        int y = 10 + m * 10;
        bool sel = (m == (int)s->cursor);
        if (sel) {
            oled_fill_rect(0, y - 1, OLED_W, 10, true);
        }
        char line[24];
        strcpy(line, m == (int)s->mode ? "> " : "  ");
        strcat(line, proto_mode_name((tk_mode_t)m));
        oled_text(2, y, line, 1, sel);
        char pct[6];
        strcpy(u32_to_str(pct, proto_mode_budget_pct((tk_mode_t)m)), "%");
        oled_text(100, y, pct, 1, sel);
    }
}

static void draw(const ui_state_t *s)
{
    oled_clear();
    switch (s->screen) {
    case SCR_STATS: draw_stats(s); break;
    case SCR_INFO: draw_info(s); break;
    case SCR_MODES: draw_modes(s); break;
    default: draw_home(s); break;
    }
    (void)oled_flush(); /* ~25 ms worst case for a full 1 KB flush at ~365 kHz */
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
    if (e.key == KEY_ENCODER) {
        int d = (e.action == ACT_CW) ? 1 : -1;
        if (s->screen == SCR_MODES) {
            s->cursor = (tk_mode_t)(((int)s->cursor + d + MODE_COUNT) % MODE_COUNT);
        } else {
            s->screen = (ui_screen_t)(((int)s->screen + d + SCR_ROTATING) % SCR_ROTATING);
        }
        return;
    }
    if (e.action != ACT_PRESS) {
        return;
    }
    tk_usb_msg_t u = {.type = USB_MSG_BUTTON, .u.input = e};
    (void)xQueueSend(app->q_usb, &u, 0); /* EVT_BUTTON to the host if connected */
    switch (e.key) {
    case KEY_ENC_SW:
        if (s->screen == SCR_HOME) {
            s->cursor = s->mode;
            s->screen = SCR_MODES;
        } else if (s->screen == SCR_MODES) {
            if (s->cursor != s->mode) {
                apply_mode(app, s, s->cursor);
            }
            s->screen = SCR_HOME;
        } else {
            s->screen = SCR_HOME;
        }
        break;
    case KEY_BTN1:
        apply_mode(app, s, (tk_mode_t)((s->mode + 1) % MODE_COUNT));
        break;
    case KEY_BTN2:
        if (s->job_state == UI_JOB_RUNNING) {
            tk_usb_msg_t c = {.type = USB_MSG_CANCEL_JOB};
            (void)xQueueSend(app->q_usb, &c, 0);
        }
        s->cursor = s->mode;
        s->screen = SCR_HOME;
        break;
    default:
        break;
    }
}

void ui_task(void *arg)
{
    const tk_app_t *app = arg;
    ui_state_t s = {.screen = SCR_HOME, .mode = MODE_DEFAULT, .cursor = MODE_DEFAULT};

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
            case UI_MSG_JOB:
                s.job_state = m.u.job.state;
                s.progress = m.u.job.progress;
                s.savings_pct = m.u.job.savings_pct;
                s.job_id = m.u.job.job_id;
                s.jobs_done = m.u.job.jobs_done;
                s.tok_in = m.u.job.tok_in;
                s.tok_out = m.u.job.tok_out;
                s.dup_hits = m.u.job.dup_hits;
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
            draw(&s);
            dirty = false;
        }
        xEventGroupSetBits(app->wd, WD_BIT_UI);
    }
}
