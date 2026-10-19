/*
 * TokenKey RT - main: board bring-up, static FreeRTOS objects, task creation, status_task
 * (LED_STAT + watchdog).
 *
 * Task          prio  stack (words)  role
 * usb_task       4     1024          TinyUSB device task + vendor-bulk frame protocol
 * input_task     3      256          encoder decode + button debounce (1 kHz while active)
 * ui_task        2      512          OLED screens, local mode selection
 * status_task    1      256          LED_STAT patterns, watchdog feed after check-ins
 * idle           0      128          (kernel)
 */
#include "FreeRTOS.h"
#include "event_groups.h"
#include "queue.h"
#include "task.h"

#include "app.h"
#include "board.h"
#include "fsl_device_registers.h"

#ifndef TK_WATCHDOG
#define TK_WATCHDOG 1
#endif
#define WDOG_TIMEOUT_MS   2000u
#define WDOG_CHECK_MS     500u

/* ---- static queues / event group ------------------------------------------------------- */
#define Q_INPUT_RAW_LEN 32
#define Q_UI_LEN        16
#define Q_USB_LEN       8
#define Q_LED_LEN       8

static StaticQueue_t s_q_input_raw_cb, s_q_ui_cb, s_q_usb_cb, s_q_led_cb;
static uint8_t s_q_input_raw_buf[Q_INPUT_RAW_LEN * sizeof(uint32_t)];
static uint8_t s_q_ui_buf[Q_UI_LEN * sizeof(tk_ui_msg_t)];
static uint8_t s_q_usb_buf[Q_USB_LEN * sizeof(tk_usb_msg_t)];
static uint8_t s_q_led_buf[Q_LED_LEN * sizeof(uint8_t)];
static StaticEventGroup_t s_wd_cb;

static tk_app_t s_app;
const tk_app_t *const g_app = &s_app;

/* ---- static tasks ---------------------------------------------------------------------- */
#define STACK_USB    1024
#define STACK_INPUT  256
#define STACK_UI     512
#define STACK_STATUS 256
#define PRIO_USB     4
#define PRIO_INPUT   3
#define PRIO_UI      2
#define PRIO_STATUS  1

static StaticTask_t s_tcb_usb, s_tcb_input, s_tcb_ui, s_tcb_status, s_tcb_idle;
static StackType_t s_stk_usb[STACK_USB], s_stk_input[STACK_INPUT], s_stk_ui[STACK_UI],
    s_stk_status[STACK_STATUS], s_stk_idle[configMINIMAL_STACK_SIZE];

void vApplicationGetIdleTaskMemory(StaticTask_t **tcb, StackType_t **stack, configSTACK_DEPTH_TYPE *size)
{
    *tcb = &s_tcb_idle;
    *stack = s_stk_idle;
    *size = configMINIMAL_STACK_SIZE;
}

void vApplicationStackOverflowHook(TaskHandle_t t, char *name)
{
    (void)t;
    __disable_irq();
    board_uart_puts("\r\n*** stack overflow: ");
    board_uart_puts(name);
    board_uart_puts("\r\n");
    for (;;) {
    }
}

void tk_assert_failed(const char *file, int line)
{
    __disable_irq();
    board_uart_puts("\r\n*** assert ");
    board_uart_puts(file);
    board_uart_puts(":");
    board_uart_puthex((uint32_t)line);
    board_uart_puts("\r\n");
    for (;;) {
    }
}

/* No heap anywhere: any malloc() reference fails at link time (-Wl,--wrap=malloc,
 * __wrap_malloc deliberately undefined). */

/* ---- status_task: LED patterns + watchdog ---------------------------------------------- */
void status_task(void *arg)
{
    const tk_app_t *app = arg;
    uint8_t pattern = LED_OFF;
    uint32_t t = 0, pulse_ms = 0;
    TickType_t last = xTaskGetTickCount();
    TickType_t wd_last = last;

#if TK_WATCHDOG
    board_wdog_start(WDOG_TIMEOUT_MS);
#endif
    for (;;) {
        uint8_t p;
        while (xQueueReceive(app->q_led, &p, 0) == pdPASS) {
            if (p == LED_PULSE) {
                pulse_ms = 40;
            } else {
                pattern = p;
            }
        }
        bool on;
        switch (pattern) {
        case LED_ON: on = true; break;
        case LED_BLINK: on = (t % 1000u) < 500u; break;
        case LED_FAST_BLINK: on = (t % 200u) < 100u; break;
        default: on = false; break;
        }
        if (pulse_ms) {
            on = !on;
            pulse_ms = pulse_ms > 20 ? pulse_ms - 20 : 0;
        }
        board_led_set(on);

        /* Watchdog: feed only if every task checked in since the last check. */
        TickType_t now = xTaskGetTickCount();
        if ((now - wd_last) >= pdMS_TO_TICKS(WDOG_CHECK_MS)) {
            wd_last = now;
            EventBits_t b = xEventGroupGetBits(app->wd);
            if ((b & WD_BITS_ALL) == WD_BITS_ALL) {
                (void)xEventGroupClearBits(app->wd, WD_BITS_ALL);
#if TK_WATCHDOG
                board_wdog_feed();
#endif
            } else {
                board_uart_puts("wdog: missing check-in ");
                board_uart_puthex(~b & WD_BITS_ALL);
                board_uart_puts("\r\n");
            }
        }
        vTaskDelayUntil(&last, pdMS_TO_TICKS(20));
        t += 20;
    }
}

int main(void)
{
    board_init();

    s_app.q_input_raw = xQueueCreateStatic(Q_INPUT_RAW_LEN, sizeof(uint32_t), s_q_input_raw_buf, &s_q_input_raw_cb);
    s_app.q_ui = xQueueCreateStatic(Q_UI_LEN, sizeof(tk_ui_msg_t), s_q_ui_buf, &s_q_ui_cb);
    s_app.q_usb = xQueueCreateStatic(Q_USB_LEN, sizeof(tk_usb_msg_t), s_q_usb_buf, &s_q_usb_cb);
    s_app.q_led = xQueueCreateStatic(Q_LED_LEN, sizeof(uint8_t), s_q_led_buf, &s_q_led_cb);
    s_app.wd = xEventGroupCreateStatic(&s_wd_cb);

    input_init();

    void *a = (void *)&s_app;
    xTaskCreateStatic(usb_task, "usb", STACK_USB, a, PRIO_USB, s_stk_usb, &s_tcb_usb);
    xTaskCreateStatic(input_task, "input", STACK_INPUT, a, PRIO_INPUT, s_stk_input, &s_tcb_input);
    xTaskCreateStatic(ui_task, "ui", STACK_UI, a, PRIO_UI, s_stk_ui, &s_tcb_ui);
    xTaskCreateStatic(status_task, "status", STACK_STATUS, a, PRIO_STATUS, s_stk_status, &s_tcb_status);

    board_uart_puts("starting scheduler\r\n");
    vTaskStartScheduler(); /* never returns (static allocation cannot fail here) */
    for (;;) {
    }
}
