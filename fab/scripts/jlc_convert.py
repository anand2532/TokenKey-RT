#!/usr/bin/env python3
"""Convert kicad-cli pos/BOM CSVs into JLC CPL + BOM; flag missing LCSC numbers."""
import csv, sys, pathlib
r, p = map(pathlib.Path, sys.argv[1:3])
rows = []
for side, f in (("Top", "pos-top.csv"), ("Bottom", "pos-bottom.csv")):
    fp = r / f
    if fp.exists():
        for x in csv.DictReader(fp.open()):
            rows.append([x["Ref"], f'{float(x["PosX"]):.4f}mm', f'{float(x["PosY"]):.4f}mm', side, f'{float(x["Rot"]):g}'])
with (p / "TokenKey-RT_CPL_jlc.csv").open("w", newline="") as o:
    w = csv.writer(o); w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"]); w.writerows(rows)
missing = []; n = 0
with (r / "bom-raw.csv").open() as i, (p / "TokenKey-RT_BOM_jlc.csv").open("w", newline="") as o:
    w = csv.writer(o); w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #"])
    for x in csv.DictReader(i):
        n += 1; fpn = x["Footprint"].split(":")[-1]
        w.writerow([x["Comment"], x["Designator"], fpn, x["LCSC Part #"]])
        if not x["LCSC Part #"].strip(): missing.append(x)
with (r / "missing-lcsc.md").open("w") as o:
    o.write(f"# Missing LCSC numbers: {len(missing)} of {n} BOM lines\n\n")
    for x in missing: o.write(f'- {x["Designator"]}: {x["Comment"]} ({x["Footprint"]})\n')
print(f"CPL rows {len(rows)}, BOM lines {n}, missing LCSC {len(missing)}")
