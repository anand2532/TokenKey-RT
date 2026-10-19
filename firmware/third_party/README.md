# Vendored dependencies (minimal subsets, unmodified)

| Dir | Upstream | Version / commit | License | What was kept |
|---|---|---|---|---|
| `cmsis/Include` | [ARM-software/CMSIS_5](https://github.com/ARM-software/CMSIS_5) | tag `5.9.0` (`2b7495b8`) | Apache-2.0 (`cmsis/LICENSE.txt`) | `core_cm7.h`, `cmsis_compiler.h`, `cmsis_gcc.h`, `cmsis_version.h`, `mpu_armv7.h`, `cachel1_armv7.h` |
| `nxp/MIMXRT1062` | [nxp-mcuxpresso/mcux-sdk](https://github.com/nxp-mcuxpresso/mcux-sdk) | tag `MCUX_2.16.100` (`0420001d`) | BSD-3-Clause (`nxp/COPYING-BSD-3`) | device headers only: `MIMXRT1062.h`, `MIMXRT1062_features.h`, `fsl_device_registers.h`, `system_MIMXRT1062.h` (no SDK drivers, no `system_MIMXRT1062.c`) |
| `tinyusb` | [hathach/tinyusb](https://github.com/hathach/tinyusb) | tag `0.20.0` (`3af1bec1`) | MIT (`tinyusb/LICENSE`) | `src/` core, `common/`, `device/`, `osal/` (FreeRTOS + none), `class/vendor/`, `portable/chipidea/ci_hs/` (device driver + i.MX RT glue) |
| `freertos` | [FreeRTOS/FreeRTOS-Kernel](https://github.com/FreeRTOS/FreeRTOS-Kernel) | tag `V11.1.0` (`dbf70559`) | MIT (`freertos/LICENSE.md`) | `tasks.c`, `queue.c`, `list.c`, `event_groups.c`, `include/`, `portable/GCC/ARM_CM7/r0p1/` (no heap_x.c: static allocation only) |

To update: re-copy the same file list from the new upstream tag and update this table.
