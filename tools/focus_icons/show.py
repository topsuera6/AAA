"""Предпросмотр иконок на фоне дерева фокусов: крупно (3x) и в игровом масштабе с плашкой.
python tools/focus_icons/show.py имя1 имя2 -l "Название 1" "Название 2" -o out.png"""
import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

TOOL = Path(__file__).resolve().parent
ap = argparse.ArgumentParser()
ap.add_argument("names", nargs="+")
ap.add_argument("-o", "--out", default=str(TOOL / "preview.png"))
ap.add_argument("-l", "--labels", nargs="*", default=[])
a = ap.parse_args()

imgs = [Image.open(TOOL / "png" / f"{n}.png").convert("RGBA") for n in a.names]
w, h = imgs[0].size
Z, PLATE = 3, 150
cell_w = w * Z + PLATE + 50
sheet = Image.new("RGBA", (cell_w * len(imgs), h * Z + 16), (14, 16, 15, 255))
d = ImageDraw.Draw(sheet)
font = ImageFont.truetype("DejaVuSans.ttf", 10)
for i, img in enumerate(imgs):
    x0 = i * cell_w + 8
    sheet.alpha_composite(img.resize((w * Z, h * Z), Image.LANCZOS), (x0, 8))
    # игровой масштаб: иконка над плашкой с названием, чуть её перекрывая
    px, py = x0 + w * Z + 20, 8 + (h * Z - h - 22) // 2
    d.rectangle((px, py + h - 8, px + PLATE, py + h + 14), fill=(38, 36, 34), outline=(150, 40, 40))
    sheet.alpha_composite(img, (px + PLATE // 2 - w // 2, py))
    label = a.labels[i] if i < len(a.labels) else a.names[i]
    d.text((px + PLATE // 2, py + h + 3), label, font=font, fill=(230, 225, 215), anchor="mm")
sheet.save(a.out)
