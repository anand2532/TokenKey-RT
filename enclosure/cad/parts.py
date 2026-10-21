"""Direction A puck: part builders (CadQuery). All dimensions from params.py."""
import math
import cadquery as cq
import params as P
from board_model import box, kbox, cyl, module_frame

EPS = 0.01


def rrect(x0, y0, w, h, r, z0, z1):
    return (cq.Workplane("XY").rect(w, h).extrude(z1 - z0)
            .edges("|Z").fillet(r).translate((x0 + w / 2, y0 + h / 2, z0)))


def outer(z0, z1, inset=0.0):
    return rrect(P.OUT_X0 + inset, P.OUT_Y0 + inset, P.OUT_W - 2 * inset, P.OUT_D - 2 * inset,
                 max(P.CORNER_R - inset, 0.3), z0, z1)


def inner(z0, z1, grow=0.0):
    return rrect(P.IN_X0 - grow, P.IN_Y0 - grow, P.PCB_W + 2 * P.BOARD_CLR + 2 * grow,
                 P.PCB_D + 2 * P.BOARD_CLR + 2 * grow, max(P.INNER_R + grow, 0.3), z0, z1)


def ring(z0, z1, inset_out, inset_in):
    return outer(z0, z1, inset_out).cut(outer(z0 - 1, z1 + 1, inset_in))


def holes_xy():
    return [P.K(*f["pos"]) for f in P.BOARD["footprints"] if f["fp"].startswith("MountingHole")]


def window_centre():
    px, py = P.J2_PIN1
    return P.K(px + P.WINDOW_OFS[0], py + P.WINDOW_OFS[1])


def module_holes():
    _, _, (x0, y0, x1, y1) = module_frame()
    e = P.MOD_HOLE_EDGE
    return [P.K(x, y) for x in (x0 + e, x1 - e) for y in (y0 + e, y1 - e)]


def usb_cuts():
    x = P.fp("J1")["pos"][0]
    ow, oh = P.USB_OUTER
    iw, ih = P.USB_INNER
    yo = P.OUT_Y0 - 1
    pocket = box(x - ow / 2, yo, P.USB_Z - oh / 2, x + ow / 2, P.IN_Y0 - P.USB_SKIN, P.USB_Z + oh / 2)
    pocket = pocket.edges("|Y").fillet(1.5)
    hole = box(x - iw / 2, yo, P.USB_Z - ih / 2, x + iw / 2, P.IN_Y0 + 1, P.USB_Z + ih / 2)
    hole = hole.edges("|Y").fillet(1.2)
    return pocket.union(hole)


def enc_xy():
    return P.K(*P.ENC_AXIS_K)


def btn_xy():
    return [P.K(*P.fp(r)["pos"]) for r in ("SW3", "SW4")]


def led_xy():
    return P.K(*P.fp("D1")["pos"])


# ------------------------------------------------------------------------------------------
def top_shell():
    s = outer(P.Z_SPLIT, P.LID_TOP).faces(">Z").edges().fillet(P.TOP_EDGE_FILLET)
    s = s.cut(inner(P.Z_SPLIT - 1, P.LID_UNDER))
    # rabbet for the tray's outer lip
    s = s.cut(outer(P.Z_SPLIT - 1, P.Z_SPLIT + P.LIP_H).cut(
        outer(P.Z_SPLIT - 2, P.Z_SPLIT + P.LIP_H + 1, P.LIP_T + P.LIP_CLR)))
    # OLED window, chamfered through the lid
    cx, cy = window_centre()
    w, h = P.WINDOW
    grow = P.LID_T * math.tan(math.radians(P.WINDOW_CHAMFER))
    win = (cq.Workplane("XY").workplane(offset=P.LID_UNDER - EPS).center(cx, cy).rect(w, h)
           .workplane(offset=P.LID_T + 2 * EPS).rect(w + 2 * grow, h + 2 * grow).loft())
    s = s.cut(win)
    # module locating posts (shoulder + pin), they do not clamp: the header sets the height
    zt = P.HEADER_H + P.OLED_PCB_T
    for (x, y) in module_holes():
        s = s.union(cyl(x, y, zt + P.LOC_SHOULDER_GAP, P.LID_UNDER + EPS, P.LOC_SHOULDER_D))
        s = s.union(cyl(x, y, zt - P.LOC_PIN_BELOW, zt + P.LOC_SHOULDER_GAP + EPS, P.LOC_PIN_D)
                    .faces("<Z").chamfer(0.4))
    # screw posts with M2 heat-set inserts, landing on the PCB top at H1-H4
    for (x, y) in holes_xy():
        s = s.union(cyl(x, y, 0, P.LID_UNDER + EPS, P.POST_D))
        s = s.cut(cyl(x, y, -EPS, P.INSERT_DEPTH + 1.0, P.INSERT_D))
    # encoder: relief over the body, through hole, radial-bearing collar
    ax, ay = enc_xy()
    bx, by, bh = P.ENC_BODY
    relief_top = bh + P.ENC_LID_RELIEF_CLR
    if relief_top > P.LID_UNDER:
        s = s.cut(box(ax - bx / 2 - 0.5, ay - by / 2 - 0.5, P.LID_UNDER - EPS,
                      ax + bx / 2 + 0.5, ay + by / 2 + 0.5, relief_top))
    s = s.union(cyl(ax, ay, P.LID_TOP - 0.3, P.COLLAR_TOP, P.COLLAR_OD))
    s = s.cut(cyl(ax, ay, 0, P.COLLAR_TOP + 1, P.ENC_HOLE_D))
    # buttons and light pipe
    for (x, y) in btn_xy():
        s = s.cut(cyl(x, y, 0, P.LID_TOP + 1, P.CAP_HOLE_D))
    lx, ly = led_xy()
    s = s.cut(cyl(lx, ly, 0, P.LID_TOP + 1, P.PIPE_D + 0.05))
    # USB-C: pocket + rib above the connector
    s = s.cut(usb_cuts())
    x = P.fp("J1")["pos"][0]
    s = s.union(box(x - P.USB_RIB_W / 2, P.IN_Y0 - EPS, P.J1_BODY["h"] + P.USB_RIB_GAP,
                    x + P.USB_RIB_W / 2, P.IN_Y0 + P.USB_RIB_LEN, P.LID_UNDER + EPS))
    return s


def tray():
    t = outer(P.Z_DESK, P.Z_SPLIT).faces("<Z").edges().fillet(0.8)
    t = t.union(ring(P.Z_SPLIT - EPS, P.Z_SPLIT + P.LIP_H, 0, P.LIP_T))
    t = t.cut(inner(P.Z_FLOOR_TOP, P.Z_SPLIT + P.LIP_H + 1))
    # bosses through the NPTH holes
    for (x, y) in holes_xy():
        t = t.union(cyl(x, y, P.Z_FLOOR_TOP - EPS, P.Z_PCB_BOT, P.BOSS_D))
        t = t.cut(cyl(x, y, P.Z_DESK - 1, 1, P.SCREW_CLR_D))
        t = t.cut(cyl(x, y, P.Z_DESK - 1, P.Z_DESK + P.SCREW_HEAD_CB_H, P.SCREW_HEAD_CB_D))
    # TC2030 / UART service hatch: through opening + recess for the cover flange
    hx, hy = P.K(*P.HATCH_CENTRE_K)
    w, h = P.HATCH
    r = P.HATCH_RECESS
    t = t.cut(box(hx - w / 2, hy - h / 2, P.Z_DESK - 1, hx + w / 2, hy + h / 2, P.Z_FLOOR_TOP + 1))
    t = t.cut(box(hx - w / 2 - r, hy - h / 2 - r, P.Z_DESK - 1, hx + w / 2 + r, hy + h / 2 + r,
                  P.Z_DESK + P.HATCH_COVER_T))
    # BOOT pinhole + guide tube under SW1 (bottom-side B3U)
    bx, by = P.K(*P.fp("SW1")["pos"])
    tube_top = P.Z_PCB_BOT - P.B3U_H - P.BOOT_TUBE_GAP
    t = t.union(cyl(bx, by, P.Z_FLOOR_TOP - EPS, tube_top, P.BOOT_TUBE_OD))
    t = t.cut(cyl(bx, by, P.Z_DESK - 1, tube_top + 1, P.BOOT_HOLE_D))
    t = t.cut(cyl(bx, by, P.Z_DESK - 1, P.Z_DESK + 0.6, P.BOOT_HOLE_D + 1.2).faces(">Z").chamfer(0.5))
    # steel-plate locating pins (plate is bonded with VHB; pins stop it sliding before the tape sets)
    for (kx, ky) in P.PLATE_PIN_K:
        t = t.union(cyl(*P.K(kx, ky), P.Z_FLOOR_TOP - EPS, P.Z_FLOOR_TOP + P.PLATE_PIN_H, P.PLATE_PIN_D)
                    .faces(">Z").chamfer(0.3))
    # silicone-foot pockets (the NE foot sits in the hatch cover instead)
    for name, (x, y) in P.FEET.items():
        if name != "NE_cover":
            t = t.cut(foot_pocket(x, y))
    t = t.cut(usb_cuts())
    return t


def hatch_cover():
    hx, hy = P.K(*P.HATCH_CENTRE_K)
    w, h = P.HATCH
    r, g = P.HATCH_RECESS, 0.1
    c = box(hx - w / 2 - r + g, hy - h / 2 - r + g, P.Z_DESK, hx + w / 2 + r - g, hy + h / 2 + r - g,
            P.Z_DESK + P.HATCH_COVER_T)
    c = c.union(box(hx - w / 2 + g, hy - h / 2 + g, P.Z_DESK + P.HATCH_COVER_T - EPS,
                    hx + w / 2 - g, hy + h / 2 - g, P.Z_FLOOR_TOP))
    # thumbnail notch + "UART/SWD" is printed on the label later
    c = c.cut(cyl(hx - w / 2 - r + g, hy, P.Z_DESK - 1, P.Z_DESK + 0.5, 3.0))
    if "NE_cover" in P.FEET:
        c = c.cut(foot_pocket(*P.FEET["NE_cover"]))
    return c


def foot_pocket(x, y):
    return cyl(x, y, P.Z_DESK - 1, P.Z_DESK + P.FOOT_POCKET_DEPTH, P.FOOT_D + 2 * P.FOOT_POCKET_CLR)


def feet():
    """Stock adhesive silicone feet (purchased; modelled for interference and the assembly)."""
    f = None
    for (x, y) in P.FEET.values():
        b = cyl(x, y, P.Z_DESK + P.FOOT_POCKET_DEPTH - P.FOOT_H, P.Z_DESK + P.FOOT_POCKET_DEPTH, P.FOOT_D)
        b = b.faces("<Z").edges().fillet(0.8)
        f = b if f is None else f.union(b)
    return f


def knob(shaft_top=None, knob_h=None, insert=None):
    shaft_top = P.SHAFT_TOP if shaft_top is None else shaft_top
    kh = P.KNOB_H if knob_h is None else knob_h
    insert = P.KNOB_INSERT if insert is None else insert
    ax, ay = enc_xy()
    z0, z1 = P.KNOB_BOTTOM, P.KNOB_BOTTOM + kh
    k = cyl(ax, ay, z0, z1, P.KNOB_D).faces(">Z").edges().fillet(1.0)
    n = 30                                    # grip flutes
    for i in range(n):
        a = 2 * math.pi * i / n
        k = k.cut(cyl(ax + (P.KNOB_D / 2 + 0.25) * math.cos(a), ay + (P.KNOB_D / 2 + 0.25) * math.sin(a),
                      z0 + 1.0, z1 - 1.5, 1.0))
    # radial bearing pocket over the lid collar
    k = k.cut(cyl(ax, ay, z0 - 1, P.KNOB_POCKET_TOP, P.COLLAR_OD + 2 * P.KNOB_BEARING_CLR))
    bore_top = shaft_top + P.KNOB_TOP_CLR
    if bore_top + P.KNOB_TOP_SKIN > z1 + 1e-6:
        raise ValueError(f"knob H {kh} too short: needs >= {bore_top + P.KNOB_TOP_SKIN - z0:.2f}")
    if insert == "sleeve":
        k = k.cut(cyl(ax, ay, P.KNOB_POCKET_TOP - EPS, bore_top, P.SLEEVE_OD))
    else:
        d = cyl(ax, ay, P.KNOB_POCKET_TOP - EPS, bore_top, P.ENC_SHAFT_D + 0.1)
        flat = box(ax - 5, ay + P.ENC_FLAT / 2 + 0.05, P.KNOB_POCKET_TOP - 1, ax + 5, ay + 5, bore_top + 1)
        k = k.cut(d.cut(flat))
        if insert == "setscrew":
            zm = (P.KNOB_POCKET_TOP + shaft_top) / 2
            k = k.cut(cq.Workplane("YZ").circle(P.SETSCREW_INSERT_D / 2).extrude(P.KNOB_D)
                      .translate((ax, ay, zm)))
    return k


def knob_sleeve(shaft_top=None):
    ax, ay = enc_xy()
    top = (P.SHAFT_TOP if shaft_top is None else shaft_top) + P.KNOB_TOP_CLR
    s = cyl(ax, ay, P.KNOB_POCKET_TOP, min(P.KNOB_POCKET_TOP + P.SLEEVE_L, top), P.SLEEVE_OD - 0.02)
    d = cyl(ax, ay, P.KNOB_POCKET_TOP - 1, top + 1, P.ENC_SHAFT_D + 0.05)
    flat = box(ax - 5, ay + P.ENC_FLAT / 2 + 0.03, P.KNOB_POCKET_TOP - 2, ax + 5, ay + 5, top + 2)
    return s.cut(d.cut(flat))


def button_cap(x, y):
    nub_bot = P.B3U_H + P.CAP_FREE
    bar_z0 = nub_bot + 0.4
    bar_z1 = bar_z0 + 1.0
    foot_bot = P.CAP_FREE + P.B3U_STROKE + P.CAP_STOP_EXTRA      # = hard-stop travel
    head_top = P.LID_TOP + P.CAP_PROUD
    c = cyl(x, y, bar_z1 - EPS, head_top, P.CAP_D).faces(">Z").edges().fillet(0.6)
    o = P.CAP_FOOT_OFS + P.CAP_FOOT_D / 2
    c = c.union(box(x - 0.6, y - o, bar_z0, x + 0.6, y + o, bar_z1))
    c = c.union(cyl(x, y, nub_bot, bar_z0 + EPS, 1.5))
    for s in (-1, 1):
        c = c.union(cyl(x, y + s * P.CAP_FOOT_OFS, foot_bot, bar_z0 + EPS, P.CAP_FOOT_D))
        # cantilever arm just under the lid, bump at the tip touches the lid underside
        za = P.LID_UNDER - P.CAP_ARM_BUMP - P.CAP_ARM_T
        r0 = P.CAP_D / 2 - 0.3
        ya, yb = sorted((y + s * r0, y + s * (r0 + P.CAP_ARM_L)))
        c = c.union(box(x - P.CAP_ARM_W / 2, ya, za, x + P.CAP_ARM_W / 2, yb, za + P.CAP_ARM_T))
        yt = y + s * (r0 + P.CAP_ARM_L - 0.5)
        c = c.union(cyl(x, yt, za + P.CAP_ARM_T - EPS, P.LID_UNDER, 0.9))
    return c


def light_pipe():
    x, y = led_xy()
    p = cyl(x, y, P.LED_H + P.PIPE_GAP, P.LID_TOP, P.PIPE_D)
    p = p.union(cyl(x, y, P.LID_UNDER - P.PIPE_FLANGE_T, P.LID_UNDER, P.PIPE_FLANGE_D))
    return p


def _poly_solid(ring_coords, z0, z1):
    pts = [P.K(x, y) for (x, y) in list(ring_coords)[:-1]]
    return cq.Workplane("XY").workplane(offset=z0).polyline(pts).close().extrude(z1 - z0)


def ballast():
    """Laser-cut steel plate, outline from plate.py (largest shape that fits under the board)."""
    import plate
    s = plate.outline()
    z0, z1 = P.Z_FLOOR_TOP, P.Z_FLOOR_TOP + P.PLATE_T
    b = _poly_solid(s.exterior.coords, z0, z1)
    for i in s.interiors:
        b = b.cut(_poly_solid(i.coords, z0 - 1, z1 + 1))
    return b


def build_all():
    (b1, b2) = btn_xy()
    parts = {
        "top_shell": top_shell(),
        "bottom_tray": tray(),
        "hatch_cover": hatch_cover(),
        "knob": knob(),
        "button_cap_btn1": button_cap(*b1),
        "button_cap_btn2": button_cap(*b2),
        "light_pipe": light_pipe(),
        "ballast": ballast(),
        "feet": feet(),
    }
    if P.KNOB_INSERT == "sleeve":
        parts["knob_sleeve"] = knob_sleeve()
    return parts
