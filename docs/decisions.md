# TokenKey RT — Design Decisions

- **Date:** 2026-10-19
- **Owner:** TokenKey PM

## Current decisions

| Area | Decision |
|------|----------|
| MCU (primary) | MIMXRT1062DVL6B, 10x10 mm BGA |
| MCU (alternate) | MIMXRT1062CVL5B, pending ball-map confirmation |
| BGA fanout | 2026-10-19, TokenKey PM: BGA via 0.15 mm drill / 0.30 mm pad; JLC small-via surcharge accepted. |
| Netclasses | 2026-10-19, TokenKey PM: Default 0.15/0.15 mm; Power 0.40 mm trunk / 0.30 mm branch; standard via 0.6/0.3 mm; USB_HS 0.155/0.20 mm (90 ohm differential). |
| Board | 2026-10-19, TokenKey PM: 50x40 mm; OLED on a header over parts no taller than 2.0 mm (PM, 2026-10-19; was 2.5 mm). |
| Boot flash | W25Q64JVSSIQ |
| External RAM | No SDRAM; QSPI PSRAM on FlexSPI B as a DNP option |
| 3.3 V supply | AP2112K-3.3 LDO, with footprint room for a buck regulator later |
| Core supply | RT1062 internal DCDC |
| USB | USB-C TYPE-C-31-M-12, 5.1k Rd on CC1/CC2, USBLC6-2SC6 ESD protection |
| USB-C placement | 2026-10-19, TokenKey PM: USB-C on the south long edge. |
| Display | I2C OLED module (128x64 preferred) |
| RTC clock | 32.768 kHz crystal |
| Debug | Tag-Connect TC2030 for SWD, plus UART console pads |
| Boot button | Bottom side of the PCB |
| KiCad project location | 2026-10-19, TokenKey PM: the whole KiCad project (`TokenKey-RT.kicad_pro`, `.kicad_sch` plus sub-sheets, `.kicad_pcb`, `.kicad_dru`) lives in `hardware/schematic/`, because KiCad only links the `.kicad_sch` and `.kicad_pcb` that sit next to the `.kicad_pro`. `hardware/pcb/` removed. |
| VDD_SOC decoupling (C11, C12 kept) | 2026-10-19, PM review of PR #10: keep both 4.7uF caps C11 and C12 on VDD_SOC. NXP MIMXRT105060HDUG Rev 3 (07/2019), Table 3 "Power sequence and recommendations", on-chip DC/DC item: "the external buck capacitor total is about 33uF, this includes all the capacitors used on DCDC_OUT and VDD_SOC_IN". VDD_SOC total = C6-C10 (5 x 0.22uF) + C11 + C12 (2 x 4.7uF) + C13 (22uF) = 1.1 + 9.4 + 22 = 32.5uF nominal (about 33uF). HDG Table 2 lists 5 x 0.22uF + 1 x 4.7uF + 1 x 22uF; the second 4.7uF brings the total to the 33uF guidance. |
| Spend gate | 2026-10-19 (Anand): schematic and layout continue; no fab, assembly, enclosure or parts spend until the PoC gates G1-G5 pass. |
| OLED back-side 1.0 mm feature (issue #32) | From HS datasheet V1.0 sec. 1.4 side view (page 6, printed rotated; read upright at 600 dpi; no back view exists on the sheet). Axes: origin header pin 1, +x toward pin 4, +y from header toward glass. The 1.00 mm dimension refers to an unlabelled rectangle on the PCB back, protruding 1.00 mm, spanning y = 10.8 ... 13.8 mm from the header-side PCB edge, i.e. **+9.3 ... +12.3 mm from pin 1 (about 3.0 mm long in y)**, measured against the front view scale (glass top 4.87 and glass bottom 21.77 mm reproduce within 0.05 mm; side-view PCB is drawn about 1.8 mm short, so take +/-0.3 mm). **Its x position and x width are not shown anywhere on the drawing (unresolved).** Identity not stated: it is not the FPC bend (the FPC wraps from the glass ledge at y 21.8 mm to the PCB *front* at the bottom edge, pads 14.50 wide) and not the driver IC (SSD1315 is COG on the glass ledge, front, y 18.7-21.8 mm); most likely a back-side component (e.g. regulator/passive) or stiffener, unconfirmed. Also drawn: a thin (~0.1 mm) undimensioned outline on the back at y ~18.7-25.6 mm from the header edge, unidentified. Treat the whole back as up to 1.0 mm tall until a physical sample is measured. |
| DCDC inductor L2 (issue #24) | 2026-10-19, Layout via PM: L2 changed from SWPA4020S4R7MT (4x4x2.0 mm) to **TDK VLS3015CX-4R7M-1** (LCSC C3220938): 4.7uH +/-20% at 1 MHz, 3.0x3.0x1.5 mm max, DCR 0.114 typ / 0.137 ohm max, Isat (30% L drop) 1.37 A max-rated / 1.52 A typ, Itemp 1.67 A, -40 to 105 C (TDK product center page and VLS3015CX-1 catalog 20200312). Alternate **Sunlord SWPA3015S4R7MT** (LCSC/JLC C19398, JLC Extended): 3.0x3.0x1.5 mm max, DCR 0.125 typ / 0.163 ohm max, Isat 1.10 A rated / 1.40 A typ, Irms 1.09 A (Sunlord SWPA datasheet rev 2022/05/15). Both meet HDG Table 3 (4.7-10uH, Isat >1 A, DCR <0.2 ohm). Footprint `TokenKey:L_3.0x3.0mm_TDK_VLS3015CX`: two 1.0 x 3.0 mm pads at x = +/-1.0 mm (1.0 mm gap, 3.0 mm outer span) = TDK recommended land; Sunlord terminals (E 0.75 mm, F gap 1.5 mm) land fully on it. Courtyard 3.7 x 3.7 mm. No 4.7uH part <=1.5 mm tall with DCR <=0.10 ohm max was found in LCSC stock; VLS3015CX-4R7M-H (C2683181, 0.120 ohm max, Isat 1.15 A) has a different land (TDK A/B/C 1.60/0.80/3.00) and only 610 in stock. |
| OLED HS96L03W2C03 mechanicals (issue #24) | From HS datasheet V1.0 sec. 1.4 Mechanical Drawing (page 6, printed rotated 90 deg; read after rotating upright) and sec. 1.1. Origin = header pin 1 (GND, square pad), +x toward pin 4 (SDA), +y from the header edge toward the glass. PCB 27.30 (x) x 27.80 (y); pin 1 at 9.84 mm from the left PCB edge (header centred: (27.30-7.62)/2) and 1.44 mm from the header-side edge; pitch 2.54, 4 pins. Glass (LCD) 24.74 x 16.90 mm: top edge 4.87 mm from the header-side PCB edge, so +3.43 mm from pin 1 in y; glass x edges -8.60 / +16.14 from pin 1 (from the 1.32 mm right-edge dim; centred would be -8.56 / +16.18). Active area 21.744 x 10.864 mm (VA 22.74 x 11.86): AA bottom edge 10.57 mm from the far PCB edge, so AA y = +4.93 ... +15.79 from pin 1; AA x about -7.06 ... +14.68 from pin 1 (x NOT dimensioned; assumes AA centred, consistent with the drawing). Mounting holes dia 2.50 (pad dia 3.00) at 2.00 mm from edges, pitch 23.30 x 23.80. FPC bend 14.50 wide at the far edge. Thickness: 2.65 mm (sec. 1.1 PCB size 27.3 x 27.8 x 2.65); side view shows glass stack 1.40, PCB 1.20 and a 1.00 mm back-side feature, so allow ~3.6 mm envelope (1.00 interpretation unconfirmed). Header height: NOT given in the datasheet (the drawing shows bare holes); measure the supplied part or set by the chosen header. |

All items remain subject to engineering verification per [baseline spec section 8](baseline-specs.md#8-design-constraints).
