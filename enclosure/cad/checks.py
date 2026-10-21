"""Automated interference / clearance checks: every part vs the board keep-out model and vs
every other part, plus the knob at full push and the OLED FPC bend vs the USB-C body."""
import itertools
import params as P

# (part, other-substring) pairs that are designed contacts or running fits (< CLASH_MIN is OK
# as long as they do not intersect).
FITS = [
    ("top_shell", "pcb"), ("bottom_tray", "pcb"), ("top_shell", "bottom_tray"),
    ("hatch_cover", "bottom_tray"), ("ballast", "bottom_tray"), ("feet", "bottom_tray"), ("feet", "hatch_cover"), ("knob_sleeve", "knob"),
    ("knob_sleeve", "SW2"), ("knob", "SW2"), ("knob", "top_shell"),
    ("button_cap", "top_shell"), ("light_pipe", "top_shell"), ("top_shell", "OLED module PCB"),
    ("button_cap_btn1", "SW3"), ("button_cap_btn2", "SW4"), ("light_pipe", "D1"),
    ("knob@full-push", "top_shell"),   # radial bearing fit stays engaged while pushed
]


def _is_fit(a, b):
    return any((x in a and y in b) or (x in b and y in a) for x, y in FITS)


def _bbox_gap(s1, s2):
    b1, b2 = s1.BoundingBox(), s2.BoundingBox()
    g = 0.0
    for lo1, hi1, lo2, hi2 in ((b1.xmin, b1.xmax, b2.xmin, b2.xmax), (b1.ymin, b1.ymax, b2.ymin, b2.ymax),
                               (b1.zmin, b1.zmax, b2.zmin, b2.zmax)):
        g = max(g, lo2 - hi1, lo1 - hi2)
    return g


def pair(a, sa, b, sb, near=3.0):
    if _bbox_gap(sa, sb) > near:
        return None
    vol = sa.intersect(sb).Volume()
    dist = 0.0 if vol > 1e-4 else sa.distance(sb)
    fit = _is_fit(a, b)
    if vol > 1e-3:
        status = "CLASH"
    elif dist < P.CLASH_MIN - 1e-6 and not fit:
        status = "TIGHT"
    else:
        status = "fit/contact" if fit and dist < P.CLASH_MIN - 1e-6 else "ok"
    return dict(a=a, b=b, vol=vol, dist=dist, status=status)


def run(parts, board):
    ps = {k: v.val() for k, v in parts.items()}
    bs = {k: v.val() for k, v in board.items() if v is not None}
    rows = []
    for (a, sa) in ps.items():
        for (b, sb) in bs.items():
            r = pair(a, sa, b, sb)
            if r:
                r["kind"] = "part-board"
                rows.append(r)
    for (a, sa), (b, sb) in itertools.combinations(ps.items(), 2):
        r = pair(a, sa, b, sb)
        if r:
            r["kind"] = "part-part"
            rows.append(r)
    # knob at full push (1.5 mm down) vs the shell and the encoder
    pushed = ps["knob"].translate((0, 0, -P.ENC_PUSH)) if hasattr(ps["knob"], "translate") else None
    if pushed is not None:
        for b, sb in (("top_shell", ps["top_shell"]),):
            r = pair("knob@full-push", pushed, b, sb)
            if r:
                r["kind"] = "motion"
                rows.append(r)
    # board vs board: OLED module / FPC bend vs J1 USB-C body
    special = []
    for b in ("OLED FPC bend", "OLED module PCB", "OLED back feature (band)"):
        r = pair(b, bs[b], "J1 USB-C body", bs["J1 USB-C body"], near=100)
        r["kind"] = "board-board"
        r["status"] = "CLASH" if r["vol"] > 1e-3 or r["dist"] < P.CLASH_MIN else "ok"
        special.append(r)
    # plan (XY) clearance FPC bend -> USB body
    fb, ub = bs["OLED FPC bend"].BoundingBox(), bs["J1 USB-C body"].BoundingBox()
    plan = fb.ymin - ub.ymax   # CAD Y: bend is north of the USB body
    mb = bs["OLED module PCB"].BoundingBox()
    return rows, special, dict(fpc_plan_clearance=plan, module_plan_clearance=mb.ymin - ub.ymax)


def report(rows, special, extra):
    lines = ["# Interference check", "",
             f"Board ref {P.BOARD['source_ref']}; clash threshold {P.CLASH_MIN} mm; "
             f"header {P.HEADER_H}, module {P.OLED_MODULE_T}, J2 y {P.J2_Y}, shaft tip {P.SHAFT_TOP}, knob H {P.KNOB_H}.", ""]
    bad = [r for r in rows if r["status"] in ("CLASH", "TIGHT")]
    lines.append(f"Pairs checked (bbox within 3 mm): {len(rows)}; CLASH/TIGHT: {len(bad)}")
    lines += ["", "| kind | A | B | min clearance (mm) | overlap (mm3) | status |", "|---|---|---|---|---|---|"]
    for r in sorted(rows, key=lambda r: (r["status"] not in ("CLASH", "TIGHT"), r["dist"])):
        if r["status"] in ("CLASH", "TIGHT") or r["dist"] < 1.0 or r["kind"] == "motion":
            lines.append(f"| {r['kind']} | {r['a']} | {r['b']} | {r['dist']:.2f} | {r['vol']:.3f} | {r['status']} |")
    lines += ["", "Rows with clearance >= 1.0 mm and no problem are omitted.", "",
              "## OLED vs USB-C (board-board)", "",
              "| A | B | min 3-D clearance (mm) | overlap (mm3) | status |", "|---|---|---|---|---|"]
    for r in special:
        lines.append(f"| {r['a']} | {r['b']} | {r['dist']:.2f} | {r['vol']:.3f} | {r['status']} |")
    lines += ["", f"- Module PCB edge -> USB-C body, plan: **{extra['module_plan_clearance']:+.2f} mm**",
              f"- FPC bend (far/south edge, {P.FPC_BEND_W} mm wide, {P.FPC_BEND_INSET} +- {P.FPC_BEND_TOL} mm "
              f"inside the outline, no wrap; modelled at the worst case) -> USB-C body, plan: "
              f"**{extra['fpc_plan_clearance']:+.2f} mm** "
              f"({'CLASH (< %.1f mm)' % P.CLASH_MIN if extra['fpc_plan_clearance'] < P.CLASH_MIN else 'ok'})",
              f"- J2 pin-row y {P.J2_Y} (from board_ref {P.BOARD['source_ref']})"]
    return "\n".join(lines) + "\n", bad
