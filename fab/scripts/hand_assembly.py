#!/usr/bin/env python3
"""Build hand_assembly_bom.csv: Module_* fields from the schematic plus fab/hand_assembly.csv.
These parts are NOT in the JLC PCBA BOM."""
import csv, re, sys, pathlib
root, out = map(pathlib.Path, sys.argv[1:3])
rows = []
for sch in sorted((root / "hardware/schematic").glob("*.kicad_sch")):
    t = sch.read_text()
    for blk in re.split(r"\(symbol \(lib_id", t)[1:]:
        f = dict(re.findall(r'\(property "([^"]+)" "([^"]*)"', blk))
        if f.get("Module_LCSC") or f.get("Module_MPN"):
            rows.append({"Item": "module", "Designator": f.get("Reference", "?") + "-module", "Qty": "1",
                         "Description": f"Module soldered onto {f.get('Reference')} ({f.get('Value','')})",
                         "MPN": f.get("Module_MPN", ""), "LCSC Part #": f.get("Module_LCSC", ""), "Step": "2",
                         "Notes": f"from {sch.name} Module_* fields"})
src = root / "fab/hand_assembly.csv"
if src.exists(): rows += list(csv.DictReader(src.open()))
cols = ["Item", "Designator", "Qty", "Description", "MPN", "LCSC Part #", "Step", "Notes"]
with out.open("w", newline="") as o:
    w = csv.DictWriter(o, cols); w.writeheader(); w.writerows(rows)
print(f"hand-assembly lines {len(rows)}")
