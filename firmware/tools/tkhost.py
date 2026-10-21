#!/usr/bin/env python3
"""tkhost - TokenKey RT host tool (protocol v1.0, firmware/docs/usb_protocol.md).

Transports:
  USB  (default): pyusb, vendor interface, bulk OUT 0x01 / IN 0x81 (VID 0x1FC9, PID 0xFFF0 dev values)
  --sim         : the device firmware's protocol + job + engine C code built as a host shared
                  library (build-host/libtksim.so), driven through ctypes with a virtual clock.

Commands: hello, ping, info, mode [M], policy [...], run FILE, stats [--reset], corpus DIR.

The host owns conversation state (SPEC 5.2 #8): reduced history, n_prev, last request time,
lapse detection. The device owns the bounded per-session dupset and returns a keep/drop
record per segment; the host assembles the reduced messages from its own bytes.
"""
from __future__ import annotations

import argparse
import ctypes
import glob
import json
import os
import struct
import sys
import time

SOF, VER = 0xA5, 1
MAX_PAYLOAD = 4096
CMD = dict(HELLO=0x01, PING=0x02, GET_INFO=0x03, SET_MODE=0x10, GET_MODE=0x11, SET_POLICY=0x12, GET_POLICY=0x13,
           JOB_BEGIN=0x20, JOB_DATA=0x21, JOB_END=0x22, RESULT_READ=0x23, JOB_ABORT=0x24, GET_STATS=0x30,
           RESET_STATS=0x31, ERROR=0xFF)
ERR = {0x01: "BAD_CRC", 0x02: "BAD_LEN", 0x03: "BAD_VERSION", 0x04: "UNKNOWN_CMD", 0x05: "BAD_PARAM", 0x06: "BUSY",
       0x07: "NO_JOB", 0x08: "BAD_OFFSET", 0x09: "CTX_OVERFLOW", 0x0A: "HASH_MISMATCH", 0x0B: "TIMEOUT",
       0x0C: "SAFE_MODE", 0x0D: "SESSION_MISMATCH", 0x0E: "POLICY_INVALID", 0x7F: "INTERNAL"}
MODES = ["economy", "balanced", "quality", "s-protect", "dedup-only"]
JOB_FLAG_FULL, JOB_FLAG_MESSAGES = 0x02, 0x04
MSGF_EXEMPT, MSGF_NEWEST = 0x01, 0x02
ROLE = {"system": 0, "user": 1, "assistant": 2, "tool": 3}
SEG_KEEP, SEG_DROP_DUP, SEG_DROP_BUDGET = 0, 1, 2
ST_DONE, ST_PASS2, ST_OVERFLOW = 0, 1, 2
PLACEHOLDER = "[TokenKey: content omitted]"
TTL_S = 300.0
POL = dict(KEEP_PCT=0x01, DEDUP=0x02, TYPE_WEIGHT=0x04, NEWEST_DEDUP=0x05, RULES=0x06, TTL_S=0x07)
SEG_TYPES = ["prose", "code", "diff", "log"]


# ---------------------------------------------------------------- CRC / XXH32
def crc16(data: bytes, crc: int = 0xFFFF) -> int:
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


P1, P2, P3, P4, P5 = 2654435761, 2246822519, 3266489917, 668265263, 374761393
M32 = 0xFFFFFFFF


def _rotl(x, r):
    return ((x << r) | (x >> (32 - r))) & M32


class XXH32:
    """Streaming XXH32 (seed 0). Uses the xxhash module when installed, else pure Python."""

    def __init__(self):
        try:
            import xxhash
            self._h = xxhash.xxh32(seed=0)
        except ImportError:
            self._h = None
            self.total, self.mem = 0, b""
            self.v = [(P1 + P2) & M32, P2, 0, (-P1) & M32]

    def update(self, data: bytes):
        if self._h is not None:
            self._h.update(data)
            return self
        self.total += len(data)
        data = self.mem + data
        n = len(data) - len(data) % 16
        v = self.v
        for i in range(0, n, 16):
            for k in range(4):
                w = int.from_bytes(data[i + 4 * k:i + 4 * k + 4], "little")
                v[k] = (_rotl((v[k] + w * P2) & M32, 13) * P1) & M32
        self.mem = data[n:]
        return self

    def intdigest(self) -> int:
        if self._h is not None:
            return self._h.intdigest()
        v = self.v
        h = (_rotl(v[0], 1) + _rotl(v[1], 7) + _rotl(v[2], 12) + _rotl(v[3], 18)) & M32 if self.total >= 16 \
            else (v[2] + P5) & M32
        h = (h + self.total) & M32
        m, i = self.mem, 0
        while i + 4 <= len(m):
            h = (_rotl((h + int.from_bytes(m[i:i + 4], "little") * P3) & M32, 17) * P4) & M32
            i += 4
        while i < len(m):
            h = (_rotl((h + m[i] * P5) & M32, 11) * P1) & M32
            i += 1
        h ^= h >> 15
        h = (h * P2) & M32
        h ^= h >> 13
        h = (h * P3) & M32
        h ^= h >> 16
        return h

    def copy(self):
        c = XXH32.__new__(XXH32)
        if self._h is not None:
            c._h = self._h.copy()
        else:
            c._h, c.total, c.mem, c.v = None, self.total, self.mem, list(self.v)
        return c


def xxh32(data: bytes) -> int:
    return XXH32().update(data).intdigest()


# ---------------------------------------------------------------- frames / transports
def build(cmd: int, seq: int, payload: bytes = b"") -> bytes:
    body = bytes([VER, cmd, seq]) + struct.pack("<H", len(payload)) + payload
    return bytes([SOF]) + body + struct.pack("<H", crc16(body))


class Parser:
    def __init__(self):
        self.buf = b""

    def feed(self, data: bytes):
        self.buf += data
        out = []
        while True:
            i = self.buf.find(bytes([SOF]))
            if i < 0:
                self.buf = b""
                return out
            self.buf = self.buf[i:]
            if len(self.buf) < 6:
                return out
            ln = struct.unpack_from("<H", self.buf, 4)[0]
            if ln > MAX_PAYLOAD:
                self.buf = self.buf[1:]
                continue
            if len(self.buf) < 8 + ln:
                return out
            body, crc = self.buf[1:6 + ln], struct.unpack_from("<H", self.buf, 6 + ln)[0]
            if crc16(body) != crc:
                self.buf = self.buf[1:]
                continue
            out.append((body[1], body[2], body[5:5 + ln]))
            self.buf = self.buf[8 + ln:]


class SimTransport:
    """Device C code in-process (ctypes). `now` is the virtual clock in seconds."""

    def __init__(self, lib=None, safe_mode=False, part=0):
        here = os.path.dirname(os.path.abspath(__file__))
        cands = [lib, os.environ.get("TK_SIM_LIB"), os.path.join(here, "..", "build-host", "libtksim.so")]
        path = next((c for c in cands if c and os.path.exists(c)), None)
        if not path:
            raise SystemExit("libtksim.so not found: build it with `cmake --preset host && cmake --build --preset host`"
                             " or pass --sim-lib PATH / TK_SIM_LIB")
        self.lib = ctypes.CDLL(path)
        self.lib.tksim_xfer.restype = ctypes.c_int
        self.lib.tksim_init(int(safe_mode), int(part))
        self.now = 0.0
        self.out = ctypes.create_string_buffer(4 * (MAX_PAYLOAD + 8) + 64)
        self.parser = Parser()
        self.pending = []

    def send(self, frame: bytes):
        n = self.lib.tksim_xfer(frame, len(frame), int(self.now * 1000) & M32, self.out, len(self.out))
        if n < 0:
            raise RuntimeError("sim output buffer too small")
        self.pending += self.parser.feed(self.out.raw[:n])

    def recv(self, timeout=0.5):
        if not self.pending:
            raise TimeoutError("no reply from simulator")
        return self.pending.pop(0)


class UsbTransport:
    VID, PID = 0x1FC9, 0xFFF0

    def __init__(self, vid=None, pid=None):
        import usb.core
        import usb.util
        self.dev = usb.core.find(idVendor=vid or self.VID, idProduct=pid or self.PID)
        if self.dev is None:
            raise SystemExit("TokenKey RT not found on USB (VID %04x PID %04x)" % (vid or self.VID, pid or self.PID))
        try:
            if self.dev.is_kernel_driver_active(0):
                self.dev.detach_kernel_driver(0)
        except (NotImplementedError, usb.core.USBError):
            pass
        self.dev.set_configuration()
        self.parser = Parser()
        self.pending = []
        self.now = None

    def send(self, frame: bytes):
        self.dev.write(0x01, frame, timeout=1000)

    def recv(self, timeout=0.5):
        import usb.core
        t_end = time.monotonic() + timeout
        while not self.pending:
            if time.monotonic() > t_end:
                raise TimeoutError("no reply from device")
            try:
                data = bytes(self.dev.read(0x81, 8192, timeout=int(timeout * 1000)))
            except usb.core.USBTimeoutError:
                continue
            self.pending += [f for f in self.parser.feed(data) if not 0x60 <= f[0] <= 0x6F]  # drop events
        return self.pending.pop(0)


class DeviceError(Exception):
    def __init__(self, cmd, code, detail):
        super().__init__("%s: %s (0x%02x) detail 0x%04x" % (cmd, ERR.get(code, "?"), code, detail))
        self.code, self.detail = code, detail


# ---------------------------------------------------------------- client
class Client:
    def __init__(self, transport):
        self.t = transport
        self.seq = 0

    def xfer(self, name: str, payload: bytes = b"", retries=3) -> bytes:
        cmd = CMD[name]
        for attempt in range(retries + 1):
            self.seq = (self.seq + 1) & 0xFF
            self.t.send(build(cmd, self.seq, payload))
            try:
                rcmd, rseq, pl = self.t.recv()
            except TimeoutError:
                if attempt == retries:
                    raise
                continue
            if rcmd == CMD["ERROR"]:
                code, detail = pl[1], struct.unpack_from("<H", pl, 2)[0]
                if code == 0x06 and attempt < retries:  # BUSY: back off and resend
                    time.sleep(0.005)
                    continue
                raise DeviceError(name, code, detail)
            if rcmd != (cmd | 0x80) or rseq != self.seq:
                raise RuntimeError("unexpected reply cmd 0x%02x seq %d" % (rcmd, rseq))
            return pl
        raise RuntimeError("unreachable")

    def hello(self):
        p = self.xfer("HELLO", bytes([VER]) + struct.pack("<H", MAX_PAYLOAD))
        proto, fw, part, mhz, maxp, win, caps = struct.unpack_from("<BIBHHBI", p)
        return dict(proto=proto, fw="%d.%d.%d" % (fw >> 16, (fw >> 8) & 0xFF, fw & 0xFF), part=["DVL6B", "CVL5B"][part & 1],
                    core_mhz=mhz, max_payload=maxp, window=win, caps=caps, minor=p[15] if len(p) > 15 else 1,
                    sessions=bool(caps & 8) and (p[15] if len(p) > 15 else 1) >= 3)  # v1.0 jobs need minor >= 3

    def ping(self, data=b"tk"):
        return self.xfer("PING", data)

    def info(self):
        p, i, out = self.xfer("GET_INFO"), 0, {}
        while i + 2 <= len(p):
            t, ln = p[i], p[i + 1]
            v = p[i + 2:i + 2 + ln]
            out[{1: "serial", 2: "build_id", 3: "flash_size", 4: "uptime_ms"}.get(t, "tlv%d" % t)] = (
                v[::-1].hex() if t == 1 else v.decode(errors="replace") if t == 2 else int.from_bytes(v, "little"))
            i += 2 + ln
        return out

    def set_mode(self, m: int):
        return self.xfer("SET_MODE", bytes([m]))[0]

    def get_mode(self):
        p = self.xfer("GET_MODE")
        return p[0], p[1]

    @staticmethod
    def parse_policy(p: bytes):
        d = dict(version=p[0], preset=p[1])
        i = 2
        while i + 2 <= len(p):
            t, ln, v = p[i], p[i + 1], p[i + 2:i + 2 + p[i + 1]]
            if t == POL["KEEP_PCT"]: d["keep_pct"] = v[0]
            elif t == POL["DEDUP"]: d["dedup"] = v[0]
            elif t == POL["NEWEST_DEDUP"]: d["newest_dedup"] = v[0]
            elif t == POL["RULES"]: d["rules"] = v[0]
            elif t == POL["TTL_S"]: d["ttl_s"] = int.from_bytes(v, "little")
            elif t == POL["TYPE_WEIGHT"]: d.setdefault("weights", {})[SEG_TYPES[v[0]]] = int.from_bytes(v[1:3], "little")
            i += 2 + ln
        return d

    def get_policy(self):
        return self.parse_policy(self.xfer("GET_POLICY"))

    def set_policy(self, preset=0xFF, keep_pct=None, dedup=None, newest_dedup=None, rules=None, ttl_s=None, weights=None):
        b = bytes([1, preset])
        for k, v in (("KEEP_PCT", keep_pct), ("DEDUP", dedup), ("NEWEST_DEDUP", newest_dedup), ("RULES", rules)):
            if v is not None:
                b += bytes([POL[k], 1, int(v)])
        if ttl_s is not None:
            b += bytes([POL["TTL_S"], 4]) + struct.pack("<I", int(ttl_s))
        for t, w in (weights or {}).items():
            b += bytes([POL["TYPE_WEIGHT"], 3, SEG_TYPES.index(t)]) + struct.pack("<H", w)
        return self.parse_policy(self.xfer("SET_POLICY", b))

    def stats(self, job_id=0xFFFF):
        p = self.xfer("GET_STATS", struct.pack("<H", job_id))
        bi, bo, ti, to, dh = struct.unpack_from("<5I", p)
        segs = struct.unpack_from("<4H", p, 20)
        sf, cyc = struct.unpack_from("<2I", p, 28)
        return dict(bytes_in=bi, bytes_out=bo, tok_in=ti, tok_out=to, dup_hits=dh, set_full=sf, cycles=cyc,
                    segments=dict(zip(SEG_TYPES, segs)), savings_pct=round(100 * (1 - bo / bi), 1) if bi else 0.0)

    def reset_stats(self):
        self.xfer("RESET_STATS")

    def run_job(self, job_id, msgs, flags, roles=None, session=0, full=True, prefix_len=0, prefix_xxh=0, spans=(),
                token_budget=0, chunk=MAX_PAYLOAD - 6):
        """msgs: list of bytes. Returns (result dict, records [(off, len, act, hash)])."""
        content = b"".join(msgs)
        roles = roles or [3] * len(msgs)
        pl = struct.pack("<HIBI", job_id, len(content), (JOB_FLAG_FULL if full else 0) | JOB_FLAG_MESSAGES, token_budget)
        pl += struct.pack("<IIIB", session, prefix_len, prefix_xxh, len(spans))
        for o, ln, k in spans:
            pl += struct.pack("<IIB", o, ln, k)
        pl += struct.pack("<H", len(msgs)) + b"".join(struct.pack("<IBB", len(m), r, f) for m, r, f in zip(msgs, roles, flags))
        self.xfer("JOB_BEGIN", pl)
        h = xxh32(content)
        res = None
        for p in range(2):
            base = p * len(content)
            for o in range(0, len(content), chunk):
                self.xfer("JOB_DATA", struct.pack("<HI", job_id, base + o) + content[o:o + chunk])
            r = self.xfer("JOB_END", struct.pack("<HI", job_id, h))
            res = dict(zip(("job_id", "status", "seg_count", "tok_in", "tok_out", "kept_bytes", "dup_hits", "set_full"),
                           struct.unpack_from("<HB6I", r)))
            if res["status"] != ST_PASS2:
                break
        res["passes"] = p + 1
        recs = []
        if res["status"] == ST_DONE:
            off, total = 0, res["seg_count"] * 13
            while off < total or not recs and total == 0:
                r = self.xfer("RESULT_READ", struct.pack("<HIH", job_id, off, MAX_PAYLOAD - 7))
                data = r[7:]
                for k in range(0, len(data), 13):
                    recs.append(struct.unpack_from("<IIBI", data, k))
                off += len(data)
                if r[6]:
                    break
        return res, recs


# ---------------------------------------------------------------- host-side reducer (SPEC 1, 2, 3)
def _fill(xs):
    return [x if x.strip() else PLACEHOLDER for x in xs]


def positional_roles(n):
    return [0 if g == 0 else 1 if g == 1 else 2 if g % 2 == 0 else 3 for g in range(n)]


def exempt(g, n):
    return not (g >= 3 and g % 2 == 1 and g != n - 1)


class Reducer:
    """variant: 's-protect' | 'economy' | 'balanced' | 'quality' (S-protect + ratio) | 'dedup-only' (G) |
    'd-economy' (firmware as written, opt-in). Drives the device through `client`."""

    def __init__(self, client, variant="s-protect", session_id=0x544B0001, ttl_s=TTL_S, verify_dups=False):
        self.c, self.v, self.sid, self.ttl = client, variant, session_id, ttl_s
        self.verify = verify_dups
        self.hist, self.n_prev, self.last_t = [], 0, None
        self.prefix_len, self.prefix_h = 0, XXH32()
        self.job_id = 0
        self.seen = {}
        self.stats = dict(full=0, warm=0, overflow=0, pass2=0, mismatch=0, collisions=0)
        if variant == "d-economy":
            client.set_policy(preset=0, rules=0, keep_pct=25)
        else:
            client.set_mode(MODES.index(variant))

    def _job(self, part, gidx, n, full):
        self.job_id = (self.job_id + 1) & 0xFFFF
        bs = [m.encode("utf-8", "surrogatepass") for m in part]
        roles = positional_roles(n)
        if self.v == "dedup-only":
            flags = [MSGF_EXEMPT] * len(bs)
        elif self.v == "d-economy":
            flags = [0] * len(bs)
        else:
            flags = [(MSGF_EXEMPT if exempt(g, n) else 0) | (MSGF_NEWEST if g == n - 1 else 0) for g in gidx]
        sid = 0 if self.v == "d-economy" else self.sid
        res, recs = self.c.run_job(self.job_id, bs, flags, [roles[g] for g in gidx], session=sid, full=full,
                                   prefix_len=0 if full else self.prefix_len,
                                   prefix_xxh=0 if full else self.prefix_h.intdigest())
        content = b"".join(bs)
        if full:
            self.prefix_len, self.prefix_h = 0, XXH32()
        self.prefix_len += len(content)
        self.prefix_h.update(content)
        self.stats["pass2"] += res["passes"] == 2
        if res["status"] == ST_OVERFLOW:
            self.stats["overflow"] += 1
            return None
        out, si, pos = [], 0, 0
        for b in bs:
            end, parts = pos + len(b), []
            while si < len(recs) and recs[si][0] < end:
                o, ln, act, h = recs[si]
                seg = content[o:o + ln]
                if act == SEG_DROP_DUP and self.verify and seg not in self.seen.get(h, ()):
                    act = SEG_KEEP  # 32-bit collision guard: no identical bytes seen before
                    self.stats["collisions"] += 1
                if act == SEG_KEEP:
                    parts.append(seg)
                if self.verify:
                    self.seen.setdefault(h, set()).add(seg)
                si += 1
            out.append(b"".join(parts).decode("utf-8", "surrogatepass"))
            pos = end
        return out

    def process(self, msgs, t):
        n = len(msgs)
        if self.v == "d-economy":
            o = self._job(msgs, range(n), n, True)
            return list(msgs) if o is None else _fill(o)
        if self.v == "dedup-only":
            full = self.n_prev == 0
            tail = msgs[self.n_prev:]
            o = self._job(tail, range(self.n_prev, n), n, full)
            self.hist = self.hist + _fill(o if o is not None else list(tail))
            self.n_prev = n
            return list(self.hist)
        lapse = self.last_t is None or t - self.last_t > self.ttl or n < self.n_prev
        if not lapse:
            try:
                o = self._job(msgs[self.n_prev:], range(self.n_prev, n), n, False)
                self.hist = self.hist + _fill(o if o is not None else list(msgs[self.n_prev:]))
                self.stats["warm"] += 1
            except DeviceError as e:
                if e.code != 0x0D:
                    raise
                self.stats["mismatch"] += 1  # device lost/expired the session: cold start
                lapse = True
        if lapse:
            if self.verify:
                self.seen = {}
            o = self._job(msgs, range(n), n, True)
            if o is None:
                o = list(msgs)
            self.hist = _fill(o)
            self.stats["full"] += 1
        self.n_prev, self.last_t = n, t
        return list(self.hist)


# ---------------------------------------------------------------- corpus check (handoff format)
CORPUS_VARIANTS = {"D_firmware_as_written_economy": "d-economy", "S_protect_economy": "economy",
                   "S_protect_balanced": "balanced", "S_protect_quality": "quality", "G_dedup_only": "dedup-only"}


def corpus_check(client_factory, inputs, expected=None, digests=None):
    """Replay every session of `inputs` through the device for each variant. Compare with the
    expected outputs (directory) and/or the sha256 digests manifest. Returns (results, mismatches)."""
    import hashlib
    results, bad = {}, []
    sessions = sorted(os.listdir(inputs))
    for vname, var in CORPUS_VARIANTS.items():
        per = []
        for sd in sessions:
            js = [json.load(open(f)) for f in sorted(glob.glob(os.path.join(inputs, sd, "req_*.json")))]
            c, tr = client_factory()
            red = Reducer(c, var)
            for i, j in enumerate(js):
                tr.now = j["t_s_modelled"]
                sent = red.process(j["messages"], j["t_s_modelled"])
                per.append((j["messages"], j["next_assistant"], sent))
                key = "%s/%s/req_%03d" % (vname, sd, i)
                if expected:
                    exp = json.load(open(os.path.join(expected, vname, sd, "req_%03d.json" % i)))["messages"]
                    if sent != exp:
                        bad.append(key)
                if digests is not None:
                    d = hashlib.sha256(json.dumps(sent, ensure_ascii=False).encode("utf-8", "surrogatepass")).hexdigest()
                    if digests.get(key) != d:
                        bad.append(key + " (digest)")
            results.setdefault(vname, {})["stats_" + sd] = red.stats
        results[vname]["sent"] = per
    return results, bad


# ---------------------------------------------------------------- CLI
def load_messages(path):
    if path == "-":
        txt = sys.stdin.read()
    else:
        txt = open(path, encoding="utf-8", errors="surrogateescape").read()
    try:
        j = json.loads(txt)
    except json.JSONDecodeError:
        return ["", txt], None  # plain text: empty system prompt + one task message
    if isinstance(j, dict):
        t = j.get("t_s_modelled")
        j = j["messages"]
    else:
        t = None
    return [m["content"] if isinstance(m, dict) else m for m in j], t


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sim", action="store_true", help="use the simulator library instead of USB")
    ap.add_argument("--sim-lib", metavar="LIB", help="simulator library path (implies --sim)")
    ap.add_argument("--safe-mode", action="store_true", help="(sim) start the simulated device in safe mode")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("hello")
    p = sub.add_parser("ping"); p.add_argument("data", nargs="?", default="tokenkey")
    sub.add_parser("info")
    p = sub.add_parser("mode"); p.add_argument("mode", nargs="?", choices=MODES)
    p = sub.add_parser("policy")
    p.add_argument("--preset", choices=MODES); p.add_argument("--keep", type=int); p.add_argument("--dedup", type=int)
    p.add_argument("--newest-dedup", type=int); p.add_argument("--rules", type=int, choices=(0, 1))
    p.add_argument("--ttl", type=int); p.add_argument("--weight", action="append", default=[], metavar="TYPE=W")
    p = sub.add_parser("run", help="reduce a request (JSON list of messages or {messages:[...]}, or plain text)")
    p.add_argument("file"); p.add_argument("--variant", default="s-protect", choices=MODES + ["d-economy"])
    p.add_argument("--state", help="session state file for DELTA across invocations")
    p.add_argument("--full", action="store_true", help="force a FULL (cold-start) job")
    p.add_argument("--out", help="write reduced messages (JSON) here")
    p.add_argument("--verify-dups", action="store_true", help="keep 'duplicates' whose bytes were never seen (collision guard)")
    p = sub.add_parser("stats"); p.add_argument("--reset", action="store_true"); p.add_argument("--job", type=int, default=0xFFFF)
    p = sub.add_parser("corpus", help="replay a golden corpus (inputs/ [expected/]) and compare")
    p.add_argument("dir"); p.add_argument("--digests")
    a = ap.parse_args(argv)

    def factory():
        tr = SimTransport(a.sim_lib, a.safe_mode) if (a.sim or a.sim_lib) else UsbTransport()
        return Client(tr), tr

    out = lambda d: print(json.dumps(d, indent=1) if a.json or not isinstance(d, str) else d)
    if a.cmd == "corpus":
        exp = os.path.join(a.dir, "expected") if os.path.isdir(os.path.join(a.dir, "expected")) else None
        dig = json.load(open(a.digests)) if a.digests else None
        res, bad = corpus_check(factory, os.path.join(a.dir, "inputs"), exp, dig)
        n = sum(len(v["sent"]) for v in res.values())
        print("corpus: %d requests x variants, %d mismatches" % (n, len(bad)))
        for b in bad[:20]:
            print("  mismatch:", b)
        return 1 if bad else 0
    c, tr = factory()
    if a.cmd == "hello":
        out(c.hello())
    elif a.cmd == "ping":
        r = c.ping(a.data.encode())
        out({"echo": r.decode(errors="replace"), "ok": r == a.data.encode()})
    elif a.cmd == "info":
        out(c.info())
    elif a.cmd == "mode":
        if a.mode:
            c.set_mode(MODES.index(a.mode))
        m, pct = c.get_mode()
        out({"mode": MODES[m], "keep_pct": pct})
    elif a.cmd == "policy":
        if any(v is not None for v in (a.preset, a.keep, a.dedup, a.newest_dedup, a.rules, a.ttl)) or a.weight:
            w = {k: int(v) for k, v in (x.split("=") for x in a.weight)}
            out(c.set_policy(MODES.index(a.preset) if a.preset else 0xFF, a.keep, a.dedup, a.newest_dedup, a.rules, a.ttl, w))
        else:
            out(c.get_policy())
    elif a.cmd == "stats":
        if a.reset:
            c.reset_stats()
        out(c.stats(a.job))
    elif a.cmd == "run":
        msgs, t = load_messages(a.file)
        t = time.time() if t is None else t
        if isinstance(tr, SimTransport):
            tr.now = t
        red = Reducer(c, a.variant, verify_dups=a.verify_dups)
        if a.state and os.path.exists(a.state) and not a.full:
            st = json.load(open(a.state))
            red.hist, red.n_prev, red.last_t = st["hist"], st["n_prev"], st["last_t"]
            # requests are append-only: the session prefix is this request's first n_prev messages
            pre = b"".join(m.encode("utf-8", "surrogatepass") for m in msgs[:red.n_prev])
            red.prefix_len, red.prefix_h = len(pre), XXH32().update(pre)
        sent = red.process(msgs, t)
        if a.state:
            json.dump({"hist": red.hist, "n_prev": red.n_prev, "last_t": red.last_t}, open(a.state, "w"))
        if a.out:
            json.dump(sent, open(a.out, "w"), ensure_ascii=False, indent=1)
        bi = sum(len(m.encode("utf-8", "surrogatepass")) for m in msgs)
        bo = sum(len(m.encode("utf-8", "surrogatepass")) for m in sent)
        out({"variant": a.variant, "messages": len(msgs), "bytes_in": bi, "bytes_out": bo,
             "savings_pct": round(100 * (1 - bo / bi), 1) if bi else 0.0, **red.stats})
    return 0


if __name__ == "__main__":
    sys.exit(main())
