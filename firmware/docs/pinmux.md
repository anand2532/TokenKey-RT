# TokenKey RT - pin mux vs. merged schematic

Checked 2026-10-21 (IST) against `main` a790a43: netlist exported with
`kicad-cli sch export netlist hardware/schematic/TokenKey-RT.kicad_sch` (KiCad 9), plus the
`U1` pad nets in `hardware/schematic/TokenKey-RT.kicad_pcb` (all 26 signal balls listed in
`docs/pin-map.md` carry the same net on the PCB; 196/196 U1 pads present), and
`docs/pin-map.md`. Firmware: `board.c` `pinmux_init()`, `board.h` `TK_PIN_*`, `boot_hdr.c`.

**Result: no net-to-pad mismatch** between schematic, PCB, `docs/pin-map.md` and firmware.
Findings fixed on this branch (see bottom): FCB read sampling vs. the floating DQS pad, FCB
quad-read mode byte, and a floating UART RX.

| Ball | Pad | Net | Other nodes on net | Firmware mux / function | Pad config | Where | Status |
|---|---|---|---|---|---|---|---|
| F11 | GPIO_AD_B0_04 | BOOT_MODE0 | R22.2, R7.1 | BOOT_MODE0 strap, never driven | untouched | - | OK |
| G14 | GPIO_AD_B0_05 | BOOT_MODE1 | Q1.1, R6.1, SW1.1 | BOOT_MODE1 strap, never driven | untouched | - | OK |
| K12 | GPIO_AD_B1_05 | BTN1 | R19.2, SW3.1 | ALT5 GPIO1_IO21 in, active low | HYS, no pull (ext 10k) | board.c, TK_PIN_BTN1 | OK |
| J12 | GPIO_AD_B1_06 | BTN2 | R20.2, SW4.1 | ALT5 GPIO1_IO22 in, active low | HYS, no pull (ext 10k) | board.c, TK_PIN_BTN2 | OK |
| L11 | GPIO_AD_B1_02 | ENC_A | C52.1, R16.2, SW2.A | ALT5 GPIO1_IO18 in | HYS, no pull (ext 10k + 10nF) | board.c, TK_PIN_ENC_A | OK |
| M12 | GPIO_AD_B1_03 | ENC_B | C53.1, R17.2, SW2.B | ALT5 GPIO1_IO19 in | HYS, no pull (ext 10k + 10nF) | board.c, TK_PIN_ENC_B | OK |
| L12 | GPIO_AD_B1_04 | ENC_SW | R18.2, SW2.S1 | ALT5 GPIO1_IO20 in, active low | HYS, no pull (ext 10k) | board.c, TK_PIN_ENC_SW | OK |
| L3 | GPIO_SD_B1_06 | FLASH_CS | R8.2, U4.1 | ALT1 FLEXSPIA_SS0_B | boot ROM | FCB (boot_hdr.c) | OK |
| P3 | GPIO_SD_B1_08 | FLASH_IO0 | U4.5 | ALT1 FLEXSPIA_DATA00 | boot ROM | FCB | OK |
| N4 | GPIO_SD_B1_09 | FLASH_IO1 | U4.2 | ALT1 FLEXSPIA_DATA01 | boot ROM | FCB | OK |
| P4 | GPIO_SD_B1_10 | FLASH_IO2 | U4.3 | ALT1 FLEXSPIA_DATA02 | boot ROM | FCB | OK |
| P5 | GPIO_SD_B1_11 | FLASH_IO3 | U4.7 | ALT1 FLEXSPIA_DATA03 | boot ROM | FCB | OK |
| F13 | GPIO_AD_B0_08 | JTAG_MOD | R5.1 | JTAG_MOD (R5 1k to GND) | untouched | - | OK |
| H13 | GPIO_AD_B1_08 | LED_STAT | R21.1 | ALT5 GPIO1_IO24 out, active high (R21 1k -> D1 anode, cathode GND) | keeper, push-pull | board.c, TK_PIN_LED | OK |
| J11 | GPIO_AD_B1_00 | OLED_SCL | J2.3, R14.2 | ALT3 LPI2C1_SCL, SION, daisy LPI2C1_SCL_SELECT_INPUT=1 | open drain, HYS, no pull (ext 4.7k) | board.c pinmux_init | OK |
| K11 | GPIO_AD_B1_01 | OLED_SDA | J2.4, R15.2 | ALT3 LPI2C1_SDA, SION, daisy LPI2C1_SDA_SELECT_INPUT=1 | open drain, HYS, no pull (ext 4.7k) | board.c | OK |
| M6 | ONOFF | ONOFF | TP5.1 | ONOFF (internal 100k PU) | - | - | OK |
| M7 | POR_B | POR_B | C48.1, J3.3, R4.2, TP4.1 | POR_B | - | - | OK |
| H2 | GPIO_SD_B0_04 | PSRAM_CS | R10.2, U5.1 | PSRAM (DNP) FLEXSPIB_SS0_B, not used by firmware | reset default | - | OK |
| M4 | GPIO_SD_B1_03 | PSRAM_IO0 | U5.5 | PSRAM (DNP) FLEXSPIB_DATA00, not used | reset default | - | OK |
| M3 | GPIO_SD_B1_02 | PSRAM_IO1 | U5.2 | PSRAM (DNP) FLEXSPIB_DATA01, not used | reset default | - | OK |
| M5 | GPIO_SD_B1_01 | PSRAM_IO2 | U5.3 | PSRAM (DNP) FLEXSPIB_DATA02, not used | reset default | - | OK |
| L5 | GPIO_SD_B1_00 | PSRAM_IO3 | U5.7 | PSRAM (DNP) FLEXSPIB_DATA03, not used | reset default | - | OK |
| L4 | GPIO_SD_B1_07 | QSPIA_SCLK | R9.1 | ALT1 FLEXSPIA_SCLK | boot ROM | FCB | OK |
| P2 | GPIO_SD_B1_04 | QSPIB_SCLK | R11.1 | PSRAM (DNP) FLEXSPIB_SCLK, not used | reset default | - | OK |
| N9 | RTC_XTALI | RTC_XTALI | C46.1, Y2.1 | RTC_XTALI 32.768 kHz | - | - | OK |
| P9 | RTC_XTALO | RTC_XTALO | C47.1, Y2.2 | RTC_XTALO | - | - | OK |
| F12 | GPIO_AD_B0_07 | SWCLK | J3.4 | ALT0 JTAG_TCK/SWCLK (reset default) | untouched | - | OK |
| E14 | GPIO_AD_B0_06 | SWDIO | J3.2 | ALT0 JTAG_TMS/SWDIO (reset default) | untouched | - | OK |
| G13 | GPIO_AD_B0_10 | SWO | J3.6 | ALT0 JTAG_TDO/SWO (reset default) | untouched | - | OK |
| L14 | GPIO_AD_B0_13 | UART_RX | TP2.1 | ALT2 LPUART1_RX (no daisy on RT1060) | **100k pull-up (new)**, HYS | board.c | OK |
| K14 | GPIO_AD_B0_12 | UART_TX | TP1.1 | ALT2 LPUART1_TX | keeper, push-pull | board.c | OK |
| M8 | USB_OTG1_DN | USB_DN | J1.A7, J1.B7, U6.3, U6.4 | USB_OTG1_DN | analog | usb_vendor.c | OK |
| L8 | USB_OTG1_DP | USB_DP | J1.A6, J1.B6, U6.1, U6.6 | USB_OTG1_DP | analog | usb_vendor.c | OK |
| N6 | USB_OTG1_VBUS | VBUS | C1.1, C26.1, C3.1, C51.1, J1.A4, J1.A9, J1.B4, J1.B9, U2.1, U2.3, U3.1, U3.4, U6.5 | USB_OTG1_VBUS | analog | usb_vendor.c | OK |
| P11 | XTALI | XTALI | C44.1, Y1.1 | XTALI 24 MHz | - | board.c clock_init | OK |
| N11 | XTALO | XTALO | C45.1, Y1.3 | XTALO | - | - | OK |
| N3 | GPIO_SD_B1_05 | unconnected-(U1E-GPIO_SD_B1_05-PadN3) | - | ALT1 FLEXSPIA_DQS (set by ROM when readSampleClkSrc=1) | floating, NC on board | FCB readSampleClkSrc=1 | OK |

All other U1 signal balls are `unconnected-*` in the netlist (no-connect flags) and stay at reset
defaults. Power/analog balls (VDD_*, NVCC_*, DCDC_*, VSS) are not mux-controlled and were not
re-checked here (see `docs/pin-map.md`).

## Flash wiring (U4 W25Q64JVSSIQ, SOIC-8)

| U4 pin | Function | Net | MCU ball |
|---|---|---|---|
| 1 | /CS | FLASH_CS (R8 10k to 3V3) | L3 GPIO_SD_B1_06 |
| 2 | DO (IO1) | FLASH_IO1 | N4 GPIO_SD_B1_09 |
| 3 | /WP (IO2) | FLASH_IO2 | P4 GPIO_SD_B1_10 |
| 4 | GND | GND | - |
| 5 | DI (IO0) | FLASH_IO0 | P3 GPIO_SD_B1_08 |
| 6 | CLK | FLASH_CLK = QSPIA_SCLK via R9 22R | L4 GPIO_SD_B1_07 |
| 7 | /HOLD (IO3) | FLASH_IO3 | P5 GPIO_SD_B1_11 |
| 8 | VCC | 3V3 | - |

IO0..IO3 order matches FlexSPIA DATA00..03 and the W25Q64JV pinout, so 1-4-4 quad read works
once QE=1 (/WP and /HOLD become IO2/IO3). DQS (N3) is unconnected.

## FCB / IVT review (`boot_hdr.c`)

| Item | Before | After | Why |
|---|---|---|---|
| readSampleClkSrc | 0 internal loopback | **1 loopback from DQS pad** | N3 is floating on the board for exactly this; RM Rev.3 s27.3.15.2 (p.1647): higher frequency than internal loopback, for devices without read strobe. Teensy 4.1 (same W25Q64JV) uses 1. |
| Quad read LUT | 0xEB, RADDR 24 @4, DUMMY 6 @4, READ | **0xEB, RADDR 24 @4, MODE8 0xFF @4, DUMMY 4 @4, READ** | The 2 mode-byte clocks were undriven; W25Q64JV enters continuous-read mode if M5-4 = 10b. Driving 0xFF is deterministic (Teensy 4.1 bootdata.c LUT words 0x0A1804EB/0x32041EFF). |
| serialClkFreq | 2 (50 MHz) | 2 (50 MHz) | kept conservative for bring-up; DQS loopback allows more later |
| QE | not set by FCB | unchanged | QE (SR2[1]) is non-volatile: set once by the flashloader option 0xC0000402 or `tools/w25q_status.py --set-qe` (bring-up checklist F); `-IQ` ships with QE=1. Writing it from the FCB at every boot would wear the status register. |
| Sizes | 8 MB A1, page 256, sector 4K, block 64K | unchanged | W25Q64JV |
| Other LUTs | 0x05 RDSR1, 0x06 WREN, 0x20/0xD8 erase, 0x02 PP, 0x60 chip erase | unchanged | single-pad, ROM sequence indices 1/3/5/8/9/11 |
| IVT / boot data | 0x412000D1, entry = vector table, boot data 0x6000_0000 / 8 MB | unchanged | |
| Recovery FCB (TK_FCB_SINGLE_PAD) | 0x0B 1-1-1, 8 dummy | unchanged (sample clock also 1) | |

## Other finding

- L14 UART_RX goes only to TP2 (no external pull): enabled the internal 100k pull-up so the
  idle line is defined when no adapter is attached.

Nothing here has been verified on hardware.
