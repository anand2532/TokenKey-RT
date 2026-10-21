# TokenKey RT enclosure v0.2: mechanical BOM (#72)

> **NOT ORDERED. Gated on the PoC spend gate G1–G5** (`docs/decisions.md`). No prices. Part numbers are **examples** to check against the datasheet at order time; equivalent parts are fine if they match the dimensions.

| # | Item | Qty | Spec / dims (from CAD) | Example part (manufacturer / P/N) | Notes |
|---|---|---|---|---|---|
| 1 | Socket head cap screw | 4 | **M2 × 8**, ISO 4762 / DIN 912, A2 stainless, head Ø3.8 × 2.0 | Bossard BN 610 M2×8 (DIN 912), or Würth 0835 2 8 / any DIN 912 M2×8 A2 | length from the stack, see below |
| 2 | Heat-set threaded insert | 4 | **M2, L 3.0, OD ≈ 3.6**, for the Ø3.2 hole | ruthex RX-M2x3.0; CNC Kitchen M2 "standard" (3.0 mm) | **Chosen over self-tapping.** The CAD posts already carry Ø3.2 × 5.0 holes. Survives repeated opening (service hatch / debug use) |
| 3 | Adhesive feet | 5 | **Ø8.0 × 2.2 mm** silicone, domed, adhesive back | **Default:** clear silicone bumper (ETOL ARF2003 class). **Alternate:** 3M Bumpon SJ5302 (PU, Ø7.9 × 2.2) | `FOOT_D/H` params; pocket Ø8.4 × 1.0 fits both; 10 × 3 mm via `TK_FOOT=10x3` |
| 4 | Steel ballast plate | 1 | **1.2 mm** cold-rolled steel DC01 (or stainless 1.4301), laser-cut from `exports/ballast_plate.dxf`: 49.8 × 39.8 envelope, 1247 mm², 3 cut-outs, 2 × Ø2.4 holes, **≈ 11.7 g** | any laser-cut sheet service | deburr; zinc-plate or prime DC01 |
| 5 | Plate adhesive | 1 piece | thin transfer tape, ≤ 0.06 mm, about 40 × 30 mm | 3M 467MP (200MP, 0.058 mm) | keep it thin. The CAD has 0.35 mm from the plate top to the 0603 parts, and thick VHB would eat that |
| 6 | Brass knob sleeve | 1 | **OD 8.0 × 7.0 long, bore Ø6.05 D-profile, 4.5 mm across the flat** (flat aligned to the knob bore) | custom turned + broached/EDM brass CuZn39Pb3 (no stock part) | Alternative without machining: `TK_KNOB_INSERT=setscrew` with an M3 heat-set insert (ruthex RX-M3x5.7) + ISO 4029 M3 × 4 cup-point set screw |
| 7 | Light pipe (if not printed) | 1 | Ø2.0 clear PMMA/PC rod, **6.5 mm** long, polished ends | generic Ø2 mm PMMA optical rod, cut and polished; or a Ø2 rigid panel light pipe of matching length | the printed SLA pipe has the Ø3 × 0.4 flange; a plain rod needs a drop of CA in the Ø2.05 hole |
| 8 | Smoked window insert (NOT in v1, future option) | 1 | 1.0 mm smoked/grey PMMA, about 24.8 × 13.9 mm | cast PMMA grey smoked sheet, laser-cut | **Not in the v0.2 CAD.** It needs a 24.8 × 13.9 × 1.0 pocket in the lid (research.md, Direction A). The open chamfered window is the v0.2 baseline |
| 9 | Printing material | – | PETG (shells, tray, hatch, knob), SLA standard/tough resin (caps), SLA clear (pipe) | any | see PRINTING.md |

**M2 screw length.** Heights are in the CAD frame, with the PCB top at z = 0:
- **Head:** it sits in the Ø4.0 × 2.2 counterbore. The head top is at desk + 2.2 = −3.5.
- **Clamp stack:** tray boss −3.5 → −1.6 (1.9 mm), then the PCB −1.6 → 0 (1.6 mm). That is 3.5 mm from under the head to the insert face.
- **Thread:** the insert runs from 0 to 3.0 (full 3.0 mm thread engagement). The post hole ends at 5.0.
- **M2 × 8:** the tip sits at +4.5, so the screw engages the whole insert, runs 1.5 mm past it, and stops 0.5 mm short of the hole bottom.
- **Other lengths:** M2 × 6 would only give 2.5 mm of thread. M2 × 10 would bottom out.


## v1 decisions (PM, #72) — supersede anything above that conflicts

- **Source of truth: FreeCAD is authoritative** (`freecad/puck.FCStd`, Params sheet). Edit the
  sheet, then `freecadcmd -c "exec(open('export_fc.py').read())"` and `print_fc.py` in `freecad/`.
  CadQuery (`cad/`) is a **reference only**: keep its `params.py` mirrored, rerun `validate_fc.py`
  to check the two agree (VALIDATION.md: all parts within tolerance, 0 clashes).
- **Print STLs** in `exports/print/` are written by `freecad/print_fc.py` from the FreeCAD model
  (tolerance coupon still from `cad/print_export.py`). Checked against the previous CadQuery print
  STLs: volumes within 0.01 %, extents within 0.005 mm, all watertight.
- **Feet: silicone by default** — Ø8.0 × 2.2 mm clear silicone bumpers (e.g. ETOL ARF2003 class),
  ×5. **Alternate: 3M Bumpon SJ5302** (polyurethane, Ø7.9 × 2.2). Pocket stays Ø8.4 × 1.0 so both fit.
- **Flick-spin:** silicone feet resist the puck walking when the knob is flicked hard; a fast flick
  can still rotate a 40 g puck on a slick desk. Expected, not a defect; note in the fit checklist.
- **No window pocket in v1:** the lid OLED opening is a plain chamfered through-window. The smoked
  acrylic insert is a possible later revision only, not part of v1 CAD or BOM.
