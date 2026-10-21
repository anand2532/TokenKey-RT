"""Headless FreeCAD driver: params.json -> puck.FCStd (Params/Points/Plate sheets + one Part per part),
assembly.FCStd (links to the parts + the CadQuery board keep-out STEP), and STEP/STL per part in exports/.

    freecadcmd build_fc.py        (or through the FreeCAD MCP: execute_code_headless(exec(open(...).read())))
"""
import json, os, sys
import FreeCAD as App
import Part, Mesh, Import

HERE = os.environ.get("TK_FC_DIR") or os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fc_parts  # noqa: E402

EXP = os.path.join(HERE, "exports")
os.makedirs(EXP, exist_ok=True)
data = json.load(open(os.path.join(HERE, "params.json")))

for d in list(App.listDocuments()):
    App.closeDocument(d)
doc = App.newDocument("puck")
sh = doc.addObject("Spreadsheet::Sheet", "Params")
sh.set("A1", "name"); sh.set("B1", "value"); sh.set("D1", "source"); sh.set("E1", "knob_insert")
sh.set("D2", f"{data['source']} @ board {data['board_ref']}, process {data['process']}")
sh.set("E2", data["knob_insert"])
# Derived values are live spreadsheet formulas (same equations as the "derived" block of params.py),
# so editing a base value (e.g. WALL, HEADER_H, LID_T) propagates; column C marks them.
DERIVED = {
    "OLED_TOP": "HEADER_H + OLED_MODULE_T", "LID_UNDER": "OLED_TOP + LID_GLASS_CLR", "LID_TOP": "LID_UNDER + LID_T",
    "Z_PCB_BOT": "-PCB_T", "Z_FLOOR_TOP": "Z_PCB_BOT - UNDER_BOARD", "Z_DESK": "Z_FLOOR_TOP - FLOOR_T",
    "Z_SPLIT": "Z_PCB_BOT", "BODY_H": "LID_TOP - Z_DESK",
    "OUT_W": "PCB_W + 2 * (BOARD_CLR + WALL)", "OUT_D": "PCB_D + 2 * (BOARD_CLR + WALL)",
    "IN_X0": "-BOARD_CLR", "IN_Y0": "-BOARD_CLR", "OUT_X0": "-BOARD_CLR - WALL", "OUT_Y0": "-BOARD_CLR - WALL",
    "SHAFT_TOP": "ENC_BODY_2 + SHAFT_L - SHAFT_TRIM", "FLAT_START": "ENC_BODY_2 + SHAFT_L - ENC_FLAT_L",
    "KNOB_BOTTOM": "LID_TOP + ENC_PUSH + KNOB_PUSH_CLR", "COLLAR_TOP": "LID_TOP + COLLAR_H",
    "KNOB_POCKET_TOP": "FLAT_START + KNOB_DKEY_MARGIN", "KNOB_TOP": "KNOB_BOTTOM + KNOB_H",
    "KNOB_H_MIN": "SHAFT_TOP + KNOB_TOP_CLR + KNOB_TOP_SKIN - KNOB_BOTTOM",
    "ENGAGEMENT": "SHAFT_TOP - KNOB_POCKET_TOP", "FOOT_PROUD": "FOOT_H - FOOT_POCKET_DEPTH",
}
sh.set("C1", "kind")
for i, (k, v) in enumerate(sorted(data["scalars"].items()), start=2):
    sh.set(f"A{i}", k)
    sh.set(f"B{i}", repr(v))
    sh.set(f"C{i}", "derived" if k in DERIVED else "base")
    try:
        sh.setAlias(f"B{i}", k)
    except Exception:
        pass                                   # alias clashes with a cell name -> value still by row
pt = doc.addObject("Spreadsheet::Sheet", "Points")
pt.set("A1", "group"); pt.set("B1", "i"); pt.set("C1", "x_cad"); pt.set("D1", "y_cad")
pt.set("F1", "feet_names"); pt.set("F2", ",".join(data["feet_names"]))
row = 2
for g, lst in data["points"].items():
    for i, (x, y) in enumerate(lst):
        pt.set(f"A{row}", g); pt.set(f"B{row}", str(i)); pt.set(f"C{row}", repr(x)); pt.set(f"D{row}", repr(y))
        row += 1
pl = doc.addObject("Spreadsheet::Sheet", "Plate")
pl.set("A1", "ring"); pl.set("B1", "x_cad"); pl.set("C1", "y_cad")
row = 2
for r, ring in enumerate(data["plate_rings_cad"]):
    for (x, y) in ring:
        pl.set(f"A{row}", str(r)); pl.set(f"B{row}", repr(x)); pl.set(f"C{row}", repr(y))
        row += 1
doc.recompute()
rows = {k: i for i, k in enumerate(sorted(data["scalars"]), start=2)}
for k, expr in DERIVED.items():
    if k in rows:
        sh.set(f"B{rows[k]}", "=" + expr)
doc.recompute()
for k in DERIVED:                                      # the formulas must reproduce params.py exactly
    if k in rows:
        assert abs(float(sh.get(k)) - data["scalars"][k]) < 1e-9, (k, sh.get(k), data["scalars"][k])

shapes = fc_parts.rebuild(doc)
doc.saveAs(os.path.join(HERE, "puck.FCStd"))
stats = {}
for k, s in shapes.items():
    bb = s.BoundBox
    stats[k] = dict(volume=s.Volume, bbox=[bb.XMin, bb.YMin, bb.ZMin, bb.XMax, bb.YMax, bb.ZMax], valid=s.isValid(),
                    solids=len(s.Solids))
    s.exportStep(os.path.join(EXP, f"{k}.step"))
    m = Mesh.Mesh()
    m.addFacets(s.tessellate(0.02))
    m.write(os.path.join(EXP, f"{k}.stl"))
    print(k, "vol", round(s.Volume, 3), "bbox", [round(v, 3) for v in (s.BoundBox.XMin, s.BoundBox.YMin, s.BoundBox.ZMin,
                                                                     s.BoundBox.XMax, s.BoundBox.YMax, s.BoundBox.ZMax)],
          "valid", s.isValid())

# assembly: links to the parts + the board keep-out (reference, from the CadQuery build)
asm = App.newDocument("assembly")
asm.saveAs(os.path.join(HERE, "assembly.FCStd"))          # cross-document links need a saved owner
grp = asm.addObject("App::Part", "TokenKey_RT_puck")
for k in shapes:
    l = asm.addObject("App::Link", k)
    l.setLink(doc.getObject(k))
    grp.addObject(l)
ko = os.path.join(HERE, "..", "exports", "board_keepout.step")
ref = asm.addObject("Part::Feature", "board_keepout_ref")
ref.Shape = Part.read(ko)
grp.addObject(ref)
asm.recompute()
asm.saveAs(os.path.join(HERE, "assembly.FCStd"))
doc.save()
json.dump(stats, open(os.path.join(EXP, "fc_stats.json"), "w"), indent=1)
print("saved", os.path.join(HERE, "puck.FCStd"), os.path.join(HERE, "assembly.FCStd"))
