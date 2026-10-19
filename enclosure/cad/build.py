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
        elif k == "knob_sleeve":
            m[k] = vol * 8.5
        elif k in ("top_shell", "bottom_tray", "hatch_cover"):
            m[k] = vol * P.RHO[P.PROCESS] * (P.FDM_FILL_FACTOR if P.PROCESS == "FDM" else 1.0)
        else:
            m[k] = vol * P.RHO["SLA"]
    m["PCBA (estimate)"] = P.PCBA_MASS
    m["4x M2x8 screws + inserts"] = 4 * 0.6
    return m


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
                  top_above_desk_with_grip_cord=round(P.KNOB_TOP - P.Z_DESK + P.GRIP_CORD_PROUD, 2)),
        stems=dict(button_cap_len=round(P.LID_TOP + P.CAP_PROUD - (P.B3U_H + P.CAP_FREE), 2),
                   light_pipe_len=round(P.LID_TOP - (P.LED_H + P.PIPE_GAP), 2),
                   cap_travel_to_stop=round(P.CAP_FREE + P.B3U_STROKE + P.CAP_STOP_EXTRA, 3)),
        usb_overmold_to_receptacle_face=round(P.BOARD_CLR + P.USB_SKIN, 2),
        mass_g={k: round(v, 1) for k, v in m.items()}, mass_total_g=round(sum(m.values()), 1),
        mass_target_g=P.MASS_TARGET, checks_bad=len(bad), fpc_plan_clearance=round(extra["fpc_plan_clearance"], 3),
        module_plan_clearance=round(extra["module_plan_clearance"], 3),
        board_unknown_heights=BM.build.unknown)
    print(json.dumps(summary, indent=1))
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
           "hatch_cover": (0, 0, -16), "ballast": (0, 0, -6), "bottom_tray": (0, 0, -10)}
    try:
        render.draw_vtk(stls, os.path.join(REN, "iso.png"), 32, 115, title="TokenKey RT puck (Direction A), isometric, user side")
        render.draw_vtk({**stls, **ref_stls}, os.path.join(REN, "exploded.png"), 20, 115, offsets=off,
                        title="Exploded: knob+sleeve, caps/pipe, top shell, board keep-outs, ballast, tray, hatch cover",
                        size=(1400, 1600))
        render.draw_vtk(stls, os.path.join(REN, "bottom.png"), -60, 115,
                        title="Bottom: M2 counterbores, TC2030/UART hatch cover, BOOT pinhole, grip groove")
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
