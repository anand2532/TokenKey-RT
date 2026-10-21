# hardware/schematic

The whole KiCad project for the TokenKey RT board lives here: `TokenKey-RT.kicad_pro`, `TokenKey-RT.kicad_sch` (plus sub-sheets), the 4-layer `TokenKey-RT.kicad_pcb` and `TokenKey-RT.kicad_dru`. KiCad only links the `.kicad_sch` and `.kicad_pcb` that sit next to the `.kicad_pro`, so keep them together in this folder.

## Deprecated generators (issue #26)

`tools/gen.py` and `tools/gen_pinmap.py` are kept for history only and refuse to run. The schematic is the source of truth and is edited directly in KiCad; re-running `gen.py` would overwrite hand edits such as L2 (#24) and the J2 header (#44). `docs/pin-map.md` is a frozen snapshot: update it by hand with any pin-mux change. `tools/rt1062_10x10_balls.json` stays as ball-function reference data.
