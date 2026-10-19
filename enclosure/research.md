# TokenKey RT: enclosure research and design directions

- **Date:** 2026-10-19
- **Owner:** TokenKey Enclosure / ID. Reviewers: TokenKey PM, Anand.
- **Status:** Research; Direction A approved. Parametric CAD is in [`cad/`](cad/README.md) (issue #42). No printing or purchases yet. Per [decisions](../docs/decisions.md), there is no enclosure spend until PoC gates G1–G5 pass.
- **Issues:** #29 (research), #42 (CAD), #52 (FPC bend vs USB-C), #54 (EC11E heights).
- **Board data:** **main `e2e5ff9`** (PR #49 merged). J2, L2 and the OLED outline are identical to Layout's #31 commit `eb4495a`, which the numbers below were first taken from.
  - Board file: `hardware/schematic/TokenKey-RT.kicad_pcb`.
  - Docs: [layout-notes](../docs/layout-notes.md) §10–§11 and §13, and [decisions](../docs/decisions.md), rows "Board", "OLED HS96L03W2C03 mechanicals" and "OLED header height".
  - Changes from main `6fb72fa`, all re-extracted:
    - J2 moved from y 5.5 to **y 5.0**;
    - L2 is now **TDK VLS3015CX (1.5 mm)** on the board (verified at `eb4495a`);
    - the OLED drawings and `OLED_KEEP_UNDER` were redrawn for y 5.0, adding the back-side block band.
  - Nothing else that matters to the enclosure moved. Earlier references: `cfc9bc3` (J2 at y 6.3) and main `6fb72fa` (J2 at y 5.5).
- **OLED stack (PM final, 2026-10-19):**
  - The module is soldered straight onto a **3.0 mm plastic-body header**, with no socket and no shim, so the module underside is at h = 3.0.
  - Module thickness ≈ 2.65, so the **OLED top is 5.65 mm** above the PCB top. That is the design value.
  - Header height and module thickness are both CAD parameters. The 6.6 mm figure is superseded.
- **Coordinates:** KiCad board coordinates in mm (x east, y **south**; the board spans 0–50 × 0–40). Assumed values are labelled as assumptions.
- **Regenerating the numbers:** `tools/board_extract.py` (KiCad 9 pcbnew) and `tools/oled_geometry.py`.

## Summary
1. **Desk grip is the most common complaint about small controllers, and mass is what fixes it.**
   - Premium pads fix sliding with a metal base plus a grip ring: Work Louder's CNC aluminium weight [S1][S2], and Monogram's 82 g module with a grip ring [S5].
   - DIY builders say rubber feet alone don't stop a light printed pad from sliding. Added weight works [S7].
   - A ~30 g printed TokenKey would slide when its EC11 is turned. The detent torque is up to 17 mN·m [S10]. **Target ≥ 100–120 g plus a silicone ring or feet.**
2. **The USB-C opening has to fit real cable overmolds, not just the spec.**
   - The spec allows up to 12.35 × 6.5 mm [S12], relaxed to 12.85 × 7.0 mm by the 2023 ECN [S13].
   - One designer measured cables up to 13.0 × 7.4 mm, off-centre, and now leaves 16 × 10 mm [S14].
   - Recessed ports that stop cables seating fully are a recurring complaint [S15]. Users also want plug/pull loads carried by the case, not the solder joints [S16].
3. **The knob is what reviewers judge first.**
   - They praise grippy textured sides, clear steps and a satisfying push click (Stream Deck+ [S8]), and smooth, weighted metal (Nuimo [S9], Surface Dial).
   - They complain about side-to-side wobble (Stream Deck+ owners [S17]) and scratchy encoders (Keychron Q0 Plus [S4]).
   - EC11 builders recommend metal knobs with set screws and a step or bearing face against the housing to cut wobble [S18].
   - Ergonomics data: finger-operated knobs work at 10–30 mm diameter and 15–25 mm height [S19].
4. **Hardware tokens (YubiKey, OnlyKey, SoloKeys, Nitrokey) win on sealed, seamless, no-moving-part construction.** Their failures are thin plastic cracking (Nitrokey 3A mini [S23]) and silicone sleeves tearing (OnlyKey [S21]). Tokens use capacitive touch with an LED prompt instead of buttons [S22][S24].
5. **Small OLED gadgets (e.g. Flipper Zero) use a separate clear screen cover inside a textured matte body.** Flipper's injection-moulding trials hit flow waves in the screen cover, sink marks and weld lines near the buttons, and flash on the screw bosses [S25][S26]. Those are the IM risks to design out.
6. **OLED HS96L03W2C03 (§1.1).**
   - Window **22.74 × 11.86 mm**, centred at J2 pin 1 + (3.81, 10.36).
   - **OLED top 5.65 mm** above the PCB (3.0 mm header + 2.65 mm module).
   - Gap from the module PCB to the USB-C body: **+1.24 mm** with J2 at y 5.0 (main `e2e5ff9`).
   - **FPC bend vs USB-C resolved (#52):** the bend is on the far (south) edge and stays inside the module outline, giving **+1.44 mm** in plan to the J1 body (see `cad/`).
7. **PM review (2026-10-19): Direction A approved.** The cable exits at the rear (board south edge) and the OLED is rotated 180° in firmware. The EC11 **keeps the 20 mm shaft** (EC11E18244A5), with a 16.5 mm knob by default (#54: the shaft tip is 24.5 mm above the PCB). See the Decisions section.
8. **Recommendation: Direction A, a flat two-shell "puck" with screws through the four M2 holes.** It has a **bottom service hatch** over the TC2030 and the UART pads, and a **BOOT pinhole**. Wedge (B) and open-plate (C) variants can share the same PCB interface.

---

## 1. Board facts that drive the enclosure (eb4495a)

To regenerate the full per-footprint data (positions, courtyards, pads, 3D model refs), run `python3 tools/board_extract.py <path/to/TokenKey-RT.kicad_pcb> <out.json>`.

| Item | Value |
|---|---|
| PCB | 50 × 40 × 1.6 mm, R1 corners; 4 × Ø2.2 NPTH at (3,3), (47,3), (3,37), (47,37), each with a 5 mm keepout |
| USB-C J1 | Top side, opening centred at **x = 17**. The receptacle **face is flush with the south edge** (y = 40). Body 9.0 wide, ~3.2 mm tall (typical; not checked against the HRO drawing) |
| EC11 SW2 | EC11E18244A5 (Alps drawing No.3). **Shaft axis (41.9, 17.5)**, body 11.7 × 12.1 × 4.5 mm, **no bushing**. The 20 mm shaft is measured from the body top, so the **tip is 24.5 mm above the PCB** (23.0 pressed). φ6 shaft, round up to 14.5, D-flat (4.5 across) from 14.5 to the tip. Push travel 1.5 mm at 4 N, 36 detents |
| OLED | **HS96L03W2C03**, 0.96" 128 × 64, on J2. **Pins at y 5.0** (main `e2e5ff9`), x 16.34–23.96; pin 1 = GND at the west end. The board carries the real outline (details in **§1.1**):<br>• module PCB: x 6.50–33.80, y 3.56–31.36<br>• glass, AA and four Ø2.5 holes<br>• the back-side block band at y 14.3–17.3<br>• rule area `OLED_KEEP_UNDER`<br>**OLED top 5.65 mm** (3.0 header + 2.65 module) |
| Under the OLED (top side) | **L2 = `TokenKey:L_3.0x3.0mm_TDK_VLS3015CX`, 1.5 mm**, at (9.15, 21.4) rot 180. Verified in the `eb4495a` board file; there is no 3D model yet. Next tallest: U6 1.45, U1 1.4, Q1 1.25 mm. The cap is 2.0 mm (decisions, "Board") |
| U4 SOIC-8 | (3.05, 25): courtyard 0.505 mm outside the module's west edge, 0.105 mm in from the board's west edge |
| Buttons SW3/SW4 | Omron B3U-1000P at (38, 30) and (44, 30), 6 mm apart. 1.6 mm plunger, **0.15 mm pretravel**, 1.5 N [S11] |
| Status LED D1 | 0603 at (36.5, 7.6) |
| **BOOT SW1** | **Bottom** at (47.6, 31). Top-actuated B3U, so it **actuates downward** and can only be reached through a bottom pinhole |
| **TC2030-NL J3** | **Bottom** at (39, 4). Guide holes at (41.54, 4.0) and (36.46, 2.98 / 5.02). The plug comes from below. Hands-free use needs a TC2030-CLIP from the **top** (10.7 × 5.1 mm, 6.7 mm tall with pins) [S28] |
| UART pads TP1–TP5 | Bottom, x 26.5–31.5, y 10–12.6 |
| Bottom heights | SW1 1.6 mm; DNP L1 2.0 mm. The **THT tails** (EC11, J1 tabs, J2 header) must be trimmed to ≤ 1.5 mm |

### 1.1 OLED HS96L03W2C03: geometry, window, standoff and USB-C clearance

**Source.** decisions.md (PR #25) [S41], from HS datasheet V1.0 §1.1 and §1.4:
- **Origin = header pin 1**, with +x toward pin 4 and +y from the header edge toward the glass.
- J2 is at rotation 90 with its pins running east, and the module extends south. Module axes therefore map straight onto board axes, with no mirroring.
- The numbers below come from `tools/oled_geometry.py` (`--header`, J2 y as arguments). The outline that main now carries on its Fab/User layers matches them.

| Feature | Relative to pin 1 (mm) | Board, J2 at y 5.5 (main 6fb72fa) | Board, **J2 at y 5.0 (main e2e5ff9, design)** |
|---|---|---|---|
| Module PCB 27.30 × 27.80 | x −9.84 … +17.46, y −1.44 … +26.36 | x 6.50–33.80, y 4.06–31.86 | y 3.56–31.36 |
| Glass 24.74 × 16.90 | x −8.60 … +16.14, y +3.43 … +20.33 | x 7.74–32.48, y 8.93–25.83 | y 8.43–25.33 |
| Active area 21.744 × 10.864 (x position assumed centred, not dimensioned) | x −7.06 … +14.68, y +4.93 … +15.79 | x 9.28–31.02, y 10.43–21.29; centre (20.15, 15.86) | y 9.93–20.79; centre (20.15, 15.36) |
| Mounting holes Ø2.50 (pad Ø3.0), pitch 23.30 × 23.80 | 2.00 mm from each edge | (8.50, 6.06), (31.80, 6.06), (8.50, 29.86), (31.80, 29.86) | y 5.56 and 29.36 |
| FPC bend, 14.50 wide, at the far (south) edge, 0.4 ± 0.2 inside the outline, no wrap | assumed centred | x 12.90–27.40, so in line with J1 (x 12.5–21.5) | outer edge y ≤ 31.16 |

(With the old J2 at y 6.3, the module would have spanned y 4.86–32.66 and overlapped the J1 body by 0.06 mm. That overlap is why Layout moved J2.)

**Window.**
- Size: AA + 0.5 mm per side = **22.74 × 11.86 mm**. That equals the datasheet viewing area (VA), with R0.5 corners.
- Position: centre at **pin 1 + (3.81, 10.36)**, which is board **(20.15, 15.36)** with J2 at 5.0 (main `e2e5ff9`), or (20.15, 15.86) with J2 at 5.5. In CAD, tie the window to J2 pin 1, not to the board origin.
- Tolerance: the 0.5 mm margin covers header solder position (±0.2), datum-post play (±0.15) and the undimensioned AA x position.
- **Lid stack:**
  - Lid underside **6.0 mm** above the PCB (OLED top 5.65 + 0.35 clearance; PM asked for 0.3–0.4).
  - Lid top **7.5 mm** (1.5 mm plate). The glass therefore sits 1.85 mm below the outer face.
  - The opening is chamfered 45° through the full lid, about **25.7 × 14.9 mm** at the outer face, so a > 160° viewing angle isn't shaded.
- **Glass edges:** the glass extends 1.0 mm past the window on the north side and 4.0 mm on the south side. Keep the lid 0.35 mm clear of the glass. Never load the glass.

**Height.**
- The module is 2.65 mm thick (glass 1.40 + PCB 1.20). The side view also shows a **1.00 mm back-side block**, which hangs **below** the module PCB. It sits in the band y +9.3…+12.3 from pin 1, x unknown.
- **Header height h** (module-PCB underside above the main PCB) = **3.0 mm** (PM). The module is soldered directly onto the header's plastic body.
- **OLED top = h + 2.65 = 5.65 mm (design value, PM final).** The lowest module point, the block, is at h − 1.0 = 2.0 mm.
- `HEADER_H` and `OLED_MODULE_T` are parameters in `cad/params.py`.

| Part under the module | Height | Margin under a 1.0 mm back feature at h = 3.0 |
|---|---|---|
| U6 SOT-23-6 (in the FPC strip) | 1.45 | **+0.55 → resolved** (it was +0.05 at h = 2.5) |
| U1 MAPBGA196 | 1.4 | +0.60 |
| L2 VLS3015CX (on the board at `eb4495a`) | 1.5 | +0.50 |

So the **1.0 mm back-feature / U6 clearance issue is resolved by the 3.0 mm header.** The L2 zero-margin case (old SWPA4020) is gone at `eb4495a`.

**Superseded:**
- 4.9 mm (Winstar-class module on a 2.5 mm header);
- layout-notes §11 "≈ 6.1 mm" (2.5 header + 3.6);
- **6.6 mm** (3.0 header + 3.6 envelope; still written in `eb4495a` layout-notes/decisions as "≈ 6.6 mm / 8.2 mm overall").

**Standoff concept.** There are no holes in the main PCB under the module holes. A foot resting on the main PCB would also hit C2 (0603) and C53 near the south holes, so the module can't be propped up from below there. Instead:
1. **The header sets the height:** the module is soldered directly onto a **3.0 mm plastic-body header** (PM). There is no shim and no socket.
2. **Top-shell datum posts only locate the module; they do not clamp it.** Four posts hang from the lid underside at the four module holes. Each has a **Ø2.2 pin** (0.15 mm radial play in the Ø2.5 hole) and a **Ø4.0 shoulder** that stops 0.1–0.2 mm above the module PCB face. The posts register the glass to the window and keep loads off the glass and header.
   - The north shoulders (holes at y 5.56 with J2 at 5.0) sit 0.87 mm clear of the glass edge.
   - Post length to the shoulder: lid underside 6.0 − module PCB face (3.0 + 1.2 = 4.2) − 0.15 gap = 1.65 mm. The pin reaches 1.6 mm below the module PCB face. The posts are at x 8.5 and 31.8, clear of the header pins at x 16.3–24.0.
3. **Production option:** screw the module to lid bosses (M2 self-tap) and connect it with a low-profile socket or a 4-wire flex. That makes window alignment independent of the main PCB. It needs a BOM or connector change.

**USB-C clearance with the real module.** The J1 body runs from y 32.6 (courtyard from 30.985), x 12.5–21.5. Its top is ~3.2 mm, a typical value not checked against the HRO drawing.
- **Which edge faces J1:** the header (pin row) is on the module's **north** edge (pin-1 origin, glass toward +y). The **far edge, where the FPC bends, is south and faces J1**. The header edge has no overhang.
- **Vertically, the module underside at h = 3.0 is still below the J1 top (~3.26 mm)**, so the clearance has to come in plan.
- **FPC bend (#52, datasheet facts):** 14.5 mm wide, centred. It curves from the glass onto the glass-side face and stays **about 0.4 mm inside the 27.80 outline (±0.2)**, with no wrap past the edge or down. The CAD models it from the glass far edge to 0.2 mm inside the outline (worst case), z 4.2–5.65.
- **J2 at y 5.0 (main `e2e5ff9`, PM final):** the module PCB's far edge is at 31.36, giving **+1.24 mm** to the J1 body. The bend is at **+1.44 mm in plan** (1.72 mm in 3D), above the 0.3 mm rule. The lid is 0.35 mm above the bend, which sits under solid lid 4.0 mm south of the window edge. No J2 shift is needed.
- **Superseded:** the v0.1 "conservative bend" (1.5 mm past the edge, down to z 2.0, −0.26 mm CLASH) is dropped.

**Orientation (decided, PM review).**
- The USB-C cable exits at the **back**, away from the user. The **board's south edge (J1) is the rear of the device**, and the user faces the north edge.
- Firmware rotates the OLED 180° using the SSD1315 segment/COM remap. No board change.
- Seen by the user:
  - the knob (EC11) is on the **left**;
  - BTN1/BTN2 sit **behind** the knob, toward the rear;
  - the status LED D1 is at the front, right of the knob;
  - the TC2030/UART service hatch is under the front half.

## 2. What users like and dislike in similar products

### 2.1 Macro pads and knob pads
- **Work Louder Creator Micro / Micro 2.**
  - A frosted or sandblasted PC shell over a CNC aluminium base. The weight is there "to prevent it from sliding around on your desk" [S1].
  - Micro 2 adds "a strong anti-slip ring" [S2].
  - Ars Technica praised "the just-heavy-enough non-skid base" and the knob [S3].
  - *Take-away: the mass and grip ring are deliberate parts of the design. Diffused PC suits the status lighting.*
- **Keychron Q0 Plus.** Full CNC aluminium, 586 g, 1.9 mm fixed feet, 5.26° typing angle [S4]. One owner review found the encoder scratchy and overly tactile [S4]. *Take-away: weight reads as quality, but encoder feel matters as much as the case.*
- **DIY / Reddit macropads.**
  - Light printed pads slide around.
  - Builders add lead or tyre weights; one added 265 g and found the pad stable.
  - They also add rubber, cork or neoprene pads, but report that feet alone may not grip a light device [S7].

### 2.2 Stream Deck-style controllers
- **Stream Deck Mini.** The fixed 45° integrated stand is praised for stability. Owners complain that it can't be adjusted and that the cable is fixed and too short [S6].
- **Stream Deck+.** The Verge found the dials "feel good to use, with grippy textured sides, and move in clearly felt steps", each with "a satisfying click". It noted the fixed 45° stand is held on with two screws and can be removed to lay the unit flat [S8]. Owners report side-to-side wobble on the dials, including on new units [S17].
  - *Take-away: knurled or ribbed knob sides, a crisp push, and the smallest possible radial play.*

### 2.3 Knob and volume controllers
- **Monogram Creative Console Dial Module.**
  - 82 g; CNC aluminium, sandblasted and anodized.
  - "Soft-touch ABS plastic underside" with a "grip ring on underside [that] prevents unwanted slipping on table tops".
  - Max size 90 × 45 × 30 mm [S5].
- **Senic Nuimo.** Reviewers praise the aluminium ring for a smooth, weighted, precise feel, likened to a hi-fi volume knob [S9].
- **Microsoft Surface Dial.** Has a rubber grip base and a weighted metal knob. One user reports it sliding on an angled Surface Studio screen [S20].
  - *Take-away: a knob reads as "premium" through metal or added mass and low wobble. A large knob on a light body needs the body to stay put.*

### 2.4 Hardware tokens
- **YubiKey 5C.**
  - Glass-fibre-reinforced plastic, no battery or moving parts, IP68, crush-resistant, rated for 100,000+ insertions [S29].
  - Hacker News reports early USB-C plastic degrading, which Yubico reportedly fixed [S30].
- **OnlyKey.** The core enclosure survives crushing and washing machines. The removable silicone jacket can tear [S21].
- **SoloKeys Solo 2.** The chip board is sealed in transparent epoxy, with capacitive touch zones and no moving button. The flat surface helps sleeves fit [S22].
- **Nitrokey 3.**
  - Users report thin plastic cracking or separating; one says a tight adapter pulled the case apart [S23].
  - The LED blinks while the key waits for touch [S24].
  - *Take-away: an unreinforced thin shell near the connector is the failure point. A clear prompt LED is the established "approve" pattern, which matters for TokenKey's approve button (hypothesis H1 in the PoC).*

### 2.5 Small OLED gadgets and earlier product designs
- **Flipper Zero.**
  - 100 × 40 × 25.6 mm, in PC, ABS and PMMA. A separate smooth screen cover sits in a shagreen-textured matte body [S25].
  - T0/T1 moulding issues: flow waves in the screen cover, sink marks and weld lines near the D-pad, ejector-pin gaps between halves, and flash on screw bosses.
  - They fixed these with process tuning, mould polishing, texture and ribs [S26].
- **0.96" OLED windows.**
  - The window should match the active area (~22 × 11 mm), not the module PCB [S31].
  - Commercial bezels for 28 × 28 mm modules are 36 × 36 mm [S32].
  - Viewing angle is > 160°, with software-adjustable contrast [S33]. A flat (untilted) device is therefore readable. A chamfered bezel avoids shading at shallow angles.

## 3. Enclosure engineering rules used

| Topic | Rule | Source |
|---|---|---|
| FDM walls | ≥ 2 mm walls. Component clearance 0.5 mm. PCB-to-wall 1.5–2 mm for FDM, 0.5 mm for SLA/SLS | [S34] |
| Snap fits | Cantilever with ≥ 2 mm engagement and a ~20 mm arm; test cycling | [S35] |
| Heat-set insert, M2 | ~3.3 mm pilot, ~4.2 mm deep, ≥ 2 mm wall round the boss | [S36] |
| IM draft | 1–2° typical, 0.5° minimum; ≥ 3° for light texture (PM-T1), ≥ 5° for medium/heavy (PM-T2) | [S37] |
| IM walls | ABS 1.14–3.56 mm, PC 1.02–3.81 mm; uniform walls; ribs and bosses 40–60 % of the wall | [S38] |
| Knob size | Finger-operated: 10–30 mm diameter, 15–25 mm tall | [S19] |
| Button actuators | Flat centred contact face, 0.3–0.5 mm guide clearance, ~0.2 mm free travel; or flexure arms | [S39][S40] |
| USB-C | Opening for the overmold plus margin, chamfered. Case takes plug loads | [S12]–[S16] |

## 4. Design directions

Common to all three directions:
- **FDM first.** PETG or ASA for the shells; PLA is fine for fit checks only. **SLA** (tough or grey resin) for the cosmetic top and the small actuators.
- **IM notes:** 1.5° draft on the shell walls (3° if textured), 1.8 mm nominal wall, 0.9 mm ribs, cored bosses. A separate PMMA or PC window, either taped or ultrasonically welded.
- **PCB retention:** 4 × M2 screws through the PCB holes. The boss OD is ≤ 5.0 mm so it fits the 5 mm keepout.
- **USB-C:** obround external pocket **13.5 × 8.0 mm** (R 3, 0.5 mm × 45° chamfer), centred at x = 17 and z = PCB top + 1.6. It is 1.9 mm deep and leaves a 0.6 mm skin, so the overmold face stops **1.1 mm** short of the flush receptacle face (0.5 mm board gap + 0.6 skin; check with real cables). The inner hole through the skin is **9.5 × 3.8 mm**. A top-shell rib sits 0.3 mm above the J1 shell to resist prying.
- **BOOT pinhole:** **Ø1.8 mm** hole in the bottom at (47.6, 31). It is drawn mirrored in bottom view, at 2.4 mm from that edge. A guide tube runs up to 0.3 mm short of the B3U plunger, for a SIM tool or paperclip. Keep any PCB ledge or rib out of x > 45.9, y 28.5–33.5.
- **Service hatch:** bottom opening **18.3 × 13 mm** covering x 25.5–43.8, y 1.0–14.0, with a separate 0.8 mm cover that drops into a 0.5 mm recess.
  - It exposes the TC2030 and TP1–TP5 for hand-held programming and UART pogo pins, and clears the H2 boss (Ø4.6, which starts at x 44.7).
  - Keep the lid above J3 free of ribs (≥ 3 mm clear) so the guide pins can poke through.
  - Hands-free TC2030-CLIP use needs the top shell removed.
- **Light pipe for D1:** Ø2 mm clear PC or PMMA rod, **6.5 mm** long (from 0.2 above the LED top at 0.8 mm to flush with the lid top at 7.5 mm), with a Ø3 × 0.4 mm flange under the lid, at (36.5, 7.6). For a quick prototype, a 0.6 mm thinned translucent wall printed in clear SLA also works.
- **Knob:** **Ø17 mm** (parameter, 16–18), **16.5 mm tall** (parameter), on the **20 mm EC11 shaft** (EC11E18244A5, 36 detents, kept by PM). The shaft tip is 24.5 mm above the PCB, so 16.5 mm is the shortest knob that covers it (tip + 0.5 clearance + 1.0 skin, from a 9.5 mm knob bottom). That is above the earlier 12–15 band.
  - Ribbed sides (30 flutes).
  - 2.0 mm axial gap above the lid: 1.5 mm push + 0.5 mm left at full push.
  - **D-bore from 15.5 mm** (1.0 mm above the flat start at 14.5), so the knob never seats on the round section. **9.0 mm shaft engagement** (≥ 7 required).
  - **Bearing step (no bushing):** a Ø11 × 5.0 mm lid boss, top at 12.5, with a Ø7.0 shaft hole (0.5 mm radial, so the shaft never touches the lid). The knob's bottom pocket runs **radially** on the boss OD with 0.15 mm clearance, and overlaps it by 3.0 mm at rest. At full push there is 1.5 mm between the pocket ceiling and the boss top. A bearing on the shaft itself would over-constrain the PCB-mounted encoder against lid tolerance.
  - **Measured option only (not the default):** trimming the shaft 2.5 mm (tip 22.0) would allow a 14 mm knob, with engagement 7.0 and the top 29.2 mm above the desk. The PM chose not to modify purchased parts.
  - **Metal-insert option** (`KNOB_INSERT`):
    - `sleeve` (default): Ø8 bore for a press-fit brass D-sleeve, 7 mm long;
    - `setscrew`: D-bore plus a radial M3 heat-set insert for a set screw;
    - `none`: plain printed D-bore.
  - Knob top **26.0 mm** above the PCB, **31.7 mm above the desk**; +0.7 mm with the grip cord fitted.
  - At Ø18 it stays clear of the OLED window (right edge x 31.52) and D1 (11.3 mm from the axis).
  - It also stays ~3 mm clear in plan of the button caps (12.5 mm south of the axis).
- **Buttons (B3U kept, PM):** printed plunger caps with a **defined travel**.
  - SLA cap Ø4.6 mm in a Ø5.0 lid hole, 0.8 mm proud of the lid.
  - **6.4 mm** from the plunger nub to the cap top (lid top 7.5 + 0.8 − B3U top 1.6 − 0.3 free travel).
  - Travel: **0.30 free + 0.15 B3U stroke + 0.05 = 0.50 mm** to a hard stop, where two Ø1.2 stop feet land on the PCB ±2.5 mm either side of the switch.
  - Two 0.35 mm SLA cantilever arms, with bumps bearing on the lid underside, hold the cap up and retain it. They add an estimated ~2–3 N at full travel; tune `CAP_ARM_T`.
  - Use a different texture per cap (concave vs. dot) plus icons.
  - Revisit after the first print fit check.
- **OLED:** window 22.74 × 11.86 mm at J2 pin 1 + (3.81, 10.36), chamfered through the lid to ~25.7 × 14.9 mm at the outer face. Lid datum posts at the four module holes, for location only. Header h = 3.0. Lid underside at **6.0 mm above the PCB** (OLED top 5.65 + 0.35), lid top at 7.5 mm (see §1.1).
- **Encoder:** the EC11E body is 4.5 mm tall, 1.5 mm below the 6.0 mm lid underside, so **no lid relief** is needed. The full 1.5 mm lid is used, plus the bearing boss on top.
- **Bottom clearance:** 2.5 mm (DNP L1 2.0 mm + 0.5 mm). THT tails are trimmed to ≤ 1.5 mm (PM).
- **Mass and grip (design parameters, no purchases):** steel or brass ballast plus a silicone grip ring or 4 × Ø8 mm feet.
  - Rough estimate: resisting a 17 mN·m detent torque with friction alone (μ ≈ 0.8, r ≈ 18 mm) needs **~120 g**. This is an assumption; the user's finger pressure helps.

### Direction A: flat "Puck" clamshell *(recommended; approved by PM)*
- **Envelope:** **55 × 45 mm**, 3.5 mm outer corner radius. Body height **13.2 mm**: floor 1.6 + clearance 2.5 + PCB 1.6 + 6.0 (OLED top 5.65 + 0.35) + top 1.5.
  - The PCB top sits 5.7 mm off the desk, and the shaft tip is at 30.2 mm above the desk (24.5 above the PCB).
  - Knob top **31.7 mm** above the desk (default 16.5 mm knob).
- **CAD:** [`cad/`](cad/README.md), CadQuery, everything driven from `params.py`.
- **Walls:** 2.0 mm on FDM, 1.6 mm on SLA. 0.5 mm PCB-to-wall gap, located by the bosses.
- **Assembly:** 4 × M2 × 8 mm (DIN 912) from below, through bottom-tray bosses, the PCB holes and into heat-set inserts in top-shell bosses. Lap joint at the parting line. No snaps, so it can be reopened many times.
- **Window:** 22.74 × 11.86 mm opening (§1.1) with a 45° outer chamfer. Optionally a 1 mm smoked PMMA insert, flush in a 24.8 × 13.9 mm pocket.
- **Ballast:** the 2.5 mm under-board gap only fits a **1.2 mm plate** under the BGA area: 18 × 18 mm, ~3 g in steel, ~7 g in tungsten. The CAD estimate is **~30 g total**, far **below the 120 g target**.
  - Reaching it needs ~90 g more, e.g. a 45 × 35 × 7 mm steel slab under a thicker floor, which adds ~7 mm height. Alternatively, accept that the user steadies the puck while turning.
- **Pros:** smallest; fastest to print; uses the existing PCB holes; all service needs met.
- **Cons:** light; flat view of the OLED; little room for ballast.

### Direction B: tilted "Wedge"
- **Envelope:** **58 × 48 mm**. The top face tilts **10°** down toward the user, with the low edge at the board's north edge. Front height ~13.2 mm, back ~21.7 mm (13.2 + 48 · tan 10°), with the USB-C on the tall rear face.
- **Inside:** the back cavity under the PCB takes a **~6 mm steel ballast block (~60–80 g)**, reaching the ≥ 100 g target. Full-perimeter silicone grip ring.
- **Construction:** the same PCB/top-shell interface, hatch and pinhole as A. Only the bottom tray changes, so B can be **a drop-in tray swap for A**.
- **Pros:** better OLED view and knob angle; stable; makes room for the stand look that Stream Deck users like [S6][S8].
- **Cons:** about 2× the print time; a larger footprint; the USB-C pocket on the tilted rear face must stay perpendicular to J1.

### Direction C: open "Sandwich" (bring-up / G4 test rig)
- **Envelope:** 54 × 44 mm. A 2 mm smoked acrylic or SLA top plate and a 2 mm bottom plate on 4 × M2 standoffs (top 7 mm so it clears the 5.65 mm OLED top; bottom 3 mm). The sides are open.
- **Top plate:** cut-outs for the OLED window, knob, flexure button tabs and D1. Plus a 12 × 7 mm **opening above J3** so the TC2030-CLIP can be fitted with the unit assembled.
- **Bottom plate:** the same hatch area left fully open, plus the BOOT pinhole.
- **Pros:** cheapest; quickest; full debug access; USB-C recess is not an issue.
- **Cons:** not a product look; exposed electronics (ESD, dust); flexure buttons feel worse.

### Recommendation
1. Prototype **Direction A** in FDM PETG/ASA, with an SLA top shell, knob and caps, as `enclosure/` v0.1 once the spend gate allows it.
2. Make the **bottom tray a swappable interface**, so the **B wedge tray** can be printed later if G4 users want more grip or tilt.
3. Use **C** only for bench bring-up.
4. CAD: issue #42, [`cad/`](cad/README.md).

## Decisions (PM review, 2026-10-19)

Direction A (the puck) is **approved**. The PM answered the open decisions as follows:

| # | Topic | Decision | Effect on the enclosure |
|---|---|---|---|
| 1 | J2 position | J2 at **y 5.0** (final; Layout `eb4495a`, on main via PR #49 at `e2e5ff9`) | Module +1.24 / FPC bend +1.44 mm to USB-C in plan; window centre (20.15, 15.36). The CAD ties to J2 pin 1 |
| 2 | Cable exit / orientation | USB-C exits at the **back**; firmware rotates the OLED 180° (SSD1315 seg/COM remap); no board change. The **board's south edge is the rear** | Knob on the user's left, buttons behind it, D1 at the front. The USB-C pocket goes on the rear face (B: the tall face) |
| 3 | EC11 shaft / knob | **Updated: option (b).** Keep the **20 mm shaft (EC11E18244A5, 36 detents)**; the 15 mm swap is dropped. Knob height is a parameter. Metal-insert option; radial bearing step. **#54:** engagement ≥ 7 mm, body 13.2 mm | Shaft tip **24.5** above the PCB (20 mm from the body top). Knob 16.5 mm, 9.0 mm engagement, top 26.0 above the PCB / **31.7 mm above the desk**. No purchased-part modifications; the trimmed-shaft 14 mm knob (29.2 mm) is a measured option only. Boss collar approved |
| 4 | THT leads | Trimmed to **≤ 1.5 mm** | Bottom clearance stays at 2.5 mm |
| 5 | User buttons | **Keep B3U**, with printed plunger caps giving a defined travel; revisit after a print fit check | Caps as specified above |
| 6 | M2 holes | Stay **NPTH** (no chassis-GND contact) | Plain screw bosses; no contact spring |
| 7 | Under the OLED / stack | Max **2.0 mm** under the OLED. **Final stack:** module soldered directly onto a 3.0 mm plastic-body header, no socket or shim; OLED top ≈ 5.65 mm | Lid underside 6.0, lid top 7.5, body 13.2 mm. U6 clearance resolved |
| — | Weight and grip | The ~120 g target and the grip ring stay **design parameters**; no purchases | Keep the ballast pocket and the grip-ring groove in CAD |

**Still open or new:**
1. **Board reference:** main `e2e5ff9` (PR #49 merged). J2 stays at y 5.0 (PM).
2. **Docs on main:** layout-notes at `e2e5ff9` now carry the 5.65 mm stack (6.6 / 8.2 superseded).
3. **EC11 heights:** now from Alps drawing No.3 (body 4.5, no bushing, tip 24.5). Confirm on one part.
4. **Measure a sample module:** the FPC bend inset, the back-block x position, and the AA x position.
5. **OLED retention:** lid datum posts locate the module for the prototype; a screwed module plus connector is deferred to production.
6. **Mass:** ~30 g estimated vs. the 120 g parameter (see Direction A).
7. Resolved since the first review:
   - the 15 mm shaft swap is dropped, so there is no EC11 BOM change;
   - L2 is now VLS3015CX on the `eb4495a` board;
   - **#52** FPC bend vs USB-C: resolved (far-edge bend inside the outline, +1.44 mm at J2 y 5.0);
   - **#54** EC11E heights: real part data, bushing-free collar, knob recomputed.

## Sources
- [S1] Core77, "Extra UI for Your Computer: The Creator Micro": https://www.core77.com/posts/133626/Extra-UI-for-Your-Computer-The-Creator-Micro
- [S2] Work Louder, Creator Micro 2: https://worklouder.cc/creator-micro-2
- [S3] Ars Technica, Figma Creator Micro review: https://arstechnica.com/gadgets/2024/01/figmas-creator-micro-made-me-a-macro-pad-person-with-its-colorful-clicky-keys/
- [S4] Keychron Q0 Plus product page (weight, feet, angle): https://www.keychron.com/products/keychron-q0-plus-qmk-custom-number-pad ; owner mini-review (encoder feel; search summary only, the page returned 403 to the fetcher): https://discuss.online/post/45538
- [S5] Monogram Dial Module: https://monogramcc.com/shop/products/dial-module/
- [S6] Stream Deck Mini reviews and complaints: https://venturebeat.com/pc-gaming/stream-deck-mini-review-an-improvement-with-fewer-buttons/ ; https://www.reddit.com/r/ElgatoGaming/comments/9qia7g/stream_deck_cable_too_short_any_suggestions_please/
- [S7] Reddit, macropad weight and anti-slip: https://www.reddit.com/r/MechanicalKeyboards/comments/16p9z8d/macropad_massive_mod/ ; https://www.reddit.com/r/ErgoMechKeyboards/comments/sylkvl/best_slipslide_mitigation/ ; https://www.reddit.com/r/3Dprinting/comments/1azo7y0/q_any_ideas_on_a_grippy_material_so_tabletop/
- [S8] The Verge, Stream Deck Plus review: https://www.theverge.com/23517751/elgato-stream-deck-plus-review
- [S9] Nuimo reviews: https://www.soundandvision.com/content/nuimo-runs-rings-around-other-smart-remotes ; https://www.slashgear.com/senic-nuimo-hands-on-the-iots-tactile-smart-controller-06421795/
- [S10] Alps EC11E18244A5: https://tech.alpsalpine.com/e/products/detail/EC11E18244A5/ ; EC11 catalogue: https://www.mouser.com/datasheet/2/15/alps_alps-s-a0008379064-1-1733314.pdf
- [S11] Omron B3U datasheet: https://omronfs.omron.com/en_US/ecb/products/pdf/en-b3u.pdf
- [S12] USB-IF, Type-C Compliance Document Rev 2.1b (Tables B-1/B-2): https://usb.org/sites/default/files/USB%20Type-C_Compliance%20Document_Rev_2_1b_June_2021.pdf
- [S13] Allion Labs, USB Type-C R2.2 ECN on overmold size (12.85 × 7.0): https://www.allion.com.tw/news-center/cabc_usb_update/
- [S14] Electronics StackExchange, max USB-C overmold: https://electronics.stackexchange.com/questions/475901/what-are-the-max-overmold-dimensions-for-usb-c-plugs
- [S15] Reddit, recessed USB ports: https://www.reddit.com/r/mildlyinfuriating/comments/1rfecnv/there_is_no_reason_to_recess_a_usb_port_it_keeps/
- [S16] Reddit r/esp32, flush USB-C in DIY enclosures: https://www.reddit.com/r/esp32/comments/1uwhh6i/diy_enclosures_any_tips_for_getting_the_esp32s/
- [S17] Reddit r/elgato, Stream Deck Plus wobbly knobs (summary from search; the page timed out on direct fetch): https://www.reddit.com/r/elgato/comments/1phi7ft/stream_deck_plus_wobbly_knobs/
- [S18] Keebio EC11 aluminium knob (set screw): https://keeb.io/products/aluminum-rotary-encoder-knob-ec11-ec11b ; Reddit encoder knob wobble: https://www.reddit.com/r/ErgoMechKeyboards/comments/wwf8i5/rotary_encoder_knob_question/
- [S19] RoyMech, machine interface controls ergonomics: https://www.roymech.co.uk/Useful_Tables/Ergonomics/Human_controls.html
- [S20] Surface Dial: https://techcrunch.com/2016/10/26/surface-dial-hands-on/ ; https://www.reddit.com/r/Surface/comments/5fd0s3/windows_central_surface_dial_review/
- [S21] OnlyKey durability: https://crp.to/2019/01/17/onlykey-durability-review/ ; https://www.chrisapproved.com/blog/onlykey_thoughts.html
- [S22] SoloKeys Solo 2: https://solokeys.com/pages/solo-2-guide ; https://blog.my1.dev/solo-v2-preprod-first-impression
- [S23] Nitrokey 3A mini broke: https://support.nitrokey.com/t/nitrokey-3a-mini-broke-plastic-enclosure/6455
- [S24] Nitrokey 3 LED and touch: https://docs.nitrokey.com/nitrokeys/nitrokey3/led
- [S25] Flipper Zero tech specs: https://docs.flipper.net/zero/development/hardware/tech-specs
- [S26] Flipper blog, "Bringing Cases to Perfection": https://blog.flipper.net/bringing-cases-to-perfection/
- [S27] 0.96" 128×64 OLED module spec (active area 21.74 × 10.86, module 27.3 × 27.8): https://tailorpixels.com/wp-content/uploads/2023/10/TOJMD096A-SPEC-0.96-Inch-OLED-128%C3%9764-1.pdf
- [S28] Tag-Connect TC2030-CLIP datasheet: https://www.tag-connect.com/wp-content/uploads/bsk-pdf-manager/TC2030-CLIP_Datasheet_24.pdf ; TC2030-IDC-NL: https://www.tag-connect.com/product/tc2030-idc-nl
- [S29] Yubico YubiKey 5C: https://www.yubico.com/product/yubikey-5-series/yubikey-5c/
- [S30] Hacker News on YubiKey 5C robustness: https://news.ycombinator.com/item?id=18058406
- [S31] 128×64 OLED enclosure: https://duino4projects.com/128x64-oled-enclosure-the-easy-way/
- [S32] Bezel for 0.96" SSD1306: https://www.bezelsanddisplays.co.uk/product/bezel-for-0-96-128x64-ssd1306-oled-display/
- [S33] 0.96" OLED datasheet (viewing angle > 160°): https://www.net4web.de/downloads/datasheets/net4web_oled_096_techdata_en_06052022.pdf
- [S34] FacFox, enclosure design for 3D printing: https://facfox.com/docs/kb/enclosure-design-guide-for-3d-printing
- [S35] FacFox, snap-fit enclosures: https://facfox.com/docs/kb/how-to-design-and-3d-print-snap-fit-enclosures
- [S36] 3D People, threaded inserts guide: https://3dpeople.uk/wp-content/uploads/2025/05/2023-06-12ThreadedInsertsGuide.pdf
- [S37] Protolabs, draft guidelines: https://www.protolabs.com/resources/design-tips/improving-part-moldability-with-draft/
- [S38] Protolabs, IM design guidelines / wall thickness: https://www.protolabs.com/services/injection-molding/plastic-injection-molding/design-guidelines/
- [S39] FreeCAD tact-switch button design (JP): https://zesys.net/ai-blog/freecad-course/fc-28/
- [S40] Volksswitch flexure spring: https://volksswitch.org/index.php/volks-devices/the-volksswitch/version-3-introducing-the-flexure-spring/
- [S41] TokenKey `docs/decisions.md`, row "OLED HS96L03W2C03 mechanicals" (PR #25, `issue-24-l2-inductor` @ f2465ab): https://github.com/anand2532/TokenKey-RT/pull/25

*Most review claims come from search-result summaries. Pages fetched and read directly this pass: S5, S8, S14, S26. Check the others before quoting them in marketing or final specs.*
