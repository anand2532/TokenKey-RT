# TokenKey RT firmware (MIMXRT1062, FreeRTOS, TinyUSB)
#
# Generator-agnostic: works with CMake's default generator (Unix Makefiles on Linux/macOS,
# no Ninja needed) or with -G Ninja. Always drive the build with `cmake --build`.
#
#   Firmware : cmake -S . -B build -DCMAKE_TOOLCHAIN_FILE=arm-none-eabi.cmake [-DTK_PART=DVL6B|CVL5B]
#              cmake --build build            -> build/tokenkey_rt.elf / .bin / .hex
#   Host test: cmake -S . -B build-host && cmake --build build-host && ctest --test-dir build-host
#   Presets  : cmake --preset dvl6b && cmake --build --preset dvl6b   (see CMakePresets.json)
cmake_minimum_required(VERSION 3.20)
project(tokenkey_rt C ASM)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_C_EXTENSIONS ON)
if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE RelWithDebInfo)
endif()

# ---- version / build id ------------------------------------------------------------------
set(TK_FW_MAJOR 0)
set(TK_FW_MINOR 1)
set(TK_FW_PATCH 0)
execute_process(COMMAND git rev-parse --short=8 HEAD WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
                OUTPUT_VARIABLE TK_GIT OUTPUT_STRIP_TRAILING_WHITESPACE ERROR_QUIET)
if(NOT TK_GIT)
  set(TK_GIT "nogit")
endif()
math(EXPR TK_FW_VERSION "(${TK_FW_MAJOR} << 16) | (${TK_FW_MINOR} << 8) | ${TK_FW_PATCH}" OUTPUT_FORMAT HEXADECIMAL)
math(EXPR TK_FW_BCD "(${TK_FW_MAJOR} << 8) | (${TK_FW_MINOR} << 4) | ${TK_FW_PATCH}" OUTPUT_FORMAT HEXADECIMAL)
set(TK_VERSION_DEFS
  TK_FW_VERSION=${TK_FW_VERSION}
  TK_FW_BCD=${TK_FW_BCD}
  TK_FW_VERSION_STR="${TK_FW_MAJOR}.${TK_FW_MINOR}.${TK_FW_PATCH}"
  TK_BUILD_ID="${TK_GIT}")

# ---- host unit test (native compiler) ----------------------------------------------------
if(NOT CMAKE_CROSSCOMPILING)
  enable_testing()
  add_executable(test_proto test_proto.c proto.c)
  target_compile_options(test_proto PRIVATE -Wall -Wextra -Werror)
  add_test(NAME proto COMMAND test_proto)
  return()
endif()

# ---- firmware ----------------------------------------------------------------------------
set(TK_PART "DVL6B" CACHE STRING "Fitted MCU: DVL6B (600 MHz) or CVL5B (528 MHz, VDD_SOC <= 1.26 V)")
set_property(CACHE TK_PART PROPERTY STRINGS DVL6B CVL5B)
if(NOT TK_PART MATCHES "^(DVL6B|CVL5B)$")
  message(FATAL_ERROR "TK_PART must be DVL6B or CVL5B (got '${TK_PART}')")
endif()
option(TK_WATCHDOG "Enable RTWDOG (2 s, fed by status_task after all task check-ins)" ON)
option(OLED_ROTATE_180 "OLED module rotated 180 deg vs module-normal: ON = SSD1315 0xA0/0xC0, OFF = module-normal 0xA1/0xC8" ON)
option(TK_FCB_SINGLE_PAD "Recovery image: FCB reads flash 1-1-1 (0x0B), boots even with QE=0" OFF)
message(STATUS "TokenKey RT: TK_PART=${TK_PART} TK_WATCHDOG=${TK_WATCHDOG} "
               "TK_FCB_SINGLE_PAD=${TK_FCB_SINGLE_PAD} OLED_ROTATE_180=${OLED_ROTATE_180} build=${TK_GIT} generator=${CMAKE_GENERATOR}")

set(TP ${CMAKE_CURRENT_SOURCE_DIR}/third_party)
set(TUSB ${TP}/tinyusb/src)
set(RTOS ${TP}/freertos)

set(APP_SOURCES
  startup.c boot_hdr.c board.c main.c usb_vendor.c proto.c oled.c ui.c input.c)

set(THIRD_PARTY_SOURCES
  ${TUSB}/tusb.c
  ${TUSB}/common/tusb_fifo.c
  ${TUSB}/device/usbd.c
  ${TUSB}/device/usbd_control.c
  ${TUSB}/class/vendor/vendor_device.c
  ${TUSB}/portable/chipidea/ci_hs/dcd_ci_hs.c
  ${RTOS}/tasks.c
  ${RTOS}/queue.c
  ${RTOS}/list.c
  ${RTOS}/event_groups.c
  ${RTOS}/portable/GCC/ARM_CM7/r0p1/port.c)

add_executable(tokenkey_rt.elf ${APP_SOURCES} ${THIRD_PARTY_SOURCES})
target_include_directories(tokenkey_rt.elf PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}
  ${TP}/cmsis/Include
  ${TP}/nxp/MIMXRT1062
  ${TUSB}
  ${RTOS}/include
  ${RTOS}/portable/GCC/ARM_CM7/r0p1)
target_compile_definitions(tokenkey_rt.elf PRIVATE
  CPU_MIMXRT1062${TK_PART}
  TK_PART_${TK_PART}=1
  TK_WATCHDOG=$<BOOL:${TK_WATCHDOG}>
  TK_FCB_SINGLE_PAD=$<BOOL:${TK_FCB_SINGLE_PAD}>
  OLED_ROTATE_180=$<BOOL:${OLED_ROTATE_180}>
  ${TK_VERSION_DEFS})
target_compile_options(tokenkey_rt.elf PRIVATE -O2 -g3)
# Strict warnings on our code; vendored code is compiled as shipped.
set_source_files_properties(${APP_SOURCES} PROPERTIES COMPILE_OPTIONS "-Wall;-Wextra;-Werror;-Wno-unused-parameter")
target_link_options(tokenkey_rt.elf PRIVATE
  -T${CMAKE_CURRENT_SOURCE_DIR}/MIMXRT1062_flexspi.ld
  -Wl,-Map=${CMAKE_CURRENT_BINARY_DIR}/tokenkey_rt.map
  -Wl,--wrap=malloc -Wl,--wrap=calloc -Wl,--wrap=realloc -Wl,--wrap=free
  -Wl,--print-memory-usage)
set_target_properties(tokenkey_rt.elf PROPERTIES LINK_DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/MIMXRT1062_flexspi.ld)

# .bin is a raw image of flash starting at 0x6000_0000 (FCB at offset 0): write it at the
# start of the QSPI flash. Absolute paths + generator expressions only, so the step behaves
# identically under Unix Makefiles and Ninja (no reliance on the generator's working dir).
set(TK_OUT ${CMAKE_CURRENT_BINARY_DIR}/tokenkey_rt)
add_custom_command(TARGET tokenkey_rt.elf POST_BUILD
  COMMAND ${CMAKE_OBJCOPY} -O binary $<TARGET_FILE:tokenkey_rt.elf> ${TK_OUT}.bin
  COMMAND ${CMAKE_OBJCOPY} -O ihex $<TARGET_FILE:tokenkey_rt.elf> ${TK_OUT}.hex
  COMMAND ${CMAKE_SIZE} -A -x $<TARGET_FILE:tokenkey_rt.elf>
  COMMAND ${CMAKE_SIZE} $<TARGET_FILE:tokenkey_rt.elf>
  BYPRODUCTS ${TK_OUT}.bin ${TK_OUT}.hex
  WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}
  COMMENT "objcopy -> tokenkey_rt.bin / .hex"
  VERBATIM)
