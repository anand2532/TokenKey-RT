/*
 * TokenKey RT - FreeRTOS kernel configuration (FreeRTOS-Kernel V11.1.0, GCC/ARM_CM7/r0p1).
 *
 * Fully static: configSUPPORT_DYNAMIC_ALLOCATION = 0, no heap_x.c is linked, every task,
 * queue and event group is created with the ...Static() API from buffers in .bss (DTCM).
 */
#ifndef FREERTOS_CONFIG_H
#define FREERTOS_CONFIG_H

#if defined(__GNUC__) && !defined(__ASSEMBLER__)
#include <stdint.h>
extern uint32_t SystemCoreClock; /* board.c, set to 600/528 MHz before the scheduler starts */
void tk_assert_failed(const char *file, int line);
#endif

/* ---- scheduler ------------------------------------------------------------------------ */
#define configUSE_PREEMPTION                    1
#define configUSE_TIME_SLICING                  1
#define configUSE_PORT_OPTIMISED_TASK_SELECTION 1         /* CLZ based, max 32 priorities */
#define configCPU_CLOCK_HZ                      (SystemCoreClock) /* SysTick runs from the core clock */
#define configTICK_RATE_HZ                      1000      /* 1 ms tick = input_task debounce clock */
#define configMAX_PRIORITIES                    6         /* 0 idle .. 5; see README for the task table */
#define configMINIMAL_STACK_SIZE                128       /* words */
#define configMAX_TASK_NAME_LEN                 12
#define configTICK_TYPE_WIDTH_IN_BITS           TICK_TYPE_WIDTH_32_BITS
#define configIDLE_SHOULD_YIELD                 1
#define configUSE_TASK_NOTIFICATIONS            1
#define configTASK_NOTIFICATION_ARRAY_ENTRIES   1

/* ---- memory: static only ------------------------------------------------------------- */
#define configSUPPORT_STATIC_ALLOCATION         1
#define configSUPPORT_DYNAMIC_ALLOCATION        0         /* no pvPortMalloc, no heap */
#define configKERNEL_PROVIDED_STATIC_MEMORY     0         /* idle task memory comes from main.c */
#define configAPPLICATION_ALLOCATED_HEAP        0

/* ---- features ------------------------------------------------------------------------ */
#define configUSE_MUTEXES                       1         /* TinyUSB OSAL */
#define configUSE_RECURSIVE_MUTEXES             0
#define configUSE_COUNTING_SEMAPHORES           0
#define configUSE_QUEUE_SETS                    0
#define configQUEUE_REGISTRY_SIZE               0
#define configUSE_TIMERS                        0         /* no timer task; nothing needs it yet */
#define configUSE_EVENT_GROUPS                  1         /* watchdog check-ins */
#define configUSE_STREAM_BUFFERS                0
#define configUSE_CO_ROUTINES                   0
#define configUSE_NEWLIB_REENTRANT              0         /* no printf/malloc in tasks */

/* ---- hooks / debugging --------------------------------------------------------------- */
#define configUSE_IDLE_HOOK                     0
#define configUSE_TICK_HOOK                     0
#define configUSE_MALLOC_FAILED_HOOK            0
#define configCHECK_FOR_STACK_OVERFLOW          2         /* pattern check -> vApplicationStackOverflowHook */
#define configUSE_TRACE_FACILITY                0
#define configGENERATE_RUN_TIME_STATS           0
#define configRECORD_STACK_HIGH_ADDRESS         1
#define configASSERT(x)                         do { if (!(x)) tk_assert_failed(__FILE__, __LINE__); } while (0)

/* ---- Cortex-M7 interrupt priorities --------------------------------------------------- */
/* RT1062 implements 4 priority bits (__NVIC_PRIO_BITS). Lower number = more urgent.
 *   0..4  : never masked by the kernel; must NOT call any FreeRTOS API (none used yet).
 *   5..15 : may call ...FromISR() APIs. USB = 5, GPIO1 = 6 (board.h TK_IRQ_PRIO_*).
 *   15    : kernel (PendSV, SysTick). */
#define configPRIO_BITS                              4
#define configLIBRARY_LOWEST_INTERRUPT_PRIORITY      15
#define configLIBRARY_MAX_SYSCALL_INTERRUPT_PRIORITY 5
#define configKERNEL_INTERRUPT_PRIORITY      (configLIBRARY_LOWEST_INTERRUPT_PRIORITY << (8 - configPRIO_BITS))
#define configMAX_SYSCALL_INTERRUPT_PRIORITY (configLIBRARY_MAX_SYSCALL_INTERRUPT_PRIORITY << (8 - configPRIO_BITS))

/* Map the port's handlers onto the CMSIS vector names used in startup.c. */
#define vPortSVCHandler     SVC_Handler
#define xPortPendSVHandler  PendSV_Handler
#define xPortSysTickHandler SysTick_Handler

/* ---- optional API ---------------------------------------------------------------------- */
#define INCLUDE_vTaskDelay                  1
#define INCLUDE_xTaskDelayUntil             1
#define INCLUDE_vTaskSuspend                1
#define INCLUDE_xTaskGetSchedulerState      1
#define INCLUDE_xTaskGetCurrentTaskHandle   1
#define INCLUDE_uxTaskGetStackHighWaterMark 1
#define INCLUDE_vTaskPrioritySet            0
#define INCLUDE_uxTaskPriorityGet           0
#define INCLUDE_vTaskDelete                 0

#endif /* FREERTOS_CONFIG_H */
