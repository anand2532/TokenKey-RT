# enclosure/freecad: FreeCAD 1.0 port of the Direction A puck (#63)

**Status: validated mirror. The CadQuery model in [`../cad/`](../cad/README.md) is still authoritative.** These documents are generated from `cad/params.py` and checked against the CadQuery STEP exports by [`VALIDATION.md`](VALIDATION.md): all parts agree to < 0.001 % volume, with identical bounding boxes, and 0 CLASH/TIGHT. FreeCAD becomes the source of truth only when the PM signs that off. Until then, change `params.py` and regenerate both models.

## Files
| File | What it is |
|---|---|
| `puck.FCStd` | Sheets `Params` (every params.py scalar, aliased by its name; derived values are live formulas, marked `derived` in column C), `Points` (board-derived XY: screw holes, module holes, window centre, encoder, buttons, LED, BOOT, hatch, plate pins, feet) and `Plate` (steel-plate outline rings). Plus one `Part::Feature` per part: `top_shell`, `bottom_tray` (foot pockets + plate pins), `hatch_cover` (NE foot pocket), `knob`, `knob_sleeve`, `button_cap_btn1/2`, `light_pipe`, `ballast` (steel plate), `feet` |
| `assembly.FCStd` | `App::Part` with links to every part in `puck.FCStd`, plus `board_keepout_ref` (the CadQuery board + component keep-out, reference only) |
| `exports/<part>.step`, `.stl` | per-part exports from FreeCAD (STL linear deflection 0.02 mm) |
| `exports/fc_stats.json`, `exports/validation.json` | raw numbers behind VALIDATION.md |
| `fc_parts.py` | the modelling recipe: a one-to-one port of `cad/parts.py` onto the Part API (same functions, same boolean order). It reads every number from the sheets |
| `build_fc.py` | headless driver: `params.json` → sheets → parts → `.FCStd`, STEP and STL |
| `export_params.py` | runs in the CadQuery venv: `cad/params.py` + board data + `plate.py` outline → `params.json` |
| `validate_fc.py`, `write_validation.py` | comparison and interference check → `VALIDATION.md` |
| `rebuild.FCMacro` | GUI macro: regenerate the parts of the open `puck.FCStd` from its sheets |

## Regenerate
```
cd enclosure/cad && ../../../cqenv/bin/python build.py            # 1. CadQuery reference (authoritative)
cd ../freecad && ../../../cqenv/bin/python export_params.py       # 2. params.json
freecadcmd -c "exec(open('build_fc.py').read())"                  # 3. FCStd + exports (or via the FreeCAD MCP execute_code_headless)
freecadcmd -c "exec(open('validate_fc.py').read())" && python3 write_validation.py   # 4. VALIDATION.md
```
(Use your own venv path for the CadQuery python; `make freecad` in `cad/` runs steps 2–4.)

## Editing in FreeCAD
1. Open `puck.FCStd` and change a **base** value in `Params` column B, for example `WALL`, `KNOB_H` or `FOOT_D`. The derived rows (`OUT_W`, `LID_TOP`, …) follow automatically.
2. Run `rebuild.FCMacro`. Each part is rebuilt from the sheets.

Notes:
- **Board-derived points** (`Points`, `Plate`) come from `board_ref.json` and `plate.py`. To change them, re-run `export_params.py`; don't edit them by hand.
- **Not live features.** The parts are rebuilt by the macro; they are not a live PartDesign feature tree. This keeps the recipe identical to CadQuery for validation. A PartDesign/Sketcher re-model is the next step once FreeCAD becomes authoritative.
- **Hidden parts in the GUI.** Documents saved headless have no GUI view data, so the parts can open hidden. Select them and press Space, or run `rebuild.FCMacro`, which sets colours.


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
