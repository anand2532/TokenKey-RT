"""PNG renders from the exported STL meshes (trimesh + matplotlib, no GPU needed)."""
import numpy as np
import trimesh
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

COLORS = {"top_shell": (0.80, 0.82, 0.86), "bottom_tray": (0.30, 0.32, 0.36), "hatch_cover": (0.45, 0.47, 0.52),
          "knob": (0.62, 0.64, 0.68), "knob_sleeve": (0.85, 0.70, 0.30), "button_cap_btn1": (0.20, 0.45, 0.80),
          "button_cap_btn2": (0.20, 0.45, 0.80), "light_pipe": (0.85, 0.95, 1.0), "ballast": (0.55, 0.55, 0.55), "feet": (0.15, 0.15, 0.15),
          "board": (0.10, 0.55, 0.25), "oled": (0.05, 0.05, 0.08)}
LIGHT = np.array([0.4, -0.5, 0.75]); LIGHT /= np.linalg.norm(LIGHT)


def _col(name):
    for k, v in COLORS.items():
        if name.startswith(k):
            return v
    return (0.7, 0.7, 0.7)


def draw(meshes, path, elev, azim, offsets=None, title="", alpha=None, size=(9, 7)):
    fig = plt.figure(figsize=size, dpi=140)
    ax = fig.add_subplot(111, projection="3d")
    allv = []
    for name, m in meshes.items():
        m = m.copy()
        if offsets and name in offsets:
            m.apply_translation(offsets[name])
        tri = m.vertices[m.faces]
        shade = 0.45 + 0.55 * np.clip(m.face_normals @ LIGHT, 0, 1)
        base = np.array(_col(name))
        fc = np.clip(base[None, :] * shade[:, None], 0, 1)
        a = (alpha or {}).get(name, 1.0)
        pc = Poly3DCollection(tri, facecolors=np.c_[fc, np.full(len(fc), a)], edgecolors="none")
        ax.add_collection3d(pc)
        allv.append(m.vertices)
    v = np.vstack(allv)
    c, r = (v.max(0) + v.min(0)) / 2, (v.max(0) - v.min(0)).max() / 2
    ax.set_xlim(c[0] - r, c[0] + r); ax.set_ylim(c[1] - r, c[1] + r); ax.set_zlim(c[2] - r, c[2] + r)
    ax.set_box_aspect((1, 1, 1)); ax.view_init(elev=elev, azim=azim); ax.set_axis_off()
    ax.set_title(title, fontsize=10)
    fig.tight_layout(); fig.savefig(path); plt.close(fig)


def section(meshes, path, x, title):
    """Cut every mesh with the plane X = x and plot the YZ outlines (filled)."""
    fig, ax = plt.subplots(figsize=(12, 5), dpi=150)
    for name, m in meshes.items():
        s = m.section(plane_origin=[x, 0, 0], plane_normal=[1, 0, 0])
        if s is None:
            continue
        p2, T = s.to_2D(to_2D=trimesh.geometry.plane_transform([x, 0, 0], [1, 0, 0]))
        for poly in p2.polygons_full:
            pts = np.array(poly.exterior.coords)
            pts3 = trimesh.transform_points(np.c_[pts, np.zeros(len(pts))], T)
            ax.fill(pts3[:, 1], pts3[:, 2], color=_col(name), alpha=0.9 if not name.startswith("kz") else 0.5,
                    lw=0.4, ec="k")
            for hole in poly.interiors:
                h = np.array(hole.coords)
                h3 = trimesh.transform_points(np.c_[h, np.zeros(len(h))], T)
                ax.fill(h3[:, 1], h3[:, 2], color="white", lw=0.3, ec="k")
    ax.set_aspect("equal"); ax.set_xlabel("Y (mm, 0 = board south/rear edge)"); ax.set_ylabel("Z (mm, 0 = PCB top)")
    ax.set_title(title, fontsize=10); ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(path); plt.close(fig)


def draw_vtk(stls, path, elev, azim, offsets=None, title="", size=(1400, 1050), opacity=None):
    """Proper z-buffered render with VTK offscreen (falls back to draw() if VTK is unavailable)."""
    import vtk
    ren = vtk.vtkRenderer()
    ren.SetBackground(1, 1, 1)
    rw = vtk.vtkRenderWindow()
    rw.SetOffScreenRendering(1)
    rw.AddRenderer(ren)
    rw.SetSize(*size)
    for name, f in stls.items():
        rd = vtk.vtkSTLReader(); rd.SetFileName(f)
        nm = vtk.vtkPolyDataNormals(); nm.SetInputConnection(rd.GetOutputPort()); nm.SetFeatureAngle(35)
        mp = vtk.vtkPolyDataMapper(); mp.SetInputConnection(nm.GetOutputPort())
        a = vtk.vtkActor(); a.SetMapper(mp)
        a.GetProperty().SetColor(*_col(name))
        a.GetProperty().SetSpecular(0.2)
        if opacity and name in opacity:
            a.GetProperty().SetOpacity(opacity[name])
        if offsets and name in offsets:
            a.SetPosition(*offsets[name])
        ren.AddActor(a)
    if title:
        t = vtk.vtkTextActor(); t.SetInput(title); t.GetTextProperty().SetFontSize(22)
        t.GetTextProperty().SetColor(0.1, 0.1, 0.1); t.SetPosition(20, size[1] - 40); ren.AddActor2D(t)
    ren.ResetCamera()
    cam = ren.GetActiveCamera()
    cam.SetViewUp(0, 0, 1)
    fp = cam.GetFocalPoint()
    import math
    d = 200.0
    e, az = math.radians(elev), math.radians(azim)
    cam.SetPosition(fp[0] + d * math.cos(e) * math.cos(az), fp[1] + d * math.cos(e) * math.sin(az),
                    fp[2] + d * math.sin(e))
    cam.SetViewUp(0, 0, 1 if elev > -85 else 0)
    ren.ResetCamera(); cam.Zoom(1.25)
    rw.Render()
    w = vtk.vtkWindowToImageFilter(); w.SetInput(rw); w.Update()
    p = vtk.vtkPNGWriter(); p.SetFileName(path); p.SetInputConnection(w.GetOutputPort()); p.Write()
