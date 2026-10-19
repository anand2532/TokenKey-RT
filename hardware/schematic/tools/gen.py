#!/usr/bin/env python3
"""Generate TokenKey-RT hierarchical KiCad 9 schematic + project libs from one netlist description."""
import json, uuid, math, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCH = os.path.join(ROOT, 'hardware/schematic'); LIB = os.path.join(ROOT, 'hardware/libraries')
PROJ = 'TokenKey-RT'
U = lambda: str(uuid.uuid4())
G = 2.54
def q(s): return '"' + str(s).replace('\\', '\\\\').replace('"', '\\"') + '"'
def fnt(hide=False, just=None):
    j = f' (justify {just})' if just else ''
    return f'(effects (font (size 1.27 1.27)){j}{" (hide yes)" if hide else ""})'

# ---------------------------------------------------------------- footprints / parts
FP = dict(R0402='Resistor_SMD:R_0402_1005Metric', C0402='Capacitor_SMD:C_0402_1005Metric',
          C0603='Capacitor_SMD:C_0603_1608Metric', SOT235='Package_TO_SOT_SMD:SOT-23-5',
          SOT236='Package_TO_SOT_SMD:SOT-23-6', SOT23='Package_TO_SOT_SMD:SOT-23',
          L4020='Inductor_SMD:L_Sunlord_SWPA4020S', LED0603='LED_SMD:LED_0603_1608Metric',
          SW_B3U='Button_Switch_SMD:SW_SPST_B3U-1000P', TP='TestPoint:TestPoint_Pad_D1.0mm')
RVAL = {'10k': ('0402WGF1002TCE', 'C25744'), '4.7k': ('0402WGF4701TCE', 'C25900'), '5.1k': ('0402WGF5101TCE', 'C25905'),
        '100k': ('0402WGF1003TCE', 'C25741'), '22R': ('0402WGF220JTCE', 'C25092'), '1k': ('0402WGF1001TCE', 'C11702'),
        '22k': ('0402WGF2202TCE', 'C25768')}
CVAL = {'100nF': ('CL05B104KO5NNNC', 'C1525', 'C0402'), '220nF': ('CL05A224KA5NNNC', 'C47129', 'C0402'),
        '1uF': ('CL05A105KA5NQNC', 'C52923', 'C0402'), '4.7uF': ('CL05A475MP5NRNC', 'C23733', 'C0402'),
        '10uF': ('CL10A106KP8NNNC', 'C19702', 'C0603'), '22uF': ('CL10A226MQ8NRNC', 'C59461', 'C0603'),
        '15pF': ('0402CG150J500NT', 'C1548', 'C0402'), '18pF': ('0402CG180J500NT', 'C1549', 'C0402'),
        '10nF': ('CL05B103KB5NNNC', 'C15195', 'C0402')}
# second sources: value -> (MPN_Alt, LCSC_Alt). 220nF: C47129 stock 1,400 on 2026-10-19; C16772 854,600 (LCSC)
CALT = {'220nF': ('CL05B224KO5NNNC', 'C16772')}

# symbol defs: name -> dict(ref, units:[ [ (num,name,type,side) ] ], hide_names)
SYMS = {}
def sym(name, ref, units, hide_names=False, hide_nums=False):
    SYMS[name] = dict(ref=ref, units=units, hide_names=hide_names, hide_nums=hide_nums)
sym('R', 'R', [[('1', '~', 'passive', 'L'), ('2', '~', 'passive', 'R')]], True, False)
sym('C', 'C', [[('1', '~', 'passive', 'L'), ('2', '~', 'passive', 'R')]], True, False)
sym('L', 'L', [[('1', '~', 'passive', 'L'), ('2', '~', 'passive', 'R')]], True, False)
sym('LED', 'D', [[('2', 'A', 'passive', 'L'), ('1', 'K', 'passive', 'R')]])
sym('SW_Push', 'SW', [[('1', '1', 'passive', 'L'), ('2', '2', 'passive', 'R')]], True)
sym('TestPoint', 'TP', [[('1', '1', 'passive', 'L')]], True)
sym('PWR_FLAG', '#FLG', [[('1', 'PWR_FLAG', 'power_out', 'L')]], True, True)
sym('AP2112K-3.3', 'U', [[('1', 'VIN', 'power_in', 'L'), ('3', 'EN', 'input', 'L'), ('2', 'GND', 'power_in', 'L'),
                          ('5', 'VOUT', 'power_out', 'R'), ('4', 'NC', 'no_connect', 'R')]])
sym('TLV62569DBV', 'U', [[('4', 'VIN', 'power_in', 'L'), ('1', 'EN', 'input', 'L'), ('2', 'GND', 'power_in', 'L'),
                          ('3', 'SW', 'power_out', 'R'), ('5', 'FB', 'input', 'R')]])
sym('AO3401A', 'Q', [[('1', 'G', 'input', 'L'), ('2', 'S', 'passive', 'R'), ('3', 'D', 'passive', 'R')]])
sym('USBLC6-2SC6', 'U', [[('1', 'I/O1', 'passive', 'L'), ('3', 'I/O2', 'passive', 'L'), ('2', 'GND', 'passive', 'L'),
                          ('6', 'I/O1', 'passive', 'R'), ('4', 'I/O2', 'passive', 'R'), ('5', 'VBUS', 'passive', 'R')]])
sym('USB_C_USB2_16P', 'J', [[('A4', 'VBUS', 'passive', 'L'), ('A9', 'VBUS', 'passive', 'L'), ('B4', 'VBUS', 'passive', 'L'),
                             ('B9', 'VBUS', 'passive', 'L'), ('A5', 'CC1', 'bidirectional', 'L'), ('B5', 'CC2', 'bidirectional', 'L'),
                             ('A1', 'GND', 'passive', 'L'), ('A12', 'GND', 'passive', 'L'), ('B1', 'GND', 'passive', 'L'),
                             ('B12', 'GND', 'passive', 'L'), ('S1', 'SHIELD', 'passive', 'L'),
                             ('A6', 'D+', 'bidirectional', 'R'), ('B6', 'D+', 'bidirectional', 'R'), ('A7', 'D-', 'bidirectional', 'R'),
                             ('B7', 'D-', 'bidirectional', 'R'), ('A8', 'SBU1', 'bidirectional', 'R'), ('B8', 'SBU2', 'bidirectional', 'R')]])
FLASH8 = [('1', '~{CS}', 'input', 'L'), ('6', 'CLK', 'input', 'L'), ('5', 'IO0', 'bidirectional', 'L'), ('2', 'IO1', 'bidirectional', 'L'),
          ('3', 'IO2', 'bidirectional', 'R'), ('7', 'IO3', 'bidirectional', 'R'), ('8', 'VCC', 'power_in', 'R'), ('4', 'GND', 'power_in', 'R')]
sym('W25Q64JVSSIQ', 'U', [FLASH8])
sym('APS6404L-3SQR', 'U', [FLASH8])
sym('Crystal_GND24', 'Y', [[('1', '1', 'passive', 'L'), ('2', 'GND', 'passive', 'L'), ('3', '3', 'passive', 'R'), ('4', 'GND', 'passive', 'R')]])
sym('Crystal', 'Y', [[('1', '1', 'passive', 'L'), ('2', '2', 'passive', 'R')]], True)
sym('RotaryEncoder_Switch', 'SW', [[('A', 'A', 'passive', 'L'), ('C', 'C', 'passive', 'L'), ('B', 'B', 'passive', 'L'),
                                    ('S1', 'S1', 'passive', 'R'), ('S2', 'S2', 'passive', 'R')]])
sym('OLED_I2C_4P', 'J', [[('1', 'GND', 'passive', 'L'), ('2', 'VCC', 'passive', 'L'), ('3', 'SCL', 'passive', 'R'), ('4', 'SDA', 'passive', 'R')]])
sym('TC2030_SWD', 'J', [[('1', 'VCC', 'passive', 'L'), ('5', 'GND', 'passive', 'L'), ('3', '~{RESET}', 'passive', 'L'),
                          ('2', 'SWDIO', 'passive', 'R'), ('4', 'SWCLK', 'passive', 'R'), ('6', 'SWO', 'passive', 'R')]])

# ---------- RT1062 multi-unit symbol from datasheet Tables 82/83 (10x10 MAPBGA)
B = json.load(open(os.path.join(ROOT, 'tools/rt1062_10x10_balls.json')))
func, sup = B['func'], B['sup']
def rowkey(ball): return ('ABCDEFGHJKLMNP'.index(ball[0]), int(ball[1:]))
PWR_IN = {'DCDC_IN', 'DCDC_IN_Q', 'VDD_HIGH_IN', 'VDD_SNVS_IN', 'NVCC_EMC', 'NVCC_GPIO', 'NVCC_SD0', 'NVCC_SD1', 'VDDA_ADC_3P3', 'VDD_SOC_IN'}
PWR_OUT = {'DCDC_LP', 'VDD_HIGH_CAP', 'VDD_SNVS_CAP', 'VDD_USB_CAP', 'NVCC_PLL'}
GNDS = {'VSS', 'DCDC_GND', 'NGND_KEL0'}
u_pwr_L, u_pwr_R = [], []
for name in sorted(sup):
    for b in sorted(sup[name], key=rowkey):
        if name in GNDS: u_pwr_R.append((b, name, 'power_in', 'R'))
        elif name in PWR_OUT:   # one power_out per internal regulator output; extra balls of the same rail are passive
            first = not any(x[1] == name for x in u_pwr_R)
            u_pwr_R.append((b, name, 'power_out' if first else 'passive', 'R'))
        elif name in PWR_IN: u_pwr_L.append((b, name, 'power_in', 'L'))
        elif name == 'DCDC_SENSE': u_pwr_L.append((b, name, 'input', 'L'))
        elif name == 'DCDC_PSWITCH': u_pwr_L.append((b, name, 'input', 'L'))
        else: u_pwr_L.append((b, name, 'passive', 'L'))   # GPANAIO
def gpio_unit(prefixes):
    names = sorted([n for n in func if any(n.startswith(p) for p in prefixes)], key=lambda n: (n.rsplit('_', 1)[0], int(n.rsplit('_', 1)[1])))
    half = (len(names) + 1) // 2
    return [(func[n], n, 'bidirectional', 'L' if i < half else 'R') for i, n in enumerate(names)]
SYS_T = {'POR_B': 'input', 'ONOFF': 'input', 'TEST_MODE': 'input', 'WAKEUP': 'bidirectional', 'PMIC_ON_REQ': 'output',
         'PMIC_STBY_REQ': 'output', 'USB_OTG1_VBUS': 'power_in', 'USB_OTG2_VBUS': 'power_in'}
sysn = [n for n in func if not n.startswith('GPIO_')]
u_sys = [(func[n], n, SYS_T.get(n, 'passive'), 'L' if (n.startswith('USB') or 'XTAL' in n) else 'R') for n in sorted(sysn)]
sym('MIMXRT1062DVL6B', 'U', [u_pwr_L + u_pwr_R, gpio_unit(['GPIO_AD_']), gpio_unit(['GPIO_B0_', 'GPIO_B1_']),
                             gpio_unit(['GPIO_EMC_']), gpio_unit(['GPIO_SD_']) + u_sys])
assert sum(len(u) for u in SYMS['MIMXRT1062DVL6B']['units']) == 196

# ---------------------------------------------------------------- netlist
SHEETS = {k: [] for k in ['power', 'mcu', 'flash', 'usb', 'ui', 'debug']}
TITLES = dict(power='Power: VBUS in, 3V3 LDO / DNP buck, RT1062 DCDC + decoupling', mcu='MCU: MIMXRT1062DVL6B, clocks, reset, boot',
              flash='FlexSPI A boot flash + DNP FlexSPI B PSRAM', usb='USB-C device, CC Rd, ESD', ui='UI: OLED, encoder, buttons, LED',
              debug='Debug: TC2030-NL SWD, UART/reset test pads')
def part(sheet, ref, symn, value, fp, mpn, lcsc, nets, dnp=False, note='', units=None, alt=None):
    SHEETS[sheet].append(dict(ref=ref, sym=symn, value=value, fp=fp, mpn=mpn, lcsc=lcsc, nets=nets, dnp=dnp, note=note, units=units, alt=alt))
cnt = {'U': 1}   # U1 reserved for the MCU
def nref(p):
    cnt[p] = cnt.get(p, 0) + 1; return f'{p}{cnt[p]}'
def R(sheet, val, a, b, dnp=False, note=''):
    mpn, lcsc = RVAL[val]; part(sheet, nref('R'), 'R', val, FP['R0402'], mpn, lcsc, {'1': a, '2': b}, dnp, note)
def C(sheet, val, a, b='GND', dnp=False, note=''):
    mpn, lcsc, f = CVAL[val]; part(sheet, nref('C'), 'C', val, FP[f], mpn, lcsc, {'1': a, '2': b}, dnp, note, alt=CALT.get(val))
def FLAG(sheet, net): part(sheet, nref('#FLG'), 'PWR_FLAG', 'PWR_FLAG', '', 'virtual', 'N/A', {'1': net})

# ---- power
FLAG('power', 'VBUS'); FLAG('power', 'GND'); FLAG('power', 'VDD_SOC')
part('power', nref('U'), 'AP2112K-3.3', 'AP2112K-3.3TRG1', FP['SOT235'], 'AP2112K-3.3TRG1', 'C51118',
     {'1': 'VBUS', '3': 'VBUS', '2': 'GND', '5': '3V3', '4': None}, note='Fitted 3V3 source (600 mA LDO)')
C('power', '1uF', 'VBUS', note='LDO input'); C('power', '10uF', '3V3', note='LDO output bulk')
part('power', nref('U'), 'TLV62569DBV', 'TLV62569DBVR', FP['SOT235'], 'TLV62569DBVR', 'C141836',
     {'4': 'VBUS', '1': 'VBUS', '2': 'GND', '3': 'BUCK_SW', '5': 'BUCK_FB'}, dnp=True, note='DNP buck fallback; fit with L2/R/C and remove U2')
part('power', nref('L'), 'L', '2.2uH', FP['L4020'], 'SWPA4020S2R2MT', 'C83423', {'1': 'BUCK_SW', '2': '3V3'}, dnp=True, note='DNP buck inductor')
R('power', '100k', '3V3', 'BUCK_FB', dnp=True, note='FB top: Vout=0.6*(1+100k/22k)=3.33 V')
R('power', '22k', 'BUCK_FB', 'GND', dnp=True, note='FB bottom')
C('power', '10uF', 'VBUS', dnp=True, note='buck CIN'); C('power', '22uF', '3V3', dnp=True, note='buck COUT')
part('power', nref('L'), 'L', '4.7uH', FP['L4020'], 'SWPA4020S4R7MT', 'C48427', {'1': 'DCDC_LP', '2': 'VDD_SOC'},
     note='RT1062 DCDC inductor (HDG: 4.7-10uH, Isat>1A, DCR<0.2R)')
R('power', '100k', '3V3', 'DCDC_PSWITCH', note='PSWITCH RC ~10 ms (DS 4.2.1.1: 5-15 ms)'); C('power', '100nF', 'DCDC_PSWITCH', note='PSWITCH RC')
for v, n, note in ([('220nF', 'VDD_SOC', 'VDD_SOC_IN F6-J9')] * 5 + [('4.7uF', 'VDD_SOC', 'VDD_SOC_IN'), ('4.7uF', 'VDD_SOC', 'VDD_SOC_IN (bring total ~33uF)'), ('22uF', 'VDD_SOC', 'VDD_SOC_IN bulk')]
                   + [('220nF', '3V3', 'DCDC_IN L1/L2/K4')] * 3 + [('4.7uF', '3V3', 'DCDC_IN'), ('22uF', '3V3', 'DCDC_IN bulk')]
                   + [('220nF', '3V3', 'VDD_HIGH_IN P12'), ('4.7uF', '3V3', 'VDD_HIGH_IN P12')]
                   + [('220nF', 'VDD_HIGH_CAP', 'VDD_HIGH_CAP P8'), ('4.7uF', 'VDD_HIGH_CAP', 'VDD_HIGH_CAP P8')]
                   + [('220nF', '3V3', 'VDD_SNVS_IN M9')]
                   + [('220nF', 'VDD_SNVS_CAP', 'VDD_SNVS_CAP M10'), ('4.7uF', 'VDD_SNVS_CAP', 'VDD_SNVS_CAP M10')]
                   + [('1uF', 'VBUS', 'USB_OTG1_VBUS N6')]
                   + [('220nF', '3V3', 'VDDA_ADC_3P3 N14'), ('1uF', '3V3', 'VDDA_ADC_3P3 N14')]
                   + [('100nF', '3V3', 'NVCC_SD0 J6'), ('4.7uF', '3V3', 'NVCC_SD0 J6'), ('100nF', '3V3', 'NVCC_SD1 K5'), ('4.7uF', '3V3', 'NVCC_SD1 K5')]
                   + [('100nF', '3V3', 'NVCC_EMC E6/F5')] * 2 + [('4.7uF', '3V3', 'NVCC_EMC')]
                   + [('100nF', '3V3', 'NVCC_GPIO E9/F10/J10')] * 3 + [('4.7uF', '3V3', 'NVCC_GPIO')]
                   + [('10uF', 'VDD_USB_CAP', 'VDD_USB_CAP K8 (EVK C82)'), ('100nF', 'VDD_USB_CAP', 'VDD_USB_CAP K8 (EVK C83)')]
                   + [('4.7uF', 'NVCC_PLL', 'NVCC_PLL P10 (EVK C26)'), ('220nF', 'NVCC_PLL', 'NVCC_PLL P10 (EVK C24)')]):
    C('power', v, n, note=note)

# ---- MCU pin assignment (frozen baseline; LED moved K10 -> H13)
PIN = {
 'GPIO_SD_B1_06': 'FLASH_CS', 'GPIO_SD_B1_07': 'QSPIA_SCLK', 'GPIO_SD_B1_08': 'FLASH_IO0', 'GPIO_SD_B1_09': 'FLASH_IO1',
 'GPIO_SD_B1_10': 'FLASH_IO2', 'GPIO_SD_B1_11': 'FLASH_IO3',
 'GPIO_SD_B1_00': 'PSRAM_IO3', 'GPIO_SD_B1_01': 'PSRAM_IO2', 'GPIO_SD_B1_02': 'PSRAM_IO1', 'GPIO_SD_B1_03': 'PSRAM_IO0',
 'GPIO_SD_B1_04': 'QSPIB_SCLK', 'GPIO_SD_B0_04': 'PSRAM_CS',
 'USB_OTG1_DP': 'USB_DP', 'USB_OTG1_DN': 'USB_DN', 'USB_OTG1_VBUS': 'VBUS',
 'XTALI': 'XTALI', 'XTALO': 'XTALO', 'RTC_XTALI': 'RTC_XTALI', 'RTC_XTALO': 'RTC_XTALO',
 'GPIO_AD_B0_04': 'BOOT_MODE0', 'GPIO_AD_B0_05': 'BOOT_MODE1', 'POR_B': 'POR_B', 'ONOFF': 'ONOFF', 'TEST_MODE': 'GND',
 'GPIO_AD_B0_06': 'SWDIO', 'GPIO_AD_B0_07': 'SWCLK', 'GPIO_AD_B0_10': 'SWO', 'GPIO_AD_B0_08': 'JTAG_MOD',
 'GPIO_AD_B0_12': 'UART_TX', 'GPIO_AD_B0_13': 'UART_RX',
 'GPIO_AD_B1_00': 'OLED_SCL', 'GPIO_AD_B1_01': 'OLED_SDA', 'GPIO_AD_B1_02': 'ENC_A', 'GPIO_AD_B1_03': 'ENC_B',
 'GPIO_AD_B1_04': 'ENC_SW', 'GPIO_AD_B1_05': 'BTN1', 'GPIO_AD_B1_06': 'BTN2', 'GPIO_AD_B1_08': 'LED_STAT',
}
SUPNET = {'VSS': 'GND', 'DCDC_GND': 'GND', 'NGND_KEL0': 'GND', 'DCDC_IN': '3V3', 'DCDC_IN_Q': '3V3', 'VDD_HIGH_IN': '3V3',
          'VDD_SNVS_IN': '3V3', 'NVCC_EMC': '3V3', 'NVCC_GPIO': '3V3', 'NVCC_SD0': '3V3', 'NVCC_SD1': '3V3', 'VDDA_ADC_3P3': '3V3',
          'VDD_SOC_IN': 'VDD_SOC', 'DCDC_SENSE': 'VDD_SOC', 'DCDC_LP': 'DCDC_LP', 'DCDC_PSWITCH': 'DCDC_PSWITCH',
          'VDD_HIGH_CAP': 'VDD_HIGH_CAP', 'VDD_SNVS_CAP': 'VDD_SNVS_CAP', 'VDD_USB_CAP': 'VDD_USB_CAP', 'NVCC_PLL': 'NVCC_PLL', 'GPANAIO': None}
mcu_nets = {}
for unit in SYMS['MIMXRT1062DVL6B']['units']:
    for (ball, name, t, s) in unit:
        mcu_nets[ball] = SUPNET[name] if name in SUPNET else PIN.get(name)
part('mcu', 'U1', 'MIMXRT1062DVL6B', 'MIMXRT1062DVL6B', 'TokenKey:NXP_MAPBGA-196_10x10mm_Layout14x14_P0.65mm', 'MIMXRT1062DVL6B', 'C2847497',
     mcu_nets, note='Alt: MIMXRT1062CVL5B (LCSC C2990557), same ball map; 528 MHz / VDD_SOC<=1.26V', units=5)
part('mcu', nref('Y'), 'Crystal_GND24', '24MHz 12pF', 'Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm', 'X322524MOB4SI', 'C70590',
     {'1': 'XTALI', '3': 'XTALO', '2': 'GND', '4': 'GND'}, note='YXC YSX321SL: ESR<=50R, DL<=200uW (meets HDG 50R/200uW)')
C('mcu', '15pF', 'XTALI'); C('mcu', '15pF', 'XTALO')
part('mcu', nref('Y'), 'Crystal', '32.768kHz 12.5pF', 'Crystal:Crystal_SMD_3215-2Pin_3.2x1.5mm', 'ABS07-32.768KHZ-T', 'C130253',
     {'1': 'RTC_XTALI', '2': 'RTC_XTALO'}, note='ESR 70k <= 100k')
C('mcu', '18pF', 'RTC_XTALI'); C('mcu', '18pF', 'RTC_XTALO')
R('mcu', '10k', '3V3', 'POR_B', note='POR_B pull-up'); C('mcu', '100nF', 'POR_B', note='POR_B delay')
R('mcu', '1k', 'JTAG_MOD', 'GND', note='JTAG_MOD low = SWD/common debug (DS Table 3)')
R('mcu', '10k', 'BOOT_MODE1', '3V3', note='BOOT_MODE1 high => mode 10 internal boot')
R('mcu', '10k', 'BOOT_MODE0', 'GND', note='BOOT_MODE0 defined low when Q1 off')
part('mcu', nref('Q'), 'AO3401A', 'AO3401A', FP['SOT23'], 'AO3401A', 'C15127', {'1': 'BOOT_MODE1', '2': '3V3', '3': 'BOOT_MODE0'},
     note='Press SW_BOOT: BM1=0 and Q1 on => BM0=1 => mode 01 serial downloader')
part('mcu', nref('SW'), 'SW_Push', 'SW_BOOT', FP['SW_B3U'], 'B3U-1000P', 'C231329', {'1': 'BOOT_MODE1', '2': 'GND'}, note='Bottom side')

# ---- flash
part('flash', nref('U'), 'W25Q64JVSSIQ', 'W25Q64JVSSIQ', 'Package_SO:SOIC-8_5.3x5.3mm_P1.27mm', 'W25Q64JVSSIQ', 'C179171',
     {'1': 'FLASH_CS', '6': 'FLASH_CLK', '5': 'FLASH_IO0', '2': 'FLASH_IO1', '3': 'FLASH_IO2', '7': 'FLASH_IO3', '8': '3V3', '4': 'GND'},
     note='Boot flash on FlexSPI A (BT_CFG all 0)')
R('flash', '10k', '3V3', 'FLASH_CS'); R('flash', '22R', 'QSPIA_SCLK', 'FLASH_CLK', note='series term, place at MCU'); C('flash', '100nF', '3V3')
part('flash', nref('U'), 'APS6404L-3SQR', 'APS6404L-3SQR-ZR', 'Package_SON:Winbond_USON-8-1EP_3x2mm_P0.5mm_EP0.2x1.6mm', 'APS6404L-3SQR-ZR', 'C3040877',
     {'1': 'PSRAM_CS', '6': 'PSRAM_CLK', '5': 'PSRAM_IO0', '2': 'PSRAM_IO1', '3': 'PSRAM_IO2', '7': 'PSRAM_IO3', '8': '3V3', '4': 'GND'},
     dnp=True, note='DNP PSRAM FlexSPI B; pinout+footprint UNVERIFIED vs AP Memory datasheet')
R('flash', '10k', '3V3', 'PSRAM_CS', dnp=True); R('flash', '22R', 'QSPIB_SCLK', 'PSRAM_CLK', dnp=True); C('flash', '100nF', '3V3', dnp=True)

# ---- usb
part('usb', nref('J'), 'USB_C_USB2_16P', 'USB-C', 'Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12', 'TYPE-C-31-M-12', 'C165948',
     {'A4': 'VBUS', 'A9': 'VBUS', 'B4': 'VBUS', 'B9': 'VBUS', 'A5': 'CC1', 'B5': 'CC2', 'A1': 'GND', 'A12': 'GND', 'B1': 'GND', 'B12': 'GND',
      'S1': 'GND', 'A6': 'USB_DP', 'B6': 'USB_DP', 'A7': 'USB_DN', 'B7': 'USB_DN', 'A8': None, 'B8': None})
R('usb', '5.1k', 'CC1', 'GND', note='Rd'); R('usb', '5.1k', 'CC2', 'GND', note='Rd')
part('usb', nref('U'), 'USBLC6-2SC6', 'USBLC6-2SC6', FP['SOT236'], 'USBLC6-2SC6', 'C7519',
     {'1': 'USB_DP', '6': 'USB_DP', '3': 'USB_DN', '4': 'USB_DN', '5': 'VBUS', '2': 'GND'}, note='Place at J1')
C('usb', '10uF', 'VBUS', note='VBUS bulk at connector')

# ---- ui
part('ui', nref('J'), 'OLED_I2C_4P', 'OLED 0.96in 128x64 I2C (SSD1315)', 'Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical',
     'HS96L03W2C03', 'C5248080', {'1': 'GND', '2': '3V3', '3': 'OLED_SCL', '4': 'OLED_SDA'},
     note='HS HS96L03W2C03 module (datasheet V1.0 s1.4/1.5): pins 1 GND 2 VCC 3 SCL 4 SDA, 2.54 mm; VCC 2.8-3.3 V max (no on-module LDO, 3V3 only); '
          'needs external SCL/SDA pull-ups (R14/R15); PCB 27.3x27.8 mm, 4x d2.5 mm holes on 23.3x23.8 mm. SSD1315 = SSD1306-compatible. '
          'Alt (out of stock): Jixin JX040102-1 C284855, SSD1306 + LDO, 30x29 mm, different hole pattern')
R('ui', '4.7k', '3V3', 'OLED_SCL'); R('ui', '4.7k', '3V3', 'OLED_SDA')
part('ui', nref('SW'), 'RotaryEncoder_Switch', 'EC11E18244A5', 'Rotary_Encoder:RotaryEncoder_Alps_EC11E-Switch_Vertical_H20mm',
     'EC11E18244A5', 'C255515', {'A': 'ENC_A', 'B': 'ENC_B', 'C': 'GND', 'S1': 'ENC_SW', 'S2': 'GND'})
for n in ['ENC_A', 'ENC_B', 'ENC_SW', 'BTN1', 'BTN2']: R('ui', '10k', '3V3', n)
C('ui', '10nF', 'ENC_A', note='debounce'); C('ui', '10nF', 'ENC_B', note='debounce')
part('ui', nref('SW'), 'SW_Push', 'BTN1', FP['SW_B3U'], 'B3U-1000P', 'C231329', {'1': 'BTN1', '2': 'GND'})
part('ui', nref('SW'), 'SW_Push', 'BTN2', FP['SW_B3U'], 'B3U-1000P', 'C231329', {'1': 'BTN2', '2': 'GND'})
R('ui', '1k', 'LED_STAT', 'LED_A')
part('ui', nref('D'), 'LED', 'RED', FP['LED0603'], 'KT-0603R', 'C2286', {'2': 'LED_A', '1': 'GND'}, note='Status LED')

# ---- debug
part('debug', nref('J'), 'TC2030_SWD', 'TC2030-NL', 'Connector:Tag-Connect_TC2030-IDC-NL_2x03_P1.27mm_Vertical', 'TC2030-NL (footprint only)', 'N/A',
     {'1': '3V3', '5': 'GND', '3': 'POR_B', '2': 'SWDIO', '4': 'SWCLK', '6': 'SWO'}, note='Tag-Connect TC2030-CTX mapping')
for n in ['UART_TX', 'UART_RX', 'GND', 'POR_B', 'ONOFF']:
    part('debug', nref('TP'), 'TestPoint', 'TP_' + n, FP['TP'], 'Test pad (no part)', 'N/A', {'1': n})

# ---------------------------------------------------------------- symbol lib text
def unit_geom(pins, hide_names):
    L = [p for p in pins if p[3] == 'L']; Rr = [p for p in pins if p[3] == 'R']
    rows = max(len(L), len(Rr), 1)
    ln = max([len(p[1]) for p in L] + [0]); rn = max([len(p[1]) for p in Rr] + [0])
    if hide_names: hw = G
    else: hw = max(2 * G, math.ceil(((ln + rn) * 1.0 + 3) * 1.27 / 2 / G) * G)
    top = math.floor((rows - 1) / 2) * G
    pos = {}
    for i, p in enumerate(L): pos[p[0] + '|L|' + str(i)] = (-(hw + G), top - i * G, 0)
    for i, p in enumerate(Rr): pos[p[0] + '|R|' + str(i)] = (hw + G, top - i * G, 180)
    h_top = top + G; h_bot = top - (rows - 1) * G - G
    return L, Rr, hw, h_top, h_bot, top
def sym_text(name, libprefix):
    d = SYMS[name]; out = []
    full = f'{libprefix}{name}'
    pn = ' (pin_names (offset 0.508)' + (' (hide yes))' if d['hide_names'] else ')')
    pnum = ' (pin_numbers (hide yes))' if d['hide_nums'] else ''
    power = ''
    out.append(f'(symbol {q(full)}{power}{pnum}{pn} (exclude_from_sim no) (in_bom {"no" if name=="PWR_FLAG" else "yes"}) (on_board {"no" if name=="PWR_FLAG" else "yes"})')
    g0 = unit_geom(d['units'][0], d['hide_names'])
    out.append(f'(property "Reference" {q(d["ref"])} (at 0 {g0[3]+1.27:.2f} 0) {fnt()})')
    out.append(f'(property "Value" {q(name)} (at 0 {g0[4]-1.27:.2f} 0) {fnt()})')
    for k in ['Footprint', 'Datasheet', 'Description']: out.append(f'(property {q(k)} "" (at 0 0 0) {fnt(True)})')
    for ui, pins in enumerate(d['units'], 1):
        L, Rr, hw, ht, hb, top = unit_geom(pins, d['hide_names'])
        out.append(f'(symbol {q(f"{name}_{ui}_1")}')
        if name != 'PWR_FLAG':
            out.append(f'(rectangle (start {-hw:.2f} {ht:.2f}) (end {hw:.2f} {hb:.2f}) (stroke (width 0.254) (type default)) (fill (type background)))')
        for side, lst in (('L', L), ('R', Rr)):
            for i, p in enumerate(lst):
                x = -(hw + G) if side == 'L' else hw + G; y = top - i * G; a = 0 if side == 'L' else 180
                out.append(f'(pin {p[2]} line (at {x:.2f} {y:.2f} {a}) (length {G}) (name {q(p[1])} {fnt()}) (number {q(p[0])} {fnt()}))')
        out.append(')')
    out.append(')')
    return '\n'.join(out)
def pin_points(name, unit):
    pins = SYMS[name]['units'][unit - 1]
    L, Rr, hw, ht, hb, top = unit_geom(pins, SYMS[name]['hide_names'])
    pts = []
    for i, p in enumerate(L): pts.append((p[0], -(hw + G), top - i * G, 'L'))
    for i, p in enumerate(Rr): pts.append((p[0], hw + G, top - i * G, 'R'))
    return pts, hw, ht, hb

# ---------------------------------------------------------------- write libs
os.makedirs(LIB, exist_ok=True)
with open(os.path.join(LIB, 'TokenKey.kicad_sym'), 'w') as f:
    f.write('(kicad_symbol_lib (version 20241209) (generator "tokenkey_gen") (generator_version "9.0")\n')
    for n in SYMS: f.write(sym_text(n, '') + '\n')
    f.write(')\n')
# BGA footprint from DS Fig.53 grid: 14x14, 0.65 mm pitch, A1 top-left, rows A..P (no I,O)
rows = 'ABCDEFGHJKLMNP'
fpl = ['(footprint "NXP_MAPBGA-196_10x10mm_Layout14x14_P0.65mm" (version 20241229) (generator "tokenkey_gen") (generator_version "9.0") (layer "F.Cu")',
       '(descr "NXP 196 MAPBGA 10x10 mm, 0.65 mm pitch (i.MX RT1060 DVL6/CVL5). NXP SOT1546-2 / 98ASA01088D Rev O (balls d0.25-0.35, A 1.43 max). Land per NXP AN4982 Rev 4 s4.2: 0.325 mm Cu NSMD, mask opening 0.450 mm")',
       '(attr smd)',
       f'(property "Reference" "REF**" (at 0 -6.2 0) (layer "F.SilkS") (uuid {q(U())}) (effects (font (size 1 1) (thickness 0.15))))',
       f'(property "Value" "NXP_MAPBGA-196_10x10mm" (at 0 6.2 0) (layer "F.Fab") (uuid {q(U())}) (effects (font (size 1 1) (thickness 0.15))))',
       '(fp_rect (start -5 -5) (end 5 5) (stroke (width 0.1) (type solid)) (fill no) (layer "F.Fab"))',
       '(fp_rect (start -5.25 -5.25) (end 5.25 5.25) (stroke (width 0.05) (type solid)) (fill no) (layer "F.CrtYd"))',
       '(fp_line (start -5.11 -4.2) (end -5.11 -5.11) (stroke (width 0.12) (type solid)) (layer "F.SilkS"))',
       '(fp_line (start -5.11 -5.11) (end -4.2 -5.11) (stroke (width 0.12) (type solid)) (layer "F.SilkS"))',
       '(fp_circle (center -5.6 -5.6) (end -5.45 -5.6) (stroke (width 0.3) (type solid)) (fill yes) (layer "F.SilkS"))']
for ri, r in enumerate(rows):
    for c in range(1, 15):
        x = (c - 7.5) * 0.65; y = (ri - 6.5) * 0.65
        fpl.append(f'(pad "{r}{c}" smd circle (at {x:.3f} {y:.3f}) (size 0.325 0.325) (layers "F.Cu" "F.Paste" "F.Mask") (solder_mask_margin 0.0625) (uuid {q(U())}))')
fpl.append(')')
open(os.path.join(LIB, 'TokenKey.pretty', 'NXP_MAPBGA-196_10x10mm_Layout14x14_P0.65mm.kicad_mod'), 'w').write('\n'.join(fpl) + '\n')

# ---------------------------------------------------------------- write schematics
VER = '(version 20250114) (generator "eeschema") (generator_version "9.0")'
ROOT_UUID = U()
sheet_uuid = {s: U() for s in SHEETS}
def glabel(net, x, y, side):
    ang, just = (180, 'right') if side == 'L' else (0, 'left')
    return (f'(global_label {q(net)} (shape passive) (at {x:.2f} {y:.2f} {ang}) (fields_autoplaced yes) {fnt(False, just)} (uuid {q(U())})'
            f' (property "Intersheetrefs" "${{INTERSHEET_REFS}}" (at {x:.2f} {y:.2f} 0) {fnt(True)}))')
def write_sheet(sname, page):
    items = []; used = set()
    x0, y0, x, y, colw = 30.48, 30.48, 30.48, 30.48, 0
    paper = 'A2' if sname in ('mcu', 'power') else 'A3'
    maxy = 390 if paper == 'A2' else 260
    for p in SHEETS[sname]:
        used.add(p['sym'])
        nunits = p['units'] or 1
        for un in range(1, nunits + 1):
            pts, hw, ht, hb = pin_points(p['sym'], un)
            h = ht - hb + 12.7
            w = 2 * hw + 2 * G + 2 * 25.4
            if y + h > maxy and y > y0:
                x += colw + 5.08; y = y0; colw = 0
            sx = round((x + w / 2) / G) * G; sy = round((y + ht + 5.08) / G) * G
            props = [('Reference', p['ref'], 0, ht + 1.27, False), ('Value', p['value'], 0, hb - 1.27, False),
                     ('Footprint', p['fp'], 0, hb - 3.81, True), ('Datasheet', '', 0, 0, True), ('Description', p['note'], 0, 0, True),
                     ('MPN', p['mpn'], 0, 0, True), ('LCSC', p['lcsc'], 0, 0, True)]
            if p.get('alt'): props += [('MPN_Alt', p['alt'][0], 0, 0, True), ('LCSC_Alt', p['alt'][1], 0, 0, True)]
            pr = ' '.join(f'(property {q(k)} {q(v)} (at {sx+dx:.2f} {sy-dy:.2f} 0) {fnt(hd)})' for k, v, dx, dy, hd in props)
            pinuu = ' '.join(f'(pin {q(pt[0])} (uuid {q(U())}))' for pt in pts)
            lib_id = 'TokenKey:' + p['sym']
            items.append(f'(symbol (lib_id {q(lib_id)}) (at {sx:.2f} {sy:.2f} 0) (unit {un}) (exclude_from_sim no) (in_bom {"no" if p["sym"]=="PWR_FLAG" else "yes"}) '
                         f'(on_board {"no" if p["sym"]=="PWR_FLAG" else "yes"}) (dnp {"yes" if p["dnp"] else "no"}) (uuid {q(U())}) {pr} {pinuu} '
                         f'(instances (project {q(PROJ)} (path {q("/"+ROOT_UUID+"/"+sheet_uuid[sname])} (reference {q(p["ref"])}) (unit {un})))))')
            for num, px, py, side in pts:
                net = p['nets'].get(num, '__missing__')
                assert net != '__missing__', (p['ref'], num)
                ax, ay = sx + px, sy - py
                stype = [pp for pp in SYMS[p['sym']]['units'][un - 1] if pp[0] == num][0][2]
                if net is None:
                    if stype != 'no_connect': items.append(f'(no_connect (at {ax:.2f} {ay:.2f}) (uuid {q(U())}))')
                else:
                    items.append(glabel(net, ax, ay, side))
            colw = max(colw, w); y += h
    libs = '\n'.join(sym_text(n, 'TokenKey:') for n in sorted(used))
    title = f'(title_block (title {q(TITLES[sname])}) (company "TokenKey RT") (rev "A0-draft") (comment 1 "Generated by tools/gen.py - frozen baseline pin map"))'
    txt = f'(kicad_sch {VER} (uuid {q(U())}) (paper {q(paper)}) {title}\n(lib_symbols\n{libs}\n)\n' + '\n'.join(items) + '\n)\n'
    open(os.path.join(SCH, f'{sname}.kicad_sch'), 'w').write(txt)
pages = {}
for i, s in enumerate(SHEETS, 2):
    write_sheet(s, i); pages[s] = i
sheets = []
for i, s in enumerate(SHEETS):
    sx, sy = 30.48 + (i % 3) * 76.2, 40.64 + (i // 3) * 50.8
    sheets.append(f'(sheet (at {sx:.2f} {sy:.2f}) (size 60.96 30.48) (exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no) (fields_autoplaced yes) '
                  f'(stroke (width 0.1524) (type solid)) (fill (color 0 0 0 0.0000)) (uuid {q(sheet_uuid[s])}) '
                  f'(property "Sheetname" {q(s)} (at {sx:.2f} {sy-0.71:.2f} 0) {fnt(False, "left bottom")}) '
                  f'(property "Sheetfile" {q(s+".kicad_sch")} (at {sx:.2f} {sy+31.07:.2f} 0) {fnt(False, "left top")}) '
                  f'(instances (project {q(PROJ)} (path {q("/"+ROOT_UUID)} (page {q(str(pages[s]))})))))')
note = ('(text "TokenKey RT - root sheet. Inter-sheet nets use global labels (same name = same net). '
        'Frozen baseline: docs/pin-map.md. DNP: buck U3/L2/R/C, PSRAM U5 + R/C." (exclude_from_sim no) (at 30.48 20.32 0) '
        f'{fnt(False, "left")} (uuid {q(U())}))')
root = (f'(kicad_sch {VER} (uuid {q(ROOT_UUID)}) (paper "A4") (title_block (title "TokenKey RT - i.MX RT1062 USB accessory") (rev "A0-draft") (company "TokenKey RT"))\n'
        '(lib_symbols)\n' + note + '\n' + '\n'.join(sheets) + '\n(sheet_instances (path "/" (page "1")))\n(embedded_fonts no)\n)\n')
open(os.path.join(SCH, f'{PROJ}.kicad_sch'), 'w').write(root)
open(os.path.join(SCH, 'sym-lib-table'), 'w').write('(sym_lib_table (version 7)\n  (lib (name "TokenKey")(type "KiCad")(uri "${KIPRJMOD}/../libraries/TokenKey.kicad_sym")(options "")(descr "TokenKey RT project symbols"))\n)\n')
open(os.path.join(SCH, 'fp-lib-table'), 'w').write('(fp_lib_table (version 7)\n  (lib (name "TokenKey")(type "KiCad")(uri "${KIPRJMOD}/../libraries/TokenKey.pretty")(options "")(descr "TokenKey RT project footprints"))\n)\n')
pro = {"meta": {"filename": f"{PROJ}.kicad_pro", "version": 3}, "schematic": {"legacy_lib_dir": "", "legacy_lib_list": []},
       "sheets": [[ROOT_UUID, "Root"]] + [[sheet_uuid[s], s] for s in SHEETS], "boards": [], "libraries": {"pinned_footprint_libs": [], "pinned_symbol_libs": []}}
json.dump(pro, open(os.path.join(SCH, f'{PROJ}.kicad_pro'), 'w'), indent=2)
json.dump({s: SHEETS[s] for s in SHEETS}, open(os.path.join(ROOT, 'tools/netlist.json'), 'w'), indent=1, default=str)
print('parts', {s: len(v) for s, v in SHEETS.items()})
