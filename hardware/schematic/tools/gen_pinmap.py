#!/usr/bin/env python3
import json, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
B = json.load(open(os.path.join(ROOT, 'tools/rt1062_10x10_balls.json'))); func = B['func']
MUX = {  # pad -> (function / mux, notes, source)
 'GPIO_SD_B1_06': ('ALT1 FLEXSPIA_SS0_B', '10k PU (R8); boot ROM default', 'DS T83, CEC 5.2'),
 'GPIO_SD_B1_07': ('ALT1 FLEXSPIA_SCLK', '22R series (R9) to FLASH_CLK', 'DS T83'),
 'GPIO_SD_B1_08': ('ALT1 FLEXSPIA_DATA00', '', 'DS T83'), 'GPIO_SD_B1_09': ('ALT1 FLEXSPIA_DATA01', '', 'DS T83'),
 'GPIO_SD_B1_10': ('ALT1 FLEXSPIA_DATA02', '', 'DS T83'), 'GPIO_SD_B1_11': ('ALT1 FLEXSPIA_DATA03', '', 'DS T83'),
 'GPIO_SD_B1_05': ('ALT1 FLEXSPIA_DQS', 'NC - floating for 133 MHz loopback', 'DS T38'),
 'GPIO_SD_B1_00': ('ALT1 FLEXSPIB_DATA03', 'DNP PSRAM', 'SDK fsl_iomuxc.h'), 'GPIO_SD_B1_01': ('ALT1 FLEXSPIB_DATA02', 'DNP PSRAM', 'SDK'),
 'GPIO_SD_B1_02': ('ALT1 FLEXSPIB_DATA01', 'DNP PSRAM', 'SDK'), 'GPIO_SD_B1_03': ('ALT1 FLEXSPIB_DATA00', 'DNP PSRAM', 'SDK'),
 'GPIO_SD_B1_04': ('ALT1 FLEXSPIB_SCLK', 'DNP PSRAM, 22R (R11, DNP)', 'SDK'),
 'GPIO_SD_B0_04': ('ALT4 FLEXSPIB_SS0_B', 'DNP PSRAM, 10k PU (R10, DNP); NVCC_SD0=3V3', 'SDK'),
 'USB_OTG1_DP': ('USB OTG1 D+', 'via USBLC6-2SC6 (U6)', 'DS T83'), 'USB_OTG1_DN': ('USB OTG1 D-', '', 'DS T83'),
 'USB_OTG1_VBUS': ('USB OTG1 VBUS', '1uF', 'DS T83'),
 'XTALI': ('24 MHz XTALI', 'Y1 C70590 + 15pF', 'DS T3, HDG T4'), 'XTALO': ('24 MHz XTALO', 'Y1 + 15pF', 'DS T3'),
 'RTC_XTALI': ('32.768 kHz', 'Y2 ABS07 + 18pF', 'DS T3/T20'), 'RTC_XTALO': ('32.768 kHz', 'Y2 + 18pF', 'DS T3'),
 'GPIO_AD_B0_04': ('BOOT_MODE0', 'R7 10k PD; Q1 AO3401A drain', 'DS 5.1'), 'GPIO_AD_B0_05': ('BOOT_MODE1', 'R6 10k PU; SW1 to GND; Q1 gate', 'DS 5.1'),
 'POR_B': ('SRC.POR_B', 'R4 10k PU + C48 100nF; TC2030 pin 3; TP4', 'DS T3'), 'ONOFF': ('ONOFF', 'TP5', 'DS T3'),
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
N = json.load(open(os.path.join(ROOT, 'tools/netlist.json')))
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
      'Also NC: USB_OTG2_*, USB_OTG1_CHD_B, CCM_CLK1_P/N, PMIC_ON_REQ, PMIC_STBY_REQ, WAKEUP, GPANAIO (DS Table 3/5).', '',
      '## Boot mode (AO3401A circuit)', '',
      '| State | BOOT_MODE1 (G14) | BOOT_MODE0 (F11) | Mode |', '|---|---|---|---|',
      '| SW1 released | 1 (R6 10k PU) | 0 (Q1 off, R7 10k PD) | 10 internal boot (QSPI) |',
      '| SW1 held at reset | 0 (SW1 to GND) | 1 (Q1 AO3401A on: gate=BM1=0, source=3V3) | 01 serial downloader (USB HID / LPUART1) |', '',
      'BOOT_MODE is latched on the POR_B rising edge: hold SW1 (bottom side) and pulse POR_B via TC2030 pin 3 or TP4.', '',
      '## Power balls (DS Table 82)', '', '| Rail | Balls | Net | Decoupling (HDG MIMXRT105060HDUG Rev.3 Table 2 / EVK SCH-31357 A2) |', '|---|---|---|---|']
DEC = {'VDD_SOC_IN': '5x220nF + 2x4.7uF + 22uF (~33uF total with DCDC note)', 'DCDC_IN': '3x220nF + 4.7uF + 22uF', 'DCDC_IN_Q': '(shares DCDC_IN caps)',
       'VDD_HIGH_IN': '220nF + 4.7uF', 'VDD_HIGH_CAP': '220nF + 4.7uF (EVK C21/C22)', 'VDD_SNVS_IN': '220nF (tied to 3V3)', 'VDD_SNVS_CAP': '220nF + 4.7uF (EVK C25/C52)',
       'VDDA_ADC_3P3': '220nF + 1uF', 'NVCC_SD0': '100nF + 4.7uF', 'NVCC_SD1': '100nF + 4.7uF', 'NVCC_EMC': '2x100nF + 4.7uF', 'NVCC_GPIO': '3x100nF + 4.7uF',
       'VDD_USB_CAP': '10uF + 100nF (EVK C82/C83)', 'NVCC_PLL': '4.7uF + 220nF (EVK C26/C24)', 'DCDC_LP': 'L2 SWPA4020S4R7MT 4.7uH to VDD_SOC',
       'DCDC_PSWITCH': 'R3 100k from 3V3 + C5 100nF (~10 ms)', 'DCDC_SENSE': 'to VDD_SOC', 'GPANAIO': 'NC (NXP use only)'}
for name, balls in sorted(B['sup'].items()):
    net = mcu['nets'][balls[0]]
    L.append(f'| {name} | {", ".join(balls)} | {net or "NC"} | {DEC.get(name, "")} |')
L += ['', '## Other interfaces', '',
      '- **USB-C J1** TYPE-C-31-M-12 (C165948): CC1/CC2 5.1k Rd (R12/R13), D+/D- to U6 USBLC6-2SC6 (C7519), shield S1 to GND, SBU NC.',
      '- **Flash U4** W25Q64JVSSIQ (C179171): CS=FLASH_CS, CLK=FLASH_CLK (via R9), IO0..3 = SD_B1_08..11.',
      '- **PSRAM U5 (DNP)** APS6404L-3SQR-ZR (C3040877): FlexSPI B as above. Pinout and USON footprint UNVERIFIED.',
      '- **OLED J2**: 1 GND, 2 3V3, 3 SCL, 4 SDA (module pin order UNVERIFIED).',
      '- **Encoder SW2** EC11E18244A5 (C255515): A=ENC_A, B=ENC_B, C=GND, S1=ENC_SW, S2=GND.',
      '- **TC2030-NL J3**: 1 VCC(3V3), 2 SWDIO, 3 nRESET(POR_B), 4 SWCLK, 5 GND, 6 SWO (Tag-Connect TC2030-CTX datasheet).',
      '- **Test pads**: TP1 UART_TX, TP2 UART_RX, TP3 GND, TP4 POR_B, TP5 ONOFF.',
      '- **3V3**: U2 AP2112K-3.3TRG1 fitted; U3 TLV62569DBVR + L1 2.2uH + R1/R2 (Vout 3.33 V) + C3/C4 all DNP (fit buck and remove U2).', '',
      '## Unverified / open', '',
      '1. RT1062 BGA footprint (TokenKey:NXP_MAPBGA-196_10x10mm...) is generated: 0.65 mm grid from DS Fig.53, **0.30 mm SMD pads are an assumption** - verify against the NXP package drawing / land pattern before layout.',
      '2. APS6404L-3SQR-ZR pinout (assumed standard QSPI 8-pin) and USON-8 footprint (Winbond 3x2 placeholder).',
      '3. OLED module pinout and LCSC part (generic module).',
      '4. 220nF 0402 (C47129) has low LCSC stock (1,447); pick an alternate before ordering.',
      '5. VDD_USB_CAP C82 = 10uF read from a partly overlapped label on EVK SCH-31357 rev A2 (EVKB B1 files need NXP login).',
      '6. Crystal load caps need bench tuning; drive level in-circuit not measured.']
open(os.path.join(ROOT, 'docs/pin-map.md'), 'w').write('\n'.join(L) + '\n')
print('written', len(L), 'lines')
