/*
 * TokenKey RT - inter-task messages and task entry points.
 *
 * Tasks never share mutable state; everything crosses task boundaries through these queues
 * (see README "Tasks and data flow").
 *
 *   GPIO1 ISR ----q_input_raw----> input_task ----q_ui----> ui_task
 *   usb_task  ----q_ui (mode/USB state/job progress)------>  ui_task
 *   ui_task   ----q_usb (mode change, buttons, cancel)---->  usb_task
 *   usb_task, ui_task ----q_led----> status_task (LED_STAT + watchdog)
 */
#ifndef TK_APP_H
#define TK_APP_H

#include <stdbool.h>
#include <stdint.h>

#include "FreeRTOS.h"
#include "event_groups.h"
#include "queue.h"

/* ---- input events (input_task -> ui_task) ------------------------------------------- */
typedef enum { KEY_ENCODER = 0, KEY_ENC_SW = 1, KEY_BTN1 = 2, KEY_BTN2 = 3 } tk_key_t;
typedef enum {
    ACT_PRESS = 0, ACT_RELEASE = 1, ACT_LONG = 2, /* buttons */
    ACT_CW = 3, ACT_CCW = 4,                      /* encoder detent */
} tk_action_t;

typedef struct {
    uint8_t key;    /* tk_key_t */
    uint8_t action; /* tk_action_t */
} tk_input_event_t;

/* ---- ui_task inbox ------------------------------------------------------------------ */
typedef enum { UI_MSG_INPUT, UI_MSG_MODE_FROM_HOST, UI_MSG_USB_STATE, UI_MSG_JOB } tk_ui_msg_type_t;
typedef enum { UI_JOB_IDLE = 0, UI_JOB_RUNNING, UI_JOB_DONE, UI_JOB_ABORTED } tk_ui_job_state_t;
typedef struct {
    uint8_t type;
    union {
        tk_input_event_t input;
        uint8_t mode; /* tk_mode_t */
        struct {
            bool mounted;
            uint32_t frames_ok;
            uint32_t frames_bad;
        } usb;
        struct {
            uint8_t state;       /* tk_ui_job_state_t */
            uint8_t progress;    /* 0..100 */
            uint8_t savings_pct; /* last finished job: 100 - 100*tok_out/tok_in */
            uint16_t job_id;
            uint32_t jobs_done;
            uint32_t tok_in, tok_out; /* lifetime */
            uint32_t dup_hits;        /* lifetime */
        } job;
    } u;
} tk_ui_msg_t;

/* ---- usb_task inbox ----------------------------------------------------------------- */
typedef enum { USB_MSG_MODE_FROM_DEVICE, USB_MSG_BUTTON, USB_MSG_CANCEL_JOB } tk_usb_msg_type_t;
typedef struct {
    uint8_t type;
    union {
        uint8_t mode;
        tk_input_event_t input;
    } u;
} tk_usb_msg_t;

/* ---- status_task inbox -------------------------------------------------------------- */
typedef enum { LED_OFF = 0, LED_ON, LED_BLINK, LED_FAST_BLINK, LED_PULSE } tk_led_pattern_t;

/* ---- watchdog check-in bits (event group, set by each task, consumed by status_task) - */
#define WD_BIT_USB    (1u << 0)
#define WD_BIT_INPUT  (1u << 1)
#define WD_BIT_UI     (1u << 2)
#define WD_BITS_ALL   (WD_BIT_USB | WD_BIT_INPUT | WD_BIT_UI)

/* Queue / event-group handles, created statically in main.c before the scheduler starts. */
typedef struct {
    QueueHandle_t q_input_raw; /* uint32_t GPIO1 snapshots from the ISR */
    QueueHandle_t q_ui;        /* tk_ui_msg_t */
    QueueHandle_t q_usb;       /* tk_usb_msg_t */
    QueueHandle_t q_led;       /* uint8_t tk_led_pattern_t */
    EventGroupHandle_t wd;     /* WD_BIT_* check-ins */
} tk_app_t;

extern const tk_app_t *const g_app;

/* Task entry points (pvParameters = g_app). */
void usb_task(void *arg);
void ui_task(void *arg);
void input_task(void *arg);
void status_task(void *arg);

/* Called from main() before the scheduler starts. */
void input_init(void);

#endif
