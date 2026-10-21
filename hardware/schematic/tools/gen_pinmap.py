#!/usr/bin/env python3
import sys
if __name__ == '__main__':
    sys.exit("tools/gen_pinmap.py is DEPRECATED (issue #26). It needs tools/netlist.json from the deprecated gen.py. "
             "docs/pin-map.md is now a frozen snapshot; update it by hand alongside schematic pin-mux changes.")
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = HERE   # repo root (or draft root): first ancestor that contains hardware/schematic
while not os.path.isdir(os.path.join(ROOT, 'hardware', 'schematic')) and os.path.dirname(ROOT) != ROOT: ROOT = os.path.dirname(ROOT)
B = json.load(open(os.path.join(HERE, 'rt1062_10x10_balls.json'))); func = B['func']
MUX = {  # pad -> (function / mux, notes, source)
 'GPIO_SD_B1_06': ('ALT1 FLEXSPIA_SS0_B', '10k PU (R8); boot ROM default', 'DS T83, CEC 5.2'),
 'GPIO_SD_B1_07': ('ALT1 FLEXSPIA_SCLK', '22R series (R9) to FLASH_CLK', 'DS T83'),
 'GPIO_SD_B1_08': ('ALT1 FLEXSPIA_DATA00', '', 'DS T83'), 'GPIO_SD_B1_09': ('ALT1 FLEXSPIA_DATA01', '', 'DS T83'),
 'GPIO_SD_B1_10': ('ALT1 FLEXSPIA_DATA02', '', 'DS T83'), 'GPIO_SD_B1_11': ('ALT1 FLEXSPIA_DATA03', '', 'DS T83'),
 'GPIO_SD_B1_05': ('ALT1 FLEXSPIA_DQS', 'NC - floating for 133 MHz loopback', 'DS T38'),
 'GPIO_SD_B1_00': ('ALT1 FLEXSPIB_DATA03', 'DNP PSRAM', 'SDK fsl_iomuxc.h'), 'GPIO_SD_B1_01': ('ALT1 FLEXSPIB_DATA02', 'DNP PSRAM', 'SDK'),
 'GPIO_SD_B1_02': ('ALT1 FLEXSPIB_DATA01', 'DNP PSRAM', 'SDK'), 'GPIO_SD_B1_03': ('ALT1 FLEXSPIB_DATA00', 'DNP PSRAM', 'SDK'),
 'GPIO_SD_B1_04': ('ALT1 FLEXSPIB_SCLK', 'DNP PSRAM, 22R (R11, DNP)', 'SDK'),
 'GPIO_SD_B0_04': ('ALT4 FLEXSPIB_SS0_B', 'DNP PSRAM, 10k PU (R10, DNP); NVCC_SD0=3V3', 'SDK fsl_iomuxc.h L1038 (ALT 0x4); DS T83 ball H2'),
 'USB_OTG1_DP': ('USB OTG1 D+', 'via USBLC6-2SC6 (U6)', 'DS T83'), 'USB_OTG1_DN': ('USB OTG1 D-', '', 'DS T83'),
 'USB_OTG1_VBUS': ('USB OTG1 VBUS', '1uF', 'DS T83'),
 'XTALI': ('24 MHz XTALI', 'Y1 C70590 + 15pF', 'DS T3, HDG T4'), 'XTALO': ('24 MHz XTALO', 'Y1 + 15pF', 'DS T3'),
 'RTC_XTALI': ('32.768 kHz', 'Y2 ABS07 + 18pF', 'DS T3/T20'), 'RTC_XTALO': ('32.768 kHz', 'Y2 + 18pF', 'DS T3'),
 'GPIO_AD_B0_04': ('BOOT_MODE0', 'R7 10k PD; Q1 AO3401A drain via R22 1k (R_S)', 'DS 5.1'), 'GPIO_AD_B0_05': ('BOOT_MODE1', 'R6 10k PU; SW1 to GND; Q1 gate', 'DS 5.1'),
 'POR_B': ('SRC.POR_B', 'R4 10k PU + C48 100nF; TC2030 pin 3; TP4', 'DS T3'), 'ONOFF': ('ONOFF', 'TP5; internal 100k PU, no external part', 'DS T3/T83'),
 'TEST_MODE': ('TEST_MODE', 'tied GND', 'DS T3'),
 'GPIO_AD_B0_06': ('JTAG_TMS / SWDIO', 'TC2030 pin 2', 'DS T83'), 'GPIO_AD_B0_07': ('JTAG_TCK / SWCLK', 'TC2030 pin 4', 'DS T83'),
 'GPIO_AD_B0_10': ('JTAG_TDO / SWO', 'TC2030 pin 6; no external pull', 'DS T3/T83'),
 'GPIO_AD_B0_08': ('JTAG_MOD', 'R5 1k to GND', 'DS T3'),
 'GPIO_AD_B0_12': ('ALT2 LPUART1_TX', 'TP1; also ROM serial downloader', 'DS boot table, HDG T11'),
 'GPIO_AD_B0_13': ('ALT2 LPUART1_RX', 'TP2', 'DS, HDG T11'),
 'GPIO_AD_B1_00': ('ALT3 LPI2C1_SCL', '4.7k PU (R14); SION=1 in SW', 'SDK fsl_iomuxc.h'),
 'GPIO_AD_B1_01': ('ALT3 LPI2C1_SDA', '4.7k PU (R15)', 'SDK fsl_iomuxc.h'),
 'GPIO_AD_B1_02': ('ALT5 GPIO1_IO18', '10k PU + 10nF', 'DS T83'), 'GPIO_AD_B1_03': ('ALT5 GPIO1_IO19', '10k PU + 10nF', 'DS T83'),
 'GPIO_AD_B1_04': ('ALT5 GPIO1_IO20', '10k PU', 'DS T83'), 'GPIO_AD_B1_05': ('ALT5 GPIO1_IO21', '10k PU', 'DS T83'),
 'GPIO_AD_B1_06': ('ALT5 GPIO1_IO22', '10k PU', 'DS T83'),
 'GPIO_AD_B1_08': ('ALT5 GPIO1_IO24', 'R21 1k -> D1; MOVED from K10 (inner) to H13 (outer ring)', 'DS T83'),
}
N = json.load(open(os.path.join(HERE, 'netlist.json')))
mcu = [p for p in N['mcu'] if p['ref'] == 'U1'][0]
L = ['# TokenKey RT - pin map (frozen baseline, rev A0-draft)', '',
     'MCU: **MIMXRT1062DVL6B** (196 MAPBGA, 10 x 10 mm, 0.65 mm pitch). Alternate **MIMXRT1062CVL5B** uses the identical ball map',
     '(IMXRT1060IEC Rev.3 Table 82/83 vs IMXRT1060CEC Rev.4 Table 82/83), but max 528 MHz and VDD_SOC_IN <= 1.26 V.', '',
     'Generated from `tools/gen.py` (same data as the schematic). Balls from IMXRT1060CEC Rev.4 Tables 82/83; all 196 balls accounted for.', '',
     '## Signal assignments', '', '| Ball | Pad | Function / mux | Net | Notes | Source |', '|---|---|---|---|---|---|']
rows = []
for pad, (fn, note, src) in MUX.items():
    ball = func[pad]; rows.append((ball, pad, fn, mcu["nets"][ball] or "NC", note, src))
for r in sorted(rows, key=lambda r: r[3]): L.append('| ' + ' | '.join(map(str, r)) + ' |')
L += ['', 'All other GPIO balls (GPIO_EMC_*, GPIO_B0/B1_* incl. BT_CFG[11:0] on GPIO_B0_04..15, spare GPIO_AD_*, GPIO_SD_B0_00..03/05) are left',
      'unconnected (no-connect flags). BT_CFG pins rely on their internal 100k pull-downs => FlexSPI NOR boot (DS 5.1; EVKB UM Table 10).',
      'Also NC: USB_OTG2_*, USB_OTG1_CHD_B, CCM_CLK1_P/N, PMIC_ON_REQ, PMIC_STBY_REQ, WAKEUP, GPANAIO (DS Table 3/5).',
      '**WAKEUP (L6) and ONOFF (M6)** rely on their internal 100k pull-ups (DS Table 83: Input, 100K PU at reset and default); no external parts. Noted on the mcu sheet.', '',
      '## Boot mode (AO3401A circuit)', '',
      '| State | BOOT_MODE1 (G14) | BOOT_MODE0 (F11) | Mode |', '|---|---|---|---|',
      '| SW1 released | 1 (R6 10k PU) | 0 (Q1 off, R7 10k PD) | 10 internal boot (QSPI) |',
      '| SW1 held at reset | 0 (SW1 to GND) | 1 (Q1 AO3401A on: gate=BM1=0, source=3V3, drain -> R22 1k R_S -> F11; 3.3*10k/11k = 3.0 V) | 01 serial downloader (USB HID / LPUART1) |', '',
      'BOOT_MODE is latched on the POR_B rising edge: hold SW1 (bottom side) and pulse POR_B via TC2030 pin 3 or TP4.', '',
      '## Power balls (DS Table 82)', '', '| Rail | Balls | Net | Decoupling (HDG MIMXRT105060HDUG Rev.3 Table 2 / EVK SCH-31357 A2) |', '|---|---|---|---|']
DEC = {'VDD_SOC_IN': '5x220nF + 2x4.7uF + 22uF (~33uF total with DCDC note)', 'DCDC_IN': '3x220nF + 4.7uF + 22uF', 'DCDC_IN_Q': '(shares DCDC_IN caps)',
       'VDD_HIGH_IN': '220nF + 4.7uF', 'VDD_HIGH_CAP': '220nF + 4.7uF (EVK C21/C22)', 'VDD_SNVS_IN': '220nF (tied to 3V3)', 'VDD_SNVS_CAP': '220nF + 4.7uF (EVK C25/C52)',
       'VDDA_ADC_3P3': '220nF + 1uF', 'NVCC_SD0': '100nF + 4.7uF', 'NVCC_SD1': '100nF + 4.7uF', 'NVCC_EMC': '2x100nF + 4.7uF', 'NVCC_GPIO': '3x100nF + 4.7uF',
       'VDD_USB_CAP': '10uF + 100nF (EVK C82/C83)', 'NVCC_PLL': '4.7uF + 220nF (EVK C26/C24)', 'DCDC_LP': 'L2 VLS3015CX-4R7M-1 4.7uH to VDD_SOC',
       'DCDC_PSWITCH': 'R3 100k from 3V3 + C5 100nF (~10 ms)', 'DCDC_SENSE': 'to VDD_SOC', 'GPANAIO': 'NC (NXP use only)'}
for name, balls in sorted(B['sup'].items()):
    net = mcu['nets'][balls[0]]
    L.append(f'| {name} | {", ".join(balls)} | {net or "NC"} | {DEC.get(name, "")} |')
L += ['', '## Other interfaces', '',
      '- **USB-C J1** TYPE-C-31-M-12 (C165948): CC1/CC2 5.1k Rd (R12/R13), D+/D- to U6 USBLC6-2SC6 (C7519), shield S1 to GND, SBU NC.',
      '- **Flash U4** W25Q64JVSSIQ (C179171): CS=FLASH_CS, CLK=FLASH_CLK (via R9), IO0..3 = SD_B1_08..11.',
      '- **PSRAM U5 (DNP)** APS6404L-3SQR-ZR (C3040877, USON-8L 3x2): 1 CE#, 2 SO/SIO1, 3 SIO2, 4 VSS, 5 SI/SIO0, 6 SCLK, 7 SIO3, 8 VDD - identical for SOP-8 (SN) and USON-8 (ZR) '
      '(AP Memory APS6404L-3SQR datasheet Rev 2.3 s3.1/s4.2). Footprint Package_SON:Winbond_USON-8-1EP_3x2mm_P0.5mm_EP0.2x1.6mm matches (pins 1-4 / 5-8 on the 2 mm sides, 0.5 mm pitch, EP 0.2x1.6 = D1xE1 nom.); EP left unconnected (not defined by AP Memory). '
      'ZR is rated Tc -25 to +85 C; VDD 3.0/3.3 V +/-10%.',
      '- **OLED J2** HS HS96L03W2C03 (LCSC C5248080, SSD1315 = SSD1306-compatible, 0.96in 128x64 I2C, addr 0x3C/0x3D): 1 GND, 2 VCC(3V3), 3 SCL, 4 SDA, 2.54 mm header. '
      'VCC 2.8-3.3 V max, no on-module regulator: 3V3 only, never VBUS. Datasheet requires external pull-ups: R14/R15 4.7k fitted. '
      'PCB 27.3 x 27.8 x 2.65 mm (thickness incl. panel); 4 x d2.5 mm holes (d3.0 pad) on 23.3 x 23.8 mm centres, 2.0 mm from edges (HS96L03W2C03 datasheet V1.0 s1.4/1.5). '
      'Alternate (out of stock 2026-10-19): Jixin JX040102-1, LCSC C284855: SSD1306, onboard SC662K-3.3 LDO and 4.7k resistors, 30 x 29 mm, holes on 25 x 24 mm (Jixin datasheet V1.0.0.0); different mechanics.',
      '- **Encoder SW2** EC11E18244A5 (C255515): A=ENC_A, B=ENC_B, C=GND, S1=ENC_SW, S2=GND.',
      '- **TC2030-NL J3**: 1 VCC(3V3), 2 SWDIO, 3 nRESET(POR_B), 4 SWCLK, 5 GND, 6 SWO (Tag-Connect TC2030-CTX datasheet).',
      '- **Test pads**: TP1 UART_TX, TP2 UART_RX, TP3 GND, TP4 POR_B, TP5 ONOFF.',
      '- **3V3**: U2 AP2112K-3.3TRG1 fitted; U3 TLV62569DBVR + L1 2.2uH + R1/R2 (Vout 3.33 V) + C3/C4 all DNP (fit buck and remove U2).', '',
      '## Unverified / open', '',
      '1. RT1062 BGA footprint: package NXP SOT1546-2, case outline 98ASA01088D Rev O (01 Jun 2017; IMXRT1060CEC Rev 4 Fig. 53): 14x14 at 0.65 mm, ball d0.25-0.35 mm, A 1.43 max. '
      'Land: 0.325 mm Cu NSMD, mask opening 0.450 mm (+0.125 mm), paste 1:1 (NXP AN4982 Rev 4 Table 1, s4.2.3); 0.20 mm mask web between openings. Check stencil (0.075-0.1 mm) and mask registration with the fab.',
      '2. APS6404L-3SQR-ZR: pinout and footprint checked (see above); exposed pad left unconnected - confirm with AP Memory if it should be GND.',
      '3. OLED: HS96L03W2C03 datasheet does not show whether the module itself carries SCL/SDA pull-ups (assume none; R14/R15 fitted). Confirm hole/header positions on a sample before enclosure CAD.',
      '4. 220nF 0402: primary CL05A224KA5NNNC C47129 (25V X5R, 1,400 in stock 2026-10-19); second source CL05B224KO5NNNC C16772 (16V X7R, 854,600 in stock) in MPN_Alt/LCSC_Alt fields.',
      '4b. 4.7uF 0402: primary CL05A475MP5NRNC C23733 (10V X5R, OUT OF STOCK at LCSC 2026-10-19); second source CL05A475KP5NRNC C368809 (10V X5R +/-10%, 1,355,750 in stock) in MPN_Alt/LCSC_Alt on all 12 parts.',
      '5. VDD_USB_CAP C82 = 10uF read from a partly overlapped label on EVK SCH-31357 rev A2 (EVKB B1 files need NXP login).',
      '6. Crystal load caps need bench tuning; drive level in-circuit not measured.']
open(os.path.join(ROOT, 'docs/pin-map.md'), 'w').write('\n'.join(L) + '\n')
print('written', len(L), 'lines')
