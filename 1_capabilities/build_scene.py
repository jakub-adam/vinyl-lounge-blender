"""build_scene.py - builds the complete "Vinyl Lounge" interior.

    python build_scene.py            (with the `bpy` 5.2 module)
    blender -b -P build_scene.py     (or inside Blender 5.2)

Outputs (out/):
    4SA1_Claude_Interier_v01.blend   scene, textures packed
    4SA1_Claude_Interier_v01.glb     glTF binary, +Y up
    layout.json                      object footprints (used by concept_board.py)

Conventions
    * metres, Blender Z-up; room interior x 0..6.0, y 0..5.2, z 0..3.0
    * every furniture/prop is modelled in local space with its front facing -Y
      and its origin on the floor/contact point, then placed with loc + rotZ
    * FURN_* = furniture, GRAB_* = grabbable props (custom property grabbable=1),
      ARCH_* = architecture; front + right walls are hidden from the camera
"""
import os
import sys
import math
import json
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

import numpy as np                       # noqa: E402
import bpy                               # noqa: E402
from mathutils import Vector, Matrix     # noqa: E402

from lib import mk, mats                 # noqa: E402
from lib.mk import (box, rbox, cushion, lathe, sweep, bezier,   # noqa: E402
                    solidify2d, grid2d)

BASENAME = "4SA1_Claude_Interier_v01"
OUT = os.path.join(ROOT, "out")
RW, RD, RH, WT = 6.0, 5.2, 3.0, 0.2          # room width/depth/height, wall thickness
WIN = dict(cx=2.75, w=1.3, z0=0.9, zs=2.05)  # arched window in left-wall local u (u = y + WT)

T0 = time.time()
COL = {}


def log(*a):
    print(f"[{time.time() - T0:6.1f}s]", *a, flush=True)


# ============================================================== setup =======
def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    mk.set_material_resolver(mats.get, mats.tile_of)
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    for name in ("Architecture", "Furniture", "Grabbables", "Lighting", "Camera"):
        c = bpy.data.collections.new(name)
        sc.collection.children.link(c)
        COL[name] = c


def new_obj(name, parts, loc=(0, 0, 0), rz=0.0, col="Furniture", **props):
    ob = mk.build_object(name, parts, loc, rz, COL[col])
    cat = {"Furniture": "furniture", "Grabbables": "grabbable",
           "Architecture": "architecture"}.get(col, col.lower())
    ob["category"] = cat
    if col == "Grabbables":
        ob["grabbable"] = 1
    for k, v in props.items():
        ob[k] = v
    return ob


def U(mat, rot=0.0):
    """box-UV spec using the material's tile size, optional rotation (grain)."""
    return ("box", mats.tile_of(mat), rot)


def leg(h, r_bot, r_top, x=0.0, y=0.0, z=0.0, mat="walnut", m=3, ferrule="brass"):
    """Tapered turned leg (+ metal ferrule at the foot)."""
    ps = [lathe([(r_bot, 0.0), (r_top, h)], m, mat=mat, uv=U(mat, 90)).bake().move(x, y, z)]
    if ferrule:
        rf = (r_bot + (r_top - r_bot) * 0.04 / h) * 1.14
        ps.append(lathe([(rf, 0.0), (rf, 0.04)], m, mat=ferrule).move(x, y, z))
    return ps


def sleeve(i, w=0.315, t=0.004):
    """Record sleeve in the XZ plane (cover facing -Y), centred on origin."""
    p = box(w, t, w, mat=f"cover{i % 6}", uv=("fit", "y")).bake()
    return p.by_normal(lambda n, c: abs(n[1]) > 0.9, f"cover{i % 6}", "cardboard")


def disc(k, r=0.1505, t=0.0016):
    """Vinyl record lying in the XY plane, centred on origin."""
    p = lathe([(r, -t / 2), (r, t / 2)], m=8, mat=f"vinyl{k}", uv=("fit", "z")).bake()
    return p.by_normal(lambda n, c: abs(n[2]) > 0.9, f"vinyl{k}", "vinyl_black")


def is_up(n, c):
    return n[2] > 0.9


# ======================================================= architecture =======
def architecture():
    # ---------------- floor: herringbone field + walnut border frieze -------
    b, FT = 0.16, 0.15
    parts = []
    fld = box(RW - 2 * b, RD - 2 * b, FT, mat="parquet", uv=("box", 0.7, -45)).bake()
    parts.append(fld.by_normal(is_up, "parquet", "section").move(RW / 2, RD / 2, -FT / 2))
    for (sx, sy, cx, cy, rot) in [
            (RW + 2 * WT, b + WT, RW / 2, RD - b + (b + WT) / 2, 0),
            (RW + 2 * WT, b + WT, RW / 2, -WT + (b + WT) / 2, 0),
            (b + WT, RD - 2 * b, -WT + (b + WT) / 2, RD / 2, 90),
            (b + WT, RD - 2 * b, RW - b + (b + WT) / 2, RD / 2, 90)]:
        s = box(sx, sy, FT, mat="walnut", uv=U("walnut", rot)).bake()
        parts.append(s.by_normal(is_up, "walnut", "section").move(cx, cy, -FT / 2))
    new_obj("ARCH_Floor", parts, col="Architecture")

    # ---------------- ceiling ----------------------------------------------
    c = box(RW + 2 * WT, RD + 2 * WT, 0.12, mat="plaster_ceiling", segs=(6, 5, 1)).bake()
    c.by_normal(lambda n, cc: n[2] < -0.9, "plaster_ceiling", "section").move(RW / 2, RD / 2, RH + 0.06)
    new_obj("ARCH_Ceiling", [c], col="Architecture")

    # ---------------- walls (plaster + section ends + skirting + cornice) ---
    def wall_parts(W, pts, faces):
        p = solidify2d(pts, faces, WT, mat="plaster").bake()
        end = lambda n, cc: (abs(n[0]) > 0.9 and (cc[0] < 1e-3 or cc[0] > W - 1e-3)) or n[2] > 0.9
        return p.by_normal(end, "section", "plaster")

    def trims(axis_pts, skirting_box):
        sk = box(*skirting_box[0], mat="paint_green", uv=U("paint_green", skirting_box[2])).bake()
        sk.move(*skirting_box[1])
        co = sweep(axis_pts, 0.055, m=4, mat="paint_white")
        return [sk, co]

    # back wall (y = RD .. RD+WT)
    W = RW + 2 * WT
    pts, f = grid2d(0, W, 0, RH, 16, 6)
    p = wall_parts(W, pts, f).move(-WT, RD, 0)
    new_obj("ARCH_Wall_Back", [p] + trims([(0, RD, RH), (RW, RD, RH)],
                                          ((RW, 0.016, 0.09), (RW / 2, RD - 0.008, 0.045), 0)),
            col="Architecture")
    # front wall (hidden from camera)
    p = wall_parts(W, pts, f).move(-WT, -WT, 0)
    ob = new_obj("ARCH_Wall_Front", [p] + trims([(0, 0, RH), (RW, 0, RH)],
                                                ((RW, 0.016, 0.09), (RW / 2, 0.008, 0.045), 0)),
                 col="Architecture", hidden_from_camera=1)
    ob.visible_camera = False
    # right wall (hidden from camera)
    W2 = RD + 2 * WT
    pts2, f2 = grid2d(0, W2, 0, RH, 14, 6)
    p = wall_parts(W2, pts2, f2).rot("z", 90).move(RW + WT, -WT, 0)
    ob = new_obj("ARCH_Wall_Right", [p] + trims([(RW, 0, RH), (RW, RD, RH)],
                                                ((0.016, RD, 0.09), (RW - 0.008, RD / 2, 0.045), 90)),
                 col="Architecture", hidden_from_camera=1)
    ob.visible_camera = False
    # left wall with the arched window opening
    pts3, f3, hole = mk.arch_wall_2d(W2, RH, WIN["cx"], WIN["w"], WIN["z0"], WIN["zs"],
                                     margin=0.25, nX=15, nZ_low=9, nZ_arch=10, rings=3,
                                     side_div=6, low_div=3, top_div=1)
    p = wall_parts(W2, pts3, f3)
    # marble window board (interior sill), in wall-local coords then rotated with the wall
    sill = box(WIN["w"] + 0.12, 0.11, 0.03, mat="marble").bake().move(WIN["cx"], 0.03 - 0.035, WIN["z0"] - 0.015)
    sill = sill.by_normal(lambda n, cc: True, "marble")
    for q in (p, sill):
        q.rot("z", 90).move(0, -WT, 0)
    new_obj("ARCH_Wall_Left", [p, sill] + trims([(0, 0, RH), (0, RD, RH)],
                                                ((0.016, RD, 0.09), (0.008, RD / 2, 0.045), 90)),
            col="Architecture")
    window(pts3[hole])

    # ---------------- exterior backdrop (emissive billboard) ----------------
    bd = box(0.02, 16, 8, mat="backdrop", uv=("fit", "x")).bake()
    bd.by_normal(lambda n, cc: n[0] > 0.9, "backdrop", "plastic_black").move(-4.5, 3.0, 2.2)
    ob = new_obj("ENV_Backdrop", [bd], col="Architecture")
    ob.visible_shadow = False

    # ---------------- slatted oak acoustic wall behind the credenza ---------
    sx0, sx1, z0, z1 = 2.0, 4.6, 0.12, 2.72
    parts = [box(sx1 - sx0, 0.012, z1 - z0, mat="felt").bake().move((sx0 + sx1) / 2, RD - 0.006, (z0 + z1) / 2)]
    n = int((sx1 - sx0) / 0.07)
    pitch = (sx1 - sx0) / n
    for i in range(n):
        x = sx0 + pitch * (i + 0.5)
        parts.append(box(0.045, 0.022, z1 - z0, mat="oak", uv=U("oak", 90)).bake()
                     .move(x, RD - 0.012 - 0.011, (z0 + z1) / 2))
    new_obj("ARCH_SlatWall", parts, col="Architecture")


def window(hole_pts):
    """Arched casement: painted frame ring, mullions, brass handle + glass pane."""
    cx, w, z0, zs = WIN["cx"], WIN["w"], WIN["z0"], WIN["zs"]
    r, f, fd, w0 = w / 2, 0.06, 0.07, 0.065
    c = np.array([cx, zs])

    def shrink(p):
        d = np.array(p) - c
        if d[1] >= -1e-9:
            return c + d / np.linalg.norm(d) * (r - f)
        ts = [(r - f) / abs(d[0])] if abs(d[0]) > 1e-9 else []
        ts.append((z0 + f - zs) / d[1])
        return c + d * min(ts)

    n = len(hole_pts)
    inner = np.array([shrink(p) for p in hole_pts])
    ring_pts = np.vstack([hole_pts, inner])
    faces = [(k, (k + 1) % n, n + (k + 1) % n, n + k) for k in range(n)]
    frame = solidify2d(ring_pts, faces, fd, mat="paint_green").bake().move(0, w0, 0)
    vbar = box(0.045, 0.05, (zs + r - f) - (z0 + f) + 0.02, mat="paint_green", uv=U("paint_green", 90)).bake()
    vbar.move(cx, w0 + fd / 2, (z0 + f + zs + r - f) / 2)
    hbar = box(2 * (r - f) + 0.02, 0.05, 0.045, mat="paint_green").bake().move(cx, w0 + fd / 2, zs)
    knob = lathe([(0.007, 0.0), (0.007, 0.02), (0.012, 0.028), (0.012, 0.04)], m=3, mat="brass")
    knob.rot("x", 90).move(cx, w0 + fd / 2 - 0.025, 1.45)
    lever = box(0.012, 0.012, 0.09, mat="brass").move(cx, w0 + fd / 2 - 0.025 - 0.036, 1.45 - 0.04)
    parts = [frame, vbar, hbar, knob, lever]
    for p in parts:
        p.rot("z", 90).move(0, -WT, 0)
    new_obj("ARCH_Window", parts, col="Architecture")

    gp, gf = mk.arch_pane_2d(cx, 2 * (r - f) + 0.02, z0 + f - 0.01, zs, nx=8, nz=6)
    glass = solidify2d(gp, gf, 0.008, mat="glass").bake()
    glass.by_normal(lambda n_, cc: abs(n_[1]) > 0.9, "glass", "rubber")
    glass.move(0, w0 + fd / 2 - 0.004, 0).rot("z", 90).move(0, -WT, 0)
    ob = new_obj("ARCH_WindowGlass", [glass], col="Architecture")
    ob.visible_shadow = False          # let the sun through (no caustics needed)


# ========================================================== furniture =======
def sofa():
    L, D = 2.2, 0.92
    P = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            P += leg(0.15, 0.015, 0.024, x=sx * (L / 2 - 0.1), y=sy * (D / 2 - 0.09))
    P.append(rbox(L, D, 0.08, 0.01, mat="walnut").bake().move(0, 0, 0.19))
    for sx in (-1, 1):
        P.append(rbox(0.15, D, 0.42, 0.04, mat="boucle", segs=(1, 3, 2)).move(sx * (L / 2 - 0.075), 0, 0.44))
    P.append(rbox(L - 0.3, 0.17, 0.5, 0.04, mat="boucle", segs=(4, 1, 2)).move(0, D / 2 - 0.085, 0.48))
    P.append(rbox(L - 0.3, D - 0.17, 0.06, 0.02, mat="boucle", segs=(4, 4, 1)).move(0, -0.085, 0.26))
    cw = (L - 0.3) / 3
    for i in range(3):
        x = -cw + i * cw
        P.append(cushion(cw - 0.006, D - 0.19, 0.15, r=0.045, mat="boucle", segs=(5, 5, 2),
                         puff=0.018, level=1).move(x, -0.095, 0.365))
        bc = cushion(cw - 0.01, 0.40, 0.17, r=0.05, mat="boucle", segs=(5, 4, 2), puff=0.02, level=1)
        P.append(bc.rot("x", 78).move(x, D / 2 - 0.24, 0.64))
    pil = cushion(0.42, 0.42, 0.12, r=0.07, mat="cloth_ochre", segs=(4, 4, 1), puff=0.045, level=2)
    P.append(pil.rot("x", 72).rot("z", -18).move(L / 2 - 0.32, D / 2 - 0.34, 0.65))
    pil2 = cushion(0.38, 0.38, 0.11, r=0.065, mat="cloth_teal", segs=(4, 4, 1), puff=0.04, level=2)
    P.append(pil2.rot("x", 70).rot("z", 14).move(-L / 2 + 0.3, D / 2 - 0.34, 0.64))
    return P


def armchair():
    P = []
    s1 = bezier((0, -0.36, 0.0), (0, -0.35, 0.3), (0, -0.345, 0.55), (0, -0.25, 0.585), 10)
    s2 = bezier((0, -0.25, 0.585), (0, -0.05, 0.605), (0, 0.12, 0.6), (0, 0.22, 0.56), 8)
    s3 = bezier((0, 0.22, 0.56), (0, 0.31, 0.5), (0, 0.36, 0.25), (0, 0.39, 0.0), 10)
    path = np.vstack([s1, s2[1:], s3[1:]])
    for sx in (-1, 1):
        P.append(sweep(path + np.array([sx * 0.36, 0, 0]), 0.024, m=2, mat="walnut").bake())
        for y in (-0.36, 0.39):
            P.append(lathe([(0.022, 0.0), (0.022, 0.008)], m=3, mat="brass").move(sx * 0.36, y, 0))
    for (y, z) in ((-0.354, 0.2), (0.372, 0.2)):
        P.append(sweep([(-0.36, y, z), (0.36, y, z)], 0.014, m=2, mat="walnut").bake())
    P.append(rbox(0.70, 0.62, 0.03, 0.006, mat="walnut").bake().move(0, -0.03, 0.25))
    P.append(cushion(0.68, 0.64, 0.13, r=0.045, mat="leather", segs=(5, 5, 2), puff=0.015, level=1)
             .rot("x", -4).move(0, -0.04, 0.33))
    shell = rbox(0.70, 0.022, 0.60, 0.008, mat="walnut").bake()
    P.append(shell.rot("x", -16).move(0, 0.343, 0.558))
    bc = cushion(0.64, 0.52, 0.12, r=0.05, mat="leather", segs=(5, 4, 2), puff=0.02, level=1)
    P.append(bc.rot("x", 74).move(0, 0.297, 0.655))
    return P


def coffee_table():
    P = [lathe([(0.43, 0.36), (0.448, 0.366), (0.45, 0.378), (0.448, 0.39), (0.44, 0.396)],
               m=12, mat="marble")]
    P.append(lathe([(0.30, 0.30), (0.33, 0.30), (0.33, 0.36), (0.30, 0.36)], m=10, closed=True,
                   mat="walnut"))
    for k in range(4):
        a = math.radians(45 + 90 * k)
        P += leg(0.30, 0.016, 0.026, x=0.315 * math.cos(a), y=0.315 * math.sin(a))
    ring = [(0.315 + 0.007 * math.cos(t), 0.1 + 0.007 * math.sin(t))
            for t in np.linspace(0, 2 * math.pi, 8, endpoint=False)]
    P.append(lathe(ring, m=10, closed=True, mat="brass"))
    return P


def side_table():
    return [lathe([(0.21, 0.5), (0.22, 0.505), (0.22, 0.52), (0.214, 0.526)], m=10, mat="walnut"),
            lathe([(0.016, 0.04), (0.016, 0.5)], m=3, mat="brass"),
            lathe([(0.155, 0.0), (0.16, 0.006), (0.16, 0.034), (0.15, 0.04)], m=10, mat="marble")]


def credenza():
    L, D, z0, z1 = 2.1, 0.45, 0.16, 0.66
    P = []
    P.append(rbox(L, D, 0.025, 0.004, mat="walnut").bake().move(0, 0, z1 - 0.0125))
    P.append(rbox(L - 0.05, D - 0.02, 0.02, 0.003, mat="walnut").bake().move(0, 0.01, z0 + 0.01))
    hin = z1 - z0 - 0.025
    for sx in (-1, 1):
        P.append(rbox(0.025, D, hin, 0.004, mat="walnut").bake().move(sx * (L / 2 - 0.0125), 0, z0 + hin / 2))
        P.append(rbox(0.02, D - 0.03, hin - 0.02, 0.003, mat="walnut").bake().move(sx * 0.35, 0.0, z0 + 0.02 + (hin - 0.02) / 2))
    P.append(box(L - 0.05, 0.012, hin, mat="walnut").bake().move(0, D / 2 - 0.006, z0 + hin / 2))
    # fluted doors (left/right bays)
    for sx in (-1, 1):
        xa, xb = sorted((sx * 0.36, sx * (L / 2 - 0.025)))
        dw = xb - xa - 0.006
        xc = (xa + xb) / 2
        P.append(rbox(dw, 0.018, hin - 0.03, 0.003, mat="walnut").bake().move(xc, -D / 2 + 0.009, z0 + 0.02 + (hin - 0.03) / 2))
        nfl = int(dw / 0.026)
        for i in range(nfl):
            x = xc - dw / 2 + dw / nfl * (i + 0.5)
            P.append(sweep([(x, -D / 2, z0 + 0.03), (x, -D / 2, z1 - 0.04)], 0.0135, m=2,
                           mat="walnut", uv=U("walnut", 90), profile_scale=(0.45, 1.0)).bake())
        kx = xb - 0.05 if sx < 0 else xa + 0.05
        knob = lathe([(0.008, 0.0), (0.008, 0.012), (0.016, 0.018), (0.016, 0.026)], m=3, mat="brass")
        P.append(knob.rot("x", 90).move(kx, -D / 2 - 0.004, z0 + 0.25))
    for sx in (-1, 1):
        for sy in (-1, 1):
            P += leg(z0, 0.014, 0.022, x=sx * (L / 2 - 0.12), y=sy * (D / 2 - 0.08))
    # records stored upright in the open middle bay, spines to the front
    rng = np.random.default_rng(11)
    x = -0.34 + 0.004
    i = 0
    while x < 0.30:
        s = sleeve(int(rng.integers(0, 6)), w=0.315, t=0.004).rot("z", 90)
        s.move(x, -0.025, z0 + 0.02 + 0.1575 + 0.001)
        P.append(s)
        x += 0.0055 + 0.002 * rng.random()
        i += 1
    return P


def speaker():
    P = [rbox(0.30, 0.32, 0.015, 0.004, mat="blackmetal").move(0, 0, 0.0075 + 0.008)]
    for sx in (-1, 1):
        for sy in (-1, 1):
            P.append(lathe([(0.004, 0.0), (0.014, 0.008)], m=2, mat="brass").move(sx * 0.12, sy * 0.13, 0))
        P.append(lathe([(0.018, 0.023), (0.018, 0.49)], m=3, mat="blackmetal").move(sx * 0.07, 0, 0))
    P.append(rbox(0.22, 0.24, 0.012, 0.003, mat="blackmetal").move(0, 0, 0.496))
    P.append(rbox(0.24, 0.27, 0.40, 0.006, mat="walnut").bake().move(0, 0, 0.502 + 0.2))
    P.append(rbox(0.222, 0.012, 0.382, 0.004, mat="grill", segs=(2, 1, 2)).bake().move(0, -0.135 - 0.004, 0.702))
    P.append(rbox(0.045, 0.004, 0.012, 0.001, mat="brass").move(0, -0.135 - 0.011, 0.53))
    return P


def record_shelf():
    W, D, H, t, lh = 0.8, 0.38, 1.17, 0.022, 0.12
    z0 = lh
    P = [rbox(W, D, t, 0.003, mat="oak").bake().move(0, 0, z0 + t / 2),
         rbox(W, D, t, 0.003, mat="oak").bake().move(0, 0, z0 + H - t / 2),
         rbox(t, D, H - 2 * t, 0.003, mat="oak", uv=U("oak", 90)).bake().move(0, 0, z0 + H / 2),
         box(W - 2 * t, 0.008, H - 2 * t, mat="oak", uv=U("oak", 90)).bake().move(0, D / 2 - 0.004, z0 + H / 2)]
    for sx in (-1, 1):
        P.append(rbox(t, D, H - 2 * t, 0.003, mat="oak", uv=U("oak", 90)).bake().move(sx * (W / 2 - t / 2), 0, z0 + H / 2))
        for sy in (-1, 1):
            P += leg(lh, 0.012, 0.016, x=sx * (W / 2 - 0.05), y=sy * (D / 2 - 0.05), mat="blackmetal", ferrule=None)
    ch = (H - 4 * t) / 3
    for k in (1, 2):
        P.append(rbox(W - 2 * t, D - 0.01, t, 0.003, mat="oak").bake().move(0, -0.005, z0 + t + k * ch + (k - 0.5) * t))
    rng = np.random.default_rng(5)
    for col in (0, 1):
        for row in range(3):
            xl = (-W / 2 + t) if col == 0 else t / 2
            zb = z0 + t + row * (ch + t)
            if (col, row) == (1, 1):          # one cube with a stack of books
                zz = zb
                for j, (cl, bw, bh, bt) in enumerate([("cloth_wine", 0.28, 0.22, 0.03),
                                                      ("cloth_teal", 0.26, 0.2, 0.024),
                                                      ("cloth_ochre", 0.3, 0.23, 0.035)]):
                    for q in book_parts(bw, bh, bt, cl):
                        P.append(q.rot("z", 6 * (j - 1)).move(xl + 0.18, -0.02, zz))
                    zz += bt
                continue
            nrec = int(rng.integers(14, 30))
            x = xl + 0.004
            for j in range(nrec):
                s = sleeve(int(rng.integers(0, 6))).rot("z", 90)
                lean = 0.0
                if j >= nrec - 2:                       # last ones lean on their neighbours
                    lean = 6 + 8 * (j - (nrec - 2))
                s.move(0, 0, 0.1575)
                s.rot("y", lean)
                s.move(x, -0.02, zb + 0.001)
                P.append(s)
                x += 0.0052 + (0.0 if lean == 0 else 0.03 * math.sin(math.radians(lean)) + 0.01)
    return P


def book_parts(w, h, t, cloth):
    """Hardcover lying flat; origin at the bottom centre."""
    bt = 0.0028
    return [box(w, h, bt, mat=cloth).bake().move(0, 0, t - bt / 2),
            box(w, h, bt, mat=cloth).bake().move(0, 0, bt / 2),
            box(bt, h, t, mat=cloth).bake().move(-w / 2 + bt / 2, 0, t / 2),
            box(w - 0.008, h - 0.008, t - 2 * bt, mat="pages").bake().move(0.001, 0, t / 2)]


def arc_lamp():
    P = [lathe([(0.165, 0.0), (0.17, 0.008), (0.17, 0.038), (0.16, 0.045)], m=10, mat="marble"),
         lathe([(0.03, 0.045), (0.03, 0.075), (0.018, 0.09)], m=4, mat="brass")]
    straight = np.array([[0, 0, z] for z in np.linspace(0.07, 1.4, 6)])
    arc = bezier((0, 0, 1.4), (0, 0, 2.15), (0, -0.85, 2.28), (0, -1.45, 1.76), 26)
    P.append(sweep(np.vstack([straight, arc[1:]]), 0.0125, m=2, mat="brass"))
    prof = [(0.025, 0.18), (0.10, 0.165), (0.17, 0.10), (0.205, 0.0), (0.198, -0.002),
            (0.163, 0.093), (0.096, 0.155), (0.025, 0.168)]
    shade = lathe(prof, m=8, mat="brass")

    def inner(n, c):
        rr = math.hypot(c[0], c[1]) + 1e-9
        radial = (n[0] * c[0] + n[1] * c[1]) / rr
        return radial < -0.3 or (n[2] < -0.5 and c[2] > 0.05)
    shade.by_normal(inner, "lamp_glow", "brass")
    P.append(shade.move(0, -1.45, 1.58))
    P.append(lathe([(0.012, 0.0), (0.03, 0.025), (0.03, 0.045), (0.012, 0.075)], m=4, mat="bulb")
             .move(0, -1.45, 1.58 + 0.06))
    return P


def big_plant(seed=3, pot_mat="terracotta", stems=7, hmin=0.85, hmax=1.55):
    rng = np.random.default_rng(seed)
    pot = lathe([(0.15, 0.0), (0.155, 0.01), (0.19, 0.36), (0.205, 0.37), (0.205, 0.40),
                 (0.19, 0.40), (0.178, 0.37)], m=8, mat=pot_mat)
    pot.by_normal(lambda n, c: n[2] > 0.9 and c[2] < 0.385, "soil", pot_mat)
    P = [pot]
    for i in range(stems):
        a = rng.uniform(0, 2 * math.pi)
        rr = rng.uniform(0.0, 0.07)
        base = np.array([rr * math.cos(a), rr * math.sin(a), 0.36])
        h = rng.uniform(hmin, hmax)
        lean = np.array([math.cos(a), math.sin(a), 0]) * rng.uniform(0.1, 0.35)
        top = base + np.array([0, 0, h]) + lean
        path = bezier(base, base + [0, 0, h * 0.45], top - lean * 0.3 - [0, 0, 0.1], top, 9)
        P.append(sweep(path, lambda t: 0.011 * (1 - 0.55 * t), m=2, mat="stem"))
        nl = int(rng.integers(4, 7))
        for k in range(nl):
            t = 0.4 + 0.6 * (k + 1) / nl
            idx = min(int(t * (len(path) - 1)), len(path) - 1)
            L = rng.uniform(0.2, 0.3) * (1.1 - 0.3 * t)
            P.append(leaf(L, L * rng.uniform(0.55, 0.7), rng.uniform(0.02, 0.06), rng.uniform(0.01, 0.025))
                     .rot("x", 90 - rng.uniform(15, 55)).rot("z", rng.uniform(0, 360))
                     .move(*path[idx]))
        P.append(leaf(0.2, 0.13, 0.02, 0.015).rot("x", 10).rot("z", rng.uniform(0, 360)).move(*top))
    return P


def leaf(L, W, droop, cup):
    pts, faces = grid2d(-1, 1, 0, 1, 2, 5)
    t, s = pts[:, 0], pts[:, 1]
    hw = W * 0.5 * np.clip((s ** 0.7) * ((1 - s) ** 0.35) / 0.56, 0.03, None)
    xz = np.column_stack([t * hw, s * L])
    p = solidify2d(xz, faces, 0.003, mat="leaf", uv=("fit", "y")).bake()
    p.mat = "leaf"
    v = p.v
    v[:, 1] += -droop * (v[:, 2] / L) ** 2 + cup * (v[:, 0] / (W * 0.5)) ** 2
    return p


def pouf():
    """Round upholstered pouf with leather piping."""
    body = lathe([(0.2, 0.012), (0.232, 0.02), (0.248, 0.05), (0.25, 0.2), (0.248, 0.33),
                  (0.232, 0.36), (0.2, 0.368)], m=8, mat="cloth_teal")
    P = [body]
    for z in (0.035, 0.345):
        ring = [(0.248 + 0.008 * math.cos(t), z + 0.008 * math.sin(t))
                for t in np.linspace(0, 2 * math.pi, 6, endpoint=False)]
        P.append(lathe(ring, m=8, closed=True, mat="leather"))
    P.append(lathe([(0.17, 0.0), (0.17, 0.014)], m=6, mat="walnut"))
    return P


def record_crate():
    """Oak crate full of records (grabbable as a whole)."""
    W, D, H, t = 0.36, 0.42, 0.28, 0.015
    P = [box(W, D, t, mat="oak").bake().move(0, 0, t / 2)]
    for sx in (-1, 1):
        P.append(box(t, D, H, mat="oak").bake().move(sx * (W / 2 - t / 2), 0, H / 2))
    for sy in (-1, 1):
        P.append(box(W - 2 * t, t, H * 0.7, mat="oak").bake().move(0, sy * (D / 2 - t / 2), H * 0.35))
    rng = np.random.default_rng(21)
    y = -D / 2 + t + 0.004
    j = 0
    while y < D / 2 - t - 0.01:
        lean = 8 if y < 0 else -6
        s = sleeve(int(rng.integers(0, 6)))
        s.move(0, 0, 0.1575).rot("x", lean).move(0, y, t + 0.001)
        P.append(s)
        y += 0.012 + 0.006 * rng.random()
        j += 1
    return P


# ======================================================== grabbables ========
def turntable():
    P = [rbox(0.45, 0.36, 0.07, 0.008, mat="walnut").bake().move(0, 0, 0.047)]
    for sx in (-1, 1):
        for sy in (-1, 1):
            P.append(lathe([(0.02, 0.0), (0.022, 0.012)], m=3, mat="rubber").move(sx * 0.18, sy * 0.14, 0))
    pc = np.array([-0.04, 0.0, 0.0])
    P.append(lathe([(0.148, 0.082), (0.15, 0.086), (0.15, 0.1), (0.147, 0.103)], m=10, mat="alu").move(*pc))
    P.append(lathe([(0.145, 0.103), (0.145, 0.106)], m=10, mat="felt").move(*pc))
    P.append(disc(0).move(pc[0], pc[1], 0.107))
    P.append(lathe([(0.0035, 0.105), (0.0035, 0.122)], m=2, mat="alu").move(*pc))
    piv = np.array([0.16, 0.10])
    P.append(lathe([(0.03, 0.082), (0.03, 0.098), (0.012, 0.104)], m=4, mat="alu").move(piv[0], piv[1], 0))
    P.append(lathe([(0.008, 0.1), (0.008, 0.132)], m=2, mat="alu").move(piv[0], piv[1], 0))
    arm = [(0.16, 0.165, 0.132), (0.16, 0.10, 0.132), (0.145, 0.02, 0.13), (0.1, -0.055, 0.126),
           (0.07, -0.082, 0.121)]
    P.append(sweep(arm, 0.0045, m=2, mat="alu"))
    P.append(lathe([(0.017, -0.018), (0.017, 0.018)], m=3, mat="plastic_black").rot("x", 90).move(0.16, 0.168, 0.132))
    hs = box(0.018, 0.038, 0.008, mat="plastic_black").rot("z", 40).move(0.062, -0.09, 0.118)
    P.append(hs)
    P.append(lathe([(0.004, 0.082), (0.004, 0.125)], m=2, mat="alu").move(0.2, -0.06, 0))
    P.append(lathe([(0.013, 0.082), (0.013, 0.094), (0.011, 0.097)], m=3, mat="alu").move(-0.175, -0.14, 0))
    P.append(lathe([(0.003, 0.082), (0.003, 0.085)], m=2, mat="led_red").move(-0.135, -0.155, 0))
    return P


def record_leaning(cover, vinyl, peek=0.07, lean=14):
    """Sleeve with the record peeking out; origin = bottom edge on the floor."""
    s = sleeve(cover)
    d = disc(vinyl).rot("x", 90).move(0.1575 - 0.15 + peek, 0, 0)
    return [q.move(0, 0, 0.1575).rot("x", -lean) for q in (s, d)]


def record_flat(cover, vinyl, peek=0.08):
    s = sleeve(cover)
    d = disc(vinyl).rot("x", 90).move(0.1575 - 0.15 + peek, 0, 0)
    return [q.rot("x", 90).move(0, 0, 0.002) for q in (s, d)]


def mug():
    body = lathe([(0.034, 0.0), (0.04, 0.006), (0.041, 0.088), (0.0395, 0.093), (0.036, 0.093),
                  (0.035, 0.085), (0.034, 0.012)], m=6, mat="ceramic_cream")
    coffee = lathe([(0.0349, 0.05), (0.0349, 0.072)], m=6, mat="coffee")
    handle = sweep(bezier((0.036, 0, 0.074), (0.088, 0, 0.082), (0.088, 0, 0.022), (0.036, 0, 0.028), 12),
                   0.006, m=2, mat="ceramic_cream", profile_scale=(1.0, 0.75))
    return [body, coffee, handle]


def headphones():
    P = []
    for sx in (-1, 1):
        cx = sx * 0.075
        pad = [(0.03 + 0.016 * (0.5 + 0.5 * math.cos(t)), 0.01 + 0.01 * math.sin(t))
               for t in np.linspace(0, 2 * math.pi, 10, endpoint=False)]
        P.append(lathe(pad, m=6, closed=True, mat="leather").move(cx, 0, 0))
        P.append(lathe([(0.031, 0.008), (0.031, 0.014)], m=6, mat="plastic_black").move(cx, 0, 0))
        P.append(lathe([(0.044, 0.018), (0.046, 0.03), (0.042, 0.048), (0.02, 0.052)], m=6,
                       mat="plastic_black").move(cx, 0, 0))
        P.append(lathe([(0.02, 0.05), (0.02, 0.054)], m=4, mat="alu").move(cx, 0, 0))
    phi = np.linspace(math.pi, 0, 26)
    band = np.column_stack([0.123 * np.cos(phi), 0.175 * np.sin(phi), 0.035 - 0.022 * np.sin(phi)])
    P.append(sweep(band, 0.0055, m=2, mat="alu"))
    phi2 = np.linspace(math.radians(140), math.radians(40), 14)
    pad = np.column_stack([0.12 * np.cos(phi2), 0.168 * np.sin(phi2), 0.035 - 0.022 * np.sin(phi2) + 0.002])
    P.append(sweep(pad, 0.011, m=2, mat="leather", profile_scale=(1.3, 0.55)))
    return P


def cactus():
    pot = lathe([(0.045, 0.0), (0.05, 0.006), (0.06, 0.075), (0.064, 0.08), (0.064, 0.09),
                 (0.058, 0.09), (0.055, 0.08)], m=5, mat="terracotta")
    pot.by_normal(lambda n, c: n[2] > 0.9 and c[2] < 0.085, "soil", "terracotta")

    def ribbed(prof, m):
        p = lathe(prof, m=m, mat="cactus")
        v = p.v
        ang = np.arctan2(v[:, 1], v[:, 0])
        k = 1 + 0.12 * np.cos(10 * ang) * (np.hypot(v[:, 0], v[:, 1]) > 0.014)
        v[:, 0] *= k
        v[:, 1] *= k
        return p
    body = ribbed([(0.012, 0.078), (0.03, 0.09), (0.036, 0.13), (0.035, 0.2), (0.028, 0.235), (0.012, 0.25)], 5)
    arm = ribbed([(0.008, 0.0), (0.016, 0.01), (0.018, 0.05), (0.014, 0.075), (0.006, 0.082)], 4)
    arm.rot("y", 35).move(0.03, 0, 0.14)
    return [pot, body, arm]


def poster():
    W, H, fw, fd = 0.5, 0.667, 0.022, 0.03
    P = [box(W - 2 * fw + 0.004, 0.006, H - 2 * fw + 0.004, mat="paper").bake().move(0, 0.0, 0)]
    P.append(box(0.40, 0.004, 0.533, mat="poster", uv=("fit", "y")).bake().move(0, -0.004, 0.01))
    for (sx, sz, x, z) in [(W, fw, 0, H / 2 - fw / 2), (W, fw, 0, -H / 2 + fw / 2),
                           (fw, H - 2 * fw, -W / 2 + fw / 2, 0), (fw, H - 2 * fw, W / 2 - fw / 2, 0)]:
        P.append(rbox(sx, fd, sz, 0.002, mat="blackmetal").move(x, -fd / 2 + 0.003, z))
    return P


# ====================================================== scene assembly ======
def aim(ob, target):
    d = Vector(target) - ob.location
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def add_light(name, kind, loc, energy, color, size=None, target=None, cam_visible=False):
    ld = bpy.data.lights.new(name, kind)
    ld.energy = energy
    ld.color = color
    if kind == "AREA":
        ld.shape = "RECTANGLE"
        ld.size, ld.size_y = size
    elif kind == "SUN":
        ld.angle = math.radians(size or 1.0)
    else:
        ld.shadow_soft_size = size or 0.05
    ob = bpy.data.objects.new(name, ld)
    ob.location = loc
    COL["Lighting"].objects.link(ob)
    if target is not None:
        aim(ob, target)
    ob.visible_camera = cam_visible
    return ob


def place_all():
    log("architecture")
    architecture()
    log("furniture")
    new_obj("FURN_Sofa", sofa(), (0.08 + 0.46, 2.55, 0), 90)
    new_obj("FURN_CoffeeTable", coffee_table(), (1.85, 2.55, 0), 0)
    rug = box(2.6, 3.0, 0.012, mat="rug", uv=("fit", "z")).bake()
    rug.by_normal(is_up, "rug", "rug_binding").move(0, 0, 0.006)
    fringe = []
    for sy in (-1, 1):
        for x in np.linspace(-1.27, 1.27, 64):
            fringe.append(box(0.006, 0.06, 0.002, mat="pages").move(x, sy * (1.5 + 0.028), 0.001))
    new_obj("FURN_Rug", [rug] + fringe, (1.95, 2.55, 0), 0)
    new_obj("FURN_Armchair", armchair(), (3.45, 3.55, 0), -58)
    a = math.radians(-58)
    right = np.array([-math.cos(a), -math.sin(a)])          # sitter's right = local -X
    st = np.array([3.45, 3.55]) + 0.68 * right
    new_obj("FURN_SideTable", side_table(), (st[0], st[1], 0), 0)
    cy = RD - 0.034 - 0.225 - 0.005
    new_obj("FURN_Credenza", credenza(), (3.3, cy, 0), 0)
    new_obj("FURN_Speaker_L", speaker(), (1.6, RD - 0.17, 0), 15)
    new_obj("FURN_Speaker_R", speaker(), (4.82, RD - 0.17, 0), -25)
    new_obj("FURN_RecordShelf", record_shelf(), (5.55, RD - 0.2, 0), 0)
    lamp_rot = 45.7
    lamp = new_obj("FURN_ArcLamp", arc_lamp(), (0.42, 4.0, 0), lamp_rot)
    new_obj("FURN_Plant", big_plant(), (0.45, 4.8, 0), 0)
    new_obj("FURN_Poster", poster(), (1.0, RD - 0.004, 1.75), 0)
    new_obj("FURN_Pouf", pouf(), (4.05, 2.6, 0), 0)
    new_obj("FURN_Plant_2", big_plant(seed=8, pot_mat="ceramic_cream", stems=8, hmin=0.75, hmax=1.35), (5.55, 2.15, 0), 0)

    log("grabbables")
    new_obj("GRAB_Turntable", turntable(), (2.85, cy, 0.66), 0)
    new_obj("GRAB_Record_LowTide", record_leaning(0, 2, lean=14), (2.52, cy - 0.225 - 0.08, 0), 0)
    new_obj("GRAB_Record_SunDial", record_leaning(3, 1, peek=0.05, lean=19), (2.77, cy - 0.225 - 0.105, 0), 4)
    new_obj("GRAB_Record_OrbitalBloom", record_flat(1, 0), (2.62, 3.82, 0.012), 25)
    new_obj("GRAB_Mug", mug(), (1.66, 2.33, 0.396), 30)
    new_obj("GRAB_Headphones", headphones(), (2.02, 2.36, 0.396), -70)
    z = 0.396
    for i, (cl, w, h, t, rz) in enumerate([("cloth_teal", 0.24, 0.31, 0.03, 8),
                                           ("cloth_wine", 0.21, 0.28, 0.024, -6),
                                           ("cloth_ochre", 0.19, 0.25, 0.02, 15)]):
        new_obj(f"GRAB_Book_{i + 1}", book_parts(w, h, t, cl), (1.92, 2.72, z), rz)
        z += t
    new_obj("GRAB_Book_4", book_parts(0.17, 0.23, 0.022, "cloth_teal"), (st[0], st[1], 0.526), 35)
    new_obj("GRAB_Cactus", cactus(), (5.42, RD - 0.2, 0.12 + 1.17), 0)
    new_obj("GRAB_RecordCrate", record_crate(), (5.0, 3.85, 0), -18)

    log("lights + camera")
    sun = add_light("Sun", "SUN", (-6, 4, 5), 9.0, (1.0, 0.83, 0.64), size=0.8)
    sun.rotation_euler = Vector((1.0, 0.1, -0.8)).normalized().to_track_quat("-Z", "Y").to_euler()
    bpy.context.view_layer.update()
    bulb = lamp.matrix_world @ Vector((0, -1.45, 1.58 + 0.1))
    add_light("Lamp_Bulb", "POINT", tuple(bulb), 60, (1.0, 0.72, 0.45), size=0.03)
    add_light("Fill_Bounce", "AREA", (3.2, 0.45, 2.85), 40, (1.0, 0.94, 0.86), size=(4.0, 1.4),
              target=(2.8, 3.5, 0.6))
    add_light("Fill_Window", "AREA", (0.06, 2.55, 1.75), 25, (0.78, 0.86, 1.0), size=(1.8, 1.3),
              target=(3.0, 2.55, 1.2))
    world = bpy.data.worlds.new("World")
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.05, 0.06, 0.08, 1)
    bg.inputs["Strength"].default_value = 1.0
    bpy.context.scene.world = world

    cd = bpy.data.cameras.new("Camera")
    cd.lens = 22
    cd.sensor_width = 36
    cd.shift_y = -0.07
    cam = bpy.data.objects.new("Camera", cd)
    cam.location = (5.0, -0.75, 1.45)
    COL["Camera"].objects.link(cam)
    aim(cam, (1.7, 3.9, 1.45))
    bpy.context.scene.camera = cam


def render_settings(res=(1920, 1080), samples=192):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = samples
    sc.cycles.use_adaptive_sampling = True
    sc.cycles.adaptive_threshold = 0.015
    sc.cycles.use_denoising = True
    try:
        sc.cycles.denoiser = "OPENIMAGEDENOISE"
    except TypeError:
        pass
    sc.cycles.max_bounces = 8
    sc.cycles.diffuse_bounces = 4
    sc.cycles.glossy_bounces = 4
    sc.cycles.transmission_bounces = 8
    sc.cycles.caustics_reflective = False
    sc.cycles.caustics_refractive = False
    sc.cycles.blur_glossy = 0.5
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"
    sc.view_settings.view_transform = "AgX"
    try:
        sc.view_settings.look = "AgX - Medium High Contrast"
    except TypeError:
        pass
    sc.view_settings.exposure = 0.0


def stats():
    faces = tris = ngons = 0
    rows = []
    for ob in bpy.data.objects:
        if ob.type != "MESH":
            continue
        me = ob.data
        nf = len(me.polygons)
        nt = sum(1 for p in me.polygons if len(p.vertices) == 3)
        nn = sum(1 for p in me.polygons if len(p.vertices) > 4)
        used = sorted({me.materials[p.material_index].name for p in me.polygons})
        faces += nf
        tris += nt
        ngons += nn
        rows.append((ob.name, nf, used))
    return faces, tris, ngons, rows


def write_layout():
    data = []
    for ob in bpy.data.objects:
        if ob.type != "MESH" or not ob.name.startswith(("FURN_", "GRAB_", "ARCH_")):
            continue
        pts = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
        xs = [p.x for p in pts]
        ys = [p.y for p in pts]
        zs = [p.z for p in pts]
        # rotated footprint rectangle (local bbox corners at min z)
        corners = [ob.matrix_world @ Vector(ob.bound_box[i]) for i in (0, 3, 7, 4)]
        data.append(dict(name=ob.name, bbox=[min(xs), min(ys), min(zs), max(xs), max(ys), max(zs)],
                         footprint=[[c.x, c.y] for c in corners]))
    with open(os.path.join(OUT, "layout.json"), "w") as f:
        json.dump(dict(room=[RW, RD, RH], window=dict(y=WIN["cx"] - WT, w=WIN["w"]), objects=data), f, indent=1)


def main():
    os.makedirs(OUT, exist_ok=True)
    reset()
    place_all()
    render_settings()
    faces, tris, ngons, rows = stats()
    log(f"objects: {len(rows)}  faces: {faces}  tris: {tris}  ngons: {ngons}")
    for name, nf, used in sorted(rows):
        log(f"   {name:28s} {nf:6d}  {', '.join(used)}")
    write_layout()
    blend = os.path.join(OUT, BASENAME + ".blend")
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=blend, compress=True)
    log("saved", blend)
    if "--no-export" not in sys.argv:
        glb = os.path.join(OUT, BASENAME + ".glb")
        bpy.ops.export_scene.gltf(filepath=glb, export_format="GLB", export_yup=True,
                                  export_apply=True, export_extras=True, export_lights=True,
                                  export_cameras=True, export_image_format="AUTO")
        log("exported", glb, f"{os.path.getsize(glb) / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
