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
