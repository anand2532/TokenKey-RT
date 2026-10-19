# TokenKey RT — Firmware Architecture (draft v0.1)

## 1. Hardware baseline (from TokenKey PM)
- MCU: MIMXRT1062DVL6B (10x10 BGA196, 600 MHz). Alternate: MIMXRT1062CVL5B (528 MHz max, VDD_SOC_IN <= 1.26 V).
- Boot: FlexSPI A (primary pin group), W25Q64 QSPI NOR (8 MB), XIP.
- USB OTG1 = device port. LPUART1 = debug console. SWD + SWO.

| Signal | Ball | Pad (verified by TokenKey Schematic vs IMXRT1060CEC Rev.4 Table 83) | Mux |
|---|---|---|---|
| OLED SCL | J11 | GPIO_AD_B1_00 | ALT3 LPI2C1_SCL (+SION) |
| OLED SDA | K11 | GPIO_AD_B1_01 | ALT3 LPI2C1_SDA (+SION) |
| ENC_A | L11 | GPIO_AD_B1_02 (GPIO1_IO18) | ALT5 GPIO |
| ENC_B | M12 | GPIO_AD_B1_03 (GPIO1_IO19) | ALT5 GPIO |
| ENC_SW | L12 | GPIO_AD_B1_04 (GPIO1_IO20) | ALT5 GPIO |
| BTN1 | K12 | GPIO_AD_B1_05 (GPIO1_IO21) | ALT5 GPIO |
| BTN2 | J12 | GPIO_AD_B1_06 (GPIO1_IO22) | ALT5 GPIO |
| LED | K10 | GPIO_AD_B1_07 (GPIO1_IO23) | ALT5 GPIO |
| UART TX | K14 | GPIO_AD_B0_12 | ALT2 LPUART1_TX |
| UART RX | L14 | GPIO_AD_B0_13 | ALT2 LPUART1_RX |
| SWO | G13 | GPIO_AD_B0_10 | ALT0 ARM_TRACE_SWO (JTAG_TDO) |

All pin numbers live in one file (`board/pin_mux.c`, `board/board.h`) so a corrected map is a one-file change. Option: ENC_A/B via XBAR→QDC instead of GPIO IRQ (open question).

## 2. Layers
```
app/ui        screens, menus, mode select, stats view
core/         ctx engine (ringbuf, xxhash, dupset, classify, rank, budget, stats) — pure C, host-testable
proto/        USB frame parser/builder, command dispatch
drivers/      usb_dev (vendor bulk), oled_ssd1306 (LPI2C1), input (enc+btn), wdog (RTWDOG), uart_log
board/        clock + part detection, pin_mux, MPU/cache, FlexSPI FCB/IVT
```
Rules: core has no hardware includes; static allocation only (no malloc/new, `-Wl,--wrap=malloc` trap to fail link); all buffers fixed-size with compile-time caps.

### 2.1 Board / clock / part detection
- Read part speed grade from OCOTP fuse (OCOTP->CFG3 / MISC_CONF speed-grade bits; exact field TBD from fuse map) before any clock change. Build option `TK_FORCE_PART=DVL6B|CVL5B` overrides; on unknown/mismatch → choose 528 MHz (safe).
- DVL6B: SDK flow DCDC → 1.275 V, ARM PLL 1200 MHz /2 = 600 MHz.
- CVL5B: DCDC target ≤ 1.250 V (≤1.26 V limit), ARM PLL 1056 MHz /2 = 528 MHz. SDK `BOARD_BootClockRUN` (600 MHz) is never called; we own `clock_config_528.c` and `clock_config_600.c`, selected by `board_clock_init(part)`.
- Order: always raise voltage before frequency, lower frequency before voltage.
- Assert at boot: read back DCDC_REG3 TRG and core freq; log over LPUART1; halt into safe mode if out of spec.

### 2.2 Drivers
- **USB**: OTG1 device, HS (FS fallback), vendor class: 1 interface, bulk IN/OUT 512 B (64 B FS). Built on MCUXpresso USB stack (static memory config). See usb_protocol.md.
- **OLED**: SSD1306/SH1106 128x64 on LPI2C1 @ 400 kHz; 1 KB framebuffer in DTCM, dirty-page flush via LPI2C EDMA, max ~20 fps.
- **Input**: encoder quadrature state table (GPIO edge IRQ, or QDC); buttons sampled 1 kHz from PIT/SysTick, 20 ms debounce, long-press 800 ms; events into 16-entry event queue.
- **Watchdog**: RTWDOG, unlock by writing 0xD928C520 to CNT (32-bit; or 0xC520,0xD928 for 16-bit), refresh by writing 0xB480A602 (or 0xA602,0xB480). Timeout 2 s, window off. Fed only from main loop after all tasks report alive (task-check bitmask). WDOG1/2 disabled at boot.
- **UART log**: LPUART1 115200 8N1, 2 KB TX ring, non-blocking, drops on full.

### 2.3 Core: context processing
- **Ring buffers**: SPSC lock-free, power-of-2 size; USB RX ring 32 KB, chunk records 16 KB metadata.
- **Streaming xxHash**: XXH32 (Cortex-M7 friendly) per chunk/line, streaming state 48 B; XXH64 optional.
- **Dup hash set**: open addressing, linear probe, fixed 8192 slots × 8 B (hash32 + chunk id), load cap 75%; when full, further items are not deduped (counted in stats), never evicted mid-session.
- **Classification**: line-oriented scanner: detects `diff --git`/`+++`/`---` headers (changed-file IDs), fenced code blocks (``` / ~~~ with info string), prose, logs. Each segment → {type, file_id, offset, len, hash, score}.
- **Ranking**: score = type weight (changed-file > fenced code > error log > prose) + recency + reference count − dup penalty; integer math only.
- **Budget**: mode sets keep ratio of input tokens: Economy 25%, Balanced 50%, Quality 85%. Token estimate = bytes/4 (configurable). Greedy select by score/size until budget; output keeps original order.
- **Stats**: bytes in/out, est. tokens in/out, dup hits, segments by type, set-full drops, time per job (DWT cycle counter).
- Max segments per job: 4096 (fixed array). Exceeding → error CTX_OVERFLOW.

### 2.4 UI
Home (mode + last savings %), Mode select (encoder rotate, SW confirm), Stats, Device info (part, MHz, fw ver). BTN1 = cycle mode, BTN2 = back/cancel job. LED: off idle, solid connected, blink busy, fast blink fault.

## 3. Memory map
| Region | Size | Use |
|---|---|---|
| FlexSPI 0x6000_0000 | 8 MB | FCB @0x0, IVT @0x1000, app A @0x2000.., app B slot @0x40_0000 (optional), config sector last 64 KB |
| ITCM 0x0000_0000 | 128 KB | vector table, ISRs, hot core loops (xxhash, scanner, dupset) |
| DTCM 0x2000_0000 | 256 KB | stack (8 KB main), .data/.bss, dupset (64 KB), segment table, framebuffer |
| OCRAM 0x2020_0000 | 128 KB | USB DMA buffers + RX/TX rings (non-cacheable MPU region), EDMA descriptors |
FlexRAM split via GPR17/GPR16 set at startup (FCB/DCD not needed): ITCM 128 / DTCM 256 / OCRAM 128 (+ dedicated 512 KB OCRAM2 at 0x2020_0000 range for large rings; adjust). D-cache on; USB buffers in non-cacheable region.

## 4. Task / ISR model
Bare-metal superloop + ISRs (no RTOS initially).
| Priority | Source | Work |
|---|---|---|
| 1 (highest) | USB OTG1 | move packets ↔ rings only |
| 2 | LPI2C/EDMA | OLED transfer completion |
| 3 | GPIO (encoder) | quadrature step → event queue |
| 4 | PIT 1 kHz | button scan, timeouts, tick |
| 5 | LPUART | log drain |
Main loop: proto_poll → ctx_step (bounded slices ≤ 2 ms) → ui_step → oled_flush → wdog_check_and_feed. ISRs never call core.

## 5. Boot / recovery flow
1. ROM boots FlexSPI A (BOOT_CFG fuses / pins), reads FCB+IVT, XIP.
2. Reset handler: disable WDOG1/2, config RTWDOG 2 s, FlexRAM, MPU/cache.
3. Detect part → clock init (528/600). Log reset cause (SRC_SRSR): if RTWDOG reset count ≥ 3 in a row (counter in SNVS GPR) → safe mode (no ctx engine, USB recovery only).
4. Init UART, OLED (splash), input, USB.
5. Recovery: hold BTN1+BTN2 at power-on → safe mode; firmware update via USB uses ROM Serial Downloader (BOOT_MODE=01 via boot button, see 5.1) or in-app updater writing slot B + CRC check + swap flag. Last-resort: SWD.

### 5.1 Boot strap circuit (final, from TokenKey Schematic)
BOOT_MODE1 = GPIO_AD_B0_05 (G14): 10k pull-up, button to GND. BOOT_MODE0 = GPIO_AD_B0_04 (F11): 10k pull-down, driven high via P-MOSFET + 1k while button held. Released = 10 (FlexSPI boot); held = 01 (serial downloader). Enter SDP: hold button, pulse reset. Firmware must leave AD_B0_04/05 as inputs or unused and never drive them. Factory policy: never blow BT_FUSE_SEL.

## 6. Open questions
1. ~~Ball→pad map~~ verified. Board pull-ups: I2C 4.7k; ENC A/B 10k+10nF; SW/BTN 10k active-low; LED active-high via 1k. Do not remux G13 (SWO).
2. OCOTP field for speed grade; or rely on per-build part selection?
3. Encoder via GPIO IRQ or QDC/XBAR?
4. OLED controller (SSD1306 vs SH1106) and I2C address.
5. In-app A/B update vs ROM SDP only? Image signing (HAB) required?
6. Token estimator: bytes/4 vs on-device tokenizer table.
7. Is the Linux companion app existing or new (affects protocol freedom)?
8. BOOT_MODE/BOOT_CFG strapping on board; USB HS PHY routing and VBUS detect.
