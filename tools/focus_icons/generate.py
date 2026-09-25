"""Генератор иконок национальных фокусов для HOI4.

Каждая иконка описана как SVG в системе координат 94x86 (размер иконки
фокуса в игре). Скрипт рендерит её с 4-кратным запасом, добавляет тёмный
контур и тень в духе ванильных иконок, уменьшает до 94x86 и сохраняет:

  gfx/interface/goals/nh/<имя>.dds      — текстура для игры
  tools/focus_icons/png/<имя>.png       — PNG для просмотра
  interface/nh_goals.gfx                — спрайты GFX_focus_nh_<имя>
  interface/nh_goals_shine.gfx          — «блеск» при наведении
  tools/focus_icons/preview.png         — лист предпросмотра

Запуск из корня мода:  python tools/focus_icons/generate.py
Зависимости:           pip install pillow cairosvg
"""

import io
import math
from pathlib import Path

import cairosvg
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[2]
TOOL_DIR = Path(__file__).resolve().parent

W, H = 94, 86          # размер иконки фокуса
SCALE = 4              # суперсэмплинг для сглаживания
PREFIX = "GFX_focus_nh_"
DDS_DIR = "gfx/interface/goals/nh"

# ---------------------------------------------------------------- палитра --
TRICOLOR = ("#e9e6dc", "#2f5aa0", "#b3312c")   # белый, синий, красный
OUTLINE = (22, 20, 18)


def grad(gid, c1, c2, x1=0, y1=0, x2=0, y2=1):
    return (f'<linearGradient id="{gid}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}">'
            f'<stop offset="0" stop-color="{c1}"/><stop offset="1" stop-color="{c2}"/>'
            f'</linearGradient>')


# ----------------------------------------------------------------- иконки --
def icon_free_elections():
    """Урна для голосования с бюллетенем."""
    return f"""
    <defs>
      {grad("front", "#6f8aa6", "#3d546d")}
      {grad("top", "#9fb4c9", "#7690aa")}
      {grad("side", "#40566e", "#2a3b4d")}
      {grad("paper", "#f6f1e3", "#d9d0b8")}
    </defs>
    <polygon points="20,38 32,28 80,28 68,38" fill="url(#top)"/>
    <polygon points="68,38 80,28 80,64 68,76" fill="url(#side)"/>
    <rect x="20" y="38" width="48" height="38" fill="url(#front)"/>
    <line x1="38" y1="33.5" x2="62" y2="33.5" stroke="#1d2833" stroke-width="3"/>
    <polygon points="41,6 63,9 60,34 38,32" fill="url(#paper)"/>
    <polyline points="44,20 49,26 58,13" fill="none" stroke="{TRICOLOR[2]}"
              stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round"/>
    <rect x="30" y="48" width="28" height="18" fill="#e4dfd1"/>
    <rect x="30" y="48" width="28" height="6" fill="{TRICOLOR[0]}"/>
    <rect x="30" y="54" width="28" height="6" fill="{TRICOLOR[1]}"/>
    <rect x="30" y="60" width="28" height="6" fill="{TRICOLOR[2]}"/>
    <line x1="20" y1="38" x2="68" y2="38" stroke="#b9c8d6" stroke-width="1"/>
    """


def icon_constitution():
    """Раскрытая книга конституции с сургучной печатью."""
    lines = []
    for i in range(6):
        y = 36 + i * 5
        lines.append(f'<line x1="17" y1="{y}" x2="42" y2="{y + 1.5}" '
                     f'stroke="#8d8471" stroke-width="1.3"/>')
        lines.append(f'<line x1="52" y1="{y + 1.5}" x2="{77 if i < 3 else 60}" y2="{y}" '
                     f'stroke="#8d8471" stroke-width="1.3"/>')
    return f"""
    <defs>
      {grad("cover", "#8e2a24", "#5a1612")}
      {grad("pageL", "#d8cfb6", "#f5efdf", 0, 0, 1, 0)}
      {grad("pageR", "#f5efdf", "#d8cfb6", 0, 0, 1, 0)}
      {grad("gold", "#f3d680", "#b58a2c")}
    </defs>
    <path d="M47,34 C38,28 22,28 8,32 L8,76 C22,72 38,72 47,78
             C56,72 72,72 86,76 L86,32 C72,28 56,28 47,34 Z" fill="url(#cover)"/>
    <path d="M47,30 C38,24 24,24 12,28 L12,71 C24,67 38,67 47,73 Z" fill="url(#pageL)"/>
    <path d="M47,30 C56,24 70,24 82,28 L82,71 C70,67 56,67 47,73 Z" fill="url(#pageR)"/>
    <line x1="47" y1="30" x2="47" y2="73" stroke="#9e937a" stroke-width="1.2"/>
    {''.join(lines)}
    <path d="M62,60 L58,76 L63,72 L66,77 L68,60 Z" fill="#7a1b16"/>
    <path d="M70,60 L74,75 L69,72 L67,77 L64,60 Z" fill="#8e2a24"/>
    <circle cx="67" cy="59" r="8" fill="#a8302a"/>
    <circle cx="67" cy="59" r="5.2" fill="none" stroke="#6e1a15" stroke-width="1.4"/>
    <circle cx="47" cy="14" r="9" fill="url(#gold)"/>
    <path d="M47,7.5 L48.9,12.3 L54,12.5 L50,15.6 L51.4,20.5 L47,17.7 L42.6,20.5
             L44,15.6 L40,12.5 L45.1,12.3 Z" fill="#fff4cf"/>
    """


def icon_parliament():
    """Здание парламента с куполом и флагом."""
    cols = "".join(
        f'<rect x="{x}" y="40" width="5" height="23" fill="url(#column)"/>'
        for x in (21, 30, 39, 50, 59, 68))
    return f"""
    <defs>
      {grad("stone", "#ece6d6", "#b9b09a")}
      {grad("column", "#f1ecdf", "#a89f88", 0, 0, 1, 0)}
      {grad("dome", "#8fc0a9", "#3f7560")}
    </defs>
    <line x1="47" y1="2" x2="47" y2="10" stroke="#3a332a" stroke-width="1.6"/>
    <path d="M47.8,2 L58,2 L58,4.4 L47.8,4.4 Z" fill="{TRICOLOR[0]}"/>
    <path d="M47.8,4.4 L58,4.4 L58,6.8 L47.8,6.8 Z" fill="{TRICOLOR[1]}"/>
    <path d="M47.8,6.8 L58,6.8 L58,9.2 L47.8,9.2 Z" fill="{TRICOLOR[2]}"/>
    <path d="M33,24 A14,14 0 0 1 61,24 Z" fill="url(#dome)"/>
    <rect x="34" y="23" width="26" height="8" fill="url(#stone)"/>
    {''.join(f'<rect x="{x}" y="24.5" width="2" height="5" fill="#8b826c"/>' for x in (37, 42, 47.5, 53))}
    <polygon points="15,36 47,25 79,36" fill="url(#stone)"/>
    <polygon points="24,34 47,27 70,34" fill="#cfc6ae"/>
    <rect x="17" y="35" width="60" height="5" fill="#d9d1bc"/>
    {cols}
    <rect x="17" y="63" width="60" height="5" fill="#cbc2aa"/>
    <rect x="12" y="68" width="70" height="7" fill="url(#stone)"/>
    """


def icon_national_revival():
    """Развевающийся триколор на древке."""
    def band(k, colour):
        a, b = k, k + 12
        return (f'<path d="M24,{12 + a} C38,{6 + a} 50,{18 + a} 66,{12 + a} '
                f'C72,{10 + a} 78,{10 + a} 84,{11 + a} L84,{11 + b} '
                f'C78,{10 + b} 72,{10 + b} 66,{12 + b} C50,{18 + b} 38,{6 + b} 24,{12 + b} Z" '
                f'fill="{colour}"/>')
    outer = ("M24,12 C38,6 50,18 66,12 C72,10 78,10 84,11 L84,47 "
             "C78,46 72,46 66,48 C50,54 38,42 24,48 Z")
    return f"""
    <defs>
      {grad("pole", "#8a6a45", "#4e3a24", 0, 0, 1, 0)}
      {grad("gold", "#f6dc8c", "#a97d24")}
      <linearGradient id="folds" x1="0" y1="0" x2="1" y2="0">
        <stop offset="0"    stop-color="#000" stop-opacity="0.25"/>
        <stop offset="0.25" stop-color="#fff" stop-opacity="0.20"/>
        <stop offset="0.45" stop-color="#000" stop-opacity="0.22"/>
        <stop offset="0.7"  stop-color="#fff" stop-opacity="0.18"/>
        <stop offset="1"    stop-color="#000" stop-opacity="0.15"/>
      </linearGradient>
    </defs>
    <rect x="19.5" y="8" width="4" height="74" fill="url(#pole)"/>
    <circle cx="21.5" cy="7" r="4" fill="url(#gold)"/>
    {band(0, TRICOLOR[0])}{band(12, TRICOLOR[1])}{band(24, TRICOLOR[2])}
    <path d="{outer}" fill="url(#folds)"/>
    """


def gear_path(cx, cy, r_out, r_in, teeth, hole):
    pts = []
    step = 2 * math.pi / teeth
    for i in range(teeth):
        a = i * step
        for da, r in ((-0.30, r_in), (-0.18, r_out), (0.18, r_out), (0.30, r_in)):
            pts.append((cx + r * math.cos(a + da * step * 1.6),
                        cy + r * math.sin(a + da * step * 1.6)))
    d = "M" + " L".join(f"{x:.2f},{y:.2f}" for x, y in pts) + " Z"
    d += (f" M{cx + hole},{cy} A{hole},{hole} 0 1 0 {cx - hole},{cy}"
          f" A{hole},{hole} 0 1 0 {cx + hole},{cy} Z")
    return d


def icon_economy():
    """Шестерня и растущий график."""
    return f"""
    <defs>
      {grad("steel", "#c9ced3", "#6a737c")}
      {grad("arrow", "#7fbf5a", "#3f7f2a")}
    </defs>
    <path d="{gear_path(38, 50, 27, 21, 10, 8)}" fill="url(#steel)" fill-rule="evenodd"/>
    <circle cx="38" cy="50" r="14" fill="none" stroke="#59616a" stroke-width="1.5"/>
    <polyline points="10,74 34,52 48,60 74,28" fill="none" stroke="#1f3a14"
              stroke-width="10" stroke-linejoin="round" stroke-linecap="round"/>
    <polyline points="10,74 34,52 48,60 74,28" fill="none" stroke="url(#arrow)"
              stroke-width="6.5" stroke-linejoin="round" stroke-linecap="round"/>
    <polygon points="86,12 82,40 60,22" fill="url(#arrow)" stroke="#1f3a14" stroke-width="1.5"/>
    """


def icon_army_reform():
    """Щит с триколором на фоне скрещённых мечей."""
    sword = """
      <polygon points="45,6 47,2 49,6 49,62 45,62" fill="url(#blade)"/>
      <line x1="47" y1="6" x2="47" y2="60" stroke="#8d949b" stroke-width="0.8"/>
      <rect x="36" y="61" width="22" height="4.5" rx="1.5" fill="url(#gold)"/>
      <rect x="45.2" y="65.5" width="3.6" height="11" fill="#5a3a22"/>
      <circle cx="47" cy="79" r="3.2" fill="url(#gold)"/>"""
    shield = ("M47,20 L71,26 L71,46 C71,61 60,71 47,78 "
              "C34,71 23,61 23,46 L23,26 Z")
    return f"""
    <defs>
      {grad("blade", "#f2f4f6", "#9aa2aa", 0, 0, 1, 0)}
      {grad("gold", "#f6dc8c", "#a97d24")}
      <clipPath id="sh"><path d="{shield}"/></clipPath>
    </defs>
    <g transform="rotate(38 47 44)">{sword}</g>
    <g transform="rotate(-38 47 44)">{sword}</g>
    <g clip-path="url(#sh)">
      <rect x="20" y="18" width="54" height="21" fill="{TRICOLOR[0]}"/>
      <rect x="20" y="39" width="54" height="18" fill="{TRICOLOR[1]}"/>
      <rect x="20" y="57" width="54" height="24" fill="{TRICOLOR[2]}"/>
      <rect x="20" y="18" width="27" height="64" fill="#fff" opacity="0.12"/>
    </g>
    <path d="{shield}" fill="none" stroke="url(#gold)" stroke-width="3"/>
    """


def icon_diplomacy():
    """Глобус в лавровом венке."""
    leaves = []
    for side in (-1, 1):
        for i in range(6):
            # от низа венка вверх по боковой дуге; y в SVG растёт вниз
            deg = 75 - i * 22
            t = math.radians(deg)
            for off in (-3.2, 3.2):                 # листья попарно снаружи и внутри
                r = 32 + off
                x = 47 + side * r * math.cos(t)
                y = 42 + r * math.sin(t)
                ang = side * (deg - 90) + side * (25 if off > 0 else -25)
                leaves.append(f'<ellipse cx="{x:.2f}" cy="{y:.2f}" rx="5.2" ry="2.3" '
                              f'transform="rotate({ang:.1f} {x:.2f} {y:.2f})" fill="url(#leaf)"/>')
    return f"""
    <defs>
      <radialGradient id="sea" cx="0.38" cy="0.35" r="0.75">
        <stop offset="0" stop-color="#8ec3e6"/><stop offset="1" stop-color="#1f4f7f"/>
      </radialGradient>
      {grad("leaf", "#9cbf5d", "#4e7026")}
      <clipPath id="g"><circle cx="47" cy="42" r="27"/></clipPath>
    </defs>
    {''.join(leaves)}
    <circle cx="47" cy="42" r="27" fill="url(#sea)"/>
    <g clip-path="url(#g)" fill="#c9b27a">
      <path d="M26,28 C32,20 42,20 46,26 C44,32 38,30 36,36 C34,42 28,42 24,38 Z"/>
      <path d="M50,24 C58,20 68,24 72,30 C70,38 62,36 60,44 C58,52 52,50 50,44 C52,36 48,30 50,24 Z"/>
      <path d="M40,50 C46,48 50,54 48,62 C46,68 40,68 38,62 C36,56 36,52 40,50 Z"/>
    </g>
    <g clip-path="url(#g)" fill="none" stroke="#e7d9a8" stroke-width="0.9" opacity="0.7">
      <ellipse cx="47" cy="42" rx="11" ry="27"/>
      <ellipse cx="47" cy="42" rx="21" ry="27"/>
      <line x1="47" y1="15" x2="47" y2="69"/>
      <line x1="20" y1="42" x2="74" y2="42"/>
      <path d="M22,30 Q47,36 72,30"/><path d="M22,54 Q47,48 72,54"/>
    </g>
    <circle cx="47" cy="42" r="27" fill="none" stroke="#caa54a" stroke-width="2"/>
    <path d="M40,76 L47,70 L54,76 L50,82 L47,78 L44,82 Z" fill="{TRICOLOR[2]}"/>
    """


def icon_free_press():
    """Газета и перо."""
    text = "".join(
        f'<rect x="{x}" y="{y}" width="{w}" height="1.8" fill="#9a9280"/>'
        for x, w in ((20, 20), (44, 20))
        for y in range(40, 74, 4))
    return f"""
    <defs>
      {grad("paper", "#f4efe0", "#cfc6ae")}
      {grad("quill", "#ffffff", "#b8b3a8", 0, 0, 1, 0)}
    </defs>
    <g transform="rotate(-7 42 48)">
      <rect x="14" y="16" width="56" height="64" fill="url(#paper)"/>
      <rect x="18" y="20" width="48" height="8" fill="#2a2a2a"/>
      <rect x="18" y="30" width="48" height="1.5" fill="#2a2a2a"/>
      <rect x="20" y="34" width="20" height="3" fill="#555"/>
      <rect x="44" y="34" width="20" height="3" fill="#555"/>
      {text}
      <rect x="44" y="52" width="20" height="14" fill="#7d8a96"/>
    </g>
    <path d="M52,76 C54,52 62,26 86,6 C82,30 70,54 52,76 Z" fill="url(#quill)"/>
    <path d="M52,76 C60,52 72,28 86,6" fill="none" stroke="#6d675c" stroke-width="1.3"/>
    <path d="M52,76 L49,84 L55,78 Z" fill="#1d1d1d"/>
    """


ICONS = {
    "free_elections":   ("Свободные выборы", icon_free_elections),
    "constitution":     ("Новая конституция", icon_constitution),
    "parliament":       ("Сильный парламент", icon_parliament),
    "national_revival": ("Национальное возрождение", icon_national_revival),
    "economy":          ("Экономические реформы", icon_economy),
    "army_reform":      ("Реформа армии", icon_army_reform),
    "diplomacy":        ("Возвращение в мир", icon_diplomacy),
    "free_press":       ("Свобода слова", icon_free_press),
}


# -------------------------------------------------------------- рендеринг --
def render(body: str) -> Image.Image:
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W * SCALE}" '
           f'height="{H * SCALE}" viewBox="0 0 {W} {H}">{body}</svg>')
    art = Image.open(io.BytesIO(cairosvg.svg2png(bytestring=svg.encode()))).convert("RGBA")
    alpha = art.getchannel("A")

    # тёмный контур ~1px в итоговом размере
    ring = alpha.filter(ImageFilter.MaxFilter(2 * SCALE - 1))
    outline = Image.new("RGBA", art.size, OUTLINE + (0,))
    outline.putalpha(ring.point(lambda a: int(a * 0.9)))

    # мягкая тень вниз-вправо
    shadow_a = ImageChops.offset(ring, SCALE, int(SCALE * 1.5)).filter(
        ImageFilter.GaussianBlur(SCALE * 1.2))
    shadow = Image.new("RGBA", art.size, (0, 0, 0, 0))
    shadow.putalpha(shadow_a.point(lambda a: int(a * 0.55)))

    out = Image.alpha_composite(shadow, outline)
    out = Image.alpha_composite(out, art)
    return out.resize((W, H), Image.LANCZOS)


def write_gfx(names):
    goals = ["spriteTypes = {"]
    shine = ["spriteTypes = {"]
    for name in names:
        tex = f"{DDS_DIR}/{name}.dds"
        goals += ["\tSpriteType = {",
                  f'\t\tname = "{PREFIX}{name}"',
                  f'\t\ttexturefile = "{tex}"',
                  "\t}"]
        shine += ["\tSpriteType = {",
                  f'\t\tname = "{PREFIX}{name}_shine"',
                  f'\t\ttexturefile = "{tex}"',
                  '\t\teffectFile = "gfx/FX/buttonstate.lua"']
        for rot in ("-90.0", "90.0"):
            shine += ["\t\tanimation = {",
                      f'\t\t\tanimationmaskfile = "{tex}"',
                      '\t\t\tanimationtexturefile = "gfx/interface/goals/shine_overlay.dds"',
                      f"\t\t\tanimationrotation = {rot}",
                      "\t\t\tanimationlooping = no",
                      "\t\t\tanimationtime = 0.75",
                      "\t\t\tanimationdelay = 0",
                      '\t\t\tanimationblendmode = "add"',
                      '\t\t\tanimationtype = "scrolling"',
                      "\t\t\tanimationrotationoffset = { x = 0.0 y = 0.0 }",
                      "\t\t\tanimationtexturescale = { x = 1.0 y = 1.0 }",
                      "\t\t}"]
        shine += ["\t\tlegacy_lazy_load = no", "\t}"]
    goals.append("}")
    shine.append("}")
    # HOI4 ожидает UTF-8 с BOM не для .gfx, а только для локализации — пишем без BOM
    (ROOT / "interface").mkdir(exist_ok=True)
    (ROOT / "interface/nh_goals.gfx").write_text("\n".join(goals) + "\n", encoding="utf-8")
    (ROOT / "interface/nh_goals_shine.gfx").write_text("\n".join(shine) + "\n", encoding="utf-8")


def preview(images):
    font = ImageFont.truetype("DejaVuSans.ttf", 11)
    cols, cell_w, cell_h = 4, 184, 170
    rows = math.ceil(len(images) / cols)
    sheet = Image.new("RGBA", (cols * cell_w, rows * cell_h), (38, 36, 31, 255))
    draw = ImageDraw.Draw(sheet)
    for i, (label, img) in enumerate(images):
        cx = (i % cols) * cell_w + cell_w // 2
        top = (i // cols) * cell_h + 14
        # плашка с названием, как в дереве фокусов
        draw.rounded_rectangle((cx - 86, top + 80, cx + 86, top + 104), 3,
                               fill=(92, 88, 76), outline=(150, 140, 110))
        sheet.alpha_composite(img, (cx - W // 2, top))
        draw.text((cx, top + 92), label, font=font, fill=(235, 228, 205), anchor="mm")
        big = img.resize((W // 2, H // 2), Image.LANCZOS)   # мелкий размер для проверки читаемости
        sheet.alpha_composite(big, (cx - W // 4, top + 108))
    sheet.save(TOOL_DIR / "preview.png")


def main():
    (ROOT / DDS_DIR).mkdir(parents=True, exist_ok=True)
    (TOOL_DIR / "png").mkdir(exist_ok=True)
    images = []
    for name, (label, fn) in ICONS.items():
        img = render(fn())
        img.save(TOOL_DIR / "png" / f"{name}.png")
        img.save(ROOT / DDS_DIR / f"{name}.dds")    # несжатый A8R8G8B8
        images.append((label, img))
    write_gfx(ICONS)
    preview(images)
    print(f"Готово: {len(ICONS)} иконок")


if __name__ == "__main__":
    main()
