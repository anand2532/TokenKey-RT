#!/usr/bin/env python3
"""Regenerate the Direction A puck: STEP/STL per part, assembly STEP, interference report, renders.

  python3 build.py              # default (stock EC11E shaft, 16.5 mm knob, header 3.0, module 2.65)
Environment overrides: TK_PROCESS (FDM|SLA), TK_HEADER, TK_MODULE_T, TK_SHAFT_TRIM (evaluation only), TK_KNOB_H,
TK_KNOB_D, TK_DKEY_MARGIN,
TK_KNOB_INSERT (none|sleeve|setscrew).
"""
import json, os, sys
import cadquery as cq
import trimesh
import params as P
import parts as PT
import board_model as BM
import checks
import render

ENC = os.path.dirname(P.HERE)
EXP, REN = os.path.join(ENC, "exports"), os.path.join(ENC, "renders")


def mass(parts):
    m = {}
    for k, v in parts.items():
        vol = v.val().Volume() / 1000.0
        if k == "ballast":
            m[k] = vol * P.BALLAST_RHO
        elif k == "feet":
            m[k] = vol * P.FOOT_RHO
        elif k == "knob_sleeve":
            m[k] = vol * 8.5
        elif k in ("top_shell", "bottom_tray", "hatch_cover"):
            m[k] = vol * P.RHO[P.PROCESS] * (P.FDM_FILL_FACTOR if P.PROCESS == "FDM" else 1.0)
        else:
            m[k] = vol * P.RHO["SLA"]
    m["PCBA (estimate)"] = P.PCBA_MASS
    m["4x M2x8 screws + inserts"] = 4 * 0.6
    return m


def plate_summary():
    import plate
    s = plate.outline()
    x0, y0, x1, y1 = s.bounds
    return dict(t=P.PLATE_T, area_mm2=round(s.area, 1), extent_kicad=[round(v, 2) for v in (x0, y0, x1, y1)],
                extent_mm=[round(x1 - x0, 2), round(y1 - y0, 2)], cutouts=len(s.interiors),
                mass_g=round(s.area * P.PLATE_T * P.BALLAST_RHO / 1000, 1),
                top_to_pcb_bottom=round(P.Z_PCB_BOT - P.Z_FLOOR_TOP - P.PLATE_T, 2))


def foot_walls():
    """Min plan material between each foot pocket and the tray edge / every other floor opening."""
    from shapely.geometry import Point, box as sbox
    r = P.FOOT_D / 2 + P.FOOT_POCKET_CLR
    holes = [Point(*P.K(*f["pos"])).buffer(P.SCREW_HEAD_CB_D / 2) for f in P.BOARD["footprints"]
             if f["fp"].startswith("MountingHole")]
    holes.append(Point(*P.K(*P.fp("SW1")["pos"])).buffer(P.BOOT_HOLE_D / 2 + 0.6))
    hx, hy = P.K(*P.HATCH_CENTRE_K); w, h = P.HATCH; rc = P.HATCH_RECESS
    hatch = sbox(hx - w / 2 - rc, hy - h / 2 - rc, hx + w / 2 + rc, hy + h / 2 + rc)
    cover_plug = sbox(hx - w / 2 + 0.1, hy - h / 2 + 0.1, hx + w / 2 - 0.1, hy + h / 2 - 0.1)
    outer = sbox(P.OUT_X0, P.OUT_Y0, P.OUT_X0 + P.OUT_W, P.OUT_Y0 + P.OUT_D)
    out = {}
    for n, (x, y) in P.FEET.items():
        c = Point(x, y).buffer(r)
        if n == "NE_cover":
            d = cover_plug.exterior.distance(c) if cover_plug.contains(c) else -1.0
        else:
            d = min([outer.exterior.distance(c) if outer.contains(c) else -1.0] +
                    [c.distance(o) for o in holes + [hatch]])
        out[n] = round(d, 2)
    return out


def support_margins():
    """Plan distance (mm, + = inside) of the knob axis and button centres from the feet's support polygon."""
    from shapely.geometry import MultiPoint, Point
    hull = MultiPoint(list(P.FEET.values())).convex_hull
    pts = {"knob axis": PT.enc_xy(), "SW3": PT.btn_xy()[0], "SW4": PT.btn_xy()[1]}
    return {k: round(hull.exterior.distance(Point(v)) * (1 if hull.contains(Point(v)) else -1), 2)
            for k, v in pts.items()}


def tip_forces(parts, m):
    """For points outside the support polygon: the vertical press (N) that would start to tip the puck,
    = weight x (COM distance to the nearest hull edge) / (point's distance outside that edge)."""
    from shapely.geometry import MultiPoint, Point, LineString
    hull = MultiPoint(list(P.FEET.values())).convex_hull
    tot, cx, cy = 0.0, 0.0, 0.0
    for k, v in parts.items():
        c = v.val().Center(); w = m[k]; tot += w; cx += w * c.x; cy += w * c.y
    extra = m["PCBA (estimate)"] + m["4x M2x8 screws + inserts"]
    tot += extra; cx += extra * P.PCB_W / 2; cy += extra * P.PCB_D / 2
    com = Point(cx / tot, cy / tot)
    W = tot / 1000 * 9.81
    out = {"com_cad": [round(com.x, 1), round(com.y, 1)]}
    pts = {"knob axis": PT.enc_xy(), "SW3": PT.btn_xy()[0], "SW4": PT.btn_xy()[1]}
    c = list(hull.exterior.coords)
    for k, v in pts.items():
        p = Point(v)
        if hull.contains(p):
            out[k] = "inside"
            continue
        best = None
        for a, b in zip(c, c[1:]):
            e = LineString([a, b])
            # signed distances to the infinite edge line
            (x1, y1), (x2, y2) = a, b
            L = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
            sd = lambda q: ((x2 - x1) * (q.y - y1) - (y2 - y1) * (q.x - x1)) / L
            if sd(p) * sd(com) < 0:            # point and COM on opposite sides of this edge
                f = W * abs(sd(com)) / abs(sd(p))
                best = f if best is None else min(best, f)
        out[k] = round(best, 2)
    return out


def write_plate_dxf(path):
    import plate
    s = plate.outline()
    lines = ["0", "SECTION", "2", "ENTITIES"]
    for ring in [s.exterior] + list(s.interiors):
        c = list(ring.coords)
        for (xa, ya), (xb, yb) in zip(c, c[1:]):      # KiCad coords, mm, y down as on the board
            lines += ["0", "LINE", "8", "PLATE", "10", f"{xa:.4f}", "20", f"{-ya:.4f}", "11", f"{xb:.4f}", "21", f"{-yb:.4f}"]
    lines += ["0", "ENDSEC", "0", "EOF"]
    open(path, "w").write("\n".join(lines) + "\n")


def main():
    check_only = "--check-only" in sys.argv
    print("engagement", P.ENGAGEMENT, "knob top above PCB", P.KNOB_TOP)
    parts = PT.build_all()
    board = BM.build()
    rows, special, extra = checks.run(parts, board)
    txt, bad = checks.report(rows, special, extra)
    m = mass(parts)
    summary = dict(
        board_ref=P.BOARD["source_ref"], process=P.PROCESS,
        outer_mm=[P.OUT_W, P.OUT_D, round(P.BODY_H, 2)],
        z=dict(desk=round(P.Z_DESK, 3), floor_top=P.Z_FLOOR_TOP, pcb_bottom=P.Z_PCB_BOT, oled_top=P.OLED_TOP,
               lid_under=P.LID_UNDER, lid_top=P.LID_TOP, collar_top=P.COLLAR_TOP,
               knob_bottom=P.KNOB_BOTTOM, knob_top=P.KNOB_TOP, shaft_top=P.SHAFT_TOP),
        j2_y=P.J2_Y,
        encoder=dict(body_h=P.ENC_BODY[2], shaft_tip=P.SHAFT_TOP, shaft_tip_pressed=P.SHAFT_TOP - P.ENC_PUSH,
                     flat_start=P.FLAT_START, trim=P.SHAFT_TRIM,
                     body_to_lid_underside=round(P.LID_UNDER - P.ENC_BODY[2], 2)),
        knob=dict(shaft_tip=P.SHAFT_TOP, height=P.KNOB_H, height_min=round(P.KNOB_H_MIN, 2), dia=P.KNOB_D,
                  insert=P.KNOB_INSERT, dkey_start=P.KNOB_POCKET_TOP, collar_top=P.COLLAR_TOP,
                  collar_overlap_rest=round(P.COLLAR_TOP - P.KNOB_BOTTOM, 2),
                  full_push_skirt_to_lid=round(P.KNOB_BOTTOM - P.ENC_PUSH - P.LID_TOP, 2),
                  full_push_pocket_to_collar=round(P.KNOB_POCKET_TOP - P.ENC_PUSH - P.COLLAR_TOP, 2),
                  engagement=round(P.ENGAGEMENT, 2),
                  top_above_desk=round(P.KNOB_TOP - P.Z_DESK, 2),
                  top_above_desk_on_feet=round(P.KNOB_TOP - P.Z_DESK + P.FOOT_PROUD, 2)),
        stems=dict(button_cap_len=round(P.LID_TOP + P.CAP_PROUD - (P.B3U_H + P.CAP_FREE), 2),
                   light_pipe_len=round(P.LID_TOP - (P.LED_H + P.PIPE_GAP), 2),
                   cap_travel_to_stop=round(P.CAP_FREE + P.B3U_STROKE + P.CAP_STOP_EXTRA, 3)),
        usb_overmold_to_receptacle_face=round(P.BOARD_CLR + P.USB_SKIN, 2),
        mass_g={k: round(v, 1) for k, v in m.items()}, mass_total_g=round(sum(m.values()), 1),
        overall_on_feet_mm=round(P.BODY_H + P.FOOT_PROUD, 2),
        feet=dict(n=len(P.FEET), d=P.FOOT_D, h=P.FOOT_H, pocket_depth=P.FOOT_POCKET_DEPTH, proud=P.FOOT_PROUD,
                  centres_cad=P.FEET),
        plate=plate_summary(), foot_min_wall=foot_walls(), support_margin=support_margins(), tip_press_N=tip_forces(parts, m), checks_bad=len(bad), fpc_plan_clearance=round(extra["fpc_plan_clearance"], 3),
        module_plan_clearance=round(extra["module_plan_clearance"], 3),
        board_unknown_heights=BM.build.unknown)
    print(json.dumps(summary, indent=1))
    bad_walls = {k: v for k, v in summary["foot_min_wall"].items() if v < P.FOOT_MIN_WALL}
    if bad_walls:
        bad.append(dict(a="foot pocket wall", b=str(bad_walls), dist=min(bad_walls.values()), vol=0, status="TIGHT", kind="floor"))
        summary["checks_bad"] = len(bad)
    if P.ENGAGEMENT < P.MIN_ENGAGEMENT:
        print(f"WARNING: shaft engagement {P.ENGAGEMENT:.2f} < {P.MIN_ENGAGEMENT}")
    if check_only:
        print(txt)
        return
    os.makedirs(EXP, exist_ok=True); os.makedirs(REN, exist_ok=True)
    with open(os.path.join(EXP, "interference_report.md"), "w") as f:
        f.write(txt)
    with open(os.path.join(EXP, "summary.json"), "w") as f:
        json.dump(summary, f, indent=1)
    write_plate_dxf(os.path.join(EXP, "ballast_plate.dxf"))
    asm = cq.Assembly(name="tokenkey_rt_puck")
    meshes = {}
    for k, v in parts.items():
        cq.exporters.export(v, os.path.join(EXP, f"{k}.step"))
        stl = os.path.join(EXP, f"{k}.stl")
        cq.exporters.export(v, stl, tolerance=0.02, angularTolerance=0.2)
        meshes[k] = trimesh.load(stl)
        asm.add(v, name=k, color=cq.Color(*render._col(k)))
    # board keep-out model (reference only) into the assembly + its own STEP
    pcb = board["pcb"]
    comp = None
    for k, v in board.items():
        if k != "pcb" and v is not None:
            comp = v if comp is None else comp.union(v)
    asm.add(pcb, name="ref_pcb", color=cq.Color(*render.COLORS["board"]))
    asm.add(comp, name="ref_components_keepout", color=cq.Color(0.15, 0.15, 0.18))
    asm.save(os.path.join(EXP, "assembly.step"))
    cq.exporters.export(pcb.union(comp), os.path.join(EXP, "board_keepout.step"))
    refdir = os.path.join(EXP, "_ref"); os.makedirs(refdir, exist_ok=True)
    stls = {k: os.path.join(EXP, f"{k}.stl") for k in parts}
    ref_stls = {"board": os.path.join(refdir, "board.stl"), "oled_components": os.path.join(refdir, "comp.stl")}
    cq.exporters.export(pcb, ref_stls["board"], tolerance=0.05)
    cq.exporters.export(comp, ref_stls["oled_components"], tolerance=0.05)
    meshes_ref = {k: trimesh.load(v) for k, v in ref_stls.items()}
    allm = dict(meshes); allm.update(meshes_ref)
    off = {"top_shell": (0, 0, 22), "knob": (0, 0, 40), "knob_sleeve": (0, 0, 40),
           "button_cap_btn1": (0, 0, 30), "button_cap_btn2": (0, 0, 30), "light_pipe": (0, 0, 30),
           "hatch_cover": (0, 0, -16), "ballast": (0, 0, -6), "bottom_tray": (0, 0, -10), "feet": (0, 0, -22)}
    try:
        render.draw_vtk(stls, os.path.join(REN, "iso.png"), 32, 115, title="TokenKey RT puck (Direction A), isometric, user side")
        render.draw_vtk({**stls, **ref_stls}, os.path.join(REN, "exploded.png"), 20, 115, offsets=off,
                        title="Exploded: knob+sleeve, caps/pipe, top shell, board keep-outs, ballast, tray, hatch cover",
                        size=(1400, 1600))
        render.draw_vtk(stls, os.path.join(REN, "bottom.png"), -60, 115,
                        title="Bottom: M2 counterbores, TC2030/UART hatch cover, BOOT pinhole, silicone feet")
        render.draw_vtk(stls, os.path.join(REN, "rear.png"), 18, -105, title="Rear (south) face: USB-C pocket")
    except Exception as ex:  # no OpenGL: painter's-algorithm fallback
        print("VTK render failed, using matplotlib:", ex)
        render.draw(meshes, os.path.join(REN, "iso.png"), 28, -125)
        render.draw(allm, os.path.join(REN, "exploded.png"), 22, -125, offsets=off, size=(9, 10))
        render.draw(meshes, os.path.join(REN, "bottom.png"), -60, 115)
    xs = P.fp("J1")["pos"][0]
    import shutil; shutil.rmtree(refdir, ignore_errors=True)
    render.section(allm, os.path.join(REN, "section_oled_usbc.png"), xs,
                   f"Section X = {xs} (USB-C centreline, through the OLED window and FPC bend)")
    print("CLASH/TIGHT rows:", len(bad))
    for r in bad:
        print("  ", r)


if __name__ == "__main__":
    main()
