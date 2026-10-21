# fab: TokenKey RT fabrication and assembly package

Fab notes for JLCPCB (PCB + Standard PCBA). Detailed derivations are in [stackup.md](stackup.md).
**No ordering:** per Anand (via TokenKey PM, 2026-10-19) there is no fab, assembly or parts spend until the PoC gates in `docs/poc/` pass. The pipeline only generates files.

## 1. How to run the pipeline

Needs `kicad-cli` 9.x (tested with 9.0.2), Python 3 and **KiKit 1.8.1** (pinned in `fab/Makefile`; `make -C fab kikit` installs it into a `--system-site-packages` venv at `/workspace/.venv-kikit`, override with `VENV=` or `KIKIT=`).

```sh
make -C fab            # dry run: every output is attempted, ERC/DRC gates are reported but do not stop it
make -C fab release    # strict: exits non-zero on any failed step, ERC error, DRC error, unconnected item or parity issue
make -C fab panel      # same full run (the panel is part of every run); outputs in out/<sha>/panel/
make -C fab clean
```

Output goes to `fab/out/<git-short-sha>[-dirty]/` (gitignored, regenerate any time):

| Path | Contents |
|---|---|
| `gerbers/` | F.Cu, In1.Cu (GND), In2.Cu (PWR), B.Cu, F/B.Mask, F/B.Paste, F/B.Silkscreen, Edge.Cuts with Protel extensions (.gtl/.g1/.g2/.gbl/.gts/.gbs/.gtp/.gbp/.gto/.gbo/.gm1), gerber job file; Excellon drill in mm with PTH/NPTH split plus drill maps; drill-file origin |
| `TokenKey-RT_gerbers_drill_<sha>.zip` | Upload zip for the PCB order |
| `pcba/TokenKey-RT_BOM_jlc.csv` | JLC BOM: Comment, Designator, Footprint, LCSC Part # (from the `LCSC` symbol field, DNP and BOM-excluded parts removed) |
| `pcba/TokenKey-RT_CPL_jlc.csv` | JLC CPL: Designator, Mid X, Mid Y, Layer (Top/Bottom), Rotation |
| `docs/assembly-top.pdf`, `docs/assembly-bottom.pdf` (mirrored) | F.Fab/B.Fab + Edge.Cuts with refdes, pad outlines, DNP crossed out |
| `TokenKey-RT.ipc356` | IPC-D-356 netlist for electrical test |
| `hand_assembly_bom.csv` | **Hand-assembly BOM, kept out of the JLC PCBA BOM**: `Module_LCSC`/`Module_MPN` symbol fields (OLED HS96L03W2C03, C5248080, on J2) plus `fab/hand_assembly.csv` (knob, mechanical) |
| `panel/TokenKey-RT-panel.kicad_pcb` | KiKit 2×2 panel (see §9) |
| `TokenKey-RT_panel_gerbers_drill_<sha>.zip` | Panel gerbers + drill for JLC |
| `panel/jlc/bom.csv`, `panel/jlc/pos.csv` | Panel BOM/CPL (JLC columns, LCSC field) |
| `reports/` | `summary.md`, `erc.json`, `drc.json` (with schematic parity), `missing-lcsc.md`, raw pos/BOM CSVs, per-step logs |

Scripts: `scripts/make_fab.sh` (driver), `scripts/hand_assembly.py` (hand-assembly BOM), `scripts/jlc_convert.py` (CPL/BOM conversion, missing-LCSC report), `scripts/gate_summary.py` (ERC/DRC counts by type).

## 2. Stackup: JLC04161H-3313, 4 layers, 1.6 mm (±10%)

| # | Layer | Function | Copper / material | Thickness | Er |
|---|---|---|---|---|---|
| L1 | F.Cu | Signal (BGA, USB pair, most parts) | 1 oz finished | 0.035 mm | |
| | Prepreg | | 3313 ×1 | 0.0994 mm | 4.1 |
| L2 | In1.Cu | Solid GND | 0.5 oz | 0.0152 mm | |
| | Core | | FR-4 | 1.265 mm | 4.6 |
| L3 | In2.Cu | PWR | 0.5 oz | 0.0152 mm | |
| | Prepreg | | 3313 ×1 | 0.0994 mm | 4.1 |
| L4 | B.Cu | Signal (BGA escape, decoupling, bottom parts) | 1 oz finished | 0.035 mm | |

Soldermask LPI, Er 3.8. Order with "Specify stackup = JLC04161H-3313" and impedance control on.

## 3. Impedance (±10%, JLC impedance calculator on JLC04161H-3313)

| Net class | Layer / reference | Geometry | Target |
|---|---|---|---|
| USB_HS (USB_DP/USB_DN) | L1 over L2 GND | 0.155 mm width / 0.20 mm gap | 90 Ω differential (calc 90.7 Ω) |
| 50 Ω single-ended | L1 over L2 GND | 0.151 mm | 50 Ω |

Route the USB pair on L1 with no layer changes and a continuous L2 reference.

## 4. Net classes and design rules

| Net class | Track / clearance | Via (pad / drill) |
|---|---|---|
| Default | 0.15 / 0.15 mm | 0.60 / 0.30 mm (standard via) |
| Power | 0.40 mm trunk / 0.30 mm branch | 0.60 / 0.30 mm |
| BGA (rule area on U1) | 0.10 / 0.10 mm escape | **0.30 / 0.15 mm** |
| USB_HS | 0.155 mm, 0.20 mm gap | none on the pair |

BGA via check at 0.65 mm pitch: hole-to-track (0.65 − 0.15)/2 − 0.05 = 0.200 mm (meets JLC "via hole to track 0.2 mm"), pad-to-track 0.125 mm, via-pad to ball-pad ≈ 0.16 mm. Small-via surcharge accepted (PM).

### Via aspect ratio (0.15 mm drill)

> **CALLOUT: 1.6 / 0.15 ≈ 10.7:1.** Within JLC's published capability (0.15/0.25 mm min via on multilayer), **above the common 10:1 rule of thumb: watch for it in JLC's EQ/DFM review at order time.**

1.6 mm / 0.15 mm ≈ **10.7:1** (finished hole ≈ 1.56 mm deep / 0.15 mm, ≈ 10.4:1 on the 1.56 mm nominal copper-to-copper). JLC's capabilities page publishes the minimum via as **0.15 mm hole / 0.25 mm diameter** for multilayer boards without a thickness restriction, and restricts only the 0.1 mm hole to boards ≤ 1.0 mm (ENIG/OSP), i.e. JLC itself caps its smallest drill at about 10:1. JLC does not publish an explicit aspect-ratio number. **Conclusion: 0.15/0.30 on 1.6 mm is within JLC's published multilayer capability** (cost-more via band); it is above the common 10:1 rule of thumb, so watch the EQ/DFM review at order time. If it is ever rejected, the fallback is 0.20/0.30 POFV (PM decision). Source: https://jlcpcb.com/capabilities/pcb-capabilities ("Min. Via hole size/diameter 0.15/0.25mm (0.1mm/0.2mm only available for board thickness ≤1mm …)", "0.1mm or 0.15mm hole size with any size via diameter … will cost more"), fetched 2026-10-21.

## 5. Via covering: DECIDED (TokenKey PM, 2026-10-21, issue #68)

**Stay on 4-layer JLC04161H-3313 with board-wide Epoxy Filled & Capped (POFV) vias.**

- Why: with a specified stackup + impedance control, JLC's form offers Plugged or Epoxy Filled & Capped, not Tented. JLC ink plugging needs ≥ 0.35 mm from mask openings ("vias with a distance less than 0.35mm from the pad cannot be plugged with ink. Such vias can be plugged with epoxy or copper"); our BGA dog-bone vias are ≈ 0.16 mm from the ball pads. Sources: https://jlcpcb.com/capabilities/pcb-capabilities (Plugged vias), https://jlcpcb.com/help/article/pcb-via-covering (updated 2026-09-09).
- **Cost:** POFV is a paid option on 4 layers (JLC raised the 4L resin-fill price on 2026-08-06). The upcharge is **indicative only, not quoted for this config; re-quote at order time.**
- **Cost comparison at order time only:** also quote 6L **JLC06161H-3313**, where POFV is free and default (https://jlcpcb.com/news/free-via-in-pad-6-20-layer-pcbs-pofv). **Do not switch stacks mid-routing**: a 6L stack would redo the impedance work (USB 0.155/0.20, 50 Ω 0.151) and the net-class rules.
- Hard rule: no dog-bone via may be open in or touching a BGA pad.

## 6. Finish, assembly and inspection

- Surface finish **ENIG** (BGA coplanarity). Mask green, silk white.
- **Both-side assembly → JLC Standard PCBA.** Panelize to ≥ 70 × 70 mm if JLC requires it (board is 50 × 40 mm); add rails/fiducials in the panel.
- **X-ray inspection of U1 (MIMXRT1062DVL6B, 0.65 mm BGA)** required.
- Exclude J3 (TC2030) and TP1–TP5 from BOM (issue #32). Trim bottom-side THT leads to ≤ 1.5 mm (issue #37).

## 7. Mechanical / assembly note: OLED stack (final)

Sources: PM decisions in issues #44 and #47, `docs/layout-notes.md` §10–§11 and `docs/decisions.md` ("OLED mounting and stack") on main. Older 4.9 / 6.5 mm (and 6.6 / 8.65 mm socket) figures are superseded; ignore them.

- **No socket.** The OLED module HS96L03W2C03 (LCSC C5248080) is soldered directly onto **J2**, a 1×4 2.54 mm male header with **3.0 mm plastic: HCTL PZ254-1-04-Z-C (LCSC C5156431)**. The module's own stock header is not used.
- **J2 pin 1 at (16.34, 5.0)** board coordinates, rotation 90°.
- OLED top ≈ **5.65 mm** above the PCB top; lowest module point ≈ **2.0 mm** above the PCB top; overall height with the 1.6 mm board ≈ **7.25 mm** (derived: 5.65 + 1.6, excluding bottom-side parts).
- **J2 is through-hole.** See §7.1 for the hand-assembly order. First build: measure the module's real height above the PCB (pin shoulders could lift it) and update the enclosure CAD.

### 7.1 Hand-solder / assembly steps (after JLC PCBA)

Parts come from `out/<sha>/hand_assembly_bom.csv` (not the JLC BOM).

1. **J2 header (HCTL PZ254-1-04-Z-C, C5156431), THT.** It is in the JLC BOM/CPL; if JLC does not place it (THT not selected), hand-solder it from the top, plastic flush on the board, square pad = pin 1 at (16.34, 5.0). Trim bottom leads ≤ 1.5 mm (#37).
2. **OLED module HS96L03W2C03 (C5248080)** soldered directly onto J2's pins, no socket. Seat the module so its underside is 3.0 mm (header plastic) above the PCB: OLED top ≈ 5.65 mm, lowest module point ≈ 2.0 mm, ≈ 7.25 mm overall with the board. Trim pins above the module.
3. **Knob** onto the EC11E18244A5 (SW2, 20 mm shaft, PCBA-placed): ~17 mm × 16.5 mm per `enclosure/cad/params.py`; part TBD in `fab/hand_assembly.csv`. Fit after the enclosure lid.

## 8. Order-time checklist (do not execute until PoC gates pass)

- [ ] Routing complete (#57–#60); `make -C fab release` passes: 0 ERC errors, 0 DRC errors, 0 unconnected, 0 parity
- [ ] Re-quote JLC (all prices indicative) and get PM sign-off on spend
- [ ] 4 layers, 1.6 mm, **JLC04161H-3313** specified, impedance control on (USB 90 Ω, 50 Ω SE, ±10%)
- [ ] Min via 0.15/0.25 band selected (small-via surcharge accepted); **10.7:1 aspect ratio, watch JLC's EQ review**
- [ ] Via covering **Epoxy Filled & Capped (POFV)**, board-wide; note the 4L upcharge
- [ ] Cost comparison only: also quote 6L JLC06161H-3313 (free POFV); don't switch unless PM re-opens the stackup
- [ ] ENIG, green/white, remove order number or specify position
- [ ] Standard PCBA, both sides, X-ray of U1; upload the **panel** zip + panel BOM/CPL (102.1 × 96.1 mm, §9), or the single board with JLC panelization
- [ ] Panel CPL repeats designators per board (KiKit default); confirm JLC accepts this in the CPL preview, otherwise rename refs per board
- [ ] BOM: 0 missing LCSC numbers; stock checked for every line; J2 THT handling decided
- [ ] Hand-assembly BOM ordered separately: OLED C5248080, knob (part TBD)
- [ ] CPL rotations checked in JLC's preview, especially U1, J1, Q1, diodes and polarized caps
- [ ] Gerber zips checked in a viewer (layer order L1/GND/PWR/L4, drill alignment, Edge.Cuts closed, mouse bites)

## 9. Panel (KiKit 1.8.1)

Board outline 50 × 40 mm with R1 corners (not straight-edged all round), so **mouse bites, not V-score**.

- Layout: **2 × 2 grid, 2 mm gap** → **102.1 × 96.1 mm** panel (≥ 70 × 70 mm). 1 × 2 would be only 50 mm wide.
- Rails: top and bottom, 5 mm wide, 2 mm from the boards.
- Tabs: fixed 3 mm, 2 per side; mouse bites 0.5 mm drill at 0.8 mm pitch, 0.2 mm offset into the board.
- **3 fiducials** on the rails (1 mm copper, 2 mm opening, 5 mm / 2.5 mm offset).
- **Tooling holes:** 1.5 mm NPTH, 2.5 mm from the rail corners (KiKit `3hole`).
- Mill radius 1 mm on internal corners.
- Single-board outputs are kept alongside the panel outputs.
