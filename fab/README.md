# fab: TokenKey RT fabrication and assembly package

Fab notes for JLCPCB (PCB + Standard PCBA). Detailed derivations are in [stackup.md](stackup.md).
**No ordering:** per Anand (via TokenKey PM, 2026-10-19) there is no fab, assembly or parts spend until the PoC gates in `docs/poc/` pass. The pipeline only generates files.

## 1. How to run the pipeline

Needs `kicad-cli` 9.x (tested with 9.0.2) and Python 3.

```sh
make -C fab            # dry run: every output is attempted, ERC/DRC gates are reported but do not stop it
make -C fab release    # strict: exits non-zero on any failed step, ERC error, DRC error, unconnected item or parity issue
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
| `reports/` | `summary.md`, `erc.json`, `drc.json` (with schematic parity), `missing-lcsc.md`, raw pos/BOM CSVs, per-step logs |

Scripts: `scripts/make_fab.sh` (driver), `scripts/jlc_convert.py` (CPL/BOM conversion, missing-LCSC report), `scripts/gate_summary.py` (ERC/DRC counts by type).

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

1.6 mm / 0.15 mm ≈ **10.7:1** (finished hole ≈ 1.56 mm deep / 0.15 mm, ≈ 10.4:1 on the 1.56 mm nominal copper-to-copper). JLC's capabilities page publishes the minimum via as **0.15 mm hole / 0.25 mm diameter** for multilayer boards without a thickness restriction, and restricts only the 0.1 mm hole to boards ≤ 1.0 mm (ENIG/OSP), i.e. JLC itself caps its smallest drill at about 10:1. JLC does not publish an explicit aspect-ratio number. **Conclusion: 0.15/0.30 on 1.6 mm is within JLC's published multilayer capability** (cost-more via band); it is above the common 10:1 rule of thumb, so watch the EQ/DFM review at order time. If it is ever rejected, the fallback is 0.20/0.30 POFV (PM decision). Source: https://jlcpcb.com/capabilities/pcb-capabilities ("Min. Via hole size/diameter 0.15/0.25mm (0.1mm/0.2mm only available for board thickness ≤1mm …)", "0.1mm or 0.15mm hole size with any size via diameter … will cost more"), fetched 2026-10-21.

## 5. Via covering (tenting) — NEEDS PM DECISION

- With a specified stackup and impedance control, JLC's quote form no longer offers "Tented"; the choices are **Plugged** (soldermask-ink filled) or **Epoxy Filled & Capped** (POFV).
- JLC on Plugged: "Filled vias should have ≥ 0.35 mm clearance from other soldermask openings (e.g. pads)" and "vias with a distance less than 0.35mm from the pad cannot be plugged with ink. Such vias can be plugged with epoxy or copper." Sources: https://jlcpcb.com/capabilities/pcb-capabilities (Plugged vias), https://jlcpcb.com/help/article/pcb-via-covering (last updated 2026-09-09).
- Our BGA dog-bone vias sit ≈ 0.16 mm from the ball-pad mask openings, so **ink plugging is not allowed for them** and a "Plugged" order would leave those vias effectively unplugged/open-risk next to BGA pads.
- **Recommendation: Epoxy Filled & Capped for the whole board** (JLC applies the selection board-wide; on 4 layers it is a paid option, free on 6+ layers). Plugged is acceptable only if JLC confirms the BGA-area vias can be left tented-without-fill — that would need a support question, which PM has ruled out. PM to decide: (a) 4L + epoxy filled & capped (cost item), or (b) quote 6L JLC06161H-3313 where POFV is free.
- Hard rule regardless of option: **no dog-bone via may be open in or touching a BGA pad**; no via in pad unless POFV is selected.

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
- **J2 is through-hole: hand-solder / THT step.** Order J2 as a THT part in PCBA (or hand-fit). The OLED module is soldered onto J2 **after** PCBA as a manual step (module's own BOM line via J2 `Module_LCSC`; the JLC BOM export does not list it, so source it separately). First build: measure the module's real height above the PCB (pin shoulders could lift it) and update the enclosure CAD.

## 8. Order-time checklist (do not execute until PoC gates pass)

- [ ] Routing complete (#57–#60); `make -C fab release` passes: 0 ERC errors, 0 DRC errors, 0 unconnected, 0 parity
- [ ] Re-quote JLC (indicative only today) and get PM sign-off on spend
- [ ] 4 layers, 1.6 mm, JLC04161H-3313 specified, impedance control on
- [ ] Min via 0.15/0.25 band selected (small-via surcharge accepted)
- [ ] Via covering per PM decision (§5)
- [ ] ENIG, green/white, remove order number or specify position
- [ ] Standard PCBA, both sides, X-ray of U1, panel ≥ 70 × 70 mm if needed
- [ ] BOM: 0 missing LCSC numbers; stock checked for every line; J2 THT and OLED hand-solder noted
- [ ] CPL rotations checked in JLC's preview, especially U1, J1, Q1, diodes and polarized caps
- [ ] Gerber zip checked in a viewer (layer order L1/GND/PWR/L4, drill alignment, Edge.Cuts closed)
