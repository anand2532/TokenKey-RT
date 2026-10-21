"""Validate the FreeCAD port against the CadQuery reference (run in freecadcmd).

For every part: volume and bounding box of freecad/exports/<p>.step vs exports/<p>.step, plus the
symmetric-difference volume (geometry that exists in only one of the two). Then an interference pass
on the FreeCAD parts: part-part and part-vs-board-keep-out boolean overlaps and min distances.
Writes freecad/exports/validation.json; VALIDATION.md is written from it.
"""
import json, os, itertools
import FreeCAD as App
import Part

HERE = os.environ.get("TK_FC_DIR") or os.path.dirname(os.path.abspath(__file__))
CQ = os.path.join(HERE, "..", "exports")
FC = os.path.join(HERE, "exports")
names = json.load(open(os.path.join(FC, "fc_stats.json"))).keys()
res = {"parts": {}, "interference": []}
fc = {}
for n in names:
    a, b = Part.read(os.path.join(CQ, f"{n}.step")), Part.read(os.path.join(FC, f"{n}.step"))
    fc[n] = b
    ba, bb = a.BoundBox, b.BoundBox
    da = [ba.XMin, ba.YMin, ba.ZMin, ba.XMax, ba.YMax, ba.ZMax]
    db = [bb.XMin, bb.YMin, bb.ZMin, bb.XMax, bb.YMax, bb.ZMax]
    only_cq = a.cut(b).Volume
    only_fc = b.cut(a).Volume
    res["parts"][n] = dict(vol_cq=a.Volume, vol_fc=b.Volume, dvol_pct=100 * (b.Volume - a.Volume) / a.Volume,
                           bbox_cq=da, bbox_fc=db, bbox_max_dev=max(abs(x - y) for x, y in zip(da, db)),
                           only_in_cq=only_cq, only_in_fc=only_fc,
                           symdiff_pct=100 * (only_cq + only_fc) / a.Volume, valid_fc=b.isValid())
FITS = [("top_shell", "bottom_tray"), ("hatch_cover", "bottom_tray"), ("ballast", "bottom_tray"),
        ("feet", "bottom_tray"), ("feet", "hatch_cover"), ("knob_sleeve", "knob"), ("button_cap", "top_shell"),
        ("light_pipe", "top_shell"), ("knob", "top_shell")]
fit = lambda a, b: any((x in a and y in b) or (x in b and y in a) for x, y in FITS)
for (a, sa), (b, sb) in itertools.combinations(fc.items(), 2):
    if sa.BoundBox.intersect(sb.BoundBox):
        v = sa.common(sb).Volume
        d = 0.0 if v > 1e-4 else sa.distToShape(sb)[0]
        st = "CLASH" if v > 1e-3 else ("TIGHT" if d < 0.3 - 1e-6 and not fit(a, b) else "ok")
        res["interference"].append(dict(a=a, b=b, overlap=v, dist=d, status=st))
ko = Part.read(os.path.join(CQ, "board_keepout.step"))
solids = ko.Solids
for n, s in fc.items():
    v = sum(s.common(k).Volume for k in solids if s.BoundBox.intersect(k.BoundBox))
    res["interference"].append(dict(a=n, b="board keep-out (all solids)", overlap=v, dist=None,
                                    status="CLASH" if v > 1e-3 else "ok"))
json.dump(res, open(os.path.join(FC, "validation.json"), "w"), indent=1)
for n, r in res["parts"].items():
    print(n, round(r["dvol_pct"], 4), round(r["bbox_max_dev"], 4), round(r["symdiff_pct"], 4))
print("interference bad:", [r for r in res["interference"] if r["status"] != "ok"])
