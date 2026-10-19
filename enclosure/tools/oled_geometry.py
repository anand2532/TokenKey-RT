#!/usr/bin/env python3
"""HS96L03W2C03 OLED module geometry in TokenKey-RT board coordinates.

Inputs come from docs/decisions.md (PR #25, "OLED HS96L03W2C03 mechanicals").
The origin there is header pin 1, +x toward pin 4, +y from the header edge toward the glass.
J2 is placed at rotation 90 with its pins along +x, and the module extends south (+y in KiCad),
so module +x/+y map directly onto board +x/+y with no mirroring.

Usage: python3 oled_geometry.py [--header H] [J2_y ...]
  defaults: header 3.0 mm (PM, 2026-10-19), J2 y 5.5 (main 6fb72fa) and 5.0 (Layout ask)
Heights: design top = header + MODULE_ALLOW (3.6 mm envelope); nominal top = header + 2.65;
lowest module point if the 1.0 mm back-side feature hangs below = header - 1.0.
"""
import sys

PIN1_X = 16.34                      # J2 pin 1 x on the board (PR #23)
MOD = dict(w=27.30, h=27.80, pin1_from_left=9.84, pin1_from_header_edge=1.44)
GLASS = dict(x=(-8.60, 16.14), y=(3.43, 3.43 + 16.90))
AA = dict(x=(-7.06, 14.68), y=(4.93, 15.79))    # AA x position assumed centred (not dimensioned)
VA = (22.74, 11.86)
HOLE_EDGE, HOLE_D = 2.00, 2.50
FPC_BEND_W = 14.50                  # at the far edge, assumed centred
J1_BODY_Y0, J1_CRTYD_Y0 = 32.60, 30.985   # USB-C body / courtyard north edge (PR #23)
J1_X = (12.48, 21.52)
WIN_MARGIN = 0.5                    # per side, AA -> window

def run(j2y):
    x0 = PIN1_X - MOD['pin1_from_left']; y0 = j2y - MOD['pin1_from_header_edge']
    pcb = (x0, y0, x0 + MOD['w'], y0 + MOD['h'])
    g = (PIN1_X + GLASS['x'][0], j2y + GLASS['y'][0], PIN1_X + GLASS['x'][1], j2y + GLASS['y'][1])
    a = (PIN1_X + AA['x'][0], j2y + AA['y'][0], PIN1_X + AA['x'][1], j2y + AA['y'][1])
    w = (a[0] - WIN_MARGIN, a[1] - WIN_MARGIN, a[2] + WIN_MARGIN, a[3] + WIN_MARGIN)
    holes = [(x0 + HOLE_EDGE, y0 + HOLE_EDGE), (pcb[2] - HOLE_EDGE, y0 + HOLE_EDGE),
             (x0 + HOLE_EDGE, pcb[3] - HOLE_EDGE), (pcb[2] - HOLE_EDGE, pcb[3] - HOLE_EDGE)]
    cx = (pcb[0] + pcb[2]) / 2
    fpc = (cx - FPC_BEND_W / 2, cx + FPC_BEND_W / 2)
    f = lambda t: "(" + ", ".join(f"{v:.2f}" for v in t) + ")"
    print(f"--- J2 pin 1 at ({PIN1_X}, {j2y}) ---")
    print("module PCB  x0,y0,x1,y1", f(pcb))
    print("glass       x0,y0,x1,y1", f(g))
    print("active area x0,y0,x1,y1", f(a), " centre", f(((a[0]+a[2])/2, (a[1]+a[3])/2)))
    print(f"window (AA+{WIN_MARGIN}) x0,y0,x1,y1", f(w), f" size {w[2]-w[0]:.2f} x {w[3]-w[1]:.2f}",
          " centre rel. pin1", f(((w[0]+w[2])/2 - PIN1_X, (w[1]+w[3])/2 - j2y)))
    print("module holes (dia %.2f)" % HOLE_D, ", ".join(f(h) for h in holes))
    print("FPC bend x-span", f(fpc), " overlaps J1 x-span" if fpc[0] < J1_X[1] and fpc[1] > J1_X[0] else "")
    print(f"far edge y {pcb[3]:.2f}: gap to J1 body {J1_BODY_Y0 - pcb[3]:+.2f} mm, to J1 courtyard {J1_CRTYD_Y0 - pcb[3]:+.2f} mm")

MODULE_NOM, MODULE_ALLOW, BACK_FEATURE = 2.65, 3.6, 1.0
LID_GAP, LID_T = 0.4, 1.5                 # lid underside above design top; lid plate thickness
KEEP_UNDER = {"U6 SOT-23-6": 1.45, "U1 BGA": 1.4, "L2 SWPA4020 (board, until sync)": 2.0,
              "L2 VLS3015CX (schematic)": 1.5}

args = sys.argv[1:]
header = 3.0
if "--header" in args:
    i = args.index("--header"); header = float(args[i + 1]); del args[i:i + 2]
for y in (map(float, args) if args else (5.5, 5.0)):
    run(y)

top_design, top_nom = header + MODULE_ALLOW, header + MODULE_NOM
lid_under = top_design + LID_GAP
print(f"--- heights above main-PCB top, header (module-PCB underside) = {header:.2f} mm ---")
print(f"OLED top: design {top_design:.2f} (header + {MODULE_ALLOW}), nominal {top_nom:.2f} (header + {MODULE_NOM})")
print(f"lid underside {lid_under:.2f}, lid top {lid_under + LID_T:.2f}; nominal glass-to-lid gap {lid_under - top_nom:.2f}")
low = header - BACK_FEATURE
print(f"lowest module point if the {BACK_FEATURE} mm back feature hangs below: {low:.2f}")
for k, v in KEEP_UNDER.items():
    print(f"  margin over {k} ({v} mm): {low - v:+.2f}")
