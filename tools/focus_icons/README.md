# Иконки фокусов

`generate.py` рисует иконки фокусов из SVG-описаний и сразу раскладывает их по папкам мода.

```
pip install pillow cairosvg
python tools/focus_icons/generate.py
```

Результат:

| Файл | Зачем |
|---|---|
| `gfx/interface/goals/nh/*.dds` | текстуры 94×86, несжатый A8R8G8B8 |
| `interface/nh_goals.gfx` | спрайты `GFX_focus_nh_<имя>` |
| `interface/nh_goals_shine.gfx` | анимация блеска при наведении |
| `tools/focus_icons/png/*.png`, `preview.png` | просмотр без игры |

В фокусе иконка подключается так:

```
focus = {
	id = RUS_free_elections
	icon = GFX_focus_nh_free_elections
	...
}
```

Новая иконка: написать функцию `icon_<имя>()`, которая возвращает SVG в координатах 94×86, добавить её в словарь `ICONS` и перезапустить скрипт. Контур и тень добавляются автоматически.

Готовую картинку (свою или найденную) можно положить в `gfx/interface/goals/nh/` как DDS 94×86 и прописать в оба `.gfx` вручную по образцу.

## Коллажные иконки (фото, карты, флаги)

Стиль как у Millennium Dawn: вырезанные с фото люди и предметы, силуэты стран, флаги, лучи, общий цветовой тон.

```
pip install pillow cairosvg numpy "rembg[cpu]"
python tools/focus_icons/icons/ussr_referendum.py
python tools/focus_icons/show.py ussr_referendum -l "Референдум о восстановлении СССР"
```

- `collage.py` — библиотека: `cutout` (вырезание фона нейросетью), `country_map` (силуэты стран из `data/countries.geojson`, Natural Earth), `waving_flag`, `soviet_flag`, `stripes_flag`, `hammer_sickle`, `gold_star`, `rays`, `backdrop`, `tone` (перекраска в палитру red/teal/gold/blue/grey), `bevel`, `edge_fade`, `Canvas` (сборка, контур, сохранение DDS и запись в оба `.gfx`).
- `icons/<имя>.py` — сценарий одной иконки: какие слои, где и в каком порядке.
- `sources/<имя>/` — исходные картинки для этой иконки.
- `show.py` — предпросмотр на фоне дерева: крупно и в игровом масштабе с плашкой.

Размер иконки задаётся в `Canvas(size=(w, h))`, по умолчанию 94×86.
