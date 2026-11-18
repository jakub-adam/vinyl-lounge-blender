"""tex.py - numpy texture generator (seamless where it matters).

All generators return float32 arrays in [0,1]: colour (H,W,3), roughness
(H,W) and height (H,W). `save_set` writes *_col.png, *_rough.png and
*_nrm.png (OpenGL tangent-space normal map from the height field).
"""
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from scipy import ndimage as ndi

FONT_DIR = "/usr/share/fonts/opentype/inter/"


# ------------------------------------------------------------- noise -------
def periodic_noise(size, cells, rng, order=3):
    """Smooth tileable value noise; cells may be (cx, cy) for anisotropy."""
    if np.isscalar(cells):
        cells = (cells, cells)
    lat = rng.random((cells[1], cells[0]))
    zy, zx = size / cells[1], size / cells[0]
    out = ndi.zoom(lat, (zy, zx), order=order, mode="grid-wrap", grid_mode=True)
    return out[:size, :size]


def fbm(size, base, octaves, rng, gain=0.5, aniso=(1, 1)):
    acc = np.zeros((size, size))
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        c = base * 2 ** o
        cx = max(1, int(c * aniso[0]))
        cy = max(1, int(c * aniso[1]))
        if cx > size or cy > size:
            break
        acc += amp * periodic_noise(size, (cx, cy), rng)
        tot += amp
        amp *= gain
    return acc / tot


def norm01(a):
    a = a - a.min()
    return a / max(a.max(), 1e-9)


def lerp(a, b, t):
    t = np.asarray(t)[..., None] if np.ndim(t) == 2 else t
    return a + (np.asarray(b) - np.asarray(a)) * t


def hexc(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)])


def ramp(t, stops):
    """Colour ramp: stops = [(pos, '#hex'), ...]."""
    t = np.clip(t, 0, 1)
    pos = np.array([s[0] for s in stops])
    cols = np.array([hexc(s[1]) for s in stops])
    out = np.zeros(t.shape + (3,))
    for c in range(3):
        out[..., c] = np.interp(t, pos, cols[:, c])
    return out


# ---------------------------------------------------------- io helpers -----
def to_img(a):
    a = np.clip(a, 0, 1)
    if a.ndim == 2:
        return Image.fromarray((a * 255 + 0.5).astype(np.uint8), "L")
    return Image.fromarray((a * 255 + 0.5).astype(np.uint8), "RGB")


def normal_from_height(h, strength=2.0, wrap=True):
    mode = "wrap" if wrap else "nearest"
    dx = ndi.sobel(h, axis=1, mode=mode) / 8.0
    dy = ndi.sobel(h, axis=0, mode=mode) / 8.0
    s = strength * h.shape[0] / 256.0
    nx, ny, nz = -dx * s, dy * s, np.ones_like(h)
    l = np.sqrt(nx * nx + ny * ny + nz * nz)
    return np.stack([nx / l * 0.5 + 0.5, ny / l * 0.5 + 0.5, nz / l * 0.5 + 0.5], -1)


def save_set(outdir, name, col, rough=None, height=None, nstrength=2.0, wrap=True):
    """Colour + normal as JPEG (keeps the .glb small), roughness as half-res PNG."""
    to_img(col).save(f"{outdir}/{name}_col.jpg", quality=92)
    if rough is not None:
        r = to_img(rough)
        r = r.resize((max(r.width // 2, 64), max(r.height // 2, 64)), Image.LANCZOS)
        r.save(f"{outdir}/{name}_rough.png")
    if height is not None:
        to_img(normal_from_height(height, nstrength, wrap)).save(
            f"{outdir}/{name}_nrm.jpg", quality=94)


# ------------------------------------------------------------ woods --------
WALNUT = [(0, "#2a160c"), (0.35, "#4a2a17"), (0.65, "#6b4026"), (1, "#8a5a36")]
OAK = [(0, "#8a6a45"), (0.4, "#b38d5f"), (0.75, "#c9a675"), (1, "#dcbd8e")]


def wood_field(size, rng, rings=18, stretch=12, warp=0.6):
    """Grain running along X. Returns t in [0,1] (ring phase) and fine pores."""
    # warp varies slowly along the grain (x) and a bit faster across it (y)
    n1 = fbm(size, 2, 3, rng, gain=0.45, aniso=(0.5, 1.5))
    # long thin streaks along the grain
    n2 = fbm(size, 4, 5, rng, gain=0.6, aniso=(0.25, stretch))
    y = np.linspace(0, 1, size, endpoint=False)[:, None] * np.ones((1, size))
    phase = (y + warp * (n1 - 0.5) * 0.22 + 0.04 * (n2 - 0.5)) * rings
    rings_t = np.abs((phase % 1.0) * 2 - 1) ** 1.6
    pores = fbm(size, 16, 3, rng, aniso=(0.06, 6))
    return rings_t, pores, n2


def wood(size, stops, rng, rings=18, rough_base=0.45):
    rt, pores, n2 = wood_field(size, rng, rings)
    t = 0.55 * rt + 0.3 * n2 + 0.15 * pores
    col = ramp(norm01(t) * 0.9 + 0.05, stops)
    rough = rough_base + 0.15 * (1 - rt) + 0.1 * pores
    height = 0.6 * rt + 0.4 * (pores > 0.62)
    return col, np.clip(rough, 0, 1), height


def herringbone(size, rng, n=5, stops=OAK, gap=0.035):
    """Seamless herringbone parquet: tile = 2n x 2n plank widths.

    Planks are 1 x n cells. Band k: horizontal brick cells (k..k+n-1, k) and
    vertical brick cells (k+n, k+1-n..k); bands repeat by (n,-n). Each cell
    stores brick id, orientation and index along the brick, so every pixel is
    covered exactly once (no black stripes)."""
    P = 2 * n
    bid = -np.ones((P, P), int)
    ori = np.zeros((P, P), int)
    pos = np.zeros((P, P), int)
    nid = 0
    for s in range(-6, 7):
        for k in range(-3 * P, 3 * P):
            ox, oy = s * n, -s * n
            key_h = ((k + ox) % P, (k + oy) % P, 0)
            cells = [((x + ox) % P, (k + oy) % P, x - k) for x in range(k, k + n)]
            if bid[cells[0][1], cells[0][0]] < 0:
                for (cx, cy, i) in cells:
                    bid[cy, cx], ori[cy, cx], pos[cy, cx] = nid, 0, i
                nid += 1
            cells = [((k + n + ox) % P, (y + oy) % P, y - (k + 1 - n)) for y in range(k + 1 - n, k + 1)]
            if bid[cells[0][1], cells[0][0]] < 0:
                for (cx, cy, i) in cells:
                    bid[cy, cx], ori[cy, cx], pos[cy, cx] = nid, 1, i
                nid += 1
    assert (bid >= 0).all(), "herringbone coverage hole"
    cp = size / P
    yy, xx = np.mgrid[0:size, 0:size] + 0.5
    cx = (xx // cp).astype(int) % P
    cy = (yy // cp).astype(int) % P
    fx = (xx % cp) / cp
    fy = (yy % cp) / cp
    B = bid[cy, cx]
    O = ori[cy, cx]
    I = pos[cy, cx]
    along = np.where(O == 0, I + fx, I + fy)          # 0..n
    across = np.where(O == 0, fy, fx)                  # 0..1
    d_edge = np.minimum(np.minimum(across, 1 - across), np.minimum(along, n - along) / 1.0)
    # per plank random tone + grain from two oriented wood fields
    tone = rng.random(nid)
    shift = rng.random(nid)
    rt_h, pores_h, n2_h = wood_field(size, rng, rings=P * 3, stretch=16)
    rt_v, pores_v, n2_v = wood_field(size, rng, rings=P * 3, stretch=16)
    rt_v, pores_v, n2_v = rt_v.T, pores_v.T, n2_v.T
    rt = np.where(O == 0, rt_h, rt_v)
    po = np.where(O == 0, pores_h, pores_v)
    n2 = np.where(O == 0, n2_h, n2_v)
    t = 0.45 * rt + 0.25 * n2 + 0.1 * po + 0.5 * (tone[B] - 0.5)
    t = np.clip(t * 0.85 + 0.12 + 0.05 * shift[B], 0, 1)
    col = ramp(t, stops)
    # bevelled seams
    seam = np.clip(d_edge / gap, 0, 1)
    seam_s = seam ** 0.6
    col = col * (0.35 + 0.65 * seam_s)[..., None]
    rough = np.clip(0.42 + 0.12 * (1 - rt) + 0.08 * po + 0.3 * (1 - seam), 0, 1)
    height = 0.07 * rt + 0.04 * po + 0.9 * seam_s
    return col, rough, height


# ------------------------------------------------------------ stone --------
def marble(size, rng, base="#ece8e1", vein="#6b6257", gold="#b39363"):
    """Calacatta-like marble. Veins are thin level sets of a domain-warped
    phase field  phi = a.x + warp(x); vein intensity = exp(-(sin(pi*phi)/w)^2).
    Two vein families (primary bold / secondary hairline) + soft clouds."""
    yy, xx = np.mgrid[0:size, 0:size] / size
    w1 = fbm(size, 2, 4, rng, gain=0.45)
    w2 = fbm(size, 3, 4, rng, gain=0.45)
    w3 = fbm(size, 6, 5, rng, gain=0.5)
    # integer frequencies keep it tileable; low-octave warp = flowing veins,
    # small high-octave term = slightly ragged vein edges
    phi1 = 1 * xx + 1 * yy + 1.1 * (w1 - 0.5) + 0.12 * (w3 - 0.5)
    phi2 = 3 * xx - 2 * yy + 0.9 * (w2 - 0.5) + 0.15 * (w3 - 0.5)
    width = 0.035 + 0.05 * w2                                  # vein thickness varies
    v1 = np.exp(-(np.sin(math.pi * phi1) / width) ** 2)
    v1w = np.exp(-(np.sin(math.pi * phi1) / 0.2) ** 2)          # soft halo
    v2 = np.exp(-(np.sin(math.pi * phi2) / 0.018) ** 2) * np.clip(w1 * 1.6 - 0.4, 0, 1)
    clouds = fbm(size, 3, 6, rng)
    col = np.ones((size, size, 3)) * hexc(base)
    col = lerp(col, hexc("#d9d3c9"), 0.5 * norm01(clouds))
    col = lerp(col, hexc(gold), 0.35 * v1w)
    col = lerp(col, hexc(vein), np.clip(0.85 * v1 + 0.55 * v2, 0, 1))
    rough = 0.12 + 0.06 * clouds + 0.05 * v1
    height = 1 - 0.3 * v1 - 0.15 * v2
    return col, rough, height


def plaster(size, rng, c0="#d8cdbb", c1="#c9bba5", c2="#e4dccd"):
    """Lime plaster: low-frequency mottling + trowel strokes."""
    m1 = fbm(size, 2, 6, rng, gain=0.6)
    m2 = fbm(size, 6, 5, rng, gain=0.5)
    strokes = fbm(size, 3, 4, rng, aniso=(3, 1))
    t = norm01(0.55 * m1 + 0.25 * m2 + 0.2 * strokes)
    col = ramp(t, [(0, c1), (0.5, c0), (1, c2)])
    fine = fbm(size, 64, 3, rng)
    rough = 0.82 + 0.1 * fine - 0.1 * strokes
    height = 0.5 * m2 + 0.3 * strokes + 0.2 * fine
    return col, np.clip(rough, 0, 1), height


# ---------------------------------------------------------- textiles -------
def boucle(size, rng, c0="#b65a35", c1="#d67c51", c2="#8a3d22"):
    """Loopy boucle fabric: thresholded blobs at two scales."""
    a = fbm(size, 48, 2, rng)
    b = fbm(size, 96, 2, rng)
    loops = norm01(np.sin(a * 22) * 0.5 + np.sin(b * 31) * 0.5)
    low = fbm(size, 4, 3, rng)
    col = ramp(loops * 0.8 + 0.2 * low, [(0, c2), (0.55, c0), (1, c1)])
    rough = 0.9 + 0.08 * loops
    height = loops
    return col, np.clip(rough, 0, 1), height


def weave(size, rng, c0="#2b2b2e", c1="#3a3a3f", threads=128):
    """Tight plain weave (speaker grill / book cloth)."""
    yy, xx = np.mgrid[0:size, 0:size] / size * threads
    wx = np.sin(xx * 2 * math.pi) * 0.5 + 0.5
    wy = np.sin(yy * 2 * math.pi) * 0.5 + 0.5
    chk = ((np.floor(xx) + np.floor(yy)) % 2)
    h = np.where(chk > 0, wx, wy)
    n = fbm(size, 32, 3, rng)
    col = ramp(0.6 * h + 0.4 * n, [(0, c0), (1, c1)])
    return col, 0.85 + 0.1 * h, h


def leather(size, rng, c0="#7a3e1d", c1="#a3592b", c2="#4f2610"):
    """Cognac leather: ridged cellular creases + patina."""
    r1 = 1 - np.abs(fbm(size, 24, 3, rng) * 2 - 1)
    r2 = 1 - np.abs(fbm(size, 48, 2, rng) * 2 - 1)
    grain = norm01(r1 ** 3 + 0.5 * r2 ** 3)
    patina = fbm(size, 3, 4, rng)
    col = ramp(0.6 * patina + 0.4 * (1 - grain), [(0, c2), (0.5, c0), (1, c1)])
    rough = 0.38 + 0.25 * grain
    return col, np.clip(rough, 0, 1), 1 - grain


def rug(size, rng):
    """Hand-knotted style rug: border bands, central lozenge, fibre noise."""
    yy, xx = (np.mgrid[0:size, 0:size] + 0.5) / size
    dx, dy = np.abs(xx - 0.5), np.abs(yy - 0.5)
    box_d = np.maximum(dx, dy)           # 0 centre .. 0.5 edge
    dia = dx + dy
    pal = {"cream": "#e6dac3", "rust": "#a5452a", "navy": "#24324a",
           "mustard": "#c9952e", "sage": "#7f8a6a"}
    col = np.ones((size, size, 3)) * hexc(pal["cream"])
    def paint(mask, c):
        col[mask] = hexc(pal[c])
    paint(box_d > 0.455, "rust")
    paint((box_d > 0.43) & (box_d <= 0.445), "navy")
    # zig-zag band
    zz = np.abs(((xx + yy) * 24) % 2 - 1) * 0.02
    paint((box_d > 0.385 + zz) & (box_d <= 0.41 + zz), "mustard")
    paint((box_d > 0.36) & (box_d <= 0.37), "navy")
    paint(dia < 0.32, "navy")
    paint(dia < 0.27, "rust")
    paint(dia < 0.21, "cream")
    paint(((dia < 0.15) & (dia > 0.12)) | (dia < 0.05), "mustard")
    # stepped motifs in field corners
    for cxp, cyp in ((0.2, 0.2), (0.8, 0.2), (0.2, 0.8), (0.8, 0.8)):
        d = np.abs(xx - cxp) + np.abs(yy - cyp)
        paint((d < 0.07) & (d > 0.045), "sage")
        paint(d < 0.025, "rust")
    fib = fbm(size, 160, 2, rng)
    abrash = fbm(size, 3, 3, rng, aniso=(1, 0.3))
    col = col * (0.82 + 0.25 * fib)[..., None] * (0.92 + 0.12 * abrash)[..., None]
    return np.clip(col, 0, 1), 0.95 - 0.05 * fib, fib


# ------------------------------------------------------------ vinyl --------
def vinyl_disc(size, rng, label_col="#d9a441", label_text="SIDE A", accent="#1e2a44"):
    """Record face: grooves (radial height ripple) + paper label in centre."""
    yy, xx = (np.mgrid[0:size, 0:size] + 0.5) / size - 0.5
    r = np.sqrt(xx ** 2 + yy ** 2) * 2           # 0..1 at disc edge
    grooves = 0.5 + 0.5 * np.sin(r * 900)
    tracks = ((r > 0.62) & (r < 0.63)) | ((r > 0.78) & (r < 0.79)) | ((r > 0.9) & (r < 0.91))
    col = np.ones((size, size, 3)) * 0.018
    col += 0.02 * grooves[..., None]
    col[tracks] *= 0.4
    lab = r < 0.34
    col[lab] = hexc(label_col)
    ring = (r > 0.25) & (r < 0.27)
    col[ring] = hexc(accent)
    col[r < 0.03] = 0.02
    img = to_img(col)
    d = ImageDraw.Draw(img)
    try:
        f = ImageFont.truetype(FONT_DIR + "Inter-SemiBold.otf", size // 30)
        d.text((size / 2, size / 2 - size * 0.09), label_text, fill=accent, font=f, anchor="mm")
        f2 = ImageFont.truetype(FONT_DIR + "Inter-Regular.otf", size // 48)
        d.text((size / 2, size / 2 + size * 0.08), "33 1/3 RPM", fill=accent, font=f2, anchor="mm")
    except OSError:
        pass
    col = np.asarray(img) / 255.0
    rough = np.where(lab, 0.85, 0.18 + 0.1 * grooves)
    height = np.where(lab, 0.5, grooves * 0.3 + 0.3)
    return col, rough, height


# ------------------------------------------------------- album covers ------
COVERS = [
    ("Low Tide", "Marlowe Quartet", "waves"),
    ("Orbital Bloom", "Sena Vale", "circles"),
    ("Midnight Grid", "The Parallels", "grid"),
    ("Sun Dial", "Okoye & Brand", "sun"),
    ("Paper Moons", "Lia Kovac", "moons"),
    ("Static Garden", "Rue Hollis", "stripes"),
]


def album_cover(size, rng, title, artist, style):
    yy, xx = (np.mgrid[0:size, 0:size] + 0.5) / size
    if style == "waves":                                   # the "wave" texture
        col = ramp(yy, [(0, "#f2e6d0"), (1, "#e9d7b8")])
        for i in range(9):
            y0 = 0.25 + i * 0.07
            w = y0 + 0.03 * np.sin(xx * 2 * math.pi * 2 + i * 0.7) + 0.015 * np.sin(xx * 15 + i)
            band = (yy > w) & (yy < w + 0.035)
            col[band] = hexc(["#1f4e5f", "#2f6f7e", "#e07a3f", "#1f4e5f"][i % 4])
    elif style == "circles":
        col = np.ones((size, size, 3)) * hexc("#1b1f3a")
        for (cx, cy, r, c) in [(0.35, 0.45, 0.28, "#e8b04a"), (0.62, 0.52, 0.2, "#d1495b"),
                               (0.5, 0.3, 0.12, "#edae49"), (0.7, 0.75, 0.08, "#66a182")]:
            m = (xx - cx) ** 2 + (yy - cy) ** 2 < r * r
            col[m] = col[m] * 0.25 + hexc(c) * 0.75
    elif style == "grid":
        col = np.ones((size, size, 3)) * hexc("#111111")
        g = ((xx * 12) % 1 < 0.06) | ((yy * 12) % 1 < 0.06)
        col[g] = hexc("#3df2c2")
        m = (np.abs(xx - 0.5) < 0.2) & (np.abs(yy - 0.42) < 0.2)
        col[m] = hexc("#ff3d7f")
    elif style == "sun":
        col = ramp(yy, [(0, "#f7c873"), (0.6, "#e9724c"), (1, "#7a2a3a")])
        m = (xx - 0.5) ** 2 + (yy - 0.62) ** 2 < 0.09
        col[m] = hexc("#fff1c9")
        for i in range(6):
            col[(yy > 0.62 + i * 0.05) & (yy < 0.64 + i * 0.05) & m] = hexc("#e9724c")
    elif style == "moons":
        col = np.ones((size, size, 3)) * hexc("#e8e2d6")
        for i in range(5):
            cx = 0.18 + i * 0.16
            m = (xx - cx) ** 2 + (yy - 0.45) ** 2 < 0.0049
            k = (xx - cx - 0.03 * (i - 2)) ** 2 + (yy - 0.45) ** 2 < 0.0049
            col[m & ~k] = hexc("#23395b")
    else:
        col = np.ones((size, size, 3)) * hexc("#556b2f")
        for i in range(14):
            m = (xx > i / 14) & (xx < i / 14 + 0.035)
            col[m] = hexc(["#f4d35e", "#ee964b", "#f95738", "#faf0ca"][i % 4])
    paper = fbm(size, 64, 2, rng)
    col = np.clip(col * (0.94 + 0.08 * paper)[..., None], 0, 1)
    img = to_img(col)
    d = ImageDraw.Draw(img)
    try:
        dark = np.mean(col[int(size * 0.04):int(size * 0.16), int(size * 0.05):int(size * 0.8)]) < 0.45
        ink = (240, 236, 226) if dark else (25, 25, 30)
        f = ImageFont.truetype(FONT_DIR + "InterDisplay-Bold.otf", size // 11)
        f2 = ImageFont.truetype(FONT_DIR + "Inter-Medium.otf", size // 22)
        d.text((size * 0.07, size * 0.06), title.upper(), fill=ink, font=f)
        d.text((size * 0.07, size * 0.88), artist, fill=ink, font=f2)
    except OSError:
        pass
    return np.asarray(img) / 255.0


# ----------------------------------------------------------- misc ----------
def ceramic(size, rng, c0="#e9e4da", c1="#cfc6b6", speck="#5b4a3a"):
    n = fbm(size, 6, 4, rng)
    sp = fbm(size, 200, 1, rng) > 0.86
    col = ramp(n, [(0, c1), (1, c0)])
    col[sp] = col[sp] * 0.4 + hexc(speck) * 0.6
    return col, 0.25 + 0.1 * n, n * 0.3 + sp * 0.4


def brushed(size, rng, c=(0.8, 0.8, 0.8)):
    s = fbm(size, 4, 6, rng, aniso=(0.02, 8))
    col = np.ones((size, size, 3)) * np.array(c) * (0.9 + 0.1 * s)[..., None]
    return col, 0.25 + 0.12 * s, s


def leaf(size, rng):
    yy, xx = (np.mgrid[0:size, 0:size] + 0.5) / size
    veins = np.exp(-((xx - 0.5) / 0.008) ** 2) + 0.5 * np.exp(-((np.abs(((yy + np.abs(xx - 0.5)) * 8) % 1 - 0.5)) / 0.03) ** 2)
    n = fbm(size, 8, 4, rng)
    col = ramp(n * 0.7 + 0.3 * yy, [(0, "#24481f"), (0.5, "#356b2b"), (1, "#4f8a3a")])
    col = lerp(col, hexc("#8fb36a"), np.clip(veins, 0, 1) * 0.6)
    return col, 0.45 + 0.1 * n, veins
