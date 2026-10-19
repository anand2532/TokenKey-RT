# TokenKey RT: PCB layout notes (outline, stackup, design rules, zoning)

- **Date:** 2026-10-19
- **Owner:** TokenKey Layout. Reviewers: TokenKey PM, TokenKey DFM, Anand.
- **Status:** SPEC ONLY. No board file yet. Placement and routing start after the schematic PR merges.
- **Project:** the whole KiCad project lives in `hardware/schematic/` (see [decisions](decisions.md)). The board will be `hardware/schematic/TokenKey-RT.kicad_pcb`, next to `TokenKey-RT.kicad_pro` / `TokenKey-RT.kicad_sch`. **The project name must stay `TokenKey-RT`** so KiCad picks up `TokenKey-RT.kicad_dru`.
- **Staged rules:** [`hardware/schematic/TokenKey-RT.kicad_dru.staged`](../hardware/schematic/TokenKey-RT.kicad_dru.staged). Rename it to `TokenKey-RT.kicad_dru` in the PR that creates the board.
- **Fab source of truth:** TokenKey DFM draft `fab/stackup.md` (JLCPCB 4-layer stackup, USB impedance, BGA via rules). JLC figures are from https://jlcpcb.com/capabilities/pcb-capabilities (fetched 2026-10-19).

All values are subject to engineering verification per [baseline spec section 8](baseline-specs.md#8-design-constraints).

---

## 1. Board outline

| Item | Value |
|---|---|
| Size | **50.0 × 40.0 mm** (a target, not a hard limit; see §7 for fit risks) |
| Corners | 1.0 mm radius, on Edge.Cuts, 0.05 mm line |
| Placement in KiCad | Upper-left corner at (0, 0); board spans x 0…50, y 0…40 (KiCad y points down) |
| Grid origin and drill/place (aux) origin | **Lower-left corner (0, 40)**, so fab and pick-and-place coordinates are positive from the lower-left |
| Thickness | 1.6 mm nominal (JLC ±10 %: 1.44–1.76 mm) |

## 2. Mounting holes

4 × `MountingHole:MountingHole_2.2mm_M2` (2.2 mm NPTH, no copper). Use the `_Pad` variant only if the enclosure needs a chassis-GND contact; decide that with the enclosure.

| Ref | Centre, KiCad coords (mm) | Centre, from lower-left aux origin (mm) |
|---|---|---|
| H1 | (3.0, 3.0) | (3.0, 37.0) |
| H2 | (47.0, 3.0) | (47.0, 37.0) |
| H3 | (3.0, 37.0) | (3.0, 3.0) |
| H4 | (47.0, 37.0) | (47.0, 3.0) |

- **Keepout:** 5.0 mm diameter (r = 2.5 mm) around each centre, on **all layers**, for footprints, tracks, vias and zones (KiCad rule area: no tracks / vias / pads / copper pours / footprints). The keepout ends 0.5 mm inside the board edge. 5 mm covers an M2 DIN 912 head (3.8 mm) or an M2 washer (5 mm).
- JLC checks: NPTH ≥ 0.50 mm (2.2 OK); NPTH to track ≥ 0.20 mm (the keepout gives ≥ 1.4 mm); copper to routed edge ≥ 0.2 mm (rule set to 0.30).

## 3. Stackup: JLCPCB **JLC04161H-3313** (4 layers, 1.6 mm)

Aligned with the TokenKey DFM draft. It replaces the -7628 from the original brief because the thin 3313 prepreg gives a 90 Ω pair narrow enough (0.155 mm) to enter a 0.65 mm-pitch BGA with only a short neck-down. On 7628 the pair is about 0.27 mm wide.

| # | Layer (KiCad name) | Function | Material | Thickness | Er |
|---|---|---|---|---|---|
| — | F.Mask | Top soldermask | LPI | ~0.03 mm over laminate / ~0.015 mm over copper | 3.8 |
| L1 | **F.Cu** | Signal: BGA, USB pair, most parts | Cu, 1 oz finished | 0.035 mm | — |
| — | Prepreg | | 3313 × 1 | **0.0994 mm** | **4.1** |
| L2 | **In1.Cu, named `GND`** | Solid GND plane, the reference for L1 | Cu, 0.5 oz | 0.0152 mm | — |
| — | Core | | FR-4 (Nan Ya NP-155F, per JLC calculator) | **1.265 mm** | **4.6** |
| L3 | **In2.Cu, named `PWR`** | 3V3 plane, plus DCDC/core islands as needed | Cu, 0.5 oz | 0.0152 mm | — |
| — | Prepreg | | 3313 × 1 | **0.0994 mm** | **4.1** |
| L4 | **B.Cu** | Signal: BGA escape, bottom decoupling, bottom parts | Cu, 1 oz finished | 0.035 mm | — |
| — | B.Mask | Bottom soldermask | LPI | as top | 3.8 |

Copper plus dielectric adds up to about 1.564 mm; JLC's calculator quotes 1.56 mm finished. Er 3313 = 4.1 (JLC capabilities page; an older JLC cart page says 4.05).
**Order settings:** 4 layers, 1.6 mm, FR-4, 1 oz outer / 0.5 oz inner, **impedance control ±10 %, stackup JLC04161H-3313** (pick it explicitly; the calculator's default tab is -3313A), **ENIG**, green mask. Small-via option ON (see §4.2).

## 4. Design rules

### 4.1 Board Setup → Constraints (global floors)

Custom rules override these, so the floors sit at the BGA values and the staged `.kicad_dru` raises everything outside the MCU courtyard back to standard values.

| Constraint | Value | JLC capability (multilayer, 1 oz) | Status |
|---|---|---|---|
| Min track width | 0.09 mm | 0.09 mm (3 mil OK in BGA fan-out) | OK |
| Min clearance | 0.09 mm | 0.09 mm | OK |
| Min via annular ring | 0.075 mm | via dia = hole + 0.10 min / + 0.15 preferred | OK (preferred value) |
| Min via diameter / hole | 0.30 / 0.15 mm | 0.25 / 0.15 min, 0.20 preferred hole | OK, **surcharge** (0.15 hole at any diameter) |
| Min through-hole | 0.15 mm | 0.15 mm | OK (at JLC minimum) |
| Hole to hole | 0.25 mm | via 0.20 mm; **PTH pad 0.45 mm** | OK (pads raised to 0.45 by custom rule) |
| Hole clearance (hole to copper) | 0.20 mm | via hole to track 0.20 mm | OK everywhere, **no exception** (§4.2) |
| Copper to edge | 0.30 mm | 0.20 mm routed | OK |
| Silk to pad / min text | 0.15 mm / 1.0 mm high, 0.15 mm stroke | 0.15 mm / 1.0 mm | OK |
| Soldermask | 1:1 expansion, min web 0.10 mm | 1:1, bridge 0.10 mm (green) | OK |

### 4.2 BGA area (MCU courtyard, MAPBGA196 10 × 10 mm, 0.65 mm pitch)

**LOCKED (TokenKey PM, 2026-10-19, supersedes the earlier 0.20/0.35 lock):** BGA fan-out via **0.15 mm drill / 0.30 mm pad (0.075 mm annular ring)**, tracks and spaces **0.10 / 0.10 mm** between vias (the rule floor is 0.09 mm to absorb rounding). TokenKey DFM confirmed that JLC's "Via hole to Track 0.2 mm" rule also applies inside the BGA fan-out, which the 0.20/0.35 via broke (0.175 mm).

- **Geometry (0.65 mm pitch, dog-bone via in the diagonal gap, one centred 0.10 mm track per channel):**
  - Via hole edge to track: (0.65 − 0.10)/2 − 0.075 = **0.200 mm**, which meets JLC's 0.2 mm rule with no exception.
  - Via pad to track: (0.65 − 0.10)/2 − 0.15 = **0.125 mm** (≥ 0.09 BGA / 0.10 general).
  - Via pad to via pad: 0.65 − 0.30 = 0.35 mm, so only one track per channel.
  - Via hole to via hole: 0.65 − 0.15 = 0.50 mm (≥ 0.25).
  - Annular ring 0.075 mm is JLC's preferred value (hole + 0.15).
- **No hole-to-track exception.** The staged `.kicad_dru` applies the 0.20 mm `hole_clearance` everywhere, on all layers. The earlier 0.17 mm BGA exception is removed. **No POFV needed.**
- **JLC surcharge:** a 0.15 mm hole costs extra at any pad size. DFM reports that 0.15 and 0.20 mm drills with a pad < 0.45 mm fall in the **same JLC small-via surcharge group**. The exact price difference is **pending** a live quote.
- **Drill / aspect ratio:** 0.15 mm is JLC's **minimum** multilayer drill (0.15/0.25), so there is no margin below it. Aspect ratio 1.6 / 0.15 = **10.7:1**. JLC's capabilities page doesn't publish a maximum aspect ratio, so **TBD (DFM):** confirm in the quote / DFM review that 10.7:1 at 1.6 mm is accepted with no extra charge or yield note. JLC's 0.1 mm holes are only offered on boards ≤ 1.0 mm thick, which doesn't apply here.
- **JLC quote (DFM, 2026-10-19):** 4 L, 50 × 50 mm, qty 5, 1.6 mm, JLC04161H-3313, impedance on. 0.15/0.30 vias come to **≈ $89.96**, against **$59.03** for the 0.3/0.45 default. The difference is a small-via line (≈ $17), an auto-added 4-wire Kelvin test (≈ $17) and Tg155 (≈ $3). Build time 3–4 days. 0.15 costs no more than 0.20.
- **Via covering (OPEN, DFM confirming before release):** JLC disables "Tented" once a stackup and impedance control are selected. Untented dog-bone vias next to BGA pads risk solder wicking, so we want soldermask-covered vias, or plugged/epoxy-filled if JLC requires that. **In KiCad, set the BGA vias to tented on both sides** (via properties, front and back), so the mask Gerbers show covered vias whatever the order option.
- Rejected alternative, kept for the record: 0.20/0.35 needed a 0.17 mm hole-to-track exception that JLC would flag.
- Never put unfilled vias in BGA pads.

### 4.3 Outside the BGA

- Default via **0.6 / 0.3 mm** (0.15 mm ring, no surcharge). DFM proposes 0.5 / 0.3, which is also no-surcharge and acceptable if density needs it.
- Via annular ring ≥ **0.125 mm**, track ≥ 0.15 mm, clearance ≥ 0.15 mm.
- Through-hole component pads (EC11, USB-C shell tabs, headers): hole to copper ≥ 0.30 mm (JLC PTH-to-track 0.28 min / 0.35 recommended; inner PTH hole to copper 0.3); PTH annular ring ≥ 0.15 mm (JLC recommends 0.20); pad hole to hole ≥ 0.45 mm.

### 4.4 Net classes (to be set in `TokenKey-RT.kicad_pro` with the board PR)

| Net class | Track | Clearance | Via (dia/hole) | Diff gap | Pattern(s) | Notes |
|---|---|---|---|---|---|---|
| **Default** | 0.15 mm | 0.15 mm | 0.60 / 0.30 | — | (everything else) | **PM-approved** |
| **Power** | 0.40 mm trunks (3V3/VBUS); 0.30 mm min for local branches | 0.20 mm | 0.60 / 0.30 | — | `VDD*`, `3V3`, `/3V3`, `VBUS`, `/VBUS`, `DCDC*`, `/DCDC*` | **PM-approved**. Pour where possible; check VBUS current |
| **USB_HS** | **0.155 mm** | 0.50 mm to other nets | none (L1 only) | **0.20 mm** | `/USB_D*`, `/USB*_D[PN]` | **PM-approved**. 90 Ω diff, JLC-calculator values (§5) |
| **BGA_Escape** | 0.10 mm (0.09 min) | 0.10 mm (0.09 min) | **0.30 / 0.15** | — | applied by area (U1 courtyard), not by net | **PM-locked** (§4.2). Enforced by the custom rules in the `.kicad_dru` |

The net patterns assume hierarchical names like `/USB_DP`, `/USB_DN`. **The schematic bot should name the USB pair `USB_DP` / `USB_DN`** (KiCad's diff-pair detection needs a `P`/`N` or `+`/`-` suffix) and keep the power nets matching the patterns above. DFM's draft calls the BGA class `BGA_Fanout`; this file uses `BGA_Escape` per the PM brief.

## 5. USB 2.0 HS impedance (90 Ω differential, L1 over L2 GND)

**Authority: JLC impedance calculator** (run by TokenKey DFM, JLC04161H-3313, Differential Pair non-coplanar, L1 ref L2, 90 Ω): **W = 0.154 mm, S = 0.20 mm**. Set KiCad to **0.155 / 0.20 mm**. 50 Ω single-ended on L1: **W = 0.151 mm** (reference only; no 50 Ω nets planned).

**Cross-check (Layout):** a 2-D quasi-static finite-difference field solve (Laplace, odd mode, 2.5–5 µm grid, converged to < 0.3 Ω) with h = 0.0994 mm, Er 4.1, t = 0.035 mm, and a conformal mask of Er 3.8 (0.03 mm on laminate, 0.015 mm on copper):

| W / S (mm) | Bare (no mask) | With mask |
|---|---|---|
| 0.15 / 0.20 | 99.4 Ω | 92.1 Ω |
| **0.155 / 0.20** | 97.8 Ω | **90.7 Ω** |
| 0.16 / 0.20 | 96.3 Ω | 89.4 Ω |
| 0.18 / 0.20 | 90.7 Ω | 84.6 Ω |
| 0.124 / 0.20 (−20 % etch) | 110.2 Ω | 101.1 Ω |
| 0.186 / 0.20 (+20 % etch) | 89.4 Ω | 83.5 Ω |

The masked solve hits 90 Ω at W ≈ 0.157 mm (90.7 Ω at 0.155 mm), so it **agrees with the JLC calculator within about 0.003 mm / 1 Ω**. As a rough check only, the IPC-2141A closed form gives 89 Ω at 0.16 / 0.20 (bare). That is about 7 Ω below the bare field solve, because the formula is unreliable when W > h, as it is here. At JLC's untrimmed ±20 % track tolerance, the masked impedance would span about 83–101 Ω, slightly past +10 % on the narrow side. That is why the order must use **impedance control**: JLC then compensates the etch and tests to ±10 % (81–99 Ω). Don't order this board without impedance control.

Routing rules (also in the `.kicad_dru`): L1 only, **no vias**, intra-pair skew ≤ 0.15 mm, uncoupled length ≤ 3 mm (the BGA escape from row L to the body edge is about 2.7 mm; neck to 0.10 mm only inside the courtyard), ≥ 0.5 mm to other signals, ≥ 1 mm from clocks (24 MHz, 32 kHz, FlexSPI SCLK) and the DCDC switch node/inductor. L2 stays solid under the whole pair, including under the USBLC6-2SC6. Put the ESD and connector pads in the path (fly-by), with no stubs.

## 6. USB-C connector (notes only, no footprint yet)

- Part: **TYPE-C-31-M-12** (Korean Hroparts), **LCSC C165948**, USB 2.0 16-pin SMD receptacle.
- **DECIDED (TokenKey PM, 2026-10-19): south long edge (y = 40), centred under the BGA (x ≈ 17 mm).** The USB balls (DN M8 / DP L8) escape south, so a south-edge connector gives a straight pair about 12–15 mm long with no bends around other parts. A short-edge connector would need the BGA rotated 90° or a pair routed around the QSPI or crystal zone.
- **USBLC6-2SC6** immediately behind the connector (about 2–3 mm), in the pair path. CC1/CC2 5.1 kΩ Rd next to the connector. VBUS input protection and the AP2112K-3.3 LDO near the connector's VBUS pins.
- Check the shell-tab THT holes against §4.3 and the mounting-hole keepouts (H3/H4 keepouts end at x = 5.5 mm and x = 44.5 mm, so they don't clash with a connector centred at x ≈ 17).

## 7. Zoning plan for later placement (proposal)

Coordinates are KiCad board coordinates (mm), with the BGA (U1) assumed at **(17, 17)**, unrotated, ball A1 top-left. Ball positions are x = 17 + (col − 7.5) × 0.65 and y = 17 + (row − 6.5) × 0.65 (rows A…P without I/O). The body spans 12–22 mm in both x and y. Balls are grouped by side:

| Group | Balls | Escape side | Zone |
|---|---|---|---|
| USB | DN M8, DP L8; VBUS N6 | **South** on L1 through the column 7/8 and 8/9 channels, no vias, solid L2 | Straight south to the USB-C on the south edge |
| DCDC | M1/M2, N1/N2 | West | **SWPA4020S4R7MT** (4 × 4 mm) on top just west of balls M1–N2 (≈ x 8–11, y 18–22), with a tight loop: DCDC_LP/LN, input cap and output cap all within about 3 mm, on solid L2, and ≥ 1 mm from the USB pair |
| QSPI boot flash | CS L3, SCLK L4, IO0–3 P3/N4/P4/P5 | South-west | **W25Q64JVSSIQ** (SOIC-8, 208 mil) south-west of the BGA (≈ x 5–12, y 24–31), clear of the H3 keepout (≥ 5.5 mm from the corner) and ≥ 1 mm from the USB pair; SCLK kept short |
| Decoupling | power balls incl. **F6–F8, L1/L2, K4** | Down (L4) | 0402/0201 caps on the **bottom**, directly under their power balls, sharing the BGA vias (NXP HDG). Bulk caps around the BGA perimeter |
| 24 MHz crystal | P11 / N11 | South-east | 2016 or 3225 crystal on top at about (21–23, 23–25). Keep ≥ 1 mm from the USB pair. Short, symmetric traces, GND guard and a local L2 return |
| 32.768 kHz **ABS07** | N9 / P9 | **East or south-east, not south** | Top at about (20–22, 22–23) with a GND guard ring. ⚠ N9/P9 sit in column 9, next to the column 8/9 channel the USB DP escape uses. Route the 32k pair east first and keep its traces ≥ 1 mm from USB outside the ball field |
| Reset / power | POR_B M7, ONOFF M6 | South/west | Small RC and pull-ups near the BGA, south-west |
| SWD / JTAG | SWDIO E14, SWCLK F12, SWO G13, JTAG_MOD F13 | East | **TC2030-NL** on the **bottom**, east of the BGA (≈ x 24–33, y 14–18, mirrored). Keep its legless-clip area and 3 NPTH locating holes clear of other bottom parts |
| Boot | F11 / G14 | East | **Boot button on the bottom** near TC2030 so it can be pressed with the case open |
| UART console | K14 / L14 | East | **UART pads (TX/RX/GND)** on the bottom, east side |
| I2C OLED | J11 / K11 | East | **27 × 27 mm I2C OLED module on top, right half** (≈ x 22–49, y 4–31), on a 4-pin 2.54 mm header so low parts can sit underneath |
| Encoder + buttons | L11 / M12 / L12 / K12 / J12 | East | **EC11 encoder on top, lower-right** (≈ x 31–43, y 27–39, clear of the H4 keepout) plus the two buttons along the east/south-east edge |
| Spare buck | — | — | **Spare buck-converter footprint on the bottom** near the USB-C VBUS input (DNP, per decisions: AP2112K LDO now, buck later) |

Notes:
- All listed signal balls are within the outer 4 rows/columns of the 14 × 14 array, which matches DFM's 4-layer escape limit (DFM §3.2 d). Unused inner balls must be GND/PWR or no-connect.
- Bottom side: passives, TC2030 pad field, boot button, UART pads and the spare buck only. Keep the BGA and everything heavy or fine-pitch on top. Double-sided means JLC **Standard PCBA** plus panelization (5 mm rails, 1 mm fiducials, mouse bites; DFM §4).
- No parts or copper inside the four 5 mm mounting-hole keepouts.

## 8. Open questions

1. **Fit:** on one 50 × 40 mm top side, OLED (27 × 27) + EC11 (~12 × 13 plus tabs) + BGA fan-out zone (~16 × 16) + USB-C (~9 × 8) only fit if the OLED module is stacked on headers over low parts, or the H2 corner hole/keepout is shared with the module's own mounting hole. Otherwise the board grows to about 60 × 40 mm (allowed: 50 × 40 is a target). Decide with the enclosure. **Resolved by PM, 2026-10-19:** keep 50 × 40 mm with the OLED on a header over parts no taller than 2.5 mm. **Tightened by PM (placement phase): ≤ 2.0 mm.**
2. **Enclosure:** not defined. It sets the mounting-hole positions, whether the holes are NPTH or plated (chassis GND), the board thickness (1.6 mm vs thinner), the USB-C overhang/recess, and the OLED window and encoder shaft height.
3. **BGA via 0.15/0.30** (§4.2): DFM to confirm the 10.7:1 aspect ratio, and **via covering** (JLC drops "Tented" with stackup + impedance; mask-covered vs plugged/epoxy-filled) before release.
4. **[decisions.md](decisions.md) still says "about 0.2 mm drill / 0.45 mm pad"** for the BGA via. **Resolved, 2026-10-19:** decisions.md now records the PM-locked 0.15 mm drill / 0.30 mm pad (PR #16).
5. **MCU refdes:** the staged rules assume `U1`. Confirm with the schematic.
6. **Default net class 0.15 vs 0.20 mm** (brief vs DFM) and **Power 0.30 vs 0.40 mm**: PM to pick; neither affects JLC compliance. **Resolved by PM, 2026-10-19:** Default 0.15 mm; Power 0.40 mm trunk / 0.30 mm branch.
7. **USB DP L8 escape** runs between N8/P8 and N9/P9 (32 kHz crystal balls). This needs a fan-out study before placement; the alternative is escaping DP via the column 6/7 channel past N6 (VBUS, DC).
8. Get the BGA land size from the NXP package drawing (assumed 0.30 mm NSMD) and re-check the channel math.

## 9. Validation done

- The staged rules file was parsed and checked with **kicad-cli 9.0.2** `pcb drc` on throwaway boards in `/tmp` (never committed). Results:
  - **Empty board** (50 × 40 R1 outline, 4 × M2 holes, 4-layer, the floors above): **0 violations, 0 unconnected**.
  - **Rule test board** (U1 = a stand-in 0.65 mm-pitch TFBGA footprint, 0.20/0.35 vias with a 0.10 mm track; superseded by the 0.15/0.30 re-test in §12).

## 10. Keep-under-OLED area (DECIDED: 50 × 40 mm, OLED on a header over low parts)

- **Area:** the OLED module outline (27.3 × 27.3 mm for the Winstar WEA012864D-03 class, about 27.3 × 27.8 mm for generic modules) on F.Fab/F.Courtyard, placed as in §13 (≈ x 6.5–33.8, y 4.3–32.1, over the MCU; the EC11 took the east edge). Inside it:
  - **Max component height on top: 2.0 mm** (PM, tightened from 2.5 mm). KiCad has no height DRC, so enforce it by hand: put each footprint's 3D model / `height` field in the BOM review, and add a `User.Comments` note "KEEP-UNDER-OLED: max 2.0 mm" on the outline. The `.kicad_dru` has a comment block for this; it is not machine-checked.
  - Allowed: 0402/0603 passives, SOT-23/SOT-23-6, 2016/3225 crystals, ABS07, the MAPBGA196. Not allowed: EC11, USB-C, SOIC-8 208 mil (up to 2.16 mm, so U4 sits outside the area), electrolytics, TC2030 (bottom anyway), test hooks. The SWPA4020 (L2) is **2.0 mm max: zero margin** at the 2.0 mm cap.
  - The module's own back-side parts, if any, must clear the tallest part underneath (2.5 mm standoff − 2.0 mm parts = 0.5 mm).
- **Header footprint:** 1 × 4, 2.54 mm pitch THT (VCC, GND, SCL, SDA; check the module's pin order). It sits on the module edge inside the area, ≥ 0.30 mm hole-to-copper.

## 11. Stack height (for the enclosure)

| Item | Value | Source |
|---|---|---|
| PCB | 1.6 mm nominal (1.44–1.76) | JLC04161H-3313, JLC ±10 % |
| Header standoff (male header plastic body) | 2.5 mm | Amtek 5PH1SDA25 "Pin Header 2.54 mm 1 Row H = 2.5 mm" (standard plastic) |
| OLED module (PCB + COG glass) | 2.37 mm (Winstar WEA012864D-03 / Raystar REA012864D-03, 27.3 × 27.3 × 2.37 mm); range 1.41–2.72 mm across 0.96" SSD1306 modules | Winstar / Raystar product pages; Midas MDOB128064WV-YBI datasheet (2.72 mm) |
| **Top of OLED above PCB top** | **≈ 4.9 mm** (2.5 + 2.37) | calculated |
| **Overall, PCB bottom to OLED top** | **≈ 6.5 mm** (1.6 + 2.5 + 2.37), plus bottom-side parts (TBD, ~1–2 mm for the boot button) | calculated |
| 1.3" 128 × 64 module (SH1106) | **TBD**: no datasheet thickness found. It is also about 35 × 33 mm, which doesn't fit the 27 × 27 zone | — |
| EC11 encoder body / shaft | **TBD**: depends on the shaft length variant | — |

Hobby "generic" 0.96" modules on 27.3 × 27.8 mm PCBs have no published thickness (**TBD**, measure a sample). The enclosure owner should design to the chosen module's datasheet.

## 12. Netlist import and re-validation

- **Done (placement phase):** the board was created as `hardware/schematic/TokenKey-RT.kicad_pcb` from the schematic and `TokenKey-RT.kicad_dru.staged` was renamed to `TokenKey-RT.kicad_dru`. See §13.
- Re-validated with kicad-cli 9.0.2 on throwaway boards in `/tmp` (never committed), with the Board Setup via floor at 0.30/0.15 and hole clearance 0.20:
  - Empty 50 × 40 board with 4 × M2: **0 violations**.
  - **Positive:** 0.15/0.30 vias at 0.65 mm pitch inside the U1 courtyard, with a 0.10 mm track centred between them (0.200 mm hole-to-track, 0.125 mm pad-to-track): **pass**.
  - **Negative:** the same track offset 0.03 mm towards one via (hole-to-track 0.170 mm) fails `hole_clearance` 0.20. Old 0.20/0.35 vias with a centred 0.10 track fail `hole_clearance` 0.175 < 0.20. A 0.30/0.15 via outside the courtyard is flagged (annular < 0.125, hole < 0.30, diameter < 0.60).


## 13. Board creation and placement (done; no routing)

All board edits were made through the KiCad MCP connector (create_board_from_schematic, replace_board_outline, add_layer, set_design_rules, create_netclass, place_component, batch_move_components, set_board_origin). Coordinates below are KiCad page coordinates in mm (x east, y south; the board spans 0–50 × 0–40). The aux/grid origin is the lower-left corner (0, 40). This section supersedes the §7 zoning where they differ.

**Board:** 50 × 40 mm, R1 corners, 4 copper layers (F.Cu, In1 "GND", In2 "PWR", B.Cu), tented vias. H1–H4 = `MountingHole_2.2mm_M2` at (3,3), (47,3), (3,37), (47,37). The 5 mm keepout is enforced by the footprint courtyard (r 2.45, F side), by the `.kicad_dru` rule "M2 mounting-hole copper keepout" (hole edge to copper ≥ 1.4 mm) and, for bottom parts, by placement. The connector has no rule-area tool, so there are no rule-area zones.

**Import:** 99 footprints, 54 named nets; every symbol has a footprint and none is missing. Pad nets match the kicad-cli netlist (0 mismatches). DNP parts are placed but stay unfitted: C3, C4, L1, R1, R2, U3 (spare buck), C50, R10, R11, U5 (PSRAM).

| Block | Placement |
|---|---|
| U1 MCU | Top, (17, 20), **rotation 0**: row A north, column 1 west, row P south, column 14 east. That matches the ball map: QSPI (L3/L4/N4/P3–P5) and DCDC (M1/M2/N1/N2) south-west, USB (L8/M8) south, SWD/UART/I2C/UI (E14/F12/G13/K14/L14/J11/K11/L11–M12) east. |
| USB | J1 HRO TYPE-C-31-M-12 top, (17, 36.3), on the south edge with the opening south and centred under the BGA. U6 USBLC6 at (17, 28.8) rotated 90° (flow-through: DP west, DN east), about 2.6 mm from the J1 pads. Corridor x ≈ 15.5–18.5 from row M to J1 is kept free of parts. CC resistors R12/R13 beside U6 at (14.5, 29.6) / (19.6, 29.6). VBUS caps C51/C26 east of J1. |
| DCDC | L2 SWPA4020 top, (9.15, 21.4), rotated 180°: the DCDC_LP pad faces M1/M2, about 1.5 mm from the BGA courtyard. Input caps C17/C20 (3V3) just south of L2 at N1/N2/L1/L2. Output caps C13 (22 µF), C11 and C12 north of L2, all on top. C5/R3 (PSWITCH) on the bottom west of the BGA. |
| BGA decoupling | 0.22 µF (C6–C10, C14–C16, C19, C21, C23, C24, C27, C43) plus C41 on the **bottom under the BGA** (rotation-0 grid at x 13.8/16.0/18.2/20.2). 100 nF C29/C31/C33/C34 bottom north and C36–C38 bottom east. Bulk on top near the edge balls: C18 22 µF north; C30/C32/C35/C39 4.7 µF east; C22 (HIGH_CAP) south-west. C40/C42/C25 on the bottom south. |
| QSPI flash | U4 SOIC-8 top, (3.5, 25), rotated 90°, in the west band **outside the OLED area** (SOIC-8 208 mil is up to 2.16 mm). R9 (SCLK 22 Ω) at (12.5, 26.4) next to the L4 escape; C49 and R8 at U4. |
| Crystals | Y1 24 MHz 3225 at (24.6, 23.2), rotated 90°, east of N11/P11; C44/C45 east of it. Y2 ABS07 at (21.2, 26.6), just south-east of N9/P9 with room for a guard ring and about 0.9 mm from the USB corridor; C46/C47 south of it. |
| Power in | U2 AP2112K top, (9, 35), C1 input and C2 output beside it, near the VBUS pins. The spare buck U3/L1/C3/C4/R1/R2 (DNP) is on the **bottom** south-east of J1. |
| UI | J2 OLED header top, (16.34, 6.3), rotated 90° (pins along x at y 6.3, pin 1 west). OLED module footprint assumed at about x 6.5–33.8, y 4.3–32.1; verify the header-to-edge offset on the module drawing. SW2 EC11 top, (39.4, 25), rotated 90°, on the east edge between the H2/H4 keepouts and **not under the OLED**. SW3/SW4 just south of it; D1/R21 north of it (visible). Pull-ups and filters R14–R20, C52, C53 in a column at x 31–32.5 under the OLED edge. |
| Boot / misc | Q1, R6, R22 (BOOT_MODE0 buffer) and R4, R5, C48 on top east of the BGA. R7 (BOOT_MODE0 10k to GND) on the bottom at (25, 15). |
| Bottom debug | J3 TC2030-NL at (39, 4), in the north-east, with the top side above it kept clear. TP1/TP2 (UART TX/RX), TP3 GND, TP4 POR_B and TP5 ONOFF at x 26.5–31.5, y 10–12.6. SW1 SW_BOOT at (47.6, 31), rotated 90°, near the east edge for a case pinhole. U5 PSRAM (DNP) with R10/R11/C50 in the bottom west band. |

**Heights under the OLED (top, max from datasheets):**

| Part | Max height |
|---|---|
| L2 SWPA4020S4R7MT | 2.0 mm (**zero margin**) |
| U1 MAPBGA196 | ≈ 1.4 mm |
| U6 SOT-23-6 | 1.45 mm |
| Q1 SOT-23 | ≈ 1.25 mm |
| Y1 3225 | ≈ 1.0 mm |
| Y2 ABS07 | ≈ 0.9 mm |
| 0603 caps | ≤ 0.95 mm |
| 0402 caps and resistors | ≤ 0.55 mm |

Outside the area: U4 SOIC-8 (west band; 0.2 mm from the assumed module edge), J1 USB-C body (starts at y 32.6, 0.5 mm south of the assumed module edge), the EC11, SW3/SW4, D1 and U2.

**DRC** (connector run_drc, KiCad 9.0.2, `.kicad_dru` active):

| Type | Count |
|---|---|
| Errors | 0 |
| Courtyard overlaps | 0 |
| Items out of board | 0 |
| Clearance errors | 0 |
| Footprint (library) errors | 0 |
| Warnings | 136: 81 silk_overlap, 49 silk_over_copper, 6 silk_edge_clearance |
| Unconnected pads (expected, not routed) | 272 |

The silk warnings are reference/value text overlaps; they get cleaned up at the silkscreen pass. J1's courtyard runs 0.45 mm past the south edge by design.

**Known gaps:**
- The connector has no stackup editor, so the JLC04161H-3313 dielectric table (§3) is not yet in the board file. Enter it in Board Setup → Physical Stackup.
- The connector's netclass call persisted the classes (Default 0.15/0.15, Power 0.40, USB_HS 0.155/0.20, BGA_Escape 0.10/0.10 with 0.30/0.15 vias) but not the net assignments. Net-to-class patterns were added to `TokenKey-RT.kicad_pro` (USB_D[PN] → USB_HS; 3V3, VBUS, VDD_*, DCDC_*, NVCC_PLL, BUCK_SW → Power).
- The connector's set_design_rules has no field for minimum annular ring, hole clearance or copper-to-edge, so the §4.1 floors (min clearance 0.09, annular 0.075, hole clearance 0.20, copper-to-edge 0.30) were written into the `TokenKey-RT.kicad_pro` design settings. The connector had also dropped the `sheets` list from that file; it was restored.
- `.kicad_dru` fix: the "USB keep-away from other signals" rule now skips pad-to-pad pairs. Once the USB_HS class was active it flagged the fixed 0.5 mm pin pitch of J1 and U6 (6 errors). It still applies to tracks and vias.
- No BGA fan-out vias yet (optional in the brief and skipped). Routing is the next phase.
