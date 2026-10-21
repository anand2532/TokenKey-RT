# TokenKey RT: JLCPCB 4-Layer Stackup, USB Impedance, and 0.65 mm BGA Via Rules (DFM)

Status: **DRAFT for review.** Owner: TokenKey DFM. Reviewers: TokenKey Layout, TokenKey PM, Anand.
Target fab and assembly house: **JLCPCB** (PCB + PCBA).
MCU: NXP i.MX RT1062, **MAPBGA196, 10 × 10 mm, 0.65 mm pitch** (DVL6x). The PM still has to choose between this package and the DVJ6x 12 × 12 mm, 0.8 mm-pitch version. See Open Items.

> Rule for this document: every fab figure is taken from a JLCPCB page cited in [Sources](#sources). Figures I calculated are labeled **ESTIMATE**, and the method is given. Final trace width and gap come from the **JLCPCB Impedance Calculator** (https://jlcpcb.com/pcb-impedance-calculator), entered with the exact stackup that will be ordered.

---

## 1. Recommended stackup: JLC04161H-3313 (4 layers, 1.6 mm)

| # | Layer | Function | Material | Thickness (JLC) | Er (JLC) |
|---|-------|----------|----------|-----------------|----------|
| — | Top soldermask | — | LPI | 1.2 mil over laminate / 0.6 mil over trace | 3.8 |
| L1 | F.Cu | **Signal** (BGA, USB pair, most parts) | Copper, 1 oz finished | 0.035 mm | — |
| — | Prepreg | — | 3313 × 1 | **0.0994 mm** | **4.1** |
| L2 | In1.Cu | **Solid GND** (reference for L1) | Copper, 0.5 oz | 0.0152 mm | — |
| — | Core | — | FR-4 core (NP-155F per calculator guide) | **1.265 mm** | **4.6** |
| L3 | In2.Cu | **PWR** (3V3, plus DCDC/core islands as needed) | Copper, 0.5 oz | 0.0152 mm | — |
| — | Prepreg | — | 3313 × 1 | 0.0994 mm | 4.1 |
| L4 | B.Cu | **Signal** (BGA escape, decoupling, bottom-side parts) | Copper, 1 oz finished | 0.035 mm | — |
| — | Bottom soldermask | — | LPI | as top | 3.8 |

Nominal finished thickness: 1.6 mm. JLC tolerance for boards ≥ 1.0 mm is ±10%, so 1.44 to 1.76 mm.

**Why 3313 instead of 7628 (JLC04161H-7628 has 0.2104 mm of 7628, Er 4.4, over a 1.065 mm core):**
- The thin 0.0994 mm L1→L2 dielectric shrinks 90 Ω differential and 50 Ω traces to about 0.16–0.19 mm (see §2). That is close to the width that can neck into a 0.65 mm-pitch BGA. On 7628, the 90 Ω pair is about 0.27–0.33 mm wide (third-party estimates, §2). That forces a long uncoupled neck-down region inside the BGA and at the USB-C pads.
- Tighter coupling to L2 GND gives better return paths and less EMI on a small USB device.
- Both stackups are 1.6 mm with the same copper weights, so the drill aspect ratio is the same.

**Why 1.6 mm and not thinner:** JLC lists 0.8, 1.0, and 1.2 mm 4-layer impedance stackups. I could not retrieve their layer tables (the page renders them in tabs that didn't load), so those are **TBD**. Stay at 1.6 mm unless the enclosure or USB-C receptacle (TYPE-C-31-M-12) needs a thinner board. A thinner board would also allow smaller drills: JLC's 0.1 mm hole / 0.2 mm via is only offered for board thickness ≤ 1.0 mm with ENIG/OSP finish. Economic PCBA accepts 0.8 to 1.6 mm boards.

**Source conflict to note:** the 3313 Er is 4.1 on https://jlcpcb.com/impedance and on the capabilities page, but 4.05 on the older cart page. That cart page also says to use 3.5 mil (instead of the 3.91 mil nominal) as the dielectric height for outer-layer impedance traces. Use whatever the live calculator uses. Its guide says the calculator assumes Nan Ya NP-155F core for 4 to 8 layers, so order that material.

**Order settings (fab):** 4 layers, 1.6 mm, FR-4, outer copper 1 oz, inner copper 0.5 oz, **Impedance control: Yes, stackup JLC04161H-3313**, **ENIG** surface finish (flat pads for the BGA; JLC requires ENIG for 0.2–0.25 mm BGA pads; HASL is uneven), green mask (fastest turnaround).

---

## 2. Impedance notes

### 2.1 USB 2.0 HS D+/D− — 90 Ω differential, L1 over L2 GND
JLC impedance tolerance: **±10%** (standard), so 81–99 Ω for a 90 Ω target. JLC offers ±5% on special request.

| Source / method | Stackup | Gap | Width | Status |
|---|---|---|---|---|
| ProtoFlow, Kirschning–Jansen, uncoated | 3313, 0.0994 mm, Er 4.1, 1 oz | 0.127 mm | 0.165 mm | ESTIMATE (third-party) |
| IndieRF, Kirschning–Jansen + mask | 3313, 3.5 mil, Er 4.1, 1 oz | 0.127 mm | 0.163 mm | ESTIMATE (third-party) |
| ProtoFlow, Kirschning–Jansen, uncoated | 3313 | **0.200 mm** | **0.183 mm** | ESTIMATE (third-party) |
| For comparison: 7628 | 7628, 0.2104 mm, Er 4.4 | 0.127 mm | 0.269–0.278 mm | ESTIMATE (third-party) |

**CONFIRMED (JLC impedance calculator, https://jlcpcb.com/pcb-impedance-calculator, stackup JLC04161H-3313, finished 1.56 mm ±10%, 2026-10-19):** **W = 0.154 mm, S = 0.20 mm** on L1 ref L2, Differential Pair (non-coplanar), 90 Ω. The earlier 0.18 mm estimate was too wide: at 0.18 mm width, 90 Ω does not converge at any spacing on this stackup (width plateaus at ~0.179 mm by S ≥ 0.5 mm). Use 0.154 / 0.20 (set KiCad to 0.155 / 0.20). Order with impedance control ±10% and select the JLC04161H-3313 stackup explicitly (the tool's default tab is -3313A).

Routing rules for the pair:
- **L2 stays solid GND under the entire pair**, from the BGA balls to the USB-C pins. Don't cross any split, slot, or void. No L2 cut-outs under the ESD part (USBLC6-2SC6) except its own pads' antipads.
- Route the pair on L1 only, with **no layer changes**. If one is unavoidable, use one via per line, placed symmetrically, with a GND stitching via within about 1 mm.
- **Intra-pair length match:** target ≤ 0.15 mm mismatch (DFM recommendation; **TBD** against the NXP HDG USB section). Put serpentine compensation near the end where the mismatch starts, not mid-run.
- Keep the uncoupled neck-down at the BGA escape and at the USB-C pads as short as possible (about 1–2 mm). Neck to 0.1 mm only inside the BGA courtyard.
- **Keepouts:** at least 0.5 mm (about 3× W) from other signals; at least 1 mm from clocks (32.768 kHz crystal, FlexSPI CLK) and from the DCDC inductor/switch node. No parallel run next to the QSPI flash bus. No stubs: ESD and connector pads sit directly in the path (fly-by).
- Optional GND pour on L1 next to the pair must be ≥ 0.3 mm from the pair edge (or co-design it as coplanar in the calculator) and must be stitched to L2.

### 2.2 50 Ω single-ended, L1 over L2 (in case it's needed, e.g. a future RF/test point)
- **CONFIRMED (JLC calculator, JLC04161H-3313, Single Ended non-coplanar, L1 ref L2, 50 Ω): W = 0.151 mm.** The earlier 0.18–0.19 mm hand estimate (uncoated Hammerstad–Jensen) overstated it.
- No 50 Ω nets are known on TokenKey RT today, so this is for reference only.

---

## 3. Advanced-via / BGA rule check: 0.65 mm-pitch MAPBGA196

### 3.1 Inputs
| Item | Value | Source |
|---|---|---|
| Ball pitch p | 0.65 mm | NXP IMXRT1060CEC |
| BGA land Dp | **0.30 mm assumed (NSMD)** — **TBD** from the NXP package drawing / footprint | Assumption. The NXP PDF couldn't be fetched |
| JLC min via (multilayer) | 0.15 mm hole / 0.25 mm diameter (costs more). **Preferred min hole 0.2 mm** | JLC capabilities |
| JLC via annular ring | via diameter = hole + 0.10 mm (min) / + 0.15 mm (preferred), i.e. 0.05 / 0.075 mm ring | JLC capabilities |
| JLC surcharge | 0.1/0.15 mm holes at any diameter, and 0.2/0.25 mm holes with diameter < 0.45 mm, **cost more** | JLC capabilities |
| JLC min track/space (multilayer, 1 oz) | 0.09/0.09 mm; "3 mil acceptable in BGA fan-outs" | JLC capabilities |
| JLC BGA pad-to-trace | ≥ 0.1 mm, min 0.09 mm on multilayer | JLC capabilities |
| JLC via hole-to-hole | 0.2 mm | JLC capabilities |
| JLC via hole to track | 0.2 mm | JLC capabilities |
| JLC min BGA pad | 0.2 mm (0.2–0.25 mm requires ENIG) | JLC capabilities |
| NXP recommendation (BGA area) | via 14/8 mil (0.356/0.203 mm), trace 4 mil (0.102 mm), space 3.79 mil (0.096 mm) | NXP MIMXRT105060HDUG §7.2 |
| NXP recommendation (outside BGA) | via 18/8 mil (0.457/0.203 mm), trace 5 mil, space 7 mil | NXP MIMXRT105060HDUG §7.2 |

### 3.2 Geometry

**(a) Dog-bone via in the diagonal gap between 4 balls.**
Distance from the via center to each surrounding ball center = p·√2 / 2 = 0.65 × 0.7071 = **0.4596 mm**.
Copper clearance between via pad and ball pad = 0.4596 − Dv/2 − Dp/2.

| Via (hole/dia) | Dp = 0.30 | Dp = 0.35 | Verdict vs JLC 0.10 (0.09 BGA min) |
|---|---|---|---|
| 0.20 / **0.35** (NXP 8/14 mil) | **0.135 mm** | 0.110 mm | **PASS** for both |
| 0.20 / 0.40 | 0.110 mm | 0.085 mm | Marginal pass / FAIL |
| 0.20 / 0.45 (no-surcharge size) | 0.085 mm | 0.060 mm | **FAIL** |
| 0.15 / 0.25 | 0.185 mm | 0.160 mm | PASS, but 1.6 / 0.15 = 10.7:1 aspect ratio and costs more |

Annular ring at 0.20/0.35: (0.35 − 0.20)/2 = **0.075 mm**, which is JLC's preferred value. Aspect ratio 1.6 / 0.2 = **8:1**.
Hole-to-hole between adjacent dog-bone vias: 0.65 − 0.20 = 0.45 mm ≥ 0.2 mm, **PASS**.

**(b) One trace between two adjacent dog-bone vias (0.65 mm center to center).**
Copper gap = 0.65 − 0.35 = **0.30 mm**. A trace w with clearance c needs w + 2c ≤ 0.30.
- JLC minimums (0.09 + 2 × 0.09 = 0.27 mm): **PASS**, 0.03 mm margin.
- NXP (0.102 + 2 × 0.096 = 0.294 mm): **PASS**, 0.006 mm margin.
- Two traces: 2 × 0.09 + 3 × 0.09 = 0.45 > 0.30, **FAIL**. Only one trace per channel.
- ⚠ JLC also lists "Via hole to Track 0.2 mm". With a 0.2 mm hole and a centered 0.1 mm trace, hole edge to trace = (0.65 − 0.10)/2 − 0.10 = **0.175 mm**, below that 0.2 mm figure. **TBD:** ask JLC whether that rule applies inside a BGA fan-out, where they explicitly allow 3 mil. If it does, the channel route fails, and the options are via-in-pad (below) or a 0.15 mm drill (0.275 − 0.075 = 0.200 mm, right at the limit).

**(c) One trace between two ball pads on L1 (outer-row escape).**
Gap = 0.65 − 0.30 = 0.35 mm. One 0.10 mm trace leaves 0.125 mm per side, **PASS**. Two traces don't fit.

**(d) Escape capacity on a 4-layer board.** Only L1 and L4 carry signals (L2 = GND, L3 = PWR), and each channel holds one trace per layer. That realistically escapes the outer **~4 rows** of the 14 × 14 array. Inner-ring balls are only reachable if they are GND or PWR (they go straight down to L2/L3) or unused. **TBD (Layout):** check the RT1062 ball map against the used pin list. A community NXP thread warns that inner-array signal balls push the design toward about 6 layers.

### 3.3 Verdict
- **LOCKED (TokenKey PM, 2026-10-19, rev 2): BGA fanout via = 0.15 mm drill / 0.30 mm pad, 0.10/0.10 mm escape tracks.** Supersedes 0.20/0.35, which gave only 0.175 mm hole-edge-to-track vs JLC's published "Via hole to Track 0.2mm". At 0.15/0.30: hole-to-track = (0.65 − 0.15)/2 − 0.05 = **0.200 mm** (meets rule, no exception needed), pad-to-track = (0.65 − 0.30)/2 − 0.05 = **0.125 mm**, via-pad to ball-pad copper = 0.4596 − 0.15 − 0.15 ≈ **0.16 mm** (0.30 ball land). Pad = hole + 0.15 (JLC preferred). Aspect ratio 1.6/0.15 ≈ 10.7:1 (JLC allows 0.15 holes on multilayer). Small-via surcharge band accepted; exact 0.15 vs 0.20 price delta TBD from live quote. POFV remains the fallback. No JLC support question needed.
- **Standard through-hole dog-bone vias at 0.20 mm hole / 0.35 mm pad: PASS** on JLC's published copper rules, assuming a ≤ 0.30 mm BGA land. It is tight, and the via-hole-to-track question (b) is open. The 0.45 mm no-surcharge via **FAILS**, so the **small-via surcharge is unavoidable**.
- **Via-in-pad (JLC POFV, epoxy filled + copper capped) is NOT required** for basic fanout if (b) is accepted and the ball map escapes within ~4 rows. It **is required** if JLC enforces the 0.2 mm via-hole-to-track rule in the BGA field, or if inner-row signals have to escape. POFV sizes for this pitch: 0.20/0.30 or 0.20/0.35 (JLC POFV table; ring 0.05 min / 0.075 preferred; ≥ 0.45 mm from regular PTH/NPTH). Never use unfilled vias in BGA pads.
- **Cost / lead time:** POFV on **4-layer boards is a paid option**, and JLC announced a slight price increase for 4-layer resin-filled vias on 2026-08-06. On **6–20 layer boards POFV is free and the default**. 6-layer boards are quoted with a 4-day build vs 24 h for 1–4 layer boards, and JLC said the 6+ layer standard delivery would be adjusted during the resin-line expansion. Exact surcharges and days are **TBD from a live quote**. If the ball-map check shows inner-row signals, **quote JLC06161H-3313 (6 L, free POFV) alongside 4 L + POFV**, because the 6-layer board can come out at a similar price and gives better routing.

### 3.4 KiCad rules (proposed)
Board Setup → Constraints: min track 0.09 mm, min clearance 0.09 mm, min via annular 0.075 mm, min via hole 0.15 mm, min via diameter 0.30 mm, hole-to-hole 0.20 mm, copper-to-edge 0.30 mm (JLC ≥ 0.2), silk-to-pad 0.15 mm, min text 1.0 mm / 0.15 mm stroke.

**Net classes LOCKED by TokenKey PM (2026-10-19):**

| Net class | Track | Clearance | Via (dia/hole) | Diff gap | Notes |
|---|---|---|---|---|---|
| Default | 0.15 mm | 0.15 mm | 0.60 / 0.30 (standard via) | — | No small-via surcharge at 0.6/0.3 |
| Power | 0.40 mm trunk / 0.30 mm branch | 0.15 mm | 0.60 / 0.30 | — | Check VBUS current; pour where possible |
| BGA via (rule area on MCU courtyard) | 0.10 mm | 0.10 mm | **0.30 / 0.15** | — | Meets JLC 0.2 mm via-hole-to-track; small-via surcharge accepted |
| USB_HS (D+/D−) | **0.155 mm** | 0.50 mm to others | avoid; 0.30/0.15 if forced | **0.20 mm** | 90.7 Ω per JLC calc (JLC04161H-3313), L1 ref L2, skew ≤ 0.15 mm |
| Decoupling (bottom, under BGA) | per Default/Power | 0.10 mm in BGA area | shares BGA vias | — | Per NXP HDG, 0402 decoupling on the bottom at the power balls |

Example custom rule (`.kicad_dru`):
```
(version 1)
(rule "BGA fanout"
  (condition "A.insideCourtyard('U1') || B.insideCourtyard('U1')")
  (constraint track_width (min 0.09mm) (opt 0.10mm))
  (constraint clearance (min 0.09mm))
  (constraint via_diameter (min 0.30mm))
  (constraint hole_size (min 0.15mm)))
(rule "USB HS diff"
  (condition "A.NetClass == 'USB_HS'")
  (constraint diff_pair_gap (opt 0.20mm))
  (constraint track_width (opt 0.155mm))
  (constraint skew (max 0.15mm)))
```
(Replace `U1` with the MCU refdes.)

---

## 4. Assembly risk flags (JLCPCB PCBA)
1. **Double-sided placement → Standard PCBA.** Economic PCBA is single-sided only. Standard supports both sides. The BOM already puts the boot button on the bottom, and NXP recommends bottom-side decoupling under the BGA, so this design is double-sided unless those parts move. Keep **the BGA and everything heavy or fine-pitch on top, and only passives (plus the button) on the bottom.**
2. **Standard PCBA minimum board size is 70 × 70 mm** (panel 70 × 70 to 250 × 250 mm), and edge rails and fiducials are required. A USB token is much smaller, so it **must be panelized**: 5 mm rails, 2 mm tooling holes, 1 mm fiducials 3.85 mm from the panel edge, mouse bites (≥ 5 mm breakaway width), per JLC outline rules. Economic PCBA goes down to 10 × 10 mm but can't do double-sided.
3. **BGA pitch:** 0.65 mm is within both tiers (Economic ≥ 0.5 mm, Standard ≥ 0.3 mm).
4. **X-ray:** JLC X-rays BGA/QFN/LGA automatically, but its own guide says detection isn't guaranteed. **Request X-ray of the MCU explicitly in the order remarks.** Cost is $1.64/component for 1–10 pcs, falling with quantity.
5. **Cost and lead time, Standard vs Economic:** setup $25.56 single-side / $51.12 double-side (vs $8.18); stencil $16.42 double-side; handling ≥ $14.93; build ≥ 4 days (vs 1–3). Prices are from the JLC PCBA price page and should be confirmed in the live quote.
6. **Reflow:** Standard 240 ± 5 °C. Check MSL/bake handling for the RT1062 tray.
7. **Finish:** ENIG is preferred for BGA coplanarity. Under the BGA, use tented or POFV vias only; plugged (mask-filled) vias need ≥ 0.35 mm from mask openings, which won't fit at this pitch.
8. **Economic PCBA "standard stack-up only":** if the plan is ever to use Economic with impedance stackup JLC04161H-3313, **TBD:** confirm it counts as "standard".

---

## 5. Open items
**TokenKey PM**
- [ ] **Package decision:** DVL6B (10 × 10, 0.65 mm) vs DVJ6B (12 × 12, 0.8 mm). At 0.8 mm the diagonal distance is 0.566 mm, so a 0.45 mm via with a 0.30 mm pad leaves 0.191 mm and no small-via surcharge applies. That removes most of §3's risk at the cost of board area.
- [ ] Accept double-sided Standard PCBA plus panelization, or move the boot button and decoupling to make it single-sided (decoupling on top is worse for SI/PI).
- [ ] Approve a 4 L vs 6 L (free POFV) quote comparison.
- [ ] Board thickness: confirm 1.6 mm against the enclosure and USB-C receptacle.

**TokenKey Layout**
- [ ] Get the BGA land size from the NXP package drawing / footprint (assumed 0.30 mm NSMD here) and re-run the §3.2 table.
- [ ] Ball-map escape study: count used signal balls beyond row 4.
- [ ] Run the JLC Impedance Calculator for 90 Ω diff (S = 0.20 mm) and 50 Ω SE on JLC04161H-3313 L1/L2, then update §2 and the net classes.
- [ ] Put the USB pair, ESD part, and USB-C on top with a solid L2 underneath; confirm the length-match target against the NXP HDG USB section.
- [ ] Ask JLC whether the 0.2 mm via-hole-to-track rule applies inside the BGA fan-out (decides whether POFV is needed).

---

## Sources
- JLCPCB controlled-impedance stackups (Er table, JLC04161H-7628/-3313/… layer thicknesses): https://jlcpcb.com/impedance (fetched 2026-10-19)
- JLCPCB older impedance page (3313 Er 4.05; dielectric-height note): https://cart.jlcpcb.com/client/template/placeOrder/impedance.html
- JLCPCB PCB capabilities (vias, annular ring, BGA, trace/space, POFV, tolerances, soldermask, outline): https://jlcpcb.com/capabilities/pcb-capabilities (fetched 2026-10-19)
- JLCPCB Impedance Calculator and user guide (NP-155F, copper/mask parameters): https://jlcpcb.com/pcb-impedance-calculator, https://jlcpcb.com/help/article/user-guide-to-the-jlcpcb-impedance-calculator
- JLCPCB POFV (free on 6–20 L, charged on 4 L; POFV size table): https://jlcpcb.com/news/free-via-in-pad-6-20-layer-pcbs-pofv
- JLCPCB news, 2026-08-06 resin-plugging adjustment: https://jlcpcb.com/news/page/2
- JLCPCB PCBA capabilities (Economic vs Standard): https://jlcpcb.com/capabilities/pcb-assembly-capabilities
- JLCPCB PCBA pricing (setup, stencil, X-ray): https://jlcpcb.com/help/article/pcb-assembly-price
- JLCPCB X-ray guide: https://jlcpcb.com/help/article/x-ray-inspection-report-interpretation-guide
- NXP MIMXRT1050/1060 Hardware Development Guide §7.2 (via/trace geometry, bottom decoupling): https://community.nxp.com/pwmxy87654/attachments/pwmxy87654/imxrt/28633/1/MIMXRT105060HDUG.pdf
- NXP IMXRT1060CEC datasheet (package list): https://www.nxp.com/docs/en/nxp/data-sheets/IMXRT1060CEC.pdf
- Third-party 90 Ω estimates (not JLC values): https://www.protoflow.ai/tools/pcb-impedance-calculator, https://www.indierf.com/notes/usb-90-ohm-differential-pair-width
- NXP community note on 0.65 mm-pitch layer count: https://community.nxp.com/t5/i-MX-RT-Crossover-MCUs/IMXRT1064-Production-package/td-p/1015318

## Appendix: JLC quote snapshot (indicative, 2026-10-19 IST, quote form only, no order)
4 L, 50×50 mm, qty 5, 1.6 mm, ENIG, 1/0.5 oz, JLC04161H-3313, impedance ±10%. Build 3–4 days in all cases. Page pricing was unstable during the session; re-quote before release.

| Min via hole/diameter | Total | Notes |
|---|---|---|
| 0.3/(0.4/0.45) default | $59.03 | Includes impedance $33.08 |
| 0.25/(0.35/0.4) | $89.86 | Via line $16.75 + auto 4-Wire Kelvin Test $16.71 + auto Tg155 $3.37 |
| 0.2/(0.3/0.35) | ~$89.86–89.96 | Possibly stale read |
| 0.15/(0.25/0.3), chosen | $89.96 | Via line $16.85 + same Kelvin/Tg155 adders |
| POFV at default via | $93.30 | Via covering $16.85 + plating method $3.34 + Kelvin + Tg155 |

Conclusion: 0.15 vs 0.20 drill is effectively the same price tier (about $0.10 difference). The small-via option adds about $31 per prototype order. "Tented" is disabled once a stackup and impedance are specified; confirm via covering for BGA vias before release.

## Update 2026-10-21 (TokenKey PM, issue #68)

- [ ] **J1 (USB-C receptacle) via-in-pad (PR #76): J1 pads B6/B7 (B-row D+/D−) and their A-row mates A6/A7 each carry a 0.15/0.30 mm via inside the 0.30 × 1.45 mm SMD pad (USB_DP: A6, B6; USB_DN: A7, B7). These vias MUST be Epoxy Filled & Copper Capped (JLC 'Epoxy Filled & Capped' / POFV). The order must NOT drop or downgrade the POFV via-covering option** (not Tented, not Plugged, not untreated): open or plugged vias in these SMD pads wick solder and cause opens or voids on the USB pins.
- **Via covering DECIDED:** stay on 4L JLC04161H-3313 with **board-wide Epoxy Filled & Capped (POFV)** vias. 4L POFV is a paid upcharge, indicative only; re-quote at order.
- **Cost comparison only:** quote 6L JLC06161H-3313 (POFV free) at order time; **do not switch stacks mid-routing**, since that redoes the impedance work.
- **Aspect ratio callout:** 1.6 / 0.15 ≈ **10.7:1**, within JLC's published capability (0.15/0.25 multilayer min via), above the 10:1 rule of thumb; watch it in JLC review.
