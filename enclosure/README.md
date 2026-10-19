# enclosure/

Enclosure and industrial design for TokenKey RT. Everything enclosure-related (research, CAD, print profiles, drawings) lives here.

| Path | Contents |
|---|---|
| [research.md](research.md) | User research with cited sources, the board facts that drive the enclosure, the OLED window, standoff and USB-C analysis, three design directions, the recommendation and the open decisions |
| `tools/board_extract.py` | Dumps outline, holes and footprints (position, courtyard, pads, 3D model refs) from the `.kicad_pcb` with the KiCad 9 pcbnew Python API |
| `tools/oled_geometry.py` | Maps the HS96L03W2C03 datasheet offsets (origin at J2 pin 1) onto board coordinates for a given J2 y, and gives window, hole, USB-C clearance and height tables |

## Board reference used
- **Current:** `main` @ **`6fb72fa`**, re-checked 2026-10-19. That includes:
  - PR #23 placement, merged at `8143f18` (J2 at y 5.5, the real OLED outline on the Fab/User layers, U4 at (3.05, 25));
  - PR #25, merged at `2e09fee` (L2 changed to VLS3015CX 1.5 mm in the schematic, and the HS96L03W2C03 mechanicals in `docs/decisions.md`).
- **First draft:** PR #23 head `cfc9bc3` (J2 at y 6.3).
- **OLED header:** 3.0 mm (TokenKey PM), giving a design OLED top of 6.6 mm. It is a parameter in `tools/oled_geometry.py`.
- **Known board-vs-schematic gap:** the board's L2 footprint is still the SWPA4020 (2.0 mm) until it is synced from the schematic.
- **When to re-run:** run both tools again after any layout PR that moves J1, J2, SW1–SW4, J3, D1 or H1–H4, and update research.md.

## Status
Research and direction only. No CAD, printing or purchases until the PoC spend gate (G1–G5 in `docs/decisions.md`) is passed.
