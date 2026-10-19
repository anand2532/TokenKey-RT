# TokenKey RT — Design Decisions

- **Date:** 2026-10-19
- **Owner:** TokenKey PM

## Current decisions

| Area | Decision |
|------|----------|
| MCU (primary) | MIMXRT1062DVL6B, 10x10 mm BGA |
| MCU (alternate) | MIMXRT1062CVL5B, pending ball-map confirmation |
| BGA fanout | Advanced via rules: about 0.2 mm drill / 0.45 mm pad |
| Boot flash | W25Q64JVSSIQ |
| External RAM | No SDRAM; QSPI PSRAM on FlexSPI B as a DNP option |
| 3.3 V supply | AP2112K-3.3 LDO, with footprint room for a buck regulator later |
| Core supply | RT1062 internal DCDC |
| USB | USB-C TYPE-C-31-M-12, 5.1k Rd on CC1/CC2, USBLC6-2SC6 ESD protection |
| Display | I2C OLED module (128x64 preferred) |
| RTC clock | 32.768 kHz crystal |
| Debug | Tag-Connect TC2030 for SWD, plus UART console pads |
| Boot button | Bottom side of the PCB |
| KiCad project location | 2026-10-19, TokenKey PM: the whole KiCad project (`TokenKey-RT.kicad_pro`, `.kicad_sch` plus sub-sheets, `.kicad_pcb`, `.kicad_dru`) lives in `hardware/schematic/`, because KiCad only links the `.kicad_sch` and `.kicad_pcb` that sit next to the `.kicad_pro`. `hardware/pcb/` removed. |

All items remain subject to engineering verification per [baseline spec section 8](baseline-specs.md#8-design-constraints).
