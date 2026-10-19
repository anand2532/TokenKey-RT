# enclosure/

Enclosure and industrial design for TokenKey RT. Everything enclosure-related (research, CAD, print profiles, drawings) lives here.

| Path | Contents |
|---|---|
| [research.md](research.md) | User research with cited sources, the board facts that drive the enclosure, the OLED window, standoff and USB-C analysis, three design directions, PM decisions and open items |
| [cad/](cad/README.md) | **Direction A puck**, parametric CadQuery model:<br>• `params.py` holds every dimension<br>• `build.py` / `Makefile` regenerate everything<br>• board keep-out model and interference checks |
| `exports/` | Generated outputs:<br>• STEP per part, `assembly.step` and `board_keepout.step`<br>• STL per part<br>• `interference_report.md` and `summary.json` |
| `renders/` | Generated PNGs: isometric, exploded, OLED/USB-C section, bottom and rear |
| `tools/board_extract.py` | Dumps outline, holes and footprints (position, courtyard, pads, 3D model refs) from the `.kicad_pcb` with the KiCad 9 pcbnew Python API |
| `tools/oled_geometry.py` | Maps the HS96L03W2C03 datasheet offsets (origin at J2 pin 1) onto board coordinates for a given J2 y, and gives window, hole, USB-C clearance and height tables |

## Board reference used
- **Current:** Layout's #31 commit **`eb4495a`** (branch `issue-31-pcb-l2`), re-extracted 2026-10-19 into `cad/board_ref.json`. Changes from main `6fb72fa`:
  - J2 at **y 5.0** (module 1.24 mm clear of the USB-C body);
  - L2 is now **TDK VLS3015CX (1.5 mm)** on the board (verified);
  - OLED drawings redrawn, including the back-side block band.
- **`eb4495a` is not on `main` yet.** Main is `995be50`, and its last board change is `6fb72fa` with J2 at y 5.5. The CAD is designed to `eb4495a`.
- **Earlier references:** `cfc9bc3` (PR #23 head, J2 at y 6.3) and `6fb72fa` (main: PR #23 merged at `8143f18`, PR #25 at `2e09fee`).
- **OLED stack (PM final):** the module is soldered directly onto a 3.0 mm plastic-body header, with no socket or shim. The **OLED top is 5.65 mm** above the PCB top (3.0 + 2.65). Both values are parameters.
- **Encoder:** EC11E18244A5, 20 mm shaft, 36 detents. The PM kept it; the 15 mm swap is dropped.
- **When to re-run:** after any layout change that moves J1, J2, SW1–SW4, J3, D1 or H1–H4:
  1. `tools/board_extract.py`
  2. `cad/make_board_ref.py`
  3. `cad/build.py`

  Then update research.md.

## Status
Research done; Direction A approved; prototype CAD in `cad/` (issue #42). No printing or purchases until the PoC spend gate (G1–G5 in `docs/decisions.md`) is passed.
