"""Intermediate-level living room with a record player (Blender 5.2, Cycles).

Mimics an intermediate student's workflow: bevelled / subdivided furniture,
live Bevel (2 segments), Subdivision and Solidify modifiers, image textures
on the main surfaces + flat-colour materials elsewhere, sun through a real
window, a warm floor lamp, framed posters, curtains, plant.

usage: python intermediate_build.py <outdir> [--render]
       (textures must already be in <outdir>/textures)
"""
import os
import sys
import math

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np                          # noqa: E402
import bpy                                  # noqa: E402
from mathutils import Vector                # noqa: E402
from lib import mk                          # noqa: E402
from lib.mk import box, rbox, cushion, lathe, sweep, bezier, solidify2d, grid2d   # noqa: E402

OUT = [a for a in sys.argv[1:] if not a.startswith("--")][-1]
TEX = os.path.join(OUT, "textures")
NAME = "4SA1_Claude_Interier_v01"
RW, RD, RH, WT = 5.0, 4.5, 2.7, 0.15
WIN = dict(y0=1.6, y1=3.0, z0=0.9, z1=2.2)          # window in the left wall (x = 0)

# ------------------------------------------------------------- materials ----
#  name: (texture prefix or None, colour, roughness, metallic, extra)
MAT = {
    "Wood_Floor":   ("wood_floor", None, None, 0, dict(tile=1.6, nrm=0.5)),
    "Oak":          ("oak", None, None, 0, dict(tile=0.6, nrm=0.3)),
    "Fabric_Sofa":  ("fabric_sofa", None, None, 0, dict(tile=0.25, nrm=0.6, sheen=0.5)),
    "Fabric_Chair": ("fabric_chair", None, None, 0, dict(tile=0.25, nrm=0.6, sheen=0.5)),
    "Fabric_Pillow": ("fabric_pillow", None, None, 0, dict(tile=0.2, nrm=0.5, sheen=0.5)),
    "Pillow_Piping": (None, (0.25, 0.16, 0.06), 0.7, 0, {}),
    "Linen":        ("linen", None, None, 0, dict(tile=0.4, nrm=0.4, sheen=0.3)),
    "Rug":          ("rug", None, None, 0, dict(nrm=0.5, sheen=0.3)),
    "Rug_Edge":     (None, (0.35, 0.12, 0.07), 0.9, 0, {}),
    "Wall_Paint":   (None, (0.80, 0.74, 0.64), 0.85, 0, {}),
    "White_Paint":  (None, (0.88, 0.87, 0.84), 0.45, 0, {}),
    "Ceiling":      (None, (0.92, 0.91, 0.89), 0.9, 0, {}),
    "Concrete":     (None, (0.35, 0.35, 0.36), 0.9, 0, {}),
    "Green_Paint":  (None, (0.10, 0.20, 0.15), 0.35, 0, {}),
    "Black_Metal":  (None, (0.03, 0.03, 0.03), 0.35, 1.0, {}),
    "Brass":        (None, (0.80, 0.60, 0.30), 0.25, 1.0, {}),
    "Aluminium":    (None, (0.80, 0.80, 0.82), 0.3, 1.0, {}),
    "Glass":        (None, (1, 1, 1), 0.0, 0, dict(transmission=1.0)),
    "Rubber":       (None, (0.02, 0.02, 0.02), 0.8, 0, {}),
    "Ceramic":      (None, (0.92, 0.90, 0.85), 0.15, 0, {}),
    "Terracotta":   (None, (0.62, 0.32, 0.20), 0.8, 0, {}),
    "Soil":         (None, (0.10, 0.07, 0.04), 1.0, 0, {}),
    "Leaf":         (None, (0.13, 0.30, 0.10), 0.45, 0, {}),
    "Coffee":       (None, (0.05, 0.025, 0.01), 0.05, 0, {}),
    "Paper":        (None, (0.93, 0.91, 0.84), 0.8, 0, {}),
    "Cardboard":    (None, (0.55, 0.42, 0.28), 0.8, 0, {}),
    "Vinyl":        (None, (0.01, 0.01, 0.01), 0.25, 0, {}),
    "Record_Label": ("record_label", None, 0.4, 0, {}),
    "Felt":         (None, (0.02, 0.02, 0.02), 1.0, 0, {}),
    "Lamp_Shade":   (None, (0.93, 0.88, 0.78), 0.7, 0, dict(emission=(1.0, 0.8, 0.55), estrength=1.5)),
    "Bulb":         (None, (1, 1, 1), 0.2, 0, dict(emission=(1.0, 0.78, 0.5), estrength=15)),
    "Ceiling_Light": (None, (0.95, 0.95, 0.95), 0.3, 0, {}),
    "Window_View":  ("window_view", None, 1.0, 0, dict(emit_tex=1.0)),
    "Poster_1":     ("poster_1", None, 0.6, 0, {}),
    "Poster_2":     ("poster_2", None, 0.6, 0, {}),
    "Album_1":      ("album_1", None, 0.5, 0, {}),
    "Album_2":      ("album_2", None, 0.5, 0, {}),
}
BOOKS = [(0.55, 0.12, 0.10), (0.12, 0.25, 0.45), (0.85, 0.65, 0.20), (0.15, 0.35, 0.25),
         (0.80, 0.78, 0.70), (0.35, 0.12, 0.25), (0.10, 0.10, 0.12), (0.70, 0.35, 0.20)]
for i, c in enumerate(BOOKS):
    MAT[f"Book_{i + 1}"] = (None, c, 0.6, 0, {})


def img(prefix, kind, noncolor):
    p = os.path.join(TEX, f"{prefix}_{kind}.jpg") if kind else os.path.join(TEX, f"{prefix}.jpg")
    if not os.path.exists(p):
        return None
    im = bpy.data.images.load(p, check_existing=True)
    im.colorspace_settings.name = "Non-Color" if noncolor else "sRGB"
    return im


def make_mat(name):
    tex, col, rough, metal, ex = MAT[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes.get("Principled BSDF")
    I = b.inputs
    if tex:
        c = img(tex, "color", False) or img(tex, None, False)
        n = nt.nodes.new("ShaderNodeTexImage")
        n.image, n.location = c, (-600, 300)
        nt.links.new(n.outputs["Color"], I["Base Color"])
        if ex.get("emit_tex"):
            nt.links.new(n.outputs["Color"], I["Emission Color"])
            I["Emission Strength"].default_value = ex["emit_tex"]
        r = img(tex, "roughness", True)
        if r:
            n = nt.nodes.new("ShaderNodeTexImage")
            n.image, n.location = r, (-600, 0)
            nt.links.new(n.outputs["Color"], I["Roughness"])
        nm = img(tex, "normal", True)
        if nm and ex.get("nrm"):
            n = nt.nodes.new("ShaderNodeTexImage")
            n.image, n.location = nm, (-600, -300)
            mapn = nt.nodes.new("ShaderNodeNormalMap")
            mapn.location = (-300, -300)
            mapn.inputs["Strength"].default_value = ex["nrm"]
            nt.links.new(n.outputs["Color"], mapn.inputs["Color"])
            nt.links.new(mapn.outputs["Normal"], I["Normal"])
    if col:
        I["Base Color"].default_value = (*col, 1)
        m.diffuse_color = (*col, 1)
    if rough is not None and not I["Roughness"].is_linked:
        I["Roughness"].default_value = rough
    I["Metallic"].default_value = metal
    if ex.get("transmission"):
        I["Transmission Weight"].default_value = 1.0
        I["IOR"].default_value = 1.45
    if ex.get("emission"):
        I["Emission Color"].default_value = (*ex["emission"], 1)
        I["Emission Strength"].default_value = ex["estrength"]
    if ex.get("sheen"):
        I["Sheen Weight"].default_value = ex["sheen"]
    return m


def get_mat(name):
    return bpy.data.materials.get(name) or make_mat(name)


def tile(name):
    return MAT.get(name, (None, None, None, 0, {}))[4].get("tile") or 1.0


# ----------------------------------------------------------------- helpers --
COL = {}


def obj(name, parts, loc=(0, 0, 0), rz=0.0, col="Furniture", bevel=None, subsurf=None):
    ob = mk.build_object(name, parts, loc, rz, COL[col])
    if bevel:                                   # live Bevel modifier (2 segments = quads)
        m = ob.modifiers.new("Bevel", "BEVEL")
        m.width, m.segments, m.limit_method = bevel, 2, "ANGLE"
        m.angle_limit = math.radians(30)
    if subsurf:
        m = ob.modifiers.new("Subdivision", "SUBSURF")
        m.levels = m.render_levels = subsurf
    return ob


def leg(h, r0, r1, x, y, mat="Oak", m=3):
    return lathe([(r0, 0.0), (r1, h)], m, mat=mat, uv=("box", tile(mat), 90)).bake().move(x, y, 0)


def wall_with_hole(W, H, x0, x1, z0, z1):
    """grid plane W x H (XZ) with a rectangular opening, all quads"""
    Xs = sorted(set(np.round(np.concatenate([np.linspace(0, x0, 5), np.linspace(x0, x1, 5),
                                             np.linspace(x1, W, 6)]), 5)))
    Zs = sorted(set(np.round(np.concatenate([np.linspace(0, z0, 3), np.linspace(z0, z1, 5),
                                             np.linspace(z1, H, 2)]), 5)))
    pts = [(x, z) for x in Xs for z in Zs]
    nz = len(Zs)
    faces = []
    for i in range(len(Xs) - 1):
        for j in range(nz - 1):
            mx, mz = (Xs[i] + Xs[i + 1]) / 2, (Zs[j] + Zs[j + 1]) / 2
            if x0 < mx < x1 and z0 < mz < z1:
                continue
            a = i * nz + j
            faces.append((a, a + nz, a + nz + 1, a + 1))
    return np.array(pts), faces


# ------------------------------------------------------------------- room ---
def room():
    f = box(RW + 2 * WT, RD + 2 * WT, 0.1, mat="Wood_Floor", uv=("box", 1.6, 0)).bake()
    f.by_normal(lambda n, c: n[2] > 0.9, "Wood_Floor", "Concrete").move(RW / 2, RD / 2, -0.05)
    obj("Floor", [f], col="Room")

    c = box(RW + 2 * WT, RD + 2 * WT, 0.1, mat="Ceiling").move(RW / 2, RD / 2, RH + 0.05)
    lamp = lathe([(0.18, RH - 0.001), (0.18, RH - 0.03), (0.16, RH - 0.05)], m=6, mat="Ceiling_Light")
    obj("Ceiling", [c, lamp.move(2.5, 2.4, 0)], col="Room")

    def skirting(sx, sy, x, y):
        return box(sx, sy, 0.08, mat="White_Paint").move(x, y, 0.04)

    pts, fc = grid2d(0, RW + 2 * WT, 0, RH, 10, 4)
    back = solidify2d(pts, fc, WT, mat="Wall_Paint").move(-WT, RD, 0)
    obj("Wall_Back", [back, skirting(RW, 0.015, RW / 2, RD - 0.0075)], col="Room")
    front = solidify2d(pts, fc, WT, mat="Wall_Paint").move(-WT, -WT, 0)
    ob = obj("Wall_Front", [front, skirting(RW, 0.015, RW / 2, 0.0075)], col="Room")
    ob.visible_camera = False                    # front walls hidden in render
    pts2, fc2 = grid2d(0, RD + 2 * WT, 0, RH, 9, 4)
    right = solidify2d(pts2, fc2, WT, mat="Wall_Paint").rot("z", 90).move(RW + WT, -WT, 0)
    ob = obj("Wall_Right", [right, skirting(0.015, RD, RW - 0.0075, RD / 2)], col="Room")
    ob.visible_camera = False
    hp, hf = wall_with_hole(RD + 2 * WT, RH, WIN["y0"] + WT, WIN["y1"] + WT, WIN["z0"], WIN["z1"])
    left = solidify2d(hp, hf, WT, mat="Wall_Paint").rot("z", 90).move(0, -WT, 0)
    sill = box(0.2, WIN["y1"] - WIN["y0"] + 0.1, 0.03, mat="White_Paint").move(-0.06, (WIN["y0"] + WIN["y1"]) / 2, WIN["z0"] - 0.015)
    obj("Wall_Left", [left, sill, skirting(0.015, RD, 0.0075, RD / 2)], col="Room")

    # window frame + glass
    y0, y1, z0, z1, fw, xc = WIN["y0"], WIN["y1"], WIN["z0"], WIN["z1"], 0.055, -WT / 2
    yc, zc = (y0 + y1) / 2, (z0 + z1) / 2
    parts = [box(0.06, fw, z1 - z0, mat="White_Paint").move(xc, y0 + fw / 2, zc),
             box(0.06, fw, z1 - z0, mat="White_Paint").move(xc, y1 - fw / 2, zc),
             box(0.056, y1 - y0, fw, mat="White_Paint").move(xc, yc, z0 + fw / 2),
             box(0.056, y1 - y0, fw, mat="White_Paint").move(xc, yc, z1 - fw / 2),
             box(0.05, 0.04, z1 - z0, mat="White_Paint").move(xc, yc, zc),
             box(0.046, y1 - y0, 0.04, mat="White_Paint").move(xc, yc, z0 + (z1 - z0) * 0.62),
             box(0.03, 0.012, 0.09, mat="Aluminium").move(xc + 0.045, yc - 0.035, zc - 0.05)]
    obj("Window_Frame", parts, col="Room", bevel=0.004)
    g = box(0.008, y1 - y0 - 0.06, z1 - z0 - 0.06, mat="Glass").bake()
    g.by_normal(lambda n, c: abs(n[0]) > 0.9, "Glass", "Rubber").move(xc, yc, zc)
    ob = obj("Window_Glass", [g], col="Room")
    ob.visible_shadow = False                    # lets the sun through
    v = box(0.02, 12, 6, mat="Window_View", uv=("fit", "x")).bake()   # picture plane outside
    v.by_normal(lambda n, c: n[0] > 0.9, "Window_View", "Rubber").move(-3.0, 2.3, 1.6)
    ob = obj("Window_View_Plane", [v], col="Room")
    ob.visible_shadow = False

    # curtains (folded panels) + rod
    parts = []
    for (ya, yb) in ((y0 - 0.43, y0 - 0.02), (y1 + 0.02, y1 + 0.43)):
        cp, cf = grid2d(0, yb - ya, 0, 2.35, 16, 6)
        p = solidify2d(cp, cf, 0.008, mat="Linen", uv=("box", 0.4)).bake()
        v = p.v
        v[:, 1] += 0.03 * np.sin(v[:, 0] / (yb - ya) * 2 * math.pi * 3.5) * (0.6 + 0.4 * v[:, 2] / 2.35)
        parts.append(p.rot("z", 90).move(0.12, ya, 0.05))
    parts.append(sweep([(0.12, y0 - 0.7, 2.43), (0.12, y1 + 0.7, 2.43)], 0.013, m=2, mat="Black_Metal"))
    obj("Curtains", parts, col="Room", subsurf=1)


# -------------------------------------------------------------- furniture ---
def sofa(W=2.1, D=0.9, fabric="Fabric_Sofa", seats=2):
    P = [leg(0.12, 0.016, 0.022, sx * (W / 2 - 0.08), sy * (D / 2 - 0.08)) for sx in (-1, 1) for sy in (-1, 1)]
    P.append(rbox(W - 0.04, D - 0.03, 0.22, 0.03, mat=fabric, segs=(2, 2, 1)).move(0, 0, 0.23))   # inset: no z-fighting with the arms
    for sx in (-1, 1):
        P.append(rbox(0.18, D, 0.5, 0.05, mat=fabric, segs=(1, 2, 2)).move(sx * (W / 2 - 0.09), 0, 0.37))
    P.append(rbox(W - 0.36, 0.2, 0.42, 0.05, mat=fabric, segs=(2, 1, 2)).move(0, D / 2 - 0.1, 0.55))
    cw = (W - 0.36) / seats
    for i in range(seats):
        x = -(W - 0.36) / 2 + cw * (i + 0.5)
        P.append(cushion(cw - 0.01, D - 0.22, 0.14, r=0.05, mat=fabric, segs=(4, 4, 1), puff=0.015,
                         level=1).move(x, -0.1, 0.41))
        P.append(cushion(cw - 0.02, 0.42, 0.15, r=0.06, mat=fabric, segs=(4, 3, 1), puff=0.02, level=1)
                 .rot("x", 80).move(x, D / 2 - 0.27, 0.69))
    return P


def coffee_table():
    P = [box(1.1, 0.6, 0.035, mat="Oak").bake().move(0, 0, 0.4),
         box(1.0, 0.5, 0.02, mat="Oak").bake().move(0, 0, 0.12)]
    for sx in (-1, 1):
        for sy in (-1, 1):
            P.append(lathe([(0.016, 0.0), (0.016, 0.383)], m=2, mat="Black_Metal").move(sx * 0.5, sy * 0.25, 0))
    return P


def sideboard():
    L, D, z0, z1 = 1.4, 0.45, 0.15, 0.65
    P = [box(L, D, 0.025, mat="Oak").bake().move(0, 0, z1 - 0.0125),
         box(L - 0.04, D - 0.02, 0.02, mat="Oak").bake().move(0, 0.01, z0 + 0.01),
         box(L - 0.04, 0.01, z1 - z0 - 0.025, mat="Oak").bake().move(0, D / 2 - 0.005, (z0 + z1 - 0.025) / 2)]
    for sx in (-1, 1):
        P.append(box(0.02, D, z1 - z0 - 0.025, mat="Oak", uv=("box", 0.6, 90)).bake().move(sx * (L / 2 - 0.01), 0, (z0 + z1 - 0.025) / 2))
        P.append(box(L / 2 - 0.025, 0.018, z1 - z0 - 0.045, mat="Green_Paint").move(sx * (L / 4 - 0.002), -D / 2 + 0.009, (z0 + z1 - 0.025) / 2))
        P.append(lathe([(0.008, 0.0), (0.008, 0.015), (0.014, 0.02), (0.014, 0.028)], m=2, mat="Brass")
                 .rot("x", 90).move(sx * 0.06, -D / 2, (z0 + z1) / 2))
        for sy in (-1, 1):
            P.append(lathe([(0.012, 0.0), (0.016, z0)], m=2, mat="Black_Metal").move(sx * (L / 2 - 0.08), sy * (D / 2 - 0.07), 0))
    return P


def bookshelf():
    W, D, H, t = 0.9, 0.32, 1.8, 0.022
    P = [box(t, D, H, mat="Oak", uv=("box", 0.6, 90)).bake().move(sx * (W / 2 - t / 2), 0, H / 2) for sx in (-1, 1)]
    levels = [0.05 + i * 0.42 for i in range(5)]
    for z in levels:
        P.append(box(W - 2 * t, D, t, mat="Oak").bake().move(0, 0, z))
    P.append(box(W - 2 * t, t, 0.05, mat="Oak").bake().move(0, -D / 2 + t / 2 + 0.01, 0.025))
    rng = np.random.default_rng(4)
    for li, z in enumerate(levels[:-1]):
        x = -W / 2 + t + 0.01
        stop = W / 2 - t - (0.25 if li % 2 else 0.05)
        while x < stop:
            bw = rng.uniform(0.022, 0.045)
            bh = rng.uniform(0.2, 0.3)
            bd = rng.uniform(0.17, 0.23)
            b = box(bw, bd, bh, mat=f"Book_{int(rng.integers(1, len(BOOKS) + 1))}").bake()
            b.by_normal(lambda n, c: n[1] > 0.9, "Paper")             # page edges at the back
            P.append(b.move(x + bw / 2, -D / 2 + 0.03 + bd / 2, z + t / 2 + bh / 2))
            x += bw + 0.002
        if li % 2:                                                        # small stack lying flat
            zz = z + t / 2
            for k in range(3):
                bh = 0.03
                b = box(0.2, 0.15, bh, mat=f"Book_{(li + k) % len(BOOKS) + 1}").move(W / 2 - t - 0.12, -0.02, zz + bh / 2)
                P.append(b)
                zz += bh
    return P


def floor_lamp():
    P = [lathe([(0.15, 0.0), (0.15, 0.02), (0.13, 0.03)], m=6, mat="Black_Metal"),
         lathe([(0.012, 0.03), (0.012, 1.42)], m=2, mat="Brass")]
    ring = [(0.22, 1.32), (0.225, 1.32), (0.225, 1.6), (0.22, 1.6)]
    P.append(lathe(ring, m=6, closed=True, mat="Lamp_Shade"))
    P.append(lathe([(0.01, 1.38), (0.03, 1.41), (0.03, 1.46), (0.01, 1.5)], m=3, mat="Bulb"))
    return P


def rug():
    pts, f = grid2d(-1.3, 1.3, -0.95, 0.95, 1, 1)
    p = mk.Part(np.column_stack([pts[:, 0], pts[:, 1], np.zeros(len(pts)) + 0.012]), f, "Rug",
                uv=("fit", "z")).bake()
    p.f = [tuple(reversed(fc)) for fc in p.f] if np.cross(p.v[p.f[0][1]] - p.v[p.f[0][0]], p.v[p.f[0][2]] - p.v[p.f[0][0]])[2] < 0 else p.f
    return [p]


def plant(seed=2):
    rng = np.random.default_rng(seed)
    pot = lathe([(0.13, 0.0), (0.16, 0.32), (0.17, 0.33), (0.17, 0.35), (0.155, 0.35), (0.15, 0.32)], m=6, mat="Terracotta")
    pot.by_normal(lambda n, c: n[2] > 0.9 and c[2] < 0.34, "Soil", "Terracotta")
    P = [pot]
    for i in range(12):
        a = rng.uniform(0, 2 * math.pi)
        h = rng.uniform(0.5, 1.15)
        lean = np.array([math.cos(a), math.sin(a), 0]) * rng.uniform(0.15, 0.35)
        base = np.array([0.04 * math.cos(a), 0.04 * math.sin(a), 0.32])
        top = base + [0, 0, h] + lean
        path = bezier(base, base + [0, 0, h * 0.5], top - lean * 0.2, top, 7)
        P.append(sweep(path, 0.007, m=2, mat="Leaf"))
        L, Wd = rng.uniform(0.26, 0.36), rng.uniform(0.17, 0.24)
        lp, lf = grid2d(-1, 1, 0, 1, 2, 4)
        s = lp[:, 1]
        hw = Wd * 0.5 * np.clip(np.sin(np.pi * s) ** 0.8, 0.05, None)
        leaf = solidify2d(np.column_stack([lp[:, 0] * hw, s * L]), lf, 0.003, mat="Leaf")
        leaf.v[:, 1] -= 0.05 * (leaf.v[:, 2] / L) ** 2
        P.append(leaf.copy().rot("x", 90 - rng.uniform(10, 40)).rot("z", math.degrees(a) + 90).move(*top))
        mid = path[len(path) // 2 + 1]
        P.append(leaf.copy().scale(0.8).rot("x", 90 - rng.uniform(5, 30)).rot("z", math.degrees(a) + 90 + rng.uniform(-100, 100)).move(*mid))
    return P


def frame(img_mat, w, h):
    P = [box(w - 0.06, 0.006, h - 0.06, mat="White_Paint").move(0, 0, 0),
         box(w - 0.12, 0.004, h - 0.12, mat=img_mat, uv=("fit", "y")).bake().move(0, -0.004, 0)]
    for (sx, sz, x, z) in [(w, 0.03, 0, h / 2 - 0.015), (w, 0.03, 0, -h / 2 + 0.015),
                           (0.03, h - 0.06, -w / 2 + 0.015, 0), (0.03, h - 0.06, w / 2 - 0.015, 0)]:
        P.append(box(sx, 0.025, sz, mat="Black_Metal").move(x, -0.01, z))
    return P


# --------------------------------------------------------------- props ------
def turntable():
    P = [rbox(0.42, 0.34, 0.07, 0.008, mat="Oak", level=1).bake().move(0, 0, 0.045)]
    for sx in (-1, 1):
        for sy in (-1, 1):
            P.append(lathe([(0.018, 0.0), (0.018, 0.01)], m=2, mat="Rubber").move(sx * 0.17, sy * 0.13, 0))
    P.append(lathe([(0.145, 0.08), (0.145, 0.1)], m=8, mat="Aluminium").move(-0.04, 0, 0))
    rec = lathe([(0.148, 0.1), (0.148, 0.102)], m=8, mat="Vinyl", uv=("fit", "z")).bake()
    rec.by_normal(lambda n, c: abs(n[2]) > 0.9, "Record_Label", "Vinyl")
    P.append(rec.move(-0.04, 0, 0))
    P.append(lathe([(0.025, 0.08), (0.025, 0.1)], m=3, mat="Aluminium").move(0.15, 0.1, 0))
    P.append(sweep([(0.15, 0.1, 0.11), (0.13, 0.0, 0.112), (0.08, -0.07, 0.108)], 0.004, m=2, mat="Aluminium"))
    P.append(box(0.02, 0.035, 0.01, mat="Black_Metal").rot("z", 35).move(0.075, -0.08, 0.105))
    return P


def sleeve(cover, disc=True):
    s = box(0.315, 0.004, 0.315, mat=cover, uv=("fit", "y")).bake()
    s.by_normal(lambda n, c: abs(n[1]) > 0.9, cover, "Cardboard")
    P = [s.move(0, 0, 0.1575)]
    if disc:
        d = lathe([(0.148, -0.001), (0.148, 0.001)], m=8, mat="Vinyl").rot("x", 90).move(0.07, 0, 0.1575)
        P.append(d)
    return P


def mug():
    body = lathe([(0.034, 0.0), (0.04, 0.006), (0.041, 0.09), (0.037, 0.09), (0.035, 0.012)], m=5, mat="Ceramic")
    coffee = lathe([(0.0355, 0.05), (0.0355, 0.075)], m=5, mat="Coffee")
    handle = sweep(bezier((0.037, 0, 0.075), (0.085, 0, 0.08), (0.085, 0, 0.025), (0.037, 0, 0.03), 9), 0.006, m=2, mat="Ceramic")
    return [body, coffee, handle]


def book(w, h, t, cover):
    b = box(w, h, t, mat=cover).bake()
    b.by_normal(lambda n, c: abs(n[2]) > 0.9 or n[0] < -0.9, cover, "Paper")
    return [b.move(0, 0, t / 2)]


def pillow():
    p = cushion(0.42, 0.42, 0.12, r=0.08, mat="Fabric_Pillow", segs=(3, 3, 1), puff=0.05, level=2)
    p.by_normal(lambda n, c: abs(n[2]) > 0.45, "Fabric_Pillow", "Pillow_Piping")
    return [p]


# --------------------------------------------------------------- scene ------
def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    mk.set_material_resolver(get_mat, tile)
    sc = bpy.context.scene
    for n in ("Room", "Furniture", "Grabbables", "Lights"):
        c = bpy.data.collections.new(n)
        sc.collection.children.link(c)
        COL[n] = c
    room()
    obj("Sofa", sofa(), (2.6, RD - 0.47, 0), 0)
    obj("Armchair", sofa(W=0.85, D=0.82, fabric="Fabric_Chair", seats=1), (3.85, 2.45, 0), -58)
    obj("Coffee_Table", coffee_table(), (2.55, 2.85, 0), 0, bevel=0.004)
    obj("Sideboard", sideboard(), (0.245, (WIN["y0"] + WIN["y1"]) / 2, 0), 90, bevel=0.003)
    obj("Bookshelf", bookshelf(), (0.17, 0.68, 0), 90, bevel=0.002)
    obj("Floor_Lamp", floor_lamp(), (3.95, RD - 0.35, 0), 0)
    rg = obj("Rug", rug(), (2.5, 2.85, 0), 0)
    rg.data.materials.append(get_mat("Rug_Edge"))
    m = rg.modifiers.new("Solidify", "SOLIDIFY")
    m.thickness, m.offset, m.material_offset_rim = 0.012, -1, 1
    obj("Plant", plant(), (0.42, RD - 0.38, 0), 0)
    obj("Poster_Left", frame("Poster_1", 0.5, 0.67), (2.2, RD - 0.005, 1.5), 0, col="Furniture")
    obj("Poster_Right", frame("Poster_2", 0.5, 0.5), (2.95, RD - 0.005, 1.42), 0, col="Furniture")

    sb_y = (WIN["y0"] + WIN["y1"]) / 2
    obj("Record_Player", turntable(), (0.24, sb_y - 0.25, 0.65), 90, col="Grabbables")
    rec = obj("Record_Sleeve", sleeve("Album_1"), (0.55, sb_y + 0.42, 0), 90, col="Grabbables")
    rec.rotation_euler = (math.radians(-14), 0, math.radians(90))
    obj("Record_Sleeve_2", [p.rot("x", 90) for p in sleeve("Album_2", disc=False)], (2.7, 2.9 + 0.1575, 0.4175 + 0.002), 25, col="Grabbables")
    obj("Mug", mug(), (2.45, 2.65, 0.4175), 20, col="Grabbables")
    obj("Book_A", book(0.17, 0.24, 0.03, "Book_2"), (2.2, 2.92, 0.4175), -8, col="Grabbables")
    obj("Book_B", book(0.15, 0.21, 0.025, "Book_1"), (2.2, 2.93, 0.4475), 12, col="Grabbables")
    pl = obj("Pillow", pillow(), (1.85, RD - 0.46, 0.70), 0, col="Grabbables")
    pl.rotation_euler = (math.radians(70), 0, math.radians(15))
    pl2 = obj("Pillow_2", pillow(), (3.35, RD - 0.46, 0.70), 0, col="Grabbables")
    pl2.rotation_euler = (math.radians(72), 0, math.radians(-12))

    # lights
    def light(name, kind, loc, energy, color, size=None, target=None, cam=False):
        ld = bpy.data.lights.new(name, kind)
        ld.energy, ld.color = energy, color
        if kind == "AREA":
            ld.shape, ld.size, ld.size_y = "RECTANGLE", size[0], size[1]
        elif kind == "SUN":
            ld.angle = math.radians(size)
        else:
            ld.shadow_soft_size = size
        ob = bpy.data.objects.new(name, ld)
        ob.location = loc
        COL["Lights"].objects.link(ob)
        if target:
            ob.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        ob.visible_camera = cam
        return ob
    sun = light("Sun", "SUN", (-4, 3, 4), 8.0, (1.0, 0.88, 0.74), size=1.2)
    sun.rotation_euler = Vector((1.0, -0.2, -0.75)).to_track_quat("-Z", "Y").to_euler()
    light("Window_Light", "AREA", (0.03, (WIN["y0"] + WIN["y1"]) / 2, 1.55), 40, (0.85, 0.9, 1.0),
          size=(1.4, 1.3), target=(3, 2.3, 1.2))
    light("Lamp_Light", "POINT", (3.95, RD - 0.35, 1.44), 40, (1.0, 0.75, 0.5), size=0.05)
    light("Fill_Light", "AREA", (2.8, 0.4, 2.6), 35, (1.0, 0.95, 0.9), size=(3.0, 1.0), target=(2.5, 3.5, 0.5))
    world = bpy.data.worlds.new("World")
    world.use_nodes = True
    sc.world = world
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.5, 0.65, 0.9, 1)
    bg.inputs["Strength"].default_value = 0.6

    cd = bpy.data.cameras.new("Camera")
    cd.lens, cd.shift_y = 26, -0.05
    cam = bpy.data.objects.new("Camera", cd)
    cam.location = (4.75, -1.25, 1.5)
    cam.rotation_euler = (Vector((1.6, 3.0, 1.5)) - cam.location).to_track_quat("-Z", "Y").to_euler()
    sc.collection.objects.link(cam)
    sc.camera = cam

    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = 160
    sc.cycles.use_denoising = True
    sc.render.resolution_x, sc.render.resolution_y = 1920, 1080
    sc.render.filepath = os.path.join(OUT, NAME + ".png")

    dg = bpy.context.evaluated_depsgraph_get()
    tot = bad = 0
    for ob in bpy.data.objects:
        if ob.type == "MESH":
            me = ob.evaluated_get(dg).to_mesh()
            tot += len(me.polygons)
            bad += sum(1 for p in me.polygons if len(p.vertices) != 4)
            used = {ob.material_slots[p.material_index].material.name for p in me.polygons}
            print(f"  {ob.name:18s} {len(me.polygons):6d}  {len(used)} mats", "" if len(used) > 1 else "  <-- 1 MATERIAL")
    print("TOTAL faces", tot, "non-quads", bad)

    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, NAME + ".blend"), compress=True)
    bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, NAME + ".glb"), export_format="GLB",
                              export_yup=True, export_apply=True)
    if "--render" in sys.argv:
        bpy.ops.render.render(write_still=True)
    print("done")


if __name__ == "__main__":
    main()
