# TokenKey RT firmware

FreeRTOS firmware for the i.MX RT1062 (MIMXRT1062DVL6B, alternate CVL5B): XIP from the W25Q64
QSPI flash, USB OTG1 vendor-bulk frame protocol (TinyUSB), SSD1315 OLED, EC11 encoder and two
buttons. Specs: [`docs/firmware_architecture.md`](docs/firmware_architecture.md),
[`docs/usb_protocol.md`](docs/usb_protocol.md), pins in [`../docs/pin-map.md`](../docs/pin-map.md).

Status: **skeleton, builds cleanly, not yet run on hardware** (see [`docs/bringup_checklist.md`](docs/bringup_checklist.md)).

## Layout (flat)

| File | Contents |
|---|---|
| `CMakeLists.txt`, `arm-none-eabi.cmake`, `CMakePresets.json` | build (firmware with the toolchain file, host test without); presets `dvl6b`, `cvl5b`, `recovery-1pad`, `host` |
| `MIMXRT1062_flexspi.ld` | XIP linker script: FCB @0x6000_0000, IVT/boot data @0x6000_1000, code @0x6000_2000, DTCM data/stacks |
| `boot_hdr.c` | FlexSPI NOR config block (W25Q64, quad 1-4-4 0xEB, 50 MHz SDR, **internal loopback** since DQS is NC; `TK_FCB_SINGLE_PAD` recovery variant 1-1-1 0x0B), IVT, boot data |
| `startup.c` | vector table, `Reset_Handler` (FlexRAM ITCM 128K / DTCM 256K / OCRAM 128K), WDOG1/2 + RTWDOG off, .data/.bss, FPU, MPU, I/D cache, fault dump on LPUART1 |
| `board.c/.h` | clocks + DCDC (600/528 MHz), pin mux, LPUART1 log, LED, GPIO, OCOTP, RTWDOG |
| `main.c` | static queues/event group/tasks; `status_task` is the LED + watchdog task |
| `FreeRTOSConfig.h` | kernel config (static allocation only, IRQ priority split) |
| `usb_vendor.c`, `tusb_config.h` | USB PHY/clock init, descriptors, `usb_task` |
| `proto.c/.h` | frame CRC/builder/parser/dispatcher (pure C, host-tested) |
| `oled.c/.h`, `ui.c` | LPI2C1 + SSD1315 driver, 1 KB framebuffer, 5x7 font; `ui_task` screens |
| `input.c` | GPIO1 ISR + `input_task` (quadrature table, debounce, long press) |
| `test_proto.c` | host unit test: CRC-16 check 0x29B1, parser resync, BAD_CRC/BAD_LEN/BAD_VERSION, commands |
| `tools/w25q_status.py` | pyOCD script: read W25Q64 SR1/SR2/SR3 over SWD, check/set QE |
| `docs/bringup_checklist.md` | bring-up steps, QE check, blhost recovery commands with NXP sources |
| `third_party/` | minimal vendored CMSIS core, MIMXRT1062 device headers, TinyUSB 0.20.0, FreeRTOS-Kernel V11.1.0 ([manifest + licenses](third_party/README.md)) |

## Build

Needs `arm-none-eabi-gcc` (tested with Debian `gcc-arm-none-eabi` 14.2.rel1) and CMake >= 3.20
(>= 3.21 for the presets). **Ninja is not required.** The build is generator-agnostic: CMake's
default generator (Unix Makefiles on Linux/macOS) works, and so does `-G Ninja` if you have it.
Always drive the build with `cmake --build`, never `make`/`ninja` directly in docs or scripts.

```sh
cd firmware
cmake -S . -B build -DCMAKE_TOOLCHAIN_FILE=arm-none-eabi.cmake -DTK_PART=DVL6B   # or CVL5B
cmake --build build -j
# -> build/tokenkey_rt.elf, build/tokenkey_rt.bin (raw image of flash from 0x6000_0000), build/tokenkey_rt.hex

# same, explicit generator (either works):
cmake -S . -B build -G "Unix Makefiles" -DCMAKE_TOOLCHAIN_FILE=arm-none-eabi.cmake
cmake -S . -B build-ninja -G Ninja -DCMAKE_TOOLCHAIN_FILE=arm-none-eabi.cmake

# presets (Unix Makefiles): dvl6b, cvl5b, recovery-1pad, host (+ dvl6b-ninja)
cmake --preset cvl5b && cmake --build --preset cvl5b          # -> build-cvl5b/

# host unit test
cmake -S . -B build-host && cmake --build build-host && ctest --test-dir build-host
# or: cmake --preset host && cmake --build --preset host && ctest --preset host
```

Options: `-DTK_PART=DVL6B|CVL5B` (default DVL6B), `-DTK_WATCHDOG=OFF` (bench debugging),
`-DTK_FCB_SINGLE_PAD=ON` (recovery image whose FCB reads 1-1-1, boots with QE=0; see the
bring-up checklist).
No heap: `malloc/calloc/realloc/free` are `--wrap`ped without a definition, so any use fails at link time.

### Clock / part selection (never 600 MHz on a CVL5B)

| Build | OCOTP 0x440[17:16] SPEED_GRADING | Result |
|---|---|---|
| `TK_PART=CVL5B` | ignored | 528 MHz, VDD_SOC 1.225 V (**PM-approved**, inside the CVL5B 1.26 V limit). The 600 MHz path is not compiled in. |
| `TK_PART=DVL6B` | `10` (600 MHz grade) | 1.275 V first, then ARM PLL 1200 MHz / 2 = 600 MHz |
| `TK_PART=DVL6B` | `01` / `00` / `11` | fallback: 528 MHz @ 1.225 V, logged on UART and shown on the splash screen |

Sequence: switch core to the 24 MHz OSC, set DCDC (`DCDC_REG3[TRG]`, 0.8 V + 25 mV/step) and wait
for DC_OK, set AHB /1, IPG /4, ARM_PODF /2, then lock PLL1 and switch back. Voltage is always
set while running at 24 MHz, so it is raised before the frequency goes up. No NXP SDK clock code
is used (`BOARD_BootClockRUN` is never called). FlexSPI and SEMC clock roots are left as the boot
ROM set them. The CVL5B target is a `-DTK_CVL5B_SOC_MV=` define (default 1225 = 1.225 V,
PM-approved, inside the CVL5B 1.26 V limit), range-checked at compile time to 1.15..1.25 V next
to the 528 MHz guard in `board.c`.

Fuse decode, verified against NXP **IMXRT1060RM Rev. 3 (07/2021), chapter 22 Fusemap, section 22.3
"Fusemap Descriptions Table", Table 22-9, p.1301**: OCOTP 0x440[17:16] SPEED_GRADING, burned by
the tester: `00` reserved, `01` 500 MHz (P/N code 05), `10` 600 MHz (P/N code 06), `11` reserved.
(Fetched 2026-10-19 from `https://www.pjrc.com/teensy/IMXRT1060RM_rev3.pdf`, a mirror of the NXP
document.) Only `10` enables 600 MHz; everything else keeps the 528 MHz fallback.

## Flashing

The `.bin` already contains the FCB and IVT; write it to the **start** of the QSPI flash
(0x6000_0000). Use the `.hex`/`.elf` with tools that understand addresses.

### A. ROM serial downloader (no debugger)

1. Hold **SW1 / SW_BOOT** (bottom side) and pulse reset (POR_B: TC2030 pin 3 or TP4), then release
   SW1. Boot pins latch `BOOT_MODE[1:0] = 01` = serial downloader.
2. The ROM enumerates on USB as HID `1FC9:0135` (also listens on LPUART1, TP1/TP2).
3. Either use **NXP MCUXpresso Secure Provisioning Tool** (processor MIMXRT1062, boot device
   *FlexSPI NOR - QuadSPI*, unsigned image, write `tokenkey_rt.bin` at 0x6000_0000), or SPSDK
   `sdphost` + `blhost` by hand. The exact, source-cited commands (including QE setting and a
   single-pad fallback) are in [`docs/bringup_checklist.md`](docs/bringup_checklist.md) step F2.
   Short form:
   ```sh
   sdphost -u 0x1fc9,0x0135 -- write-file 0x20000000 ivt_flashloader.bin
   sdphost -u 0x1fc9,0x0135 -- jump-address 0x20000400
   blhost -u -- fill-memory 0x2000 4 0xC0000402 word   # SFDP quad, QE = SR2[1] via 0x31, 50 MHz
   blhost -u -- configure-memory 0x9 0x2000
   blhost -u -- flash-erase-region 0x60000000 0x100000
   blhost -u -- write-memory 0x60000000 build/tokenkey_rt.bin
   ```
4. Power-cycle or pulse reset without SW1: `BOOT_MODE = 10`, internal boot from FlexSPI.

### B. SWD via TC2030-NL (J3: 1 VCC, 2 SWDIO, 3 nRESET, 4 SWCLK, 5 GND, 6 SWO)

- pyOCD: `pyocd flash -t mimxrt1060 build/tokenkey_rt.hex` (its QSPI algorithm is generic SFDP; verify on W25Q64).
- J-Link: device `MIMXRT1062xxx6B`, `loadfile build/tokenkey_rt.hex`, QSPI flash loader.
- OpenOCD: debug/attach only (no FlexSPI flash driver upstream); load to flash with A or J-Link/pyOCD.
- SWO is on G13 (GPIO_AD_B0_10, JTAG_TDO) and is never remuxed by the firmware.

**Never blow `BT_FUSE_SEL`** (factory policy, `docs/firmware_architecture.md` 5.1). The board
relies on the BOOT_CFG pin straps (internal pull-downs, FlexSPI NOR) and on the SW1
serial-downloader recovery path; moving boot configuration into eFuses is irreversible. The
firmware never drives GPIO_AD_B0_04/05 (BOOT_MODE0/1).

## Tasks and data flow (FreeRTOS)

| Task | Prio | Stack (words) | Does | Blocks on |
|---|---|---|---|---|
| `usb_task` | 4 | 1024 | `tud_task_ext()`, bulk OUT -> `proto_parser_feed()` -> `proto_handle()` -> bulk IN; sends EVT_MODE/EVT_BUTTON | TinyUSB event queue (20 ms) |
| `input_task` | 3 | 256 | encoder quadrature decode, 20 ms button debounce, 800 ms long press | `q_input_raw` (100 ms idle, 1 ms while active) |
| `ui_task` | 2 | 512 | splash, mode screen, encoder/BTN mode selection | `q_ui` (100 ms) |
| `status_task` | 1 | 256 | **the LED + watchdog task**: LED_STAT patterns and the only RTWDOG feed | 20 ms period |
| idle | 0 | 128 | kernel | - |

IRQs: USB_OTG1 priority 5, GPIO1_16_31 priority 6; both `>= configMAX_SYSCALL_INTERRUPT_PRIORITY` (5),
kernel at 15. All kernel objects are static (`configSUPPORT_DYNAMIC_ALLOCATION 0`, no heap).

```
 GPIO1 IRQ (ENC_A/B, ENC_SW, BTN1, BTN2)
        | uint32 PSR snapshot, xQueueSendFromISR
        v
   q_input_raw --> [input_task] --tk_ui_msg(INPUT)--> q_ui --> [ui_task] --> OLED (LPI2C1)
                                                        ^          |
          tk_ui_msg(MODE_FROM_HOST, USB_STATE)          |          | tk_usb_msg(MODE_FROM_DEVICE, BUTTON)
                                                        |          v
 USB OTG1 IRQ --> TinyUSB --> [usb_task] <-------------------- q_usb
                                  |  frames <-> host (bulk 0x01/0x81)
                                  |
          q_led (ON/OFF/PULSE) <--+--> [status_task] --> LED_STAT
                                           ^
   event group wd: WD_BIT_USB | WD_BIT_INPUT | WD_BIT_UI  (each task sets its bit every loop)
```

`status_task` is the LED + watchdog task: it owns LED_STAT and is the only code that feeds the
watchdog. Watchdog: `status_task` checks the event group every 500 ms and feeds RTWDOG (2 s timeout, 32 kHz
LPO, halted while a debugger holds the core) only if all three bits are set, then clears them.
A stuck task stops the feed and the chip resets.

LED_STAT: off = not enumerated, on = enumerated, short inverted pulse = frame received.
UI: rotate = highlight mode, ENC_SW = apply, BTN1 = next mode, BTN2 = cancel highlight.
Mode changes from the host (SET_MODE) show on the OLED; local changes go to the host as EVT_MODE (0x62).

## USB protocol (implemented subset)

VID/PID: **DEV ONLY**, defined once as `TK_USB_VID` / `TK_USB_PID` in `usb_vendor.c` (the single
to-do for replacing them is marked there, nowhere else). Interface class 0xFF, bulk OUT 0x01 / IN 0x81, 512 B HS / 64 B FS.
Linux udev example: use the hex values of `TK_USB_VID`/`TK_USB_PID`:
`SUBSYSTEM=="usb", ATTR{idVendor}=="<vid>", ATTR{idProduct}=="<pid>", MODE="0666"`.

Implemented: HELLO (15-byte reply), PING (<= 64 B echo), GET_INFO (TLV serial/build id/flash
size/uptime), SET_MODE, GET_MODE, ERROR replies (BAD_CRC, BAD_LEN, BAD_VERSION, BAD_PARAM,
UNKNOWN_CMD), events EVT_BUTTON/EVT_MODE. JOB_*, GET_STATS, RESET_STATS and ENTER_BOOTLOADER
return `ERROR UNKNOWN_CMD` with detail `0x0001` (not implemented yet).

## Bring-up checklist

Moved to [`docs/bringup_checklist.md`](docs/bringup_checklist.md): UART banner and VDD_SOC
checks, W25Q64 SR2 (0x35) QE=1 check, ROM SDP + flashloader recovery (quad with QE setting, and
a single-pad fallback), MCUXpresso Secure Provisioning path, USB/UI/watchdog checks.

## Flash notes

- W25Q64JV quad read needs status register 2 `QE = 1` (bit 1). The `-IQ` parts ship with QE=1;
  check with `tools/w25q_status.py` and set it via the flashloader option word (checklist F2).
- Internal loopback sampling limits the read clock. 50 MHz is a conservative choice; 60 MHz is the
  usual ceiling.
