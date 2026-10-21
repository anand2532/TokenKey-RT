"""FreeCAD (Part workbench) port of cad/parts.py, the Direction A puck.

Every dimension is read from the document's `Params` spreadsheet (alias = the params.py name), and
every board-derived point from the `Points` / `Plate` sheets. Nothing is hard-coded here except the
modelling recipe, which mirrors cad/parts.py one-to-one (same function names, same order of operations).

    rebuild(doc)  -> regenerates every part object (Part::Feature) from the sheets.
Run inside FreeCAD (GUI macro rebuild.FCMacro, or freecadcmd via build_fc.py).
"""
import math
import FreeCAD as App
import Part

V = App.Vector
EPS = 0.01
PART_NAMES = ["top_shell", "bottom_tray", "hatch_cover", "knob", "button_cap_btn1", "button_cap_btn2",
              "light_pipe", "ballast", "feet", "knob_sleeve"]


def _txt(sheet, cell):
    return sheet.getContents(cell).lstrip("'")


class Params(dict):
    """Attribute access to the Params sheet: P.WALL, P.USB_OUTER_0 ..."""
    __getattr__ = dict.__getitem__


def read_params(doc):
    sh = doc.getObject("Params")
    P = Params()
    row = 2
    while True:
        name = _txt(sh, f"A{row}")
        if not name:
            break
        P[name] = float(sh.get(f"B{row}"))
        row += 1
    pts = {}
    shp = doc.getObject("Points")
    row = 2
    while shp.getContents(f"A{row}"):
        g = _txt(shp, f"A{row}")
        pts.setdefault(g, []).append((float(shp.get(f"C{row}")), float(shp.get(f"D{row}"))))
        row += 1
    rings = {}
    shr = doc.getObject("Plate")
    row = 2
    while shr.getContents(f"A{row}"):
        r = int(float(shr.get(f"A{row}")))
        rings.setdefault(r, []).append((float(shr.get(f"B{row}")), float(shr.get(f"C{row}"))))
        row += 1
    meta = doc.getObject("Params")
    P["_insert"] = _txt(meta, "E2") or "sleeve"
    return P, pts, [rings[k] for k in sorted(rings)]


# ---- primitives (same semantics as the CadQuery helpers) ------------------------------------
def box(x0, y0, z0, x1, y1, z1):
    return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))


def cyl(x, y, z0, z1, d):
    return Part.makeCylinder(d / 2, z1 - z0, V(x, y, z0))


def _edges_par_z(s):
    return [e for e in s.Edges if isinstance(e.Curve, Part.Line)
            and abs(abs(e.Curve.Direction.z) - 1) < 1e-9]


def _face_at(s, top=True):
    return max(s.Faces, key=lambda f: f.CenterOfMass.z) if top else min(s.Faces, key=lambda f: f.CenterOfMass.z)


def fillet_face(s, r, top=True):
    return s.makeFillet(r, _face_at(s, top).Edges)


def chamfer_face(s, d, top=True):
    return s.makeChamfer(d, _face_at(s, top).Edges)


def rrect(x0, y0, w, h, r, z0, z1):
    b = box(x0, y0, z0, x0 + w, y0 + h, z1)
    return b.makeFillet(r, _edges_par_z(b))


def fuse(*shapes):
    s = shapes[0]
    for t in shapes[1:]:
        s = s.fuse(t)
    return s


def clean(s):
    s = s.removeSplitter()
    return s.Solids[0] if len(s.Solids) == 1 else s


class Model:
    def __init__(self, P, pts, rings):
        self.P, self.pts, self.rings = P, pts, rings
        p = P
        self.OLED_TOP = p.HEADER_H + p.OLED_MODULE_T
        self.LID_UNDER = self.OLED_TOP + p.LID_GLASS_CLR
        self.LID_TOP = self.LID_UNDER + p.LID_T
        self.Z_PCB_BOT = -p.PCB_T
        self.Z_FLOOR_TOP = self.Z_PCB_BOT - p.UNDER_BOARD
        self.Z_DESK = self.Z_FLOOR_TOP - p.FLOOR_T
        self.Z_SPLIT = self.Z_PCB_BOT

    # -- shells --
    def outer(self, z0, z1, inset=0.0):
        p = self.P
        return rrect(p.OUT_X0 + inset, p.OUT_Y0 + inset, p.OUT_W - 2 * inset, p.OUT_D - 2 * inset,
                     max(p.CORNER_R - inset, 0.3), z0, z1)

    def inner(self, z0, z1, grow=0.0):
        p = self.P
        return rrect(p.IN_X0 - grow, p.IN_Y0 - grow, p.PCB_W + 2 * p.BOARD_CLR + 2 * grow,
                     p.PCB_D + 2 * p.BOARD_CLR + 2 * grow, max(p.INNER_R + grow, 0.3), z0, z1)

    def ring(self, z0, z1, inset_out, inset_in):
        return self.outer(z0, z1, inset_out).cut(self.outer(z0 - 1, z1 + 1, inset_in))

    def usb_cuts(self):
        p = self.P
        x = p.J1_X
        ow, oh, iw, ih = p.USB_OUTER_0, p.USB_OUTER_1, p.USB_INNER_0, p.USB_INNER_1
        yo = p.OUT_Y0 - 1
        pocket = box(x - ow / 2, yo, p.USB_Z - oh / 2, x + ow / 2, p.IN_Y0 - p.USB_SKIN, p.USB_Z + oh / 2)
        pocket = pocket.makeFillet(1.5, [e for e in pocket.Edges if abs(abs(e.Curve.Direction.y) - 1) < 1e-9])
        hole = box(x - iw / 2, yo, p.USB_Z - ih / 2, x + iw / 2, p.IN_Y0 + 1, p.USB_Z + ih / 2)
        hole = hole.makeFillet(1.2, [e for e in hole.Edges if abs(abs(e.Curve.Direction.y) - 1) < 1e-9])
        return pocket.fuse(hole)

    # -- parts --
    def top_shell(self):
        p, M = self.P, self
        s = fillet_face(M.outer(M.Z_SPLIT, M.LID_TOP), p.TOP_EDGE_FILLET, top=True)
        s = s.cut(M.inner(M.Z_SPLIT - 1, M.LID_UNDER))
        s = s.cut(M.outer(M.Z_SPLIT - 1, M.Z_SPLIT + p.LIP_H).cut(
            M.outer(M.Z_SPLIT - 2, M.Z_SPLIT + p.LIP_H + 1, p.LIP_T + p.LIP_CLR)))
        (cx, cy), = self.pts["window_centre"]
        w, h = p.WINDOW_0, p.WINDOW_1
        grow = p.LID_T * math.tan(math.radians(p.WINDOW_CHAMFER))
        z0, z1 = M.LID_UNDER - EPS, M.LID_UNDER - EPS + p.LID_T + 2 * EPS

        def rect(z, ww, hh):
            return Part.makePolygon([V(cx - ww / 2, cy - hh / 2, z), V(cx + ww / 2, cy - hh / 2, z),
                                     V(cx + ww / 2, cy + hh / 2, z), V(cx - ww / 2, cy + hh / 2, z),
                                     V(cx - ww / 2, cy - hh / 2, z)])
        s = s.cut(Part.makeLoft([rect(z0, w, h), rect(z1, w + 2 * grow, h + 2 * grow)], True))
        zt = p.HEADER_H + p.OLED_PCB_T
        adds = []
        for (x, y) in self.pts["module_holes"]:
            adds.append(cyl(x, y, zt + p.LOC_SHOULDER_GAP, M.LID_UNDER + EPS, p.LOC_SHOULDER_D))
            adds.append(chamfer_face(cyl(x, y, zt - p.LOC_PIN_BELOW, zt + p.LOC_SHOULDER_GAP + EPS, p.LOC_PIN_D),
                                     0.4, top=False))
        for (x, y) in self.pts["screw_holes"]:
            adds.append(cyl(x, y, 0, M.LID_UNDER + EPS, p.POST_D))
        s = s.fuse(fuse(*adds))
        for (x, y) in self.pts["screw_holes"]:
            s = s.cut(cyl(x, y, -EPS, p.INSERT_DEPTH + 1.0, p.INSERT_D))
        (ax, ay), = self.pts["enc_axis"]
        bx, by, bh = p.ENC_BODY_0, p.ENC_BODY_1, p.ENC_BODY_2
        relief_top = bh + p.ENC_LID_RELIEF_CLR
        if relief_top > M.LID_UNDER:
            s = s.cut(box(ax - bx / 2 - 0.5, ay - by / 2 - 0.5, M.LID_UNDER - EPS,
                          ax + bx / 2 + 0.5, ay + by / 2 + 0.5, relief_top))
        s = s.fuse(cyl(ax, ay, M.LID_TOP - 0.3, M.LID_TOP + p.COLLAR_H, p.COLLAR_OD))
        s = s.cut(cyl(ax, ay, 0, M.LID_TOP + p.COLLAR_H + 1, p.ENC_HOLE_D))
        for (x, y) in self.pts["buttons"]:
            s = s.cut(cyl(x, y, 0, M.LID_TOP + 1, p.CAP_HOLE_D))
        (lx, ly), = self.pts["led"]
        s = s.cut(cyl(lx, ly, 0, M.LID_TOP + 1, p.PIPE_D + 0.05))
        s = s.cut(M.usb_cuts())
        x = p.J1_X
        s = s.fuse(box(x - p.USB_RIB_W / 2, p.IN_Y0 - EPS, p.J1_BODY_H + p.USB_RIB_GAP,
                       x + p.USB_RIB_W / 2, p.IN_Y0 + p.USB_RIB_LEN, M.LID_UNDER + EPS))
        return clean(s)

    def foot_pocket(self, x, y):
        p = self.P
        return cyl(x, y, self.Z_DESK - 1, self.Z_DESK + p.FOOT_POCKET_DEPTH, p.FOOT_D + 2 * p.FOOT_POCKET_CLR)

    def bottom_tray(self):
        p, M = self.P, self
        t = fillet_face(M.outer(M.Z_DESK, M.Z_SPLIT), 0.8, top=False)
        t = t.fuse(M.ring(M.Z_SPLIT - EPS, M.Z_SPLIT + p.LIP_H, 0, p.LIP_T))
        t = t.cut(M.inner(M.Z_FLOOR_TOP, M.Z_SPLIT + p.LIP_H + 1))
        for (x, y) in self.pts["screw_holes"]:
            t = t.fuse(cyl(x, y, M.Z_FLOOR_TOP - EPS, M.Z_PCB_BOT, p.BOSS_D))
            t = t.cut(cyl(x, y, M.Z_DESK - 1, 1, p.SCREW_CLR_D))
            t = t.cut(cyl(x, y, M.Z_DESK - 1, M.Z_DESK + p.SCREW_HEAD_CB_H, p.SCREW_HEAD_CB_D))
        (hx, hy), = self.pts["hatch_centre"]
        w, h, r = p.HATCH_0, p.HATCH_1, p.HATCH_RECESS
        t = t.cut(box(hx - w / 2, hy - h / 2, M.Z_DESK - 1, hx + w / 2, hy + h / 2, M.Z_FLOOR_TOP + 1))
        t = t.cut(box(hx - w / 2 - r, hy - h / 2 - r, M.Z_DESK - 1, hx + w / 2 + r, hy + h / 2 + r,
                      M.Z_DESK + p.HATCH_COVER_T))
        (bx, by), = self.pts["boot"]
        tube_top = M.Z_PCB_BOT - p.B3U_H - p.BOOT_TUBE_GAP
        t = t.fuse(cyl(bx, by, M.Z_FLOOR_TOP - EPS, tube_top, p.BOOT_TUBE_OD))
        t = t.cut(cyl(bx, by, M.Z_DESK - 1, tube_top + 1, p.BOOT_HOLE_D))
        t = t.cut(chamfer_face(cyl(bx, by, M.Z_DESK - 1, M.Z_DESK + 0.6, p.BOOT_HOLE_D + 1.2), 0.5, top=True))
        for (x, y) in self.pts["plate_pins"]:
            t = t.fuse(chamfer_face(cyl(x, y, M.Z_FLOOR_TOP - EPS, M.Z_FLOOR_TOP + p.PLATE_PIN_H, p.PLATE_PIN_D),
                                    0.3, top=True))
        for name, (x, y) in zip(self.pts["_feet_names"], self.pts["feet"]):
            if name != "NE_cover":
                t = t.cut(M.foot_pocket(x, y))
        t = t.cut(M.usb_cuts())
        return clean(t)

    def hatch_cover(self):
        p, M = self.P, self
        (hx, hy), = self.pts["hatch_centre"]
        w, h, r, g = p.HATCH_0, p.HATCH_1, p.HATCH_RECESS, 0.1
        c = box(hx - w / 2 - r + g, hy - h / 2 - r + g, M.Z_DESK, hx + w / 2 + r - g, hy + h / 2 + r - g,
                M.Z_DESK + p.HATCH_COVER_T)
        c = c.fuse(box(hx - w / 2 + g, hy - h / 2 + g, M.Z_DESK + p.HATCH_COVER_T - EPS,
                       hx + w / 2 - g, hy + h / 2 - g, M.Z_FLOOR_TOP))
        c = c.cut(cyl(hx - w / 2 - r + g, hy, M.Z_DESK - 1, M.Z_DESK + 0.5, 3.0))
        for name, (x, y) in zip(self.pts["_feet_names"], self.pts["feet"]):
            if name == "NE_cover":
                c = c.cut(M.foot_pocket(x, y))
        return clean(c)

    def _knob_z(self):
        p, M = self.P, self
        shaft_top = p.ENC_BODY_2 + p.SHAFT_L - p.SHAFT_TRIM
        flat_start = p.ENC_BODY_2 + p.SHAFT_L - p.ENC_FLAT_L
        kb = M.LID_TOP + p.ENC_PUSH + p.KNOB_PUSH_CLR
        return shaft_top, kb, flat_start + p.KNOB_DKEY_MARGIN

    def knob(self):
        p, M = self.P, self
        shaft_top, z0, pocket_top = M._knob_z()
        z1 = z0 + p.KNOB_H
        (ax, ay), = self.pts["enc_axis"]
        k = fillet_face(cyl(ax, ay, z0, z1, p.KNOB_D), 1.0, top=True)
        fl = []
        for i in range(30):
            a = 2 * math.pi * i / 30
            fl.append(cyl(ax + (p.KNOB_D / 2 + 0.25) * math.cos(a), ay + (p.KNOB_D / 2 + 0.25) * math.sin(a),
                          z0 + 1.0, z1 - 1.5, 1.0))
        k = k.cut(fuse(*fl))
        k = k.cut(cyl(ax, ay, z0 - 1, pocket_top, p.COLLAR_OD + 2 * p.KNOB_BEARING_CLR))
        bore_top = shaft_top + p.KNOB_TOP_CLR
        if bore_top + p.KNOB_TOP_SKIN > z1 + 1e-6:
            raise ValueError("knob too short for the shaft")
        ins = p._insert
        if ins == "sleeve":
            k = k.cut(cyl(ax, ay, pocket_top - EPS, bore_top, p.SLEEVE_OD))
        else:
            d = cyl(ax, ay, pocket_top - EPS, bore_top, p.ENC_SHAFT_D + 0.1)
            flat = box(ax - 5, ay + p.ENC_FLAT / 2 + 0.05, pocket_top - 1, ax + 5, ay + 5, bore_top + 1)
            k = k.cut(d.cut(flat))
            if ins == "setscrew":
                zm = (pocket_top + shaft_top) / 2
                k = k.cut(Part.makeCylinder(p.SETSCREW_INSERT_D / 2, p.KNOB_D, V(ax, ay, zm), V(1, 0, 0)))
        return clean(k)

    def knob_sleeve(self):
        p, M = self.P, self
        shaft_top, _, pocket_top = M._knob_z()
        (ax, ay), = self.pts["enc_axis"]
        top = shaft_top + p.KNOB_TOP_CLR
        s = cyl(ax, ay, pocket_top, min(pocket_top + p.SLEEVE_L, top), p.SLEEVE_OD - 0.02)
        d = cyl(ax, ay, pocket_top - 1, top + 1, p.ENC_SHAFT_D + 0.05)
        flat = box(ax - 5, ay + p.ENC_FLAT / 2 + 0.03, pocket_top - 2, ax + 5, ay + 5, top + 2)
        return clean(s.cut(d.cut(flat)))

    def button_cap(self, x, y):
        p, M = self.P, self
        nub_bot = p.B3U_H + p.CAP_FREE
        bar_z0 = nub_bot + 0.4
        bar_z1 = bar_z0 + 1.0
        foot_bot = p.CAP_FREE + p.B3U_STROKE + p.CAP_STOP_EXTRA
        head_top = M.LID_TOP + p.CAP_PROUD
        c = fillet_face(cyl(x, y, bar_z1 - EPS, head_top, p.CAP_D), 0.6, top=True)
        o = p.CAP_FOOT_OFS + p.CAP_FOOT_D / 2
        adds = [box(x - 0.6, y - o, bar_z0, x + 0.6, y + o, bar_z1), cyl(x, y, nub_bot, bar_z0 + EPS, 1.5)]
        for s in (-1, 1):
            adds.append(cyl(x, y + s * p.CAP_FOOT_OFS, foot_bot, bar_z0 + EPS, p.CAP_FOOT_D))
            za = M.LID_UNDER - p.CAP_ARM_BUMP - p.CAP_ARM_T
            r0 = p.CAP_D / 2 - 0.3
            ya, yb = sorted((y + s * r0, y + s * (r0 + p.CAP_ARM_L)))
            adds.append(box(x - p.CAP_ARM_W / 2, ya, za, x + p.CAP_ARM_W / 2, yb, za + p.CAP_ARM_T))
            yt = y + s * (r0 + p.CAP_ARM_L - 0.5)
            adds.append(cyl(x, yt, za + p.CAP_ARM_T - EPS, M.LID_UNDER, 0.9))
        return clean(c.fuse(fuse(*adds)))

    def light_pipe(self):
        p, M = self.P, self
        (x, y), = self.pts["led"]
        s = cyl(x, y, p.LED_H + p.PIPE_GAP, M.LID_TOP, p.PIPE_D)
        s = s.fuse(cyl(x, y, M.LID_UNDER - p.PIPE_FLANGE_T, M.LID_UNDER, p.PIPE_FLANGE_D))
        return clean(s)

    def ballast(self):
        p, M = self.P, self
        z0, z1 = M.Z_FLOOR_TOP, M.Z_FLOOR_TOP + p.PLATE_T

        def prism(ring, za, zb):
            w = Part.makePolygon([V(x, y, za) for (x, y) in ring] + [V(ring[0][0], ring[0][1], za)])
            return Part.Face(w).extrude(V(0, 0, zb - za))
        b = prism(self.rings[0], z0, z1)
        for r in self.rings[1:]:
            b = b.cut(prism(r, z0 - 1, z1 + 1))
        return clean(b)

    def feet(self):
        p, M = self.P, self
        fs = []
        for (x, y) in self.pts["feet"]:
            f = cyl(x, y, M.Z_DESK + p.FOOT_POCKET_DEPTH - p.FOOT_H, M.Z_DESK + p.FOOT_POCKET_DEPTH, p.FOOT_D)
            fs.append(fillet_face(f, 0.8, top=False))
        return Part.makeCompound(fs)

    def build_all(self):
        (b1, b2) = self.pts["buttons"]
        out = {"top_shell": self.top_shell(), "bottom_tray": self.bottom_tray(), "hatch_cover": self.hatch_cover(),
               "knob": self.knob(), "button_cap_btn1": self.button_cap(*b1), "button_cap_btn2": self.button_cap(*b2),
               "light_pipe": self.light_pipe(), "ballast": self.ballast(), "feet": self.feet()}
        if self.P._insert == "sleeve":
            out["knob_sleeve"] = self.knob_sleeve()
        return out


COLORS = {"top_shell": (0.80, 0.82, 0.86), "bottom_tray": (0.30, 0.32, 0.36), "hatch_cover": (0.45, 0.47, 0.52),
          "knob": (0.62, 0.64, 0.68), "knob_sleeve": (0.85, 0.70, 0.30), "button_cap_btn1": (0.20, 0.45, 0.80),
          "button_cap_btn2": (0.20, 0.45, 0.80), "light_pipe": (0.85, 0.95, 1.0), "ballast": (0.55, 0.55, 0.55),
          "feet": (0.15, 0.15, 0.15)}


def rebuild(doc):
    """Regenerate every part object of `doc` from its Params / Points / Plate sheets."""
    P, pts, rings = read_params(doc)
    names = _txt(doc.getObject("Points"), "F2").split(",")
    pts["_feet_names"] = names
    shapes = Model(P, pts, rings).build_all()
    for k, s in shapes.items():
        o = doc.getObject(k) or doc.addObject("Part::Feature", k)
        o.Shape = s
        o.Label = k
        if App.GuiUp:
            o.ViewObject.ShapeColor = COLORS[k]
    doc.recompute()
    return shapes
