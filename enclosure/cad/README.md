# enclosure/cad: Direction A "puck", parametric CadQuery model

Issue #42. Board reference: Layout #31 commit `eb4495a` (`board_ref.json`; **not on main yet**). Prototype for FDM/SLA, modelled **without draft**. For injection moulding:
- add **1–2° draft** on every face parallel to the pull (Z);
- use **3°** on textured faces (≥ 5° for medium/heavy texture);
- core out the bosses, and keep ribs at 40–60 % of the wall.

## Build
```
python3 -m venv venv && venv/bin/pip install cadquery trimesh matplotlib shapely networkx scipy rtree
venv/bin/python build.py          # or: make PY=venv/bin/python
make variant-a                    # cheap variant (a): 15 mm shaft + 7 mm knob, check only (not exported)
TK_PROCESS=SLA TK_KNOB_INSERT=setscrew TK_HEADER=3.0 TK_MODULE_T=2.65 TK_SHAFT=20 TK_KNOB_H=14 venv/bin/python build.py
```

`build.py` writes:
- `../exports/<part>.step` and `<part>.stl`;
- `../exports/assembly.step` (parts plus the reference board and keep-outs);
- `../exports/board_keepout.step`;
- `../exports/interference_report.md` and `../exports/summary.json`;
- `../renders/*.png`: VTK offscreen, with a matplotlib fallback.

A full run takes about 40 s.

To refresh the board data:
```
python3 ../tools/board_extract.py TokenKey-RT.kicad_pcb raw.json
python3 make_board_ref.py raw.json <sha> > board_ref.json
```

## Frame
- **X** = KiCad x (east).
- **Y** = 40 − KiCad y. Y = 0 is the board's south edge, which is the **rear**, with USB-C.
- **Z** = 0 at the main-PCB top.
- The user faces the north edge. Seen by the user, the knob is on the left, the buttons are behind it, the LED is at the front, and the service hatch is under the front.

## Parts
| Part | What it does |
|---|---|
| `top_shell` | 1.5 mm lid, plus 2.0 mm walls (FDM) or 1.6 mm (SLA). It carries:<br>• the OLED window, 22.74 × 11.86 at J2 pin 1 + (3.81, 10.36), chamfered 45° through the lid to 25.74 × 14.86<br>• four locating posts (Ø2.2 pin, Ø4.0 shoulder stopping 0.15 mm above the module PCB) at the module holes; they locate only, since the header sets the height<br>• four M2 heat-set-insert posts landing on the PCB at H1–H4<br>• an EC11 body relief (0.7 mm skin) and the Ø11 × 3.5 radial-bearing collar<br>• the button and light-pipe holes<br>• the USB-C pocket and a rib 0.3 mm above J1<br>• a 1.0 mm rabbet for the tray lip |
| `bottom_tray` | 1.6 mm floor with 2.5 mm under the board. It carries:<br>• four Ø4.6 M2 bosses with Ø4.0 × 2.2 counterbores (M2 × 8 DIN 912)<br>• an 18.3 × 13 service hatch (TC2030 J3 and TP1–TP5) with a 0.5 mm cover recess<br>• the Ø1.8 BOOT pinhole with a guide tube ending 0.3 mm short of the SW1 plunger<br>• the ballast pocket<br>• the grip-cord groove (1.6 × 0.8 for a Ø1.5 silicone cord)<br>• the USB-C pocket's lower half |
| `hatch_cover` | 0.8 mm flange plus a 0.8 mm plug, with a thumbnail notch. Friction fit; add a snap or screw after the fit check |
| `knob` | Ø17 × 14, 30 flutes. Its bottom pocket rides radially on the collar (0.15 mm clearance). 2.0 mm axial push clearance (1.5 travel + 0.5). 7.0 mm shaft engagement. Insert options: `sleeve` (Ø8 bore for a brass D-sleeve), `setscrew` (D-bore + radial M3 heat-set insert) or `none` |
| `knob_sleeve` | Brass D-sleeve, OD 8 / Ø6 D (4.5 across the flat), 7 mm long. Exported for `KNOB_INSERT=sleeve` |
| `button_cap_btn1/2` | SLA cap, Ø4.6 head 0.8 mm proud. Travel: **0.30 free + 0.15 B3U stroke + 0.05 → hard stop at 0.50 mm**, where two Ø1.2 feet land on the PCB. Two 0.35 mm cantilever arms bear on the lid underside to hold the cap up and retain it |
| `light_pipe` | Ø2.0 × 6.5 mm clear PC/PMMA, 0.2 mm above D1, flush with the lid top, Ø3 × 0.4 flange |
| `ballast` | 18 × 18 × 1.2 mm plate (steel; tungsten option) under the BGA area |

## Key results (default build)
| Item | Value |
|---|---|
| Overall body | **55.0 × 45.0 × 13.2 mm** (desk → lid top), 3.5 mm corner radius |
| Stack (z, PCB top = 0) | desk −5.7, floor top −4.1, PCB bottom −1.6, OLED top 5.65, lid underside 6.0, lid top 7.5 |
| Knob, default (b): 20 mm shaft, 14 mm knob | Bottom 9.5 / top **23.5 mm above the PCB = 29.2 mm above the desk** (29.9 with the grip cord); engagement 7.0 mm |
| Knob, variant (a): 15 mm shaft, 7 mm knob | Top 16.5 mm above the PCB = 22.2 mm above the desk; **engagement only 2.0 mm** (< 6), so flag only, not exported |
| Button cap / light pipe | Cap 6.4 mm from the plunger nub to the cap top; pipe 6.5 mm |
| USB-C | Overmold face stops 1.1 mm short of the receptacle face (check with real cables) |
| Mass (FDM PETG, steel ballast) | **≈ 30 g**, against the 120 g design parameter (see research.md, Direction A) |
| Interference | 310 pairs within 3 mm checked: **0 part clashes, 0 tight**. Designed fits are listed in the report |
| **FPC bend vs USB-C** | The conservative bend (1.5 mm out, 14.5 wide, down to z 2.0) is **−0.26 mm in plan, so CLASH**. Module PCB edge +1.24 mm. A bend protrusion ≤ 0.94 mm would pass |

## Parameters (`params.py`)
| Name | Default | Notes |
|---|---|---|
| `HEADER_H` | 3.0 | module-PCB underside above the PCB (env `TK_HEADER`) |
| `OLED_MODULE_T` | 2.65 | so OLED top = 5.65 (env `TK_MODULE_T`) |
| `LID_GLASS_CLR` | 0.35 | lid underside above the glass (PM 0.3–0.4) |
| `OLED_BACK_FEATURE`, `OLED_BACK_BAND` | 1.0, y +9.3…+12.3 | back-side block, modelled over the full module width |
| `FPC_BEND_OUT`, `FPC_BEND_W` | 1.5, 14.5 | conservative bend allowance at the module's south edge |
| `WALL` | 2.0 FDM / 1.6 SLA | env `TK_PROCESS` |
| `LID_T`, `FLOOR_T` | 1.5, 1.6 | |
| `BOARD_CLR`, `UNDER_BOARD`, `THT_TAIL` | 0.5, 2.5, 1.5 | |
| `CORNER_R`, `INNER_R` | 3.5, 1.5 | |
| `SHAFT_L` | 20 | 15 = variant (a) (env `TK_SHAFT`) |
| `ENC_BODY`, `ENC_BUSHING_TOP` | 12.4 × 13.4 × 6.5, 7.0 | Alps values; **verify on a part** |
| `COLLAR_OD`, `COLLAR_H` | 11.0, 3.5 | radial bearing collar |
| `KNOB_D`, `KNOB_H` | 17, 14 | 16–18 / 12–15 default band, 15–25 allowed (env `TK_KNOB_D`, `TK_KNOB_H`) |
| `KNOB_INSERT` | sleeve | sleeve / setscrew / none (env `TK_KNOB_INSERT`) |
| `KNOB_PUSH_CLR`, `KNOB_BEARING_CLR`, `MIN_ENGAGEMENT` | 0.5, 0.15, 6.0 | |
| `CAP_FREE`, `B3U_STROKE`, `CAP_STOP_EXTRA` | 0.30, 0.15, 0.05 | defined travel 0.50 to the hard stop |
| `CAP_ARM_T`, `CAP_ARM_L` | 0.35, 2.5 | return/retention cantilevers |
| `USB_OUTER`, `USB_INNER`, `USB_SKIN`, `USB_Z` | 13.5 × 8.0, 9.5 × 3.8, 0.6, 1.63 | |
| `HATCH`, `HATCH_CENTRE_K` | 18.3 × 13.0, (34.65, 7.5) KiCad | |
| `BOOT_HOLE_D`, `BOOT_TUBE_GAP` | 1.8, 0.3 | |
| `BALLAST_K`, `BALLAST_T`, `BALLAST_RHO` | x 6–24, y 10–28, 1.2, 7.85 | |
| `GRIP_INSET`, `GRIP_W`, `GRIP_D` | 1.2, 1.6, 0.8 | Ø1.5 silicone cord |
| `MASS_TARGET` | 120 g | design parameter only |
| `CLASH_MIN` | 0.3 | clearance flag threshold |

## Assumptions to verify on parts
- EC11E body height (6.5) and bushing top (7.0), and whether L1 = 20 is measured from the PCB.
- J1 shell height 3.26 and its face flush with the board edge.
- B3U-1000P height 1.6 and stroke 0.15.
- Component heights are the courtyard box × the typical maximum height (`board_model.HEIGHTS`).
