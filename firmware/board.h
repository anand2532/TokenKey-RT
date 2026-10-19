/*
 * TokenKey RT - board support (MIMXRT1062, 196 MAPBGA 10x10)
 *
 * Pin map: docs/pin-map.md (frozen baseline rev A0-draft) + firmware/docs/firmware_architecture.md.
 * All pad numbers live in board.c; this header only exposes logical names.
 */
#ifndef TK_BOARD_H
#define TK_BOARD_H

#include <stdbool.h>
#include <stdint.h>

/* Build-time part selection (CMake: -DTK_PART=DVL6B|CVL5B -> TK_PART_DVL6B=1 / TK_PART_CVL5B=1). */
#if !defined(TK_PART_DVL6B) && !defined(TK_PART_CVL5B)
#define TK_PART_CVL5B 1 /* safe default: never assume the 600 MHz grade */
#endif

typedef enum {
    TK_PART_ID_DVL6B = 0, /* matches HELLO.part in usb_protocol.md */
    TK_PART_ID_CVL5B = 1,
} tk_part_id_t;

/* Result of clock bring-up, reported over USB (HELLO/GET_INFO) and on the OLED. */
typedef struct {
    tk_part_id_t part;        /* part the clock tree was configured for */
    uint32_t core_hz;         /* 600000000 or 528000000 */
    uint8_t dcdc_trg;         /* DCDC_REG3[TRG] actually programmed (0.8 V + 25 mV * TRG) */
    uint8_t fuse_speed_grade; /* OCOTP 0x440[17:16]: 01 = 500/528 MHz grade, 10 = 600 MHz grade */
    bool fell_back;           /* build asked for DVL6B but fuses did not confirm -> 528 MHz */
} tk_clock_info_t;

/* GPIO1 bit numbers (all ALT5 on GPIO_AD_B1_xx). */
#define TK_PIN_ENC_A   18u /* L11 GPIO_AD_B1_02 */
#define TK_PIN_ENC_B   19u /* M12 GPIO_AD_B1_03 */
#define TK_PIN_ENC_SW  20u /* L12 GPIO_AD_B1_04, active low */
#define TK_PIN_BTN1    21u /* K12 GPIO_AD_B1_05, active low */
#define TK_PIN_BTN2    22u /* J12 GPIO_AD_B1_06, active low */
#define TK_PIN_LED     24u /* H13 GPIO_AD_B1_08, active high (moved from K10, see docs/pin-map.md) */

#define TK_INPUT_PIN_MASK ((1u << TK_PIN_ENC_A) | (1u << TK_PIN_ENC_B) | (1u << TK_PIN_ENC_SW) | \
                           (1u << TK_PIN_BTN1) | (1u << TK_PIN_BTN2))

/* NVIC priorities (4 bits implemented, 0 = highest).
 * Every ISR that calls a FreeRTOS ...FromISR() API must have a numeric priority >=
 * configMAX_SYSCALL_INTERRUPT_PRIORITY >> (8 - __NVIC_PRIO_BITS) = 5 (see FreeRTOSConfig.h). */
#define TK_IRQ_PRIO_USB   5u
#define TK_IRQ_PRIO_GPIO  6u

/* Board bring-up, called once from main() before the scheduler starts. */
void board_init(void);
const tk_clock_info_t *board_clock_info(void);

/* Debug UART (LPUART1, 115200 8N1, polled TX; only for boot logs and fault messages). */
void board_uart_puts(const char *s);
void board_uart_puthex(uint32_t v);

/* LED_STAT */
void board_led_set(bool on);

/* Raw GPIO1 input snapshot (bit n = GPIO1_IOn). */
uint32_t board_gpio1_read(void);

/* 64-bit unique ID from OCOTP CFG0/CFG1. */
uint64_t board_unique_id(void);

/* Watchdog (RTWDOG, 32 kHz LPO). */
void board_wdog_start(uint32_t timeout_ms);
void board_wdog_feed(void);

/* Busy-wait delay; only valid before the scheduler starts or in fault handlers. */
void board_delay_us(uint32_t us);

#endif
