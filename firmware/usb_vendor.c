/*
 * TokenKey RT - USB OTG1 device: PHY/clock bring-up, descriptors, ISR and usb_task.
 *
 * One vendor interface (class 0xFF), bulk OUT 0x01 / bulk IN 0x81, 512 B at HS, 64 B at FS.
 * Frames (firmware/docs/usb_protocol.md) are parsed by proto.c as a byte stream, so a frame
 * may span any number of USB packets.
 *
 * VID/PID: development values, see TK_USB_PID below (the single place they are defined).
 */
#include <string.h>

#include "FreeRTOS.h"
#include "task.h"

#include "app.h"
#include "board.h"
#include "fsl_device_registers.h"
#include "jobs.h"
#include "proto.h"
#include "tusb.h"

/* TODO(#30): replace the dev VID/PID (pid.codes allocation or an owned VID) before any unit
 * leaves the bench. 0x1FC9 is NXP's VID; 0xFFF0 is a made-up PID not assigned to us. This is
 * the only place either value is defined; README "USB protocol" points here. */
#define TK_USB_VID 0x1FC9u
#define TK_USB_PID 0xFFF0u

/* ------------------------------------------------------------------------------------------ */
/* Hardware: PLL3 / USBPHY1 / OTG1 clocks (sequence from fsl_clock.c CLOCK_EnableUsbhs0*)       */
/* ------------------------------------------------------------------------------------------ */
static void usb_hw_init(void)
{
    if (CCM_ANALOG->PLL_USB1 & CCM_ANALOG_PLL_USB1_ENABLE_MASK) {
        /* PLL3 already running (the boot ROM may clock FlexSPI from PLL3 PFD0): never bypass
         * or re-lock it while executing in place, just enable the USB clock output. */
        CCM_ANALOG->PLL_USB1_SET = CCM_ANALOG_PLL_USB1_EN_USB_CLKS_MASK;
    } else {
        CCM_ANALOG->PLL_USB1 = (CCM_ANALOG->PLL_USB1 & ~CCM_ANALOG_PLL_USB1_BYPASS_CLK_SRC_MASK) |
                               CCM_ANALOG_PLL_USB1_BYPASS_MASK | CCM_ANALOG_PLL_USB1_BYPASS_CLK_SRC(0);
        CCM_ANALOG->PLL_USB1 = (CCM_ANALOG->PLL_USB1 & ~CCM_ANALOG_PLL_USB1_DIV_SELECT_MASK) |
                               CCM_ANALOG_PLL_USB1_ENABLE_MASK | CCM_ANALOG_PLL_USB1_POWER_MASK |
                               CCM_ANALOG_PLL_USB1_EN_USB_CLKS_MASK | CCM_ANALOG_PLL_USB1_DIV_SELECT(0);
        while ((CCM_ANALOG->PLL_USB1 & CCM_ANALOG_PLL_USB1_LOCK_MASK) == 0u) {
        }
        CCM_ANALOG->PLL_USB1 &= ~CCM_ANALOG_PLL_USB1_BYPASS_MASK;
    }

    USBPHY1->CTRL &= ~USBPHY_CTRL_SFTRST_MASK;
    USBPHY1->CTRL &= ~USBPHY_CTRL_CLKGATE_MASK;
    USBPHY1->PWD = 0;
    USBPHY1->CTRL |= USBPHY_CTRL_ENAUTOCLR_PHY_PWD_MASK | USBPHY_CTRL_ENAUTOCLR_CLKGATE_MASK |
                     USBPHY_CTRL_ENUTMILEVEL2_MASK | USBPHY_CTRL_ENUTMILEVEL3_MASK;
    /* TX timing trim (TinyUSB imxrt BSP / NXP EVK values) */
    uint32_t tx = USBPHY1->TX & ~(USBPHY_TX_D_CAL_MASK | USBPHY_TX_TXCAL45DM_MASK | USBPHY_TX_TXCAL45DP_MASK);
    USBPHY1->TX = tx | USBPHY_TX_D_CAL(0x0C) | USBPHY_TX_TXCAL45DP(0x06) | USBPHY_TX_TXCAL45DM(0x06);

    CCM->CCGR6 |= CCM_CCGR6_CG0_MASK; /* usboh3 */
    PMU->REG_3P0 = (PMU->REG_3P0 & ~PMU_REG_3P0_OUTPUT_TRG_MASK) | PMU_REG_3P0_OUTPUT_TRG(0x17) |
                   PMU_REG_3P0_ENABLE_LINREG_MASK;

    /* USB ISR calls xQueueSendFromISR (TinyUSB OSAL): must be >= configMAX_SYSCALL priority. */
    NVIC_SetPriority(USB_OTG1_IRQn, TK_IRQ_PRIO_USB);
}

void USB_OTG1_IRQHandler(void) { tusb_int_handler(BOARD_TUD_RHPORT, true); }

/* ------------------------------------------------------------------------------------------ */
/* Descriptors                                                                                 */
/* ------------------------------------------------------------------------------------------ */
enum { STR_LANG = 0, STR_MANUF, STR_PRODUCT, STR_SERIAL, STR_ITF };

static const tusb_desc_device_t s_dev_desc = {
    .bLength = sizeof(tusb_desc_device_t),
    .bDescriptorType = TUSB_DESC_DEVICE,
    .bcdUSB = 0x0200,
    .bDeviceClass = 0x00,
    .bDeviceSubClass = 0x00,
    .bDeviceProtocol = 0x00,
    .bMaxPacketSize0 = CFG_TUD_ENDPOINT0_SIZE,
    .idVendor = TK_USB_VID,
    .idProduct = TK_USB_PID,
    .bcdDevice = TK_FW_BCD,
    .iManufacturer = STR_MANUF,
    .iProduct = STR_PRODUCT,
    .iSerialNumber = STR_SERIAL,
    .bNumConfigurations = 1,
};

const uint8_t *tud_descriptor_device_cb(void) { return (const uint8_t *)&s_dev_desc; }

#define EP_OUT 0x01
#define EP_IN  0x81
#define CONFIG_LEN (TUD_CONFIG_DESC_LEN + TUD_VENDOR_DESC_LEN)

static const uint8_t s_cfg_hs[] = {
    TUD_CONFIG_DESCRIPTOR(1, 1, 0, CONFIG_LEN, 0x80, 100),
    TUD_VENDOR_DESCRIPTOR(0, STR_ITF, EP_OUT, EP_IN, 512),
};
static const uint8_t s_cfg_fs[] = {
    TUD_CONFIG_DESCRIPTOR(1, 1, 0, CONFIG_LEN, 0x80, 100),
    TUD_VENDOR_DESCRIPTOR(0, STR_ITF, EP_OUT, EP_IN, 64),
};
static uint8_t s_cfg_other[CONFIG_LEN];

const uint8_t *tud_descriptor_configuration_cb(uint8_t index)
{
    (void)index;
    return (tud_speed_get() == TUSB_SPEED_HIGH) ? s_cfg_hs : s_cfg_fs;
}

static const tusb_desc_device_qualifier_t s_qualifier = {
    .bLength = sizeof(tusb_desc_device_qualifier_t),
    .bDescriptorType = TUSB_DESC_DEVICE_QUALIFIER,
    .bcdUSB = 0x0200,
    .bDeviceClass = 0x00,
    .bDeviceSubClass = 0x00,
    .bDeviceProtocol = 0x00,
    .bMaxPacketSize0 = CFG_TUD_ENDPOINT0_SIZE,
    .bNumConfigurations = 1,
    .bReserved = 0,
};

const uint8_t *tud_descriptor_device_qualifier_cb(void) { return (const uint8_t *)&s_qualifier; }

const uint8_t *tud_descriptor_other_speed_configuration_cb(uint8_t index)
{
    (void)index;
    memcpy(s_cfg_other, (tud_speed_get() == TUSB_SPEED_HIGH) ? s_cfg_fs : s_cfg_hs, CONFIG_LEN);
    s_cfg_other[1] = TUSB_DESC_OTHER_SPEED_CONFIG;
    return s_cfg_other;
}

static uint16_t s_str[33];

const uint16_t *tud_descriptor_string_cb(uint8_t index, uint16_t langid)
{
    (void)langid;
    static const char *const fixed[] = {
        [STR_MANUF] = "TokenKey (DEV)",
        [STR_PRODUCT] = "TokenKey RT [DEV ONLY VID/PID]",
        [STR_ITF] = "TokenKey vendor bulk v1",
    };
    char tmp[32];
    const char *s;
    size_t n;

    if (index == STR_LANG) {
        s_str[1] = 0x0409;
        n = 1;
    } else {
        if (index == STR_SERIAL) {
            uint64_t id = board_unique_id();
            for (int i = 0; i < 16; i++) {
                uint32_t nib = (uint32_t)(id >> (60 - 4 * i)) & 0xFu;
                tmp[i] = (char)(nib < 10 ? '0' + nib : 'A' + nib - 10);
            }
            tmp[16] = 0;
            s = tmp;
        } else if (index < sizeof fixed / sizeof fixed[0] && fixed[index]) {
            s = fixed[index];
        } else {
            return NULL;
        }
        n = strlen(s);
        if (n > 32) {
            n = 32;
        }
        for (size_t i = 0; i < n; i++) {
            s_str[1 + i] = (uint8_t)s[i];
        }
    }
    s_str[0] = (uint16_t)((TUSB_DESC_STRING << 8) | (2 * n + 2));
    return s_str;
}

/* ------------------------------------------------------------------------------------------ */
/* usb_task                                                                                    */
/* ------------------------------------------------------------------------------------------ */
static proto_parser_t s_parser;
static uint8_t s_rx[512];
static uint8_t s_tx[PROTO_MAX_FRAME];
static uint8_t s_evt_seq;

/* v1.0 job layer storage: ~5 x 34 KB session slots + ~135 KB engine tables. Too big for DTCM
 * (256 KB with .bss + stacks), so it lives in the dedicated 512 KB OCRAM (zeroed by startup.c).
 * Only usb_task touches it. */
#define OCRAM_BSS __attribute__((section(".ocram_bss"), aligned(32)))
static tk_slot_t s_slots[TK_SLOTS] OCRAM_BSS;
static tk_engine_t s_engine OCRAM_BSS;
static tk_jobs_t s_jobs OCRAM_BSS;

/* Queue bytes for bulk IN; keep servicing the stack while the TX FIFO drains. */
static bool usb_send(const uint8_t *buf, size_t len)
{
    size_t off = 0;
    TickType_t t0 = xTaskGetTickCount();
    while (off < len) {
        if (!tud_vendor_mounted()) {
            return false;
        }
        off += tud_vendor_write(buf + off, (uint32_t)(len - off));
        tud_vendor_write_flush();
        if (off < len) {
            if ((xTaskGetTickCount() - t0) > pdMS_TO_TICKS(200)) {
                return false; /* host not reading: drop the rest of this frame */
            }
            tud_task_ext(1, false);
        }
    }
    return true;
}

static void send_event(uint8_t cmd, const uint8_t *pl, uint16_t len)
{
    size_t n = proto_build(s_tx, sizeof s_tx, cmd, s_evt_seq++, pl, len);
    if (n) {
        (void)usb_send(s_tx, n);
    }
}

static void post_ui_job(const tk_app_t *app, const tk_jobs_t *j, uint8_t state, uint8_t pct)
{
    tk_ui_msg_t m = {.type = UI_MSG_JOB};
    m.u.job.state = state;
    m.u.job.progress = pct;
    m.u.job.savings_pct = j->last_savings_pct;
    m.u.job.job_id = j->job_id;
    m.u.job.jobs_done = j->jobs_done;
    m.u.job.tok_in = j->lifetime.tok_in;
    m.u.job.tok_out = j->lifetime.tok_out;
    m.u.job.dup_hits = j->lifetime.dup_hits;
    (void)xQueueSend(app->q_ui, &m, 0);
}

/* After every frame / tick: EVT_PROGRESS (job_id u16, pct u8) to the host every >= 10 %, and the
 * same progress / savings to the OLED. */
static void report_job(const tk_app_t *app, const tk_jobs_t *j, bool mounted, bool aborted)
{
    static uint8_t last_pct = 0xFF;
    static tk_job_state_t last_state = JOB_IDLE;
    uint8_t pct = tk_jobs_progress(j);
    bool running = (j->state == JOB_PASS1 || j->state == JOB_PASS2);
    if (aborted) {
        post_ui_job(app, j, UI_JOB_ABORTED, 0);
    } else if (j->state != last_state || (running && (last_pct == 0xFF || pct >= last_pct + 10u))) {
        if (running || j->state == JOB_DONE) {
            if (mounted) {
                uint8_t pl[3] = {(uint8_t)j->job_id, (uint8_t)(j->job_id >> 8), pct};
                send_event(EVT_PROGRESS, pl, sizeof pl);
            }
            post_ui_job(app, j, running ? UI_JOB_RUNNING : UI_JOB_DONE, pct);
        }
        last_pct = pct;
    }
    if (!running) {
        last_pct = 0xFF;
    }
    last_state = j->state;
}

static void post_ui_state(const tk_app_t *app, bool mounted, uint32_t ok, uint32_t bad)
{
    tk_ui_msg_t m = {.type = UI_MSG_USB_STATE};
    m.u.usb.mounted = mounted;
    m.u.usb.frames_ok = ok;
    m.u.usb.frames_bad = bad;
    (void)xQueueSend(app->q_ui, &m, 0);
}

void usb_task(void *arg)
{
    const tk_app_t *app = arg;
    const tk_clock_info_t *clk = board_clock_info();

    const tk_boot_info_t *boot = board_boot_info();
    tk_jobs_init(&s_jobs, s_slots, &s_engine, MODE_DEFAULT);
    s_jobs.cycles = board_cycles; /* GET_STATS cycles */
    proto_device_t dev = {
        .mode = MODE_DEFAULT,
        .part = (uint8_t)clk->part,
        .core_mhz = (uint16_t)(clk->core_hz / 1000000u),
        .fw_version = TK_FW_VERSION,
        .serial = board_unique_id(),
        .build_id = TK_BUILD_ID,
        .flash_size = 8u * 1024u * 1024u,
        .caps = PROTO_CAP_EVENTS, /* + PROTO_CAP_SESSIONS added by proto_handle unless safe mode */
        .jobs = &s_jobs,
        .safe_mode = boot->safe_mode,
    };
    proto_parser_init(&s_parser);

    usb_hw_init();
    const tusb_rhport_init_t rh = {.role = TUSB_ROLE_DEVICE, .speed = TUSB_SPEED_AUTO};
    (void)tusb_init(BOARD_TUD_RHPORT, &rh);

    bool mounted = false;
    uint32_t ok = 0, bad = 0, reported_ok = 0, reported_bad = 0;
    TickType_t last_report = 0;

    for (;;) {
        /* Runs the TinyUSB device stack; returns when its event queue is empty or after 20 ms. */
        tud_task_ext(20, false);

        bool m = tud_vendor_mounted();
        if (m != mounted) {
            mounted = m;
            proto_parser_init(&s_parser);
            post_ui_state(app, mounted, ok, bad);
            uint8_t led = mounted ? LED_ON : LED_OFF;
            (void)xQueueSend(app->q_led, &led, 0);
        }

        /* Host -> device frames */
        while (tud_vendor_available()) {
            uint32_t n = tud_vendor_read(s_rx, sizeof s_rx);
            for (uint32_t i = 0; i < n; i++) {
                proto_parse_result_t r = proto_parser_feed(&s_parser, s_rx[i]);
                if (r == PARSE_NONE) {
                    continue;
                }
                if (r == PARSE_FRAME) {
                    ok++;
                } else {
                    bad++;
                }
                dev.uptime_ms = (uint32_t)(xTaskGetTickCount() * portTICK_PERIOD_MS);
                size_t len = proto_handle(&dev, r, &s_parser.frame, s_tx, sizeof s_tx);
                if (len) {
                    (void)usb_send(s_tx, len);
                }
                report_job(app, &s_jobs, mounted, false);
                xEventGroupSetBits(app->wd, WD_BIT_USB); /* long bursts: keep checking in */
                if (dev.mode_changed) {
                    dev.mode_changed = false;
                    tk_ui_msg_t um = {.type = UI_MSG_MODE_FROM_HOST};
                    um.u.mode = (uint8_t)dev.mode;
                    (void)xQueueSend(app->q_ui, &um, 0);
                }
                uint8_t led = LED_PULSE; /* short blink on traffic */
                (void)xQueueSend(app->q_led, &led, 0);
            }
        }

        /* Device -> host: mode changes and button events coming from ui_task */
        tk_usb_msg_t msg;
        while (xQueueReceive(app->q_usb, &msg, 0) == pdPASS) {
            if (msg.type == USB_MSG_MODE_FROM_DEVICE && msg.u.mode < MODE_COUNT) {
                dev.mode = (tk_mode_t)msg.u.mode;
                tk_jobs_set_mode(&s_jobs, dev.mode); /* device-global policy follows the mode */
                if (mounted) {
                    send_event(EVT_MODE, &msg.u.mode, 1);
                }
            } else if (msg.type == USB_MSG_CANCEL_JOB) {
                if (tk_jobs_cancel(&s_jobs)) {
                    report_job(app, &s_jobs, mounted, true);
                }
            } else if (msg.type == USB_MSG_BUTTON && mounted) {
                uint8_t pl[2] = {msg.u.input.key, msg.u.input.action};
                send_event(EVT_BUTTON, pl, 2);
            }
        }

        TickType_t now = xTaskGetTickCount();
        if (tk_jobs_tick(&s_jobs, (uint32_t)(now * portTICK_PERIOD_MS))) {
            report_job(app, &s_jobs, mounted, true); /* host went quiet mid-job: aborted, session restored */
        }
        if ((ok != reported_ok || bad != reported_bad) && (now - last_report) > pdMS_TO_TICKS(250)) {
            reported_ok = ok;
            reported_bad = bad;
            last_report = now;
            post_ui_state(app, mounted, ok, bad);
        }

        xEventGroupSetBits(app->wd, WD_BIT_USB);
    }
}
