"""Steel ballast plate under the board (#53): the largest outline that fits the 2.5 mm under-board gap.

Computed in KiCad board coordinates with shapely, from board_ref.json and params.py:
  base     = cavity inset by PLATE_EDGE_GAP
  minus    every bottom-side part whose underside comes within PLATE_Z_CLR of the plate top
           (courtyard + PLATE_PART_GAP), every THT lead tail (lead dia + 0.4, + PLATE_PART_GAP),
           the screw bosses, the BOOT guide tube and the service-hatch opening (+ recess + rim)
  then     a morphological opening of PLATE_MIN_FEATURE / 2 removes slivers; the largest piece is kept.
Returns shapely geometry (KiCad coords); parts.py extrudes it, build.py also writes a DXF.
"""
from shapely.geometry import box as sbox, Point
from shapely.ops import unary_union
import params as P


def keepouts():
    top = P.Z_FLOOR_TOP + P.PLATE_T                     # plate top (CAD z)
    g, ko = P.PLATE_PART_GAP, []
    import board_model as BM
    for f in P.BOARD["footprints"]:
        name = f["fp"]
        if f["side"] == "bottom":
            h = BM.HEIGHTS.get(name, BM.UNKNOWN_H)
            if -P.PCB_T - h < top + P.PLATE_Z_CLR:       # part reaches down too close to the plate
                ko.append(sbox(*f["crtyd"]).buffer(g, join_style=2))
        if not name.startswith("MountingHole") and f["ref"] != "J3":
            for (x, y, d) in f["tht"]:
                ko.append(Point(x, y).buffer((d + 0.4) / 2 + g))
    for f in P.BOARD["footprints"]:                      # tray screw bosses
        if name_is_hole(f):
            ko.append(Point(*f["pos"]).buffer(P.BOSS_D / 2 + g))
    bx, by = P.fp("SW1")["pos"]
    ko.append(Point(bx, by).buffer(P.BOOT_TUBE_OD / 2 + g))
    hx, hy = P.HATCH_CENTRE_K
    w, h = P.HATCH
    r = P.HATCH_RECESS + P.PLATE_HATCH_RIM
    ko.append(sbox(hx - w / 2 - r, hy - h / 2 - r, hx + w / 2 + r, hy + h / 2 + r))
    return unary_union(ko)


def name_is_hole(f):
    return f["fp"].startswith("MountingHole")


def outline():
    base = sbox(-P.BOARD_CLR + P.PLATE_EDGE_GAP, -P.BOARD_CLR + P.PLATE_EDGE_GAP,
                P.PCB_W + P.BOARD_CLR - P.PLATE_EDGE_GAP, P.PCB_D + P.BOARD_CLR - P.PLATE_EDGE_GAP)
    shape = base.difference(keepouts())
    m = P.PLATE_MIN_FEATURE / 2
    shape = shape.buffer(-m, join_style=2).buffer(m, join_style=1)
    if shape.geom_type == "MultiPolygon":
        shape = max(shape.geoms, key=lambda p: p.area)
    shape = shape.simplify(0.02)
    for (x, y) in P.PLATE_PIN_K:                          # locating-pin holes
        shape = shape.difference(Point(x, y).buffer(P.PLATE_PIN_HOLE_D / 2))
    return shape


if __name__ == "__main__":
    s = outline()
    b = s.bounds
    print("area mm2", round(s.area, 1), "bounds", [round(v, 2) for v in b],
          "holes", len(s.interiors), "mass g", round(s.area * P.PLATE_T * P.BALLAST_RHO / 1000, 1))
