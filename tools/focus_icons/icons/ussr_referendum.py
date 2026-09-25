"""Референдум о восстановлении СССР — карта союзных республик, флаг СССР, звезда."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from collage import *  # noqa: E402,F403

USSR = ["Russia", "Ukraine", "Belarus", "Kazakhstan", "Uzbekistan", "Turkmenistan",
        "Kyrgyzstan", "Tajikistan", "Georgia", "Armenia", "Azerbaijan", "Moldova",
        "Lithuania", "Latvia", "Estonia"]

c = Canvas()
W, H = c.size
c.add(backdrop(c.size, alpha=230, centre=(0.5, 0.52), inner=0.25, outer=0.62))
c.add(rays(c.size, "#b01212", n=20, centre=(0.5, 0.55), alpha=220))
m = country_map(USSR, c.size, fill="#b3191c", edge="#4a0606", box=(0.02, 0.12, 0.98, 0.84), lon0=80)
m = bevel(inner_shade(m, "#ff8a70", "#3a0000", 0.3), depth=SS * 1.2, strength=0.6)
c.add(m, shadow=True)
flag = adjust(tone(waving_flag(soviet_flag(), waves=1.2, amp=0.09), "red", 0.3), contrast=1.1, brightness=0.9)
c.add(flag, at=(0.02, 0.0), scale=0.62, anchor="top-left", rotate=6, fade=0.12, fade_sides="b")
c.add(gold_star(160), at=(0.8, 0.78), scale=0.42, shadow=True)
c.save("ussr_referendum")
print("ok")
