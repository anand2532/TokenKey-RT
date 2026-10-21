#!/usr/bin/env python3
"""Print-ready STLs (#72): every printed part rotated into its print orientation, sitting on z = 0,
centred on x = y = 0, written to ../exports/print/<part>.stl, plus the tolerance coupon.

Orientation choices and reasons are in ../PRINTING.md (table "Orientation"). Purchased / non-printed
parts (steel plate -> DXF, feet, brass sleeve) are not exported here.
    python print_export.py
"""
import os
import cadquery as cq
import params as P
import parts as PT

OUT = os.path.join(os.path.dirname(P.HERE), "exports", "print")
# part -> (rotation axis, angle deg) applied about the part's own centre; None = as modelled
ORIENT = {
    "top_shell": None,            # lid up: the 5 mm knob boss stands above the lid, so it cannot print face-down
    "bottom_tray": None,          # floor on the bed: flat datum, pockets/counterbores are short bridges
    "hatch_cover": None,          # outer (desk) face on the bed -> flush, flat
    "knob": ((1, 0, 0), 180),     # top face on the bed: the collar pocket and sleeve bore open upward, no bridges
    "button_cap_btn1": None,      # SLA: head up, supports on the stop feet / bar underside only
    "button_cap_btn2": None,
    "light_pipe": None,           # SLA clear: optical top face up and unsupported; supports on the LED end
}
STL_TOL, STL_ANG = 0.01, 0.1


def place(shape, rot):
    s = shape
    if rot:
        bb = s.val().BoundingBox()
        c = cq.Vector((bb.xmin + bb.xmax) / 2, (bb.ymin + bb.ymax) / 2, (bb.zmin + bb.zmax) / 2)
        s = s.rotate(c, c + cq.Vector(*rot[0]), rot[1])
    bb = s.val().BoundingBox()
    return s.translate((-(bb.xmin + bb.xmax) / 2, -(bb.ymin + bb.ymax) / 2, -bb.zmin))


def coupon():
    """Tolerance coupon: the fits that matter, in one 62 x 26 x 3 mm plate (+ pegs), printed flat.
    Row 1 (holes, through):  M2 insert holes d 3.0/3.2/3.4  | M2 clearance d 2.2/2.4/2.6
    Row 2 (holes):           cap guide d 4.8/5.0/5.2       | foot pockets d 8.2/8.4/8.6 x 1.0 deep (blind)
    Pegs (separate, same plate edge): boss peg d 11.0 x 5 with 3 test rings bore 11.2/11.3/11.4
      (= 0.10/0.15/0.20 radial running fit, PRINTING.md), cap peg d 4.6 x 4."""
    t = 3.0
    plate = cq.Workplane("XY").box(62, 26, t, centered=(False, False, False))
    def hole(x, y, d, depth=None):
        return cq.Workplane("XY").circle(d / 2).extrude(depth or t + 2).translate((x, y, -1 if depth is None else t - depth))
    for i, d in enumerate((3.0, 3.2, 3.4)):
        plate = plate.cut(hole(5 + 6 * i, 6, d))
    for i, d in enumerate((2.2, 2.4, 2.6)):
        plate = plate.cut(hole(25 + 5 * i, 6, d))
    for i, d in enumerate((4.8, 5.0, 5.2)):
        plate = plate.cut(hole(5 + 7 * i, 18, d))
    for i, d in enumerate((8.2, 8.4, 8.6)):
        plate = plate.cut(hole(30 + 10 * i, 18, d, depth=1.0))
    # engraved labels are left to the slicer; hole order is ascending left -> right
    peg = cq.Workplane("XY").circle(P.COLLAR_OD / 2).extrude(5).translate((49, 6, t))
    cap = cq.Workplane("XY").circle(P.CAP_D / 2).extrude(4).translate((58, 6, t))
    out = plate.union(peg).union(cap)
    rings = None
    for i, bore in enumerate((11.2, 11.3, 11.4)):
        r = (cq.Workplane("XY").circle(8.0).circle(bore / 2).extrude(3.0).translate((10 + 20 * i, 40, 0)))
        rings = r if rings is None else rings.union(r)
    return out.union(rings)


def main():
    os.makedirs(OUT, exist_ok=True)
    parts = PT.build_all()
    for k, rot in ORIENT.items():
        cq.exporters.export(place(parts[k], rot), os.path.join(OUT, f"{k}.stl"), tolerance=STL_TOL, angularTolerance=STL_ANG)
        print("wrote", k)
    cq.exporters.export(place(coupon(), None), os.path.join(OUT, "tolerance_coupon.stl"), tolerance=STL_TOL,
                        angularTolerance=STL_ANG)
    print("wrote tolerance_coupon")


if __name__ == "__main__":
    main()
