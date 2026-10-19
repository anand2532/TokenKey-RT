/*
 * TokenKey RT - startup: vector table, Reset_Handler, FlexRAM, watchdogs, C runtime, FPU,
 * MPU, caches.
 */
#include <stdint.h>
#include <string.h>
#include "fsl_device_registers.h"
#include "board.h"

extern uint32_t _estack, __vector_table;
extern uint32_t __data_start, __data_end, __data_load;
extern uint32_t __ramfunc_start, __ramfunc_end, __ramfunc_load;
extern uint32_t __bss_start, __bss_end, __ocram_bss_start, __ocram_bss_end;

extern int main(void);
void Reset_Handler(void);
void reset_c(void);

/* ---- exception / IRQ handlers ---------------------------------------------------------- */
__attribute__((noreturn)) static void fault_halt(const char *what)
{
    __disable_irq();
    board_uart_puts("\r\n*** ");
    board_uart_puts(what);
    board_uart_puts(" CFSR=");
    board_uart_puthex(SCB->CFSR);
    board_uart_puts(" HFSR=");
    board_uart_puthex(SCB->HFSR);
    board_uart_puts(" MMFAR=");
    board_uart_puthex(SCB->MMFAR);
    board_uart_puts(" BFAR=");
    board_uart_puthex(SCB->BFAR);
    board_uart_puts("\r\n");
    for (;;) {
        /* RTWDOG (if started) resets the chip; with a debugger attached it is halted. */
    }
}

void Default_Handler(void) { fault_halt("unhandled IRQ"); }
void NMI_Handler(void) { fault_halt("NMI"); }
void HardFault_Handler(void) { fault_halt("HardFault"); }
void MemManage_Handler(void) { fault_halt("MemManage"); }
void BusFault_Handler(void) { fault_halt("BusFault"); }
void UsageFault_Handler(void) { fault_halt("UsageFault"); }
void DebugMon_Handler(void) { fault_halt("DebugMon"); }

/* FreeRTOS port handlers (names mapped in FreeRTOSConfig.h) */
void SVC_Handler(void);
void PendSV_Handler(void);
void SysTick_Handler(void);

/* Device IRQs used by the firmware (defined in usb_vendor.c / input.c) */
void USB_OTG1_IRQHandler(void);
void GPIO1_Combined_16_31_IRQHandler(void);

typedef void (*vector_t)(void);

#define IRQ(n) (16 + (n))
__attribute__((used, section(".isr_vector"), aligned(1024)))
const vector_t g_vectors[NUMBER_OF_INT_VECTORS] = {
    [0] = (vector_t)(uintptr_t)&_estack, /* also re-read by FreeRTOS to reset MSP */
    [1] = Reset_Handler,
    [2] = NMI_Handler,
    [3] = HardFault_Handler,
    [4] = MemManage_Handler,
    [5] = BusFault_Handler,
    [6] = UsageFault_Handler,
    [11] = SVC_Handler,
    [12] = DebugMon_Handler,
    [14] = PendSV_Handler,
    [15] = SysTick_Handler,
    [IRQ(USB_OTG1_IRQn)] = USB_OTG1_IRQHandler,
    [IRQ(GPIO1_Combined_16_31_IRQn)] = GPIO1_Combined_16_31_IRQHandler,
};

/* ---- Reset ------------------------------------------------------------------------------ */
/*
 * FlexRAM must be re-banked before anything touches the stack: _estack is the top of a
 * 256 KB DTCM, which does not exist with the fuse default (128 KB DTCM). So the first part
 * is register-only assembly.
 *   GPR17 = 0x5AAFFAA5 : banks {O O D D D D I I I I D D D D O O} (RM fusemap 0x6D0 entry 1000b)
 *                        -> DTCM 256 KB, ITCM 128 KB, OCRAM 128 KB
 *   GPR16 |= FLEXRAM_BANK_CFG_SEL (use GPR17 instead of the fuses)
 *   GPR14[23:20] CM7_CFGDTCMSZ = 0x9 (256 KB), [19:16] CM7_CFGITCMSZ = 0x8 (128 KB)
 *                        (AN12077; reserved/undocumented in IMXRT1060RM Rev.3)
 */
__attribute__((naked, noreturn)) void Reset_Handler(void)
{
    __asm volatile(
        "cpsid i                 \n"
        "ldr   r0, =0x400AC000   \n" /* IOMUXC_GPR */
        "ldr   r1, =0x5AAFFAA5   \n"
        "str   r1, [r0, #0x44]   \n" /* GPR17 */
        "ldr   r1, [r0, #0x40]   \n"
        "orr   r1, r1, #4        \n"
        "str   r1, [r0, #0x40]   \n" /* GPR16 */
        "ldr   r1, [r0, #0x38]   \n"
        "bic   r1, r1, #0x00FF0000 \n"
        "orr   r1, r1, #0x00980000 \n"
        "str   r1, [r0, #0x38]   \n" /* GPR14 */
        "dsb                     \n"
        "isb                     \n"
        "ldr   r0, =_estack      \n"
        "msr   msp, r0           \n"
        "bl    reset_c           \n"
        "b     .                 \n");
}

static void watchdogs_off(void)
{
    /* WDOG1/WDOG2: clear the 16 s power-down counter and WDE if the ROM/fuses set it. */
    WDOG1->WMCR = 0;
    WDOG2->WMCR = 0;
    if (WDOG1->WCR & WDOG_WCR_WDE_MASK) {
        WDOG1->WCR &= ~(uint16_t)WDOG_WCR_WDE_MASK;
    }
    if (WDOG2->WCR & WDOG_WCR_WDE_MASK) {
        WDOG2->WCR &= ~(uint16_t)WDOG_WCR_WDE_MASK;
    }
    /* RTWDOG: unlock, max timeout, disable, keep UPDATE=1 so main() can re-enable it. */
    if (RTWDOG->CS & RTWDOG_CS_CMD32EN_MASK) {
        RTWDOG->CNT = 0xD928C520u;
    } else {
        RTWDOG->CNT = 0xC520u;
        RTWDOG->CNT = 0xD928u;
    }
    RTWDOG->TOVAL = 0xFFFFu;
    RTWDOG->CS = (RTWDOG->CS & ~RTWDOG_CS_EN_MASK) | RTWDOG_CS_UPDATE_MASK;
}

static void mpu_init(void)
{
    ARM_MPU_Disable();
    /* 0: whole 0x6000_0000 window (FlexSPI AMBA + unused) as device, XN: stop speculation */
    MPU->RBAR = ARM_MPU_RBAR(0, 0x60000000u);
    MPU->RASR = ARM_MPU_RASR(1, ARM_MPU_AP_FULL, 0, 0, 0, 1, 0, ARM_MPU_REGION_SIZE_512MB);
    /* 1: SEMC window (nothing fitted) as device, XN */
    MPU->RBAR = ARM_MPU_RBAR(1, 0x80000000u);
    MPU->RASR = ARM_MPU_RASR(1, ARM_MPU_AP_FULL, 0, 0, 0, 1, 0, ARM_MPU_REGION_SIZE_512MB);
    /* 2: the 8 MB QSPI NOR: normal, write-back, read-only, executable */
    MPU->RBAR = ARM_MPU_RBAR(2, 0x60000000u);
    MPU->RASR = ARM_MPU_RASR(0, ARM_MPU_AP_RO, 0, 0, 1, 1, 0, ARM_MPU_REGION_SIZE_8MB);
    /* 3: OCRAM2 + FlexRAM OCRAM: normal, WBWA (TEX=1,C=1,B=1) */
    MPU->RBAR = ARM_MPU_RBAR(3, 0x20200000u);
    MPU->RASR = ARM_MPU_RASR(0, ARM_MPU_AP_FULL, 1, 0, 1, 1, 0, ARM_MPU_REGION_SIZE_1MB);
    /* ITCM/DTCM are never cached; peripherals use the default (device) map. */
    ARM_MPU_Enable(MPU_CTRL_PRIVDEFENA_Msk);
}

void reset_c(void)
{
    watchdogs_off();

    SCB->CPACR |= (3uL << 20) | (3uL << 22); /* CP10/CP11 full access: FPU on */
    __DSB();
    __ISB();
    SCB->VTOR = (uint32_t)&__vector_table;

    /* C runtime: .ramfunc -> ITCM, .data -> DTCM, zero .bss / .ocram_bss */
    for (uint32_t *s = &__ramfunc_load, *d = &__ramfunc_start; d < &__ramfunc_end;) {
        *d++ = *s++;
    }
    for (uint32_t *s = &__data_load, *d = &__data_start; d < &__data_end;) {
        *d++ = *s++;
    }
    for (uint32_t *d = &__bss_start; d < &__bss_end;) {
        *d++ = 0;
    }
    for (uint32_t *d = &__ocram_bss_start; d < &__ocram_bss_end;) {
        *d++ = 0;
    }

    mpu_init();
    SCB_EnableICache();
    SCB_EnableDCache();

    /* Interrupts stay masked (cpsid i in Reset_Handler); the FreeRTOS scheduler unmasks them
     * when the first task starts, so no ISR can run before the queues exist. */
    (void)main();
    for (;;) {
    }
}
