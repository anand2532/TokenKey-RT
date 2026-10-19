# enclosure/cad: Direction A "puck", parametric CadQuery model

Issue #42; follow-ups #52 (FPC bend vs USB-C) and #54 (EC11E heights). Board reference: **main `e2e5ff9`** (PR #49 merged; `board_ref.json`). J2 is at y 5.0. Prototype for FDM/SLA, modelled **without draft**. For injection moulding:
- add **1–2° draft** on every face parallel to the pull (Z);
- use **3°** on textured faces (≥ 5° for medium/heavy texture);
- core out the bosses, and keep ribs at 40–60 % of the wall.

## Build
```
python3 -m venv venv && venv/bin/pip install cadquery trimesh matplotlib shapely networkx scipy rtree
venv/bin/python build.py          # or: make PY=venv/bin/python
TK_PROCESS=SLA TK_KNOB_INSERT=setscrew TK_HEADER=3.0 TK_MODULE_T=2.65 TK_KNOB_H=16.5 venv/bin/python build.py
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

## Board reference
- `board_ref.json` was regenerated from **main `e2e5ff9`** (PR #49 merged) on 2026-10-19.
- Against `eb4495a`/`b23a696`, **J2 (16.34, 5.0), L2 (TDK VLS3015CX at (9.15, 21.4), 1.5 mm) and the OLED outline graphics are unchanged**. The only J2 change is its Value text. Other changes are net names on unconnected pads, with no geometry change.
- `J2_Y` follows the board (5.0, PM final). The module, window, locating posts and header all follow J2 pin 1.

## Frame
- **X** = KiCad x (east).
- **Y** = 40 − KiCad y. Y = 0 is the board's south edge, which is the **rear**, with USB-C.
- **Z** = 0 at the main-PCB top.
- The user faces the north edge. Seen by the user, the knob is on the left, the buttons are behind it, the LED is at the front, and the service hatch is under the front.

## Parts
| Part | What it does |
|---|---|
| `top_shell` | 1.5 mm lid, plus 2.0 mm walls (FDM) or 1.6 mm (SLA). It carries:<br>• the OLED window, 22.74 × 11.86 at J2 pin 1 + (3.81, 10.36), chamfered 45° through the lid to 25.74 × 14.86<br>• four locating posts (Ø2.2 pin, Ø4.0 shoulder stopping 0.15 mm above the module PCB) at the module holes; they locate only, since the header sets the height<br>• four M2 heat-set-insert posts landing on the PCB at H1–H4<br>• the Ø11 × 5.0 bearing collar (a lid boss with a Ø7.0 shaft hole; no body relief needed)<br>• the button and light-pipe holes<br>• the USB-C pocket and a rib 0.3 mm above J1<br>• a 1.0 mm rabbet for the tray lip |
| `bottom_tray` | 1.6 mm floor with 2.5 mm under the board. It carries:<br>• four Ø4.6 M2 bosses with Ø4.0 × 2.2 counterbores (M2 × 8 DIN 912)<br>• an 18.3 × 13 service hatch (TC2030 J3 and TP1–TP5) with a 0.5 mm cover recess<br>• the Ø1.8 BOOT pinhole with a guide tube ending 0.3 mm short of the SW1 plunger<br>• the ballast pocket<br>• the grip-cord groove (1.6 × 0.8 for a Ø1.5 silicone cord)<br>• the USB-C pocket's lower half |
| `hatch_cover` | 0.8 mm flange plus a 0.8 mm plug, with a thumbnail notch. Friction fit; add a snap or screw after the fit check |
| `knob` | Ø17 × 16.5, 30 flutes. Its bottom pocket rides radially on the collar (0.15 mm clearance). 2.0 mm axial push clearance (1.5 travel + 0.5). The D-bore starts 1.0 mm above the D-flat start, so it never seats on the round section; **9.0 mm shaft engagement**. Insert options: `sleeve` (Ø8 bore for a brass D-sleeve), `setscrew` (D-bore + radial M3 heat-set insert) or `none` |
| `knob_sleeve` | Brass D-sleeve, OD 8 / Ø6 D (4.5 across the flat), 7 mm long, from the D-key start at 15.5 to 22.5 (all on the flat). Exported for `KNOB_INSERT=sleeve` |
| `button_cap_btn1/2` | SLA cap, Ø4.6 head 0.8 mm proud. Travel: **0.30 free + 0.15 B3U stroke + 0.05 → hard stop at 0.50 mm**, where two Ø1.2 feet land on the PCB. Two 0.35 mm cantilever arms bear on the lid underside to hold the cap up and retain it |
| `light_pipe` | Ø2.0 × 6.5 mm clear PC/PMMA, 0.2 mm above D1, flush with the lid top, Ø3 × 0.4 flange |
| `ballast` | 18 × 18 × 1.2 mm plate (steel; tungsten option) under the BGA area |

## Key results (default build)
| Item | Value |
|---|---|
| Overall body | **55.0 × 45.0 × 13.2 mm** (desk → lid top), 3.5 mm corner radius |
| Stack (z, PCB top = 0) | desk −5.7, floor top −4.1, PCB bottom −1.6, OLED top 5.65, lid underside 6.0, lid top 7.5 |
| EC11E18244A5 (Alps drawing No.3) | Body 4.5 mm tall, **no bushing**. Shaft Ø6, round up to 14.5 mm above the PCB, then D-flat (4.5 across) up to the **tip at 24.5 mm** (23.0 pressed; 1.5 mm push). Body to lid underside 1.5 mm, so the lid needs no relief |
| Knob, default: stock shaft, 16.5 mm knob | Bottom 9.5 / top **26.0 mm above the PCB = 31.7 mm above the desk** (32.4 with the grip cord). D-key from 15.5; **engagement 9.0 mm**. 16.5 is the minimum height that covers the stock tip (24.5 + 0.5 clearance + 1.0 skin) |
| Collar and push | Collar top 12.5, overlapping the knob skirt by 3.0 mm at rest. At full push: skirt to lid 0.5 mm, pocket ceiling to collar top 1.5 mm |
| Button cap / light pipe | Cap 6.4 mm from the plunger nub to the cap top; pipe 6.5 mm |
| USB-C | Overmold face stops 1.1 mm short of the receptacle face (check with real cables) |
| Mass (FDM PETG, steel ballast) | **≈ 30 g**, against the 120 g design parameter (see research.md, Direction A) |
| Interference | 309 pairs within 3 mm checked: **0 part clashes, 0 tight**. Designed fits are listed in the report |
| **FPC bend vs USB-C (#52)** | **Resolved.** The bend is on the module's **far edge**, which is the south side facing J1, opposite the header edge. It is modelled inside the outline (0.4 ± 0.2 mm, worst case 0.2), 14.5 wide, centred, from the glass far edge to the outline, z 4.2–5.65, with no wrap. Clearances to the J1 body: FPC **+1.44 mm in plan** (1.72 in 3D), module PCB +1.24 mm. Lid underside over the bend 0.35 mm. The bend is under solid lid, 4.0 mm south of the window edge at the lid underside (2.5 mm at the chamfered outer face), and far inside the south wall |

## Parameters (`params.py`)
| Name | Default | Notes |
|---|---|---|
| `HEADER_H` | 3.0 | module-PCB underside above the PCB (env `TK_HEADER`) |
| `OLED_MODULE_T` | 2.65 | so OLED top = 5.65 (env `TK_MODULE_T`) |
| `LID_GLASS_CLR` | 0.35 | lid underside above the glass (PM 0.3–0.4) |
| `OLED_BACK_FEATURE`, `OLED_BACK_BAND` | 1.0, y +9.3…+12.3 | back-side block, modelled over the full module width |
| `J2_Y` | 5.0 | J2 pin-row y (KiCad), read from `board_ref.json` |
| `FPC_BEND_W`, `FPC_BEND_INSET`, `FPC_BEND_TOL` | 14.5, 0.4, 0.2 | far-edge bend, inside the module outline, no wrap |
| `WALL` | 2.0 FDM / 1.6 SLA | env `TK_PROCESS` |
| `LID_T`, `FLOOR_T` | 1.5, 1.6 | |
| `BOARD_CLR`, `UNDER_BOARD`, `THT_TAIL` | 0.5, 2.5, 1.5 | |
| `CORNER_R`, `INNER_R` | 3.5, 1.5 | |
| `ENC_BODY` | 12 × 12 × 4.5 | EC11E (11.7 × 12 per drawing), no bushing |
| `SHAFT_L`, `SHAFT_TRIM` | 20 (from the body top), 0 | tip 24.5 above the PCB. `SHAFT_TRIM` stays 0: no modifications to purchased parts (env `TK_SHAFT_TRIM` for evaluation only) |
| `ENC_SHAFT_D`, `ENC_FLAT`, `ENC_FLAT_L` | 6.0, 4.5, 10.0 | D-flat from 14.5 to the tip |
| `ENC_HOLE_D` | 7.0 | lid/collar hole, 0.5 mm radial: the shaft never touches the lid |
| `COLLAR_OD`, `COLLAR_H` | 11.0, 5.0 | bearing boss on the lid, top at 12.5 |
| `KNOB_D`, `KNOB_H` | 17, 16.5 | 16.5 is the minimum for the stock shaft; the build errors if the knob can't cover the tip (env `TK_KNOB_D`, `TK_KNOB_H`) |
| `KNOB_DKEY_MARGIN`, `KNOB_TOP_SKIN` | 1.0, 1.0 | D-key start above the flat start; skin over the bore (env `TK_DKEY_MARGIN`) |
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

## Collar design (#54)
The EC11E18244A5 has no bushing, so the lid can't clamp to a threaded bushing. The bearing is a **Ø11 × 5.0 boss on the lid**, top at 12.5:
- The shaft passes through a **Ø7.0 hole with 0.5 mm radial clearance**, so the shaft never bears on the lid.
- The **knob's bottom pocket runs radially on the boss OD** (0.15 mm clearance) and takes side loads into the lid.
- The shaft only carries torque and push, through the D-key.
- **Why not a bushing or bearing on the shaft:** the encoder is soldered to the PCB, and the lid is located by the screws and posts. A close fit around the rotating shaft would over-constrain the shaft against the lid tolerance (±0.2–0.3 mm on FDM), causing binding and extra friction on the detents and the push. With the knob-on-boss bearing, lid misalignment only shifts the knob's running fit.

## Measured option (not built): trimmed shaft + 14 mm knob
For reference only. The PM default is the stock shaft with the 16.5 mm knob, and purchased parts are not modified.
- Cutting 2.5 mm off the shaft (tip 22.0) allows a 14 mm knob with the D-key from 15.0.
- Engagement would be 7.0 mm, and the knob top 23.5 above the PCB / 29.2 above the desk.
- Evaluated with `TK_SHAFT_TRIM=2.5 TK_KNOB_H=14 TK_DKEY_MARGIN=0.5 python build.py --check-only`: 0 CLASH/TIGHT. Nothing is exported.

## Assumptions to verify on parts
- EC11E heights per Alps drawing No.3 (body 4.5, tip 24.5 above the PCB, flat from 14.5); measure one part.
- HS96L03W2C03 FPC bend inset (0.4 ± 0.2 mm) on a real module.
- J1 shell height 3.26 and its face flush with the board edge.
- B3U-1000P height 1.6 and stroke 0.15.
- Component heights are the courtyard box × the typical maximum height (`board_model.HEIGHTS`).
