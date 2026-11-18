"""2D inspiration image for the simple version. usage: python simple_inspo.py <outdir>"""
import os
import sys
from PIL import Image, ImageDraw, ImageFont

OUT = sys.argv[1]
T = os.path.join(OUT, "textures")
F = "/usr/share/fonts/truetype/dejavu/"
img = Image.new("RGB", (1920, 1080), (246, 243, 237))
d = ImageDraw.Draw(img)
H1 = ImageFont.truetype(F + "DejaVuSans-Bold.ttf", 56)
H2 = ImageFont.truetype(F + "DejaVuSans-Bold.ttf", 28)
f = ImageFont.truetype(F + "DejaVuSans.ttf", 22)
fs = ImageFont.truetype(F + "DejaVuSans.ttf", 19)
INK = (40, 40, 40)

d.text((60, 40), "Inšpirácia – obývačka", font=H1, fill=INK)
d.text((62, 112), "4SA1 · Interiér · Claude · v01", font=f, fill=(120, 110, 100))
d.line((60, 150, 1860, 150), fill=(205, 195, 180), width=3)

# materials / colours
d.text((60, 180), "Materiály a farby", font=H2, fill=INK)
tiles = [("wood_floor_color.jpg", "drevená podlaha"), ("oak_color.jpg", "dub – stolík, komoda")]
for i, (fn, lab) in enumerate(tiles):
    im = Image.open(os.path.join(T, fn)).convert("RGB")
    im = im.crop((0, 0, min(im.size), min(im.size))).resize((240, 240))
    x = 60 + i * 270
    img.paste(im, (x, 230))
    d.rectangle((x, 230, x + 240, 470), outline=(90, 90, 90), width=2)
    d.text((x, 480), lab, font=f, fill=INK)
cols = [((92, 107, 84), "šalviová – pohovka"), ((140, 64, 38), "terakota – kreslo"),
        ((26, 51, 38), "zelená – dvierka"), ((199, 140, 38), "horčicová – vankúš"),
        ((204, 189, 163), "béžové steny"), ((15, 15, 17), "čierny televízor")]
for i, (c, lab) in enumerate(cols):
    x, y = 60 + (i % 2) * 270, 540 + (i // 2) * 150
    d.rectangle((x, y, x + 110, y + 110), fill=c, outline=(90, 90, 90), width=2)
    d.text((x + 122, y + 40), lab.split(" – ")[0], font=f, fill=INK)
    if " – " in lab:
        d.text((x + 122, y + 68), lab.split(" – ")[1], font=fs, fill=(110, 100, 90))

# plan
d.text((640, 180), "Pôdorys (4,5 × 4 m)", font=H2, fill=INK)
ox, oy, s = 640, 240, 160
RW, RD = 4.5, 4.0


def P(x, y):
    return ox + x * s, oy + (RD - y) * s


d.rectangle((*P(0, RD), *P(RW, 0)), fill=(226, 205, 172), outline=INK, width=6)
d.line((*P(0, 1.5), *P(0, 2.8)), fill=(110, 170, 220), width=12)
d.text((P(0.12, 2.25)[0], P(0.12, 2.25)[1] - 12), "okno", font=fs, fill=(60, 110, 160))


def rect(x0, y0, x1, y1, c, lab):
    d.rectangle((*P(x0, y1), *P(x1, y0)), fill=c, outline=INK, width=2)
    cx, cy = P((x0 + x1) / 2, (y0 + y1) / 2)
    d.text((cx - d.textlength(lab, font=fs) / 2, cy - 11), lab, font=fs, fill=(250, 250, 250) if sum(c) < 300 else INK)


rect(1.3, 3.54, 2.7, 3.94, (60, 95, 75), "komoda")
rect(1.37, 3.9, 2.63, 3.99, (15, 15, 17), "")
d.text((P(2.75, 3.97)[0], P(2.75, 3.97)[1] - 2), "TV na stene", font=fs, fill=INK)
rect(1.5, 2.12, 2.5, 2.68, (190, 150, 105), "stolík")
rect(1.0, 0.7, 3.0, 1.6, (100, 115, 92), "pohovka")
rect(3.33, 2.03, 4.17, 2.87, (150, 72, 45), "kreslo")
cam = P(4.35, 0.15)
d.polygon([(cam[0], cam[1]), (cam[0] - 26, cam[1] - 6), (cam[0] - 8, cam[1] - 26)], fill=(200, 60, 40))
d.text((cam[0] - 110, cam[1] - 30), "kamera", font=fs, fill=(200, 60, 40))

# idea
d.text((1440, 180), "Nápad", font=H2, fill=INK)
lines = ["Jednoduchá obývačka", "na sedenie a TV.", "", "• pohovka oproti televízoru",
         "• kreslo pri stolíku", "• komoda pod televízorom", "• okno na ľavej stene",
         "• na stolíku hrnček a kniha,", "  vankúš na pohovke,", "  platňa pri komode",
         "", "Svetlé steny, drevo,", "zelená a terakota."]
for i, t in enumerate(lines):
    d.text((1440, 236 + i * 36), t, font=f, fill=INK)

path = os.path.join(OUT, "4SA1_Claude_Interier_v01.jpg")
img.save(path, quality=92)
print("saved", path)
