"""TokenKey RT enclosure, Direction A "puck": every key dimension lives here (mm, g/cm3).

CAD frame: X = KiCad x (east), Y = 40 - KiCad y (north up; the board's SOUTH edge, J1/USB-C,
is the REAR of the device at Y = 0), Z = 0 at the main-PCB TOP surface, +Z up.
Board reference: main e2e5ff9 (PR #49 merged; see board_ref.json).

Injection-moulding note (production only): add 1-2 deg draft on all walls/bosses parallel to
the pull direction (Z), 3 deg on textured faces; the FDM/SLA prototype is modelled draft-free.
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
BOARD = json.load(open(os.path.join(HERE, "board_ref.json")))

# --- process -------------------------------------------------------------------------------
PROCESS = os.environ.get("TK_PROCESS", "FDM")          # "FDM" or "SLA"
WALL = {"FDM": 2.0, "SLA": 1.6}[PROCESS]               # side wall
LID_T = 1.5                                            # top plate
FLOOR_T = 1.6                                          # tray floor
CORNER_R = 3.5                                         # outer plan corner radius
INNER_R = 1.5                                          # cavity corner radius = board corner R1.0 + BOARD_CLR
TOP_EDGE_FILLET = 1.2

# --- board ---------------------------------------------------------------------------------
PCB_W, PCB_D = BOARD["board"]["size_mm"][0] - 0.1, BOARD["board"]["size_mm"][1] - 0.1  # 50 x 40
PCB_T = BOARD["board"]["thickness_mm"]                 # 1.6
BOARD_CLR = 0.5                                        # board edge -> inner wall
UNDER_BOARD = 2.5                                      # PCB bottom -> floor top
THT_TAIL = 1.5                                         # THT leads trimmed to <= 1.5 (PM)

# --- OLED HS96L03W2C03 (decisions.md; J2 pin 1 origin) --------------------------------------
HEADER_H = float(os.environ.get("TK_HEADER", 3.0))   # module-PCB underside above main-PCB top (3.0 mm plastic header, PM)
OLED_MODULE_T = float(os.environ.get("TK_MODULE_T", 2.65))   # module PCB 1.2 + glass stack 1.4 (+0.05) -> OLED top 5.65 (PM final)
OLED_PCB_T = 1.2
OLED_BACK_FEATURE = 1.0   # back-side block, band y +9.3..+12.3 from pin 1 (x unknown -> full width)
OLED_BACK_BAND = (9.3, 12.3)
LID_GLASS_CLR = 0.35      # lid underside above OLED top (PM: 0.3-0.4)
MOD_W, MOD_H, PIN1_FROM_LEFT, PIN1_FROM_EDGE = 27.30, 27.80, 9.84, 1.44
GLASS_X, GLASS_Y = (-8.60, 16.14), (3.43, 20.33)
WINDOW = (22.74, 11.86)                # VA, opening at the lid underside
WINDOW_OFS = (3.81, 10.36)             # window centre from J2 pin 1 (KiCad +x, +y)
WINDOW_CHAMFER = 45.0                  # deg, through the full lid
MOD_HOLE_D, MOD_HOLE_EDGE = 2.50, 2.00
# FPC bend (LCSC datasheet sec. 1.4 p.6): on the FAR edge (opposite the header = south, toward J1),
# 14.5 mm wide centred on the module, curving from the glass ledge onto the glass-side face of the
# module PCB; it does NOT wrap past the edge. Outer extent ~0.4 mm inside the 27.80 outline (+-0.2,
# by scale). Modelled worst case: from the glass far edge to (outline - (INSET - TOL)), z module-PCB
# top .. OLED top.
FPC_BEND_W = 14.5
FPC_BEND_INSET, FPC_BEND_TOL = 0.4, 0.2
HEADER_PIN_ABOVE = 1.0                 # header pin tips above the module PCB after trimming

# --- lid posts locating the module (the header sets the height; posts only locate) -----------
LOC_PIN_D = 2.2                        # into the dia 2.5 module holes
LOC_SHOULDER_D = 4.0
LOC_SHOULDER_GAP = 0.15                # shoulder stays clear of the module PCB (no clamping)
LOC_PIN_BELOW = 1.6                    # pin length below the module PCB top

# --- screws / bosses (M2, NPTH holes H1-H4) -------------------------------------------------
BOSS_D = 4.6
SCREW_CLR_D = 2.4
SCREW_HEAD_CB_D, SCREW_HEAD_CB_H = 4.0, 2.2   # DIN 912 M2 head 3.8 x 2.0
POST_D = 4.6
INSERT_D, INSERT_DEPTH = 3.2, 4.0             # M2 heat-set insert in the top-shell posts

# --- joint ---------------------------------------------------------------------------------
LIP_T, LIP_H, LIP_CLR = 1.0, 1.0, 0.15        # top-shell lip dropping inside the tray wall

# --- USB-C (J1, HRO TYPE-C-31-M-12) --------------------------------------------------------
J1_BODY = dict(w=8.94, y0=32.60, y1=40.00, h=3.26)    # KiCad y range of the shell body
USB_Z = 1.63                                  # plug centreline above the PCB top
USB_OUTER = (13.5, 8.0)                       # overmold pocket on the rear face
USB_INNER = (9.5, 3.8)                        # opening through the skin
USB_SKIN = 0.6                                # skin left at the pocket bottom
USB_RIB_W, USB_RIB_GAP, USB_RIB_LEN = 1.2, 0.3, 5.0

# --- encoder SW2 EC11E18244A5 (20 mm flat shaft, 36 detents, 1.5 mm push) --------------------
# Alps drawing No.3 (EC11E catalogue p.2, via TokenKey Schematic): body 11.7 x 12 footprint, 4.5 mm above
# the PCB seating plane; NO bushing; 20 mm shaft measured from the BODY TOP (tip 24.5 above the PCB,
# ~23.0 pressed); dia 6, round for the first 7 mm, D-flat (4.5 across) for the last 10 mm.
ENC_BODY = (12.0, 12.0, 4.5)        # 11.7 x 12 -> 12 x 12 (orientation not re-checked), height above PCB
SHAFT_L = 20.0                      # from the body top (EC11E18244A5, kept by PM)
SHAFT_TRIM = float(os.environ.get("TK_SHAFT_TRIM", 0.0))   # 0 = stock part (PM: no purchased-part mods); evaluation only
ENC_SHAFT_D, ENC_FLAT, ENC_FLAT_L = 6.0, 4.5, 10.0   # D-flat across-flats 4.5, last 10 mm (untrimmed)
ENC_PUSH = 1.5
ENC_LID_RELIEF_CLR = 0.3            # lid relief over the body, only cut if body + clr > lid underside
ENC_HOLE_D = 7.0                    # lid/collar bore: 0.5 mm radial clearance, the shaft never touches the lid
COLLAR_OD, COLLAR_H = 11.0, 5.0     # lid boss around the shaft; the KNOB bears radially on its OD

# --- knob -----------------------------------------------------------------------------------
KNOB_D = float(os.environ.get("TK_KNOB_D", 17.0))    # 16-18
KNOB_H = float(os.environ.get("TK_KNOB_H", 16.5))    # min that covers the 24.5 mm shaft tip (see README)
KNOB_PUSH_CLR = 0.5                 # left between knob skirt and lid at full push
KNOB_BEARING_CLR = 0.15             # radial, knob bore on collar OD
KNOB_TOP_CLR = 0.5                  # shaft tip -> blind-bore end
KNOB_TOP_SKIN = 1.0                 # solid knob top above the blind bore
KNOB_DKEY_MARGIN = float(os.environ.get("TK_DKEY_MARGIN", 1.0))   # D-key starts this far above the flat start
KNOB_INSERT = os.environ.get("TK_KNOB_INSERT", "sleeve")   # "none" | "sleeve" | "setscrew"
SLEEVE_OD, SLEEVE_L = 8.0, 7.0      # brass D-sleeve, press fit (bore OD+0.0 for SLA, +0.1 FDM)
SETSCREW_INSERT_D = 4.0             # M3 heat-set insert, radial, for an M3 cup-point set screw
MIN_ENGAGEMENT = 6.0

# --- buttons SW3/SW4 B3U-1000P ----------------------------------------------------------------
B3U_H = 1.6
B3U_STROKE = 0.15
CAP_D, CAP_PROUD = 4.6, 0.8
CAP_HOLE_D = 5.0
CAP_FREE = 0.30                     # free travel before the plunger
CAP_STOP_EXTRA = 0.05               # after the switch bottoms -> total travel 0.50 (hard stop)
CAP_FOOT_D, CAP_FOOT_OFS = 1.2, 2.5 # stop feet land on the PCB at +-2.5 mm (Y)
CAP_ARM_T, CAP_ARM_W, CAP_ARM_L, CAP_ARM_BUMP = 0.35, 2.0, 2.5, 0.3   # two cantilevers (+-Y) hold the cap up

# --- LED light pipe (D1) ---------------------------------------------------------------------
LED_H = 0.8
PIPE_D, PIPE_GAP = 2.0, 0.2
PIPE_FLANGE_D, PIPE_FLANGE_T = 3.0, 0.4

# --- bottom tray features ----------------------------------------------------------------------
HATCH = (18.3, 13.0)                # TC2030 / UART service hatch opening (KiCad x 25.5-43.8, y 1.0-14.0)
HATCH_CENTRE_K = (34.65, 7.5)       # KiCad coords of the hatch centre (J3 at 39.0, 4.0; TP1-TP5 at x 26.5-31.5)
HATCH_RECESS = 0.5                  # cover flange per side
HATCH_COVER_T = 0.8
BOOT_HOLE_D, BOOT_TUBE_OD, BOOT_TUBE_GAP = 1.8, 3.6, 0.3
# Steel ballast plate (#53): laser-cut outline computed by plate.py (largest shape that fits).
PLATE_T = 1.2                       # stock 1.2 mm cold-rolled steel (DC01); top at floor + 1.2 = PCB bottom - 1.3
PLATE_Z_CLR = 0.3                   # min vertical gap plate top -> any bottom-side part (0603: 0.35, 0402: 0.75)
PLATE_PART_GAP = 0.5                # plan gap to courtyards / lead tails / bosses that are too tall
PLATE_EDGE_GAP = 0.6                # plan gap to the tray cavity wall
PLATE_HATCH_RIM = 1.0               # floor rim kept around the hatch recess
PLATE_MIN_FEATURE = 3.0             # no slivers / necks narrower than this (laser-cut, flat)
PLATE_PIN_K = ((5.0, 12.0), (20.0, 30.0))    # KiCad xy of two printed locating pins (tray) / plate holes
PLATE_PIN_D, PLATE_PIN_HOLE_D = 2.0, 2.4    # pins 1.0 mm tall; plate bonded with VHB tape (see BOM)
PLATE_PIN_H = 1.0
BALLAST_RHO = 7.85                  # g/cm3 steel (stainless 7.9)
# Silicone feet (#53): stock adhesive bumpers in blind pockets in the tray underside.
FOOT_D, FOOT_H = 8.0, 2.2           # silicone 8.0 x 2.2 (ETOL ARF2003); alt 3M SJ5302 PU 7.9 x 2.2 (TK_FOOT=10x3 -> 10 x 3)
if os.environ.get("TK_FOOT", "") == "10x3":
    FOOT_D, FOOT_H = 10.0, 3.0
FOOT_POCKET_CLR = 0.20              # radial; pocket stays d 8.4 (fits 7.9 SJ5302 too)
FOOT_POCKET_DEPTH = 1.0             # floor left 0.6 mm; foot stands FOOT_H - depth proud
# Foot centres, CAD XY (Y = 40 - KiCad y). Five, because the east side has no free corner: the hatch
# fills the NE corner (that foot sits ON the hatch cover) and the BOOT hole + H2 boss fill the SE corner.
# "E" keeps the knob axis and both buttons inside the support polygon (see README, tipping check).
FEET = {"SW": (10.0, 4.0), "NW": (10.0, 36.0), "SE": (40.5, 6.0), "E": (47.3, 15.5), "NE_cover": (38.5, 33.5)}
FOOT_RHO = 1.15                     # silicone
FOOT_MIN_WALL = 0.8                 # build asserts this much material to every other floor opening
# Grip-cord groove: REMOVED in v0.2 (feet replace it; see README).

# --- mass -------------------------------------------------------------------------------------
RHO = {"FDM": 1.27, "SLA": 1.18}    # PETG / standard resin
FDM_FILL_FACTOR = 0.8               # walls ~solid at 2 mm; ~80 % of solid
PCBA_MASS = 9.0                     # estimate: 50x40x1.6 FR4 ~6 g + parts
# MASS_TARGET dropped (PM #53): slim 13.2 mm puck, feet + steel plate instead of a 120 g target

# --- interference ----------------------------------------------------------------------------
CLASH_MIN = 0.3                     # flag clearances below this

# --- derived -------------------------------------------------------------------------------
OLED_TOP = HEADER_H + OLED_MODULE_T
LID_UNDER = OLED_TOP + LID_GLASS_CLR
LID_TOP = LID_UNDER + LID_T
Z_PCB_BOT = -PCB_T
Z_FLOOR_TOP = Z_PCB_BOT - UNDER_BOARD
Z_DESK = Z_FLOOR_TOP - FLOOR_T
Z_SPLIT = Z_PCB_BOT
FOOT_PROUD = FOOT_H - FOOT_POCKET_DEPTH          # 1.2: tray underside above the desk
BODY_H = LID_TOP - Z_DESK
OUT_W = PCB_W + 2 * (BOARD_CLR + WALL)
OUT_D = PCB_D + 2 * (BOARD_CLR + WALL)
IN_X0, IN_Y0 = -BOARD_CLR, -BOARD_CLR
OUT_X0, OUT_Y0 = -BOARD_CLR - WALL, -BOARD_CLR - WALL


def K(x, y):
    """KiCad board coords -> CAD XY."""
    return (x, PCB_D - y)


def fp(ref):
    return next(f for f in BOARD["footprints"] if f["ref"] == ref)


_j2 = fp("J2")
J2_Y = _j2["tht"][0][1]                            # J2 pin-row y (KiCad), from board_ref: 5.0 (PM final)
J2_PIN1 = (_j2["tht"][0][0], J2_Y)                # module, window, posts and header all follow pin 1
_sw2 = fp("SW2")
_mp = [p for p in _sw2["tht"] if p[2] > 2.0]
ENC_AXIS_K = (sum(p[0] for p in _mp) / len(_mp), sum(p[1] for p in _mp) / len(_mp))
SHAFT_TOP = ENC_BODY[2] + SHAFT_L - SHAFT_TRIM      # 24.5 above the PCB
FLAT_START = ENC_BODY[2] + SHAFT_L - ENC_FLAT_L     # 14.5: round below, D-flat above
KNOB_BOTTOM = LID_TOP + ENC_PUSH + KNOB_PUSH_CLR
COLLAR_TOP = LID_TOP + COLLAR_H
KNOB_POCKET_TOP = FLAT_START + KNOB_DKEY_MARGIN     # D-key never reaches the round section
assert COLLAR_TOP + ENC_PUSH + KNOB_PUSH_CLR <= KNOB_POCKET_TOP + 1e-9, "collar too tall for the knob pocket"
KNOB_TOP = KNOB_BOTTOM + KNOB_H
KNOB_H_MIN = SHAFT_TOP + KNOB_TOP_CLR + KNOB_TOP_SKIN - KNOB_BOTTOM
ENGAGEMENT = SHAFT_TOP - KNOB_POCKET_TOP
