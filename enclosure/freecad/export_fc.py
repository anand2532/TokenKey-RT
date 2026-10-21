"""Authoritative export (FreeCAD is the source of truth since PM sign-off, #63).

Opens puck.FCStd, rebuilds every part from ITS OWN Params / Points / Plate sheets (it never reads
params.json or cad/params.py), saves it, refreshes assembly.FCStd, and writes:
  exports/<part>.step, exports/<part>.stl, exports/fc_stats.json, exports/params_fc.json (sheet dump).
Run:  freecadcmd -c "exec(open('export_fc.py').read())"   or via user-freecad execute_code_headless.
"""
import json, os, sys
import FreeCAD as App
import Mesh

HERE = os.environ.get("TK_FC_DIR") or os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fc_parts  # noqa: E402

EXP = os.path.join(HERE, "exports")
os.makedirs(EXP, exist_ok=True)
for d in list(App.listDocuments()):
    App.closeDocument(d)
doc = App.openDocument(os.path.join(HERE, "puck.FCStd"))
shapes = fc_parts.rebuild(doc)
doc.save()
stats = {}
for k, s in shapes.items():
    bb = s.BoundBox
    stats[k] = dict(volume=s.Volume, bbox=[bb.XMin, bb.YMin, bb.ZMin, bb.XMax, bb.YMax, bb.ZMax], valid=s.isValid(),
                    solids=len(s.Solids))
    s.exportStep(os.path.join(EXP, f"{k}.step"))
    m = Mesh.Mesh()
    m.addFacets(s.tessellate(0.02))
    m.write(os.path.join(EXP, f"{k}.stl"))
json.dump(stats, open(os.path.join(EXP, "fc_stats.json"), "w"), indent=1)
P, pts, rings = fc_parts.read_params(doc)
json.dump(dict(params={k: v for k, v in P.items() if not k.startswith("_")}, knob_insert=P["_insert"],
               points={k: v for k, v in pts.items()}), open(os.path.join(EXP, "params_fc.json"), "w"), indent=1)
asm = App.openDocument(os.path.join(HERE, "assembly.FCStd"))
asm.recompute()
asm.save()
print("exported", len(shapes), "parts from puck.FCStd")
