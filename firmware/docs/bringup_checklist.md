# TokenKey RT firmware bring-up checklist

Status: **none of this has run on hardware yet.** Tick items on the first boards and record
the measured values in the issue. Commands below run from `firmware/`.

Sources used (fetched 2026-10-19 IST):

| Ref | Document | Where |
|---|---|---|
| [RM] | NXP *i.MX RT1060 Processor Reference Manual*, IMXRT1060RM **Rev. 3, 07/2021** | ch. 9 System Boot (9.13 ROM APIs, Table 9-50/9-51 FlexSPI NOR config option), ch. 22 Fusemap (Table 22-9), ch. 27 FlexSPI. Copy fetched from `https://www.pjrc.com/teensy/IMXRT1060RM_rev3.pdf` (NXP document, mirrored) |
| [FLSRC] | NXP MCUXpresso SDK MCU bootloader/flashloader source, `nxp-mcuxpresso/mcuxsdk-middleware-bootloader` @ `mcux_main` (commit 2cae99c533, 2025-02-25) | `src/memory/src/flexspi_nor_memory.c` (configure-memory handling: option tag 0xC, magic 0xF000000F, full FCB "fallback mode"), `src/drivers/flexspi_nor/flexspi_nor_flash.{h,c}` (`kSerialNorQuadMode_*`) |
| [MUG] | NXP *i.MX RT1060 Manufacturing User Guide* (same repo, `docs/iMXRT1060_Manufacturing_User_Guide`, commit 6c9ca280ba) | "Generate SB file for plaintext FlexSPI NOR image programming" (0xF000000F) |
| [AN12238] | NXP AN12238 *i.MX RT Flashloader Use Case*, §4.2.1 | `sdphost write-file 0x20000000 ivt_flashloader.bin`, `jump-address 0x20000400` |
| [BLHOST] | NXP *blhost User's Guide* (MCUBLHOSTUG), §4.2.9 fill-memory, §4.2.19 configure-memory | |

## A. Power and clocks

1. UART log on TP1 (LPUART1, 115200 8N1): banner, `part=`, `core=`, `fuse_sg=`, `dcdc_trg=`.
2. `fuse_sg` is OCOTP 0x440[17:16] SPEED_GRADING ([RM] Table 22-9, p.1301): `1` = 500 MHz
   class (P/N code 5, i.e. CVL**5**B), `2` = 600 MHz (P/N code 6, DVL**6**B). Anything else
   is reserved and the firmware falls back to 528 MHz.
3. Measure VDD_SOC: ~1.275 V (DVL6B @ 600 MHz) or ~1.225 V (CVL5B @ 528 MHz; the PM-approved
   setpoint, inside the 1.26 V CVL5B limit).

## F. QSPI flash (W25Q64JV) quad-enable

The FCB in `boot_hdr.c` boots with Fast Read Quad I/O (0xEB, 1-4-4). That needs the
non-volatile **QE bit = Status Register-2 bit 1** set. W25Q64JV**-IQ** ships with QE=1; other
suffixes/second-source parts may not.

F1. **Read SR2 (command 0x35) and confirm QE = 1 (bit 1).** With the board powered and SWD on
    J3 (TC2030):

    ```sh
    pip install pyocd
    python3 tools/w25q_status.py
    # SR1=0x00 SR2=0x02 SR3=0x60  QE(SR2[1])=1     <- expected (exit code 0)
    ```

    The script halts the core and issues FlexSPI IP commands (0x05/0x35/0x15) from the debugger
    using a scratch LUT sequence (15) that the FCB does not use ([RM] ch. 27). It works even when
    the flash is blank or the image does not boot. `--set-qe` sends 0x06 + 0x31 (SR2 |= 0x02).
    Untested on hardware: if it misbehaves, use F2, which sets QE as a side effect.

F2. **Recovery programming via ROM serial downloader + NXP flashloader (no debugger).** This
    path must work with QE=0 and must leave QE=1.

    Enter serial downloader: hold SW1 (SW_BOOT), pulse reset (TC2030 pin 3 / TP4), release SW1
    (`BOOT_MODE=01`). The ROM enumerates as USB HID `1FC9:0135`.

    ```sh
    # 1. Load and start the flashloader (ivt_flashloader.bin from the RT1060 SDK / MCUXpresso
    #    Secure Provisioning Tool install). Addresses per [AN12238] §4.2.1. Check the image first:
    #    `od -A x -t x1 -j 0x400 -N 4 ivt_flashloader.bin` must show the IVT header `d1 00 20 4x`.
    sdphost -u 0x1fc9,0x0135 -- write-file 0x20000000 ivt_flashloader.bin
    sdphost -u 0x1fc9,0x0135 -- jump-address 0x20000400
    #    The flashloader re-enumerates as its own USB HID device (15A2:0073 on the RT10xx
    #    flashloader); plain `blhost -u` uses that default.
    blhost -u -- get-property 1                       # sanity: current version

    # 2. Configure FlexSPI NOR (memory id 9) from a config-option word ([RM] Table 9-51,
    #    [BLHOST] 4.2.9/4.2.19, [FLSRC] flexspi_nor_memory.c "kSerialNorCfgOption_Tag"):
    #      0xC0000402 = tag 0xC | size 0 | device_type 0 (SFDP, SDR) | query_pads 0 (1 pad)
    #                   | cmd_pads 0 (1 pad) | quad_mode_setting 4 = "set bit 1 in SR2 via 0x31"
    #                   | misc 0 | max_freq 2 (50 MHz, same as our FCB)
    #    Alternative 0xC0000202 (quad_mode_setting 2 = "set bit 1 in SR2", written with 0x01 + 2 bytes).
    #    Both suit W25Q64JV. Note from [RM] Table 9-51 and [FLSRC] flexspi_nor_flash.c: if the
    #    flash's SFDP is JESD216A or later, the flashloader takes the QE method from SFDP
    #    (Basic table DWORD15) and ignores quad_mode_setting; either way it sets QE (non-volatile)
    #    during configure-memory if QE was 0.
    blhost -u -- fill-memory 0x2000 4 0xC0000402 word
    blhost -u -- configure-memory 0x9 0x2000

    # 3. Erase and program. tokenkey_rt.bin already starts with our own FCB at offset 0 and
    #    IVT at 0x1000, so write it at 0x60000000. (Do not also program the flashloader-generated
    #    FCB with the 0xF000000F magic from [MUG]; our image's FCB would overwrite it anyway.)
    blhost -u -- flash-erase-region 0x60000000 0x100000
    blhost -u -- write-memory 0x60000000 build-dvl6b/tokenkey_rt.bin
    blhost -u -- read-memory 0x60000000 0x200 fcb_readback.bin   # optional: compare with the .bin
    ```

    **Single-pad fallback.** If quad configuration fails (e.g. SFDP read error, signal
    integrity), program with a single-pad configuration instead:

    - Flashloader side: `configure-memory` also accepts a complete 512-byte FCB ("FCFB" tag,
      [FLSRC] flexspi_nor_memory.c "Fallback mode"). Build the recovery image (its FCB uses
      Fast Read 0x0B 1-1-1, `sflashPadType=1`, no QE needed) and hand its first 512 bytes to the
      flashloader:
      ```sh
      cmake --preset recovery-1pad && cmake --build --preset recovery-1pad
      head -c 512 build-recovery/tokenkey_rt.bin > fcb_1pad.bin
      blhost -u -- write-memory 0x2000 fcb_1pad.bin
      blhost -u -- configure-memory 0x9 0x2000
      blhost -u -- flash-erase-region 0x60000000 0x100000
      blhost -u -- write-memory 0x60000000 build-recovery/tokenkey_rt.bin
      ```
      The recovery image boots 1-1-1 at 50 MHz whatever QE is (528 MHz core, safe on both parts).
    - Then set QE (F1 `--set-qe`, or F2 step 2 with 0xC0000402) and re-flash the normal quad
      image.

F3. **MCUXpresso Secure Provisioning Tool path** (GUI alternative to F2): processor MIMXRT1062,
    boot type *Unsigned*, boot memory *FlexSPI NOR - QuadSPI*, "Boot memory configuration":
    use the *simplified/option-word* setting with 0xC0000402 (or the Winbond W25Q-series
    template), write `tokenkey_rt.bin` as a *binary with FCB* at 0x60000000. SPT runs the
    same flashloader underneath, so QE behaviour is the same as F2. (GUI field names vary
    between SPT versions; this step has not been tried yet.)

F4. After programming, re-run F1 and confirm `QE(SR2[1])=1`, then reset without SW1:
    `BOOT_MODE=10`, the board should XIP-boot and print the banner.

## U. USB, UI, watchdog

1. LED pulses on USB traffic; `lsusb` shows the dev VID/PID (`TK_USB_VID`/`TK_USB_PID` in
   `usb_vendor.c`); HELLO/PING round-trip from a libusb script.
2. OLED splash, then mode screen; check orientation (`0xA1/0xC8` in `oled.c`) and contrast.
3. Encoder direction (`TK_ENC_INVERT`) and steps per detent (`TK_ENC_STEPS_PER_DETENT`, 2 for EC11E18244A5).
4. I2C SCL frequency on a scope (target <= 400 kHz; ~365 kHz expected).
5. Watchdog (`status_task` is the LED + watchdog task): stall a task in a test build and
   confirm the RTWDOG reset after ~2 s.
