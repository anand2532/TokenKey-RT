/*
 * TokenKey RT - MIMXRT1062 XIP from FlexSPI A (W25Q64, 8 MB @ 0x6000_0000)
 *
 *   0x6000_0000  FCB (FlexSPI NOR config block, 512 B)       .boot_hdr.conf
 *   0x6000_1000  IVT (32 B) + boot data (16 B)               .boot_hdr.ivt / .boot_hdr.boot_data
 *   0x6000_2000  vector table, .text, .rodata, .data LMA
 *   0x607F_0000  last 64 KB reserved for the config sector (firmware_architecture.md 3)
 *
 * FlexRAM is re-banked in startup.c to ITCM 128 KB / DTCM 256 KB / OCRAM 128 KB
 * (fuse table entry 1000b), so these lengths are only valid after Reset_Handler ran.
 */
ENTRY(Reset_Handler)

MEMORY
{
  FLASH_CFG (rx)  : ORIGIN = 0x60000000, LENGTH = 0x00001000
  FLASH_IVT (rx)  : ORIGIN = 0x60001000, LENGTH = 0x00001000
  FLASH     (rx)  : ORIGIN = 0x60002000, LENGTH = 0x007EE000   /* up to 0x607F0000 */
  ITCM      (rwx) : ORIGIN = 0x00000000, LENGTH = 128K
  DTCM      (rw)  : ORIGIN = 0x20000000, LENGTH = 256K
  OCRAM2    (rw)  : ORIGIN = 0x20200000, LENGTH = 512K          /* dedicated OCRAM */
  OCRAM_FX  (rw)  : ORIGIN = 0x20280000, LENGTH = 128K          /* FlexRAM part */
}

__main_stack_size = 8K;
__flash_size      = 8M;

SECTIONS
{
  .boot_hdr.conf : { KEEP(*(.boot_hdr.conf)) } > FLASH_CFG
  .boot_hdr.ivt  : { KEEP(*(.boot_hdr.ivt)) KEEP(*(.boot_hdr.boot_data)) } > FLASH_IVT

  .text : ALIGN(1024)
  {
    __vector_table = .;
    KEEP(*(.isr_vector))
    *(.text*)
    *(.rodata*)
    . = ALIGN(4);
  } > FLASH

  .ARM.exidx : { __exidx_start = .; *(.ARM.exidx* .gnu.linkonce.armexidx.*) __exidx_end = .; } > FLASH

  .ramfunc : ALIGN(4)
  {
    __ramfunc_start = .;
    *(.ramfunc*)
    . = ALIGN(4);
    __ramfunc_end = .;
  } > ITCM AT > FLASH
  __ramfunc_load = LOADADDR(.ramfunc);

  .data : ALIGN(4)
  {
    __data_start = .;
    *(.data*)
    . = ALIGN(4);
    __data_end = .;
  } > DTCM AT > FLASH
  __data_load = LOADADDR(.data);

  .bss (NOLOAD) : ALIGN(4)
  {
    __bss_start = .;
    *(.bss*)
    *(COMMON)
    . = ALIGN(4);
    __bss_end = .;
  } > DTCM

  /* Large / DMA buffers that do not fit DTCM. Cacheable: users must do cache maintenance. */
  .ocram_bss (NOLOAD) : ALIGN(32)
  {
    __ocram_bss_start = .;
    *(.ocram_bss*)
    . = ALIGN(4);
    __ocram_bss_end = .;
  } > OCRAM2

  __flash_image_end = __data_load + SIZEOF(.data);
  _estack = ORIGIN(DTCM) + LENGTH(DTCM);
  ASSERT(__bss_end + __main_stack_size <= _estack, "DTCM overflow: .data+.bss+main stack > 256 KB")
  ASSERT(__flash_image_end <= ORIGIN(FLASH) + LENGTH(FLASH), "image overlaps the config sector")

  /DISCARD/ : { *(.ARM.attributes) *(.comment) *(.note*) }
}
