# FreeCAD port: validation against the CadQuery reference

- Reference: `enclosure/exports/<part>.step` from `cad/build.py` (CadQuery, authoritative), board `e2e5ff9`, process FDM.
- Port: `enclosure/freecad/exports/<part>.step` from `build_fc.py` (FreeCAD 1.0, Part workbench), driven by the `Params`/`Points`/`Plate` sheets of `puck.FCStd`.
- Method (`validate_fc.py`, run in `freecadcmd`): both STEPs are loaded, then the script compares:
  - volume;
  - axis-aligned bounding box;
  - the **symmetric difference**: volume that exists in only one of the two (`A.cut(B) + B.cut(A)`). A small number here means the shapes coincide, not just that the totals match.
- Pass criteria: |ΔV| < 1 %, bbox within 0.01 mm, valid solids.

## Per-part comparison

| Part | V CadQuery (mm³) | V FreeCAD (mm³) | ΔV | max bbox dev (mm) | only-in-CQ + only-in-FC (mm³) | sym. diff | valid | result |
|---|---|---|---|---|---|---|---|---|
| top_shell | 6165.41 | 6165.41 | -0.0000 % | 0.0000 | 0.000 | 0.0000 % | True | pass |
| bottom_tray | 4417.03 | 4417.03 | -0.0000 % | 0.0000 | 0.000 | 0.0000 % | True | pass |
| hatch_cover | 339.02 | 339.02 | +0.0000 % | 0.0000 | 0.000 | 0.0000 % | True | pass |
| knob | 2591.58 | 2591.58 | -0.0000 % | 0.0000 | 0.000 | 0.0000 % | True | pass |
| button_cap_btn1 | 97.94 | 97.94 | +0.0000 % | 0.0000 | 0.000 | 0.0000 % | True | pass |
| button_cap_btn2 | 97.94 | 97.94 | +0.0000 % | 0.0000 | 0.000 | 0.0000 % | True | pass |
| light_pipe | 21.99 | 21.99 | +0.0000 % | 0.0000 | 0.000 | 0.0000 % | True | pass |
| ballast | 1496.68 | 1496.69 | +0.0001 % | 0.0000 | 0.004 | 0.0003 % | True | pass |
| feet | 536.43 | 536.43 | -0.0000 % | 0.0000 | 0.000 | 0.0000 % | True | pass |
| knob_sleeve | 163.07 | 163.07 | -0.0000 % | 0.0000 | 0.000 | 0.0000 % | True | pass |

**Result: all parts pass.** The two models share the OpenCascade kernel and the same recipe, so they agree to meshing/boolean round-off. The largest gap is the steel plate's 0.0003 % symmetric difference, from the 16k-entity polygon outline being re-triangulated. No gap needs explaining against the 1 % budget.

## Interference check in FreeCAD

This runs on the FreeCAD parts (`validate_fc.py`):
- **Part vs part:** a boolean common and a minimum distance for every pair whose bounding boxes overlap. Designed fits (lip joint, caps and light pipe in their lid holes, knob on the boss, plate/feet in the tray) are allowed to touch.
- **Part vs board keep-out:** a boolean common of each part with every solid of `exports/board_keepout.step`.

| A | B | overlap (mm³) | min dist (mm) | status |
|---|---|---|---|---|
| top_shell | bottom_tray | 0.0000 | 0.00 | ok |
| top_shell | knob | 0.0000 | 0.15 | ok |
| top_shell | button_cap_btn1 | 0.0000 | 0.00 | ok |
| top_shell | button_cap_btn2 | 0.0000 | 0.00 | ok |
| top_shell | light_pipe | 0.0000 | 0.00 | ok |
| bottom_tray | hatch_cover | 0.0000 | 0.00 | ok |
| bottom_tray | ballast | 0.0000 | 0.00 | ok |
| bottom_tray | feet | 0.0000 | 0.00 | ok |
| hatch_cover | ballast | 0.0000 | 1.36 | ok |
| hatch_cover | feet | 0.0000 | 0.00 | ok |
| knob | knob_sleeve | 0.0000 | 0.01 | ok |
| top_shell | board keep-out (all solids) | 0.0000 | - | ok |
| bottom_tray | board keep-out (all solids) | 0.0000 | - | ok |
| hatch_cover | board keep-out (all solids) | 0.0000 | - | ok |
| knob | board keep-out (all solids) | 0.0000 | - | ok |
| button_cap_btn1 | board keep-out (all solids) | 0.0000 | - | ok |
| button_cap_btn2 | board keep-out (all solids) | 0.0000 | - | ok |
| light_pipe | board keep-out (all solids) | 0.0000 | - | ok |
| ballast | board keep-out (all solids) | 0.0000 | - | ok |
| feet | board keep-out (all solids) | 0.0000 | - | ok |
| knob_sleeve | board keep-out (all solids) | 0.0000 | - | ok |

**21 checks, 0 CLASH/TIGHT.** The full clearance analysis (384 pairs, with the 0.3 mm TIGHT rule against every keep-out solid) stays in the CadQuery report, `../exports/interference_report.md`, which also reports 0 CLASH/TIGHT.

## Parametric check

These edits were made in the `Params` sheet of `puck.FCStd`, followed by `fc_parts.rebuild(doc)` (not saved):
- `WALL` 2.0 → 1.6: the `OUT_W`/`OUT_D` formulas give 54.2 × 44.2, and the top shell rebuilds to X −2.1…52.1 (tight bbox).
- `FOOT_D`/`FOOT_H` 7.9/2.2 → 10/3: the feet volume goes from 522.9 to 1157.3 mm³.
- `KNOB_H` 16.5 → 18: the knob top goes from 26.0 to 27.5.
- `HEADER_H` 3.0 → 2.5: the lid drops, and the knob guard correctly refuses a 16.5 mm knob that no longer covers the shaft. This is the same guard as in CadQuery.

_Generated 2026-10-21 by `write_validation.py`._
