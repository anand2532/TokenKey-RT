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
| Min via diameter / hole | 0.35 / 0.20 mm | 0.25 / 0.15 min, 0.20 preferred hole | OK, **surcharge** (hole 0.2 with dia < 0.45) |
| Min through-hole | 0.20 mm | 0.15 mm | OK |
| Hole to hole | 0.25 mm | via 0.20 mm; **PTH pad 0.45 mm** | OK (pads raised to 0.45 by custom rule) |
| Hole clearance (hole to copper) | 0.20 mm | via hole to track 0.20 mm | OK outside BGA; **exception in BGA** (§4.2) |
| Copper to edge | 0.30 mm | 0.20 mm routed | OK |
| Silk to pad / min text | 0.15 mm / 1.0 mm high, 0.15 mm stroke | 0.15 mm / 1.0 mm | OK |
| Soldermask | 1:1 expansion, min web 0.10 mm | 1:1, bridge 0.10 mm (green) | OK |

### 4.2 BGA area (MCU courtyard, MAPBGA196 10 × 10 mm, 0.65 mm pitch)

**LOCKED (TokenKey PM, 2026-10-19):** BGA fan-out via **0.20 mm drill / 0.35 mm pad (0.075 mm annular ring)**, tracks and spaces **0.10 / 0.10 mm** between vias (the rule floor is 0.09 mm to absorb rounding).

- **JLC small-via surcharge:** a 0.2 mm hole with pad < 0.45 mm costs more. PM accepted it as a cost item. The 0.45 mm no-surcharge pad does not fit at 0.65 mm pitch (DFM §3.2).
- **Geometry:** dog-bone via in the diagonal gap. One 0.10 mm track between two adjacent vias leaves 0.10 mm copper clearance on each side (0.65 − 0.35 − 0.10 = 0.20 → 0.10 + 0.10). Only one track per channel.
- **Hole-to-track exception (needed for DRC):** JLC lists "via hole to track 0.2 mm". A centred 0.10 mm track sits **0.175 mm** from each via hole edge ((0.65 − 0.10)/2 − 0.10). The staged rule `BGA via hole to track exception` lowers `hole_clearance` to **0.17 mm on outer layers inside the U1 courtyard only**. Inner layers keep 0.20 mm (JLC inner-layer via hole to copper 0.2 mm), so the L2/L3 plane antipads stay compliant.
- **OPEN (TokenKey DFM):** DFM is still checking with JLC whether the 0.2 mm via-hole-to-track rule applies inside a BGA fan-out, where JLC explicitly allows 3 mil track/space. **Fallback:** JLC POFV via-in-pad (epoxy filled and capped, 0.20/0.35), which is a paid option on 4-layer boards. Escalate to PM before switching to POFV.
- Hole to hole between adjacent BGA vias: 0.65 − 0.20 = 0.45 mm (≥ 0.25 OK). Aspect ratio 1.6 / 0.2 = 8:1.
- Never put unfilled vias in BGA pads.

### 4.3 Outside the BGA

- Default via **0.6 / 0.3 mm** (0.15 mm ring, no surcharge). DFM proposes 0.5 / 0.3, which is also no-surcharge and acceptable if density needs it.
- Via annular ring ≥ **0.125 mm**, track ≥ 0.15 mm, clearance ≥ 0.15 mm.
- Through-hole component pads (EC11, USB-C shell tabs, headers): hole to copper ≥ 0.30 mm (JLC PTH-to-track 0.28 min / 0.35 recommended; inner PTH hole to copper 0.3); PTH annular ring ≥ 0.15 mm (JLC recommends 0.20); pad hole to hole ≥ 0.45 mm.

### 4.4 Net classes (to be set in `TokenKey-RT.kicad_pro` with the board PR)

| Net class | Track | Clearance | Via (dia/hole) | Diff gap | Pattern(s) | Notes |
|---|---|---|---|---|---|---|
| **Default** | 0.15 mm | 0.15 mm | 0.60 / 0.30 | — | (everything else) | DFM proposes 0.20 mm track as the cost floor; 0.15 is still standard at JLC |
| **Power** | 0.30 mm (0.40 preferred) | 0.20 mm | 0.60 / 0.30 | — | `VDD*`, `3V3`, `/3V3`, `VBUS`, `/VBUS`, `DCDC*`, `/DCDC*` | Pour where possible; check VBUS current |
| **USB_HS** | **0.155 mm** | 0.50 mm to other nets | none (L1 only) | **0.20 mm** | `/USB_D*`, `/USB*_D[PN]` | 90 Ω diff, JLC-calculator values (§5) |
| **BGA_Escape** | 0.10 mm (0.09 min) | 0.10 mm (0.09 min) | **0.35 / 0.20** | — | applied by area (U1 courtyard), not by net | Enforced by the custom rules in the `.kicad_dru` |

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
- **Recommendation: south long edge (y = 40), centred under the BGA (x ≈ 17 mm).** The USB balls (DN M8 / DP L8) escape south, so a south-edge connector gives a straight pair about 12–15 mm long with no bends around other parts. A short-edge connector would need the BGA rotated 90° or a pair routed around the QSPI or crystal zone.
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

1. **Fit:** on one 50 × 40 mm top side, OLED (27 × 27) + EC11 (~12 × 13 plus tabs) + BGA fan-out zone (~16 × 16) + USB-C (~9 × 8) only fit if the OLED module is stacked on headers over low parts, or the H2 corner hole/keepout is shared with the module's own mounting hole. Otherwise the board grows to about 60 × 40 mm (allowed: 50 × 40 is a target). Decide with the enclosure. **Resolved by PM, 2026-10-19:** keep 50 × 40 mm with the OLED on a header over parts no taller than 2.5 mm.
2. **Enclosure:** not defined. It sets the mounting-hole positions, whether the holes are NPTH or plated (chassis GND), the board thickness (1.6 mm vs thinner), the USB-C overhang/recess, and the OLED window and encoder shaft height.
3. **JLC via-hole-to-track in BGA fan-out** (§4.2): DFM confirming with JLC. If it is enforced, use POFV (paid on 4 L) or quote the 6-layer JLC06161H-3313 (free POFV) for comparison.
4. **[decisions.md](decisions.md) still says "about 0.2 mm drill / 0.45 mm pad"** for the BGA via. The PM lock is 0.20 / 0.35. That row should be updated by PM.
5. **MCU refdes:** the staged rules assume `U1`. Confirm with the schematic.
6. **Default net class 0.15 vs 0.20 mm** (brief vs DFM) and **Power 0.30 vs 0.40 mm**: PM to pick; neither affects JLC compliance. **Resolved by PM, 2026-10-19:** Default 0.15 mm; Power 0.40 mm trunk / 0.30 mm branch.
7. **USB DP L8 escape** runs between N8/P8 and N9/P9 (32 kHz crystal balls). This needs a fan-out study before placement; the alternative is escaping DP via the column 6/7 channel past N6 (VBUS, DC).
8. Get the BGA land size from the NXP package drawing (assumed 0.30 mm NSMD) and re-check the channel math.

## 9. Validation done

- The staged rules file was parsed and checked with **kicad-cli 9.0.2** `pcb drc` on throwaway boards in `/tmp` (never committed). Results:
  - **Empty board** (50 × 40 R1 outline, 4 × M2 holes, 4-layer, the floors above): **0 violations, 0 unconnected**.
  - **Rule test board** (U1 = a stand-in 0.65 mm-pitch TFBGA footprint, 0.20/0.35 vias at 0.65 mm with a 0.10 mm track between them; a 0.20/0.35 via outside the courtyard): the BGA vias and the track between them pass. With the hole-to-track exception removed, they fail `hole_clearance` 0.175 < 0.20 as expected. The out-of-courtyard 0.35/0.20 via is correctly flagged (annular 0.075 < 0.125, hole < 0.30, diameter < 0.60).
