# kryuk24.ru — файлы сайта

Эта папка = содержимое `kryuk24/public_html` на Beget (без этого README, `_ready/`).
Последняя выкладка — тег git `v32-live` (05.10.2026).

## Что где

| Файл | Что это |
| --- | --- |
| `index.html`, `styles.css`, `app.js` | Главная: hero, расчет + карта, тарифы и города, галерея, FAQ, окно записи |
| `<slug>/index.html` | SEO-страницы городов и услуг. **Не править руками** — генерирует `tools/make_seo_pages.py` |
| `_ready/` | Готовые, но скрытые страницы (Химки). На сервер не выкладывается |
| `assets/` | Шрифты, фото, логотип, `pages.css` для SEO-страниц |
| `favicon*`, `icon-*`, `apple-touch-icon-180.png`, `site.webmanifest` | Иконки (новый крюк) |
| `.htaccess`, `404.html`, `robots.txt`, `sitemap.xml`, `google…html` | Сервер, ошибки, поиск |

## Как выложить изменение

1. Поднять `?v=` у измененных `styles.css` / `app.js` в `index.html` (и `VER` в генераторе, если менялись SEO-страницы) — Beget кеширует CSS/JS 7 дней.
2. Проверить локально: `tools/.venv/Scripts/python.exe tools/tests/run_checks.py` — issues 0, errors [], links_bad [].
3. Показать Гевору и получить «да».
4. Собрать измененные файлы в zip с путями от корня сайта и загрузить через файловый менеджер Beget (`cp.beget.com/fm` → `kryuk24/public_html`), там же «Распаковать Архив» в `/kryuk24/public_html`. FTP нет.
   Автоматический режим Claude Code эту загрузку и распаковку отклоняет («Production Deploy»): Гев ставит ручной режим и подтверждает запрос.
5. Убрать zip из `public_html` (переместить в домашнюю папку аккаунта), чтобы он не открывался по ссылке.
6. Сверить хеши живых файлов с локальными и прогнать `run_checks.py live`.
7. `git commit`, `main` на этот коммит, `git tag vNN-live`, отметить в `00_STATE.md`. Локальный zip — в `_ARCHIVE/deploy_packages/`.

Внешние сервисы без ключей: Photon (подсказки адресов), OSRM (км по дорогам), виджет Яндекс Карт.
Метрика 113277361 (цели `call`, `whatsapp`, `telegram`).
