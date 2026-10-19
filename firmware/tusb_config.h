/* TokenKey RT - TinyUSB configuration: USB OTG1 device, high speed, one vendor interface. */
#ifndef TUSB_CONFIG_H
#define TUSB_CONFIG_H

#define CFG_TUSB_MCU               OPT_MCU_MIMXRT1XXX
#define CFG_TUSB_OS                OPT_OS_FREERTOS
#define CFG_TUSB_DEBUG             0

#define BOARD_TUD_RHPORT           0 /* USB_OTG1 */
#define CFG_TUSB_RHPORT0_MODE      (OPT_MODE_DEVICE | OPT_MODE_HIGH_SPEED)
#define CFG_TUD_ENABLED            1
#define CFG_TUD_MAX_SPEED          OPT_MODE_HIGH_SPEED

/* Endpoint buffers live in .bss = DTCM (not cached); TinyUSB still does D-cache maintenance
 * for anything outside 0x2000_0000..0x200F_FFFF (ci_hs_imxrt.h). */
#define CFG_TUSB_MEM_SECTION
#define CFG_TUSB_MEM_ALIGN         __attribute__((aligned(32)))

#define CFG_TUD_ENDPOINT0_SIZE     64

#define CFG_TUD_CDC                0
#define CFG_TUD_MSC                0
#define CFG_TUD_HID                0
#define CFG_TUD_MIDI               0
#define CFG_TUD_VENDOR             1
#define CFG_TUD_VENDOR_EPSIZE      512   /* HS bulk; descriptor drops to 64 at FS */
#define CFG_TUD_VENDOR_RX_BUFSIZE  2048
#define CFG_TUD_VENDOR_TX_BUFSIZE  2048

#endif
