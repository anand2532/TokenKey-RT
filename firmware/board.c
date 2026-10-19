/*
 * TokenKey RT - board support: clocks/power, pin mux, debug UART, LED, OCOTP, RTWDOG.
 *
 * Register-level on purpose (no fsl_clock/fsl_iomuxc): the only NXP files used are the
 * CMSIS device headers in third_party/nxp. Register sequences follow the MCUXpresso SDK
 * (fsl_clock.c, EVKB BOARD_BootClockRUN) and IMXRT1060RM Rev.3.
 */
#include "board.h"
#include "fsl_device_registers.h"

uint32_t SystemCoreClock = 24000000u; /* CMSIS; updated by clock_init() */

static tk_clock_info_t s_clk;
static bool s_uart_ready; /* fault handlers may run before uart_init() */

/* ------------------------------------------------------------------------------------------ */
/* Pin mux                                                                                     */
/* ------------------------------------------------------------------------------------------ */
/* SW_MUX_CTL: MUX_MODE[2:0], SION[4]. SW_PAD_CTL: SRE[0] DSE[5:3] SPEED[7:6] ODE[11] PKE[12]
 * PUE[13] PUS[15:14] HYS[16]. */
#define MUX_ALT2      2u
#define MUX_ALT3      3u
#define MUX_ALT5      5u
#define MUX_SION      (1u << 4)
#define PAD_DSE(x)    ((uint32_t)(x) << 3)
#define PAD_SPEED(x)  ((uint32_t)(x) << 6)
#define PAD_ODE       (1u << 11)
#define PAD_PKE       (1u << 12)
#define PAD_HYS       (1u << 16)

/* Inputs with external 10k pull-ups (+10nF on ENC_A/B): internal pull/keeper disabled, hysteresis on. */
#define PAD_IN_EXT_PU (PAD_HYS | PAD_SPEED(2) | PAD_DSE(6))
/* I2C with external 4.7k pull-ups: open drain, no internal pull. */
#define PAD_I2C       (PAD_HYS | PAD_ODE | PAD_SPEED(2) | PAD_DSE(6))
/* LED push-pull and UART: NXP default 0x10B0 (keeper, 100 MHz, R0/6). */
#define PAD_PUSHPULL  (PAD_PKE | PAD_SPEED(2) | PAD_DSE(6))

static void pin(uint32_t mux_idx, uint32_t pad_idx, uint32_t mux, uint32_t pad)
{
    IOMUXC->SW_MUX_CTL_PAD[mux_idx] = mux;
    IOMUXC->SW_PAD_CTL_PAD[pad_idx] = pad;
}

static void pinmux_init(void)
{
    CCM->CCGR4 |= CCM_CCGR4_CG1_MASK; /* iomuxc */

    /* OLED on LPI2C1: J11 GPIO_AD_B1_00 ALT3 SCL, K11 GPIO_AD_B1_01 ALT3 SDA, SION=1. */
    pin(kIOMUXC_SW_MUX_CTL_PAD_GPIO_AD_B1_00, kIOMUXC_SW_PAD_CTL_PAD_GPIO_AD_B1_00, MUX_ALT3 | MUX_SION, PAD_I2C);
    pin(kIOMUXC_SW_MUX_CTL_PAD_GPIO_AD_B1_01, kIOMUXC_SW_PAD_CTL_PAD_GPIO_AD_B1_01, MUX_ALT3 | MUX_SION, PAD_I2C);
    IOMUXC->SELECT_INPUT[kIOMUXC_LPI2C1_SCL_SELECT_INPUT] = 1u; /* daisy: GPIO_AD_B1_00 */
    IOMUXC->SELECT_INPUT[kIOMUXC_LPI2C1_SDA_SELECT_INPUT] = 1u; /* daisy: GPIO_AD_B1_01 */

    /* Encoder / buttons, GPIO1_IO18..22, ALT5, external pull-ups, active low. */
    pin(kIOMUXC_SW_MUX_CTL_PAD_GPIO_AD_B1_02, kIOMUXC_SW_PAD_CTL_PAD_GPIO_AD_B1_02, MUX_ALT5, PAD_IN_EXT_PU); /* L11 ENC_A  */
    pin(kIOMUXC_SW_MUX_CTL_PAD_GPIO_AD_B1_03, kIOMUXC_SW_PAD_CTL_PAD_GPIO_AD_B1_03, MUX_ALT5, PAD_IN_EXT_PU); /* M12 ENC_B  */
    pin(kIOMUXC_SW_MUX_CTL_PAD_GPIO_AD_B1_04, kIOMUXC_SW_PAD_CTL_PAD_GPIO_AD_B1_04, MUX_ALT5, PAD_IN_EXT_PU); /* L12 ENC_SW */
    pin(kIOMUXC_SW_MUX_CTL_PAD_GPIO_AD_B1_05, kIOMUXC_SW_PAD_CTL_PAD_GPIO_AD_B1_05, MUX_ALT5, PAD_IN_EXT_PU); /* K12 BTN1   */
    pin(kIOMUXC_SW_MUX_CTL_PAD_GPIO_AD_B1_06, kIOMUXC_SW_PAD_CTL_PAD_GPIO_AD_B1_06, MUX_ALT5, PAD_IN_EXT_PU); /* J12 BTN2   */

    /* LED_STAT: H13 GPIO_AD_B1_08 ALT5 GPIO1_IO24 (docs/pin-map.md moved it from K10/AD_B1_07). */
    pin(kIOMUXC_SW_MUX_CTL_PAD_GPIO_AD_B1_08, kIOMUXC_SW_PAD_CTL_PAD_GPIO_AD_B1_08, MUX_ALT5, PAD_PUSHPULL);

    /* Debug UART: K14 GPIO_AD_B0_12 ALT2 LPUART1_TX, L14 GPIO_AD_B0_13 ALT2 LPUART1_RX (no daisy on RT1060). */
    pin(kIOMUXC_SW_MUX_CTL_PAD_GPIO_AD_B0_12, kIOMUXC_SW_PAD_CTL_PAD_GPIO_AD_B0_12, MUX_ALT2, PAD_PUSHPULL);
    pin(kIOMUXC_SW_MUX_CTL_PAD_GPIO_AD_B0_13, kIOMUXC_SW_PAD_CTL_PAD_GPIO_AD_B0_13, MUX_ALT2, PAD_PUSHPULL);

    /* Deliberately NOT touched:
     *  - GPIO_AD_B0_04 / _05 (F11 BOOT_MODE0, G14 BOOT_MODE1): strap pins, never driven by firmware.
     *  - GPIO_AD_B0_06 / _07 (SWDIO/SWCLK) and GPIO_AD_B0_10 (G13 SWO): stay in JTAG/SWD mux from reset.
     *  - GPIO_SD_B1_xx (FlexSPI A, configured by the boot ROM from the FCB). */
}

/* ------------------------------------------------------------------------------------------ */
/* Clocks and power                                                                            */
/* ------------------------------------------------------------------------------------------ */
#define DCDC_TRG(mv)  ((uint8_t)(((mv) - 800u) / 25u)) /* DCDC_REG3[TRG]: 0.8 V + 25 mV/step (RM 0xE = 1.15 V) */

/* DVL6B 600 MHz "overdrive": VDD_SOC_IN 1.25..1.3 V (IMXRT1060CEC Table 10); SDK uses 1.275 V. */
#define TK_DVL6B_SOC_MV   1275u
/* CVL5B 528 MHz: VDD_SOC = 1.225 V, PM-approved setpoint (issue #30), inside the CVL5B
 * VDD_SOC_IN limit of 1.26 V (IMXRT1060IEC); min 1.15 V. 1.225 V sits 75 mV above min and 35 mV
 * below max. Override with -DTK_CVL5B_SOC_MV=... only with bench data; the guard below keeps
 * any override at or below 1.25 V. */
#ifndef TK_CVL5B_SOC_MV
#define TK_CVL5B_SOC_MV   1225u
#endif
#if (TK_CVL5B_SOC_MV > 1250u) || (TK_CVL5B_SOC_MV < 1150u)
#error "TK_CVL5B_SOC_MV must stay within 1.15..1.25 V (CVL5B limit 1.26 V; approved 1.225 V)"
#endif

#define ARM_PLL_DIV_600   100u /* 24 MHz * 100 / 2 = 1200 MHz, ARM_PODF /2 -> 600 MHz */
#define ARM_PLL_DIV_528    88u /* 24 MHz *  88 / 2 = 1056 MHz, ARM_PODF /2 -> 528 MHz */

/* OCOTP 0x440 (CFG3) [17:16] SPEED_GRADING[1:0], "burned by tester program, for indicating IC
 * core speed": 00 reserved, 01 = 500 MHz (P/N code 05), 10 = 600 MHz (P/N code 06), 11 reserved.
 * Verified against NXP IMXRT1060RM Rev. 3, 07/2021, chapter 22 "Fusemap", section 22.3
 * "Fusemap Descriptions Table", Table 22-9, p.1301 (fetched 2026-10-19 from
 * https://www.pjrc.com/teensy/IMXRT1060RM_rev3.pdf). Shadow register: OCOTP->CFG3 at offset
 * 0x440 (MIMXRT1062.h). Only 10 enables 600 MHz; 01, reserved codes or a bad read -> 528 MHz. */
#define SPEED_GRADE_5     1u
#define SPEED_GRADE_6     2u

#define CDHIPR_BUSY_MASK  (CCM_CDHIPR_SEMC_PODF_BUSY_MASK | CCM_CDHIPR_AHB_PODF_BUSY_MASK | \
                           CCM_CDHIPR_PERIPH2_CLK_SEL_BUSY_MASK | CCM_CDHIPR_PERIPH_CLK_SEL_BUSY_MASK | \
                           CCM_CDHIPR_ARM_PODF_BUSY_MASK)

static void ccm_wait(void)
{
    while ((CCM->CDHIPR & CDHIPR_BUSY_MASK) != 0u) {
    }
}

static uint8_t fuse_speed_grade(void)
{
    CCM->CCGR2 |= CCM_CCGR2_CG6_MASK; /* ocotp_ctrl clock (shadow registers) */
    return (uint8_t)((OCOTP->CFG3 >> 16) & 0x3u);
}

static void dcdc_set_mv(uint32_t mv)
{
    uint8_t trg = DCDC_TRG(mv);
    DCDC->REG3 = (DCDC->REG3 & ~DCDC_REG3_TRG_MASK) | DCDC_REG3_TRG(trg);
    while ((DCDC->REG0 & DCDC_REG0_STS_DC_OK_MASK) == 0u) {
    }
    s_clk.dcdc_trg = trg;
}

static void clock_init(void)
{
    /* ---- 1. decide the operating point BEFORE touching anything ------------------------- */
    s_clk.fuse_speed_grade = fuse_speed_grade();
#if defined(TK_PART_DVL6B) && TK_PART_DVL6B
    /* Build says DVL6B. Go to 600 MHz only if the fuses positively confirm the 600 MHz grade;
     * anything else (500 class, reserved, unreadable) -> 528 MHz guard @ 1.225 V (PM-approved,
     * inside the CVL5B 1.26 V limit, so a mis-built CVL5B board is still in spec). */
    bool go600 = (s_clk.fuse_speed_grade == SPEED_GRADE_6);
    s_clk.fell_back = !go600;
#else
    /* Build says CVL5B: 528 MHz guard. 528 MHz unconditionally, whatever the fuses read; the
     * 600 MHz path is not even compiled in. VDD_SOC = TK_CVL5B_SOC_MV = 1.225 V (PM-approved,
     * inside the CVL5B 1.26 V limit). The 528 MHz fallback on DVL6B builds uses the same 1.225 V. */
    const bool go600 = false;
    s_clk.fell_back = false;
#endif

    /* ---- 2. 24 MHz crystal, run everything from OSC while PLL/voltage change -------------- */
    CCM_ANALOG->MISC0_CLR = CCM_ANALOG_MISC0_XTAL_24M_PWD_MASK;
    while ((XTALOSC24M->LOWPWR_CTRL & XTALOSC24M_LOWPWR_CTRL_XTALOSC_PWRUP_STAT_MASK) == 0u) {
    }
    CCM_ANALOG->MISC0_SET = CCM_ANALOG_MISC0_OSC_XTALOK_EN_MASK;
    while ((CCM_ANALOG->MISC0 & CCM_ANALOG_MISC0_OSC_XTALOK_MASK) == 0u) {
    }
    CCM_ANALOG->MISC0_CLR = CCM_ANALOG_MISC0_OSC_XTALOK_EN_MASK;
    XTALOSC24M->LOWPWR_CTRL_CLR = XTALOSC24M_LOWPWR_CTRL_CLR_OSC_SEL_MASK; /* select XTAL */
    CCM->CCR = (CCM->CCR & ~CCM_CCR_OSCNT_MASK) | CCM_CCR_OSCNT(127);

    CCM->CBCMR = (CCM->CBCMR & ~CCM_CBCMR_PERIPH_CLK2_SEL_MASK) | CCM_CBCMR_PERIPH_CLK2_SEL(1); /* osc */
    CCM->CBCDR = (CCM->CBCDR & ~CCM_CBCDR_PERIPH_CLK2_PODF_MASK) | CCM_CBCDR_PERIPH_CLK2_PODF(0);
    CCM->CBCDR |= CCM_CBCDR_PERIPH_CLK_SEL_MASK; /* periph_clk <- periph_clk2 (24 MHz) */
    ccm_wait();

    /* ---- 3. voltage first (we are at 24 MHz now, so lowering is also safe) -------------- */
    dcdc_set_mv(go600 ? TK_DVL6B_SOC_MV : TK_CVL5B_SOC_MV);
    board_delay_us(100);

    /* ---- 4. bus dividers: AHB /1, IPG /4 (<=150 MHz), ARM_PODF /2 ------------------------ */
    CCM->CBCDR = (CCM->CBCDR & ~(CCM_CBCDR_AHB_PODF_MASK | CCM_CBCDR_IPG_PODF_MASK)) |
                 CCM_CBCDR_AHB_PODF(0) | CCM_CBCDR_IPG_PODF(3);
    ccm_wait();
    CCM->CACRR = CCM_CACRR_ARM_PODF(1);
    ccm_wait();

    /* ---- 5. ARM PLL (PLL1): bypass, program, lock, un-bypass ------------------------------ */
    uint32_t div = go600 ? ARM_PLL_DIV_600 : ARM_PLL_DIV_528;
    CCM_ANALOG->PLL_ARM = (CCM_ANALOG->PLL_ARM & ~CCM_ANALOG_PLL_ARM_BYPASS_CLK_SRC_MASK) |
                          CCM_ANALOG_PLL_ARM_BYPASS_MASK | CCM_ANALOG_PLL_ARM_BYPASS_CLK_SRC(0);
    CCM_ANALOG->PLL_ARM = (CCM_ANALOG->PLL_ARM & ~(CCM_ANALOG_PLL_ARM_DIV_SELECT_MASK | CCM_ANALOG_PLL_ARM_POWERDOWN_MASK)) |
                          CCM_ANALOG_PLL_ARM_ENABLE_MASK | CCM_ANALOG_PLL_ARM_DIV_SELECT(div);
    while ((CCM_ANALOG->PLL_ARM & CCM_ANALOG_PLL_ARM_LOCK_MASK) == 0u) {
    }
    CCM_ANALOG->PLL_ARM &= ~CCM_ANALOG_PLL_ARM_BYPASS_MASK;

    /* ---- 6. core <- pre_periph <- divided PLL1 ----------------------------------------- */
    CCM->CBCMR = (CCM->CBCMR & ~CCM_CBCMR_PRE_PERIPH_CLK_SEL_MASK) | CCM_CBCMR_PRE_PERIPH_CLK_SEL(3);
    ccm_wait();
    CCM->CBCDR &= ~CCM_CBCDR_PERIPH_CLK_SEL_MASK;
    ccm_wait();

    /* FlexSPI clock root (set by the boot ROM from the FCB, we are executing from it) and
     * SEMC are intentionally left untouched. */

    /* ---- 7. peripheral roots from the 24 MHz OSC (gate off while switching) --------------- */
    CCM->CCGR5 &= ~CCM_CCGR5_CG12_MASK; /* lpuart1 */
    CCM->CCGR2 &= ~CCM_CCGR2_CG3_MASK;  /* lpi2c1 */
    CCM->CSCDR1 = (CCM->CSCDR1 & ~(CCM_CSCDR1_UART_CLK_SEL_MASK | CCM_CSCDR1_UART_CLK_PODF_MASK)) |
                  CCM_CSCDR1_UART_CLK_SEL(1) | CCM_CSCDR1_UART_CLK_PODF(0);       /* 24 MHz */
    CCM->CSCDR2 = (CCM->CSCDR2 & ~(CCM_CSCDR2_LPI2C_CLK_SEL_MASK | CCM_CSCDR2_LPI2C_CLK_PODF_MASK)) |
                  CCM_CSCDR2_LPI2C_CLK_SEL(1) | CCM_CSCDR2_LPI2C_CLK_PODF(0);     /* 24 MHz */
    CCM->CSCMR1 = (CCM->CSCMR1 & ~(CCM_CSCMR1_PERCLK_CLK_SEL_MASK | CCM_CSCMR1_PERCLK_PODF_MASK)) |
                  CCM_CSCMR1_PERCLK_CLK_SEL(1) | CCM_CSCMR1_PERCLK_PODF(0);       /* 24 MHz (PIT/GPT) */

    s_clk.part = go600 ? TK_PART_ID_DVL6B : TK_PART_ID_CVL5B;
    s_clk.core_hz = go600 ? 600000000u : 528000000u;
    SystemCoreClock = s_clk.core_hz;
}

const tk_clock_info_t *board_clock_info(void) { return &s_clk; }

/* ------------------------------------------------------------------------------------------ */
/* Debug UART: LPUART1 115200 8N1 from 24 MHz: OSR=16, SBR=13 -> 115385 baud (+0.16 %)         */
/* ------------------------------------------------------------------------------------------ */
static void uart_init(void)
{
    CCM->CCGR5 |= CCM_CCGR5_CG12_MASK;
    LPUART1->GLOBAL = LPUART_GLOBAL_RST_MASK;
    LPUART1->GLOBAL = 0;
    LPUART1->BAUD = LPUART_BAUD_OSR(15) | LPUART_BAUD_SBR(13);
    LPUART1->CTRL = LPUART_CTRL_TE_MASK | LPUART_CTRL_RE_MASK;
    s_uart_ready = true;
}

void board_uart_puts(const char *s)
{
    if (!s_uart_ready) {
        return;
    }
    while (*s) {
        while ((LPUART1->STAT & LPUART_STAT_TDRE_MASK) == 0u) {
        }
        LPUART1->DATA = (uint8_t)*s++;
    }
}

void board_uart_puthex(uint32_t v)
{
    char b[11] = "0x";
    for (int i = 0; i < 8; i++) {
        uint32_t n = (v >> (28 - 4 * i)) & 0xFu;
        b[2 + i] = (char)(n < 10 ? '0' + n : 'A' + n - 10);
    }
    b[10] = 0;
    board_uart_puts(b);
}

/* ------------------------------------------------------------------------------------------ */
/* GPIO                                                                                        */
/* ------------------------------------------------------------------------------------------ */
static void gpio_init(void)
{
    CCM->CCGR1 |= CCM_CCGR1_CG13_MASK; /* gpio1 */
    /* IOMUXC_GPR_GPR26 left at reset (0): these pads are routed to GPIO1, not fast GPIO6. */
    GPIO1->DR_CLEAR = 1u << TK_PIN_LED;
    GPIO1->GDIR = (GPIO1->GDIR | (1u << TK_PIN_LED)) & ~TK_INPUT_PIN_MASK;
    GPIO1->IMR &= ~TK_INPUT_PIN_MASK;      /* enabled later by input_init() */
    GPIO1->EDGE_SEL |= TK_INPUT_PIN_MASK;  /* any edge (overrides ICR) */
    GPIO1->ISR = TK_INPUT_PIN_MASK;        /* w1c */
}

void board_led_set(bool on)
{
    if (on) {
        GPIO1->DR_SET = 1u << TK_PIN_LED;
    } else {
        GPIO1->DR_CLEAR = 1u << TK_PIN_LED;
    }
}

uint32_t board_gpio1_read(void) { return GPIO1->PSR; }

uint64_t board_unique_id(void) { return ((uint64_t)OCOTP->CFG1 << 32) | OCOTP->CFG0; }

/* ------------------------------------------------------------------------------------------ */
/* RTWDOG (WDOG3). Clock: LPO = 32.768 kHz (RM 58.1). TOVAL is 16 bit -> max ~2 s.             */
/* ------------------------------------------------------------------------------------------ */
void board_wdog_start(uint32_t timeout_ms)
{
    uint32_t toval = (timeout_ms * 32768u) / 1000u;
    if (toval > 0xFFFFu) {
        toval = 0xFFFFu;
    }
    uint32_t primask = __get_PRIMASK();
    __disable_irq(); /* unlock -> reconfigure must complete within 255 bus clocks */
    RTWDOG->CNT = 0xD928C520u;
    while ((RTWDOG->CS & RTWDOG_CS_ULK_MASK) == 0u) {
    }
    RTWDOG->WIN = 0;
    RTWDOG->TOVAL = toval;
    /* DBG=0: watchdog halted while the core is halted by a debugger. */
    RTWDOG->CS = RTWDOG_CS_EN_MASK | RTWDOG_CS_CLK(1) | RTWDOG_CS_UPDATE_MASK | RTWDOG_CS_CMD32EN_MASK;
    while ((RTWDOG->CS & RTWDOG_CS_RCS_MASK) == 0u) {
    }
    __set_PRIMASK(primask);
}

void board_wdog_feed(void) { RTWDOG->CNT = 0xB480A602u; }

/* ------------------------------------------------------------------------------------------ */
void board_delay_us(uint32_t us)
{
    uint32_t start = DWT->CYCCNT;
    uint32_t ticks = us * (SystemCoreClock / 1000000u);
    while ((DWT->CYCCNT - start) < ticks) {
    }
}

static void dwt_init(void)
{
    CoreDebug->DEMCR |= CoreDebug_DEMCR_TRCENA_Msk;
    DWT->LAR = 0xC5ACCE55u; /* CoreSight unlock (M7) */
    DWT->CYCCNT = 0;
    DWT->CTRL |= DWT_CTRL_CYCCNTENA_Msk;
}

void board_init(void)
{
    dwt_init();
    clock_init();
    pinmux_init();
    gpio_init();
    uart_init();

    board_uart_puts("\r\nTokenKey RT fw " TK_FW_VERSION_STR " (" TK_BUILD_ID ")\r\n");
    board_uart_puts("part=");
    board_uart_puts(s_clk.part == TK_PART_ID_DVL6B ? "DVL6B" : "CVL5B");
    board_uart_puts(s_clk.core_hz == 600000000u ? " core=600MHz" : " core=528MHz");
    board_uart_puts(" fuse_sg=");
    board_uart_puthex(s_clk.fuse_speed_grade);
    board_uart_puts(" dcdc_trg=");
    board_uart_puthex(DCDC->REG3 & DCDC_REG3_TRG_MASK);
    if (s_clk.fell_back) {
        board_uart_puts(" (DVL6B build, fuses not 600 MHz grade -> 528 MHz fallback)");
    }
    board_uart_puts("\r\n");
}
