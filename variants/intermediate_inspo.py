"""Mood board (2D inspiration image) for the intermediate version.

usage: python intermediate_inspo.py <outdir>      (reads <outdir>/textures)
"""
import os
import sys
from PIL import Image, ImageDraw, ImageFont

OUT = sys.argv[1]
T = os.path.join(OUT, "textures")
F = "/usr/share/fonts/truetype/dejavu/"
W, H = 1920, 1080
BG = (245, 241, 234)
INK = (40, 40, 40)
img = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(img)
f_title = ImageFont.truetype(F + "DejaVuSans-Bold.ttf", 56)
f_h = ImageFont.truetype(F + "DejaVuSans-Bold.ttf", 28)
f = ImageFont.truetype(F + "DejaVuSans.ttf", 22)
f_s = ImageFont.truetype(F + "DejaVuSans.ttf", 19)

d.text((60, 40), "Moodboard – obývačka s gramofónom", font=f_title, fill=INK)
d.text((62, 112), "4SA1 · Interiér · Claude · v01", font=f, fill=(120, 110, 100))
d.line((60, 150, W - 60, 150), fill=(200, 190, 175), width=3)

# materials 2x3
d.text((60, 180), "Materiály", font=f_h, fill=INK)
sw = [("wood_floor_color.jpg", "drevená podlaha"), ("oak_color.jpg", "dub – nábytok"),
      ("fabric_sofa_color.jpg", "látka – pohovka"), ("fabric_chair_color.jpg", "látka – kreslo"),
      ("rug_color.jpg", "koberec"), ("linen_color.jpg", "ľan – závesy")]
for i, (fn, lab) in enumerate(sw):
    x, y = 60 + (i % 3) * 250, 230 + (i // 3) * 290
    im = Image.open(os.path.join(T, fn)).convert("RGB")
    s = min(im.size)
    im = im.crop((0, 0, s, s)).resize((220, 220))
    img.paste(im, (x, y))
    d.rectangle((x, y, x + 220, y + 220), outline=(90, 90, 90), width=2)
    d.text((x, y + 230), lab, font=f, fill=INK)

# palette
px = 860
d.text((px, 180), "Farby", font=f_h, fill=INK)
pal = [((95, 110, 87), "šalviová"), ((156, 74, 44), "terakota"), ((201, 149, 46), "horčicová"),
       ((180, 140, 95), "dub"), ((204, 189, 163), "béžové steny"), ((26, 51, 38), "tmavozelená"),
       ((20, 20, 20), "čierny kov")]
for i, (c, lab) in enumerate(pal):
    x = px + i * 140
    d.ellipse((x, 230, x + 110, 340), fill=c, outline=(90, 90, 90), width=2)
    d.text((x + 55 - d.textlength(lab, font=f_s) / 2, 350), lab, font=f_s, fill=INK)

# plan
d.text((px, 420), "Pôdorys (5 × 4,5 m)", font=f_h, fill=INK)
ox, oy, s = px, 470, 100
d.rectangle((ox, oy, ox + 5 * s, oy + 4.5 * s), fill=(232, 214, 186), outline=INK, width=5)
d.line((ox, oy + (4.5 - 3.0) * s, ox, oy + (4.5 - 1.6) * s), fill=(110, 170, 220), width=9)


def r(x0, y0, x1, y1, col, lab):
    d.rectangle((ox + x0 * s, oy + (4.5 - y1) * s, ox + x1 * s, oy + (4.5 - y0) * s), fill=col, outline=INK, width=2)
    d.text((ox + (x0 + x1) / 2 * s - d.textlength(lab, font=f_s) / 2, oy + (4.5 - (y0 + y1) / 2) * s - 10),
           lab, font=f_s, fill=INK)


r(1.2, 1.9, 3.8, 3.8, (214, 170, 130), "")
r(1.55, 3.58, 3.65, 4.48, (122, 140, 110), "pohovka")
r(2.0, 2.55, 3.1, 3.15, (190, 150, 100), "stolík")
r(0.02, 1.6, 0.47, 3.0, (60, 90, 70), "")
d.text((ox + 0.55 * s, oy + (4.5 - 2.4) * s), "komoda +", font=f_s, fill=INK)
d.text((ox + 0.55 * s, oy + (4.5 - 2.4) * s + 22), "gramofón", font=f_s, fill=INK)
r(0.01, 0.23, 0.33, 1.13, (190, 150, 100), "")
d.text((ox + 0.4 * s, oy + (4.5 - 0.75) * s), "knižnica", font=f_s, fill=INK)
r(3.45, 2.05, 4.25, 2.85, (170, 85, 55), "kreslo")
d.ellipse((ox + 3.8 * s, oy + (4.5 - 4.3) * s, ox + 4.1 * s, oy + (4.5 - 4.0) * s), fill=(240, 230, 200), outline=INK, width=2)
d.text((ox + 4.15 * s, oy + (4.5 - 4.25) * s), "lampa", font=f_s, fill=INK)
d.ellipse((ox + 0.25 * s, oy + (4.5 - 4.3) * s, ox + 0.6 * s, oy + (4.5 - 3.95) * s), fill=(90, 140, 80), outline=INK, width=2)
d.text((ox + 0.05 * s, oy + 4.5 * s + 10), "okno vľavo, kamera spredu sprava", font=f_s, fill=(120, 110, 100))

# notes
nx = 1420
d.text((nx, 420), "Nápad", font=f_h, fill=INK)
notes = ["útulná obývačka na", "počúvanie platní", "", "• gramofón na komode", "  pod oknom",
         "• zelená pohovka, terakotové", "  kreslo, horčicové vankúše", "• drevo + čierny kov",
         "• denné svetlo z okna,", "  večer stojaca lampa", "• plagáty, knihy, rastlina"]
for i, t in enumerate(notes):
    d.text((nx, 470 + i * 34), t, font=f, fill=INK)

# record covers strip
for i, fn in enumerate(["album_1.jpg", "album_2.jpg", "poster_2.jpg"]):
    im = Image.open(os.path.join(T, fn)).convert("RGB").resize((150, 150))
    img.paste(im, (60 + i * 170, 830))
    d.rectangle((60 + i * 170, 830, 210 + i * 170, 980), outline=(90, 90, 90), width=2)
d.text((60, 990), "platne a plagáty na stenu", font=f, fill=INK)

path = os.path.join(OUT, "4SA1_Claude_Interier_v01.jpg")
img.save(path, quality=92)
print("saved", path)
