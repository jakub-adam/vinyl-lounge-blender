"""Textures for the intermediate version -> <outdir>/textures (1k, like downloaded PBR sets).

usage: python intermediate_textures.py <outdir> <advanced_textures_dir>
"""
import os
import sys
import shutil
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from lib import tex as T  # noqa: E402

OUT = os.path.join(sys.argv[1], "textures")
ADV = sys.argv[2]
os.makedirs(OUT, exist_ok=True)


def save(name, col, rough=None, height=None, nstr=2.0, wrap=True):
    T.to_img(col).save(f"{OUT}/{name}_color.jpg", quality=90)
    if rough is not None:
        T.to_img(rough).save(f"{OUT}/{name}_roughness.jpg", quality=90)
    if height is not None:
        T.to_img(T.normal_from_height(height, nstr, wrap)).save(f"{OUT}/{name}_normal.jpg", quality=92)


def planks(size, rng, rows=8):
    """Straight plank floor, 2 planks per row per tile, staggered rows (tileable)."""
    rt, pores, n2 = T.wood_field(size, rng, rings=36, stretch=14)
    yy, xx = np.mgrid[0:size, 0:size]
    rh = size // rows
    row = yy // rh
    off = (rng.random(rows) * size).astype(int)
    L = size // 2
    xs = (xx + off[row]) % size
    pid = row * 2 + xs // L
    tone = rng.random(rows * 2)
    t = 0.5 * rt + 0.3 * n2 + 0.1 * pores + 0.45 * (tone[pid] - 0.5)
    col = T.ramp(np.clip(t * 0.85 + 0.1, 0, 1),
                 [(0, "#6e4a2c"), (0.45, "#9a6d45"), (0.8, "#b98b5d"), (1, "#cfa577")])
    fy = (yy % rh) / rh
    fx = (xs % L) / L
    seam = np.minimum(np.minimum(fy, 1 - fy) * rh, np.minimum(fx, 1 - fx) * L)
    s = np.clip(seam / 2.5, 0, 1)
    col = col * (0.45 + 0.55 * s)[..., None]
    rough = 0.5 + 0.15 * (1 - rt) + 0.25 * (1 - s)
    return col, np.clip(rough, 0, 1), 0.1 * rt + 0.9 * s


r = np.random.default_rng
save("wood_floor", *planks(1024, r(101)), nstr=2.5)
save("oak", *T.wood(1024, T.OAK, r(102), rings=18, rough_base=0.45), nstr=1.2)
save("fabric_sofa", *T.weave(1024, r(103), "#5f6e57", "#76866b", threads=150), nstr=1.5)
save("fabric_chair", *T.weave(1024, r(104), "#9c4a2c", "#b55e3a", threads=150), nstr=1.5)
save("fabric_pillow", *T.weave(512, r(105), "#c9952e", "#dcae4a", threads=80), nstr=1.2)
save("linen", *T.weave(512, r(106), "#e7e0d2", "#f2ece0", threads=110), nstr=0.8)
col, rough, h = T.rug(1024, r(107))
save("rug", col, rough, h, nstr=2.0, wrap=False)
for src, dst in [("poster_col.jpg", "poster_1.jpg"), ("cover3_col.jpg", "poster_2.jpg"),
                 ("cover0_col.jpg", "album_1.jpg"), ("cover1_col.jpg", "album_2.jpg"),
                 ("vinyl0_col.jpg", "record_label.jpg")]:
    shutil.copy(os.path.join(ADV, src), os.path.join(OUT, dst))
print("textures ->", OUT, len(os.listdir(OUT)))
