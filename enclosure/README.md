# enclosure/

Enclosure and industrial design for TokenKey RT. Everything enclosure-related (research, CAD, print profiles, drawings) lives here.

| Path | Contents |
|---|---|
| [research.md](research.md) | User research with cited sources, the board facts that drive the enclosure, the OLED window, standoff and USB-C analysis, three design directions, PM decisions and open items |
| [cad/](cad/README.md) | **Direction A puck**, parametric CadQuery model:<br>• `params.py` holds every dimension<br>• `build.py` / `Makefile` regenerate everything<br>• board keep-out model and interference checks |
| [freecad/](freecad/README.md) | **FreeCAD 1.0 port** (#63): `puck.FCStd` (Params/Points/Plate spreadsheets + one Part per part), `assembly.FCStd` with the board keep-out, STEP/STL in `freecad/exports/`, and `VALIDATION.md` against the CadQuery reference |
| [PRINTING.md](PRINTING.md) | **v0.2 print package** (#72): material, orientation, settings, tolerances and coupon, post-processing, assembly order, fit-print checklist (incl. #55) |
| [BOM.md](BOM.md) | Mechanical BOM with example part numbers; **not ordered, gated on PoC G1–G5** |
| `exports/print/` | Print-ready, pre-oriented STLs per printed part + `tolerance_coupon.stl` (`cad/print_export.py`, `make print`) |
| `exports/` | Generated outputs:<br>• STEP per part, `assembly.step` and `board_keepout.step`<br>• STL per part<br>• `interference_report.md` and `summary.json` |
| `renders/` | Generated PNGs: isometric, exploded, OLED/USB-C section, bottom and rear |
| `tools/board_extract.py` | Dumps outline, holes and footprints (position, courtyard, pads, 3D model refs) from the `.kicad_pcb` with the KiCad 9 pcbnew Python API |
| `tools/oled_geometry.py` | Maps the HS96L03W2C03 datasheet offsets (origin at J2 pin 1) onto board coordinates for a given J2 y, and gives window, hole, USB-C clearance and height tables |

## Source of truth
**The CadQuery model in `cad/` is authoritative.** The FreeCAD documents are generated from `cad/params.py` and checked against the CadQuery exports. Volume, bounding box and symmetric-difference volume agree to < 0.001 %; see `freecad/VALIDATION.md`. Edit `params.py`, rebuild CadQuery, then regenerate FreeCAD. Only switch the authority to FreeCAD once the PM signs that off.

## Board reference used
- **Current:** **main `e2e5ff9`** (PR #49 merged), re-extracted 2026-10-19 into `cad/board_ref.json`. J2, L2 and the OLED outline are identical to Layout's `eb4495a`. Relative to the older main `6fb72fa`:
  - J2 at **y 5.0** (PM final; module 1.24 mm and FPC bend 1.44 mm clear of the USB-C body);
  - L2 is now **TDK VLS3015CX (1.5 mm)** on the board (verified);
  - OLED drawings redrawn, including the back-side block band.
- **Earlier references:** `cfc9bc3` (PR #23 head, J2 at y 6.3) and `6fb72fa` (main: PR #23 merged at `8143f18`, PR #25 at `2e09fee`).
- **OLED stack (PM final):** the module is soldered directly onto a 3.0 mm plastic-body header, with no socket or shim. The **OLED top is 5.65 mm** above the PCB top (3.0 + 2.65). Both values are parameters.
- **Encoder:** EC11E18244A5, 20 mm shaft from the body top, 36 detents. Body 4.5 mm, no bushing; the shaft tip is 24.5 mm above the PCB (#54).
- **When to re-run:** after any layout change that moves J1, J2, SW1–SW4, J3, D1 or H1–H4:
  1. `tools/board_extract.py`
  2. `cad/make_board_ref.py`
  3. `cad/build.py`

  Then update research.md.

## Status
Research done; Direction A approved; prototype CAD in `cad/` (issue #42; #52 FPC and #54 EC11 follow-ups). No printing or purchases until the PoC spend gate (G1–G5 in `docs/decisions.md`) is passed.


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
