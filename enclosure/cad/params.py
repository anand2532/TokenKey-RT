"""TokenKey RT enclosure, Direction A "puck": every key dimension lives here (mm, g/cm3).

CAD frame: X = KiCad x (east), Y = 40 - KiCad y (north up; the board's SOUTH edge, J1/USB-C,
is the REAR of the device at Y = 0), Z = 0 at the main-PCB TOP surface, +Z up.
Board reference: Layout #31 commit eb4495a (see board_ref.json).

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
J2_PIN1 = None            # filled from board_ref (J2 pad 1)
MOD_W, MOD_H, PIN1_FROM_LEFT, PIN1_FROM_EDGE = 27.30, 27.80, 9.84, 1.44
GLASS_X, GLASS_Y = (-8.60, 16.14), (3.43, 20.33)
WINDOW = (22.74, 11.86)                # VA, opening at the lid underside
WINDOW_OFS = (3.81, 10.36)             # window centre from J2 pin 1 (KiCad +x, +y)
WINDOW_CHAMFER = 45.0                  # deg, through the full lid
MOD_HOLE_D, MOD_HOLE_EDGE = 2.50, 2.00
FPC_BEND_W = 14.5                      # at the module's south (far) edge, assumed centred
FPC_BEND_OUT = 1.5                     # conservative protrusion past the module edge (task: >= 1.5)
FPC_BEND_ZMIN = None                   # lowest point of the bend: default = module underside - back feature
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
SHAFT_L = float(os.environ.get("TK_SHAFT", 20.0))    # 20 default (PM); 15 = cheap variant (a)
ENC_BODY = (12.4, 13.4, 6.5)        # x, y (board, rot 90), height above PCB (Alps 6.5, verify)
ENC_BUSHING_D, ENC_BUSHING_TOP = 7.0, 7.0   # Alps LB = 7 from the mounting surface (verify)
ENC_SHAFT_D, ENC_FLAT, ENC_FLAT_L = 6.0, 4.5, 10.0   # D-flat across-flats 4.5, flat length R = 10 from the tip
ENC_PUSH = 1.5
ENC_LID_RELIEF_CLR = 0.3            # lid underside relief over the encoder body
ENC_HOLE_D = 7.6
COLLAR_OD, COLLAR_H = 11.0, 3.5     # radial bearing collar on the lid around the shaft

# --- knob -----------------------------------------------------------------------------------
KNOB_D = float(os.environ.get("TK_KNOB_D", 17.0))    # 16-18
KNOB_H = float(os.environ.get("TK_KNOB_H", 14.0))    # 12-15 default band; 15-25 allowed
KNOB_PUSH_CLR = 0.5                 # left between knob skirt and lid at full push
KNOB_BEARING_CLR = 0.15             # radial, knob bore on collar OD
KNOB_TOP_CLR = 0.5                  # shaft tip -> blind-bore end
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
BALLAST_K = (6.0, 10.0, 24.0, 28.0) # KiCad x0,y0,x1,y1 of the ballast plate (under the BGA area)
BALLAST_T = 1.2
BALLAST_RHO = 7.85                  # steel; tungsten 19.3
BALLAST_WALL = 0.8
GRIP_INSET, GRIP_W, GRIP_D = 1.2, 1.6, 0.8   # groove for a 1.5 mm silicone cord
GRIP_CORD_PROUD = 0.7

# --- mass -------------------------------------------------------------------------------------
RHO = {"FDM": 1.27, "SLA": 1.18}    # PETG / standard resin
FDM_FILL_FACTOR = 0.8               # walls ~solid at 2 mm; ~80 % of solid
PCBA_MASS = 9.0                     # estimate: 50x40x1.6 FR4 ~6 g + parts
MASS_TARGET = 120.0                 # design parameter only

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
J2_PIN1 = (_j2["tht"][0][0], _j2["tht"][0][1])   # pad 1 (16.34, 5.0) at eb4495a
_sw2 = fp("SW2")
_mp = [p for p in _sw2["tht"] if p[2] > 2.0]
ENC_AXIS_K = (sum(p[0] for p in _mp) / len(_mp), sum(p[1] for p in _mp) / len(_mp))
SHAFT_TOP = SHAFT_L                  # Alps L1 from the mounting surface (PCB), verify on a part
KNOB_BOTTOM = LID_TOP + ENC_PUSH + KNOB_PUSH_CLR
COLLAR_TOP = LID_TOP + COLLAR_H
KNOB_POCKET_TOP = COLLAR_TOP + KNOB_PUSH_CLR + ENC_PUSH      # ceiling clears the collar at full push
KNOB_TOP = KNOB_BOTTOM + KNOB_H
ENGAGEMENT = SHAFT_TOP - KNOB_POCKET_TOP
