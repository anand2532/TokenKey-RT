# enclosure/

Enclosure and industrial design for TokenKey RT. Everything enclosure-related (research, CAD, print profiles, drawings) lives here.

| Path | Contents |
|---|---|
| [research.md](research.md) | User research with cited sources, the board facts that drive the enclosure, the OLED window, standoff and USB-C analysis, three design directions, the recommendation and the open decisions |
| `tools/board_extract.py` | Dumps outline, holes and footprints (position, courtyard, pads, 3D model refs) from the `.kicad_pcb` with the KiCad 9 pcbnew Python API |
| `tools/oled_geometry.py` | Maps the HS96L03W2C03 datasheet offsets (origin at J2 pin 1) onto board coordinates for a given J2 y, and gives window, hole, USB-C clearance and height tables |

## Board reference used
- **PCB:** `hardware/schematic/TokenKey-RT.kicad_pcb` at **`cfc9bc3`**. That is the head of PR #23 (`issue-22-placement`), still unmerged; `main` has no board file yet.
- **OLED mechanicals:** `docs/decisions.md` at **`f2465ab`**, the head of PR #25 (`issue-24-l2-inductor`), still unmerged.
- **Uncommitted layout work seen on 2026-10-19:** J2 moved from y 6.3 to y 5.5. research.md covers both positions.
- **When to re-run:** run both tools again once PR #23 and PR #25 (or later layout PRs) merge, and update research.md.

## Status
Research and direction only. No CAD, printing or purchases until the PoC spend gate (G1–G5 in `docs/decisions.md`) is passed.
