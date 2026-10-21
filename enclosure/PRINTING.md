# TokenKey RT enclosure v0.2: printing and assembly (#72)

> **Not printed yet.** No prints, orders or spend until the PoC gate (G1–G5 in `docs/decisions.md`) passes. This is the package to use at that point.
> Geometry source: the **CadQuery** exports, which are authoritative. The print STLs come from `cad/print_export.py` (`make print` in `cad/`). The FreeCAD port (`freecad/`) is a validated mirror.

## Files
| File (`exports/print/`) | Part | Process |
|---|---|---|
| `top_shell.stl` | lid + walls, posts, knob boss | FDM PETG (PLA for fit prints) |
| `bottom_tray.stl` | floor, bosses, hatch frame, BOOT tube, plate pins, 4 foot pockets | FDM PETG |
| `hatch_cover.stl` | TC2030/UART hatch cover with the 5th foot pocket | FDM PETG |
| `knob.stl` | Ø17 × 16.5 fluted knob | FDM PETG; SLA tough resin optional |
| `button_cap_btn1.stl`, `button_cap_btn2.stl` | B3U plunger caps with 0.35 mm return arms | **SLA** (standard or tough resin) |
| `light_pipe.stl` | Ø2 × 6.5 pipe with Ø3 flange | **SLA clear** (or a Ø2 PMMA rod, see BOM) |
| `tolerance_coupon.stl` | fit coupon, print first | same printer/material as the shells |

The steel plate (`exports/ballast_plate.dxf`, laser-cut), the feet and the brass sleeve are bought parts; see [BOM.md](BOM.md). The STLs are the **FDM** build: 2.0 mm walls. For an all-SLA shell, rebuild with `TK_PROCESS=SLA` (1.6 mm walls) and re-run `make print`.

## Orientation (already applied in the STLs; parts sit on z = 0)
| Part | Orientation | Why |
|---|---|---|
| top_shell | **Lid up, as installed** | The Ø11 knob boss stands 5 mm above the lid, so face-down printing is impossible without supporting the whole cosmetic face. Upright, the window chamfer widens upward and needs no support. The only supports are under the lid underside (a non-cosmetic cavity) and under the post tips. |
| bottom_tray | Floor on the bed | Flat datum for the lip and bosses. Foot pockets (Ø8.4), counterbores (Ø4.0) and the hatch recess are short bridges, so no supports are needed. |
| hatch_cover | Outer face on the bed | The flush cosmetic face is the bed face. The foot-pocket roof is an 8.4 mm bridge. |
| knob | **Top on the bed** (flipped) | The bearing pocket (Ø11.3) and sleeve bore open upward, so there are no internal bridges. The flutes run vertical, which gives the best grip texture and roundness. The 1 mm top fillet prints as a small bed-edge overhang, which is acceptable. For SLA, tilt it 30° in the slicer with supports on the skirt only. |
| button caps | Head up | SLA. Supports on the stop feet and bar underside only. The head stays support-free because it is the touch surface. |
| light_pipe | Optical top face up | SLA clear. The exit face stays unsupported, with supports on the LED end only. |

## Print settings (0.4 mm nozzle)
| Part | Layer | Walls / perimeters | Top / bottom | Infill | Supports |
|---|---|---|---|---|---|
| top_shell | 0.16 (0.12 for the top 2 mm) | 4 (≈ 1.8 mm, so the 2.0 wall is solid) | 6 / 5 | 40 % gyroid | **Tree, build plate only**, inside the cavity. Enforce under the lid underside, the 4 screw posts and the module posts. Block them in the window and button holes. Ironing on the top face optional |
| bottom_tray | 0.20 | 4 | 5 / 6 | 30 % gyroid | none |
| hatch_cover | 0.12 | 3 | solid (1.6 mm part) | 100 % | none |
| knob | 0.12 | 5 | 6 / 6 | 60 % (mass, sleeve support) | none |
| button caps (SLA) | 0.05 | – | – | solid | light supports, ≥ 0.3 mm tips, on the feet/bar |
| light pipe (SLA clear) | 0.05 | – | – | solid | LED end only |
| coupon | as the shells | 4 | 5 / 5 | 40 % | none |

PETG: nozzle 235–245 °C, bed 75–80 °C, fan 30–50 %. PLA fit prints: holes come out about 0.05 mm tighter than in PETG.

## Tolerances and fits (CAD values; check them with the coupon)
| Feature | CAD | Expectation / adjust |
|---|---|---|
| M2 clearance through tray bosses | Ø2.4 (screw 2.0) | ok down to Ø2.3 as printed |
| Head counterbore | Ø4.0 × 2.2 (DIN 912 head Ø3.8 × 2.0) | head sits 0.2 below the floor face |
| Heat-set insert holes (top-shell posts) | **Ø3.2 × 5.0 deep** (4.0 + 1.0 melt relief) | for M2 × 3.0 inserts (OD ≈ 3.6). If inserts walk, use the coupon's Ø3.0/3.4 holes to pick the size |
| Knob on the boss (radial running fit) | knob bore Ø11.3 on the Ø11.0 boss = **0.15 mm radial** | FDM holes print 0.1–0.2 small. Test the coupon rings 11.2 / 11.3 / 11.4 on the Ø11 peg: pick the one that spins freely without wobble, then set `KNOB_BEARING_CLR` (0.10 / 0.15 / 0.20) |
| Knob axial | 2.0 mm skirt-to-lid gap at rest (1.5 push + 0.5) | set it with a 2.0 mm shim at assembly |
| Shaft through the lid | Ø7.0 on the Ø6 shaft (0.5 radial) | never touches; no fit |
| Brass sleeve in the knob | bore Ø8.0, sleeve OD 8.0 | press or heat-press, see post-processing |
| Button cap in the lid hole | Ø4.6 cap in a Ø5.0 hole (0.2 radial) | caps must drop freely. Coupon holes 4.8 / 5.0 / 5.2 against the Ø4.6 peg |
| Cap travel | 0.30 free + 0.15 B3U + 0.05 = **0.50 mm to the hard stop** | measure; see the checklist |
| Light pipe | Ø2.0 in a Ø2.05 hole; flange Ø3 × 0.4 under the lid | slip fit; one drop of CA if loose |
| Window | 22.74 × 11.86 at the lid underside, 45° chamfer to 25.74 × 14.86 | self-supporting upright; deburr the chamfer edge |
| Tray lip / rabbet | 1.0 × 1.0 lip, 0.15 clearance | should slide together by hand |
| Hatch cover | 0.1 per side in the recess | friction fit; sand the plug if tight |
| Foot pockets | Ø8.4 × 1.0 for Ø7.9 feet | coupon pockets 8.2 / 8.4 / 8.6 |
| Steel plate | on the floor, 2 × Ø2.0 pins in Ø2.4 plate holes | plate top 1.3 mm under the PCB, 0.35 over 0603s |

**Tolerance coupon** (`tolerance_coupon.stl`, about 62 × 26 mm plus three loose rings). Print it first, in the same material and settings as the shells. Hole sizes go up from left to right.
- **Row 1:** insert holes Ø3.0 / 3.2 / 3.4, then M2 clearance Ø2.2 / 2.4 / 2.6.
- **Row 2:** cap holes Ø4.8 / 5.0 / 5.2, then blind foot pockets Ø8.2 / 8.4 / 8.6 × 1.0.
- **Pegs and rings:** a Ø11 × 5 boss peg, a Ø4.6 cap peg, and three rings with bores 11.2 / 11.3 / 11.4 for the knob running fit.

## Post-processing
1. **Remove supports** from the top-shell cavity. Clean up the post tips and the lid underside where the module posts and caps sit; no stringing in the button and pipe holes.
2. **SLA parts:** wash in IPA (2 × 3 min), dry, then UV-cure as the resin datasheet says. Cure the caps lightly, because over-cured arms get brittle. Sand the support nubs off the cap feet so the hard-stop height stays true.
3. **Heat-set inserts:** soldering iron with an M2 insert tip, about 220–230 °C for PETG (190–200 °C for PLA). Press straight down into each top-shell post until the insert is **flush with the post end face**, the face that lands on the PCB. Let it cool before loading. Check with an M2 screw.
4. **Knob sleeve:** press the brass D-sleeve into the knob bore, flat aligned to the bore's D, flush with the pocket ceiling. Use a vise with soft jaws, or warm the sleeve to about 120 °C for PETG.
5. Deburr the window chamfer and the USB-C pocket edges, then wipe with IPA before fitting the feet.
6. **Steel plate:** deburr the laser-cut edges and wipe clean. Coat it against rust (zinc plate or primer), or use stainless 1.4301.

## Assembly order
1. Top shell: inserts are in (post-processing 3).
2. Light pipe into its lid hole from inside, flange against the lid underside.
3. Button caps from inside, heads up through the Ø5.0 holes. The arm bumps rest on the lid underside.
4. Lower the top shell onto the PCBA (OLED already soldered on its 3.0 mm header):
   - the module locating posts drop into the four module holes;
   - the encoder shaft passes the Ø7 boss hole;
   - the screw posts land on the PCB at H1–H4;
   - USB-C lines up with the rear pocket.
5. Bottom tray: stick the steel plate onto the floor over the two pins, using thin transfer tape (BOM).
6. Close the tray onto the board, lip into the rabbet. Fit 4 × M2 × 8 from below and tighten until snug, about 0.15 N·m. Don't strip the inserts.
7. Press in the hatch cover, thumbnail notch to the west.
8. Clean the pockets with IPA and press in the 5 feet: 4 in the tray, 1 in the hatch cover.
9. Knob: align the sleeve's D with the shaft flat and push on with a 2.0 mm shim under the skirt. Remove the shim and check the push click.

## Fit-print checklist (first article; record the results in #72)
- [ ] Coupon: choose the insert hole, M2 clearance, cap hole, foot pocket and knob-ring fit, and feed any change back to `params.py`.
- [ ] Shells close by hand. The lip seats all round with no rocking, and the parting line is even.
- [ ] Screws: head flush or below the floor face, inserts don't spin, and you can reopen it 5 times.
- [ ] OLED: glass centred in the window (±0.3 mm), not touched by the lid (0.35 gap), no pressure on the glass when you squeeze the lid.
- [ ] Knob: no wobble on the boss, no rub at rest, a full 1.5 mm push with a clear click, and the skirt doesn't touch the lid at full push.
- [ ] **#55 B3U cap force:** with a force gauge or kitchen scale, measure:
  - the force to actuate each cap, target ≤ 4 N (B3U ~1.5 N plus arm preload);
  - the hard stop reached at 0.5 mm;
  - that the cap always returns and nothing sticks.
  - Adjust `CAP_ARM_T` 0.35 ±0.05 and reprint if needed.
- [ ] LED visible through the pipe in daylight and off-axis.
- [ ] USB-C: three different cables (thin, standard, thick overmold) fully seat. Check plug/pull with the case holding the load.
- [ ] Service: TC2030 reachable with the hatch removed. BOOT pinhole works with a paperclip and releases cleanly.
- [ ] Desk: no slip when turning the knob with a hand resting on the puck. No tipping when pressing SW4 hard. All 5 feet in contact, with no rocking.
- [ ] Mass on a scale vs the CAD estimate (≈ 39.5 g).
