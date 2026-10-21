#!/usr/bin/env python3
"""Dump the CadQuery parameter set (cad/params.py) plus the board-derived points the parts need into
params.json, the single input of the FreeCAD port (build_fc.py writes it into the Params spreadsheet).

Run with the CadQuery venv (needs shapely for the plate outline):  python export_params.py
"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "cad"))
import params as P          # noqa: E402
import parts as PT          # noqa: E402
import plate                # noqa: E402

scalars, docs = {}, {}
for k in dir(P):
    if not k.isupper() or k.startswith("_"):
        continue
    v = getattr(P, k)
    if isinstance(v, bool):
        continue
    if isinstance(v, (int, float)):
        scalars[k] = float(v)
    elif isinstance(v, (tuple, list)) and v and all(isinstance(x, (int, float)) for x in v):
        for i, x in enumerate(v):
            scalars[f"{k}_{i}"] = float(x)
scalars["J1_X"] = P.fp("J1")["pos"][0]
scalars["J1_BODY_H"] = P.J1_BODY["h"]

pt = lambda xy: [round(float(xy[0]), 4), round(float(xy[1]), 4)]
s = plate.outline()
points = {
    "screw_holes": [pt(p) for p in PT.holes_xy()],
    "module_holes": [pt(p) for p in PT.module_holes()],
    "window_centre": [pt(PT.window_centre())],
    "enc_axis": [pt(PT.enc_xy())],
    "buttons": [pt(p) for p in PT.btn_xy()],
    "led": [pt(PT.led_xy())],
    "boot": [pt(P.K(*P.fp("SW1")["pos"]))],
    "hatch_centre": [pt(P.K(*P.HATCH_CENTRE_K))],
    "plate_pins": [pt(P.K(*k)) for k in P.PLATE_PIN_K],
    "feet": [pt(v) for v in P.FEET.values()],
}
feet_names = list(P.FEET.keys())
rings = [[pt(P.K(x, y)) for (x, y) in list(r.coords)[:-1]] for r in [s.exterior] + list(s.interiors)]
out = dict(source="cad/params.py", board_ref=P.BOARD["source_ref"], process=P.PROCESS, knob_insert=P.KNOB_INSERT,
           scalars=scalars, points=points, feet_names=feet_names, plate_rings_cad=rings)
json.dump(out, open(os.path.join(HERE, "params.json"), "w"), indent=1)
print(len(scalars), "scalars,", sum(len(v) for v in points.values()), "points,", len(rings), "plate rings")
