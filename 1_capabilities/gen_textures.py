"""Generate every texture of the Vinyl Lounge scene into ./textures.

Run:  python gen_textures.py          (plain Python 3.11+ with numpy/scipy/pillow,
                                        or Blender's bundled Python)
Deterministic: every generator gets its own seeded RNG.
"""
import os
import sys
import time
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import tex as T  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "textures")
os.makedirs(OUT, exist_ok=True)


def rng(seed):
    return np.random.default_rng(seed)


def job(name, fn):
    t = time.time()
    fn()
    print(f"  {name:22s} {time.time() - t:5.1f}s", flush=True)


def parquet():
    col, rough, h = T.herringbone(2048, rng(1), n=5)
    T.save_set(OUT, "parquet", col, rough, h, nstrength=3.0)


def woods():
    T.save_set(OUT, "walnut", *T.wood(1024, T.WALNUT, rng(2), rings=14, rough_base=0.38), nstrength=1.5)
    T.save_set(OUT, "oak", *T.wood(1024, T.OAK, rng(3), rings=20, rough_base=0.5), nstrength=1.5)
    # painted wood (window frame / skirting): deep green, subtle brush strokes
    r = rng(4)
    s = T.fbm(512, 3, 5, r, aniso=(0.1, 4))
    col = T.ramp(s, [(0, "#1f3b30"), (1, "#2a4a3c")])
    T.save_set(OUT, "paint_green", col, 0.42 + 0.1 * s, s * 0.4, nstrength=0.6)


def stone_plaster():
    T.save_set(OUT, "marble", *T.marble(1024, rng(5)), nstrength=0.5)
    T.save_set(OUT, "plaster", *T.plaster(1024, rng(6)), nstrength=1.2)
    T.save_set(OUT, "plaster_ceiling",
               *T.plaster(1024, rng(7), c0="#ece6da", c1="#e2dacb", c2="#f3eee5"), nstrength=0.8)


def textiles():
    T.save_set(OUT, "boucle", *T.boucle(1024, rng(8)), nstrength=4.0)
    T.save_set(OUT, "leather", *T.leather(1024, rng(9)), nstrength=1.2)
    col, rough, h = T.rug(2048, rng(10))
    T.save_set(OUT, "rug", col, rough, h, nstrength=2.5, wrap=False)
    T.save_set(OUT, "grill", *T.weave(1024, rng(11)), nstrength=2.0)
    T.save_set(OUT, "cloth_teal", *T.weave(512, rng(12), "#1d4d4f", "#2b6264", threads=96), nstrength=1.0)
    T.save_set(OUT, "cloth_ochre", *T.weave(512, rng(13), "#a8741f", "#c08a2d", threads=96), nstrength=1.0)
    T.save_set(OUT, "cloth_wine", *T.weave(512, rng(14), "#5a1f2a", "#6e2a36", threads=96), nstrength=1.0)


def vinyl():
    labels = [("#d9a441", "SIDE A", "#1e2a44"), ("#c6402f", "SIDE B", "#f4ead5"),
              ("#2f6f7e", "LOW TIDE", "#f2e6d0")]
    for i, (c, txt, acc) in enumerate(labels):
        T.save_set(OUT, f"vinyl{i}", *T.vinyl_disc(1024, rng(20 + i), c, txt, acc),
                   nstrength=0.8, wrap=False)


def covers():
    for i, (title, artist, style) in enumerate(T.COVERS):
        col = T.album_cover(1024, rng(30 + i), title, artist, style)
        T.to_img(col).save(f"{OUT}/cover{i}_col.jpg", quality=92)


def cardboard():
    r = rng(40)
    fib = T.fbm(512, 64, 3, r, aniso=(1, 0.3))
    low = T.fbm(512, 4, 3, r)
    col = T.ramp(0.6 * low + 0.4 * fib, [(0, "#b08a5c"), (1, "#c9a578")])
    T.save_set(OUT, "cardboard", col, 0.85 + 0.1 * fib, fib, nstrength=0.8)
    # inner sleeve paper (white) for the record peeking out
    col = T.ramp(fib, [(0, "#e9e5dc"), (1, "#f6f3ec")])
    T.save_set(OUT, "paper", col, 0.8 + 0.1 * fib, fib, nstrength=0.3)


def ceramics_metals_plants():
    T.save_set(OUT, "ceramic_cream", *T.ceramic(512, rng(50)), nstrength=0.4)
    T.save_set(OUT, "terracotta",
               *T.ceramic(512, rng(51), "#b8643f", "#9c5232", "#6e3a22"), nstrength=0.8)
    col, rough, h = T.brushed(512, rng(52), (0.86, 0.68, 0.38))
    T.save_set(OUT, "brass", col, rough * 0.9, h, nstrength=0.3)
    col, rough, h = T.brushed(512, rng(53), (0.82, 0.83, 0.85))
    T.save_set(OUT, "alu", col, rough, h, nstrength=0.3)
    r = rng(54)
    n = T.fbm(512, 12, 4, r)
    T.save_set(OUT, "blackmetal", T.ramp(n, [(0, "#121214"), (1, "#1c1c1f")]), 0.45 + 0.15 * n, n,
               nstrength=0.3)
    T.save_set(OUT, "leaf", *T.leaf(512, rng(55)), nstrength=0.8, wrap=False)
    n = T.fbm(512, 24, 4, rng(56))
    T.save_set(OUT, "soil", T.ramp(n, [(0, "#1d140d"), (1, "#3b2a1c")]), 0.95 + 0 * n, n, nstrength=2)
    n = T.fbm(256, 8, 3, rng(57))
    T.save_set(OUT, "rubber", T.ramp(n, [(0, "#0d0d0d"), (1, "#1a1a1a")]), 0.75 + 0.1 * n, n, nstrength=0.2)


def poster():
    """Framed print: abstract 'listening session' poster (original artwork)."""
    W, H = 1024, 1365
    r = rng(60)
    yy, xx = (np.mgrid[0:H, 0:W] + 0.5) / np.array([H, W])[:, None, None]
    col = np.ones((H, W, 3)) * T.hexc("#efe6d4")
    # concentric arcs = sound / grooves
    cx, cy = 0.5, 0.58
    rr = np.sqrt(((xx - cx) * W / H) ** 2 + (yy - cy) ** 2)
    for i, c in enumerate(["#a5452a", "#c9952e", "#24324a", "#7f8a6a", "#a5452a"]):
        m = (rr > 0.06 + i * 0.055) & (rr < 0.09 + i * 0.055) & (yy < cy)
        col[m] = T.hexc(c)
    col[(rr < 0.045)] = T.hexc("#24324a")
    col[(yy > cy) & (yy < cy + 0.012) & (np.abs(xx - 0.5) < 0.4)] = T.hexc("#24324a")
    img = T.to_img(col)
    d = ImageDraw.Draw(img)
    f = ImageFont.truetype(T.FONT_DIR + "InterDisplay-Bold.otf", 96)
    f2 = ImageFont.truetype(T.FONT_DIR + "Inter-Medium.otf", 34)
    d.text((W / 2, H * 0.14), "SLOW MUSIC", fill=(36, 50, 74), font=f, anchor="mm")
    d.text((W / 2, H * 0.21), "listening sessions  ·  side a / side b", fill=(165, 69, 42), font=f2, anchor="mm")
    d.text((W / 2, H * 0.86), "VINYL LOUNGE  —  EST. 2026", fill=(36, 50, 74), font=f2, anchor="mm")
    noise = (T.fbm(1024, 96, 2, r)[:, :] - 0.5) * 0.06
    arr = np.asarray(img) / 255.0
    arr = np.clip(arr + np.resize(noise, (H, W))[..., None], 0, 1)
    T.to_img(arr).save(f"{OUT}/poster_col.jpg", quality=92)


def backdrop():
    """Exterior seen through the arched window: late-afternoon sky + tree line."""
    W, H = 2048, 1024
    r = rng(70)
    yy, xx = (np.mgrid[0:H, 0:W] + 0.5) / np.array([H, W])[:, None, None]
    sky = T.ramp(1 - yy, [(0, "#f4c58e"), (0.35, "#f1d7b0"), (0.7, "#b9cbd6"), (1, "#86a7c2")])
    cl = T.fbm(1024, 3, 6, r, aniso=(1, 3))
    cl = np.asarray(Image.fromarray((cl * 255).astype(np.uint8)).resize((W, H))) / 255.0
    clouds = np.clip((cl - 0.55) * 3, 0, 1) * (yy < 0.55)
    sky = T.lerp(sky, T.hexc("#fbefe0"), clouds * 0.7)
    # tree silhouettes: layered 1D noise ridges
    for k, (base, amp, c) in enumerate([(0.62, 0.12, "#6f7f68"), (0.7, 0.1, "#46553f"),
                                        (0.8, 0.07, "#2e3a2a")]):
        n1 = T.fbm(1024, 6 + 4 * k, 5, r)[0]
        n1 = np.interp(np.linspace(0, 1023, W), np.arange(1024), n1)
        ridge = base - amp * n1
        sky[yy > ridge[None, :]] = T.hexc(c)
    T.to_img(sky).save(f"{OUT}/backdrop_col.jpg", quality=92)


if __name__ == "__main__":
    t0 = time.time()
    print("Generating textures ->", OUT)
    for name, fn in [("parquet (herringbone)", parquet), ("woods", woods),
                     ("marble/plaster", stone_plaster), ("textiles+rug", textiles),
                     ("vinyl labels", vinyl), ("album covers", covers),
                     ("cardboard/paper", cardboard), ("ceramic/metal/plant", ceramics_metals_plants),
                     ("poster", poster), ("backdrop", backdrop)]:
        job(name, fn)
    print(f"done in {time.time() - t0:.1f}s, {len(os.listdir(OUT))} files")
