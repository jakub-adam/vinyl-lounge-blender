"""Simple 2D inspiration image (beginner style: plain sketch + colours)."""
import sys
from PIL import Image, ImageDraw, ImageFont
out = sys.argv[1]
F = "/usr/share/fonts/truetype/dejavu/"
img = Image.new("RGB", (1600, 900), "white")
d = ImageDraw.Draw(img)
big = ImageFont.truetype(F + "DejaVuSans-Bold.ttf", 54)
mid = ImageFont.truetype(F + "DejaVuSans.ttf", 30)
small = ImageFont.truetype(F + "DejaVuSans.ttf", 24)
d.text((60, 40), "Inšpirácia - moja izba", font=big, fill="black")
d.text((60, 115), "Interiér 4SA1", font=mid, fill=(90, 90, 90))
# napad / plan zhora
d.text((60, 190), "Plán zhora:", font=mid, fill="black")
ox, oy, s = 80, 250, 140                     # 4 x 4 m izba
d.rectangle((ox, oy, ox + 4 * s, oy + 4 * s), outline="black", width=6)
def r(x0, y0, x1, y1, col, txt):
    d.rectangle((ox + x0 * s, oy + (4 - y1) * s, ox + x1 * s, oy + (4 - y0) * s), fill=col, outline="black", width=3)
    d.text((ox + x0 * s + 8, oy + (4 - y1) * s + 6), txt, font=small, fill="black")
r(0.05, 2.0, 1.05, 4.0, (225, 200, 160), "posteľ")
r(2.3, 3.3, 3.5, 3.9, (210, 170, 120), "stôl")
r(2.68, 2.78, 3.12, 3.22, (160, 110, 70), "")
d.text((ox + 2.5 * s, oy + (4 - 2.7) * s), "stolička", font=small, fill="black")
r(0.05, 0.4, 0.65, 1.6, (240, 240, 240), "skriňa")
d.line((ox + 1.6 * s, oy + 4 * s + 30, ox + 2.6 * s, oy + 4 * s + 30), fill="black", width=3)
d.text((ox + 1.65 * s, oy + 4 * s + 38), "1 m", font=small, fill="black")
# farby
d.text((780, 190), "Farby:", font=mid, fill="black")
cols = [((217, 204, 179), "steny"), ((115, 66, 30), "drevo"), ((235, 235, 230), "biela"),
        ((40, 77, 153), "modrá"), ((153, 20, 20), "červená")]
for i, (c, t) in enumerate(cols):
    x = 780 + i * 150
    d.rectangle((x, 250, x + 120, 370), fill=c, outline="black", width=2)
    d.text((x, 380), t, font=small, fill="black")
d.text((780, 470), "Nápad:", font=mid, fill="black")
lines = ["Jednoduchá izba pre študenta.", "Posteľ, stôl so stoličkou a skriňa.",
         "Svetlé steny a drevená podlaha.", "Na stole notebook a kniha,", "na posteli vankúš, pri posteli krabica."]
for i, t in enumerate(lines):
    d.text((780, 525 + i * 40), "- " + t, font=small, fill="black")
img.save(out, quality=90)
print("saved", out)
