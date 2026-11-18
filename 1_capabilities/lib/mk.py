"""mk.py - quad-only procedural mesh toolkit (Blender 5.2, bpy module).

Every primitive returns a Part: a plain-python/numpy description of a closed,
all-quad surface plus its material name and UV mode. Parts are combined into
Blender objects by `build_object`. No primitive ever emits a triangle or n-gon:
round caps use an elliptically mapped square grid ("quad disk") instead of a
triangle fan, so the whole scene stays 100 % quads.
"""
import math
import numpy as np
import bpy
import bmesh


# ----------------------------------------------------------------- Part ----
class Part:
    __slots__ = ("v", "f", "mat", "uv", "smooth", "fmat", "fuv")

    def __init__(self, v, f, mat="default", uv=None, smooth=True):
        self.v = np.asarray(v, dtype=np.float64).reshape(-1, 3)
        self.f = [tuple(int(i) for i in face) for face in f]
        self.mat = mat
        self.uv = uv
        self.smooth = smooth
        self.fmat = None          # optional per-face material override list
        self.fuv = None           # optional baked per-face-loop UVs

    def copy(self):
        p = Part(self.v.copy(), list(self.f), self.mat, self.uv, self.smooth)
        p.fmat = None if self.fmat is None else list(self.fmat)
        p.fuv = None if self.fuv is None else [a.copy() for a in self.fuv]
        return p

    def bake(self):
        """Freeze UVs in the current (local) orientation; later rot/move keep them."""
        self.fuv = [_uv_for_part(self, fc, self.v) for fc in self.f]
        return self

    def by_normal(self, test, mat_true, mat_false=None):
        """Per-face material: test(normal, centroid) -> bool."""
        mat_false = mat_false or self.mat
        fm = []
        for fc in self.f:
            vs = self.v[list(fc)]
            n = np.cross(vs[1] - vs[0], vs[2] - vs[0])
            if len(fc) == 4:
                n = n + np.cross(vs[2] - vs[0], vs[3] - vs[0])
            n = n / (np.linalg.norm(n) + 1e-12)
            fm.append(mat_true if test(n, vs.mean(0)) else mat_false)
        self.fmat = fm
        self.mat = mat_false if mat_false in fm else mat_true
        return self

    # transforms (return self for chaining)
    def move(self, x=0.0, y=0.0, z=0.0):
        self.v += np.array([x, y, z])
        return self

    def scale(self, sx, sy=None, sz=None):
        sy = sx if sy is None else sy
        sz = sx if sz is None else sz
        self.v *= np.array([sx, sy, sz])
        if sx * sy * sz < 0:
            self.f = [tuple(reversed(face)) for face in self.f]
            if self.fmat is not None:
                pass
        return self

    def rot(self, axis, deg):
        a = math.radians(deg)
        c, s = math.cos(a), math.sin(a)
        if axis == "x":
            m = np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
        elif axis == "y":
            m = np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
        else:
            m = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
        self.v = self.v @ m.T
        return self

    def set(self, **kw):
        for k, val in kw.items():
            setattr(self, k, val)
        return self


def merge_parts(parts):
    """Concatenate parts that share one material/uv into a single Part."""
    vs, fs, off = [], [], 0
    for p in parts:
        vs.append(p.v)
        fs += [tuple(i + off for i in face) for face in p.f]
        off += len(p.v)
    return Part(np.vstack(vs), fs, parts[0].mat, parts[0].uv, parts[0].smooth)


# ----------------------------------------------------------- primitives ----
def grid_box(xs, ys, zs):
    """Closed all-quad box surface whose cut lines are given per axis."""
    xs, ys, zs = list(xs), list(ys), list(zs)
    nx, ny, nz = len(xs), len(ys), len(zs)
    idx, verts = {}, []

    def vid(i, j, k):
        key = (i, j, k)
        if key not in idx:
            idx[key] = len(verts)
            verts.append((xs[i], ys[j], zs[k]))
        return idx[key]

    faces = []
    # -X / +X
    for i, sgn in ((0, -1), (nx - 1, 1)):
        for j in range(ny - 1):
            for k in range(nz - 1):
                q = [vid(i, j, k), vid(i, j + 1, k), vid(i, j + 1, k + 1), vid(i, j, k + 1)]
                faces.append(q if sgn > 0 else q[::-1])
    for j, sgn in ((0, -1), (ny - 1, 1)):
        for i in range(nx - 1):
            for k in range(nz - 1):
                q = [vid(i, j, k), vid(i, j, k + 1), vid(i + 1, j, k + 1), vid(i + 1, j, k)]
                faces.append(q if sgn > 0 else q[::-1])
    for k, sgn in ((0, -1), (nz - 1, 1)):
        for i in range(nx - 1):
            for j in range(ny - 1):
                q = [vid(i, j, k), vid(i + 1, j, k), vid(i + 1, j + 1, k), vid(i, j + 1, k)]
                faces.append(q if sgn > 0 else q[::-1])
    return np.array(verts), faces


def _cuts(size, r, n=1):
    """Axis cut list -size/2..size/2 with support loops at distance r."""
    h = size / 2.0
    if r <= 0 or r * 2 >= size:
        return list(np.linspace(-h, h, n + 1))
    mid = list(np.linspace(-h + r, h - r, n + 1))
    return [-h] + mid + [h]


def box(sx, sy, sz, mat="default", uv=None, segs=(1, 1, 1)):
    """Hard box centred on origin (flat shaded)."""
    v, f = grid_box(np.linspace(-sx / 2, sx / 2, segs[0] + 1),
                    np.linspace(-sy / 2, sy / 2, segs[1] + 1),
                    np.linspace(-sz / 2, sz / 2, segs[2] + 1))
    return Part(v, f, mat, uv, smooth=False)


def rbox(sx, sy, sz, r=0.01, mat="default", uv=None, segs=(1, 1, 1), level=1):
    """Rounded box: support loops at distance r + Catmull-Clark subdivision."""
    v, f = grid_box(_cuts(sx, r, segs[0]), _cuts(sy, r, segs[1]), _cuts(sz, r, segs[2]))
    p = Part(v, f, mat, uv, smooth=True)
    return subsurf(p, level) if level else p


def cushion(sx, sy, sz, r=0.05, mat="default", uv=None, segs=(4, 4, 1), puff=0.012, level=2):
    """Soft cushion: rounded box whose top/bottom faces bulge slightly."""
    v, f = grid_box(_cuts(sx, r, segs[0]), _cuts(sy, r, segs[1]), _cuts(sz, r, segs[2]))
    v = np.array(v)
    nx = np.clip(1 - (2 * v[:, 0] / sx) ** 2, 0, 1)
    ny = np.clip(1 - (2 * v[:, 1] / sy) ** 2, 0, 1)
    v[:, 2] += np.sign(v[:, 2]) * puff * nx * ny
    p = Part(v, f, mat, uv, smooth=True)
    return subsurf(p, level)


# --------------------------------------------------------- quad disk -------
def ring_angles(m):
    """Angles of a 4m-vertex ring matching quad_disk(m) boundary order."""
    n = 4 * m
    return [-math.pi * 0.75 + 2 * math.pi * k / n for k in range(n)]


def quad_disk(m, relax=6):
    """All-quad unit disk built from an m x m square grid.

    Returns (verts2d (N,2), faces, boundary) where boundary lists the 4m
    boundary vertex ids counter-clockwise, starting at angle -135 deg, so it
    lines up with ring_angles(m).
    """
    g = np.linspace(-1, 1, m + 1)
    X, Y = np.meshgrid(g, g, indexing="ij")
    U = X * np.sqrt(1 - Y ** 2 / 2)
    V = Y * np.sqrt(1 - X ** 2 / 2)
    pts = np.stack([U.ravel(), V.ravel()], 1)

    def vid(i, j):
        return i * (m + 1) + j

    faces = []
    for i in range(m):
        for j in range(m):
            faces.append((vid(i, j), vid(i + 1, j), vid(i + 1, j + 1), vid(i, j + 1)))
    # boundary ccw from corner (-1,-1)
    b = []
    for i in range(m):
        b.append(vid(i, 0))
    for j in range(m):
        b.append(vid(m, j))
    for i in range(m, 0, -1):
        b.append(vid(i, m))
    for j in range(m, 0, -1):
        b.append(vid(0, j))
    ang = ring_angles(m)
    for k, vi in enumerate(b):
        pts[vi] = (math.cos(ang[k]), math.sin(ang[k]))
    # Laplacian relaxation of interior verts for even quads
    bset = set(b)
    nb = {i: set() for i in range(len(pts))}
    for fc in faces:
        for a in range(4):
            nb[fc[a]].add(fc[(a + 1) % 4])
            nb[fc[a]].add(fc[(a - 1) % 4])
    for _ in range(relax):
        new = pts.copy()
        for i in range(len(pts)):
            if i in bset:
                continue
            new[i] = 0.5 * pts[i] + 0.5 * pts[list(nb[i])].mean(0)
        pts = new
    return pts, faces, b


def lathe(profile, m=6, cap_bottom=True, cap_top=True, closed=False,
          mat="default", uv=None, smooth=True):
    """Revolve a (r, z) profile around Z. Caps are quad disks (no poles).

    closed=True connects the last profile point back to the first
    (used for tori / ring shapes)."""
    ang = ring_angles(m)
    n = len(ang)
    verts, faces = [], []
    rings = []
    for (r, z) in profile:
        ring = []
        for a in ang:
            ring.append(len(verts))
            verts.append((r * math.cos(a), r * math.sin(a), z))
        rings.append(ring)
    nr = len(rings)
    for k in range(nr - 1 + (1 if closed else 0)):
        r0, r1 = rings[k], rings[(k + 1) % nr]
        for i in range(n):
            j = (i + 1) % n
            faces.append((r0[i], r0[j], r1[j], r1[i]))

    def cap(ring, r, z, up):
        pts, df, b = quad_disk(m)
        remap = {}
        for k, vi in enumerate(b):
            remap[vi] = ring[k]
        for vi in range(len(pts)):
            if vi not in remap:
                remap[vi] = len(verts)
                verts.append((pts[vi][0] * r, pts[vi][1] * r, z))
        for fc in df:
            q = tuple(remap[i] for i in fc)
            faces.append(q if up else q[::-1])

    if cap_bottom and not closed:
        cap(rings[0], profile[0][0], profile[0][1], False)
    if cap_top and not closed:
        cap(rings[-1], profile[-1][0], profile[-1][1], True)
    p = Part(np.array(verts), faces, mat, uv, smooth)
    return orient_outward(p)


def cylinder(r, h, m=6, mat="default", uv=None, bevel=0.0, z0=0.0):
    """Cylinder from z0 to z0+h; optional small bevel rings for crisp highlights."""
    if bevel > 0:
        b = bevel
        prof = [(r - b, z0), (r - b * 0.3, z0 + b * 0.05), (r, z0 + b), (r, z0 + h - b),
                (r - b * 0.3, z0 + h - b * 0.05), (r - b, z0 + h)]
    else:
        prof = [(r, z0), (r, z0 + h)]
    return lathe(prof, m, mat=mat, uv=uv)


def sweep(path, radius, m=3, closed=False, caps=True, mat="default",
          uv=None, smooth=True, profile_scale=None):
    """Sweep a circular (4m-gon) profile along a polyline with parallel transport."""
    P = np.asarray(path, dtype=np.float64)
    npts = len(P)
    T = np.zeros_like(P)
    for i in range(npts):
        if closed:
            T[i] = P[(i + 1) % npts] - P[i - 1]
        else:
            T[i] = P[min(i + 1, npts - 1)] - P[max(i - 1, 0)]
        T[i] /= np.linalg.norm(T[i])
    ref = np.array([0, 0, 1.0]) if abs(T[0][2]) < 0.9 else np.array([1.0, 0, 0])
    N = np.cross(T[0], ref)
    N /= np.linalg.norm(N)
    ang = ring_angles(m)
    verts, faces, rings = [], [], []
    rad = radius if callable(radius) else (lambda t: radius)
    for i in range(npts):
        if i > 0:
            N = N - np.dot(N, T[i]) * T[i]
            N /= np.linalg.norm(N)
        B = np.cross(T[i], N)
        rr = rad(i / max(npts - 1, 1))
        ring = []
        for a in ang:
            off = (math.cos(a) * N + math.sin(a) * B) * rr
            if profile_scale is not None:
                off = math.cos(a) * N * rr * profile_scale[0] + math.sin(a) * B * rr * profile_scale[1]
            ring.append(len(verts))
            verts.append(P[i] + off)
        rings.append(ring)
    n = len(ang)
    for k in range(npts - 1 + (1 if closed else 0)):
        r0, r1 = rings[k], rings[(k + 1) % npts]
        for i in range(n):
            j = (i + 1) % n
            faces.append((r0[i], r0[j], r1[j], r1[i]))
    if caps and not closed:
        for end in (0, npts - 1):
            pts, df, b = quad_disk(m)
            Tn = T[end]
            Nn = (np.array(verts[rings[end][0]]) - P[end])
            # rebuild local frame from ring
            a0 = np.array(verts[rings[end][0]]) - P[end]
            a1 = np.array(verts[rings[end][m]]) - P[end]
            c0, s0 = math.cos(ang[0]), math.sin(ang[0])
            c1, s1 = math.cos(ang[m]), math.sin(ang[m])
            M = np.array([[c0, s0], [c1, s1]])
            Minv = np.linalg.inv(M)
            Nv = Minv[0, 0] * a0 + Minv[0, 1] * a1
            Bv = Minv[1, 0] * a0 + Minv[1, 1] * a1
            remap = {b[k]: rings[end][k] for k in range(len(b))}
            for vi in range(len(pts)):
                if vi not in remap:
                    remap[vi] = len(verts)
                    verts.append(P[end] + pts[vi][0] * Nv + pts[vi][1] * Bv)
            for fc in df:
                q = tuple(remap[i] for i in fc)
                faces.append(q)
    p = Part(np.array(verts), faces, mat, uv, smooth)
    return orient_outward(p)


def bezier(p0, p1, p2, p3, n=16):
    t = np.linspace(0, 1, n)[:, None]
    p0, p1, p2, p3 = map(np.asarray, (p0, p1, p2, p3))
    return ((1 - t) ** 3) * p0 + 3 * ((1 - t) ** 2) * t * p1 + 3 * (1 - t) * t * t * p2 + t ** 3 * p3


# -------------------------------------------------------- 2D -> solid ------
def solidify2d(pts2d, faces, thickness, mat="default", uv=None, smooth=False):
    """Extrude a flat 2D quad mesh (in XZ plane, y=0) to a closed slab y in [0,t]."""
    pts2d = np.asarray(pts2d)
    n = len(pts2d)
    front = np.column_stack([pts2d[:, 0], np.zeros(n), pts2d[:, 1]])
    back = front.copy()
    back[:, 1] = thickness
    verts = np.vstack([front, back])
    out = []
    ecount = {}
    for fc in faces:
        out.append(tuple(fc))
        out.append(tuple(i + n for i in reversed(fc)))
        for a in range(len(fc)):
            e = (fc[a], fc[(a + 1) % len(fc)])
            ecount[e] = ecount.get(e, 0) + 1
    for (a, b) in list(ecount):
        if (b, a) not in ecount:            # boundary edge
            out.append((b, a, a + n, b + n))
    p = Part(verts, out, mat, uv, smooth)
    return orient_outward(p)


def grid2d(x0, x1, z0, z1, nx, nz):
    xs = np.linspace(x0, x1, nx + 1)
    zs = np.linspace(z0, z1, nz + 1)
    pts = [(x, z) for x in xs for z in zs]
    faces = []
    for i in range(nx):
        for j in range(nz):
            a = i * (nz + 1) + j
            faces.append((a, a + (nz + 1), a + (nz + 1) + 1, a + 1))
    return np.array(pts), faces


def arch_wall_2d(W, H, cx, w, z0, zs, margin=0.25, nX=13, nZ_low=8, nZ_arch=9,
                 rings=3, side_div=6, low_div=3, top_div=2):
    """2D quad mesh of a wall W x H with an arched opening.

    Opening: rectangle [cx-w/2, cx+w/2] x [z0, zs] topped by a semicircle of
    radius w/2 centred at (cx, zs). Returns (pts, faces, hole_loop_ids).
    The opening is ringed by a frame of quads mapped radially from the arch
    centre, so the whole wall is all-quad with no T-junctions.
    """
    r = w / 2
    xa, xb = cx - r - margin, cx + r + margin
    zb, zt = z0 - margin, zs + r + margin
    c = np.array([cx, zs])
    # x where the ray through the sill corners meets the frame bottom
    k = (zs - zb) / (zs - z0)
    xL, xR = cx - r * k, cx + r * k
    X_R = sorted(set(np.round(np.concatenate([
        np.linspace(xa, xL, 2), np.linspace(xL, xR, nX), np.linspace(xR, xb, 2)]), 6)))
    Z_R = sorted(set(np.round(np.concatenate([
        np.linspace(zb, zs, nZ_low), np.linspace(zs, zt, nZ_arch)]), 6)))
    Xs = sorted(set(np.round(np.concatenate([
        np.linspace(0, xa, side_div + 1), X_R, np.linspace(xb, W, side_div + 1)]), 6)))
    Zs = sorted(set(np.round(np.concatenate([
        np.linspace(0, zb, low_div + 1), Z_R, np.linspace(zt, H, top_div + 1)]), 6)))
    nxg, nzg = len(Xs), len(Zs)
    pts = [(x, z) for x in Xs for z in Zs]

    def gid(i, j):
        return i * nzg + j

    faces = []
    for i in range(nxg - 1):
        for j in range(nzg - 1):
            mx = (Xs[i] + Xs[i + 1]) / 2
            mz = (Zs[j] + Zs[j + 1]) / 2
            if xa < mx < xb and zb < mz < zt:
                continue
            faces.append((gid(i, j), gid(i + 1, j), gid(i + 1, j + 1), gid(i, j + 1)))
    ia, ib = Xs.index(round(xa, 6)), Xs.index(round(xb, 6))
    ja, jb = Zs.index(round(zb, 6)), Zs.index(round(zt, 6))
    loop = []
    for i in range(ia, ib):
        loop.append(gid(i, ja))
    for j in range(ja, jb):
        loop.append(gid(ib, j))
    for i in range(ib, ia, -1):
        loop.append(gid(i, jb))
    for j in range(jb, ja, -1):
        loop.append(gid(ia, j))

    def hit(p):
        d = np.array(p) - c
        if d[1] >= -1e-9:
            return c + d / np.linalg.norm(d) * r
        ts = []
        if abs(d[0]) > 1e-9:
            ts.append(r / abs(d[0]))
        ts.append((z0 - zs) / d[1])
        return c + d * min(ts)

    pts = [list(p) for p in pts]
    outer = loop
    inner_pts = [hit(pts[i]) for i in loop]
    prev = outer
    for s in range(1, rings + 1):
        t = s / rings
        ring = []
        for kk, vi in enumerate(loop):
            po = np.array(pts[vi])
            pi = inner_pts[kk]
            # ease: denser near the opening
            tt = 1 - (1 - t) ** 1.4
            ring.append(len(pts))
            pts.append(list(po + (pi - po) * tt))
        n = len(loop)
        for kk in range(n):
            a, b = prev[kk], prev[(kk + 1) % n]
            faces.append((a, b, ring[(kk + 1) % n], ring[kk]))
        prev = ring
    return np.array(pts), faces, prev


def arch_pane_2d(cx, w, z0, zs, nx=8, nz=6):
    """All-quad fill of the arched opening (rectangle + half quad-disk)."""
    r = w / 2
    m = nx // 2 * 2
    pts, faces = [], []
    # rectangle part
    xs = np.linspace(cx - r, cx + r, m + 1)
    zz = np.linspace(z0, zs, nz + 1)
    for x in xs:
        for z in zz:
            pts.append((x, z))

    def rid(i, j):
        return i * (nz + 1) + j
    for i in range(m):
        for j in range(nz):
            faces.append((rid(i, j), rid(i + 1, j), rid(i + 1, j + 1), rid(i, j + 1)))
    # half disk: elliptical grid mapping of [-1,1]x[0,1] (m x m/2 cells)
    g = np.linspace(-1, 1, m + 1)
    h = np.linspace(0, 1, m // 2 + 1)
    base = len(pts)
    hid = {}
    for i, X in enumerate(g):
        for j, Y in enumerate(h):
            if j == 0:
                hid[(i, j)] = rid(i, nz)
                continue
            U = X * math.sqrt(1 - Y * Y / 2)
            V = Y * math.sqrt(1 - X * X / 2)
            hid[(i, j)] = len(pts)
            pts.append((cx + U * r, zs + V * r))
    # snap arc boundary to the true circle with even angles
    bnd = [(m, j) for j in range(1, m // 2 + 1)] + [(i, m // 2) for i in range(m - 1, 0, -1)] + \
          [(0, j) for j in range(m // 2, 0, -1)]
    for k, key in enumerate(bnd):
        a = math.pi * (k + 1) / (len(bnd) + 1)
        pts[hid[key]] = (cx + r * math.cos(a), zs + r * math.sin(a))
    for i in range(m):
        for j in range(m // 2):
            faces.append((hid[(i, j)], hid[(i + 1, j)], hid[(i + 1, j + 1)], hid[(i, j + 1)]))
    return np.array(pts), faces


# ------------------------------------------------------------ helpers -------
def orient_outward(p):
    """Make faces of each closed shell point outward (via bmesh)."""
    bm = bmesh.new()
    vs = [bm.verts.new(tuple(v)) for v in p.v]
    for fc in p.f:
        try:
            bm.faces.new([vs[i] for i in fc])
        except ValueError:
            pass
    bm.faces.ensure_lookup_table()
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.verts.index_update()
    newf = [tuple(v.index for v in f.verts) for f in bm.faces]
    bm.free()
    p.f = newf
    return p


def subsurf(p, level=1):
    """Catmull-Clark subdivision through Blender's modifier (output: all quads)."""
    me = bpy.data.meshes.new("_tmp")
    me.from_pydata(p.v.tolist(), [], p.f)
    ob = bpy.data.objects.new("_tmp", me)
    bpy.context.scene.collection.objects.link(ob)
    mod = ob.modifiers.new("ss", "SUBSURF")
    mod.levels = level
    mod.render_levels = level
    dg = bpy.context.evaluated_depsgraph_get()
    dg.update()
    me2 = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    v = np.array([vv.co[:] for vv in me2.vertices])
    f = [tuple(pp.vertices) for pp in me2.polygons]
    bpy.data.objects.remove(ob)
    bpy.data.meshes.remove(me)
    bpy.data.meshes.remove(me2)
    q = Part(v, f, p.mat, p.uv, p.smooth)
    return q


# ---------------------------------------------------------------- UVs -------
def _uv_for_part(p, face, co):
    if p.uv is None:
        p.uv = ("box", _TILE_RESOLVER(p.mat) if _TILE_RESOLVER else 1.0)
    mode = p.uv[0]
    if mode == "box":
        s = p.uv[1]
        rot = p.uv[2] if len(p.uv) > 2 else 0.0
        vs = co[list(face)]
        nrm = np.cross(vs[1] - vs[0], vs[2] - vs[0])
        if len(face) == 4:
            nrm += np.cross(vs[2] - vs[0], vs[3] - vs[0])
        ax = int(np.argmax(np.abs(nrm)))
        if ax == 0:
            uv = vs[:, [1, 2]] * (1 if nrm[0] > 0 else -1, 1)
        elif ax == 1:
            uv = vs[:, [0, 2]] * (-1 if nrm[1] > 0 else 1, 1)
        else:
            uv = vs[:, [0, 1]]
        uv = uv / s
        if rot:
            a = math.radians(rot)
            R = np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])
            uv = uv @ R.T
        return uv
    if mode == "fit":                    # planar fit of bbox, axis = p.uv[1]
        ax = p.uv[1]
        lo, hi = p.v.min(0), p.v.max(0)
        a, b = {"x": (1, 2), "y": (0, 2), "z": (0, 1)}[ax]
        vs = co[list(face)]
        u = (vs[:, a] - lo[a]) / max(hi[a] - lo[a], 1e-9)
        v = (vs[:, b] - lo[b]) / max(hi[b] - lo[b], 1e-9)
        flip = p.uv[2] if len(p.uv) > 2 else False
        if flip:
            u = 1 - u
        return np.column_stack([u, v])
    if mode == "cyl":                    # cylindrical around local Z
        s = p.uv[1]
        vs = co[list(face)]
        ang = np.arctan2(vs[:, 1], vs[:, 0])
        # avoid seam wrap within one face
        if ang.max() - ang.min() > math.pi:
            ang = np.where(ang < 0, ang + 2 * math.pi, ang)
        return np.column_stack([ang / (2 * math.pi) * 3.0, vs[:, 2] / s])
    raise ValueError(mode)


# ------------------------------------------------------- object builder ----
def build_object(name, parts, location=(0, 0, 0), rotation_z=0.0,
                 collection=None, sharp_angle=35.0):
    """Create one Blender mesh object from a list of Parts.

    UVs are computed per part *before* the object transform so textures stay
    locked to the object. Faces of every part are smooth shaded with sharp
    edges above `sharp_angle` (auto-smooth equivalent, glTF safe)."""
    mats = []
    for p in parts:
        names = [p.mat] if p.fmat is None else sorted(set(p.fmat))
        for mname in names:
            if mname not in mats:
                mats.append(mname)
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    for p in parts:
        bv = [bm.verts.new(tuple(v)) for v in p.v]
        for fi, fc in enumerate(p.f):
            try:
                f = bm.faces.new([bv[i] for i in fc])
            except ValueError:
                continue
            mname = p.mat if p.fmat is None else p.fmat[fi]
            f.material_index = mats.index(mname)
            f.smooth = p.smooth
            uv = p.fuv[fi] if p.fuv is not None else _uv_for_part(p, fc, p.v)
            for li, loop in enumerate(f.loops):
                loop[uvl].uv = (float(uv[li][0]), float(uv[li][1]))
    bm.normal_update()
    lim = math.radians(sharp_angle)
    for e in bm.edges:
        if len(e.link_faces) == 2:
            a, b = e.link_faces
            if a.normal.angle(b.normal, 0.0) > lim or a.smooth != b.smooth \
                    or a.material_index != b.material_index:
                e.smooth = False
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for mname in mats:
        me.materials.append(get_material(mname))
    ob = bpy.data.objects.new(name, me)
    ob.location = location
    ob.rotation_euler = (0, 0, math.radians(rotation_z))
    (collection or bpy.context.scene.collection).objects.link(ob)
    return ob


_MAT_RESOLVER = None
_TILE_RESOLVER = None


def set_material_resolver(fn, tile_fn=None):
    """fn(name) -> bpy material; tile_fn(name) -> metres per texture repeat."""
    global _MAT_RESOLVER, _TILE_RESOLVER
    _MAT_RESOLVER = fn
    _TILE_RESOLVER = tile_fn


def get_material(name):
    if _MAT_RESOLVER is not None:
        return _MAT_RESOLVER(name)
    m = bpy.data.materials.get(name)
    if m is None:
        m = bpy.data.materials.new(name)
    return m
