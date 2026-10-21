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
| Min track width | **0.10 mm** (raised from 0.09, layout-minimums) | 0.09 mm (3 mil OK in BGA fan-out) | OK, 0.01 mm margin over JLC |
| Min clearance | **0.10 mm** (raised from 0.09, layout-minimums) | 0.09 mm | OK, 0.01 mm margin over JLC |
| Min via annular ring | 0.075 mm | via dia = hole + 0.10 min / + 0.15 preferred | OK (preferred value) |
| Min via diameter / hole | 0.30 / 0.15 mm | 0.25 / 0.15 min, 0.20 preferred hole | OK, **surcharge** (0.15 hole at any diameter) |
| Min through-hole | 0.15 mm | 0.15 mm | OK (at JLC minimum) |
| Hole to hole | 0.25 mm | via 0.20 mm; **PTH pad 0.45 mm** | OK (pads raised to 0.45 by custom rule) |
| Hole clearance (hole to copper) | 0.20 mm | via hole to track 0.20 mm | OK everywhere, **no exception** (§4.2) |
| Copper to edge | 0.30 mm | 0.20 mm routed | OK |
| Silk to pad / min text | 0.15 mm / 1.0 mm high, 0.15 mm stroke | 0.15 mm / 1.0 mm | OK |
| Soldermask | 1:1 expansion, min web 0.10 mm | 1:1, bridge 0.10 mm (green) | OK |

### 4.2 BGA area (MCU courtyard, MAPBGA196 10 × 10 mm, 0.65 mm pitch)

**LOCKED (TokenKey PM, 2026-10-19, supersedes the earlier 0.20/0.35 lock):** BGA fan-out via **0.15 mm drill / 0.30 mm pad (0.075 mm annular ring)**, tracks and spaces **0.10 / 0.10 mm** between vias. The rule floor is also 0.10 mm (raised from 0.09 on the layout-minimums branch), which keeps a margin over JLC's 0.09 mm minimum. TokenKey DFM confirmed that JLC's "Via hole to Track 0.2 mm" rule also applies inside the BGA fan-out, which the 0.20/0.35 via broke (0.175 mm).

- **Geometry (0.65 mm pitch, dog-bone via in the diagonal gap, one centred 0.10 mm track per channel):**
  - Via hole edge to track: (0.65 − 0.10)/2 − 0.075 = **0.200 mm**, which meets JLC's 0.2 mm rule with no exception.
  - Via pad to track: (0.65 − 0.10)/2 − 0.15 = **0.125 mm** (≥ 0.10 floor).
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
| **BGA_Escape** | 0.10 mm (0.10 min) | 0.10 mm (0.10 min) | **0.30 / 0.15** | — | applied by area (U1 courtyard), not by net | **PM-locked** (§4.2). Enforced by the custom rules in the `.kicad_dru` |

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

**Routing result (#58, L1 only, no vias).** Both nets: 0.10 mm neck inside the U1 courtyard (L8/M8 escape through the column 6/7 and 8/9 channels), then 0.155 mm fly-by through the USBLC6 pins (DP 6→1, DN 4→3) into J1 A6/A7. USB_DP = USB_DN = 11.234 mm (incl. 0.10 neck), skew 0.000 mm (DN carries two small meanders at y ≈ 26 to match). Clearance to other signals ≥ 0.5 mm, 0 clearance errors. **Open deviations (need PM decision):** (1) J1 B6 (DP) and B7 (DN) are not tied: the A/B pins interleave (B7 DN–A6 DP–A7 DN–B6 DP), so the DN tie can't be made on L1 without a via, and a DP tie passes < 0.5 mm from A8/A5. (2) The pair can't hold 0.20 mm gap: the BGA channels are 1.3 mm apart and the USBLC6 flow-through pins 1.9 mm apart, so DRC reports 8 × diff_pair_gap_out_of_range and 1 × uncoupled length (11.25 mm vs 3 mm). These need a rule exception or a footprint/placement change.

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
| DCDC | M1/M2, N1/N2 | West | **TDK VLS3015CX-4R7M-1** (3.0 × 3.0 × 1.5 mm max, Isat 1.37 A; alternate Sunlord SWPA3015S4R7MT; replaces the 2.0 mm SWPA4020 per schematic issue #24) in a reserved 4 × 4 mm area on top just west of balls M1–N2 (≈ x 8–11, y 18–22), with a tight loop: DCDC_LP/LN, input cap and output cap all within about 3 mm, on solid L2, and ≥ 1 mm from the USB pair |
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

- **Area:** the OLED module outline (27.3 × 27.3 mm for the Winstar WEA012864D-03 class, about 27.3 × 27.8 mm for generic modules) placed as in §13 over the MCU (the EC11 took the east edge). **Corrected to the real HS96L03W2C03 drawing (layout follow-up), see §10.1.** Inside it:
  - **Max component height on top: 2.0 mm** (PM, tightened from 2.5 mm). KiCad has no height DRC, so enforce it by hand: put each footprint's 3D model / `height` field in the BOM review, and add a `User.Comments` note "KEEP-UNDER-OLED: max 2.0 mm" on the outline. The `.kicad_dru` has a comment block for this; it is not machine-checked.
  - Allowed: 0402/0603 passives, SOT-23/SOT-23-6, 2016/3225 crystals, ABS07, the MAPBGA196. Not allowed: EC11, USB-C, SOIC-8 208 mil (up to 2.16 mm, so U4 sits outside the area), electrolytics, TC2030 (bottom anyway), test hooks. L2 becomes the **TDK VLS3015CX-4R7M-1 at 1.5 mm max** (alternate **SWPA3015S4R7MT**), so the under-OLED margin at the 2.0 mm cap is now **0.5 mm**. **Done (issue #31):** L2 is now the `TokenKey:L_3.0x3.0mm_TDK_VLS3015CX` footprint on the board.
  - **OLED header (DECIDED, PM, issue #31): 3.0 mm plastic header**, up from the 2.5 mm standard. **Why:** the HS96L03W2C03 side view shows a 1.0 mm back-side feature. Schematic located it at about **y +9.3…+12.3 mm from J2 pin 1** (board y 14.3–17.3 with J2 at y 5.0, drawn as a band on User.Comments), but its **x position is unknown**. PM's rule is that an undetermined location means 3.0 mm, which gives a real gap under the module of 3.0 − 1.0 = **2.0 mm**, meeting the 2.0 mm cap. **The block position is unverified: measure a real module before going to a lower header.** The band y 14.3–17.3 (full module width, x 6.5–33.8) is where tall parts are **riskiest**. Parts there today: U1 rows A–D (1.4 mm), C13 0603 (0.95), C11/C12/C30/C32/C48, R4/R5/R14/R15/R22 0402 (≤ 0.55). All are ≤ 1.4 mm.
  - **J2 header (PM): 1 × 4, 2.54 mm male header with 3.0 mm plastic; the OLED is soldered directly onto it.** Header part per Schematic #47: **HCTL PZ254-1-04-Z-C** (LCSC C5156431). A socket plus pins would stack to about 8.65 mm, so the socket was dropped. **Board updated in #43 after #47:** J2 is `Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical`, value `Header 1x04 P2.54 H3.0 (OLED)`, MPN/LCSC fields as in the schematic, pin 1 at (16.34, 5.0), rotation 90°. The footprint (1.7 mm pads, 1.0 mm drill) is unchanged, so the OLED drawings, keep-under area, USB-C clearance and H1/H2 keepouts are unchanged. **3D model:** the generic KiCad `PinHeader_1x04_P2.54mm_Vertical.step` has 2.5 mm plastic, so the 3D view and STEP export understate the 3.0 mm header by 0.5 mm. A z offset can't stretch the body, so the model was left as is. For the enclosure, use 3.0 mm plastic (§11), or swap in an HCTL PZ254 model when one is available.
### 10.1 HS96L03W2C03 outline, mapped onto the board (layout follow-up)

Drawing coordinates are from header pin 1 (GND, the square pad). +x runs toward pin 4 and +y toward the glass, the side the module overhangs. J2 pin 1 sits at board **(16.34, 5.0)** (issue #31; it was 5.5 in PR #23). J2 is at rotation 90°, with pins along +x and the glass toward +y (south), so board = (16.34 + x, 5.0 + y).

| Feature | Drawing (from pin 1) | Board (mm) |
|---|---|---|
| Module PCB | x −9.84…+17.46, y −1.44…+26.36 (27.30 × 27.80) | **x 6.50–33.80, y 3.56–31.36** |
| Glass (24.74 × 16.90) | x −8.60…+16.14, y +3.43…+20.33 | x 7.74–32.48, y 8.43–25.33 |
| Active area (21.744 × 10.864; x assumed centred, per decisions.md) | x −7.06…+14.68, y +4.93…+15.79 | x 9.28–31.02, y 9.93–20.79 |
| Mounting holes Ø2.5, pad Ø3.0 (2.0 mm in from the PCB edges, 23.3 × 23.8 pitch) | — | (8.50, 5.56), (31.80, 5.56), (8.50, 29.36), (31.80, 29.36) |
| 1.0 mm back-side block (x unknown) | y +9.3…+12.3 | y 14.3–17.3 band |
| FPC bend (14.50 wide, far edge) | at y +26.36, x not dimensioned | at y 31.36 |
| Module thickness | 2.65 mm nominal (PCB + glass). The 1.0 mm back-side block sits inside the 3.0 mm header gap (2.0 mm real gap); stack per §11 | — |

- The placement assumed x 6.5–33.8, y 4.3–32.1 with J2 at y 6.3. With the real offsets and J2 at y 6.3, the module PCB would have spanned y 4.86–32.66, which runs 0.06 mm over the J1 USB-C body (body starts at y 32.6, about 3.2 mm tall, so it collides with the module underside at 2.5 mm). **J2 moved 0.8 mm north, from (16.34, 6.3) to (16.34, 5.5)**, which left 0.74 mm. **Issue #31 (PM enclosure review, target ≥ 1.0 mm): J2 moved to (16.34, 5.0).** The module PCB now ends at y 31.36, **1.24 mm clear of the J1 USB-C body** (body starts at y 32.6). J1's courtyard still overlaps the module outline in plan view; the body does not. **Open:** the FPC bend at the far edge (14.5 mm wide) overlaps J1 in x if it is centred, x ≈ 12.9–27.4 against the J1 body at x 12.5–21.5. If the bend protrudes more than about 1.2 mm past the module PCB edge, it reaches the J1 body. Measure it on a real module.
- The module stays fully inside the 50 × 40 board (**no overhang**): 6.5 mm from the west edge, **3.56 mm** from the north edge, 16.2 mm from the east edge, 8.64 mm from the south edge. J2's pads (y 4.15–5.85, x 15.5–24.8) are far from the H1/H2 keepouts (x ≤ 5.5 / ≥ 44.5).
- EC11 (SW2): courtyard 0.955 mm and body 2.24 mm east of the module PCB edge (x 33.80), so the module, including a 1.0 mm back-side allowance, does not sit over the encoder.
- U4: courtyard **0.505 mm** and body 0.75 mm outside the module PCB west edge (x 6.50), after the move to (3.05, 25). U4 is 5.6 mm from J1.
- On the board: module PCB outline on F.Fab and User.Comments, glass, active area and the four Ø2.5 holes (with Ø3.0 pads) on User.Drawings, the back-side block band on User.Comments, and a rule area `OLED_KEEP_UNDER` (F.Cu, no keepout flags, marker only; KiCad has no height DRC) on the module PCB outline.
- Top parts under the module PCB, all within the 2.0 mm cap (2.0 mm real gap with the 3.0 mm header): U1 (1.4), U6 (1.45), Q1 (1.25), Y1 (1.0), Y2 (0.9), 0603 C2/C13/C18 (≤ 0.95; C2 straddles the south edge), 0402 C11/C12/C17/C20/C22/C30/C32/C35/C39/C44–C48/C52/C53, R4–R6/R9/R12–R20/R22 (≤ 0.55), J2 itself (header), and **L2 VLS3015CX at 1.5 mm (0.5 mm margin)**. The tallest part under the module is L2 at 1.5 mm.
- **Header footprint:** 1 × 4, 2.54 mm pitch THT (VCC, GND, SCL, SDA; check the module's pin order). It sits on the module edge inside the area, ≥ 0.30 mm hole-to-copper.

## 11. Stack height (for the enclosure)

| Item | Value | Source |
|---|---|---|
| PCB | 1.6 mm nominal (1.44–1.76) | JLC04161H-3313, JLC ±10 % |
| Header standoff (J2: 1 × 4 2.54 mm male header, 3.0 mm plastic, OLED soldered directly) | **3.0 mm** (DECIDED, PM; was 2.5 mm) | The 1.0 mm module back-side block at an unknown x sits inside the 3.0 mm gap, leaving a 2.0 mm real gap (§10). HCTL PZ254-1-04-Z-C (#47). J2 updated on the board in #43; the generic 3D model shows 2.5 mm plastic (§10). Socket + pins (≈ 8.65 mm) dropped |
| OLED module (PCB + COG glass) | 2.37 mm (Winstar WEA012864D-03 / Raystar REA012864D-03, 27.3 × 27.3 × 2.37 mm); range 1.41–2.72 mm across 0.96" SSD1306 modules | Winstar / Raystar product pages; Midas MDOB128064WV-YBI datasheet (2.72 mm) |
| HS96L03W2C03 module (chosen part) | 2.65 mm nominal (PCB + glass, above the header plastic). The 1.0 mm back-side block hangs into the 3.0 mm header gap, so it adds no stack height (earlier 3.6 mm envelope superseded) | TokenKey Schematic, from the HS96L03W2C03 drawing |
| **Top of OLED above PCB top (enclosure number)** | **≈ 5.65 mm** (3.0 mm header plastic + 2.65 mm module; the 1.0 mm back-side block is inside the 3.0 mm gap, leaving 2.0 mm real gap) | calculated (PM, #43; supersedes 6.6 mm) |
| **Overall, PCB bottom to OLED top** | **≈ 7.25 mm** (1.6 + 3.0 + 2.65), plus bottom-side parts (TBD, ~1–2 mm for the boot button) | calculated (PM, #43; supersedes 8.2 mm) |
| Earlier estimate (Winstar-class module, 2.37 mm) | 4.9 mm above PCB top / 6.5 mm overall | superseded |
| 1.3" 128 × 64 module (SH1106) | **TBD**: no datasheet thickness found. It is also about 35 × 33 mm, which doesn't fit the 27 × 27 zone | — |
| EC11 encoder body / shaft | **EC11E18244A5, 20 mm shaft** (PM, issue #45; the 15 mm swap from issue #31 is cancelled because knob engagement would be too short). Schematic keeps the same footprint (`RotaryEncoder_Alps_EC11E-Switch_Vertical_H20mm`), so no board change | PM / Schematic |

Hobby "generic" 0.96" modules on 27.3 × 27.8 mm PCBs have no published thickness (**TBD**, measure a sample). The enclosure owner should design to the chosen module's datasheet.

## 12. Netlist import and re-validation

- **Done (placement phase):** the board was created as `hardware/schematic/TokenKey-RT.kicad_pcb` from the schematic and `TokenKey-RT.kicad_dru.staged` was renamed to `TokenKey-RT.kicad_dru`. See §13.
- Re-validated with kicad-cli 9.0.2 on throwaway boards in `/tmp` (never committed), with the Board Setup via floor at 0.30/0.15 and hole clearance 0.20:
  - Empty 50 × 40 board with 4 × M2: **0 violations**.
  - **Positive:** 0.15/0.30 vias at 0.65 mm pitch inside the U1 courtyard, with a 0.10 mm track centred between them (0.200 mm hole-to-track, 0.125 mm pad-to-track): **pass**.
  - **Negative:** the same track offset 0.03 mm towards one via (hole-to-track 0.170 mm) fails `hole_clearance` 0.20. Old 0.20/0.35 vias with a centred 0.10 track fail `hole_clearance` 0.175 < 0.20. A 0.30/0.15 via outside the courtyard is flagged (annular < 0.125, hole < 0.30, diameter < 0.60).


## 13. Board creation and placement (done; no routing)

All board edits were made through the KiCad MCP connector (create_board_from_schematic, replace_board_outline, add_layer, set_design_rules, create_netclass, place_component, batch_move_components, set_board_origin). Coordinates below are KiCad page coordinates in mm (x east, y south; the board spans 0–50 × 0–40). The aux/grid origin is the lower-left corner (0, 40). This section supersedes the §7 zoning where they differ.

**Board:** 50 × 40 mm, R1 corners, 4 copper layers (F.Cu, In1 "GND", In2 "PWR", B.Cu), tented vias. H1–H4 = `MountingHole_2.2mm_M2` at (3,3), (47,3), (3,37), (47,37). **5 mm keepout rule areas (PR #23 review, MUST-FIX):** each H footprint carries a rule area `Hn M2 keepout 5mm`, a circle of r 2.5 mm on all copper layers, that disallows tracks, vias, pads, copper pours and footprints. It is an annulus with an r 1.2 mm cut-out around the 2.2 mm NPTH, so the hole's own pad isn't flagged; the parent footprint is exempt. They sit inside the footprint because a board-level keepout flags the mounting hole itself. KiCad therefore reports 4 `lib_footprint_mismatch` warnings (local override of the library footprint). Negative test on a throwaway copy: a via, an In2 track and a bottom 0402 placed inside were all flagged `items_not_allowed`. No part courtyard or copper sits inside them (DRC 0 errors). The `.kicad_dru` rule "M2 mounting-hole copper keepout" (hole edge to copper ≥ 1.4 mm) stays as a second check.

**Import:** 99 footprints, 54 named nets; every symbol has a footprint and none is missing. Pad nets match the kicad-cli netlist (0 mismatches). DNP parts are placed but stay unfitted: C3, C4, L1, R1, R2, U3 (spare buck), C50, R10, R11, U5 (PSRAM).

| Block | Placement |
|---|---|
| U1 MCU | Top, (17, 20), **rotation 0**: row A north, column 1 west, row P south, column 14 east. That matches the ball map: QSPI (L3/L4/N4/P3–P5) and DCDC (M1/M2/N1/N2) south-west, USB (L8/M8) south, SWD/UART/I2C/UI (E14/F12/G13/K14/L14/J11/K11/L11–M12) east. |
| USB | J1 HRO TYPE-C-31-M-12 top, (17, 36.3), on the south edge with the opening south and centred under the BGA. U6 USBLC6 at (17, 28.8) rotated 90° (flow-through: DP west, DN east), about 2.6 mm from the J1 pads. Corridor x ≈ 15.5–18.5 from row M to J1 is kept free of parts. CC resistors R12/R13 beside U6 at (14.5, 29.6) / (19.6, 29.6). VBUS caps C51/C26 east of J1. |
| DCDC | L2 **TDK VLS3015CX-4R7M-1** (`TokenKey:L_3.0x3.0mm_TDK_VLS3015CX`, issue #31) top, (9.15, 21.4), **rotated 180°**, centred in the 4.0 × 4.0 mm reserved area (x 7.15–11.15, y 19.4–23.4, User.Comments). The courtyard is x 7.255–11.045, y 19.505–23.295. Of the four rotations, 180° puts the DCDC_LP pad (pad 1, centre (10.15, 21.4)) closest to ball M1 (12.775, 22.925): 3.04 mm centre to centre, 2.13 mm from pad edge to ball centre. 90° ties on edge distance at 2.13 but is 3.66 mm centre to centre. The VDD_SOC pad faces the output caps. The library footprint has no `(attr smd)`, so the board keeps `smd` for the position file, at the cost of one `lib_footprint_mismatch` warning; Schematic should add `attr smd` to the library footprint. the DCDC_LP pad faces M1/M2, about 1.5 mm from the BGA courtyard. Input caps C17/C20 (3V3) just south of L2 at N1/N2/L1/L2. Output caps C13 (22 µF), C11 and C12 north of L2, all on top. C5/R3 (PSWITCH) on the bottom west of the BGA. |
| BGA decoupling | 0.22 µF (C6–C10, C14–C16, C19, C21, C23, C24, C27, C43) plus C41 on the **bottom under the BGA** (rotation-0 grid at x 13.8/16.0/18.2/20.2). 100 nF C29/C31/C33/C34 bottom north and C36–C38 bottom east. Bulk on top near the edge balls: C18 22 µF north; C30/C32/C35/C39 4.7 µF east; C22 (HIGH_CAP) south-west. C40/C42/C25 on the bottom south. |
| QSPI flash | U4 SOIC-8 top, **(3.05, 25)** (moved 0.45 mm west in the follow-up; courtyard 0.505 mm outside the OLED module PCB, 0.105 mm in from the west board edge), rotated 90°, in the west band **outside the OLED area** (SOIC-8 208 mil is up to 2.16 mm). R9 (SCLK 22 Ω) at (12.5, 26.4) next to the L4 escape; C49 and R8 at U4. |
| Crystals | Y1 24 MHz 3225 at (24.6, 23.2), rotated 90°, east of N11/P11; C44/C45 east of it. Y2 ABS07 at (21.2, 26.6), just south-east of N9/P9 with room for a guard ring and about 0.9 mm from the USB corridor; C46/C47 south of it. |
| Power in | U2 AP2112K top, (9, 35), C1 input and C2 output beside it, near the VBUS pins. The spare buck U3/L1/C3/C4/R1/R2 (DNP) is on the **bottom** south-east of J1. |
| UI | J2 OLED header top, **(16.34, 5.0)** (from y 6.3, then 5.5 in PR #23, then 5.0 in issue #31), rotated 90° (pins along x, pin 1 west); 3.0 mm header. OLED module PCB x 6.50–33.80, y 3.56–31.36 from the HS96L03W2C03 drawing (§10.1). SW2 EC11 top, (39.4, 25), rotated 90°, on the east edge between the H2/H4 keepouts and **not under the OLED**. SW3/SW4 just south of it; D1/R21 north of it (visible). Pull-ups and filters R14–R20, C52, C53 in a column at x 31–32.5 under the OLED edge. |
| Boot / misc | Q1, R6, R22 (BOOT_MODE0 buffer) and R4, R5, C48 on top east of the BGA. R7 (BOOT_MODE0 10k to GND) on the bottom at (25, 15). |
| Bottom debug | J3 TC2030-NL at (39, 4), in the north-east, with the top side above it kept clear. TP1/TP2 (UART TX/RX), TP3 GND, TP4 POR_B and TP5 ONOFF at x 26.5–31.5, y 10–12.6. SW1 SW_BOOT at (47.6, 31), rotated 90°, near the east edge for a case pinhole. U5 PSRAM (DNP) with R10/R11/C50 in the bottom west band. |

**Heights under the OLED (top, max from datasheets):**

| Part | Max height |
|---|---|
| L2 VLS3015CX-4R7M-1 (issue #31; was SWPA4020 at 2.0 mm) | 1.5 mm (0.5 mm margin) |
| U1 MAPBGA196 | ≈ 1.4 mm |
| U6 SOT-23-6 | 1.45 mm |
| Q1 SOT-23 | ≈ 1.25 mm |
| Y1 3225 | ≈ 1.0 mm |
| Y2 ABS07 | ≈ 0.9 mm |
| 0603 caps | ≤ 0.95 mm |
| 0402 caps and resistors | ≤ 0.55 mm |

Outside the area: U4 SOIC-8 (west band; courtyard 0.505 mm, body 0.75 mm from the real module edge), J1 USB-C body (starts at y 32.6, **1.24 mm** south of the real module edge with J2 at y 5.0), the EC11, SW3/SW4, D1 and U2.

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

**Follow-up (PR #23 review) DRC**, run through the connector run_drc and kicad-cli 9.0.2:

| Type | Count |
|---|---|
| Errors | **0** |
| silk_overlap / silk_over_copper | **0** (was 81 / 49) |
| silk_edge_clearance | 2: J1's own footprint silk where it crosses the board edge (the connector overhangs) |
| lib_footprint_mismatch | 4: H1–H4, which carry the local keepout rule areas |
| lib_footprint_mismatch (issue #31) | L2: **cleared in #43**. #47 added `attr smd` to the library footprint and L2 was updated from the library (4 in total, H1–H4) |
| Unconnected pads (not routed) | 272 |

Silk pass: the reference designators were moved through the connector's move_footprint_text, placed by a collision search on a throwaway copy against pads (+0.12 mm), footprint silk and other references, ≥ 0.3 mm from the edge and ≤ 1.8 mm from their part. 24 references with no free spot at 1.0 mm text were hidden on silk; they stay on F.Fab/B.Fab for the assembly drawing: C5, C8–C11, C15–C17, C19, C21, C22, C24, C32, C33, C35, C39, C41, C44, C48 (dense BGA, decoupling and crystal clusters), R13, R16, R17, R19 and R2 (DNP).

**Board flags:** DNP set on C3, C4, C50, L1, R1, R2, R10, R11, U3, U5, matching the schematic. J3 and TP1–TP5 are excluded from BOM and position files. **Issue #38:** the schematic now has J3/TP1–TP5 at `in_bom no`. The schematic-to-board update (issue #43) confirmed the board flags match: excluded from BOM and from position files. H1–H4 are marked board-only (`not_in_schematic`) so schematic parity doesn't flag them as extra footprints. **L2 lib mismatch: cleared (#43).** #47 added `attr smd` to the library `TokenKey:L_3.0x3.0mm_TDK_VLS3015CX`, and L2 was updated from the library with the same position (9.15, 21.4), rotation 180° and nets. Schematic parity is clean.

**Known gaps:**
- **Done (follow-up, PM-approved hand edit):** the JLC04161H-3313 stackup is in the `.kicad_pcb` `(setup (stackup …))`: F.Mask 0.015 (Er 3.8) / F.Cu 0.035 / prepreg 3313 0.0994 (Er 4.1) / In1.Cu GND 0.0152 / core 1.265 (Er 4.6) / In2.Cu PWR 0.0152 / prepreg 3313 0.0994 (Er 4.1) / B.Cu 0.035 / B.Mask 0.015, ENIG, silk and paste both sides. Total 1.564 mm copper + dielectric, 1.594 mm with mask (board thickness 1.6). The core is kept at the JLC table value; it does not affect the L1/L2 impedance.
- The connector's netclass call persisted the classes (Default 0.15/0.15, Power 0.40, USB_HS 0.155/0.20, BGA_Escape 0.10/0.10 with 0.30/0.15 vias) but not the net assignments. Net-to-class patterns were added to `TokenKey-RT.kicad_pro` (USB_D[PN] → USB_HS; 3V3, VBUS, VDD_*, DCDC_*, NVCC_PLL, BUCK_SW → Power).
- The connector's set_design_rules has no field for minimum annular ring, hole clearance or copper-to-edge, so the §4.1 floors (min clearance 0.10, raised from 0.09 on layout-minimums; min track 0.10; annular 0.075, hole clearance 0.20, copper-to-edge 0.30) were written into the `TokenKey-RT.kicad_pro` design settings. The connector had also dropped the `sheets` list from that file; it was restored.
- `.kicad_dru` fix: the "USB keep-away from other signals" rule now skips pad-to-pad pairs. Once the USB_HS class was active it flagged the fixed 0.5 mm pin pitch of J1 and U6 (6 errors). It still applies to tracks and vias.
- No BGA fan-out vias yet (optional in the brief and skipped). Routing is the next phase.
