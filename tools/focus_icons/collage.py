"""Инструменты для коллажных иконок фокусов (в стиле Millennium Dawn / TNO).

Иконка собирается слоями на холсте с запасом по разрешению (SS раз больше
итогового), а в конце уменьшается, обводится и сохраняется в DDS:

    c = Canvas()
    c.add(rays(c.size, "#c41e1e"))
    c.add(country_map(["Russia"], c.size, fill="#b01818"), fade=0.3)
    c.add(waving_flag(soviet_flag(), c.size), at=(0.62, 0.2), scale=0.5)
    c.add(cutout("photos/zyuganov.jpg"), at=(0.5, 0.95), scale=0.8, anchor="bottom")
    c.save("victory_in_elections")

Координаты `at` — доли холста (0..1), `scale` — доля высоты холста.
"""

import io
import json
import math
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageOps

ROOT = Path(__file__).resolve().parents[2]
TOOL_DIR = Path(__file__).resolve().parent
DATA = TOOL_DIR / "data"
CACHE = TOOL_DIR / ".cache"

ICON_W, ICON_H = 94, 86     # итоговый размер; меняется через Canvas(size=...)
SS = 4                      # суперсэмплинг
PREFIX = "GFX_focus_nh_"
DDS_DIR = "gfx/interface/goals/nh"


# ---------------------------------------------------------------- цвета --
def rgb(c):
    if isinstance(c, str):
        c = c.lstrip("#")
        return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))
    return tuple(c[:3])


PALETTES = {
    # тёмный, средний, светлый — для duotone/tritone
    "red":  ("#1a0505", "#a3141a", "#ffd9c2"),
    "teal": ("#031417", "#12848c", "#d6fbff"),
    "gold": ("#1a1204", "#a8761c", "#fff1c4"),
    "blue": ("#050b1a", "#2a58a8", "#dfe9ff"),
    "grey": ("#101010", "#707070", "#f0f0f0"),
}


def tone(img, palette="red", strength=1.0, keep=("#b3312c",)):
    """Перекрашивает картинку в градиент палитры по яркости (как на примерах).
    strength=1 — полностью в тоне, 0.5 — наполовину сохраняет исходные цвета."""
    dark, mid, light = (rgb(c) for c in (PALETTES[palette] if isinstance(palette, str) else palette))
    arr = np.asarray(img.convert("RGBA")).astype(np.float32)
    lum = (arr[..., 0] * 0.3 + arr[..., 1] * 0.59 + arr[..., 2] * 0.11) / 255
    lum = np.clip((lum - 0.04) / 0.92, 0, 1)[..., None]
    d, m, l = (np.array(x, np.float32) for x in (dark, mid, light))
    toned = np.where(lum < 0.5, d + (m - d) * (lum * 2), m + (l - m) * (lum * 2 - 1))
    arr[..., :3] = arr[..., :3] * (1 - strength) + toned * strength
    return Image.fromarray(arr.clip(0, 255).astype(np.uint8), "RGBA")


def adjust(img, contrast=1.0, brightness=1.0, saturation=1.0):
    a = img.getchannel("A")
    rgb_img = img.convert("RGB")
    rgb_img = ImageEnhance.Contrast(rgb_img).enhance(contrast)
    rgb_img = ImageEnhance.Brightness(rgb_img).enhance(brightness)
    rgb_img = ImageEnhance.Color(rgb_img).enhance(saturation)
    rgb_img.putalpha(a)
    return rgb_img


# ------------------------------------------------------------ вырезание --
@lru_cache(maxsize=1)
def _rembg_session(model):
    from rembg import new_session
    return new_session(model)


def cutout(path, model="isnet-general-use", crop=None, refine=True):
    """Вырезает объект/человека с фото. Результат кэшируется в .cache/.
    crop=(x0, y0, x1, y1) в долях — обрезать исходник до вырезания."""
    path = Path(path)
    src = Image.open(path).convert("RGBA")
    if crop:
        w, h = src.size
        src = src.crop((int(crop[0] * w), int(crop[1] * h), int(crop[2] * w), int(crop[3] * h)))
    CACHE.mkdir(exist_ok=True)
    key = CACHE / f"{path.stem}_{model}_{'_'.join(map(str, crop or ()))}.png"
    if key.exists():
        return Image.open(key).convert("RGBA")
    from rembg import remove
    out = remove(src, session=_rembg_session(model), post_process_mask=refine)
    out = out.crop(out.getbbox())
    out.save(key)
    return out


def fit(img, height):
    w, h = img.size
    return img.resize((max(1, round(w * height / h)), round(height)), Image.LANCZOS)


# ------------------------------------------------------------------ карты --
@lru_cache(maxsize=1)
def _countries():
    with open(DATA / "countries.geojson", encoding="utf-8") as f:
        feats = json.load(f)["features"]
    return {ft["properties"]["name"]: ft["geometry"] for ft in feats}


def _lcc(lon, lat, lon0, lat1=52, lat2=64, lat0=58):
    """Коническая проекция Ламберта — Россия выглядит «как на картах»."""
    p = math.pi / 180
    n = math.log(math.cos(lat1 * p) / math.cos(lat2 * p)) / math.log(
        math.tan((90 + lat2) / 2 * p) / math.tan((90 + lat1) / 2 * p))
    F = math.cos(lat1 * p) * math.tan((45 + lat1 / 2) * p) ** n / n
    rho = F / math.tan((45 + lat / 2) * p) ** n
    rho0 = F / math.tan((45 + lat0 / 2) * p) ** n
    th = n * (lon - lon0) * p
    return rho * math.sin(th), rho0 - rho * math.cos(th)


def country_map(names, size, fill="#b01818", edge="#2a0000", lon0=None,
                box=(0.02, 0.02, 0.98, 0.98), min_area=0.0003, highlight=None):
    """Силуэт одной или нескольких стран, вписанный в box (доли холста).
    highlight={"Belarus": "#e0c040"} — перекрасить отдельные страны."""
    geoms = _countries()
    polys = []
    for name in names:
        g = geoms[name]
        rings = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        for poly in rings:
            ring = [(lon + 360 if lon < -30 and name == "Russia" else lon, lat) for lon, lat in poly[0]]
            polys.append((name, ring))
    lons = [lon for _, r in polys for lon, _ in r]
    lon0 = lon0 if lon0 is not None else (min(lons) + max(lons)) / 2
    proj = [(n, [_lcc(lo, la, lon0) for lo, la in r]) for n, r in polys]
    xs = [x for _, r in proj for x, _ in r]
    ys = [y for _, r in proj for _, y in r]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    W, H = size
    bw, bh = (box[2] - box[0]) * W, (box[3] - box[1]) * H
    k = min(bw / (x1 - x0), bh / (y1 - y0))
    ox = box[0] * W + (bw - (x1 - x0) * k) / 2
    oy = box[1] * H + (bh - (y1 - y0) * k) / 2
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    total = (x1 - x0) * (y1 - y0)
    for name, r in proj:
        pts = [(ox + (x - x0) * k, oy + (y1 - y) * k) for x, y in r]
        rx = [p[0] for p in pts]
        ry = [p[1] for p in pts]
        if (max(rx) - min(rx)) * (max(ry) - min(ry)) / (k * k) < total * min_area:
            continue                                    # мелкие острова только шумят
        colour = (highlight or {}).get(name, fill)
        d.polygon(pts, fill=rgb(colour) + (255,), outline=rgb(edge) + (255,),
                  width=max(1, W // 300))
    return img


# -------------------------------------------------------- флаги и символы --
def stripes_flag(colours, w=300, h=200, vertical=False):
    img = Image.new("RGBA", (w, h))
    d = ImageDraw.Draw(img)
    n = len(colours)
    for i, c in enumerate(colours):
        if vertical:
            d.rectangle((i * w / n, 0, (i + 1) * w / n, h), fill=rgb(c))
        else:
            d.rectangle((0, i * h / n, w, (i + 1) * h / n), fill=rgb(c))
    return img


def hammer_sickle(size=200, colour="#f2c230"):
    """Серп и молот, нарисованные примитивами (без внешних картинок)."""
    s = size * SS
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = rgb(colour) + (255,)
    # серп: полумесяц = большой круг минус смещённый круг
    blade = Image.new("L", (s, s), 0)
    bd = ImageDraw.Draw(blade)
    bd.ellipse((0.14 * s, 0.10 * s, 0.86 * s, 0.82 * s), fill=255)
    bd.ellipse((0.20 * s, 0.02 * s, 0.84 * s, 0.70 * s), fill=0)
    bd.rectangle((0, 0, 0.5 * s, 0.45 * s), fill=0)        # остриё только справа сверху
    img.paste(Image.new("RGBA", (s, s), c), (0, 0), blade)
    d.line((0.26 * s, 0.70 * s, 0.10 * s, 0.90 * s), fill=c, width=int(0.07 * s))
    # молот
    ham = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    hd = ImageDraw.Draw(ham)
    hd.rectangle((0.47 * s, 0.22 * s, 0.53 * s, 0.95 * s), fill=c)
    hd.rectangle((0.33 * s, 0.14 * s, 0.67 * s, 0.30 * s), fill=c)
    ham = ham.rotate(45, center=(0.5 * s, 0.55 * s), resample=Image.BICUBIC)
    img.alpha_composite(ham)
    return img.resize((size, size), Image.LANCZOS)


def star(size=100, colour="#f2c230", points=5, inner=0.4):
    s = size * SS
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    pts = []
    for i in range(points * 2):
        r = s / 2 if i % 2 == 0 else s / 2 * inner
        a = -math.pi / 2 + i * math.pi / points
        pts.append((s / 2 + r * math.cos(a), s / 2 + r * math.sin(a)))
    ImageDraw.Draw(img).polygon(pts, fill=rgb(colour) + (255,))
    return img.resize((size, size), Image.LANCZOS)


def soviet_flag(w=300, h=150):
    img = Image.new("RGBA", (w, h), rgb("#cc0000") + (255,))
    img.alpha_composite(hammer_sickle(int(h * 0.36)), (int(h * 0.12), int(h * 0.2)))
    st = star(int(h * 0.15), inner=0.38)
    img.alpha_composite(st, (int(h * 0.12 + h * 0.36 / 2 - h * 0.075 + h * 0.04), int(h * 0.04)))
    return img


def waving_flag(flag, pole=True, waves=1.4, amp=0.07, shade=0.45, pole_colour="#6b4b2a"):
    """Натягивает прямоугольный флаг на волну и затеняет складки."""
    f = np.asarray(flag.convert("RGBA")).astype(np.float32)
    h, w = f.shape[:2]
    A = amp * h
    pad = int(A * 2) + 2
    out = np.zeros((h + pad * 2, w, 4), np.float32)
    for x in range(w):
        t = x / w
        ph = 2 * math.pi * waves * t
        dy = A * math.sin(ph) * (0.3 + 0.7 * t)             # у древка волна меньше
        light = 1 + shade * math.cos(ph) * (0.3 + 0.7 * t) * 0.6
        y0 = pad + int(round(dy))
        col = f[:, x].copy()
        col[:, :3] *= light
        out[y0:y0 + h, x] = col
    img = Image.fromarray(out.clip(0, 255).astype(np.uint8), "RGBA")
    if pole:
        pw = max(4, w // 40)
        canvas = Image.new("RGBA", (w + pw, int(h * 2.2) + pad), (0, 0, 0, 0))
        d = ImageDraw.Draw(canvas)
        d.rectangle((0, pad // 2, pw, canvas.height), fill=rgb(pole_colour) + (255,))
        d.ellipse((-pw * 0.4, pad // 2 - pw, pw * 1.4, pad // 2 + pw), fill=rgb("#d8b24a") + (255,))
        canvas.alpha_composite(img, (pw, 0))
        img = canvas
    return img


def rays(size, colour="#c41e1e", n=18, centre=(0.5, 0.55), alpha=200, fade=True):
    """Солнечные лучи из центра, как на агитплакатах."""
    W, H = size
    cx, cy = centre[0] * W, centre[1] * H
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    R = math.hypot(W, H)
    for i in range(n):
        a0 = 2 * math.pi * i / n
        a1 = a0 + math.pi / n
        d.polygon([(cx, cy), (cx + R * math.cos(a0), cy + R * math.sin(a0)),
                   (cx + R * math.cos(a1), cy + R * math.sin(a1))], fill=rgb(colour) + (alpha,))
    if fade:
        img.putalpha(ImageChops.multiply(img.getchannel("A"), radial_mask(size, centre, 0.15, 0.62)))
    return img


def banner(text_img_or_none, w, h, colour="#a01010"):
    img = Image.new("RGBA", (w, h), rgb(colour) + (255,))
    if text_img_or_none:
        img.alpha_composite(text_img_or_none, ((w - text_img_or_none.width) // 2,
                                               (h - text_img_or_none.height) // 2))
    return img


def text(s, height, colour="#ffffff", font="DejaVuSans-Bold.ttf", stroke="#000000"):
    from PIL import ImageFont
    fnt = ImageFont.truetype(font, height)
    bbox = fnt.getbbox(s, stroke_width=max(1, height // 12))
    img = Image.new("RGBA", (bbox[2] - bbox[0] + 4, bbox[3] - bbox[1] + 4), (0, 0, 0, 0))
    ImageDraw.Draw(img).text((2 - bbox[0], 2 - bbox[1]), s, font=fnt, fill=rgb(colour),
                             stroke_width=max(1, height // 12), stroke_fill=rgb(stroke))
    return img


# ------------------------------------------------------------------ маски --
def radial_mask(size, centre=(0.5, 0.5), inner=0.3, outer=0.55):
    W, H = size
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.hypot((x - centre[0] * W) / W, (y - centre[1] * H) / H * (H / W))
    m = np.clip((outer - r) / max(outer - inner, 1e-6), 0, 1)
    return Image.fromarray((m * 255).astype(np.uint8), "L")


def edge_fade(img, amount=0.25, sides="lrtb"):
    """Растворяет края слоя в прозрачность (края коллажа на примерах)."""
    W, H = img.size
    m = np.ones((H, W), np.float32)
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    if "l" in sides: m *= np.clip(x / (W * amount), 0, 1)
    if "r" in sides: m *= np.clip((W - x) / (W * amount), 0, 1)
    if "t" in sides: m *= np.clip(y / (H * amount), 0, 1)
    if "b" in sides: m *= np.clip((H - y) / (H * amount), 0, 1)
    a = np.asarray(img.getchannel("A")).astype(np.float32) * m
    out = img.copy()
    out.putalpha(Image.fromarray(a.astype(np.uint8), "L"))
    return out


def grunge(size, seed=1, strength=0.35):
    """Шумовая маска «потёртости» — умножается на альфу фона."""
    rng = np.random.default_rng(seed)
    W, H = size
    n = Image.fromarray((rng.random((H // 6 + 1, W // 6 + 1)) * 255).astype(np.uint8), "L")
    n = n.resize(size, Image.BICUBIC).filter(ImageFilter.GaussianBlur(2))
    fine = Image.fromarray((rng.random((H, W)) * 255).astype(np.uint8), "L")
    n = ImageChops.multiply(n, fine.point(lambda v: 150 + v * 105 // 255))
    return n.point(lambda v: int(255 * (1 - strength) + v * strength))


# ----------------------------------------------------------------- холст --
class Canvas:
    def __init__(self, size=(ICON_W, ICON_H)):
        self.out_size = size
        self.size = (size[0] * SS, size[1] * SS)
        self.img = Image.new("RGBA", self.size, (0, 0, 0, 0))

    def add(self, layer, at=(0.5, 0.5), scale=None, anchor="center", rotate=0,
            opacity=1.0, fade=0.0, fade_sides="lrtb", shadow=False, mask=None):
        """Кладёт слой. scale — доля высоты холста; at — точка на холсте в долях;
        anchor — какой точкой слоя её касаться: center, top, bottom-left, ..."""
        if scale is not None:
            layer = fit(layer, self.size[1] * scale)
        if rotate:
            layer = layer.rotate(rotate, expand=True, resample=Image.BICUBIC)
        if fade:
            layer = edge_fade(layer, fade, fade_sides)
        if opacity < 1:
            layer = layer.copy()
            layer.putalpha(layer.getchannel("A").point(lambda a: int(a * opacity)))
        w, h = layer.size
        x = at[0] * self.size[0]
        y = at[1] * self.size[1]
        ax = 0 if "left" in anchor else 1 if "right" in anchor else 0.5
        ay = 0 if "top" in anchor else 1 if "bottom" in anchor else 0.5
        x -= w * ax
        y -= h * ay
        pos = (round(x), round(y))
        if shadow:
            sh = Image.new("RGBA", layer.size, (0, 0, 0, 0))
            sh.putalpha(layer.getchannel("A").point(lambda a: int(a * 0.6)))
            sh = sh.filter(ImageFilter.GaussianBlur(SS * 1.5))
            self._paste(sh, (pos[0] + SS, pos[1] + SS))
        self._paste(layer, pos, mask)
        return self

    def _paste(self, layer, pos, mask=None):
        full = Image.new("RGBA", self.size, (0, 0, 0, 0))
        full.paste(layer, pos, layer)
        if mask is not None:
            full.putalpha(ImageChops.multiply(full.getchannel("A"), mask))
        self.img = Image.alpha_composite(self.img, full)

    def finish(self, outline=True):
        img = self.img
        if outline:
            a = img.getchannel("A").point(lambda v: 255 if v > 90 else 0)
            ring = a.filter(ImageFilter.MaxFilter(2 * SS - 1)).filter(ImageFilter.GaussianBlur(SS / 2))
            back = Image.new("RGBA", self.size, (10, 6, 6, 0))
            back.putalpha(ring.point(lambda v: int(v * 0.85)))
            img = Image.alpha_composite(back, img)
        return img.resize(self.out_size, Image.LANCZOS)

    def save(self, name, outline=True):
        img = self.finish(outline)
        (ROOT / DDS_DIR).mkdir(parents=True, exist_ok=True)
        (TOOL_DIR / "png").mkdir(exist_ok=True)
        img.save(TOOL_DIR / "png" / f"{name}.png")
        img.save(ROOT / DDS_DIR / f"{name}.dds")
        register(name)
        return img


# ------------------------------------------------------------ .gfx файлы --
def _shine_block(name, tex):
    anim = lambda rot: (
        "\t\tanimation = {\n"
        f'\t\t\tanimationmaskfile = "{tex}"\n'
        '\t\t\tanimationtexturefile = "gfx/interface/goals/shine_overlay.dds"\n'
        f"\t\t\tanimationrotation = {rot}\n"
        "\t\t\tanimationlooping = no\n\t\t\tanimationtime = 0.75\n\t\t\tanimationdelay = 0\n"
        '\t\t\tanimationblendmode = "add"\n\t\t\tanimationtype = "scrolling"\n'
        "\t\t\tanimationrotationoffset = { x = 0.0 y = 0.0 }\n"
        "\t\t\tanimationtexturescale = { x = 1.0 y = 1.0 }\n\t\t}\n")
    return (f'\tSpriteType = {{\n\t\tname = "{PREFIX}{name}_shine"\n\t\ttexturefile = "{tex}"\n'
            '\t\teffectFile = "gfx/FX/buttonstate.lua"\n'
            + anim("-90.0") + anim("90.0") + "\t\tlegacy_lazy_load = no\n\t}\n")


def register(name):
    """Добавляет спрайт в interface/nh_goals*.gfx, если его там ещё нет."""
    tex = f"{DDS_DIR}/{name}.dds"
    for fname, block in (
            ("nh_goals.gfx", f'\tSpriteType = {{\n\t\tname = "{PREFIX}{name}"\n'
                             f'\t\ttexturefile = "{tex}"\n\t}}\n'),
            ("nh_goals_shine.gfx", _shine_block(name, tex))):
        path = ROOT / "interface" / fname
        path.parent.mkdir(exist_ok=True)
        body = path.read_text(encoding="utf-8") if path.exists() else "spriteTypes = {\n}\n"
        marker = f'name = "{PREFIX}{name}' + ('_shine"' if "shine" in fname else '"')
        if marker in body:
            continue
        head, _, _ = body.rstrip().rpartition("}")
        path.write_text(head + block + "}\n", encoding="utf-8")


# --------------------------------------------------------------- эффекты --
def bevel(img, depth=6, strength=0.9, light=(-0.6, -0.8)):
    """Тиснение: светлый верхне-левый край, тёмный нижне-правый (карты на примерах)."""
    a = np.asarray(img.getchannel("A").filter(ImageFilter.GaussianBlur(depth))).astype(np.float32) / 255
    gy, gx = np.gradient(a)
    shade = -(gx * light[0] + gy * light[1]) * depth * 2.2 * strength
    arr = np.asarray(img).astype(np.float32)
    arr[..., :3] += (shade[..., None] * 255)
    return Image.fromarray(arr.clip(0, 255).astype(np.uint8), "RGBA")


def inner_shade(img, top="#ffffff", bottom="#000000", amount=0.35):
    """Вертикальный градиент света поверх слоя (объём у плоских заливок)."""
    W, H = img.size
    t = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
    c1, c2 = np.array(rgb(top), np.float32), np.array(rgb(bottom), np.float32)
    arr = np.asarray(img).astype(np.float32)
    over = c1 * (1 - t) + c2 * t
    arr[..., :3] = arr[..., :3] * (1 - amount) + over * amount
    return Image.fromarray(arr.clip(0, 255).astype(np.uint8), "RGBA")


def backdrop(size, colour="#000000", alpha=200, centre=(0.5, 0.5), inner=0.2, outer=0.55):
    """Тёмная подложка, растворяющаяся к краям: коллаж читается на фоне дерева."""
    img = Image.new("RGBA", size, rgb(colour) + (0,))
    img.putalpha(radial_mask(size, centre, inner, outer).point(lambda v: v * alpha // 255))
    return img


def gold_star(size=120, fill="#c01414", rim="#e8b64a", rim_width=0.14):
    s = star(size, rim)
    inner_size = int(size * (1 - rim_width * 2))
    s.alpha_composite(star(inner_size, fill), ((size - inner_size) // 2, (size - inner_size) // 2 + 1))
    return bevel(s, depth=max(2, size // 30), strength=0.8)
