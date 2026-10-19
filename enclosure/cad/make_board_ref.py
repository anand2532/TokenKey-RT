#!/usr/bin/env python3
"""Slim the board_extract.py JSON down to what the enclosure CAD needs -> board_ref.json.

Usage:
  python3 ../tools/board_extract.py <TokenKey-RT.kicad_pcb> raw.json
  python3 make_board_ref.py raw.json <git-ref> > board_ref.json
Coordinates stay in KiCad board mm (x east, y SOUTH, origin top-left); the CAD converts them.
"""
import json, sys

raw = json.load(open(sys.argv[1]))
out = {"source_ref": sys.argv[2] if len(sys.argv) > 2 else "?",
       "board": {k: raw["board"][k] for k in ("size_mm", "thickness_mm")},
       "footprints": []}
for f in raw["footprints_all"]:
    out["footprints"].append({
        "ref": f["ref"], "value": f.get("value", ""), "fp": f["footprint"].split(":")[-1],
        "pos": f["pos_mm"], "rot": f["rot_deg"], "side": f["side"], "dnp": f["dnp"],
        "crtyd": f["courtyard_bbox"],
        "tht": [[p["pos"][0], p["pos"][1], max(p["drill"])] for p in f["pads"] if p["drill"][0] > 0],
    })
json.dump(out, sys.stdout, indent=1)
