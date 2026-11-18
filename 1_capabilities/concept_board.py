"""concept_board.py - 2D inspiration / concept board (mood board + plan).

    python concept_board.py      -> out/4SA1_Claude_Interier_v01.jpg

Built only from the project's own generated textures and out/layout.json
(written by build_scene.py), so it is fully original.
"""
import os
import json
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.abspath(__file__))
TEX = os.path.join(ROOT, "textures")
OUT = os.path.join(ROOT, "out")
FD = "/usr/share/fonts/opentype/inter/"
W, H = 2480, 1600
PAPER = (239, 233, 222)
INK = (36, 50, 74)
RUST = (165, 69, 42)
MUTED = (110, 104, 96)


def font(name, size):
    return ImageFont.truetype(FD + name, size)


def spaced(d, xy, text, f, fill, spacing=4):
    x, y = xy
    for ch in text:
        d.text((x, y), ch, font=f, fill=fill)
        x += d.textlength(ch, font=f) + spacing


def wrap(d, text, f, width):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if d.textlength(t, font=f) > width and cur:
            lines.append(cur)
            cur = w
        else:
            cur = t
    lines.append(cur)
    return lines


def tex_crop(name, size, zoom=0.5):
    im = Image.open(os.path.join(TEX, name)).convert("RGB")
    w, h = im.size
    cw, ch = int(w * zoom), int(w * zoom * size[1] / size[0])
    x0, y0 = (w - cw) // 2, (h - ch) // 2
    return im.crop((x0, y0, x0 + cw, y0 + ch)).resize(size, Image.LANCZOS)


def mean_hex(name):
    a = np.asarray(Image.open(os.path.join(TEX, name)).convert("RGB").resize((64, 64))) / 255.0
    m = a.reshape(-1, 3).mean(0)
    return tuple(int(v * 255) for v in m)


def shadow_paste(img, tile, xy, r=0):
    sh = Image.new("RGBA", (tile.width + 16, tile.height + 16), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rectangle((8, 10, tile.width + 8, tile.height + 10), fill=(0, 0, 0, 40))
    img.paste(sh, (xy[0] - 8, xy[1] - 8), sh)
    img.paste(tile, xy)


def plan(img, d, layout, ox, oy, s):
    RW, RD, RH = layout["room"]
    WT = 0.2

    def P(x, y):
        return (ox + x * s, oy + (RD - y) * s)

    # floor + border frieze
    d.rectangle((*P(0, RD), *P(RW, 0)), fill=(226, 205, 170))
    b = 0.16
    d.rectangle((*P(b, RD - b), *P(RW - b, b)), fill=(233, 216, 186))
    # herringbone hint
    for k in range(-40, 60):
        x0 = b + k * 0.18
        for j in range(0, int((RD - 2 * b) / 0.18)):
            y = b + j * 0.18
            xa, xb = x0 + (j % 2) * 0.09, x0 + (j % 2) * 0.09 + 0.09
            if b < xa < RW - b and b < y < RD - b:
                d.line((*P(xa, y), *P(min(xb, RW - b), min(y + 0.09, RD - b))), fill=(214, 191, 152), width=1)
    # walls
    wall = (52, 52, 56)
    d.rectangle((*P(-WT, RD + WT), *P(RW + WT, RD)), fill=wall)
    d.rectangle((*P(-WT, 0), *P(RW + WT, -WT)), fill=wall)
    d.rectangle((*P(RW, RD), *P(RW + WT, 0)), fill=wall)
    wy, ww = layout["window"]["y"], layout["window"]["w"]
    d.rectangle((*P(-WT, RD), *P(0, wy + ww / 2)), fill=wall)
    d.rectangle((*P(-WT, wy - ww / 2), *P(0, 0)), fill=wall)
    # window: glazing lines + light wedge
    for xx in (-0.13, -0.07):
        d.line((*P(xx, wy - ww / 2), *P(xx, wy + ww / 2)), fill=(90, 140, 170), width=3)
    sun = Image.new("RGBA", img.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(sun)
    sd.polygon([P(0, wy - ww / 2), P(0, wy + ww / 2), P(3.3, wy + ww / 2 + 0.33), P(3.3, wy - ww / 2 + 0.33)],
               fill=(255, 214, 120, 70))
    img.paste(Image.alpha_composite(img.convert("RGBA"), sun).convert("RGB"))
    round_names = ("CoffeeTable", "SideTable", "Pouf", "Plant", "ArcLamp", "Cactus", "Mug")
    fills = {"FURN": (196, 120, 86), "GRAB": (36, 50, 74)}
    f_small = font("Inter-Medium.otf", 19)
    labels = []
    objs = sorted(layout["objects"], key=lambda o: (o["name"] != "FURN_Rug", o["name"].startswith("GRAB_")))
    for ob in objs:
        n = ob["name"]
        if not n.startswith(("FURN_", "GRAB_")) or n in ("FURN_Poster",):
            continue
        kind = n.split("_")[0]
        col = fills[kind]
        if n == "FURN_Rug":
            pts = [P(*c) for c in ob["footprint"]]
            d.polygon(pts, fill=(205, 160, 120), outline=(150, 70, 45))
            d.polygon([P(1.95 - 0.9, 2.55), P(1.95, 2.55 + 0.9), P(1.95 + 0.9, 2.55), P(1.95, 2.55 - 0.9)],
                      outline=(36, 50, 74), width=3)
            continue
        if any(r in n for r in round_names):
            x0, y0, _, x1, y1, _ = ob["bbox"]
            if n == "FURN_ArcLamp":
                cx, cy, rr = 0.42, 4.0, 0.17
                sx_, sy_ = 0.42 + 1.45 * math.sin(math.radians(45.7)), 4.0 - 1.45 * math.cos(math.radians(45.7))
                d.line((*P(cx, cy), *P(sx_, sy_)), fill=(150, 120, 60), width=4)
                d.ellipse((*P(sx_ - 0.2, sy_ + 0.2), *P(sx_ + 0.2, sy_ - 0.2)), outline=(150, 120, 60), width=3)
                d.ellipse((*P(cx - rr, cy + rr), *P(cx + rr, cy - rr)), fill=(200, 170, 90), outline=(120, 90, 40), width=2)
                continue
            if "Plant" in n:
                cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
                for k in range(9):
                    a = k * 2 * math.pi / 9
                    lx, ly = cx + 0.28 * math.cos(a), cy + 0.28 * math.sin(a)
                    d.ellipse((*P(lx - 0.13, ly + 0.13), *P(lx + 0.13, ly - 0.13)), fill=(96, 140, 90))
                d.ellipse((*P(cx - 0.2, cy + 0.2), *P(cx + 0.2, cy - 0.2)), fill=(184, 100, 63) if n == "FURN_Plant" else (230, 225, 214), outline=(90, 60, 40))
                continue
            d.ellipse((*P(x0, y1), *P(x1, y0)), fill=col if kind == "FURN" else (230, 222, 205),
                      outline=(60, 40, 30), width=3)
        else:
            pts = [P(*c) for c in ob["footprint"]]
            if kind == "GRAB":
                d.polygon(pts, fill=(250, 246, 238), outline=INK, width=2)
            else:
                d.polygon(pts, fill=col, outline=(60, 40, 30), width=3)
    # camera
    cam = (5.0, -0.75)
    d.line((*P(*cam), *P(0.0, 0.6)), fill=(170, 160, 150), width=1)
    d.line((*P(*cam), *P(5.55, 5.2)), fill=(170, 160, 150), width=1)
    d.ellipse((*P(cam[0] - 0.1, cam[1] + 0.1), *P(cam[0] + 0.1, cam[1] - 0.1)), fill=RUST)
    d.text((P(*cam)[0] + 20, P(*cam)[1] - 14), "kamera", font=f_small, fill=RUST)
    # labels
    lab = [("pohovka", 0.54, 2.55), ("konferenčný\nstolík", 1.85, 2.0), ("kreslo", 3.45, 3.55),
           ("komoda + gramofón", 3.3, 4.62), ("reproduktory", 1.6, 4.62), ("regál\nna platne", 5.55, 4.45),
           ("taburet", 4.05, 2.15), ("debnička\ns platňami", 5.0, 3.3), ("koberec", 1.95, 1.25),
           ("oblúkové okno", 0.62, 1.2), ("lampa", 0.95, 4.02), ("rastlina", 0.45, 4.42)]
    for t, x, y in lab:
        px, py = P(x, y)
        for i, line in enumerate(t.split("\n")):
            w_ = d.textlength(line, font=f_small)
            d.text((px - w_ / 2 + 1, py - 10 + i * 22 + 1), line, font=f_small, fill=(250, 246, 238))
            d.text((px - w_ / 2, py - 10 + i * 22), line, font=f_small, fill=INK)
    # scale bar
    sx, sy = P(0, -0.55)
    for i in range(3):
        d.rectangle((sx + i * s, sy, sx + (i + 1) * s, sy + 10), fill=INK if i % 2 == 0 else PAPER, outline=INK)
    d.text((sx + 3 * s + 14, sy - 8), "3 m", font=f_small, fill=INK)
    d.text((sx, sy + 18), "PÔDORYS  ·  6,0 × 5,2 m, svetlá výška 3,0 m", font=f_small, fill=MUTED)


def main():
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    # header
    spaced(d, (90, 70), "4SA1  ·  INTERIÉR  ·  KONCEPT / INŠPIRÁCIA  ·  v01", font("Inter-SemiBold.otf", 26), RUST, 5)
    d.text((84, 108), "VINYL LOUNGE", font=font("InterDisplay-Bold.otf", 150), fill=INK)
    f_sub = font("Inter-Regular.otf", 33)
    sub = ("Miestnosť na počúvanie platní: teplé drevo, bouclé a mosadz, nízke popoludňajšie slnko "
           "cez oblúkové okno a analógový rituál pri gramofóne.")
    for i, line in enumerate(wrap(d, sub, f_sub, 1060)):
        d.text((90, 290 + i * 44), line, font=f_sub, fill=MUTED)
    # plan
    with open(os.path.join(OUT, "layout.json")) as f:
        layout = json.load(f)
    plan(img, d, layout, 140, 470, 160)

    # right column
    X0 = 1290
    f_h = font("Inter-SemiBold.otf", 26)
    f_l = font("Inter-Medium.otf", 22)
    f_t = font("Inter-Regular.otf", 24)
    spaced(d, (X0, 76), "MATERIÁLY", f_h, INK, 4)
    sw = [("parquet_col.jpg", "Parkety – rybia kosť, dub", 0.5), ("walnut_col.jpg", "Orech – komoda, rám", 0.6),
          ("oak_col.jpg", "Dub – akustické lamely", 0.6), ("marble_col.jpg", "Mramor – stolík, parapet", 0.8),
          ("boucle_col.jpg", "Bouclé – pohovka", 0.35), ("leather_col.jpg", "Koža koňak – kreslo", 0.5),
          ("plaster_col.jpg", "Vápenná omietka – steny", 0.9), ("rug_col.jpg", "Ručne viazaný koberec", 1.0)]
    tw, th = 255, 190
    for i, (fn, label, z) in enumerate(sw):
        cx = X0 + (i % 4) * (tw + 30)
        cy = 124 + (i // 4) * (th + 70)
        shadow_paste(img, tex_crop(fn, (tw, th), z), (cx, cy))
        d.text((cx, cy + th + 12), label, font=f_l, fill=INK)

    # palette
    py = 670
    spaced(d, (X0, py), "FAREBNÁ PALETA", f_h, INK, 4)
    pal = [("Orech", mean_hex("walnut_col.jpg")), ("Bouclé", mean_hex("boucle_col.jpg")),
           ("Koňak", mean_hex("leather_col.jpg")), ("Mosadz", (201, 160, 92)),
           ("Petrolej", (29, 77, 79)), ("Okr", (201, 149, 46)), ("Lesná zelená", (31, 59, 48)),
           ("Omietka", mean_hex("plaster_col.jpg"))]
    for i, (name, c) in enumerate(pal):
        x = X0 + i * 136
        d.rounded_rectangle((x, py + 48, x + 118, py + 166), 14, fill=c)
        d.text((x, py + 176), name, font=font("Inter-Medium.otf", 18), fill=INK)
        d.text((x, py + 199), "#%02X%02X%02X" % c, font=font("Inter-Regular.otf", 17), fill=MUTED)

    # mood: record covers + poster
    my = 920
    spaced(d, (X0, my), "NÁLADA – PLATNE NA STENE A V REGÁLI", f_h, INK, 4)
    for i in range(6):
        cv = Image.open(os.path.join(TEX, f"cover{i}_col.jpg")).convert("RGB").resize((150, 150), Image.LANCZOS)
        shadow_paste(img, cv, (X0 + i * 172, my + 50))
    vin = Image.open(os.path.join(TEX, "vinyl0_col.jpg")).convert("RGB").resize((150, 150))
    mask = Image.new("L", (150, 150), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, 149, 149), fill=255)
    img.paste(vin, (X0 + 6 * 172 - 40, my + 50), mask)

    # notes
    ny = 1150
    spaced(d, (X0, ny), "KONCEPT", f_h, INK, 4)
    notes = [
        "Svetlo: nízke slnko cez oblúkové okno kreslí na koberec tvar okna; večer teplá oblúková lampa nad stolíkom.",
        "Zvuk: orechová komoda s gramofónom, regálové reproduktory na stojanoch, dubové lamely na filci tlmia ozvenu.",
        "Sedenie: bouclé pohovka pod oknom, kožené kreslo natočené k stolíku, taburet ako podnožka.",
        "Uchopiteľné predmety: gramofón, platne, debnička s platňami, hrnček, slúchadlá, knihy, kaktus.",
        "Technika: procedurálne quad modely + numpy textúry, Principled BSDF, Cycles, export glTF (+Y up).",
    ]
    yy = ny + 46
    for t in notes:
        lines = wrap(d, t, f_t, 1080)
        d.ellipse((X0, yy + 11, X0 + 9, yy + 20), fill=RUST)
        for j, line in enumerate(lines):
            d.text((X0 + 24, yy + j * 32), line, font=f_t, fill=INK)
        yy += len(lines) * 32 + 14

    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, "4SA1_Claude_Interier_v01.jpg")
    img.save(path, quality=93)
    print("saved", path)


if __name__ == "__main__":
    main()
