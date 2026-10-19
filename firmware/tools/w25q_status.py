#!/usr/bin/env python3
"""Read (and optionally set QE in) the W25Q64JV status registers over SWD.

TokenKey RT bring-up helper (firmware/docs/bringup_checklist.md, step F1).
UNTESTED ON HARDWARE.

How it works: the debugger halts the core (so nothing executes from flash) and drives
FlexSPI IP commands directly through the FlexSPI register block (IMXRT1060RM Rev.3,
chapter 27 "FlexSPI": LUT key 0x5AF05AF0 / LUTCR unlock, IPCR0[SFAR] = device address
without base, IPCR1 ISEQID/IDATSZ, IPCMD TRG, RFDR/TFDR FIFOs). It uses LUT sequence 15,
which the TokenKey FCB (boot_hdr.c) leaves unused, so XIP reads (sequence 0) are unaffected.
Reset the board afterwards.

    pip install pyocd
    python3 tools/w25q_status.py              # print SR1/SR2/SR3, check QE (SR2 bit 1)
    python3 tools/w25q_status.py --set-qe     # 0x06 WREN, 0x31 SR2|=0x02 (non-volatile)
"""
import argparse
import sys
import time

from pyocd.core.helpers import ConnectHelper

FLEXSPI = 0x402A8000
MCR0, INTR, LUTKEY, LUTCR = 0x00, 0x14, 0x18, 0x1C
IPCR0, IPCR1, IPCMD, IPRXFCR, IPTXFCR, STS0 = 0xA0, 0xA4, 0xB0, 0xB8, 0xBC, 0xE0
RFDR, TFDR, LUT = 0x100, 0x180, 0x200
LUT_KEY = 0x5AF05AF0
SEQ = 15                                 # scratch LUT sequence (unused by the FCB)

CMD_SDR, READ_SDR, WRITE_SDR, STOP = 0x01, 0x09, 0x08, 0x00
INTR_IPCMDDONE, INTR_IPCMDERR = 0x01, 0x08


def lut_word(op0, pad0, arg0, op1=STOP, pad1=0, arg1=0):
    return ((arg0 & 0xFF) | ((pad0 & 3) << 8) | ((op0 & 0x3F) << 10) |
            ((arg1 & 0xFF) << 16) | ((pad1 & 3) << 24) | ((op1 & 0x3F) << 26))


class FlexSpiIp:
    def __init__(self, target):
        self.t = target

    def w(self, off, val):
        self.t.write32(FLEXSPI + off, val & 0xFFFFFFFF)

    def r(self, off):
        return self.t.read32(FLEXSPI + off)

    def load_seq(self, words):
        self.w(LUTKEY, LUT_KEY)
        self.w(LUTCR, 0x2)                         # unlock
        for i in range(4):
            self.w(LUT + 4 * (SEQ * 4 + i), words[i] if i < len(words) else 0)
        self.w(LUTKEY, LUT_KEY)
        self.w(LUTCR, 0x1)                         # lock

    def run(self, nbytes=0, tx=None):
        while (self.r(STS0) & 0x3) != 0x3:         # SEQIDLE | ARBIDLE
            pass
        self.w(IPRXFCR, self.r(IPRXFCR) | 0x1)    # clear RX FIFO
        self.w(IPTXFCR, self.r(IPTXFCR) | 0x1)    # clear TX FIFO
        self.w(INTR, 0xFFFFFFFF)                   # clear flags (w1c)
        if tx is not None:
            self.w(TFDR, tx)
        self.w(IPCR0, 0)                           # SFAR: device address, no base
        self.w(IPCR1, (SEQ << 16) | (nbytes & 0xFFFF))
        self.w(IPCMD, 0x1)                         # TRG
        t0 = time.time()
        while True:
            st = self.r(INTR)
            if st & INTR_IPCMDERR:
                raise RuntimeError("FlexSPI IPCMDERR, INTR=0x%08X" % st)
            if st & INTR_IPCMDDONE:
                break
            if time.time() - t0 > 1.0:
                raise RuntimeError("FlexSPI IP command timeout, INTR=0x%08X" % st)
        return self.r(RFDR) & 0xFF if nbytes else None

    def read_reg(self, opcode):
        self.load_seq([lut_word(CMD_SDR, 0, opcode, READ_SDR, 0, 1)])
        return self.run(nbytes=1)

    def write_enable(self):
        self.load_seq([lut_word(CMD_SDR, 0, 0x06)])
        self.run()

    def write_sr2(self, value):
        self.load_seq([lut_word(CMD_SDR, 0, 0x31, WRITE_SDR, 0, 1)])
        self.run(nbytes=1, tx=value)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--set-qe", action="store_true", help="set SR2.QE (bit 1) via 0x31")
    ap.add_argument("--target", default="mimxrt1060")
    a = ap.parse_args()
    with ConnectHelper.session_with_chosen_probe(target_override=a.target) as s:
        t = s.target
        t.halt()
        f = FlexSpiIp(t)
        sr1, sr2, sr3 = f.read_reg(0x05), f.read_reg(0x35), f.read_reg(0x15)
        print("SR1=0x%02X SR2=0x%02X SR3=0x%02X  QE(SR2[1])=%d" % (sr1, sr2, sr3, (sr2 >> 1) & 1))
        if a.set_qe and not (sr2 & 0x02):
            f.write_enable()
            f.write_sr2(sr2 | 0x02)
            while f.read_reg(0x05) & 0x01:          # BUSY
                time.sleep(0.005)
            sr2 = f.read_reg(0x35)
            print("after 0x31: SR2=0x%02X QE=%d" % (sr2, (sr2 >> 1) & 1))
        print("done; reset the board (core left halted)")
        return 0 if (sr2 & 0x02) else 1


if __name__ == "__main__":
    sys.exit(main())
