"""Board + component keep-out solids (CAD frame) built from board_ref.json, for interference checks.

Conservative: each part is its courtyard box x a datasheet/typical max height, except the
encoder, USB-C, OLED header and OLED module, which are modelled from their mechanical data.
"""
import cadquery as cq
import params as P

HEIGHTS = {  # max body height above the board surface, mm
    "C_0402_1005Metric": 0.55, "R_0402_1005Metric": 0.55, "C_0603_1608Metric": 0.95,
    "LED_0603_1608Metric": P.LED_H, "Crystal_SMD_3215-2Pin_3.2x1.5mm": 0.9,
    "Crystal_SMD_3225-4Pin_3.2x2.5mm": 1.0, "L_3.0x3.0mm_TDK_VLS3015CX": 1.5,
    "L_Sunlord_SWPA4020S": 2.0, "NXP_MAPBGA-196_10x10mm_Layout14x14_P0.65mm": 1.4,
    "SOIC-8_5.3x5.3mm_P1.27mm": 2.16, "SOT-23": 1.25, "SOT-23-5": 1.45, "SOT-23-6": 1.45,
    "SW_SPST_B3U-1000P": P.B3U_H, "Winbond_USON-8-1EP_3x2mm_P0.5mm_EP0.2x1.6mm": 0.55,
    "TestPoint_Pad_D1.0mm": 0.0, "Tag-Connect_TC2030-IDC-NL_2x03_P1.27mm_Vertical": 0.0,
}
SPECIAL = {"SW2", "J1", "J2"}
UNKNOWN_H = 2.0


def box(x0, y0, z0, x1, y1, z1):
    return cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))


def kbox(kb, z0, z1):
    """KiCad bbox (x0, y0, x1, y1) -> CAD box."""
    x0, ky0, x1, ky1 = kb
    return box(x0, P.PCB_D - ky1, z0, x1, P.PCB_D - ky0, z1)


def cyl(x, y, z0, z1, d):
    return cq.Workplane("XY").circle(d / 2).extrude(z1 - z0).translate((x, y, z0))


def module_frame():
    px, py = P.J2_PIN1
    x0 = px - P.PIN1_FROM_LEFT
    y0 = py - P.PIN1_FROM_EDGE
    return px, py, (x0, y0, x0 + P.MOD_W, y0 + P.MOD_H)


def oled_parts():
    px, py, (mx0, my0, mx1, my1) = module_frame()
    zb, zt = P.HEADER_H, P.HEADER_H + P.OLED_PCB_T
    out = {}
    slab = kbox((mx0, my0, mx1, my1), zb, zt)
    for hx in (mx0 + P.MOD_HOLE_EDGE, mx1 - P.MOD_HOLE_EDGE):
        for hy in (my0 + P.MOD_HOLE_EDGE, my1 - P.MOD_HOLE_EDGE):
            slab = slab.cut(cyl(*P.K(hx, hy), zb - 1, zt + 1, P.MOD_HOLE_D))
    out["OLED module PCB"] = slab
    out["OLED glass"] = kbox((px + P.GLASS_X[0], py + P.GLASS_Y[0], px + P.GLASS_X[1], py + P.GLASS_Y[1]),
                             zt, P.OLED_TOP)
    b0, b1 = P.OLED_BACK_BAND
    out["OLED back feature (band)"] = kbox((mx0, py + b0, mx1, py + b1), zb - P.OLED_BACK_FEATURE, zb)
    cx = (mx0 + mx1) / 2
    zmin = P.FPC_BEND_ZMIN if P.FPC_BEND_ZMIN is not None else zb - P.OLED_BACK_FEATURE
    out["OLED FPC bend (conservative)"] = kbox((cx - P.FPC_BEND_W / 2, my1, cx + P.FPC_BEND_W / 2,
                                               my1 + P.FPC_BEND_OUT), zmin, P.OLED_TOP)
    # header: plastic body + pins (trimmed) above the module
    out["J2 header body"] = kbox((px - 1.27, py - 1.27, px + 3 * 2.54 + 1.27, py + 1.27), 0, P.HEADER_H)
    pins = None
    for i in range(4):
        c = cyl(*P.K(px + i * 2.54, py), zt, zt + P.HEADER_PIN_ABOVE, 1.0)
        pins = c if pins is None else pins.union(c)
    out["J2 pin tips"] = pins
    return out


def encoder():
    ax, ay = P.K(*P.ENC_AXIS_K)
    bx, by, bh = P.ENC_BODY       # board x/y extents (footprint rot 90)
    body = box(ax - bx / 2, ay - by / 2, 0, ax + bx / 2, ay + by / 2, bh)
    bush = cyl(ax, ay, bh, P.ENC_BUSHING_TOP, P.ENC_BUSHING_D) if P.ENC_BUSHING_TOP > bh else None
    shaft = cyl(ax, ay, bh, P.SHAFT_TOP, P.ENC_SHAFT_D).cut(
        box(ax - 4, ay + P.ENC_FLAT / 2, P.SHAFT_TOP - P.ENC_FLAT_L, ax + 4, ay + 4, P.SHAFT_TOP + 1))
    s = body.union(shaft)
    return s.union(bush) if bush is not None else s


def usb_c():
    b = P.J1_BODY
    x = P.fp("J1")["pos"][0]
    return kbox((x - b["w"] / 2, b["y0"], x + b["w"] / 2, b["y1"]), 0, b["h"])


def build():
    """Return dict name -> solid (CAD frame). Names starting with 'pcb' are the board itself."""
    out = {}
    pcb = cq.Workplane("XY").rect(P.PCB_W, P.PCB_D).extrude(P.PCB_T).translate(
        (P.PCB_W / 2, P.PCB_D / 2, -P.PCB_T)).edges("|Z").fillet(1.0)
    for f in P.BOARD["footprints"]:
        if f["fp"].startswith("MountingHole"):
            pcb = pcb.cut(cyl(*P.K(*f["pos"]), -2, 1, 2.2))
    out["pcb"] = pcb
    unknown = []
    for f in P.BOARD["footprints"]:
        ref, name = f["ref"], f["fp"]
        if name.startswith("MountingHole") or ref in SPECIAL:
            pass
        else:
            h = HEIGHTS.get(name)
            if h is None:
                h = UNKNOWN_H
                unknown.append(ref)
            if h > 0:
                z0, z1 = (0, h) if f["side"] == "top" else (-P.PCB_T - h, -P.PCB_T)
                out[f"{ref} ({name.split('_')[0]}{' DNP' if f['dnp'] else ''})"] = kbox(f["crtyd"], z0, z1)
        if ref != "J3" and not name.startswith("MountingHole"):   # J3 TC2030 holes take no leads
            for (x, y, d) in f["tht"]:
                out.setdefault("THT tails", None)
                t = cyl(*P.K(x, y), -P.PCB_T - P.THT_TAIL, -P.PCB_T, d + 0.4)
                out["THT tails"] = t if out["THT tails"] is None else out["THT tails"].union(t)
    out["SW2 EC11 body+shaft"] = encoder()
    out["J1 USB-C body"] = usb_c()
    out.update(oled_parts())
    build.unknown = unknown
    return out
