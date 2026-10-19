/*
 * TokenKey RT - input: EC11 encoder (ENC_A/ENC_B), ENC_SW, BTN1, BTN2.
 *
 * GPIO1 any-edge IRQ (pins 18..22) -> ISR snapshots GPIO1->PSR -> q_input_raw (xQueueSendFromISR)
 * -> input_task decodes the encoder with a quadrature state table and debounces the
 * buttons on the 1 kHz FreeRTOS tick, then posts tk_input_event_t to ui_task.
 * All inputs are active low with external 10k pull-ups (+10nF RC on ENC_A/B).
 */
#include "FreeRTOS.h"
#include "task.h"

#include "app.h"
#include "board.h"
#include "fsl_device_registers.h"

#ifndef TK_ENC_STEPS_PER_DETENT
#define TK_ENC_STEPS_PER_DETENT 2 /* EC11E18244A5: 18 pulses / 36 detents -> 2 edges per detent */
#endif
#ifndef TK_ENC_INVERT
#define TK_ENC_INVERT 0           /* set to 1 if CW/CCW come out swapped on the board */
#endif
#define DEBOUNCE_MS   20u
#define LONGPRESS_MS  800u
#define ACTIVE_MS     50u         /* keep scanning at 1 kHz this long after the last edge */

/* ---- ISR -------------------------------------------------------------------------------- */
static QueueHandle_t s_raw_q;

void GPIO1_Combined_16_31_IRQHandler(void)
{
    uint32_t isr = GPIO1->ISR & TK_INPUT_PIN_MASK;
    GPIO1->ISR = isr; /* w1c */
    uint32_t sample = GPIO1->PSR;
    BaseType_t woken = pdFALSE;
    if (s_raw_q != NULL) {
        (void)xQueueSendFromISR(s_raw_q, &sample, &woken); /* full -> dropped; the task resyncs */
    }
    __DSB();
    portYIELD_FROM_ISR(woken);
}

void input_init(void)
{
    s_raw_q = g_app->q_input_raw;
    GPIO1->ISR = TK_INPUT_PIN_MASK;
    GPIO1->IMR |= TK_INPUT_PIN_MASK;
    NVIC_SetPriority(GPIO1_Combined_16_31_IRQn, TK_IRQ_PRIO_GPIO); /* >= configMAX_SYSCALL (5) */
    NVIC_EnableIRQ(GPIO1_Combined_16_31_IRQn);                     /* PRIMASK still set until the scheduler starts */
}

/* ---- encoder ---------------------------------------------------------------------------- */
/* index = prev_AB << 2 | cur_AB ; +1 = one quarter step CW, -1 = CCW, 0 = none/invalid (bounce) */
static const int8_t k_quad[16] = {0, -1, +1, 0, +1, 0, 0, -1, -1, 0, 0, +1, 0, +1, -1, 0};

typedef struct {
    uint8_t ab;
    int8_t acc;
} enc_t;

static uint8_t enc_ab(uint32_t psr)
{
    return (uint8_t)((((psr >> TK_PIN_ENC_A) & 1u) << 1) | ((psr >> TK_PIN_ENC_B) & 1u));
}

static void post(const tk_app_t *app, uint8_t key, uint8_t action)
{
    tk_ui_msg_t m = {.type = UI_MSG_INPUT};
    m.u.input.key = key;
    m.u.input.action = action;
    (void)xQueueSend(app->q_ui, &m, 0);
}

static void enc_update(const tk_app_t *app, enc_t *e, uint32_t psr)
{
    uint8_t ab = enc_ab(psr);
    int8_t d = k_quad[(e->ab << 2) | ab];
    e->ab = ab;
    if (TK_ENC_INVERT) {
        d = (int8_t)-d;
    }
    e->acc = (int8_t)(e->acc + d);
    if (e->acc >= TK_ENC_STEPS_PER_DETENT) {
        e->acc = 0;
        post(app, KEY_ENCODER, ACT_CW);
    } else if (e->acc <= -TK_ENC_STEPS_PER_DETENT) {
        e->acc = 0;
        post(app, KEY_ENCODER, ACT_CCW);
    }
}

/* ---- buttons ---------------------------------------------------------------------------- */
typedef struct {
    uint8_t key, pin;
    bool pressed;     /* debounced state */
    bool long_sent;
    uint16_t cnt_ms;  /* time the raw level has disagreed with the debounced state */
    TickType_t t_press;
} btn_t;

static bool btn_update(const tk_app_t *app, btn_t *b, uint32_t psr, uint32_t elapsed_ms, TickType_t now)
{
    bool raw = ((psr >> b->pin) & 1u) == 0u; /* active low */
    if (raw != b->pressed) {
        b->cnt_ms = (uint16_t)(b->cnt_ms + elapsed_ms);
        if (b->cnt_ms >= DEBOUNCE_MS) {
            b->pressed = raw;
            b->cnt_ms = 0;
            if (raw) {
                b->t_press = now;
                b->long_sent = false;
                post(app, b->key, ACT_PRESS);
            } else {
                post(app, b->key, ACT_RELEASE);
            }
        }
    } else {
        b->cnt_ms = 0;
    }
    if (b->pressed && !b->long_sent && (now - b->t_press) >= pdMS_TO_TICKS(LONGPRESS_MS)) {
        b->long_sent = true;
        post(app, b->key, ACT_LONG);
    }
    return b->pressed || b->cnt_ms != 0; /* still needs scanning */
}

void input_task(void *arg)
{
    const tk_app_t *app = arg;
    btn_t btn[3] = {
        {.key = KEY_ENC_SW, .pin = TK_PIN_ENC_SW},
        {.key = KEY_BTN1, .pin = TK_PIN_BTN1},
        {.key = KEY_BTN2, .pin = TK_PIN_BTN2},
    };
    enc_t enc = {.ab = enc_ab(board_gpio1_read()), .acc = 0};
    TickType_t last_scan = xTaskGetTickCount();
    TickType_t active_until = last_scan;
    bool busy = false;

    for (;;) {
        TickType_t now = xTaskGetTickCount();
        bool active = busy || (int32_t)(active_until - now) > 0;
        uint32_t sample;
        /* Idle: block until an edge (or 100 ms for the watchdog check-in). Active: 1 ms tick. */
        if (xQueueReceive(app->q_input_raw, &sample, active ? 1 : pdMS_TO_TICKS(100)) == pdPASS) {
            enc_update(app, &enc, sample);
            active_until = xTaskGetTickCount() + pdMS_TO_TICKS(ACTIVE_MS);
        }
        now = xTaskGetTickCount();
        if (now != last_scan) {
            uint32_t psr = board_gpio1_read();
            last_scan = now;
            busy = false;
            for (unsigned i = 0; i < 3; i++) {
                /* count scans, not wall time: a late scan never shortens the 20 ms debounce */
                busy |= btn_update(app, &btn[i], psr, 1u, now);
            }
            /* resync the encoder state if an ISR sample was dropped */
            if (uxQueueMessagesWaiting(app->q_input_raw) == 0) {
                enc_update(app, &enc, psr);
            }
        }
        xEventGroupSetBits(app->wd, WD_BIT_INPUT);
    }
}
