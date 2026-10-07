# Фавикон — как подключить

Положить все файлы в корень сайта, в `<head>` добавить:

```html
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32.png">
<link rel="icon" type="image/png" sizes="16x16" href="/favicon-16.png">
<link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon-180.png">
<link rel="manifest" href="/site.webmanifest">
<meta name="theme-color" content="#111111">
```

## Что где

| Файл | Где показывается |
|---|---|
| `favicon.ico` | Вкладка браузера, закладки. Внутри 16/32/48 |
| `favicon-16/32/48/96.png` | Современные браузеры |
| `apple-touch-icon-180.png` | Иконка на домашнем экране iPhone/iPad |
| `icon-192.png`, `icon-512.png` | Android, PWA, манифест |
| `site.webmanifest` | Манифест PWA |

## Откуда

Копия иконок из `site` (новый крюк, 03.10.2026): вкладка — прозрачный фон, иконки домашнего
экрана — крюк на белой плашке. Пересобирает `tools/make_brand.py` (копирует с сайта).
